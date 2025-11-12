"""
SAI Quote Search - WITH MODULE 1 MATCHING
Claude Dark Mode Interface + Module 1 Assembly Selection
"""
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import json
import sys
import os

# Add Module1Matcher to path
# Assumes Module1Matcher.py is in the same directory
try:
    from Module1Matcher import match_from_user_input, get_matcher
    MODULE1_AVAILABLE = True
except ImportError:
    MODULE1_AVAILABLE = False
    st.error("⚠️ Module1Matcher.py not found. Module 1 matching disabled.")

# Configuration from Streamlit secrets
SEARCH_ENDPOINT = st.secrets["SEARCH_ENDPOINT"]
SEARCH_KEY = st.secrets["SEARCH_KEY"]
INDEX_NAME = st.secrets["INDEX_NAME"]
AZURE_OPENAI_ENDPOINT = st.secrets["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = st.secrets["AZURE_OPENAI_KEY"]
AZURE_OPENAI_DEPLOYMENT = st.secrets["AZURE_OPENAI_DEPLOYMENT"]
AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS = st.secrets["AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS"]

# Password protection
AUTHORIZED_USERS = st.secrets["AUTHORIZED_USERS"]

openai.api_type = "azure"
openai.api_key = AZURE_OPENAI_KEY
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = "2024-02-01"

# Page config
st.set_page_config(
    page_title="SAI Quote Search + Module 1",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Claude Dark Mode + Module 1 Cards
st.markdown("""
<style>
    /* Claude Dark Mode Colors */
    :root {
        --bg-primary: #1e1e1e;
        --bg-secondary: #2d2d2d;
        --bg-tertiary: #3a3a3a;
        --text-primary: #e8e8e8;
        --text-secondary: #b0b0b0;
        --accent-blue: #2563EB;
        --accent-green: #10B981;
        --accent-yellow: #F59E0B;
        --border-color: #404040;
    }
    
    /* Main background */
    .stApp {
        background-color: #1e1e1e;
        color: #e8e8e8;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Header */
    .main-header {
        background: #2d2d2d;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid #404040;
    }
    
    .main-header h1 {
        color: #e8e8e8;
        margin: 0;
        font-size: 1.75rem;
        font-weight: 600;
    }
    
    .main-header p {
        color: #b0b0b0;
        margin: 0.5rem 0 0 0;
        font-size: 0.95rem;
    }
    
    /* Module 1 Badge */
    .module1-badge {
        background: #10B981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-left: 1rem;
    }
    
    /* Chat input */
    .stChatInput {
        background: #2d2d2d !important;
        border: 1px solid #404040 !important;
        border-radius: 24px !important;
    }
    
    .stChatInput textarea {
        background: #2d2d2d !important;
        color: #e8e8e8 !important;
        border: none !important;
    }
    
    /* Message bubbles - User */
    .user-message {
        background: #2563EB;
        color: white;
        padding: 1rem 1.25rem;
        border-radius: 18px;
        margin: 1.5rem 0;
        max-width: 85%;
        margin-left: auto;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    /* Message bubbles - Assistant */
    .assistant-message {
        background: #2d2d2d;
        color: #e8e8e8;
        padding: 1.25rem 1.5rem;
        border-radius: 18px;
        margin: 1.5rem 0;
        max-width: 85%;
        border: 1px solid #404040;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    /* BOM Card */
    .bom-card {
        background: linear-gradient(135deg, #2d2d2d 0%, #3a3a3a 100%);
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        border: 2px solid #10B981;
        box-shadow: 0 8px 24px rgba(16, 185, 129, 0.2);
    }
    
    .bom-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #404040;
    }
    
    .bom-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #10B981;
    }
    
    .bom-assembly {
        font-size: 1.125rem;
        color: #e8e8e8;
        font-weight: 600;
    }
    
    /* Component list */
    .component-item {
        background: #2d2d2d;
        padding: 0.875rem 1.25rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #10B981;
    }
    
    .component-number {
        font-family: 'Courier New', monospace;
        color: #10B981;
        font-weight: 600;
    }
    
    /* Quote cards */
    .quote-card {
        background: #2d2d2d;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #404040;
        transition: all 0.2s;
    }
    
    .quote-card:hover {
        border-color: #2563EB;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    
    /* Status badges */
    .status-exact {
        background: #10B981;
        color: white;
        padding: 0.375rem 0.875rem;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-ambiguous {
        background: #F59E0B;
        color: white;
        padding: 0.375rem 0.875rem;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-nomatch {
        background: #EF4444;
        color: white;
        padding: 0.375rem 0.875rem;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* Spec labels and values */
    .spec-label {
        font-size: 0.75rem;
        color: #b0b0b0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
        margin-bottom: 0.25rem;
    }
    
    .spec-value {
        font-size: 1.125rem;
        color: #e8e8e8;
        font-weight: 600;
    }
    
    /* Streamlit components override */
    .stMarkdown {
        color: #e8e8e8;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #2d2d2d;
        border-right: 1px solid #404040;
    }
    
    /* Buttons */
    .stButton > button {
        background: #2563EB;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background: #1d4ed8;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #2d2d2d;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #404040;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #505050;
    }
</style>
""", unsafe_allow_html=True)

def check_password():
    """Returns True if user is authenticated"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    # Show login form
    st.markdown("""
    <div class="main-header">
        <h1>SAI Quote Search + Module 1</h1>
        <p>Sign in to access the quote search and BOM generation system</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Welcome back")
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")
        
        if st.button("Sign in", use_container_width=True):
            if username in AUTHORIZED_USERS and AUTHORIZED_USERS[username] == password:
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.success("Signed in successfully")
                st.rerun()
            else:
                st.error("Invalid credentials")
        
        st.markdown("---")
        st.caption("For authorized SAI personnel only")
    
    return False

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'search_client' not in st.session_state:
    st.session_state.search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY)
    )
