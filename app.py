import streamlit as st
from supabase import create_client, Client

# 1. Setup Connection
url = "https://olxkyjgzrmddodluuwbd.supabase.co"
key = "sb_secret_MXc_h5Ye8_3RqlG2cQ7EsA_winHKfK3"
supabase: Client = create_client(url, key)

# 2. Fetch All Data
@st.cache_data(ttl=60)
def get_all_data():
    # Fetch Tenants
    tenants = supabase.table("tenant mapping").select("*").execute().data
    
    # Fetch RAG Source Mappings
    sources = supabase.table("rag sources").select("*").execute().data
    
    # Create Dictionaries for easy lookup
    num_to_name = {s['RAG source']: s['source name'] for s in sources}
    name_to_num = {s['source name']: s['RAG source'] for s in sources}
    
    return tenants, num_to_name, name_to_num

tenants, SOURCE_MAP, REVERSE_MAP = get_all_data()

st.title("Tenant RAG Mapping Manager")

# 3. Management UI
if tenants:
    # Use a dropdown list of the friendly names we found in the database
    display_options = sorted(list(SOURCE_MAP.values()))

    for tenant in tenants:
        current_num = tenant.get('RAG source', "Default")
        current_display = SOURCE_MAP.get(current_num, current_num)
        
        # We use expanded=False by default, but the form prevents the 'auto-close' on change
        with st.expander(f"Tenant: {tenant['WhatsApp number']} ({current_display})"):
            # Wrap the selection and button in a form
            with st.form(key=f"form_{tenant['id']}"):
                selected_name = st.selectbox(
                    "Change Knowledge Base",
                    options=display_options,
                    index=display_options.index(current_display) if current_display in display_options else 0
                )
                
                # Use form_submit_button instead of st.button
                submit_button = st.form_submit_button("Save Changes")
                
                if submit_button:
                    db_value = REVERSE_MAP.get(selected_name, selected_name)
                    
                    supabase.table("tenant mapping") \
                        .update({"RAG source": db_value}) \
                        .eq("id", tenant["id"]) \
                        .execute()
                    
                    st.success("Updated!")
                    st.cache_data.clear()
                    st.rerun()
else:
    st.info("No tenants found.")