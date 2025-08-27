import streamlit as st
import pandas as pd
from pathlib import Path

@st.cache_data(show_spinner=False)
def load_data(path: str | Path = "data/sample.csv") -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10),
                             "sales": range(10)})
    return pd.read_csv(p)
