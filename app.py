import streamlit as st

# --- Page config ---
st.set_page_config(
    page_title="Finance App",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Hide default Streamlit UI ---
st.markdown("""
    <style>
        .reportview-container {margin-top: -10rem;}
        [data-testid="stSidebarNav"] {display: none;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- Import login page ---
from pages.Login import run_login

# --- Check login ---
if "user_id" not in st.session_state or st.session_state.user_id is None:
    run_login()
else:
    # --- Your custom sidebar navigation ---
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Go to", ["Dashboard", "Recordings", "Recurring" "Settings"])

    # --- Load Pages ---
    if page == "Dashboard":
        from pages.Dashboard import run_dashboard
        run_dashboard()
    elif page == "Recordings":
        from pages.Records import run_recordings
        run_recordings()
    elif page == "Recurring":
        from pages.Recurrings import run_recurring
        run_recurring()
    elif page == "Settings":
        from pages.Settings import run_settings
        run_settings()
