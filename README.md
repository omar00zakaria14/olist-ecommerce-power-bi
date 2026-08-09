# Olist E-Commerce — Power BI Project

**End-to-End Customer Journey Intelligence** for Olist's Brazilian e-commerce operations, covering revenue performance, logistics efficiency, and product category profitability.

- **Dataset:** Brazilian E-Commerce (Olist) · 2016–2018
- **Report pages:** 3 dashboard pages + data model + full DAX library
- **Total measures:** 25 DAX measures · 7 calculated columns
- **Records:** 99,441 orders · 3,095 sellers · 96,096 unique customers

## Project Team
Rawda Hesham · Shaza Yasser · Ismail Mahmoud · Hamza Ahmed · Omar Zakria · Wadie Tofiek

## Table of Contents
1. [Project Overview & Business Context](#1-project-overview--business-context)
2. [Data Sources](#2-data-sources)
3. [Data Model & DAX Reference](#3-data-model--dax-reference)
4. [Dashboard Pages](#4-dashboard-pages)
5. [KPI Reference & Verified Numbers](#5-kpi-reference--verified-numbers)
6. [Design & UX Decisions](#6-design--ux-decisions)
7. [Recommendations](#7-recommendations)

---

## 1. Project Overview & Business Context

This Power BI report delivers a full view of Olist's Brazilian e-commerce operations — covering revenue performance, logistics efficiency, and product category profitability. The project transforms 8 raw CSV files into an interactive dashboard that supports strategic and operational decision-making.

### Business Objectives
- Identify growth drivers, top regions, and top product categories
- Detect delivery delays, seller performance issues, and logistics inefficiencies
- Understand product/category profitability and freight burden
- Enable data-driven decisions for seller management, logistics, and marketing

### Report Structure

| Page | Title | Primary Focus | Key KPIs |
|---|---|---|---|
| 1 | Commercial Overview | Revenue & Market Performance | Revenue, AOV, On-Time %, Total Orders, Avg Review |
| 2 | Operations Intelligence | Delivery & Logistics | Active Sellers, On-Time %, Avg Delivery, Delayed Orders, Top Route |
| 3 | Category Analysis | Product & Freight Performance | Freight Ratio, Avg Freight, Avg Price, Total Orders, High Freight % |

> **Note:** The original documentation included a 4th "Customer Insights" page. It has been removed from this documentation set since that page is not present in the delivered `.pbix` report.

---

## 2. Data Sources

The dataset is the publicly available Olist Brazilian E-Commerce dataset. Eight CSV files were loaded into Power BI.

| File Name | Rows | Role in Model | Key Columns |
|---|---|---|---|
| olist_orders_dataset.csv | 99,441 | Fact (bridging) | order_id, customer_id, order_status, timestamps |
| olist_order_items_dataset.csv | 112,650 | Fact (main — fact_order_items) | order_id, product_id, seller_id, price, freight_value |
| olist_order_payments_dataset.csv | 103,886 | Fact (fact_payment) | order_id, payment_type, payment_value, installments |
| olist_order_reviews_dataset.csv | 98,673 | Fact (fact_reviews) | order_id, review_score, timestamps |
| olist_customers_dataset.csv | 99,441 | Dimension (dim_customer) | customer_id, customer_unique_id, city, state |
| olist_sellers_dataset.csv | 3,095 | Dimension (dim_sellers) | seller_id, seller_name, city, state |
| olist_products_dataset.csv | 32,951 | Dimension (dim_product) | product_id, category, weight_g, dimensions |
| product_category_name_translation.csv | 71 | Lookup (merged into dim_product) | category PT → EN translation |

---

## 3. Data Model & DAX Reference

Full details on the star schema, table relationships, Power Query transformations, calculated columns, and the complete DAX measure library live in [`docs/Data-Model.md`](docs/Data-Model.md) and [`docs/DAX-Reference.md`](docs/DAX-Reference.md).

**Model summary:** Star schema with `fact_order_items` as the central fact table, surrounded by `dim_order`, `dim_customer`, `dim_sellers`, `dim_product`, `dim_geolocation`, plus a DAX-generated `Date Dim` table for time intelligence and a dedicated empty `Dax Measures` table hosting all 25 measures.

---

## 4. Dashboard Pages

### 4.1 Page 1 — Commercial Overview
Executive-level snapshot of revenue performance, payment methods, top categories, and geographic distribution.

**KPI Cards**

| KPI Card | Measure Used | Value | Notes |
|---|---|---|---|
| Total Revenue | Total Revenue | 15.42M BRL | Payment-based, delivered orders only |
| (AOV) | (AOV) | $156.31 | Average order value from payments |
| On-Time Delivery % | On-Time Delivery % | 20.89% | Strict date-context calculation |
| Total Orders | Total Orders | 99K | All orders in dataset |
| Avg Review Score | Stars Measure + Avg Review Score | 4.09 ★★★★☆ | Star visual + numeric KPI |

**Visuals**

| Visual | Type | X / Axis | Y / Value | Purpose |
|---|---|---|---|---|
| Performance Trend Analysis | Line Chart | Month Name (Date Dim) | Total Revenue | Revenue growth 2016–2018 with Black Friday spike |
| Payment Types | Donut Chart | payment_type | Count / Amount | 73.92% credit card · 19.04% boleto · 5.56% voucher |
| Top Categories | Bar Chart | category | Total Revenue | Top 5: Health Beauty 1.42M, Watches 1.27M, Bed Bath 1.25M |
| Map | Azure Map | lat/lng | Total Orders (bubble size) | Geographic distribution — concentrated in SE Brazil |

### 4.2 Page 2 — Operations Intelligence
Operational view of delivery performance, seller activity, delay patterns by geography, and route efficiency.

**KPI Cards**

| KPI Card | Measure Used | Value | Notes |
|---|---|---|---|
| Active Sellers | Active Sellers | 3K | Distinct seller_id count |
| On-Time Delivery % | On-Time Delivery % | 20.89% | Strict — with USERELATIONSHIP |
| Avg Delivery Time | Avg Delivery Time | 12.43 days | Purchase to customer delivery |
| Delayed Orders | Delayed Orders | 7K | Orders with Delay Days > 0 |
| Top Delay Route | Top Delay Route | BA → MA | Highest avg delay route |

**Visuals**

| Visual | Type | X / Axis | Y / Value | Purpose |
|---|---|---|---|---|
| Avg Delivery Time by Year and Month | Line Chart | Month Name | Avg Delivery Time | Trend — early 2016 spike, stabilizing 2017–18 |
| Avg Delay Duration by state | Bar Chart | state (dim_customer) | Avg Delay Duration | AP, RR, AM top worst states — North/Northeast gap |
| Avg Delay Duration and Orders by state | Azure Map | lat/lng | Avg Delay (bubble size) | Geographic heatmap of delay severity |
| Seller Performance Table | Matrix | seller_name | total_orders, avg_review_score, avg_delay | Sellers with order count and performance scores |

### 4.3 Page 3 — Category Analysis
Deep dive into product category performance — freight cost burden, weight, price positioning, revenue, and review scores. Parameter slicer for Top N enabled.

**KPI Cards**

| KPI Card | Measure Used | Value |
|---|---|---|
| Freight Cost Ratio | Freight Cost Ratio | 14.21% |
| AVG Freight Cost | AVG Freight Cost | 19.99 BRL |
| Avg Product Price | Avg Product Price | 145.30 BRL |
| Total Orders | Total Orders | 99K |
| High Freight Order % | High Freight Order % | 35.62% |

**Visuals**

| Visual | Type | Axes | Purpose |
|---|---|---|---|
| Total Orders & Freight Cost by Category | Combo Bar+Line | category / Total Orders + Freight Cost | Compare order volume vs freight spend per category |
| Total Weight (KG) by Category | Treemap | category / Total Weight (KG) | Visual size = weight — identifies heavy shipping categories |
| Avg Price × Review Score × Orders | Bubble Chart | X=Avg Price, Y=Avg Review Score, Size=Orders | Quadrant analysis: high price + high review = premium segment |
| Total Revenue by Category | Horizontal Bar | category / Total Revenue | Revenue ranking — Health Beauty leads at 1.42M |

---

## 5. KPI Reference & Verified Numbers

All values confirmed from raw CSV data analysis. Use these to validate measures after refresh.

| KPI | Dashboard Value | Raw Data Value | Measure |
|---|---|---|---|
| Total Revenue | 15.42M BRL | 15,422,000 BRL (payments) | Total Revenue |
| AOV | $156.31 | 160.99 BRL | (AOV) |
| Total Orders | 99K | 99,441 | Total Orders |
| Active Sellers | 3K | 3,095 unique | Active Sellers |
| On-Time Delivery % | 20.89% | 20.89% (strict) | On-Time Delivery % |
| Avg Delivery Time | 12.43 days | 12.09 days avg | Avg Delivery Time |
| Delayed Orders | 7K | 7,315 orders | Delayed Orders |
| Top Delay Route | BA → MA | Highest avg delay route | Top Delay Route |
| Freight Cost Ratio | 14.21% | 14.21% confirmed | Freight Cost Ratio |
| AVG Freight Cost | 19.99 BRL | 19.99 BRL | AVG Freight Cost |
| Avg Product Price | 145.30 BRL | 145.30 BRL | Avg Product Price |
| High Freight Order % | 35.62% | 35.62% confirmed | High Freight Order % |
| Avg Review Score | 4.09 | 4.0864 | Avg Review Score |
| Stars Display | ★★★★☆ | ROUND(4.09) = 4 stars | Stars Measure |

---

## 6. Design & UX Decisions

| Decision | Rationale |
|---|---|
| Dedicated 'Dax Measures' empty table | Best practice — all measures in one place, easy to find in Data pane |
| Star schema over flat table | Better performance, cleaner relationships, enables RELATED() functions |
| Date Dim via DAX CALENDARAUTO() | Required for DATESYTD, SAMEPERIODLASTYEAR — doesn't exist in raw data |
| Two Date Dim relationships (one inactive) | Allows switching between order_date and delivered_date contexts via USERELATIONSHIP |
| Separate page per business domain | Reduces visual clutter, allows page-level filters without affecting other pages |
| Parameter table for Top N | Dynamic filtering without modifying DAX — user-controlled via slicer |
| Black Friday Marker measure | Annotates the Nov 2017 spike without hardcoding it in a visual — context-aware |
| USERELATIONSHIP in On-Time % | Activates secondary date relationship only where needed — avoids model bloat |
| AVERAGEX with VALUES() for Avg Price | Computes average at product level — prevents order-quantity bias |

---

## 7. Recommendations

| # | Finding | Recommendation | Priority |
|---|---|---|---|
| 1 | BA, AM, RR states: avg delivery 26–29 days | Recruit local sellers in Northeast & North Brazil to reduce inter-state shipping | High |
| 2 | 35.62% of orders have freight >30% of price | Introduce freight subsidy for high-ratio categories; negotiate carrier rates for heavy goods | High |
| 3 | On-Time % = 20.89% (strict) — delivery vs estimate mismatch | Recalibrate estimated delivery dates — currently over-promising speed to customers | High |
| 4 | Health Beauty leads revenue at 1.42M | Expand seller recruitment in this category; run targeted promotions | Medium |
| 5 | Black Friday spike (Nov 2017) showed capacity strain | Pre-plan logistics and seller inventory before annual peak periods | Medium |
| 6 | 7K delayed orders — delay → review score correlation -0.33 | Fix delay = fix satisfaction. Focus on last-mile (carrier→customer = 8.88 days avg) | High |

---

## Repository Structure

```
olist-ecommerce-power-bi/
├── README.md
├── docs/
│   ├── Data-Model.md       # Star schema, tables, relationships, transformations, calculated columns
│   └── DAX-Reference.md    # Full DAX measure library (25 measures)
└── reports/
    └── project-depi.pbix   # Power BI project file
```

**Tool:** Power BI Desktop · All DAX verified against raw CSV data.