if 'module1_mode' not in st.session_state:
    st.session_state.module1_mode = False

# Check authentication first
if not check_password():
    st.stop()

def is_module1_query(text):
    """Detect if query is about Module 1 / BOM generation"""
    module1_keywords = [
        'module 1', 'module1', 'bom', 'bill of materials',
        'assembly', 'components', 'parts list',
        'box building', 'breaker', 'emax', 'tmax'
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in module1_keywords)

def detect_dimensions_in_query(text):
    """Check if query contains dimension specifications"""
    import re
    # Look for patterns like "90H", "40W", "60D", "90 inches", etc.
    dimension_patterns = [
        r'\d+\s*(?:inch|in|"|\')*\s*(?:H|high|height)',
        r'\d+\s*(?:inch|in|"|\')*\s*(?:W|wide|width)',
        r'\d+\s*(?:inch|in|"|\')*\s*(?:D|deep|depth)',
        r'\d+H\s*x\s*\d+W\s*x\s*\d+D',
        r'\d+\s*x\s*\d+\s*x\s*\d+'
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in dimension_patterns)

def generate_embedding(text):
    """Generate embedding for search query"""
    try:
        response = openai.Embedding.create(
            input=text,
            engine=AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS
        )
        return response['data'][0]['embedding']
    except Exception as e:
        st.error(f"Error generating embedding: {e}")
        return None

