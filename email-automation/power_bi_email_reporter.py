"""
Power BI Desktop Metric Extractor & Automated Gmail Reporter
===========================================================
Extracts live DAX measures and summary metrics from an open local Power BI Desktop
report (100% Free - no Power BI Pro / Fabric / Azure subscription required)
and emails a styled executive report using Gmail SMTP.

Author: Antigravity Assistant
"""
from dotenv import load_dotenv 
load_dotenv()

import argparse
import csv
import io
import json
import os
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

import psutil

# Ensure terminal console supports UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ==============================================================================
# CONFIGURATION
# You can set these directly here, or use a .env file / environment variables.
# ==============================================================================

DEFAULT_CONFIG = {
    # Gmail Sender credentials (Requires a Gmail "App Password", not your main password)
    # See instructions in README_EMAIL_SETUP.md or run --help
    "GMAIL_SENDER": os.getenv("GMAIL_SENDER"),
    "GMAIL_APP_PASSWORD": os.getenv("GMAIL_APP_PASSWORD"),
    
    # Default recipient(s) (comma-separated if multiple)
    "RECIPIENT_EMAILS": os.getenv("RECIPIENT_EMAILS"),
    
    # Email Subject
    "EMAIL_SUBJECT":os.getenv("EMAIL_SUBJECT"),
    
    # SMTP Configuration
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 465,  # 465 for SSL, 587 for STARTTLS
    "USE_SSL": True,
}


def load_env_file(filepath: str = ".env") -> None:
    """Load key-value pairs from a .env file into environment variables."""
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception as e:
        print(f"[Warning] Failed to load {filepath}: {e}")


# Load environment variables on startup
load_env_file()


