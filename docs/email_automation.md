# Email Automation — Power BI Executive Reporter

This module extracts live KPIs directly from a locally running **Power BI Desktop** report and emails a styled executive summary via **Gmail SMTP** — no Power BI Pro, Fabric, or Azure subscription required.

![Sample executive email report](../email-automation/Screenshot%202026-08-17%20071816.png)

## How It Works

1. **Detects the local Power BI session.** `LocalPowerBIExtractor` scans running processes for `PBIDesktop.exe` and its background `msmdsrv.exe` (the embedded Analysis Services / SSAS tabular engine) to find the local port Power BI Desktop is listening on, and locates the Microsoft ADOMD.NET client DLL needed to query it.
2. **Runs DAX queries.** It shells out to PowerShell to load the ADOMD.NET assembly and execute DAX (`EVALUATE ROW(...)` for summary KPIs, `EVALUATE TOPN(...)` for the top 5 product categories), returning results as JSON.
3. **Builds the report.** `EmailReportBuilder` formats the extracted values (currency, percentages, decimals) into a responsive HTML email and a companion CSV export of the raw metrics.
4. **Sends via Gmail.** `GmailSender` authenticates with a Gmail **App Password** over SMTP (SSL on port 465 by default, or STARTTLS on 587) and delivers the HTML email with the CSV attached.

## KPIs Extracted

| Metric | Source DAX Measure |
|---|---|
| Total Revenue / Avg CLV | `[Total Revenue]`, `[Average CLV]` |
| Total Orders / Customers | `[Total Orders]`, `[Total Customers]` |
| Avg Review Score | `[Avg Review Score]` |
| On-Time Delivery % / Delayed Orders | `[On-Time Delivery %]`, `[Delayed Orders]` |
| Active Sellers | `[Active Sellers]` |
| Avg Delivery Time / Freight Cost | `[Avg Delivery Time]`, `[Freight Cost]` |
| Top 5 Categories by Revenue | `SUMMARIZECOLUMNS(dim_product[category], ...)` |

> Customize the DAX expressions inside `extract_report_data()` to match the measure names in your own `.pbix` model.

## Requirements

- Windows OS (uses PowerShell + the ADOMD.NET client shipped with Power BI Desktop).
- Power BI Desktop installed and **open with the report file loaded** while the script runs.
- A Gmail account with **2-Step Verification** enabled and a 16-character **App Password** (not your normal password) — generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
- Python packages: `python-dotenv`, `psutil` (see `requirements.txt`).

## Setup

1. Install dependencies:
   ```bash
   pip install -r email-automation/requirements.txt
   ```
2. Copy `.env.example` to `.env` in the same folder and fill in your credentials:
   ```
   GMAIL_SENDER=your_email@gmail.com
   GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
   RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com
   EMAIL_SUBJECT=Olist E-commerce — Executive Performance Summary
   ```
3. Open the Olist `.pbix` report in Power BI Desktop and leave it running.

## Usage

Run all commands from the `email-automation/` folder with the `.pbix` open in Power BI Desktop.

**Send the report immediately** (uses recipients/subject from `.env`):
```bash
python power_bi_email_reporter.py
```

**Preview without sending** (writes `report_preview.html` and `report_data.csv` locally):
```bash
python power_bi_email_reporter.py --preview-only
```

**List all DAX measures available in the open model** (useful for adapting the queries to a new report):
```bash
python power_bi_email_reporter.py --list-measures
```

**Override recipients, sender, or subject inline:**
```bash
python power_bi_email_reporter.py --to "alice@example.com,bob@example.com" --subject "Weekly Olist KPI Snapshot"
```

## Scheduling It

To fully automate delivery, register the script with **Windows Task Scheduler**:
1. Trigger: daily/weekly at your preferred time.
2. Action: start a program → `python.exe` with argument `C:\path\to\power_bi_email_reporter.py`.
3. Ensure the task runs only while Power BI Desktop is open with the report loaded, or chain it after a script that opens the `.pbix` first.

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `Could not connect to local Power BI Desktop` | Power BI Desktop isn't open, or no report loaded | Open the `.pbix` file and wait for it to fully load before running |
| `Authentication failed with Gmail SMTP` | Using your regular Gmail password instead of an App Password | Generate an App Password with 2-Step Verification enabled |
| ADOMD DLL not found | Power BI Desktop installed in a nonstandard path | Confirm install path matches `C:\Program Files\Microsoft Power BI Desktop\bin` or `(x86)` equivalent |
| Empty KPI values in the email | DAX measure names in the script don't match your model | Run `--list-measures` and update `extract_report_data()` accordingly |

## Security Notes

- Never commit `.env` or real credentials — only `.env.example` (with placeholders) should be tracked. Add `.env` to `.gitignore`.
- App Passwords are scoped to SMTP access only and can be revoked anytime from your Google Account without changing your main password.
