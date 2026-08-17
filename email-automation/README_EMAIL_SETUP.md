# 🚀 Power BI Local Extractor & Gmail Automation Guide

This script extracts live DAX measures and results directly from your **local Power BI Desktop** instance (100% free — no Power BI Pro / Fabric / Azure capacity required) and sends a formatted HTML executive summary email using **Gmail SMTP**.

---

## 🛠️ Step 1: Set Up Free Gmail App Password (1 minute)

Because Google requires 2-Factor Authentication (2FA) for security, standard email apps connect using a free **16-character App Password**:

1. Go to your Google Account Security settings: **[https://myaccount.google.com/security](https://myaccount.google.com/security)**
2. Make sure **2-Step Verification** is turned **ON**.
3. Search for or go directly to **App Passwords**: **[https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)**
4. Enter an App Name (e.g. `PowerBI Reporter`) and click **Create**.
5. Copy the generated **16-character password** (e.g., `abcd efgh ijkl mnop`).

---

## ⚙️ Step 2: Configure Credentials

Create a `.env` file in the project folder (or copy `.env.example` to `.env`):

```ini
GMAIL_SENDER=your_email@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
RECIPIENT_EMAILS=recipient1@gmail.com, recipient2@gmail.com
```

*(Alternatively, you can edit the `DEFAULT_CONFIG` dictionary directly in `report.py`)*

---

## 🏃 Step 3: Run the Script

Make sure your report (`.pbix`) is open in **Power BI Desktop**, then run:

### 1. Preview Extracted Metrics Locally (without sending email):
```bash
py report.py --preview-only
```
This extracts the live measures and creates:
- `report_preview.html` (Double-click to open in your browser and see the formatted email!)
- `report_data.csv` (Spreadsheet export of the measures)

### 2. List All Discovered Measures in Your Active Power BI Model:
```bash
py report.py --list-measures
```

### 3. Extract and Send the Email:
```bash
py report.py
```

### 4. Send to a Specific Recipient on the fly:
```bash
py report.py --to="colleague@example.com" --subject="Weekly Sales Summary"
```

---

## 📊 Extracted Measures & Customization

The script is pre-configured to extract key metrics from your model:
- **Financials**: Total Revenue, Total Orders, Average CLV
- **Customer & Service**: Total Customers, Avg Review Score, On-Time Delivery %
- **Fulfillment**: Delayed Orders, Active Sellers, Avg Delivery Time, Freight Cost
- **Category Breakdown**: Top 5 Product Categories by Revenue, Orders, and Review Score

To customize the measures or add new DAX calculations, simply edit `extract_report_data()` inside `report.py`!
