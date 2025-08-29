
def run_settings():
    # pages/Settings.py
    import streamlit as st
    from st_supabase_connection import SupabaseConnection
    import bcrypt

    # --- Require login ---
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        from pages.Login import run_login
        run_login()
        return

    st.title("⚙️ Settings & Profile")

    # --- Connect to Supabase ---
    conn = st.connection("supabase", type=SupabaseConnection)

    st.subheader("Change Password")
    current_pw = st.text_input("Current Password", type="password")
    new_pw = st.text_input("New Password", type="password")
    confirm_pw = st.text_input("Confirm New Password", type="password")

    if st.button("Update Password", type="primary"):
        if not current_pw or not new_pw or not confirm_pw:
            st.warning("Please fill in all password fields.")
        elif new_pw != confirm_pw:
            st.warning("New passwords do not match.")
        else:
            # Fetch current user
            user = conn.table("users").select("*").eq("id", st.session_state.user_id).execute().data
            if not user:
                st.error("User not found.")
            else:
                user = user[0]
                # Verify current password
                if not bcrypt.checkpw(current_pw.encode(), user["password_hash"].encode()):
                    st.error("❌ Current password is incorrect.")
                else:
                    # Hash new password and update
                    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
                    conn.table("users").update({"password_hash": new_hash}) \
                        .eq("id", st.session_state.user_id).execute()
                    st.success("✅ Password updated successfully!")

    st.markdown("---")
    st.subheader("Other Profile Settings")
    st.info("You can add additional settings here, e.g., change email, display name, etc.")
