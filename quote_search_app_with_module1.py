"""
SAI Quote Search - WITH PDF UPLOAD + INSTANT MODULE 1 BOM
Upload PDF → Extract Specs → Match Assembly → Generate BOM
"""
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import json
import re
from io import BytesIO

# Module 1 Matcher
try:
    from Module1Matcher import match_from_user_input, get_matcher, match_quote_to_assembly
    MODULE1_AVAILABLE = True
except ImportError:
    MODULE1_AVAILABLE = False
    st.error("⚠️ Module1Matcher.py not found. Module 1 matching disabled.")

# PDF Processing
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

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
    page_title="SAI Module 1 BOM Generator",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [KEEPING ALL YOUR EXISTING CSS - Same as before]
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
    
    .stApp {
        background-color: #1e1e1e;
        color: #e8e8e8;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
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
</style>
""", unsafe_allow_html=True)

def check_password():
    """Returns True if user is authenticated"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    st.markdown("""
    <div class="main-header">
        <h1>SAI Module 1 BOM Generator</h1>
        <p>Sign in to access the automated BOM generation system</p>
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

# Check authentication
if not check_password():
    st.stop()

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

def extract_specs_from_text(text):
    """Use Azure OpenAI to extract specifications from quote text"""
    system_prompt = """You are an electrical switchgear specification extractor.

Extract these details from the quote:
- Dimensions (Height x Width x Depth) for each section
- Breaker types and quantities
- Mount type (Fixed or Drawout)
- Access type (Front only or Front and rear)
- NEMA rating
- UL rating

Output as JSON with this structure:
{
  "sections": [
    {
      "identifier": "Section 101",
      "dimensions": {"height": "90", "width": "40", "depth": "60"},
      "main_circuit_breaker": {
        "type": "ABB SACE Emax 6.2",
        "quantity": 1
      }
    }
  ],
  "special_construction_requirements": ["fixed mount", "front and rear access"]
}"""

    user_prompt = f"""Extract specifications from this quote:

{text[:10000]}

Return complete JSON with all technical details."""
    
    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=2000,
            timeout=30
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Clean JSON
        ai_response = ai_response.replace("```json", "").replace("```", "").strip()
        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        if start != -1 and end > start:
            ai_response = ai_response[start:end]
        
        # Remove trailing commas
        for _ in range(5):
            ai_response = re.sub(r',(\s*[}\]])', r'\1', ai_response)
        
        parsed = json.loads(ai_response)
        return parsed
        
    except Exception as e:
        st.error(f"Error extracting specs: {e}")
        return None

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
        <div class="bom-assembly" style="font-size: 1.125rem; color: #e8e8e8; font-weight: 600;">
            Assembly: {bom['assembly_number']}
        </div>
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
                <div style="color: #b0b0b0; font-size: 0.85rem; margin-top: 0.25rem;">{comp.get('description', '')[:80]}</div>
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
    """Display a quote card"""
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

def generate_response(query, search_results):
    """Generate AI response based on search results"""
    if not search_results:
        return "I couldn't find any quotes matching those specifications."
    
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
                {"role": "system", "content": "You are a helpful assistant for SAI Advanced Power Solutions. Help users find relevant switchgear quotes."},
                {"role": "user", "content": f"Based on these quotes:\n\n{context}\n\nAnswer: {query}"}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except:
        return f"I found {len(search_results)} similar quotes."

# Header
module1_badge = '<span class="module1-badge">BOM Generator</span>' if MODULE1_AVAILABLE else ''
st.markdown(f"""
<div class="main-header">
    <h1>SAI Module 1 {module1_badge}</h1>
    <p>Upload quote PDFs or type specifications for instant BOM generation</p>
</div>
""", unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Type specs for Module 1 BOM... (e.g., '90H x 40W x 60D, Emax 6.2')")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    if MODULE1_AVAILABLE:
        with st.spinner("Matching to Module 1 assembly..."):
            module1_result = match_from_user_input(user_input)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": module1_result['message'],
                "module1_result": module1_result,
                "type": "module1"
            })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Module 1 matching is not available. Please check if Module1Matcher.py and Module 1.xlsx are present.",
            "type": "error"
        })

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Only display Module 1 BOM cards
        if message.get("type") == "module1" and "module1_result" in message:
            display_bom_card(message["module1_result"])

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.get('current_user', 'User')}")
    
    if st.button("🚪 Sign out"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()
    
    st.markdown("---")
    
    # PDF UPLOAD FOR MODULE 1
    if MODULE1_AVAILABLE and PDF_AVAILABLE:
        st.markdown("### 📤 Upload Quote PDF")
        st.caption("Get instant Module 1 BOM")
        
        uploaded_pdf = st.file_uploader(
            "Drop quote PDF here",
            type=['pdf'],
            help="Upload quote PDF to automatically generate Module 1 BOM",
            key="pdf_uploader"
        )
        
        if uploaded_pdf is not None:
            if st.button("🔧 Generate BOM", use_container_width=True):
                with st.spinner("📄 Reading PDF..."):
                    # Extract text
                    text = extract_text_from_pdf(uploaded_pdf)
                    
                    if text:
                        with st.spinner("🤖 Extracting specifications..."):
                            # Extract specs
                            specs_json = extract_specs_from_text(text)
                            
                            if specs_json:
                                with st.spinner("🔍 Matching to Module 1..."):
                                    # Match to Module 1
                                    module1_result = match_quote_to_assembly(specs_json)
                                    
                                    # Show extracted features for user
                                    features = module1_result.get('extracted_features', {})
                                    feature_text = f"Detected: {features.get('height', '?')}\"H x {features.get('width', '?')}\"W x {features.get('depth', '?')}\"D"
                                    if features.get('breaker_type'):
                                        feature_text += f", {features['breaker_type']}"
                                    
                                    # Add to messages
                                    st.session_state.messages.append({
                                        "role": "user",
                                        "content": f"📄 {uploaded_pdf.name}\n{feature_text}"
                                    })
                                    
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": module1_result['message'],
                                        "module1_result": module1_result,
                                        "type": "module1"
                                    })
                                    
                                    st.rerun()
                            else:
                                st.error("❌ Could not extract specs from PDF")
                    else:
                        st.error("❌ Could not read PDF")
        
        st.markdown("---")
    
    # Module 1 Quick Access
    if MODULE1_AVAILABLE:
        st.markdown("### 💡 Example Queries")
        
        with st.expander("Try these"):
            if st.button("90H x 40W x 60D, Emax 6.2", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "90H x 40W x 60D, Emax 6.2, fixed, front and rear"
                })
                st.rerun()
            
            if st.button("78H x 42W x 33D, Square D", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "78H x 42W x 33D, Square D"
                })
                st.rerun()
        
        if st.button("📋 List All Assemblies", use_container_width=True):
            matcher = get_matcher()
            st.markdown("#### Available Assemblies:")
            for asm_num in matcher.assembly_specs.keys():
                specs = matcher.assembly_specs[asm_num]
                st.caption(f"**{asm_num}**")
                st.caption(f"{specs['height']}\"H x {specs['width']}\"W x {specs['depth']}\"D")
                st.markdown("")
        
        st.markdown("---")
    
    st.markdown("### 📊 Stats")
    st.caption(f"{len(st.session_state.messages)} messages")
    
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.caption("SAI Advanced Power Solutions")
    st.caption("Module 1 BOM Generator v3.0")