# ==============================================================================
# 1. LOCAL POWER BI DESKTOP EXTRACTOR
# ==============================================================================
class LocalPowerBIExtractor:
    """
    Connects directly to the local Analysis Services (SSAS) tabular engine hosted
    by Power BI Desktop on Windows. Extracts tables, DAX measures, and query results.
    """

    def __init__(self):
        self.port, self.bin_dir = self._detect_powerbi_process()
        self.dll_path = self._find_adomd_dll(self.bin_dir) if self.bin_dir else None

    @staticmethod
    def _detect_powerbi_process() -> Tuple[Optional[int], Optional[str]]:
        """
        Locates the running Power BI Desktop instance and its background
        Analysis Services (msmdsrv.exe) listening port.
        """
        msmdsrv_port = None
        pbi_bin_dir = None

        for proc in psutil.process_iter(["name", "exe"]):
            try:
                name = (proc.info["name"] or "").lower()
                if "msmdsrv" in name:
                    # Retrieve TCP listening ports
                    connections = (
                        proc.net_connections()
                        if hasattr(proc, "net_connections")
                        else proc.connections()
                    )
                    for conn in connections:
                        if conn.status == "LISTEN":
                            msmdsrv_port = conn.laddr.port
                            break
                elif "pbidesktop" in name:
                    exe_path = proc.info["exe"] or ""
                    if exe_path:
                        pbi_bin_dir = os.path.dirname(exe_path)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return msmdsrv_port, pbi_bin_dir

    @staticmethod
    def _find_adomd_dll(bin_dir: Optional[str]) -> Optional[str]:
        """Locates the required Microsoft ADOMD Client DLL."""
        search_dirs = []
        if bin_dir:
            search_dirs.append(bin_dir)
        
        # Common fallback locations for Power BI Desktop
        search_dirs.extend([
            r"C:\Program Files\Microsoft Power BI Desktop\bin",
            r"C:\Program Files (x86)\Microsoft Power BI Desktop\bin",
        ])

        candidates = [
            "Microsoft.PowerBI.AdomdClient.dll",
            "Microsoft.AnalysisServices.AdomdClient.dll",
        ]

        for d in search_dirs:
            if os.path.exists(d):
                for candidate in candidates:
                    candidate_path = os.path.join(d, candidate)
                    if os.path.exists(candidate_path):
                        return candidate_path

        return None

    def is_connected(self) -> bool:
        """Returns True if Power BI Desktop and ADOMD DLL were found."""
        return bool(self.port and self.dll_path)

    def execute_dax(self, dax_query: str) -> List[Dict[str, Any]]:
        """
        Executes a DAX query against the local Power BI Desktop instance
        and returns the results as a list of dictionaries.
        """
        if not self.is_connected():
            raise RuntimeError(
                "Power BI Desktop is not running or no active report is open.\n"
                "Please open your Power BI (.pbix) report in Power BI Desktop first."
            )

        ps_script = f"""
$dll = '{self.dll_path}'
[System.Reflection.Assembly]::LoadFrom($dll) | Out-Null
$connStr = 'Data Source=localhost:{self.port};'
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($connStr)
$conn.Open()

$cmd = $conn.CreateCommand()
$cmd.CommandText = @'
{dax_query}
'@

$adapter = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdDataAdapter($cmd)
$dt = New-Object System.Data.DataTable
$adapter.Fill($dt) | Out-Null

$rows = @()
foreach ($r in $dt.Rows) {{
    $obj = [ordered]@{{}}
    foreach ($col in $dt.Columns) {{
        $obj[$col.ColumnName] = $r[$col.ColumnName]
    }}
    $rows += $obj
}}

$conn.Close()

$rows | ConvertTo-Json -Depth 5
"""
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
        )

        if res.returncode != 0 or (res.stderr and "Exception calling" in res.stderr):
            err_msg = res.stderr.strip() or res.stdout.strip()
            raise RuntimeError(f"DAX Execution Error:\n{err_msg}")

        output_str = res.stdout.strip()
        if not output_str:
            return []

        data = json.loads(output_str)
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        return []

    def get_all_measures(self) -> List[Dict[str, str]]:
        """Discovers all DAX measures defined across all tables in the active model."""
        if not self.is_connected():
            return []

        ps_script = f"""
$dll = '{self.dll_path}'
[System.Reflection.Assembly]::LoadFrom($dll) | Out-Null
$connStr = 'Data Source=localhost:{self.port};'
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($connStr)
$conn.Open()

# 1. Get Tables mapping
$cmd = $conn.CreateCommand()
$cmd.CommandText = 'SELECT [ID], [Name] FROM $SYSTEM.TMSCHEMA_TABLES'
$adapter = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdDataAdapter($cmd)
$dtTables = New-Object System.Data.DataTable
$adapter.Fill($dtTables) | Out-Null

$tableMap = @{{}}
foreach ($r in $dtTables.Rows) {{
    $tableMap[$r['ID']] = $r['Name']
}}

# 2. Get Measures
$cmd.CommandText = 'SELECT [TableID], [Name], [Expression] FROM $SYSTEM.TMSCHEMA_MEASURES'
$dtMeasures = New-Object System.Data.DataTable
$adapter.Fill($dtMeasures) | Out-Null

$measures = @()
foreach ($r in $dtMeasures.Rows) {{
    $tName = $tableMap[$r['TableID']]
    $measures += @{{
        Table = $tName
        Name = $r['Name']
        Expression = $r['Expression']
    }}
}}

$conn.Close()
$measures | ConvertTo-Json -Depth 5
"""
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                parsed = json.loads(res.stdout.strip())
                return parsed if isinstance(parsed, list) else [parsed]
            except Exception:
                pass
        return []

    def extract_report_data(self) -> Dict[str, Any]:
        """
        Extracts high-level executive KPIs and breakdown tables from the active model.
        Customize the DAX expressions here to match your specific report measures!
        """
        # 1. Summary KPIs
        summary_dax = """
EVALUATE
ROW(
    "Total Revenue", [Total Revenue],
    "Total Orders", [Total Orders],
    "Total Customers", [Total Customers],
    "Avg Review Score", [Avg Review Score],
    "On-Time Delivery %", [On-Time Delivery %],
    "Delayed Orders", [Delayed Orders],
    "Active Sellers", [Active Sellers],
    "Avg Delivery Time (Days)", [Avg Delivery Time],
    "Average CLV", [Average CLV],
    "Freight Cost", [Freight Cost]
)
"""
        summary_results = self.execute_dax(summary_dax)
        kpis = summary_results[0] if summary_results else {}

        # 2. Category Performance Breakdown
        category_dax = """
EVALUATE
TOPN(
    5,
    SUMMARIZECOLUMNS(
        dim_product[category],
        "Revenue", [Total Revenue],
        "Orders", [Total Orders],
        "AvgReview", [Avg Review Score]
    ),
    [Revenue],
    DESC
)
"""
        category_results = self.execute_dax(category_dax)

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kpis": kpis,
            "top_categories": category_results,
        }


