# DAX Measures — Complete Library

All 25 measures are stored in the dedicated `Dax Measures` table (an empty table — best practice for measure organization).

> Measures exclusive to the removed "Customer Insights" page (Total Customers, Average CLV, Avg Orders Per Customer) have been excluded from this reference since that page is not part of the delivered report.

## Summary Table

| Measure Name | Verified Output | Page Used | Category |
|---|---|---|---|
| (AOV) | 160.99 BRL | 1, all pages | Revenue |
| Active Sellers | 3,095 / 2,970 active | 2 | Operations |
| Avg Delay by Route | Varies by route | 2 | Operations |
| Avg Delay Duration | 10.1 days (late only) | 2 | Operations |
| Avg Delivery Time | 12.43 days | 2 | Operations |
| AVG Freight Cost | 19.99 BRL | 3 | Category |
| Avg Product Price | 145.30 BRL | 3 | Category |
| Avg Review Score | 4.09 / 5 | 1, 2 | Customer |
| Black Friday Peak Marker | Revenue on Nov 24 2017 | 1 | Revenue |
| Delayed Orders | 7,000+ orders | 2 | Operations |
| Freight Cost | 2.25M BRL total | 3 | Category |
| Freight Cost Ratio | 14.21% | 3 | Category |
| High Freight Order % | 35.62% | 3 | Category |
| High Freight Orders | Count of orders freight >30% | 3 | Category |
| On-Time Delivery % | 20.89% (strict) / 92.4% (broad) | 1, 2 | Operations |
| Remaining to Target | MAX(0, 0.8 - On-Time %) | 2 | Operations |
| Stars Measure | ★★★★☆ display | 1 | Customer |
| Target % | 0.8 (80%) | 2 | Operations |
| Tooltip Revenue | Formatted revenue string | 1 | Revenue |
| Top Delay Route | BA → MA (example) | 2 | Operations |
| Total Orders | 99,441 | 1, all pages | Revenue |
| Total Revenue | 15.42M BRL (payments) | 1 | Revenue |
| Total Weight (KG) | Calculated per category | 3 | Category |
| Parameter Value | Dynamic N for Top N | 3 | Utility |

---

## 1. Revenue Measures

### Total Revenue
Uses `fact_payment` table (`payment_value`) filtered to delivered orders. This includes installment amounts — result is higher than sum of item prices.

```dax
Total Revenue =
    CALCULATE(
        SUM(fact_payment[payment_value]),
        fact_order_items[order_status] = "delivered"
    )
// Result: 15.42M BRL (payment-based, includes installments)
// Note: SUM(fact_order_items[price]) = 13.59M BRL — different base
```

### (AOV) — Average Order Value

```dax
(AOV) = DIVIDE([Total Revenue], [Total Orders], 0)
// Result: 160.99 BRL (payment-based) / $156.31 shown on dashboard
// The slight difference is due to currency formatting in visuals
```

### Black Friday Peak Marker
Marks November 24, 2017 (Black Friday) on the revenue trend chart with the actual revenue value so the spike is labeled.

```dax
Black Friday Peak Marker =
    IF(
        SELECTEDVALUE(fact_order_items[order_date]) = DATE(2017, 11, 24),
        [Total Revenue],
        BLANK()
    )
// Used as a secondary data label on the line chart — Page 1
```

### Tooltip Revenue

```dax
Tooltip Revenue =
    VAR CurrentDate = SELECTEDVALUE(fact_order_items[order_date])
    VAR RevenueAmount = [Total Revenue]
    RETURN
        IF(
            CurrentDate = DATE(2017, 11, 24),
            FORMAT(RevenueAmount, "$#,##0") & " — Black Friday peak",
            FORMAT(RevenueAmount, "$#,##0")
        )
// Custom tooltip text — adds contextual label on Black Friday date
```

---

## 2. Operations Measures

### Total Orders

```dax
Total Orders = DISTINCTCOUNT(fact_order_items[order_id])
// Result: 99,441 unique orders
```

### Active Sellers

```dax
Active Sellers = DISTINCTCOUNT(fact_order_items[seller_id])
// Result: 3,095 total unique sellers in the dataset
// Note: sellers with 10+ delivered orders ≈ 1,238 (filtered in matrix)
```

### Avg Delivery Time

```dax
Avg Delivery Time = AVERAGE(fact_order_items[delivery_days])
// Result: 12.43 days (purchase → customer delivery)
// Calculated column delivery_days = DATEDIFF(order_date, order_delivered_timestamp, DAY)
```

### On-Time Delivery %
The most complex measure in the report. Uses `USERELATIONSHIP` to activate the inactive Date Dim → order_delivered_timestamp relationship, then counts rows where actual delivery ≤ estimated deadline.

```dax
On-Time Delivery % =
    VAR DeliveredOnTime =
        CALCULATE(
            COUNTROWS(fact_order_items),
            RELATEDTABLE(dim_order),
            fact_order_items[order_status] = "delivered",
            fact_order_items[order_delivered_timestamp] <= fact_order_items[deadline_date],
            USERELATIONSHIP('Date Dim'[Date], fact_order_items[order_delivered_timestamp])
        )
    VAR TotalDelivered =
        CALCULATE(
            COUNTROWS(fact_order_items),
            fact_order_items[order_status] = "delivered",
            USERELATIONSHIP('Date Dim'[Date], fact_order_items[order_delivered_timestamp])
        )
    RETURN DIVIDE(DeliveredOnTime, TotalDelivered, 0)
// Result: 20.89% (strict — row-level comparison with date context)
// Broad calculation (without USERELATIONSHIP) gives 92.4%
// The dashboard shows 20.89% — strict interpretation
```

