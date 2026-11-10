# KPI definitions

Every KPI uses the same six parts. Decisions are mine; the reasons are next to them.

## 1. OTIF (line level)
- Definition: an order line is OTIF when every ordered unit is delivered on or before the promised date.
- Formula: OTIF % = OTIF lines / eligible lines
- Grain: one order line, reported by promised date (day or week)
- Decision: early delivery counts as on time, because customers don't penalize early arrival. Cancelled lines are excluded, since they were never meant to ship.
- Edge cases: a line split into two shipments is OTIF only if both arrive by the promised date. A late partial is a miss.
- Source: fct_order_lines (qty_ordered, promised_date, line_status), fct_shipments (delivered_at, qty_delivered)

## 2. OTIF (order level)
- Definition: an order is OTIF when every eligible line on it is OTIF.
- Formula: OTIF % = OTIF orders / eligible orders
- Grain: one order, reported by the latest promised date on the order (day or week)
- Decision: cancelled lines are excluded, so an order with one cancelled line can still be OTIF. Cancellations are tracked as their own KPI, so they aren't counted twice.
- Edge cases: an order where every line was cancelled has no eligible lines and is left out completely.
- Source: fct_order_lines (order_id, is_otif, line_status)

## 3. Unit fill rate
- Definition: the share of ordered units shipped on the first shipment.
- Formula: fill rate % = units shipped on first shipment / units ordered
- Grain: one order line, reported by order date (day or week)
- Decision: first shipment only (first-pass fill rate), because it shows whether stock was on hand when the order arrived, which is what stockouts hurt.
- Edge cases: a backorder that ships later doesn't count toward fill rate, even if it beats the promised date. OTIF already covers that.
- Source: fct_order_lines (qty_ordered), fct_shipments (qty_shipped, shipment_seq)

## 4. Supplier on-time receipt
- Definition: the share of PO lines a supplier delivered on or before the promised date.
- Formula: on-time % = PO lines received on or before promised date / PO lines received
- Grain: one PO line, reported by promised date (week or month), per supplier
- Decision: received means arrived at the dock, not put away, because the supplier controls arrival while putaway speed is our warehouse's job.
- Edge cases: a line cancelled then reinstated is judged against the promised date active when it arrived.
- Source: fct_po_lines (promised_date, received_at, line_status, supplier_key)

## 5. Supplier lead time
- Definition: the number of days from placing a PO line to receiving it.
- Formula: lead time = received date - PO date, in calendar days; reported as p50 and p90
- Grain: one PO line, reported by receipt month, per supplier
- Decision: calendar days, because inventory runs out on weekends too, and it matches promised_lead_time_days and the safety stock formula.
- Edge cases: a line received in partial deliveries uses the last receipt, when the line was complete.
- Source: fct_po_lines (po_date, received_at), dim_supplier (promised_lead_time_days)

## 6. Dock-to-stock time
- Definition: the hours goods wait between arriving at the dock and being put away on a shelf.
- Formula: dock-to-stock = putaway time - receipt time, in elapsed hours; reported as average and p90
- Grain: one received PO line, reported by receipt day, per DC
- Decision: elapsed clock hours, not working hours, because that's how long stock is unavailable to sell, and it's simpler to build.
- Edge cases: both timestamps are converted to UTC before subtracting, since WMS events carry local time with an offset.
- Source: fct_inventory_movements (event_type RECEIPT and PUTAWAY, event_ts_utc, dc_id)

## 7. Days of supply
- Definition: how many days current stock would last at the recent demand rate.
- Formula: days of supply = end-of-day on-hand / average daily units ordered over the trailing 28 days
- Grain: one SKU, DC and day
- Decision: demand is measured by orders, not shipments, because shipments undercount during stockouts.
- Edge cases: no demand in 28 days returns NULL with a "no recent demand" flag instead of dividing by zero.
- Source: fct_inventory_daily (on_hand_eaches), fct_order_lines (qty_ordered by day)

