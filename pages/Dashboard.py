import streamlit as st
import polars as pl
import altair as alt

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("NYC Yellow Taxi — Dashboard")

# ── Guard: make sure data exists ─────────────────────────────────────────────

required_keys = ["q1", "q2", "q3", "q6", "q7"]
if not all(k in st.session_state for k in required_keys):
    st.warning("No data found. Please run the **main page** first to load and clean the data.")
    st.stop()

# ── Retrieve query results from session_state ────────────────────────────────

q1 = st.session_state["q1"]   # Top pickup zones
q2 = st.session_state["q2"]   # Avg fare by hour
q3 = st.session_state["q3"]   # Payment type dist
q6 = st.session_state["q6"]   # Distance distribution
q7 = st.session_state["q7"]   # Heatmap data

# ── Chart 1: Top 10 Pick-up Zones ────────────────────────────────────────────

st.subheader("Top 10 Pick-up Zones by Pickups")

df1 = q1.rename({c: c.strip() for c in q1.columns}).rename(
    {"Pick-up Zone Name": "pickup_zone"}
).with_columns(
    pl.col("NUMOFPICKUPS").cast(pl.Int64),
    pl.col("pickup_zone").cast(pl.Utf8),
)

chart1 = alt.Chart(df1).mark_bar().encode(
    x=alt.X("pickup_zone:N", sort="-y", title="Pick-up Zone"),
    y=alt.Y("NUMOFPICKUPS:Q", title="Number of Pickups"),
    tooltip=["LocationID:Q", "pickup_zone:N", "NUMOFPICKUPS:Q"],
).properties(height=400)

st.altair_chart(chart1, use_container_width=True)

# ── Chart 2: Average Fare by Hour ────────────────────────────────────────────

st.subheader("Average Fare Amount by Pickup Hour")

df2 = q2.rename({c: c.strip() for c in q2.columns}).with_columns(
    pl.col("pickup_hour").cast(pl.Int64),
    pl.col("AVERAGEFAREAMOUNT").cast(pl.Float64),
).sort("pickup_hour")

chart2 = alt.Chart(df2).mark_line(point=True).encode(
    x=alt.X("pickup_hour:Q", title="Pickup Hour (0–23)"),
    y=alt.Y("AVERAGEFAREAMOUNT:Q", title="Average Fare Amount"),
    tooltip=["pickup_hour:Q", "AVERAGEFAREAMOUNT:Q"],
).properties(height=400)

st.altair_chart(chart2, use_container_width=True)

# ── Charts 3 & 4 side by side ────────────────────────────────────────────────

col_left, col_right = st.columns(2)

# Chart 3: Trip Distance Distribution
with col_left:
    st.subheader("Trip Distance Distribution (0–50 mi)")

    df_dist = q6.with_columns(
        pl.col("trips").cast(pl.Int64),
        pl.col("dist_bin").cast(pl.Int64),
    )

    chart3 = alt.Chart(df_dist).mark_bar().encode(
        x=alt.X("dist_bin:Q", title="Trip distance (miles, 1-mile bins)"),
        y=alt.Y("trips:Q", title="Number of trips"),
        tooltip=["dist_bin:Q", "trips:Q"],
    ).properties(height=350)

    st.altair_chart(chart3, use_container_width=True)

# Chart 4: Payment Type Distribution
with col_right:
    st.subheader("Payment Type Distribution")

    mapping = {
        1: "Credit card", 2: "Cash", 3: "No charge",
        4: "Dispute", 5: "Unknown", 6: "Voided",
    }

    df3 = q3.with_columns(
        pl.col("NUMOFPAYMENTS").cast(pl.Int64),
        pl.col("PERCENTAGE").cast(pl.Float64),
    ).with_columns(
        pl.col("payment_type")
          .cast(pl.Int64)
          .map_elements(lambda x: mapping.get(x, f"Other ({x})"), return_dtype=pl.Utf8)
          .alias("payment_name")
    )

    chart4 = alt.Chart(df3).mark_bar().encode(
        x=alt.X("payment_name:N", title="Payment Type"),
        y=alt.Y("NUMOFPAYMENTS:Q", title="Number of Payments"),
        tooltip=[
            "payment_name:N", "NUMOFPAYMENTS:Q",
            alt.Tooltip("PERCENTAGE:Q", format=".2f"),
        ],
    ).properties(height=350)

    st.altair_chart(chart4, use_container_width=True)

# ── Chart 5: Heatmap — Trips by Day × Hour ──────────────────────────────────

st.subheader("Trips by Day of Week and Hour")

df7 = q7.with_columns(
    pl.col("pickup_hour").cast(pl.Int64),
    pl.col("num_trips").cast(pl.Int64),
    pl.col("pickup_date_of_week").cast(pl.Utf8),
)

day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]

heatmap = alt.Chart(df7).mark_rect().encode(
    x=alt.X("pickup_hour:O", title="Hour of Day"),
    y=alt.Y("pickup_date_of_week:N", sort=day_order, title="Day of Week"),
    color=alt.Color("num_trips:Q", title="Trips"),
    tooltip=[
        alt.Tooltip("pickup_date_of_week:N", title="Day"),
        alt.Tooltip("pickup_hour:Q", title="Hour"),
        alt.Tooltip("num_trips:Q", title="Trips"),
    ],
).properties(height=400)

st.altair_chart(heatmap, use_container_width=True)