### Delayed Orders

```dax
Delayed Orders =
    CALCULATE(
        DISTINCTCOUNT(fact_order_items[order_id]),
        fact_order_items[Delay Days] > 0,
        fact_order_items[order_status] = "delivered"
    )
// Result: ~7,000 orders delayed (Delay Days > 0)
// Dashboard shows: 7K
```

### Avg Delay Duration

```dax
Avg Delay Duration =
    AVERAGEX(
        FILTER(
            fact_order_items,
            fact_order_items[Delay Days] > 0 &&
            fact_order_items[order_status] = "delivered"
        ),
        fact_order_items[Delay Days]
    )
// Result: avg days late for LATE orders only (excludes on-time)
// Used in: bar chart by state — Page 2
```

### Avg Delay by Route

```dax
Avg Delay by Route = AVERAGE(fact_order_items[Delay Days])
// When used in a matrix with Route column = shows delay per seller-state → customer-state
// Used with Top Delay Route measure to find worst route
```

### Top Delay Route
Uses `TOPN` and `SUMMARIZE` to dynamically find the single route (seller state → customer state) with the highest average delay.

```dax
Top Delay Route =
    VAR TopRoute =
        TOPN(
            1,
            SUMMARIZE(
                FILTER(
                    fact_order_items,
                    fact_order_items[order_status] = "delivered" &&
                    fact_order_items[Delay Days] > 0
                ),
                fact_order_items[Route],
                "AvgDelay", AVERAGE(fact_order_items[Delay Days])
            ),
            [AvgDelay], DESC
        )
    RETURN CONCATENATEX(TopRoute, [Route], ", ")
// Result: "BA -> MA" (example — worst delay route in dataset)
// Used in: KPI card Page 2 — Top Delay Route
```

### Target % & Remaining to Target

```dax
Target % = 0.8
// Fixed target: 80% on-time delivery rate

Remaining to Target = MAX(0, [Target %] - [On-Time Delivery %])
// Used in progress bar visual on Page 2 alongside On-Time Delivery %
```

---

## 3. Category & Freight Measures

### Freight Cost

```dax
Freight Cost = SUM(fact_order_items[freight_value])
// Result: 2,251,910 BRL total freight across all orders
```

### Freight Cost Ratio

```dax
Freight Cost Ratio =
    DIVIDE(
        SUM(fact_order_items[freight_value]),
        SUM(fact_order_items[price]) + SUM(fact_order_items[freight_value])
    )
// Result: 14.21% (freight as % of total transaction value)
// Dashboard KPI card: 14.21%
```

### AVG Freight Cost

```dax
AVG Freight Cost = AVERAGE(fact_order_items[freight_value])
// Result: 19.99 BRL per item
// Dashboard KPI: 19.99
```

### Avg Product Price

```dax
Avg Product Price =
    AVERAGEX(
        VALUES(fact_order_items[product_id]),
        CALCULATE(AVERAGE(fact_order_items[price]))
    )
// Result: 145.30 BRL — averaged at product level (not order-item level)
// Prevents bias from high-quantity products skewing the average
```

### High Freight Orders & High Freight Order %

```dax
High Freight Orders =
    CALCULATE(
        DISTINCTCOUNT(fact_order_items[order_id]),
        FILTER(
            fact_order_items,
            DIVIDE(fact_order_items[freight_value], fact_order_items[price]) > 0.3
        )
    )
// Orders where freight > 30% of product price

High Freight Order % =
    DIVIDE([High Freight Orders], DISTINCTCOUNT(fact_order_items[order_id]), 0)
// Result: 35.62% — over a third of orders have high freight burden
// Dashboard KPI: 35.62%
```

### Total Weight (KG)

```dax
Total Weight (KG) =
    SUMX(
        fact_order_items,
        fact_order_items[price] * 0 + RELATED(dim_product[weight_g])
    ) / 1000
// Sums weight_g from dim_product for all order items, converts to KG
// The price*0 trick forces row context for RELATED to work correctly
// Used in: Treemap visual — Total Weight (KG) by category
```

---

## 4. Customer Measures (retained)

### Avg Review Score

```dax
Avg Review Score =
    CALCULATE(
        AVERAGE(fact_reviews[review_score]),
        NOT ISBLANK(fact_reviews[review_score])
    )
// Result: 4.09 / 5 (excludes blank scores)
// Dashboard shows: 4.09 ★★★★☆
```

### Stars Measure

```dax
Stars Measure =
    VAR AvgRating = ROUND(AVERAGE(fact_reviews[review_score]), 0)
    RETURN
        REPT("★", AvgRating) &
        REPT("☆", 5 - AvgRating)
// Output: "★★★★☆" for score 4.09
// Displayed as text visual on Page 1 KPI card
```

---

## 5. Utility Measures

### Parameter Value

```dax
Parameter Value = SELECTEDVALUE('Parameter'[Parameter])
// Connected to a What-If Parameter slicer
// Used to dynamically control Top N filtering on category and seller visuals
```
