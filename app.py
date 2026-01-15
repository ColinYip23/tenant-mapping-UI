import streamlit as st
from supabase import create_client, Client

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Tenant Mapping Manager",
    page_icon="🗺️",
    layout="centered"
)

st.markdown(
    """
    <style>
    /* Change cursor to hand for selectbox */
    div[data-baseweb="select"] {
        cursor: pointer;
    }

    /* Ensure all inner elements also show pointer */
    div[data-baseweb="select"] * {
        cursor: pointer !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 2. DATABASE SETUP (SUPABASE)
# ==========================================
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
# 3. MANAGEMENT UI
# ==========================================
st.title("🗺️ Tenant RAG Mapping Manager")
st.write("Manage which Knowledge Base each tenant is connected to.")

st.markdown("### ➕ Add New Tenant Mapping")

with st.expander("Add a new tenant → Knowledge Base mapping"):
    with st.form("add_new_mapping_form"):
        new_whatsapp = st.text_input(
            "WhatsApp Number",
            placeholder="+60123456789"
        )

        new_source_name = st.selectbox(
            "Assign Knowledge Base",
            options=sorted(list(SOURCE_MAP.values()))
        )

        create_btn = st.form_submit_button("Create Mapping")

        if create_btn:
            if not new_whatsapp.strip():
                st.error("WhatsApp number is required.")
            else:
                db_value = REVERSE_MAP.get(new_source_name, new_source_name)

                try:
                    supabase.table("tenant mapping").insert({
                        "WhatsApp number": new_whatsapp,
                        "RAG source": db_value
                    }).execute()

                    st.success(f"Mapping created for {new_whatsapp}")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to create mapping: {e}")


if tenants:
    display_options = sorted(list(SOURCE_MAP.values()))

    for tenant in tenants:
        current_num = tenant.get('RAG source', "Default")
        current_display = SOURCE_MAP.get(current_num, current_num)
        whatsapp = tenant.get('WhatsApp number', 'Unknown')
        
        # Expander with explicit Black Text styling
        with st.expander(f"📱 {whatsapp} — Current: {current_display}"):
            with st.form(key=f"form_{tenant['id']}"):
                
                # Column Titles for clarity
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<p class="column-header">Current RAG Details</p>', unsafe_allow_html=True)
                    st.write(f"**WhatsApp:** {whatsapp}")
                    st.write(f"**Source Number:** `{current_num}`")
                
                with col2:
                    st.markdown('<p class="column-header">Update Mapping</p>', unsafe_allow_html=True)
                    selected_name = st.selectbox(
                        "Assign New Knowledge Base",
                        options=display_options,
                        index=display_options.index(current_display) if current_display in display_options else 0,
                        label_visibility="collapsed" # Hide the redundant label as we have a title
                    )
                
                st.write("---")
                submit_button = st.form_submit_button("Save Changes")
                
                if submit_button:
                    db_value = REVERSE_MAP.get(selected_name, selected_name)
                    try:
                        supabase.table("tenant mapping") \
                            .update({"RAG source": db_value}) \
                            .eq("id", tenant["id"]) \
                            .execute()
                        
                        st.success(f"Updated to {selected_name}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
else:
    st.info("No tenants found in the database.")