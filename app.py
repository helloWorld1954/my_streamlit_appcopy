import streamlit as st
import polars as pl
import pandas as pd
import numpy as np
import duckdb
from pydantic import BaseModel, ValidationError
from datetime import datetime
import logging
import requests
import io

st.set_page_config(
    page_title='NYC Taxi Dashboard',
    page_icon='🚕',
    layout='wide',
    initial_sidebar_state='expanded'
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  CACHED DATA LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Downloading trip data…")
def load_validate_Tripdata():

    # -------- Download file --------
    try:
        response = requests.get(
            "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logging.warning(err)
        st.error("Failed to download dataset")
        return pd.DataFrame()

    # -------- Validation model --------
    class TripTable(BaseModel):
        tpep_pickup_datetime: datetime
        tpep_dropoff_datetime: datetime
        passenger_count: int
        trip_distance: float
        fare_amount: float
        tip_amount: float
        total_amount: float
        payment_type: int

    # -------- Read parquet from memory --------
    TripTable_df = pl.read_parquet(io.BytesIO(response.content)).select([
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "PULocationID",
        "DOLocationID",
        "passenger_count",
        "trip_distance",
        "fare_amount",
        "tip_amount",
        "total_amount",
        "payment_type"
    ])

    # -------- Validate first row --------
    try:
        TripTable.model_validate(
            TripTable_df.row(0, named=True),
            strict=True
        )
    except ValidationError as exc:
        logging.warning(exc)

    return TripTable_df


@st.cache_data(show_spinner="Downloading taxi zone lookup…")
def load_validate_TaxiZones():

    try:
        response = requests.get(
            "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logging.warning(err)
        st.error("Failed to download taxi zones")
        return pl.DataFrame()

    class TaxiZone(BaseModel):
        LocationID: int
        Borough: str
        Zone: str
        service_zone: str

    TaxiZone_df = pl.read_csv(response.content)

    for row in TaxiZone_df.to_dicts():
        try:
            TaxiZone.model_validate(row, strict=True)
        except ValidationError as exc:
            logging.warning(exc)

    return TaxiZone_df


# ═══════════════════════════════════════════════════════════════════════════════
#  LOAD RAW DATA
# ═══════════════════════════════════════════════════════════════════════════════

TripTable_df = load_validate_Tripdata()
TaxiZone_df = load_validate_TaxiZones()

# ═══════════════════════════════════════════════════════════════════════════════
#  CLEANING & FILTERING  (from notebook)
# ═══════════════════════════════════════════════════════════════════════════════

raw_count = TripTable_df.height

# Drop nulls
clean_df = TripTable_df.drop_nulls(
    subset=["tpep_pickup_datetime", "tpep_dropoff_datetime",
            "PULocationID", "DOLocationID", "fare_amount"]
)
nulls_removed = raw_count - clean_df.height

# Positive distance only
filtered = clean_df.filter(pl.col("trip_distance") > 0)
dist_removed = clean_df.height - filtered.height

# Pickup must be before dropoff
prev = filtered.height
filtered = filtered.filter(
    pl.col("tpep_pickup_datetime") < pl.col("tpep_dropoff_datetime")
)
time_removed = prev - filtered.height

# Fare between 0 and 500
prev = filtered.height
filtered = filtered.filter(
    (pl.col("fare_amount") > 0) & (pl.col("fare_amount") <= 500)
)
fare_removed = prev - filtered.height

# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE ENGINEERING  (from notebook)
# ═══════════════════════════════════════════════════════════════════════════════

filtered = filtered.with_columns(
    ((pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime"))
     .dt.total_seconds() / 60).alias("trip_duration_min"),
    pl.col("tpep_pickup_datetime").dt.date().alias("pickup_date"),
)

filtered = filtered.with_columns(
    (pl.col("trip_distance") / (pl.col("trip_duration_min") / 60))
    .alias("trip_speed_mph"),
    pl.col("tpep_pickup_datetime").dt.hour().alias("pickup_hour"),
    pl.col("tpep_pickup_datetime").dt.strftime("%A").alias("pickup_date_of_week"),
)

# Convert to Pandas for the metrics section
df = filtered.to_pandas()

# ═══════════════════════════════════════════════════════════════════════════════
#  DUCKDB SUMMARY QUERIES  (from notebook)
# ═══════════════════════════════════════════════════════════════════════════════

con = duckdb.connect()
con.register("filteredTripTable", filtered)
con.register("TaxiZone_df", TaxiZone_df)

# Q1 — Top 10 pickup zones
q1 = con.sql("""
    SELECT PULocationID AS LocationID,
           SUM(PULocationID) AS NUMOFPICKUPS,
           TaxiZone_df.Zone AS "Pick-up Zone Name"
    FROM filteredTripTable
    JOIN TaxiZone_df ON filteredTripTable.PULocationID = TaxiZone_df.LocationID
    GROUP BY PULocationID, TaxiZone_df.Zone
    ORDER BY NUMOFPICKUPS DESC
    LIMIT 10
""").pl()

# Q2 — Average fare by hour
q2 = con.sql("""
    SELECT pickup_hour, AVG(fare_amount) AS AVERAGEFAREAMOUNT
    FROM filteredTripTable
    GROUP BY pickup_hour
    ORDER BY AVERAGEFAREAMOUNT DESC
""").pl()

# Q3 — Payment type distribution
q3 = con.sql("""
    SELECT payment_type,
           COUNT(payment_type) AS NUMOFPAYMENTS,
           NUMOFPAYMENTS * 100.0 / (SELECT COUNT(*) FROM filteredTripTable) AS PERCENTAGE
    FROM filteredTripTable
    GROUP BY payment_type
""").pl()

# Q4 — Tip/fare ratio by day (credit card only)
q4 = con.sql("""
    SELECT pickup_date_of_week,
           AVG(tip_amount / fare_amount) * 100 AS "RATIO TIP/FARE"
    FROM filteredTripTable
    WHERE payment_type = 1
    GROUP BY pickup_date_of_week
""").pl()

# Q5 — Top 5 pickup-dropoff pairs
q5 = con.sql("""
    WITH grouped_trips AS (
        SELECT PULocationID, DOLocationID, COUNT(*) AS NumOfOccurrences
        FROM filteredTripTable
        GROUP BY PULocationID, DOLocationID
    )
    SELECT g.PULocationID, g.DOLocationID, g.NumOfOccurrences,
           pu.Zone AS "Pick Up Zone",
           do_zone.Zone AS "Drop Off Zone"
    FROM grouped_trips g
    LEFT JOIN TaxiZone_df pu ON g.PULocationID = pu.LocationID
    LEFT JOIN TaxiZone_df do_zone ON g.DOLocationID = do_zone.LocationID
    ORDER BY g.NumOfOccurrences DESC
    LIMIT 5
""").pl()

# Q6 — Trip distance distribution
q6 = con.sql("""
    SELECT CAST(FLOOR(trip_distance) AS INTEGER) AS dist_bin,
           COUNT(*) AS trips
    FROM filteredTripTable
    WHERE trip_distance > 0 AND trip_distance <= 50
    GROUP BY dist_bin
    ORDER BY dist_bin
""").pl()

# Q7 — Heatmap: trips by day × hour
q7 = con.sql("""
    SELECT pickup_date_of_week, pickup_hour, COUNT(*) AS num_trips
    FROM filteredTripTable
    GROUP BY pickup_date_of_week, pickup_hour
""").pl()

con.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  STORE IN SESSION STATE FOR DASHBOARD PAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.session_state["filtered_df"] = filtered
st.session_state["TaxiZone_df"] = TaxiZone_df
st.session_state["q1"] = q1
st.session_state["q2"] = q2
st.session_state["q3"] = q3
st.session_state["q4"] = q4
st.session_state["q5"] = q5
st.session_state["q6"] = q6
st.session_state["q7"] = q7

# Also store the summary metrics so Dashboard can reuse them
st.session_state["metrics"] = {
    "total_trips": len(df),
    "avg_fare": df["fare_amount"].mean(),
    "total_revenue": df["fare_amount"].sum(),
    "avg_distance": df["trip_distance"].mean(),
    "avg_duration": df["trip_duration_min"].mean(),
}

# ═══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="main-header">NYC Taxi Trip Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Exploring Yellow Taxi Data from January 2024</p>', unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  KEY METRICS
# ═══════════════════════════════════════════════════════════════════════════════

st.subheader('Key Metrics at a Glance')

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="Total Trips",
        value=f"{len(df):,}"
    )

with col2:
    avg_fare = df['fare_amount'].mean()
    st.metric(
        label="Average Fare",
        value=f"${avg_fare:.2f}"
    )

with col3:
    Total_Revenue = df['fare_amount'].sum()
    st.metric(
        label="Total Revenue",
        value=f"${Total_Revenue:,.2f}"
    )

with col4:
    avg_distance = df['trip_distance'].mean()
    st.metric(
        label="Avg Distance",
        value=f"{avg_distance:.2f} mi"
    )

with col5:
    avg_duration = df['trip_duration_min'].mean()
    st.metric(
        label="Avg Duration",
        value=f"{avg_duration:.1f} min"
    )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  DATA COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════

st.subheader('Data Coverage')

col1, col2 = st.columns(2)

with col1:
    min_date = df['pickup_date'].min()
    max_date = df['pickup_date'].max()
    st.info(f"**Date Range:** {min_date} to {max_date}")

with col2:
    payment_map = {1: 'Credit Card', 2: 'Cash', 3: 'No Charge', 4: 'Dispute'}
    top_payment = df['payment_type'].map(payment_map).value_counts().idxmax()
    st.info(f"**Most Common Payment:** {top_payment}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  CLEANING SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

st.subheader('Data Cleaning Summary')

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Raw Records", f"{raw_count:,}")
c2.metric("Nulls Removed", f"{nulls_removed:,}")
c3.metric("Zero/Neg Distance", f"{dist_removed:,}")
c4.metric("Bad Pickup Time", f"{time_removed:,}")
c5.metric("Out-of-Range Fare", f"{fare_removed:,}")

st.success(f"**{filtered.height:,}** clean records ready for analysis")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  QUERY RESULTS (tabs)
# ═══════════════════════════════════════════════════════════════════════════════

st.subheader('Summary Query Results')

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Top Pickup Zones", "Avg Fare by Hour", "Payment Types",
    "Tip/Fare Ratio", "Top Routes"
])

with tab1:
    st.dataframe(q1.to_pandas(), use_container_width=True)
with tab2:
    st.dataframe(q2.to_pandas(), use_container_width=True)
with tab3:
    st.dataframe(q3.to_pandas(), use_container_width=True)
with tab4:
    st.dataframe(q4.to_pandas(), use_container_width=True)
with tab5:
    st.dataframe(q5.to_pandas(), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  ABOUT / SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader('About This Dashboard')

st.markdown("""
This dashboard lets you explore NYC Yellow Taxi trip data.
Use the **sidebar** to navigate between pages.
""")

st.sidebar.success("Pick a page above to explore!")
st.sidebar.markdown("---")
st.sidebar.markdown("**Dataset:** NYC Yellow Taxi (Jan 2024)")
st.sidebar.markdown(f"**Sample Size:** {len(df):,} trips")