# ==============================================================================
# 2. HTML EMAIL REPORT BUILDER
# ==============================================================================
class EmailReportBuilder:
    """Formats extracted Power BI metrics into a responsive, modern HTML email."""

    @staticmethod
    def format_currency(val: Any) -> str:
        try:
            return f"${float(val):,.2f}"
        except (ValueError, TypeError):
            return str(val)

    @staticmethod
    def format_number(val: Any) -> str:
        try:
            return f"{int(float(val)):,}"
        except (ValueError, TypeError):
            return str(val)

    @staticmethod
    def format_percent(val: Any) -> str:
        try:
            return f"{float(val) * 100:.2f}%"
        except (ValueError, TypeError):
            return str(val)

    @staticmethod
    def format_decimal(val: Any, decimals: int = 2) -> str:
        try:
            return f"{float(val):.{decimals}f}"
        except (ValueError, TypeError):
            return str(val)

    def build_html(self, report_data: Dict[str, Any]) -> str:
        """Constructs a responsive executive email report."""
        kpis = report_data.get("kpis", {})
        categories = report_data.get("top_categories", [])
        timestamp = report_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Clean KPI keys
        clean_kpis = {k.strip("[]"): v for k, v in kpis.items()}

        total_revenue = self.format_currency(clean_kpis.get("Total Revenue", 0))
        total_orders = self.format_number(clean_kpis.get("Total Orders", 0))
        total_customers = self.format_number(clean_kpis.get("Total Customers", 0))
        avg_review = self.format_decimal(clean_kpis.get("Avg Review Score", 0), 2)
        on_time_pct = self.format_percent(clean_kpis.get("On-Time Delivery %", 0))
        delayed_orders = self.format_number(clean_kpis.get("Delayed Orders", 0))
        active_sellers = self.format_number(clean_kpis.get("Active Sellers", 0))
        avg_delivery = self.format_decimal(clean_kpis.get("Avg Delivery Time (Days)", 0), 1) + " days"
        avg_clv = self.format_currency(clean_kpis.get("Average CLV", 0))
        freight_cost = self.format_currency(clean_kpis.get("Freight Cost", 0))

        # Build table rows for categories
        cat_rows_html = ""
        for idx, row in enumerate(categories, 1):
            cat_name = row.get("dim_product[category]", "N/A")
            rev = self.format_currency(row.get("[Revenue]", row.get("Revenue", 0)))
            orders = self.format_number(row.get("[Orders]", row.get("Orders", 0)))
            review = self.format_decimal(row.get("[AvgReview]", row.get("AvgReview", 0)), 2)

            bg_color = "#ffffff" if idx % 2 != 0 else "#f8fafc"
            cat_rows_html += f"""
            <tr style="background-color: {bg_color};">
                <td style="padding: 12px 16px; font-weight: 600; color: #1e293b; border-bottom: 1px solid #e2e8f0;">#{idx} {cat_name}</td>
                <td style="padding: 12px 16px; text-align: right; color: #0f766e; font-weight: 700; border-bottom: 1px solid #e2e8f0;">{rev}</td>
                <td style="padding: 12px 16px; text-align: right; color: #334155; border-bottom: 1px solid #e2e8f0;">{orders}</td>
                <td style="padding: 12px 16px; text-align: right; color: #d97706; font-weight: 600; border-bottom: 1px solid #e2e8f0;">★ {review}</td>
            </tr>
            """

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Power BI Executive Summary</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #334155;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9; padding: 30px 10px;">
        <tr>
            <td align="center">
                <!-- Main Container -->
                <table role="presentation" width="650" cellspacing="0" cellpadding="0" style="max-width: 650px; width: 100%; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
                    
                    <!-- Header Banner -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 32px 30px; text-align: left;">
                            <table width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <div style="font-size: 12px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px;">
                                            AUTOMATED REPORT • POWER BI
                                        </div>
                                        <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; line-height: 1.2;">
                                            Executive Performance Summary
                                        </h1>
                                        <div style="font-size: 13px; color: #94a3b8; margin-top: 8px;">
                                            Generated: {timestamp} • Source: Local Power BI Desktop
                                        </div>
                                    </td>
                                    <td align="right" valign="top">
                                        <span style="background-color: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; padding: 6px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase;">
                                            LIVE SYNC
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Content Body -->
                    <tr>
                        <td style="padding: 30px;">
                            
                            <!-- KPI Cards Grid (Row 1) -->
                            <div style="font-size: 14px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px;">
                                📈 Core Financial & Growth Metrics
                            </div>
                            <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                <tr>
                                    <!-- Revenue Card -->
                                    <td width="50%" style="padding-right: 8px;" valign="top">
                                        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 18px; text-align: left;">
                                            <div style="font-size: 12px; font-weight: 600; color: #166534; text-transform: uppercase;">Total Revenue</div>
                                            <div style="font-size: 26px; font-weight: 800; color: #15803d; margin: 4px 0;">{total_revenue}</div>
                                            <div style="font-size: 12px; color: #166534;">Avg CLV: <b>{avg_clv}</b></div>
                                        </div>
                                    </td>
                                    <!-- Orders Card -->
                                    <td width="50%" style="padding-left: 8px;" valign="top">
                                        <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 18px; text-align: left;">
                                            <div style="font-size: 12px; font-weight: 600; color: #1e40af; text-transform: uppercase;">Total Orders</div>
                                            <div style="font-size: 26px; font-weight: 800; color: #1d4ed8; margin: 4px 0;">{total_orders}</div>
                                            <div style="font-size: 12px; color: #1e40af;">Customers: <b>{total_customers}</b></div>
                                        </div>
                                    </td>
                                </tr>
                            </table>

                            <!-- KPI Cards Grid (Row 2) -->
                            <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 30px;">
                                <tr>
                                    <!-- Review Score -->
                                    <td width="33.33%" style="padding-right: 6px;" valign="top">
                                        <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; padding: 14px; text-align: center;">
                                            <div style="font-size: 11px; font-weight: 600; color: #92400e; text-transform: uppercase;">Avg Review</div>
                                            <div style="font-size: 20px; font-weight: 800; color: #b45309; margin: 4px 0;">★ {avg_review} <span style="font-size: 12px; font-weight: normal; color: #92400e;">/ 5.0</span></div>
                                        </div>
                                    </td>
                                    <!-- On-Time Delivery -->
                                    <td width="33.33%" style="padding: 0 3px;" valign="top">
                                        <div style="background-color: #faf5ff; border: 1px solid #e9d5ff; border-radius: 10px; padding: 14px; text-align: center;">
                                            <div style="font-size: 11px; font-weight: 600; color: #6b21a8; text-transform: uppercase;">On-Time %</div>
                                            <div style="font-size: 20px; font-weight: 800; color: #7e22ce; margin: 4px 0;">{on_time_pct}</div>
                                        </div>
                                    </td>
                                    <!-- Active Sellers -->
                                    <td width="33.33%" style="padding-left: 6px;" valign="top">
                                        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; text-align: center;">
                                            <div style="font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase;">Active Sellers</div>
                                            <div style="font-size: 20px; font-weight: 800; color: #334155; margin: 4px 0;">{active_sellers}</div>
                                        </div>
                                    </td>
                                </tr>
                            </table>

                            <!-- Operations & Fulfillment Summary -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; margin-bottom: 30px;">
                                <div style="font-size: 13px; font-weight: 700; color: #334155; margin-bottom: 8px;">
                                    🚚 Operations & Logistics Highlights:
                                </div>
                                <table width="100%" cellspacing="0" cellpadding="4" style="font-size: 13px; color: #475569;">
                                    <tr>
                                        <td>• <b>Avg Delivery Time:</b> {avg_delivery}</td>
                                        <td>• <b>Delayed Orders:</b> {delayed_orders}</td>
                                    </tr>
                                    <tr>
                                        <td>• <b>Total Freight Cost:</b> {freight_cost}</td>
                                        <td>• <b>Status:</b> Healthy Operation</td>
                                    </tr>
                                </table>
                            </div>

                            <!-- Top Product Categories Table -->
                            <div style="font-size: 14px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">
                                🏆 Top Product Categories by Revenue
                            </div>
                            <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; width: 100%; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; font-size: 13px;">
                                <thead>
                                    <tr style="background-color: #f1f5f9; color: #475569; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">
                                        <th style="padding: 12px 16px; text-align: left; border-bottom: 2px solid #cbd5e1;">Category</th>
                                        <th style="padding: 12px 16px; text-align: right; border-bottom: 2px solid #cbd5e1;">Revenue</th>
                                        <th style="padding: 12px 16px; text-align: right; border-bottom: 2px solid #cbd5e1;">Orders</th>
                                        <th style="padding: 12px 16px; text-align: right; border-bottom: 2px solid #cbd5e1;">Avg Review</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {cat_rows_html}
                                </tbody>
                            </table>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 30px; text-align: center; font-size: 12px; color: #94a3b8;">
                            <p style="margin: 0 0 6px 0;">This email was automatically generated from your local Power BI Desktop environment.</p>
                            <p style="margin: 0;">© {datetime.now().year} Power BI Automated Reporter • 100% Free Local Automation</p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        return html_template

    @staticmethod
    def clean_column_name(col_name: str) -> str:
        """Cleans table prefixes and brackets from DAX column names."""
        name = col_name.strip()
        if "[" in name and name.endswith("]"):
            name = name.split("[")[-1].rstrip("]")
        return name

    def build_csv_attachment(self, report_data: Dict[str, Any]) -> str:
        """Generates a formatted CSV string containing extracted measures and breakdown data."""
        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Summary KPIs Section
        writer.writerow(["--- POWER BI SUMMARY METRICS ---"])
        writer.writerow(["Metric Name", "Value"])
        kpis = report_data.get("kpis", {})
        for k, v in kpis.items():
            writer.writerow([self.clean_column_name(k), v])

        writer.writerow([])

        # 2. Category Section
        writer.writerow(["--- TOP CATEGORIES BREAKDOWN ---"])
        categories = report_data.get("top_categories", [])
        if categories:
            headers = [self.clean_column_name(h) for h in categories[0].keys()]
            writer.writerow(headers)
            for row in categories:
                writer.writerow(list(row.values()))

        return output.getvalue()