def search_quotes(query, top_k=5):
    """Search for similar quotes"""
    embedding = generate_embedding(query)
    if not embedding:
        return []
    
    try:
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector"
        )
        
        results = st.session_state.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["quote_number", "customer_name", "project_title", "quote_date", 
                   "dimensions_text", "voltage", "amperage", "modules_summary", "full_content"],
            top=top_k
        )
        return list(results)
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def display_bom_card(bom_data):
    """Display Module 1 BOM in a beautiful card"""
    if not bom_data or 'bom' not in bom_data or not bom_data['bom']:
        return
    
    bom = bom_data['bom']
    status = bom_data['status']
    
    # Status badge
    if status == 'exact_match':
        badge_html = '<span class="status-exact">✅ Exact Match</span>'
    elif status == 'ambiguous':
        badge_html = '<span class="status-ambiguous">⚠️ Multiple Matches</span>'
    else:
        badge_html = '<span class="status-nomatch">❌ No Match</span>'
    
    st.markdown(f"""
    <div class="bom-card">
        <div class="bom-header">
            <div class="bom-title">🔧 Module 1 BOM</div>
            {badge_html}
        </div>
        <div class="bom-assembly">Assembly: {bom['assembly_number']}</div>
        <div style="color: #b0b0b0; margin-top: 0.5rem;">{bom['project']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Specifications
    specs = bom['specifications']
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**Dimensions**")
        st.code(f"{specs['height']}\"H x {specs['width']}\"W x {specs['depth']}\"D")
    
    with col2:
        st.markdown("**Breaker**")
        st.code(f"{specs['breaker_type']}")
    
    with col3:
        st.markdown("**Mount**")
        st.code(specs['mount'])
    
    with col4:
        st.markdown("**Access**")
        st.code(specs['access'])
    
    st.markdown(f"**Total Components:** `{bom['total_parts']} parts`")
    
    # Components list
    with st.expander(f"📋 View all {bom['total_parts']} components", expanded=False):
        for i, comp in enumerate(bom['components'], 1):
            st.markdown(f"""
            <div class="component-item">
                <span style="color: #b0b0b0; font-size: 0.85rem;">#{i}</span>
                <span class="component-number">{comp['part_number']}</span>
                <span style="color: #b0b0b0; margin-left: 1rem;">Qty: {comp['quantity']}</span>
                <div style="color: #b0b0b0; font-size: 0.85rem; margin-top: 0.25rem;">{comp['description'][:80]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Export button
    if st.button("📥 Export BOM to JSON", key=f"export_{bom['assembly_number']}"):
        json_str = json.dumps(bom, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"{bom['assembly_number']}_BOM.json",
            mime="application/json"
        )

def display_quote_card(quote, score):
    """Display a quote card using native Streamlit components"""
    quote_num = quote.get('quote_number', 'N/A')
    voltage = quote.get('voltage', 'N/A')
    amperage = quote.get('amperage', 'N/A')
    dimensions = quote.get('dimensions_text', 'N/A')
    date = quote.get('quote_date', 'N/A')
    modules = quote.get('modules_summary', 'N/A')
    
    with st.expander(f"**{quote_num}** — {int(score * 100)}% match", expanded=True):
        st.caption(modules)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Voltage**")
            st.markdown(f"`{voltage}`")
        
        with col2:
            st.markdown("**Amperage**")
            st.markdown(f"`{amperage}`")
        
        with col3:
            st.markdown("**Date**")
            st.markdown(f"`{date}`")
        
        if dimensions and dimensions != 'N/A':
            st.markdown("**Dimensions**")
            dims_list = dimensions.split(" | ")
            for dim in dims_list:
                st.markdown(f"- {dim}")
        
        st.markdown("")

def generate_response(query, search_results):
    """Generate AI response based on search results"""
    if not search_results:
        return "I couldn't find any quotes matching those specifications. Try different voltage, amperage, or broader search terms."
    
    context = "\n\n".join([
        f"Quote {r.get('quote_number')}: {r.get('voltage')}, {r.get('amperage')}\n"
        f"Dimensions: {r.get('dimensions_text')}\n"
        f"Details: {r.get('modules_summary')}"
        for r in search_results[:3]
    ])
    
    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for SAI Advanced Power Solutions. Help users find relevant switchgear quotes. Be concise and highlight key specs."},
                {"role": "user", "content": f"Based on these quotes:\n\n{context}\n\nAnswer: {query}"}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except:
        return f"I found {len(search_results)} similar quotes based on your search."

# Header
module1_badge = '<span class="module1-badge">+ Module 1</span>' if MODULE1_AVAILABLE else ''
st.markdown(f"""
<div class="main-header">
    <h1>SAI Quote Search{module1_badge}</h1>
    <p>Find similar switchgear quotes and generate Module 1 BOMs using AI</p>
</div>
""", unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Search quotes or generate Module 1 BOM... (e.g., '90H x 40W x 60D, Emax 6.2')")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Detect if this is a Module 1 query
    is_module1 = is_module1_query(user_input) or detect_dimensions_in_query(user_input)
    
    if is_module1 and MODULE1_AVAILABLE:
        # Module 1 matching
        with st.spinner("Matching to Module 1 assembly..."):
            module1_result = match_from_user_input(user_input)
            
            response_text = module1_result['message']
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "module1_result": module1_result,
                "type": "module1"
            })
    else:
        # Regular quote search
        with st.spinner("Searching quotes..."):
            results = search_quotes(user_input)
            ai_response = generate_response(user_input, results)
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": ai_response,
            "results": results,
            "type": "search"
        })

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Display results based on type
        if message.get("type") == "module1" and "module1_result" in message:
            display_bom_card(message["module1_result"])
        
        elif message.get("type") == "search" and "results" in message and message["results"]:
            for result in message["results"]:
                display_quote_card(result, result.get('@search.score', 0.8))

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.get('current_user', 'User')}")
    
    if st.button("🚪 Sign out"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()
    
    st.markdown("---")
    
    # Module 1 Quick Access
    if MODULE1_AVAILABLE:
        st.markdown("### 🔧 Module 1 BOM")
        st.caption("Generate BOMs for box assemblies")
        
        # Quick examples
        with st.expander("💡 Example queries"):
            st.code("90H x 40W x 60D, Emax 6.2")
            st.code("90 high, 30 wide, 48 deep, Emax 2.2, drawout")
            st.code("78H x 42W x 33D, Square D")
        
        # List assemblies button
        if st.button("📋 List All Assemblies", use_container_width=True):
            matcher = get_matcher()
            st.markdown("#### Available Assemblies:")
            for asm_num in matcher.assembly_specs.keys():
                specs = matcher.assembly_specs[asm_num]
                st.caption(f"**{asm_num}**")
                st.caption(f"{specs['height']}\"H x {specs['width']}\"W x {specs['depth']}\"D")
                st.markdown("")
        
        st.markdown("---")
    
    # File upload section
    st.markdown("### 📤 Upload New Quote")
    uploaded_file = st.file_uploader(
        "Drop PDF here",
        type=['pdf'],
        help="Upload a quote PDF to process"
    )
    
    if uploaded_file is not None:
        if st.button("Upload & Process", use_container_width=True):
            with st.spinner("Uploading..."):
                try:
                    from azure.storage.blob import BlobServiceClient
                    
                    STORAGE_CONNECTION_STRING = st.secrets.get("STORAGE_CONNECTION_STRING", "")
                    
                    if STORAGE_CONNECTION_STRING:
                        blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
                        raw_container = blob_service.get_container_client("raw")
                        
                        blob_client = raw_container.get_blob_client(uploaded_file.name)
                        blob_client.upload_blob(uploaded_file.getvalue(), overwrite=True)
                        
                        st.success(f"✅ Uploaded: {uploaded_file.name}")
                        st.info("File is being processed. Check back in 2-3 minutes.")
                    else:
                        st.error("❌ Storage not configured")
                        
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
    
    st.markdown("---")
    st.markdown("### 📊 Stats")
    st.caption(f"{len(st.session_state.messages)} messages")
    
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.caption("SAI Advanced Power Solutions")
    st.caption("Quote Search + Module 1 v2.1")
