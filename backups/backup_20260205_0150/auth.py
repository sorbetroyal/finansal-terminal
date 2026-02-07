"""
Authentication module for Supabase Auth integration.
"""
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def init_auth_state():
    """Initialize authentication state."""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None

def get_current_user():
    """Get the currently logged in user."""
    return st.session_state.get("user")

def get_user_id():
    """Get the current user's ID."""
    user = get_current_user()
    return user.id if user else None

def login(email: str, password: str) -> tuple[bool, str]:
    """Login with email and password."""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            st.session_state.user = response.user
            st.session_state.access_token = response.session.access_token
            return True, "Giriş başarılı!"
        return False, "Giriş başarısız: Kullanıcı bilgileri alınamadı."
        
    except Exception as e:
        error_msg = str(e)
        # Detailed error handling
        if "Invalid login credentials" in error_msg:
            return False, "E-posta veya şifre hatalı! Lütfen bilgilerinizi kontrol edin."
        elif "Email not confirmed" in error_msg:
            return False, "⚠️ Bu hesap henüz onaylanmamış! Lütfen e-postanızı kontrol edin veya Supabase panelinden 'Confirm email' ayarını kapatın."
        elif "captcha" in error_msg.lower():
            return False, "Güvelik doğrulaması (Captcha) hatası. Supabase panelinden Captcha'yı kapatmayı deneyin."
        
        return False, f"Supabase Hatası: {error_msg}"


def register(email: str, password: str) -> tuple[bool, str]:
    """Register a new user."""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Check for immediate session (Auto-confirm is ON in Supabase)
            if hasattr(response, 'session') and response.session:
                st.session_state.user = response.user
                st.session_state.access_token = response.session.access_token
                return True, "🎉 Kayıt başarılı! Uygulamaya giriş yapılıyor..."
            else:
                return True, "✅ Kayıt başarılı! Lütfen giriş yapın."
        
        return False, "Kullanıcı oluşturulamadı. Bilgileri kontrol edin."


        
    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            return False, "Bu e-posta adresi zaten kayıtlı!"
        elif "Password should be at least" in error_msg:
            return False, "Şifre en az 6 karakter olmalıdır!"
        elif "over the limit" in error_msg.lower():
            return False, "Kayıt deneme limitine ulaştınız. Lütfen biraz bekleyin."
        return False, f"Hata: {error_msg}"


def logout():
    """Logout the current user."""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except:
        pass
    
    st.session_state.user = None
    st.session_state.access_token = None

def render_auth_page():
    """Render the login/register page."""
    
    # Centered container with styling
    st.markdown("""
    <style>
        .auth-container {
            max-width: 400px;
            margin: 50px auto;
            padding: 40px;
            background: rgba(23, 27, 33, 0.9);
            border-radius: 20px;
            border: 1px solid rgba(0, 242, 255, 0.2);
            box-shadow: 0 0 40px rgba(0, 242, 255, 0.1);
        }
        .auth-title {
            text-align: center;
            color: #00f2ff;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(0, 242, 255, 0.3);
        }
        .auth-subtitle {
            text-align: center;
            color: rgba(255,255,255,0.5);
            font-size: 0.9rem;
            margin-bottom: 30px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-title">💹 Finansal Terminal</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Portföyünüzü yönetin, performansınızı takip edin</div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Giriş Yap", "📝 Kayıt Ol"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("📧 E-posta", placeholder="ornek@email.com")
                password = st.text_input("🔑 Şifre", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
                
                if submit:
                    if email and password:
                        success, message = login(email, password)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Lütfen tüm alanları doldurun.")
        
        with tab2:
            with st.form("register_form"):
                reg_email = st.text_input("📧 E-posta", placeholder="ornek@email.com", key="reg_email")
                reg_password = st.text_input("🔑 Şifre (min. 6 karakter)", type="password", placeholder="••••••••", key="reg_pass")
                reg_password2 = st.text_input("🔑 Şifre Tekrar", type="password", placeholder="••••••••", key="reg_pass2")
                submit_reg = st.form_submit_button("Kayıt Ol", type="primary", use_container_width=True)
                
                if submit_reg:
                    if reg_email and reg_password and reg_password2:
                        if reg_password != reg_password2:
                            st.error("Şifreler eşleşmiyor!")
                        elif len(reg_password) < 6:
                            st.error("Şifre en az 6 karakter olmalıdır!")
                        else:
                            success, message = register(reg_email, reg_password)
                            if success:
                                st.success(message)
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(message)

                    else:
                        st.warning("Lütfen tüm alanları doldurun.")

def require_auth(func):
    """Decorator to require authentication."""
    def wrapper(*args, **kwargs):
        init_auth_state()
        if not get_current_user():
            render_auth_page()
            st.stop()
        return func(*args, **kwargs)
    return wrapper