## 8. Stockout day
- Definition: a SKU-DC-day with no stock at end of day while there was demand.
- Formula: stockout day = end-of-day on-hand <= 0 AND units ordered that day > 0; stockout rate % = stockout days / SKU-DC-days with demand
- Grain: one SKU, DC and day
- Decision: end of day only, because it matches the daily snapshot table and doesn't need every movement replayed.
- Edge cases: negative on-hand is flagged as a data issue (such as a unit-of-measure error), not counted as a real stockout.
- Source: fct_inventory_daily (on_hand_eaches, snapshot_date), fct_order_lines (qty_ordered)

## 9. Carrier on-time delivery
- Definition: the share of shipments a carrier delivered on or before its committed date.
- Formula: on-time % = shipments delivered on or before committed date / delivered shipments
- Grain: one shipment, reported by committed date (week), per carrier and lane
- Decision: delivered means the first DELIVERED event that comes after a PICKED_UP event, so broken feeds with delivery before pickup can't count as on time.
- Edge cases: a shipment with an EXCEPTION and then a DELIVERED event counts, judged on its final delivery time.
- Source: fct_shipments (committed_date, delivered_at, carrier_id), tracking events

## 10. Three-way match rate
- Definition: the share of invoice lines where the billed quantity matches what was received and the billed price matches the PO price.
- Formula: match % = matching invoice lines / invoice lines; a line matches when billed_qty = qty_received AND |billed_unit_cost - PO unit cost| <= 1% of PO unit cost
- Grain: one invoice line, reported by invoice date (week or month), per supplier
- Decision: the right price is the unit cost valid on the PO date from the SCD2 product dimension, not today's cost; tolerance is 1%, which ignores rounding but catches real pricing errors.
- Edge cases: billing more units than were received is a mismatch even when the price is right.
- Source: fct_invoice_match (billed_qty, billed_unit_cost), fct_po_lines (qty_received, po_date, unit_cost), dim_product (unit_cost, valid_from, valid_to)

## 11. WAPE (forecast error)
- Definition: total forecast error as a share of what actually sold.
- Formula: WAPE % = sum of |forecast - actual| / sum of actual
- Grain: one SKU, DC and week, summed over the test period; also reported by ABC class
- Decision: measured weekly, the level planners order at, because daily error is mostly noise.
- Edge cases: weeks with zero sales are fine, since WAPE divides by the total, not each week's actual. That's why it's used instead of MAPE.
- Source: forecast output table (forecast_qty), fct_order_lines (qty_ordered summed by week)

## 12. Forecast bias
- Definition: whether the forecast runs high or low overall.
- Formula: bias % = sum of (forecast - actual) / sum of actual; positive means over-forecasting
- Grain: same as WAPE (SKU, DC and week)
- Decision: same level as WAPE so the two numbers line up, always shown with its sign.
- Edge cases: bias near 0% can hide large errors that cancel out, so it's always reported next to WAPE.
- Source: same as WAPE



## Table grains

| Table | One row per | Unique key |
| --- | --- | --- |
| fct_order_lines | sales order line | order_line_id |
| fct_shipments | shipment of an order line (a line shipped in 2 boxes has 2 rows) | shipment_id |
| fct_inventory_movements | warehouse event, after removing duplicates | event_id |
| fct_inventory_daily | SKU, DC and day | sku_id + dc_id + snapshot_date |
| fct_po_lines | purchase order line | po_line_id |
| fct_invoice_match | supplier invoice line | invoice_number + line_no |
| dim_product | version of a SKU (SCD2: a new row each time cost changes) | product_key |
| dim_supplier | version of a supplier (SCD2: a new row each time tier changes) | supplier_key |
| dim_dc | distribution center | dc_id |
| dim_customer | customer | customer_id |
| dim_carrier | carrier | carrier_id |
| dim_date | calendar day | date_day |