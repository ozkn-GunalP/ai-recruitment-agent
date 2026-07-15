import streamlit as st


def check_password() -> bool:
    """Basit parola koruması. Doğruysa True döner, değilse formu gösterir ve False döner."""

    if st.session_state.get("authenticated"):
        return True

    password = st.secrets.get("APP_PASSWORD")
    if not password:
        # Parola tanımlı değilse korumayı atla (yerel geliştirme kolaylığı)
        return True

    st.markdown("## 🔒 Giriş")
    entered = st.text_input("Parola", type="password", key="_auth_pw")

    if st.button("Giriş", key="_auth_btn"):
        if entered == password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Yanlış parola.")

    return False
