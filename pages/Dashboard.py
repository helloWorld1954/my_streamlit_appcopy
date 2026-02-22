import streamlit as st
import polars as pl
import altair as alt

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
#  CUSTOM CSS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* --- Interpretation callout box --- */
    .interp-box {
        background: linear-gradient(135deg, #EEF2F7 0%, #F7F9FC 100%);
        border-left: 5px solid #1E3A5F;
        padding: 18px 22px;
        margin: 8px 0 32px 0;
        border-radius: 0 10px 10px 0;
        font-size: 0.92rem;
        color: #1E3A5F;
        line-height: 1.65;
    }
    .interp-box .interp-label {
        font-weight: 800;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #0D2137;
        margin-bottom: 6px;
    }
    .interp-box .interp-sub {
        font-weight: 700;
        color: #2C5F8A;
        margin-top: 10px;
        margin-bottom: 2px;
        font-size: 0.88rem;
    }

    /* --- Chart section header --- */
    .chart-header {
        font-size: 1.35rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 2px;
        margin-top: 8px;
    }
    .chart-sub {
        font-size: 0.88rem;
        color: #777;
        margin-bottom: 10px;
    }

    /* --- Executive summary box --- */
    .exec-box {
        background: #1E3A5F;
        color: #FFFFFF;
        padding: 24px 28px;
        border-radius: 12px;
        margin: 12px 0;
        line-height: 1.7;
        font-size: 0.95rem;
    }
    .exec-box strong { color: #FFD866; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  HIGH-CONTRAST PALETTE
# ═══════════════════════════════════════════════════════════════════════════════

COLOR_PRIMARY   = "#1E3A5F"
COLOR_ACCENT    = "#E8443A"
COLOR_SECONDARY = "#2CA02C"
BAR_GRADIENT    = alt.Gradient(
    gradient="linear",
    stops=[
        alt.GradientStop(color="#1E3A5F", offset=0),
        alt.GradientStop(color="#2C7FB8", offset=1),
    ],
    x1=0, x2=0, y1=1, y2=0,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  GUARD
# ═══════════════════════════════════════════════════════════════════════════════

required_keys = ["q1", "q2", "q3", "q6", "q7", "metrics"]
if not all(k in st.session_state for k in required_keys):
    st.warning("⚠️ No data found. Please visit the **main page** first to load and clean the data.")
    st.stop()

q1 = st.session_state["q1"]
q2 = st.session_state["q2"]
q3 = st.session_state["q3"]
q6 = st.session_state["q6"]
q7 = st.session_state["q7"]
m  = st.session_state["metrics"]

# ═══════════════════════════════════════════════════════════════════════════════
#  HEADER + METRICS
# ═══════════════════════════════════════════════════════════════════════════════

st.title("📊 NYC Yellow Taxi — Dashboard")
st.caption("January 2024  ·  Cleaned & filtered dataset")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Trips",   f"{m['total_trips']:,}")
col2.metric("Average Fare",  f"${m['avg_fare']:.2f}")
col3.metric("Total Revenue", f"${m['total_revenue']:,.2f}")
col4.metric("Avg Distance",  f"{m['avg_distance']:.2f} mi")
col5.metric("Avg Duration",  f"{m['avg_duration']:.1f} min")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 1 — Top 10 Pick-up Zones
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="chart-header">1. Top 10 Pick-up Zones by Pickups</p>', unsafe_allow_html=True)

df1 = q1.rename({c: c.strip() for c in q1.columns}).rename(
    {"Pick-up Zone Name": "pickup_zone"}
).with_columns(
    pl.col("NUMOFPICKUPS").cast(pl.Int64),
    pl.col("pickup_zone").cast(pl.Utf8),
)

chart1 = alt.Chart(df1).mark_bar(
    cornerRadiusTopRight=6,
    cornerRadiusBottomRight=6,
).encode(
    y=alt.Y("pickup_zone:N", sort="-x", title=None,
            axis=alt.Axis(labelFontSize=12, labelFontWeight="bold", labelColor="#1E3A5F")),
    x=alt.X("NUMOFPICKUPS:Q", title="Number of Pickups",
            axis=alt.Axis(format="~s", labelFontSize=11)),
    color=alt.Color("NUMOFPICKUPS:Q", scale=alt.Scale(scheme="blues"), legend=None),
    tooltip=["pickup_zone:N", alt.Tooltip("NUMOFPICKUPS:Q", format=",")],
).properties(height=380).configure_view(strokeWidth=0)

st.altair_chart(chart1, use_container_width=True)

st.markdown("""
<div class="interp-box">
    <div class="interp-label">Refined Interpretation</div>
The Upper East Side South and Upper East Side Northzones exhibit the highest pickup volumes,reflecting dense residential population, strong commercial activity, and structural reliance on ride-sharing.
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 2 — Average Fare by Hour
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="chart-header">2. Average Fare Amount by Pickup Hour</p>', unsafe_allow_html=True)

df2 = q2.rename({c: c.strip() for c in q2.columns}).with_columns(
    pl.col("pickup_hour").cast(pl.Int64),
    pl.col("AVERAGEFAREAMOUNT").cast(pl.Float64),
).sort("pickup_hour")

line = alt.Chart(df2).mark_line(
    strokeWidth=3, color=COLOR_PRIMARY
).encode(
    x=alt.X("pickup_hour:Q", title="Pickup Hour (0–23)",
            scale=alt.Scale(domain=[0, 23]),
            axis=alt.Axis(tickCount=24, labelFontSize=11)),
    y=alt.Y("AVERAGEFAREAMOUNT:Q", title="Average Fare ($)",
            scale=alt.Scale(zero=False),
            axis=alt.Axis(format="$.0f", labelFontSize=11)),
)

points = alt.Chart(df2).mark_circle(
    size=70, color=COLOR_ACCENT
).encode(
    x="pickup_hour:Q",
    y="AVERAGEFAREAMOUNT:Q",
    tooltip=["pickup_hour:Q", alt.Tooltip("AVERAGEFAREAMOUNT:Q", format="$.2f")],
)

# Highlight 4-6am band
band = alt.Chart(df2).mark_rect(
    opacity=0.12, color=COLOR_ACCENT
).encode(
    x=alt.value(4 / 23 * 600),   # approximate; use rule instead
).properties()

rule_4am = alt.Chart(df2.filter(pl.col("pickup_hour").is_in([4, 5, 6]))).mark_rule(
    color=COLOR_ACCENT, strokeDash=[4, 4], strokeWidth=1.5
).encode(x="pickup_hour:Q")

chart2 = (line + points + rule_4am).properties(height=380).configure_view(strokeWidth=0)

st.altair_chart(chart2, use_container_width=True)

st.markdown("""
<div class="interp-box">
    <div class="interp-label">Refined Interpretation</div> Average fares remain relatively stable throughout the day, with a notable spike between 4 AM and 6 AM. This is likely driven by longer-distance trips (e.g. airport rides) and reduced driver supply during those hours.
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  CHARTS 3 & 4 — Side by Side
# ═══════════════════════════════════════════════════════════════════════════════

col_left, col_right = st.columns(2)

# ── Chart 3: Trip Distance Distribution ──

with col_left:
    st.markdown('<p class="chart-header">3. Trip Distance Distribution</p>', unsafe_allow_html=True)
    st.markdown('<p class="chart-sub">1-mile bins, capped at 50 miles</p>', unsafe_allow_html=True)

    df_dist = q6.with_columns(
        pl.col("trips").cast(pl.Int64),
        pl.col("dist_bin").cast(pl.Int64),
    )

    chart3 = alt.Chart(df_dist).mark_bar(
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4,
        color=COLOR_PRIMARY,
    ).encode(
        x=alt.X("dist_bin:Q", title="Trip Distance (miles)",
                axis=alt.Axis(labelFontSize=11)),
        y=alt.Y("trips:Q", title="Number of Trips",
                axis=alt.Axis(format="~s", labelFontSize=11)),
        opacity=alt.condition(
            alt.datum.dist_bin <= 5,
            alt.value(1.0),
            alt.value(0.55),
        ),
        tooltip=["dist_bin:Q", alt.Tooltip("trips:Q", format=",")],
    ).properties(height=340).configure_view(strokeWidth=0)

    st.altair_chart(chart3, use_container_width=True)

    st.markdown("""
    <div class="interp-box">
        <div class="interp-label">Refined Interpretation</div>
Most trips are short distance (0–5 miles) with a long right tail representing longer trips.
    </div>
    """, unsafe_allow_html=True)

# ── Chart 4: Payment Type Distribution ──

with col_right:
    st.markdown('<p class="chart-header">4. Payment Type Distribution</p>', unsafe_allow_html=True)
    st.markdown('<p class="chart-sub">Transaction count by payment method</p>', unsafe_allow_html=True)

    mapping = {
        1: "Credit Card", 2: "Cash", 3: "No Charge",
        4: "Dispute", 5: "Unknown", 6: "Voided",
    }

    payment_colors = {
        "Credit Card": "#1E3A5F",
        "Cash":        "#E8443A",
        "No Charge":   "#F5A623",
        "Dispute":     "#7B2D8E",
        "Unknown":     "#999999",
        "Voided":      "#CCCCCC",
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

    chart4 = alt.Chart(df3).mark_bar(
        cornerRadiusTopLeft=6,
        cornerRadiusTopRight=6,
    ).encode(
        x=alt.X("payment_name:N", title=None, sort="-y",
                axis=alt.Axis(labelFontSize=12, labelFontWeight="bold", labelAngle=0)),
        y=alt.Y("NUMOFPAYMENTS:Q", title="Number of Payments",
                axis=alt.Axis(format="~s", labelFontSize=11)),
        color=alt.Color("payment_name:N",
                        scale=alt.Scale(domain=list(payment_colors.keys()),
                                        range=list(payment_colors.values())),
                        legend=None),
        tooltip=[
            "payment_name:N",
            alt.Tooltip("NUMOFPAYMENTS:Q", format=","),
            alt.Tooltip("PERCENTAGE:Q", format=".2f", title="Share (%)"),
        ],
    ).properties(height=340).configure_view(strokeWidth=0)

    st.altair_chart(chart4, use_container_width=True)

    st.markdown("""
    <div class="interp-box">
        <div class="interp-label">Refined Interpretation</div>
        Credit cards dominate the payment ecosystem,accounting for roughly 80% of transactions Cash and other methods represent a minority share.
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  CHART 5 — Heatmap: Trips by Day × Hour
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="chart-header">5. Trips by Day of Week and Hour</p>', unsafe_allow_html=True)

df7 = q7.with_columns(
    pl.col("pickup_hour").cast(pl.Int64),
    pl.col("num_trips").cast(pl.Int64),
    pl.col("pickup_date_of_week").cast(pl.Utf8),
)

day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]

heatmap = alt.Chart(df7).mark_rect(
    cornerRadius=3
).encode(
    x=alt.X("pickup_hour:O", title="Hour of Day",
            axis=alt.Axis(labelFontSize=11, labelAngle=0)),
    y=alt.Y("pickup_date_of_week:N", sort=day_order, title=None,
            axis=alt.Axis(labelFontSize=12, labelFontWeight="bold", labelColor="#1E3A5F")),
    color=alt.Color("num_trips:Q", title="Trips",
                    scale=alt.Scale(scheme="darkblue"),
                    legend=alt.Legend(direction="horizontal", orient="top",
                                     titleFontSize=11, labelFontSize=10)),
    tooltip=[
        alt.Tooltip("pickup_date_of_week:N", title="Day"),
        alt.Tooltip("pickup_hour:Q", title="Hour"),
        alt.Tooltip("num_trips:Q", title="Trips", format=","),
    ],
).properties(height=320).configure_view(strokeWidth=0)

st.altair_chart(heatmap, use_container_width=True)

st.markdown("""
<div class="interp-box">
    <div class="interp-label">Refined Interpretation</div>
    Demand peaks during weekday evening commute hours (5–7 PM) and is lowest during late-night hours (2–5 AM).
    Weekend demand is more evenly distributed throughout the day, with later morning start times.
    Fare spikes during off-peak hours cannot be ruled out as supply-demand imbalance effects — surge pricing
    is driven by the ratio of demand to supply.
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()

st.markdown('<p class="chart-header">Done By</p>', unsafe_allow_html=True)

st.markdown("""
<div class="exec-box">
    Daniel Mangal
    Assignment (1)
    COMP3605 - Big Data Analytics
</div>
""", unsafe_allow_html=True)
