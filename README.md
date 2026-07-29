# NYC Yellow Taxi Data Pipeline — Azure Medallion Architecture

An end-to-end batch data engineering pipeline built on Azure, ingesting NYC TLC
yellow taxi trip data, cleaning and enriching it, and producing business-ready
aggregate tables for analysis.

## Architecture

```
NYC TLC Open Data (HTTPS Parquet)
        │
        ▼
  Azure Data Factory  ──▶  Bronze (raw, as-is)
        │                       │
        │                       ▼
        │                 Azure Databricks (PySpark)
        │                       │
        │                       ▼
        │                  Silver (cleaned, deduplicated, zone-enriched)
        │                       │
        │                       ▼
        │                  Gold (aggregated, business-ready)
        │                       │
        │                       ▼
        └──────────────▶  Visualization (matplotlib / Power BI)
```

**Medallion layers:**
- **Bronze** — raw monthly Parquet files landed exactly as published by NYC TLC, plus a taxi zone lookup reference table
- **Silver** — cleaned data: invalid fares/distances/passenger counts removed, duplicates dropped, pickup/dropoff location IDs joined against the zone lookup table to produce human-readable borough and zone names
- **Gold** — three aggregate tables answering specific business questions (see below)

## Tech stack

| Component | Purpose |
|---|---|
| Azure Data Lake Storage Gen2 | Data lake storage (bronze/silver/gold containers) |
| Azure Data Factory | Scheduled, parameterized ingestion pipeline |
| Azure Databricks (PySpark) | Data cleaning, transformation, aggregation |
| Bicep | Infrastructure as code for the storage layer |
| Python (matplotlib) | Data visualization |

## Dataset

[NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) —
Yellow Taxi trips, January–April 2024 (~13M raw rows), published monthly by
the NYC Taxi & Limousine Commission as public Parquet files.

## Data pipeline details

### Ingestion (Bronze)
An Azure Data Factory pipeline (`pl_copy_yellow_taxi`) is parameterized on a
`p_month` value, pulling one month's Parquet file directly from TLC's public
CloudFront endpoint into the `bronze` container, partitioned by year/month.
A `ForEach` + `Execute Pipeline` wrapper (`pl_backfill_yellow_taxi`) backfills
multiple months in one run.

### Transformation (Silver)
PySpark logic filters out records with:
- Non-positive fare, total amount, or trip distance
- Passenger counts of 0 or greater than 6
- Dropoff timestamp at or before pickup timestamp
- Exact duplicate rows

~12.3% of raw records (1.6M of 13.07M rows) were filtered as data quality
issues. Remaining trips are joined twice against the zone lookup table — once
for pickup location, once for dropoff — to attach borough and zone names.

### Aggregation (Gold)
Three tables, each answering a specific analytical question:

| Table | Question answered |
|---|---|
| `revenue_by_borough` | Which pickup boroughs generate the most revenue, and what's the average fare? |
| `trip_volume_by_time` | When is rider demand highest, by day of week and hour? |
| `tip_by_payment` | How does tipping behavior differ by payment method? |

## Key insights

- **Manhattan dominates trip volume** (10.3M of ~11.5M cleaned trips) but
  **Queens has the highest average fare** (~$73 vs Manhattan's ~$23) —
  consistent with airport-trip pricing (JFK/LaGuardia are in Queens).
- **Demand peaks on weekday evenings** (5–7pm, Tue–Thu heaviest) with a
  secondary spike in **weekend late-night hours** (Fri/Sat/Sun, 12–2am),
  consistent with nightlife-driven demand.
- **Credit card tips average 25.4%**, while **cash tips show as 0%** — not
  because cash riders don't tip, but because cash tips aren't captured in
  the TLC dataset (drivers don't report them digitally). Worth noting as a
  known data limitation, not a modeling error.

## Known data limitations
- ~0.3% of trips have `Unknown` or missing pickup/dropoff zone IDs, likely
  edge-of-service-area location codes not present in the zone lookup table.
- Cash tip amounts are not reliably captured in the source data (a documented
  TLC data characteristic), so tip-percentage analysis is only meaningful
  for credit card payments.

## Infrastructure as code
The storage layer (`main.bicep`) is deployed via Bicep for reproducibility.
See `DEPLOY.md` for deployment steps. Data Factory and Databricks resources
were provisioned via the Azure Portal for this iteration; a future
improvement would extend the Bicep template to cover these as well.

## Challenges solved
This project was built on an Azure for Students subscription, which comes
with restrictive regional VM quotas. Several common Databricks-compatible VM
families (Dsv2, Dv3, DC-series, Eadsv7) returned zero available quota in the
East US region. The fix: redeploying the Databricks workspace in **East US 2**,
which exposed a usable general-purpose VM catalog, combined with using
**Serverless notebook compute** where possible to sidestep cluster
provisioning entirely for lightweight interactive work.

## Repository structure
```
├── README.md                  # this file
├── infra/
│   ├── main.bicep              # storage account + container IaC
│   └── DEPLOY.md                # deployment instructions
├── notebooks/
│   └── bronze_to_gold.py        # PySpark transformation logic (Bronze → Silver → Gold)
└── visuals/
    ├── revenue_by_borough.png
    ├── trip_volume_heatmap.png
    └── tip_by_payment.png
```

## Possible next steps
- Add a scheduled trigger to Data Factory for ongoing monthly ingestion
- Extend IaC to cover Data Factory and Databricks resources
- Add data quality checks as a distinct validation step (e.g. Great Expectations)
- Connect a proper BI tool (Power BI / Synapse Serverless SQL) for interactive dashboards
