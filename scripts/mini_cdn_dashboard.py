import requests
import pandas as pd
import streamlit as st

API_BASE = "http://127.0.0.1:8000"


# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Mini CDN Cache Dashboard",
    page_icon="📡",
    layout="wide",
)

st.title("Mini CDN Cache Dashboard")
st.caption("Big Data Pipeline → Hot Video Prediction → Cache Recommendation → Mini CDN Simulation")


# =========================
# HELPER FUNCTIONS
# =========================

def api_get(endpoint: str):
    url = f"{API_BASE}{endpoint}"
    try:
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


def api_post(endpoint: str):
    url = f"{API_BASE}{endpoint}"
    try:
        response = requests.post(url, timeout=180)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


def show_api_error(error):
    st.error(
        "Unable to connect to the Mini CDN API. "
        "Please make sure the FastAPI server is running at http://127.0.0.1:8000"
    )
    st.code(error)


# =========================
# SIDEBAR
# =========================

st.sidebar.header("Control Panel")
st.sidebar.write("Mini CDN API")
st.sidebar.code(API_BASE)

if st.sidebar.button("Reset Statistics"):
    result, error = api_post("/reset")
    if error:
        show_api_error(error)
    else:
        st.sidebar.success("Statistics reset successfully.")


# =========================
# CHECK API SERVER
# =========================

home, error = api_get("/")

if error:
    show_api_error(error)
    st.stop()

st.success("Mini CDN API Server is running.")


# =========================
# CURRENT CDN STATISTICS
# =========================

st.subheader("Current CDN Statistics")

stats, error = api_get("/stats")

if error:
    show_api_error(error)
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Requests", stats.get("total_requests", 0))

with col2:
    st.metric("Cache Hits", stats.get("cache_hits", 0))

with col3:
    st.metric("Cache Misses", stats.get("cache_misses", 0))

with col4:
    hit_ratio = stats.get("cache_hit_ratio", 0)
    st.metric("Cache Hit Ratio", f"{hit_ratio * 100:.2f}%")

with col5:
    st.metric("Average Latency", f"{stats.get('average_latency_ms', 0):.2f} ms")


# =========================
# LIVE DEMO ACTIONS
# =========================

st.subheader("Live Demo Actions")

action_col1, action_col2, action_col3 = st.columns(3)

with action_col1:
    st.write("Simulate a request for a cached video")
    if st.button("Request Cached Video"):
        result, error = api_get("/demo/cache-hit")
        if error:
            show_api_error(error)
        else:
            st.session_state["last_result"] = result

with action_col2:
    st.write("Simulate a request for a non-cached video")
    if st.button("Request Non-Cached Video"):
        result, error = api_get("/demo/cache-miss")
        if error:
            show_api_error(error)
        else:
            st.session_state["last_result"] = result

with action_col3:
    st.write("Simulate multiple mixed video requests")

    mixed_count = st.number_input(
        "Request Count",
        min_value=1,
        max_value=100,
        value=20,
        step=1,
    )

    cache_ratio = st.slider(
        "Expected Cache Ratio",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.1,
    )

    if st.button("Run Mixed Demo"):
        endpoint = f"/demo/mixed?count={mixed_count}&cache_ratio={cache_ratio}"
        result, error = api_get(endpoint)
        if error:
            show_api_error(error)
        else:
            st.session_state["mixed_result"] = result


# =========================
# MANUAL VIDEO REQUEST
# =========================

st.subheader("Manual Video Request")

video_id = st.text_input("Enter a video ID", value="1289459")

manual_col1, manual_col2 = st.columns([1, 4])

with manual_col1:
    if st.button("Request This Video"):
        result, error = api_get(f"/video/{video_id}")
        if error:
            show_api_error(error)
        else:
            st.session_state["last_result"] = result

with manual_col2:
    st.caption(
        "Use this section to manually request any video ID and check whether the server returns "
        "CACHE HIT or CACHE MISS."
    )


# =========================
# LAST REQUEST RESULT
# =========================

if "last_result" in st.session_state:
    st.subheader("Last Request Result")

    result = st.session_state["last_result"]

    status = result.get("status", "")
    served_from = result.get("served_from", "")
    latency_ms = result.get("latency_ms", 0)

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric("Status", status)

    with r2:
        st.metric("Served From", served_from)

    with r3:
        st.metric("Latency", f"{latency_ms} ms")

    with r4:
        st.metric("Current Hit Ratio", f"{result.get('current_cache_hit_ratio', 0) * 100:.2f}%")

    st.json(result)


# =========================
# MIXED DEMO RESULT
# =========================

if "mixed_result" in st.session_state:
    st.subheader("Mixed Demo Result")

    mixed = st.session_state["mixed_result"]

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("Demo Requests", mixed.get("demo_requests", 0))

    with m2:
        st.metric("Cache Hits", mixed.get("cache_hits", 0))

    with m3:
        st.metric("Cache Misses", mixed.get("cache_misses", 0))

    with m4:
        st.metric("Average Latency", f"{mixed.get('average_latency_ms', 0):.2f} ms")

    results = mixed.get("results", [])

    if len(results) > 0:
        result_df = pd.DataFrame(results)

        st.write("Request Results")
        st.dataframe(result_df, use_container_width=True)

        chart_df = result_df["status"].value_counts().reset_index()
        chart_df.columns = ["Status", "Count"]

        st.write("Cache Hit / Miss Distribution")
        st.bar_chart(chart_df, x="Status", y="Count")

# TOP CACHED VIDEOS

st.subheader("Top Cached Videos")

top_n = st.slider(
    "Number of Top Cached Videos",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
)

top_result, error = api_get(f"/cache/top?n={top_n}")

if error:
    show_api_error(error)
else:
    top_records = top_result.get("records", [])

    if len(top_records) > 0:
        top_df = pd.DataFrame(top_records)

        st.write("Top Cached Video-Window Records")
        st.dataframe(top_df, use_container_width=True)

        if "hot_score" in top_df.columns:
            chart_df = top_df[["video_id", "hot_score"]].copy()
            chart_df["video_id"] = chart_df["video_id"].astype(str)

            st.write("Top Cached Videos by Hot Score")
            st.bar_chart(chart_df, x="video_id", y="hot_score")
    else:
        st.info("No cached videos found.")
