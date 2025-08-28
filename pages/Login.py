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

    st.markdown(
        """
        <style>
        .main {background-color: #f5f5f5;}
        .stButton>button {background-color:#4CAF50;color:white;height:3em;width:100%;}
        .stTextInput>div>div>input {height:2em;}
        .login-box {background-color:white;padding:2em;border-radius:15px;box-shadow: 0 0 20px rgba(0,0,0,0.1);}
        .link {color: #1a73e8; cursor:pointer; text-decoration: underline;}
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.title("🔑 Welcome")

    # Toggle between login/signup
    if not st.session_state.show_signup:
        st.subheader("Login to your account")
        email = st.text_input("Email", key="login_email")
        email = email.lower()
        password = st.text_input("Password", type="password", key="login_pw")
        
        if st.button("Login"):
            try:
                users = conn.table("users").select("*").eq("email", email).execute().data
                if users:
                    user = users[0]
                    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                        st.session_state.user_id = user["id"]
                        st.session_state.user_email = user["email"]
                        st.success(f"✅ Logged in as {email}")
                    else:
                        st.error("❌ Invalid password")
                else:
                    st.error("❌ User not found")
            except Exception as e:
                st.error(f"Error logging in: {e}")

        st.markdown(
            "<p class='link' onclick='window.dispatchEvent(new Event(\"signup_toggle\"))'>Don't have an account? Sign up</p>",
            unsafe_allow_html=True
        )
    else:
        st.subheader("Create a new account")
        new_email = st.text_input("Email", key="signup_email")
        new_email = new_email.lower()
        new_password = st.text_input("Password", type="password", key="signup_pw")
        full_name = st.text_input("Full Name (optional)", key="signup_name")
        
        if st.button("Sign Up"):
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
                    st.success("✅ Account created! Please login above.")
                    st.session_state.show_signup = False
            except Exception as e:
                st.error(f"Error signing up: {e}")

        st.markdown(
            "<p class='link' onclick='window.dispatchEvent(new Event(\"signup_toggle\"))'>Already have an account? Login</p>",
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Logout button if logged in
    if st.session_state.user_id:
        if st.button("Logout"):
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.success("Logged out successfully")
