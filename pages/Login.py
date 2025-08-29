# pages/Login.py
import streamlit as st
import bcrypt
from st_supabase_connection import SupabaseConnection
import pandas as pd

def run_login():
    # --- Connect to Supabase ---
    conn = st.connection("supabase", type=SupabaseConnection)

    # --- Initialize session state ---
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False

    # --- Page layout ---
    st.set_page_config(page_title="Login / Sign Up", page_icon="🔑", layout="centered")
    st.markdown("""
        <style>
        .main {background-color: #f5f5f5;}
        .stTextInput>div>div>input {height:2em;}
        .login-box {
            background-color:white;
            padding:2em;
            border-radius:15px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.title("🔑 Welcome")

    # --- Login or Signup Form ---
    if not st.session_state.show_signup:
        st.subheader("Login to your account")
        email = st.text_input("Email", key="login_email").lower()
        password = st.text_input("Password", type="password", key="login_pw")

        # Primary login button (light blue)
        if st.button("Login", key="login_btn", type="primary"):
            try:
                users = conn.table("users").select("*").eq("email", email).execute().data
                if users:
                    user = users[0]
                    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                        st.session_state.user_id = user["id"]
                        st.session_state.user_email = user["email"]
                        st.rerun()
                    else:
                        st.error("❌ Invalid password")
                else:
                    st.error("❌ User not found")
            except Exception as e:
                st.error(f"Error logging in: {e}")

        # Secondary toggle button (light grey)
        if st.button("Don't have an account? Sign up", key="toggle_signup", type="secondary"):
            st.session_state.show_signup = True
            st.rerun()

    else:
        st.subheader("Create a new account")
        new_email = st.text_input("Email", key="signup_email").lower()
        new_password = st.text_input("Password", type="password", key="signup_pw")
        full_name = st.text_input("Full Name (optional)", key="signup_name")

        # Primary signup button (light blue)
        if st.button("Sign Up", key="signup_btn", type="primary"):
            try:
                existing_users = conn.table("users").select("*").eq("email", new_email).execute().data
                if existing_users:
                    st.warning("User already exists!")
                else:
                    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                    conn.table("users").insert({
                        "email": new_email,
                        "password_hash": pw_hash,
                        "full_name": full_name
                    }).execute()
                    st.success("✅ Account created! Please login.")
                    st.session_state.show_signup = False
            except Exception as e:
                st.error(f"Error signing up: {e}")

        # Secondary toggle button (light grey)
        if st.button("Already have an account? Login", key="toggle_login", type="secondary"):
            st.session_state.show_signup = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
