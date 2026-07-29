# bronze_to_gold.py
#
# Databricks notebook logic for transforming NYC Yellow Taxi trip data
# from the Bronze layer through Silver (cleaned + enriched) to Gold
# (business-ready aggregates).
#
# Run in an Azure Databricks notebook attached to a cluster with access
# to the target ADLS Gen2 storage account.

from pyspark.sql.functions import col, hour, date_format, when, avg, sum as _sum, count, round as _round

# ---------------------------------------------------------------------------
# Storage configuration
# ---------------------------------------------------------------------------
storage_account_name = "nyctaxi1001"
storage_account_key = "<YOUR_STORAGE_ACCOUNT_KEY>"  # store in a secret scope in production

spark.conf.set(
    f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
    storage_account_key
)

bronze_base = f"abfss://bronze@{storage_account_name}.dfs.core.windows.net/"
silver_base = f"abfss://silver@{storage_account_name}.dfs.core.windows.net/"
gold_base = f"abfss://gold@{storage_account_name}.dfs.core.windows.net/"

# ---------------------------------------------------------------------------
# Bronze: read raw trip data + zone lookup
# ---------------------------------------------------------------------------
trips_df = spark.read.option("recursiveFileLookup", "true") \
    .parquet(f"{bronze_base}yellow_taxi/")
print(f"Raw row count: {trips_df.count()}")

zone_df = spark.read.parquet(f"{bronze_base}taxi_zone_lookup/")

# ---------------------------------------------------------------------------
# Silver: clean, deduplicate, and enrich with zone names
# ---------------------------------------------------------------------------
clean_df = trips_df.filter(
    (col("fare_amount") > 0) &
    (col("trip_distance") > 0) &
    (col("passenger_count") > 0) &
    (col("passenger_count") <= 6) &
    (col("tpep_pickup_datetime") < col("tpep_dropoff_datetime")) &
    (col("total_amount") > 0)
).dropDuplicates()

print(f"Rows before cleaning: {trips_df.count()}")
print(f"Rows after cleaning: {clean_df.count()}")

zone_df_pu = zone_df.select(
    col("LocationID").alias("PULocationID"),
    col("Borough").alias("PU_Borough"),
    col("Zone").alias("PU_Zone")
)
zone_df_do = zone_df.select(
    col("LocationID").alias("DOLocationID"),
    col("Borough").alias("DO_Borough"),
    col("Zone").alias("DO_Zone")
)

silver_df = clean_df \
    .join(zone_df_pu, on="PULocationID", how="left") \
    .join(zone_df_do, on="DOLocationID", how="left")

silver_df.write.mode("overwrite").parquet(f"{silver_base}yellow_taxi/")
print("Silver layer written successfully")

# ---------------------------------------------------------------------------
# Gold: business-ready aggregate tables
# ---------------------------------------------------------------------------

# 1. Revenue by pickup borough
revenue_by_borough = silver_df.groupBy("PU_Borough").agg(
    _round(_sum("total_amount"), 2).alias("total_revenue"),
    count("*").alias("trip_count"),
    _round(_sum("total_amount") / count("*"), 2).alias("avg_fare_per_trip")
).orderBy(_round(_sum("total_amount"), 2).desc())

# 2. Trip volume by day of week and hour
trip_volume_by_time = silver_df.withColumn(
    "pickup_hour", hour("tpep_pickup_datetime")
).withColumn(
    "day_of_week", date_format("tpep_pickup_datetime", "EEEE")
).groupBy("day_of_week", "pickup_hour").agg(
    count("*").alias("trip_count")
).orderBy("pickup_hour")

# 3. Average tip percentage by payment type
tip_by_payment = silver_df.withColumn(
    "payment_type_desc",
    when(col("payment_type") == 1, "Credit Card")
    .when(col("payment_type") == 2, "Cash")
    .when(col("payment_type") == 3, "No Charge")
    .when(col("payment_type") == 4, "Dispute")
    .otherwise("Other")
).withColumn(
    "tip_pct", (col("tip_amount") / col("fare_amount")) * 100
).groupBy("payment_type_desc").agg(
    count("*").alias("trip_count"),
    _round(avg("tip_pct"), 2).alias("avg_tip_pct")
).orderBy(col("trip_count").desc())

revenue_by_borough.write.mode("overwrite").parquet(f"{gold_base}revenue_by_borough/")
trip_volume_by_time.write.mode("overwrite").parquet(f"{gold_base}trip_volume_by_time/")
tip_by_payment.write.mode("overwrite").parquet(f"{gold_base}tip_by_payment/")

print("All Gold tables written successfully")
