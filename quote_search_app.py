"""
SAI Quote Search - Claude-style Interface
Beautiful light mode with blue accents - SECURE VERSION
"""
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
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

# Custom CSS - Claude-style with blue
st.markdown("""
<style>
    /* Main background - light cream like Claude */
    .stApp {
        background-color: #F7F5F2;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom header */
    .custom-header {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        padding: 1.5rem 2rem;
        border-radius: 0.75rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.1);
    }
    
    .custom-header h1 {
        color: white;
        margin: 0;
        font-size: 1.875rem;
        font-weight: 600;
        letter-spacing: -0.025em;
    }
    
    .custom-header p {
        color: #DBEAFE;
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
    }
    
    /* Search box */
    .stTextInput > div > div > input {
        border-radius: 0.75rem;
        border: 2px solid #E5E7EB;
        padding: 0.875rem 1rem;
        font-size: 1rem;
        background: white;
        transition: all 0.2s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #2563EB;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    
    /* Message bubbles - user (blue) */
    .user-message {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        padding: 1rem 1.25rem;
        border-radius: 1rem;
        margin: 1rem 0;
        margin-left: 20%;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
    }
    
    /* Message bubbles - assistant (white) */
    .assistant-message {
        background: white;
        color: #1F2937;
        padding: 1.25rem 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        margin-right: 20%;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    /* Quote cards */
    .quote-card {
        background: white;
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.2s;
    }
    
    .quote-card:hover {
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
        border-color: #2563EB;
    }
    
    .quote-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #F3F4F6;
    }
    
    .quote-number {
        font-size: 1.125rem;
        font-weight: 600;
        color: #2563EB;
    }
    
    .relevance-badge {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .quote-customer {
        font-size: 1rem;
        color: #6B7280;
        margin-bottom: 0.5rem;
    }
    
    .quote-project {
        font-size: 0.875rem;
        color: #9CA3AF;
    }
    
    .spec-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .spec-item {
        background: #F9FAFB;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border-left: 3px solid #2563EB;
    }
    
    .spec-label {
        font-size: 0.75rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }
    
    .spec-value {
        font-size: 1rem;
        color: #1F2937;
        font-weight: 600;
        margin-top: 0.25rem;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.625rem 1.25rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    
    /* Clean scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #F3F4F6;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2563EB;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #1D4ED8;
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
    <div class="custom-header">
        <h1>🔒 SAI Quote Search - Login</h1>
        <p>Enter your credentials to access the quote search system</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Welcome back!")
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")
        
        if st.button("Login", use_container_width=True):
            if username in AUTHORIZED_USERS and AUTHORIZED_USERS[username] == password:
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
        
        st.markdown("---")
        st.info("🔐 This system is for authorized SAI personnel only")
    
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
        results = st.session_state.search_client.search(
            search_text=query,
            vector_queries=[{
                "vector": embedding,
                "k_nearest_neighbors": top_k,
                "fields": "content_vector"
            }],
            select=["quote_number", "customer_name", "project_title", "quote_date", 
                   "dimensions_text", "voltage", "amperage", "modules_summary", "full_content"],
            top=top_k
        )
        return list(results)
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def display_quote_card(quote, score):
    """Display a quote as a beautiful card"""
    st.markdown(f"""
    <div class="quote-card">
        <div class="quote-header">
            <div>
                <div class="quote-number">{quote.get('quote_number', 'N/A')}</div>
                <div class="quote-customer">{quote.get('customer_name', 'N/A')}</div>
                <div class="quote-project">{quote.get('project_title', 'N/A')}</div>
            </div>
            <div class="relevance-badge">{int(score * 100)}% match</div>
        </div>
        
        <div class="spec-grid">
            <div class="spec-item">
                <div class="spec-label">Voltage</div>
                <div class="spec-value">{quote.get('voltage', 'N/A')}</div>
            </div>
            <div class="spec-item">
                <div class="spec-label">Amperage</div>
                <div class="spec-value">{quote.get('amperage', 'N/A')}</div>
            </div>
            <div class="spec-item">
                <div class="spec-label">Date</div>
                <div class="spec-value">{quote.get('quote_date', 'N/A')}</div>
            </div>
        </div>
        
        <div class="spec-item" style="margin-top: 1rem;">
            <div class="spec-label">Dimensions</div>
            <div class="spec-value">{quote.get('dimensions_text', 'N/A')}</div>
        </div>
        
        {f'<div class="spec-item" style="margin-top: 0.5rem;"><div class="spec-label">Modules</div><div class="spec-value">{quote.get("modules_summary", "N/A")}</div></div>' if quote.get('modules_summary') != 'N/A' else ''}
    </div>
    """, unsafe_allow_html=True)

def generate_response(query, search_results):
    """Generate AI response based on search results"""
    if not search_results:
        return "I couldn't find any similar quotes. Try rephrasing your query or being more specific about dimensions, voltage, or customer requirements."
    
    context = "\n\n".join([
        f"Quote {r.get('quote_number')}: {r.get('customer_name')} - {r.get('project_title')}\n"
        f"Specs: {r.get('voltage')}, {r.get('amperage')}\n"
        f"Dimensions: {r.get('dimensions_text')}"
        for r in search_results[:3]
    ])
    
    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for SAI Advanced Power Solutions. Help users find relevant switchgear quotes based on their requirements. Be concise and highlight key specs."},
                {"role": "user", "content": f"Based on these quotes:\n\n{context}\n\nAnswer this query: {query}"}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except:
        return f"I found {len(search_results)} similar quotes. Here are the most relevant ones:"

# Header
st.markdown("""
<div class="custom-header">
    <h1>SAI Quote Search</h1>
    <p>Find similar switchgear quotes instantly using AI</p>
</div>
""", unsafe_allow_html=True)

# Main chat interface
st.markdown("### 💬 Ask me about quotes")
st.markdown("*Try: 'Show me 480V quotes with NEMA 1 enclosure' or 'Find quotes similar to CF Industries'*")

# Chat input
user_input = st.chat_input("What quotes are you looking for?")

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
        
        # Display quote cards if available
        if "results" in message and message["results"]:
            st.markdown("---")
            for result in message["results"]:
                display_quote_card(result, result.get('@search.score', 0.8))

# Sidebar with filters
with st.sidebar:
    st.markdown(f"### 👤 Logged in as: {st.session_state.get('current_user', 'User')}")
    
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 🔍 Filters")
    st.markdown("*Coming soon: Filter by voltage, customer, date range*")
    
    st.markdown("---")
    st.markdown("### 📊 Stats")
    st.info(f"💬 {len(st.session_state.messages)} messages")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