# ==============================================================================
# 3. GMAIL SMTP SENDER
# ==============================================================================
class GmailSender:
    """Handles secure authentication and email delivery via Gmail SMTP."""

    def __init__(
        self,
        sender_email: str,
        app_password: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 465,
        use_ssl: bool = True,
    ):
        self.sender_email = sender_email.strip()
        self.app_password = app_password.strip().replace(" ", "")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl

    def send_report(
        self,
        recipient_emails: List[str],
        subject: str,
        html_content: str,
        csv_attachment: Optional[str] = None,
        csv_filename: str = "powerbi_measures.csv",
    ) -> bool:
        """
        Sends the HTML report and optional CSV attachment to recipients.
        """
        if not self.sender_email or not self.app_password:
            raise ValueError(
                "Gmail sender email or App Password is missing!\n"
                "Please configure GMAIL_SENDER and GMAIL_APP_PASSWORD in .env or DEFAULT_CONFIG."
            )

        if not recipient_emails:
            raise ValueError("No recipient email address provided.")

        msg = MIMEMultipart("mixed")
        msg["From"] = f"Power BI Reporter <{self.sender_email}>"
        msg["To"] = ", ".join(recipient_emails)
        msg["Subject"] = subject

        # HTML Body
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # CSV Attachment
        if csv_attachment:
            attachment_part = MIMEApplication(csv_attachment.encode("utf-8"), Name=csv_filename)
            attachment_part["Content-Disposition"] = f'attachment; filename="{csv_filename}"'
            msg.attach(attachment_part)

        # Connect and Send
        print(f"Connecting to {self.smtp_server}:{self.smtp_port}...")
        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.app_password)
                    server.sendmail(self.sender_email, recipient_emails, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.sender_email, self.app_password)
                    server.sendmail(self.sender_email, recipient_emails, msg.as_string())

            print(f"✅ Email successfully sent to: {', '.join(recipient_emails)}")
            return True
        except smtplib.SMTPAuthenticationError as auth_err:
            raise RuntimeError(
                f"Authentication failed with Gmail SMTP ({auth_err}).\n"
                "Please ensure you are using a 16-character 'Gmail App Password' "
                "(with 2-Step Verification enabled on your Google Account), not your regular password.\n"
                "Generate one here: https://myaccount.google.com/apppasswords"
            ) from auth_err


