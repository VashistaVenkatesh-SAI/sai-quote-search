"""
SAI Quote Search - Claude Dark Mode Interface
Exact replica of Claude.ai's beautiful dark design
"""
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import json

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
    page_title="SAI Quote Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS - Claude Dark Mode
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
        background: #000000;
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
    
    .quote-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #404040;
    }
    
    .quote-number {
        font-size: 1.125rem;
        font-weight: 600;
        color: #2563EB;
    }
    
    .quote-subtitle {
        font-size: 0.875rem;
        color: #b0b0b0;
        margin-top: 0.25rem;
    }
    
    .match-badge {
        background: #2563EB;
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
    
    /* Divider */
    hr {
        border-color: #404040;
        margin: 1.5rem 0;
    }
    
    /* Info boxes */
    .stInfo {
        background: #2d2d2d !important;
        border: 1px solid #404040 !important;
        color: #e8e8e8 !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #2d2d2d;
        border-right: 1px solid #404040;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #e8e8e8;
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
    
    /* Text inputs */
    .stTextInput input {
        background: #2d2d2d !important;
        border: 1px solid #404040 !important;
        color: #e8e8e8 !important;
        border-radius: 8px;
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
        <h1>🔒 SAI Quote Search</h1>
        <p>Sign in to access the quote search system</p>
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
                st.success("✅ Signed in successfully")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
        
        st.markdown("---")
        st.caption("🔐 For authorized SAI personnel only")
    
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

# Check authentication first
if not check_password():
    st.stop()

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

def display_quote_card(quote, score):
    """Display a quote card in dark mode"""
    quote_num = quote.get('quote_number', 'N/A')
    voltage = quote.get('voltage', 'N/A')
    amperage = quote.get('amperage', 'N/A')
    dimensions = quote.get('dimensions_text', 'N/A')
    date = quote.get('quote_date', 'N/A')
    modules = quote.get('modules_summary', 'N/A')
    
    st.markdown(f"""
    <div class="quote-card">
        <div class="quote-header">
            <div>
                <div class="quote-number">📋 {quote_num}</div>
                <div class="quote-subtitle">{modules}</div>
            </div>
            <div class="match-badge">{int(score * 100)}% match</div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin-bottom: 1rem;">
            <div>
                <div class="spec-label">⚡ Voltage</div>
                <div class="spec-value">{voltage}</div>
            </div>
            <div>
                <div class="spec-label">🔌 Amperage</div>
                <div class="spec-value">{amperage}</div>
            </div>
            <div>
                <div class="spec-label">📅 Date</div>
                <div class="spec-value">{date}</div>
            </div>
        </div>
        
        {f'<div><div class="spec-label">📏 Dimensions</div><div class="spec-value" style="font-size: 0.9rem; margin-top: 0.5rem;">{dimensions}</div></div>' if dimensions != 'N/A' else ''}
    </div>
    """, unsafe_allow_html=True)

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
st.markdown("""
<div class="main-header">
    <h1>SAI Quote Search</h1>
    <p>Find similar switchgear quotes using AI-powered search</p>
</div>
""", unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Search for quotes... (e.g., '480V NEMA 1' or '90 inch height')")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Search
    with st.spinner("Searching quotes..."):
        results = search_quotes(user_input)
        ai_response = generate_response(user_input, results)
    
    # Add assistant response
    st.session_state.messages.append({
        "role": "assistant", 
        "content": ai_response,
        "results": results
    })

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Display quote cards
        if "results" in message and message["results"]:
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
    st.markdown("### 📊 Stats")
    st.caption(f"💬 {len(st.session_state.messages)} messages in this session")
    
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.caption("SAI Advanced Power Solutions")
    st.caption("Quote Search System v2.0")
