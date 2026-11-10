# Data model

## Bus matrix

Which dimensions each fact joins to directly.

|Fact|date|product|supplier|dc|customer|carrier|
|-|-|-|-|-|-|-|
|fct_order_lines|Yes|Yes||Yes|Yes||
|fct_shipments|Yes|||||Yes|
|fct_inventory_movements|Yes|Yes||Yes|||
|fct_inventory_daily|Yes|Yes||Yes|||
|fct_po_lines|Yes|Yes|Yes|Yes|||
|fct_invoice_match|Yes||Yes||||



## Entity relationship diagram

Facts point at dimensions. SCD2 dimensions (product, supplier) have one row per version, and facts store the key of the version that was valid on the fact's date.

```mermaid
erDiagram
    DIM_DATE ||--o{ FCT_ORDER_LINES : "order_date"
    DIM_PRODUCT ||--o{ FCT_ORDER_LINES : "product_key"
    DIM_DC ||--o{ FCT_ORDER_LINES : "dc_id"
    DIM_CUSTOMER ||--o{ FCT_ORDER_LINES : "customer_id"
    FCT_ORDER_LINES ||--o{ FCT_SHIPMENTS : "order_line_id"
    DIM_CARRIER ||--o{ FCT_SHIPMENTS : "carrier_id"
    DIM_PRODUCT ||--o{ FCT_INVENTORY_MOVEMENTS : "product_key"
    DIM_DC ||--o{ FCT_INVENTORY_MOVEMENTS : "dc_id"
    DIM_PRODUCT ||--o{ FCT_INVENTORY_DAILY : "product_key"
    DIM_DC ||--o{ FCT_INVENTORY_DAILY : "dc_id"
    DIM_DATE ||--o{ FCT_INVENTORY_DAILY : "snapshot_date"
    DIM_SUPPLIER ||--o{ FCT_PO_LINES : "supplier_key"
    DIM_PRODUCT ||--o{ FCT_PO_LINES : "product_key"
    DIM_DC ||--o{ FCT_PO_LINES : "dc_id"
    FCT_PO_LINES ||--o{ FCT_INVOICE_MATCH : "po_line_id"
    DIM_SUPPLIER ||--o{ FCT_INVOICE_MATCH : "supplier_key"
    DIM_DATE ||--o{ FCT_SHIPMENTS : "ship_date"
    DIM_DATE ||--o{ FCT_INVENTORY_MOVEMENTS : "event_date"
    DIM_DATE ||--o{ FCT_PO_LINES : "po_date"
    DIM_DATE ||--o{ FCT_INVOICE_MATCH : "invoice_date"

    FCT_ORDER_LINES {
        int order_line_id PK
        int order_id
        date order_date FK
        date promised_date
        int product_key FK
        int dc_id FK
        int customer_id FK
        int qty_ordered
        string line_status
        boolean is_otif
    }
    FCT_SHIPMENTS {
        string shipment_id PK
        int order_line_id FK
        int carrier_id FK
        date ship_date FK
        date committed_date
        timestamp delivered_at
        int qty_shipped
    }
    FCT_INVENTORY_MOVEMENTS {
        string event_id PK
        timestamp event_ts_utc
        date event_date FK
        string event_type
        int product_key FK
        int dc_id FK
        int qty_eaches
    }
    FCT_INVENTORY_DAILY {
        int sku_id PK
        int dc_id PK, FK
        date snapshot_date PK, FK
        int product_key FK
        int on_hand_eaches
    }
    FCT_PO_LINES {
        int po_line_id PK
        string po_number
        int supplier_key FK
        int product_key FK
        int dc_id FK
        date po_date FK
        date promised_date
        timestamp received_at
        int qty_ordered
        int qty_received
        number unit_cost
    }
    FCT_INVOICE_MATCH {
        string invoice_number PK
        int line_no PK
        int po_line_id FK
        int supplier_key FK
        date invoice_date FK
        int billed_qty
        number billed_unit_cost
        string match_status
    }
    DIM_PRODUCT {
        int product_key PK "one row per version (SCD2)"
        int sku_id
        string sku_code
        string category
        number unit_cost
        date valid_from
        date valid_to
        boolean is_current
    }
    DIM_SUPPLIER {
        int supplier_key PK "one row per version (SCD2)"
        int supplier_id
        string supplier_code
        string tier
        int promised_lead_time_days
        date valid_from
        date valid_to
    }
    DIM_DC {
        int dc_id PK
        string dc_code
        string timezone
    }
    DIM_CUSTOMER {
        int customer_id PK
        string customer_type
        int home_dc_id
        date created_at
    }
    DIM_CARRIER {
        int carrier_id PK
        string carrier_code
        string mode
    }
    DIM_DATE {
        date date_day PK
        int week_of_year
        boolean is_holiday
        boolean is_promo_week
    }
```

