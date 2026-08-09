# Data Model & Relationships (Star Schema)

The model follows a Star Schema design with `fact_order_items` as the central fact table, surrounded by dimension tables. A dedicated Date Dim table is created via DAX to enable time intelligence functions.

## Tables in the Model

| Table Name | Type | Description |
|---|---|---|
| `fact_order_items` | Fact | Central fact table — one row per order item. Contains price, freight_value, seller_id, product_id, timestamps, and all calculated columns. |
| `fact_payment` | Fact | Payment details per order — payment_type, payment_value, installments. |
| `fact_reviews` | Fact | Customer reviews — review_score per order_id. |
| `dim_order` | Dimension | Order-level metadata — order_status, customer_id. |
| `dim_customer` | Dimension | Customer profile — customer_unique_id, city, state, zip_code. |
| `dim_sellers` | Dimension | Seller profile — seller_id, seller_name, city, state. |
| `dim_product` | Dimension | Product specs — category (English), weight_g, dimensions. |
| `dim_geolocation` | Dimension | Geographic data — lat, lng, city, state, zip_code. |
| `Date Dim` | Date Table | Created via DAX (CALENDARAUTO). Contains Date, Day Number, Day of Week, Is Weekend, Month Name. |
| `Dax Measures` | Measure Table | Empty table used to host all DAX measures — best practice for measure organization. |
| `Parameter` | Parameter Table | What-if parameter — used for dynamic Top N filtering on visuals. |

## Relationships

| From Table · Column | To Table · Column | Cardinality | Active |
|---|---|---|---|
| `fact_order_items[order_id]` | `dim_order[order_id]` | Many → One | ✓ Active |
| `fact_order_items[product_id]` | `dim_product[product_id]` | Many → One | ✓ Active |
| `fact_order_items[seller_id]` | `dim_sellers[seller_id]` | Many → One | ✓ Active |
| `dim_order[customer_id]` | `dim_customer[customer_id]` | Many → One | ✓ Active |
| `dim_customer[zip_code]` | `dim_geolocation[zip_code]` | Many → One | ✓ Active |
| `fact_payment[order_id]` | `dim_order[order_id]` | Many → One | ✓ Active |
| `fact_reviews[order_id]` | `dim_order[order_id]` | Many → One | ✓ Active |
| `Date Dim[Date]` | `fact_order_items[order_date]` | One → Many | ✓ Active (default) |
| `Date Dim[Date]` | `fact_order_items[order_delivered_timestamp]` | One → Many | ⚠ Inactive* |

\* Inactive relationship activated inside the **On-Time Delivery %** measure via `USERELATIONSHIP(Date Dim[Date], fact_order_items[order_delivered_timestamp])`.

> ⚠️ **Important:** The `Date Dim` table is marked as a **Date Table** in Power BI (right-click → Mark as date table). This is required for all time intelligence DAX functions (`DATESYTD`, `SAMEPERIODLASTYEAR`, `DATEADD`, etc.) to work correctly.
>
> The relationship between `Date Dim` and `fact_order_items[order_delivered_timestamp]` is **inactive by default** and is only activated inside the On-Time Delivery % measure using `USERELATIONSHIP()`.

## Date Dim — DAX Definition

```dax
Date Dim =
  ADDCOLUMNS(
    CALENDARAUTO(),
    "Day Number", DAY([Date]),
    "Day of Week", FORMAT([Date], "dddd"),
    "Is Weekend", IF(WEEKDAY([Date], 2) >= 6, TRUE(), FALSE()),
    "Month Name", FORMAT([Date], "MMM YYYY")
  )
```

---

## Data Transformations & Power Query

| Table | Transformation | Reason |
|---|---|---|
| fact_order_items | Merged olist_orders columns (order_status, customer_id, timestamps) into fact_order_items | Centralize all order-level data for calculated columns |
| fact_order_items | Renamed order_purchase_timestamp → order_date | Cleaner field name for Date Dim relationship |
| fact_order_items | Renamed order_delivered_customer_date → order_delivered_timestamp | Consistency in naming |
| fact_order_items | Renamed order_estimated_delivery_date → deadline_date | Clarity for delivery calculations |
| dim_product | Merged product_category_name_translation into products table | English category names for all visuals |
| dim_product | Renamed product_category_name_english → category | Shorter field name |
| dim_sellers | Added seller_name column (synthetic — sellers identified by state + id) | Required for seller table visual on Page 2 |
| dim_customer | Promoted headers, set data types (text/number) | Data integrity |
| All tables | Removed null rows in key columns (order_id, product_id) | Data quality |
| All tables | Set correct data types for timestamp columns → Date/Time | Required for DATEDIFF calculated columns |

---

## Calculated Columns

All calculated columns live in the `fact_order_items` table unless noted. They are computed row-by-row at data refresh time and stored in the model.

### Delay Days
Calculates the delay in days between actual delivery date and the promised estimated delivery date. Positive = late, Negative = early, Zero = exact.

```dax
Delay Days =
    IF(
        fact_order_items[order_status] = "delivered",
        DATEDIFF(
            fact_order_items[order_estimated_delivery_date],
            fact_order_items[order_delivered_timestamp],
            DAY
        )
    )
// Result: positive = late, negative = early, BLANK for non-delivered orders
// Avg when late: +10.1 days | Max: 189 days
```

### Delay Severity
Categorizes each order's delay into 4 severity buckets for use in charts and slicers.

```dax
Delay Severity =
    SWITCH(
        TRUE(),
        [Delay Days] <= 0, "On Time",
        [Delay Days] <= 3, "Low Delay",
        [Delay Days] <= 7, "Medium Delay",
        "Critical Delay"
    )
// Used in: bar chart on Page 2 — Avg Delay Duration by state
```

### Delivery Status

```dax
Delivery Status =
    IF(
        fact_order_items[Delay Days] > 0,
        "Delayed",
        "On Time"
    )
// Binary flag for filtering — used in KPI card for Delayed Orders
```

### Late Delivery Flag

```dax
Late Delivery Flag =
    IF(
        fact_order_items[Delay Days] > 3,
        1,
        0
    )
// Numeric flag (1/0) — threshold >3 days for 'meaningfully late'
// Used in: Delayed Orders measure, On-Time % measure
```

### Route
Creates a seller-to-customer route string by combining seller state and customer state. Used to identify the most delay-prone shipping routes.

```dax
Route =
    RELATED(dim_sellers[state])
    & " -> " &
    RELATED(dim_customer[state])
// Example: "SP -> BA" | "SP -> RJ" | "BA -> MA"
// Used in: Top Delay Route measure (Page 2 KPI card)
```

### Freight Ratio %

```dax
Freight Ratio % =
    DIVIDE(
        fact_order_items[freight_value],
        fact_order_items[Total_cost]
    )
// Row-level freight ratio: freight ÷ (price + freight)
// Note: Total_cost must exist as a column: price + freight_value
```

### delivery_days (lowercase)

```dax
delivery_days =
    DATEDIFF(
        fact_order_items[order_date],
        fact_order_items[order_delivered_timestamp],
        DAY
    )
// This measures TOTAL journey time (purchase → delivery)
// Different from Delay Days which measures vs estimated date
// Used in: Avg Delivery Time KPI (Page 2) = 12.43 days
```
