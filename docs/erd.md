# Data model

## Bus matrix

Which dimensions each fact joins to directly.

|Fact|date|product|supplier|dc|customer|carrier|
|-|-|-|-|-|-|-|
|fct\_order\_lines|Yes|Yes||Yes|Yes||
|fct\_shipments|Yes|||||Yes|
|fct\_inventory\_movements|Yes|Yes||Yes|||
|fct\_inventory\_daily|Yes|Yes||Yes|||
|fct\_po\_lines|Yes|Yes|Yes|Yes|||
|fct\_invoice\_match|Yes||Yes||||



## Entity relationship diagram

Facts point at dimensions. SCD2 dimensions (product, supplier) have one row per version, and facts store the key of the version that was valid on the fact's date.

```mermaid
erDiagram
    DIM\_DATE ||--o{ FCT\_ORDER\_LINES : "order\_date"
    DIM\_PRODUCT ||--o{ FCT\_ORDER\_LINES : "product\_key"
    DIM\_DC ||--o{ FCT\_ORDER\_LINES : "dc\_id"
    DIM\_CUSTOMER ||--o{ FCT\_ORDER\_LINES : "customer\_id"
    FCT\_ORDER\_LINES ||--o{ FCT\_SHIPMENTS : "order\_line\_id"
    DIM\_CARRIER ||--o{ FCT\_SHIPMENTS : "carrier\_id"
    DIM\_PRODUCT ||--o{ FCT\_INVENTORY\_MOVEMENTS : "product\_key"
    DIM\_DC ||--o{ FCT\_INVENTORY\_MOVEMENTS : "dc\_id"
    DIM\_PRODUCT ||--o{ FCT\_INVENTORY\_DAILY : "product\_key"
    DIM\_DC ||--o{ FCT\_INVENTORY\_DAILY : "dc\_id"
    DIM\_DATE ||--o{ FCT\_INVENTORY\_DAILY : "snapshot\_date"
    DIM\_SUPPLIER ||--o{ FCT\_PO\_LINES : "supplier\_key"
    DIM\_PRODUCT ||--o{ FCT\_PO\_LINES : "product\_key"
    DIM\_DC ||--o{ FCT\_PO\_LINES : "dc\_id"
    FCT\_PO\_LINES ||--o{ FCT\_INVOICE\_MATCH : "po\_line\_id"
    DIM\_SUPPLIER ||--o{ FCT\_INVOICE\_MATCH : "supplier\_key"
    DIM\_DATE ||--o{ FCT\_SHIPMENTS : "ship\_date"
    DIM\_DATE ||--o{ FCT\_INVENTORY\_MOVEMENTS : "event\_date"
    DIM\_DATE ||--o{ FCT\_PO\_LINES : "po\_date"
    DIM\_DATE ||--o{ FCT\_INVOICE\_MATCH : "invoice\_date"

    FCT\_ORDER\_LINES {
        int order\_line\_id PK
        int order\_id
        date order\_date FK
        date promised\_date
        int product\_key FK
        int dc\_id FK
        int customer\_id FK
        int qty\_ordered
        string line\_status
        boolean is\_otif
    }
    FCT\_SHIPMENTS {
        string shipment\_id PK
        int order\_line\_id FK
        int carrier\_id FK
        date ship\_date FK
        date committed\_date
        timestamp delivered\_at
        int qty\_shipped
    }
    FCT\_INVENTORY\_MOVEMENTS {
        string event\_id PK
        timestamp event\_ts\_utc
        date event\_date FK
        string event\_type
        int product\_key FK
        int dc\_id FK
        int qty\_eaches
    }
    FCT\_INVENTORY\_DAILY {
        int sku\_id PK
        int dc\_id PK, FK
        date snapshot\_date PK, FK
        int product\_key FK
        int on\_hand\_eaches
    }
    FCT\_PO\_LINES {
        int po\_line\_id PK
        string po\_number
        int supplier\_key FK
        int product\_key FK
        int dc\_id FK
        date po\_date FK
        date promised\_date
        timestamp received\_at
        int qty\_ordered
        int qty\_received
        number unit\_cost
    }
    FCT\_INVOICE\_MATCH {
        string invoice\_number PK
        int line\_no PK
        int po\_line\_id FK
        int supplier\_key FK
        date invoice\_date FK
        int billed\_qty
        number billed\_unit\_cost
        string match\_status
    }
    DIM\_PRODUCT {
        int product\_key PK "one row per version (SCD2)"
        int sku\_id
        string sku\_code
        string category
        number unit\_cost
        date valid\_from
        date valid\_to
        boolean is\_current
    }
    DIM\_SUPPLIER {
        int supplier\_key PK "one row per version (SCD2)"
        int supplier\_id
        string supplier\_code
        string tier
        int promised\_lead\_time\_days
        date valid\_from
        date valid\_to
    }
    DIM\_DC {
        int dc\_id PK
        string dc\_code
        string timezone
    }
    DIM\_CUSTOMER {
        int customer\_id PK
        string customer\_type
        int home\_dc\_id
        date created\_at
    }
    DIM\_CARRIER {
        int carrier\_id PK
        string carrier\_code
        string mode
    }
    DIM\_DATE {
        date date\_day PK
        int week\_of\_year
        boolean is\_holiday
        boolean is\_promo\_week
    }
```