# ==============================================================================
# 4. MAIN ORCHESTRATOR & CLI
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Extract metrics from local Power BI Desktop and send email reports via Gmail."
    )
    parser.add_argument(
        "--list-measures",
        action="store_true",
        help="List all tables and DAX measures discovered in the open Power BI Desktop model.",
    )
    parser.add_argument(
        "--preview-only",
        "--dry-run",
        action="store_true",
        help="Extract measures and generate 'report_preview.html' and 'report_data.csv' without sending an email.",
    )
    parser.add_argument(
        "--to",
        type=str,
        default=DEFAULT_CONFIG["RECIPIENT_EMAILS"],
        help="Recipient email address(es), comma-separated.",
    )
    parser.add_argument(
        "--sender",
        type=str,
        default=DEFAULT_CONFIG["GMAIL_SENDER"],
        help="Gmail sender email address.",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default=DEFAULT_CONFIG["EMAIL_SUBJECT"],
        help="Subject line for the email report.",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("📊 Power BI Local DAX Extractor & Gmail Automation")
    print("=" * 65)

    # 1. Initialize Extractor
    extractor = LocalPowerBIExtractor()
    if not extractor.is_connected():
        print("❌ Could not connect to local Power BI Desktop.")
        print("\nTroubleshooting tips:")
        print(" 1. Make sure Power BI Desktop is open with your report (.pbix).")
        print(" 2. Ensure Power BI Desktop is actively running.")
        sys.exit(1)

    print(f"✔ Connected to Local Power BI Desktop on Port: {extractor.port}")
    print(f"✔ Using ADOMD Driver: {extractor.dll_path}")

    # 2. List Measures if requested
    if args.list_measures:
        print("\n🔍 Discovering DAX measures in active model...")
        measures = extractor.get_all_measures()
        print(f"Found {len(measures)} measures:")
        for m in measures:
            print(f"  • [{m.get('Table')}].[{m.get('Name')}] => {m.get('Expression', '').strip()}")
        return

    # 3. Extract Live Report Data
    print("\n⚡ Extracting measures and summary results from Power BI...")
    try:
        report_data = extractor.extract_report_data()
    except Exception as e:
        print(f"❌ Failed to extract report data: {e}")
        sys.exit(1)

    print(f"✔ Extracted {len(report_data.get('kpis', {}))} KPI metrics")
    print(f"✔ Extracted {len(report_data.get('top_categories', []))} Category breakdown rows")

    # 4. Build HTML & CSV
    builder = EmailReportBuilder()
    html_content = builder.build_html(report_data)
    csv_content = builder.build_csv_attachment(report_data)

    # Always save a local preview for user inspection
    preview_file = "report_preview.html"
    csv_file = "report_data.csv"

    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write(csv_content)

    print(f"✔ Saved HTML preview to: {os.path.abspath(preview_file)}")
    print(f"✔ Saved CSV data export to: {os.path.abspath(csv_file)}")

    # 5. Handle Dry-Run / Preview Mode
    if args.preview_only:
        print("\n✨ Dry-run mode completed. Open 'report_preview.html' in your browser to inspect the result.")
        return

    # 6. Send Email via Gmail
    sender_email = args.sender or DEFAULT_CONFIG["GMAIL_SENDER"]
    app_password = DEFAULT_CONFIG["GMAIL_APP_PASSWORD"]
    recipients = [r.strip() for r in args.to.split(",") if r.strip()]

    if not sender_email or not app_password or not recipients:
        print("\n" + "!" * 65)
        print("ℹ Gmail Credentials / Recipients Not Yet Configured!")
        print("!" * 65)
        print("To send the email automatically:")
        print("1. Create a '.env' file or fill in DEFAULT_CONFIG at the top of report.py:")
        print("     GMAIL_SENDER=your_email@gmail.com")
        print("     GMAIL_APP_PASSWORD=your_16_char_app_password")
        print("     RECIPIENT_EMAILS=recipient@example.com")
        print("\n2. Need a Gmail App Password? Follow the guide in README_EMAIL_SETUP.md")
        print("   (It's completely free and takes 1 minute in your Google Account Security settings).")
        print("\n💡 You can still view your extracted report right now in 'report_preview.html'!")
        return

    print(f"\n📧 Sending report to: {', '.join(recipients)}...")
    sender = GmailSender(
        sender_email=sender_email,
        app_password=app_password,
        smtp_server=DEFAULT_CONFIG["SMTP_SERVER"],
        smtp_port=DEFAULT_CONFIG["SMTP_PORT"],
        use_ssl=DEFAULT_CONFIG["USE_SSL"],
    )

    try:
        sender.send_report(
            recipient_emails=recipients,
            subject=args.subject,
            html_content=html_content,
            csv_attachment=csv_content,
            csv_filename=f"PowerBI_Report_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        print("\n🎉 All Done! Your Power BI report was extracted and delivered successfully.")
    except Exception as e:
        print(f"\n❌ Error sending email: {e}")


if __name__ == "__main__":
    main()
