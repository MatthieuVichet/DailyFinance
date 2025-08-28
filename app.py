import streamlit as st

st.set_page_config(page_title="Finance App", layout="wide")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Go to", ["Dashboard", "Recordings", "Recurring"])

# --- Import pages ---
if page == "Dashboard":
    from pages.Dashboard import run_dashboard
    run_dashboard()
elif page == "Recordings":
    from pages.Records import run_recordings
    run_recordings()
elif page == "Recurring":
    from pages.Recurrings import run_recurring
    run_recurring()
