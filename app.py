import streamlit as st
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials, auth

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Tenant Mapping Manager",
    page_icon="🗺️",
    layout="centered"
)

# Custom CSS for a professional look
st.markdown("""
    <style>
    .stApp { background-color: #f9f9f9; }
    .st-expander { border: 1px solid #e6e6e6; border-radius: 8px; background-color: white; margin-bottom: 10px; }
    .stButton button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. AUTHENTICATION (FIREBASE)
# ==========================================
if not firebase_admin._apps:
    try:
        fb_creds = dict(st.secrets["firebase"])
        # Fix for newline characters in TOML secrets
        fb_creds["private_key"] = fb_creds["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Internal Error: Firebase setup failed. {e}")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_screen():
    st.title("🗺️ Tenant Manager Login")
    email = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    
    if st.button("Sign In"):
        try:
            # Check if user exists in Firebase
            user = auth.get_user_by_email(email)
            st.session_state.authenticated = True
            st.rerun()
        except Exception:
            st.error("Access Denied: Invalid credentials or unauthorized user.")

if not st.session_state.authenticated:
    login_screen()
    st.stop()

# ==========================================
# 3. DATABASE SETUP (SUPABASE)
# ==========================================
# Sidebar Logout
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=60)
def get_all_data():
    # Fetch data using exact column names from your DB
    tenants = supabase.table("tenant mapping").select("*").execute().data
    sources = supabase.table("rag sources").select("*").execute().data
    
    # Map Phone Numbers to Friendly Names
    num_to_name = {s['RAG source']: s['source name'] for s in sources}
    name_to_num = {s['source name']: s['RAG source'] for s in sources}
    
    return tenants, num_to_name, name_to_num

try:
    tenants, SOURCE_MAP, REVERSE_MAP = get_all_data()
except Exception as e:
    st.error(f"Database Error: {e}")
    st.stop()

# ==========================================
# 4. MANAGEMENT UI
# ==========================================
st.title("🗺️ Tenant RAG Mapping Manager")
st.write("Manage which Knowledge Base each tenant is connected to.")

if tenants:
    display_options = sorted(list(SOURCE_MAP.values()))

    for tenant in tenants:
        # Resolve current mapping
        current_num = tenant.get('RAG source', "Default")
        current_display = SOURCE_MAP.get(current_num, current_num)
        
        # Expander for each tenant
        with st.expander(f"Tenant: {tenant.get('WhatsApp number', 'Unknown')} — ({current_display})"):
            # Use form to prevent page refresh/expander closing during selection
            with st.form(key=f"form_{tenant['id']}"):
                st.write(f"**Current RAG Number:** `{current_num}`")
                
                selected_name = st.selectbox(
                    "Assign New Knowledge Base",
                    options=display_options,
                    index=display_options.index(current_display) if current_display in display_options else 0
                )
                
                submit_button = st.form_submit_button("Save Changes")
                
                if submit_button:
                    db_value = REVERSE_MAP.get(selected_name, selected_name)
                    
                    try:
                        supabase.table("tenant mapping") \
                            .update({"RAG source": db_value}) \
                            .eq("id", tenant["id"]) \
                            .execute()
                        
                        st.success(f"Updated to {selected_name}")
                        st.cache_data.clear() # Clear cache to refresh the UI
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
else:
    st.info("No tenants found in the database.")