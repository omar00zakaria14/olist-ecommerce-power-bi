# Olist E-Commerce — Power BI Project

**End-to-End Customer Journey Intelligence** dashboard for Olist's Brazilian e-commerce operations, covering commercial performance, delivery operations, and product-category analysis.

- **Dataset:** Brazilian E-Commerce (Olist), 2016–2018
- **Report pages:** 3 dashboard pages
- **Model:** Star schema with dedicated date and measure tables
- **Measures:** 25 documented DAX measures
- **Calculated columns:** 7
- **Records:** 99,441 orders, 3,095 sellers

## Project Overview

This Power BI project transforms eight Olist CSV files into an interactive report supporting revenue analysis, logistics monitoring, freight analysis, seller performance, and product-category decisions.

The original PDF contained a Customer Insights page. That page is intentionally excluded here because it is not present in the delivered report.

## Dashboard Preview

### Page 1 — Commercial Overview

Executive view of revenue, average order value, on-time delivery, orders, reviews, payment types, top categories, revenue trend, and geographic distribution.

![Page 1 — Commercial Overview](screenshots/Page%201%20%E2%80%94%20Commercial%20Overview.png)

### Page 2 — Operations Intelligence

Operational view of active sellers, delivery performance, delayed orders, delivery trends, delay duration by state, geographic delay distribution, and seller performance.

![Page 2 — Operations Intelligence](screenshots/Page%202%20%E2%80%94%20Operations%20Intelligence.png)

### Page 3 — Category Analysis

Category-level analysis of freight burden, average product price, order volume, product weight, review scores, and revenue.

![Page 3 — Category Analysis](screenshots/Page%203%20%E2%80%94%20Category%20Analysis.png)

## Data Model

The report uses `fact_order_items` as the central fact table, surrounded by order, customer, seller, product, geolocation, payment, review, and date tables. The inactive delivery-date relationship is activated by the on-time delivery measure using `USERELATIONSHIP`.

![Power BI Data Model](screenshots/Data%20Model.png)

Detailed model documentation is available in [`docs/Data-Model.md`](docs/Data-Model.md).

## Report Pages

| Page | Focus | Main KPIs |
|---|---|---|
| Commercial Overview | Revenue and market performance | Revenue, AOV, on-time delivery, total orders, review score |
| Operations Intelligence | Delivery and logistics | Active sellers, on-time delivery, average delivery, delayed orders, top route |
| Category Analysis | Product and freight performance | Freight ratio, average freight, average price, total orders, high-freight percentage |

## Key KPIs

| KPI | Value |
|---|---:|
| Total Revenue | 15.42M BRL |
| Average Order Value | 160.99 BRL |
| Total Orders | 99,441 |
| Active Sellers | 3,095 |
| On-Time Delivery | 20.89% strict calculation |
| Average Delivery Time | 12.43 days |
| Delayed Orders | Approximately 7K |
| Freight Cost Ratio | 14.21% |
| Average Freight Cost | 19.99 BRL |
| Average Product Price | 145.30 BRL |
| High Freight Order Percentage | 35.62% |
| Average Review Score | 4.09 / 5 |

## Data Sources

The model uses the public Olist Brazilian E-Commerce dataset:

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_sellers_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`

## Documentation

- [`docs/Data-Model.md`](docs/Data-Model.md) — tables, relationships, Power Query transformations, date table, and calculated columns.
- [`docs/DAX-Reference.md`](docs/DAX-Reference.md) — documented DAX measures, formulas, outputs, and usage.
- [`screenshots/`](screenshots/) — dashboard page and data-model screenshots.

## Email Automation

An automated Gmail reporter (`email-automation/power_bi_email_reporter.py`) connects live to this dashboard while it's open in Power BI Desktop, extracts the core KPIs and top product categories via DAX, and emails a styled executive summary plus a CSV export — fully free, no Power BI Pro required.

![Executive email report sample](email-automation/Screenshot%202026-08-17%20071816.png)

See [`docs/email_automation.md`](docs/email_automation.md) for setup, usage, and scheduling instructions.

## Recommendations

The analysis highlights several priorities: improve delivery performance in high-delay regions, reduce the freight burden on high-ratio orders, recalibrate delivery estimates, strengthen Health Beauty category growth, and prepare logistics capacity for peak events such as Black Friday.

**Tool:** Power BI Desktop,PowerQuery,DAX,Antigravity