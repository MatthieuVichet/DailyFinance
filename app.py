import streamlit as st
from src.data.loader import load_data

st.set_page_config(page_title="Demo App", page_icon="📊", layout="wide")

st.title("Daily App")
st.caption("A multi-page Streamlit template")
