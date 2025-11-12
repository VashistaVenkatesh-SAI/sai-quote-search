"""
SAI Module 1 BOM Generator - COMPLETE VERSION
Upload quote PDFs or type specifications for instant BOM generation
Uses Module1_Training_Examples.xlsx for matching
"""
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import pandas as pd
import json
import re
import io

# Module 1 Matcher
try:
    from Module1Matcher import match_from_user_input, get_matcher, match_quote_to_assembly
    MODULE1_AVAILABLE = True
except ImportError:
    MODULE1_AVAILABLE = False

# PDF Processing
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Configuration
SEARCH_ENDPOINT = st.secrets["SEARCH_ENDPOINT"]
SEARCH_KEY = st.secrets["SEARCH_KEY"]
INDEX_NAME = st.secrets["INDEX_NAME"]
AZURE_OPENAI_ENDPOINT = st.secrets["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = st.secrets["AZURE_OPENAI_KEY"]
AZURE_OPENAI_DEPLOYMENT = st.secrets["AZURE_OPENAI_DEPLOYMENT"]
AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS = st.secrets["AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS"]
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

# CSS Styling - Exact Grok Layout
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --grok-bg: #0a0a0a;
        --grok-surface: #1a1a1a;
        --grok-surface-hover: #222222;
        --grok-border: #2a2a2a;
        --grok-text: #ffffff;
        --grok-text-secondary: #6b6b6b;
        --grok-accent: #303030;
    }
    
    /* Global Styles */
    * {
        font-family: 'Corbel', 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stApp {
        background: #0a0a0a !important;
        color: var(--grok-text);
    }
    
    /* Force uniform background */
    .main, .block-container, [data-testid="stAppViewContainer"] {
        background: #0a0a0a !important;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    /* Main Container - Centered like Grok */
    .main .block-container {
        max-width: 900px;
        padding: 1rem 2rem 4rem 2rem;
        margin: 0 auto;
    }
    
    /* Top Left Controls - Extreme top-left like Grok */
    .element-container:has(.top-left-controls) {
        position: fixed !important;
        top: 1rem !important;
        left: 1rem !important;
        z-index: 9999 !important;
        display: flex !important;
        gap: 0.5rem !important;
    }
    
    /* Style for top control buttons */
    div[data-testid="column"]:has(button) {
        min-width: fit-content !important;
    }
    
    /* Logo - Centered at top like Grok */
    .grok-logo {
        text-align: center;
        margin-bottom: 3rem;
    }
    
    .grok-logo h1 {
        color: var(--grok-text);
        margin: 0;
        font-size: 2.5rem;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    .grok-logo-badge {
        color: var(--grok-text-secondary);
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 0.5rem;
    }
    
    /* Search Bar Container - Exactly like Grok */
    .search-container {
        margin: 0 auto 2rem;
        max-width: 700px;
    }
    
    /* Main Search Input - Grok style with high curve */
    .stChatInput {
        margin-bottom: 1rem;
    }
    
    .stChatInput > div {
        background: var(--grok-surface);
        border: 1px solid var(--grok-border);
        border-radius: 30px !important;
        padding: 0.25rem 0.5rem;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: var(--grok-text) !important;
        padding: 1rem 1.5rem !important;
        font-size: 1rem !important;
        min-height: 50px !important;
    }
    
    .stChatInput textarea::placeholder {
        color: var(--grok-text-secondary) !important;
    }
    
    /* Action Buttons Below Search - Like Grok's DeepSearch, Pick Personas, Voice */
    .search-actions {
        display: flex;
        justify-content: center;
        gap: 0.75rem;
        margin-top: 1rem;
    }
    
    .search-action-btn {
        background: var(--grok-surface);
        border: 1px solid var(--grok-border);
        color: var(--grok-text-secondary);
        padding: 0.625rem 1.25rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .search-action-btn:hover {
        background: var(--grok-surface-hover);
        color: var(--grok-text);
        border-color: #404040;
    }
    
    /* Chat Messages - Monotone */
    .user-message {
        background: var(--grok-surface);
        border: 1px solid var(--grok-border);
        color: var(--grok-text);
        padding: 1rem 1.5rem;
        border-radius: 20px;
        margin: 1.5rem auto;
        margin-left: auto;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .assistant-message {
        background: var(--grok-surface);
        border: 1px solid var(--grok-border);
        color: var(--grok-text);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        margin: 1.5rem auto;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.7;
    }
    
    /* BOM Card - Monotone */
    .bom-card {
        background: var(--grok-surface);
        border: 1px solid var(--grok-border);
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem auto;
        max-width: 100%;
    }
    
    .bom-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--grok-border);
    }
    
    .bom-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--grok-text);
        letter-spacing: -0.01em;
    }
    
    .status-badge {
        background: var(--grok-accent);
        color: var(--grok-text);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Component Items - Monotone */
    .component-item {
        background: transparent;
        border: 1px solid var(--grok-border);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 0.75rem 0;
        transition: all 0.2s ease;
    }
    
    .component-item:hover {
        background: var(--grok-surface-hover);
        border-color: #404040;
    }
    
    .component-number {
        font-family: 'Courier New', monospace;
        color: var(--grok-text);
        font-weight: 500;
        font-size: 0.95rem;
    }
    
    /* Buttons - Monotone Grok style */
    .stButton > button {
        background: var(--grok-surface);
        color: var(--grok-text);
        border: 1px solid var(--grok-border);
        border-radius: 20px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: var(--grok-surface-hover);
        border-color: #404040;
        transform: translateY(-1px);
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: var(--grok-surface);
        color: var(--grok-text);
        border: 1px solid var(--grok-border);
        border-radius: 20px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
    }
    
    .stDownloadButton > button:hover {
        background: var(--grok-surface-hover);
        border-color: #404040;
    }
    
    /* File Uploader - Monotone and compact */
    .stFileUploader {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }
    
    .stFileUploader > div {
        background: var(--grok-surface) !important;
        border: 1px solid var(--grok-border) !important;
        border-radius: 20px !important;
        padding: 0.625rem 1.25rem !important;
    }
    
    .stFileUploader label {
        color: var(--grok-text-secondary) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
    }
    
    .stFileUploader:hover > div {
        border-color: #404040 !important;
        background: var(--grok-surface-hover) !important;
    }
    
    /* Make all column buttons compact */
    div[data-testid="column"] .stButton > button {
        padding: 0.625rem 1rem !important;
        border-radius: 20px !important;
        font-size: 0.875rem !important;
        min-width: fit-content !important;
    }
    
    /* Metrics - Monotone */
    .stMetric {
        background: transparent;
        border: 1px solid var(--grok-border);
        border-radius: 12px;
        padding: 1rem;
    }
    
    .stMetric label {
        color: var(--grok-text-secondary) !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: var(--grok-text) !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }
    
    /* Expander - Monotone */
    .streamlit-expanderHeader {
        background: transparent;
        border: 1px solid var(--grok-border);
        border-radius: 12px;
        color: var(--grok-text) !important;
        font-weight: 500;
    }
    
    .streamlit-expanderHeader:hover {
        background: var(--grok-surface-hover);
        border-color: #404040;
    }
    
    /* Info/Success/Warning Boxes - Monotone */
    .stAlert {
        background: var(--grok-surface);
        border: 1px solid var(--grok-border);
        border-radius: 12px;
        color: var(--grok-text);
    }
    
    /* Scrollbar - Minimal */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--grok-border);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #404040;
    }
    
    /* Code Blocks - Monotone */
    code {
        background: var(--grok-surface) !important;
        border: 1px solid var(--grok-border) !important;
        color: var(--grok-text) !important;
        padding: 0.25rem 0.5rem !important;
        border-radius: 6px !important;
        font-family: 'Courier New', monospace !important;
    }
    
    /* Dividers */
    hr {
        border-color: var(--grok-border);
        margin: 2rem 0;
        opacity: 0.5;
    }
    
    /* Footer - Minimal like Grok */
    .footer-text {
        text-align: center;
        color: var(--grok-text-secondary);
        font-size: 0.75rem;
        margin-top: 4rem;
        padding: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_training_examples():
    """Load training examples from Excel"""
    try:
        df = pd.read_excel('Module1_Training_Examples.xlsx', sheet_name='Examples')
        
        # Convert to dictionary grouped by assembly
        examples_dict = {}
        for _, row in df.iterrows():
            assembly = row['Assembly_Number']
            example = row['Example_Quote_Snippet']
            
            if assembly not in examples_dict:
                examples_dict[assembly] = []
            examples_dict[assembly].append(example)
        
        # Create formatted text for AI with ALL examples
        examples_text = "MODULE 1 TRAINING EXAMPLES:\n\n"
        for assembly, examples in sorted(examples_dict.items()):
            examples_text += f"Assembly {assembly}:\n"
            for i, example in enumerate(examples, 1):
                examples_text += f"  Example {i}: \"{example}\"\n"
            examples_text += "\n"
        
        return examples_text, examples_dict
        
    except Exception as e:
        st.error(f"⚠️ Could not load training examples: {e}")
        return None, None

def check_password():
    """Authentication"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    st.markdown("""
    <div class="grok-header">
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
    """Extract text from PDF"""
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
    """Extract specifications and match to examples from Excel"""
    
    # Load training examples from Excel
    examples_text, examples_dict = load_training_examples()
    
    if not examples_text:
        st.warning("⚠️ Reference data not available - using fallback")
        examples_text = """10 assemblies available:
123456-0100-101: 90H x 40W x 60D, Emax 6.2
123456-0100-102: 90H x 40W x 60D, (3) Emax 2.2
123456-0100-103: 90H x 40W x 60D, (2) Emax 2.2
123456-0100-201: 90H x 40W x 60D, Emax 6.2, Drawout
123456-0100-202: 90H x 40W x 60D, Emax 2.2, Drawout
123456-0100-203: 90H x 40W x 60D, (2) Emax 2.2, Drawout
123456-0100-204: 90H x 42W x 60D, Tmax
123456-0100-301: 90H x 30W x 48D, Emax 2.2
123456-0100-302: 90H x 42W x 48D, Tmax
123456-0100-401: 78H x 42W x 33D, Square D"""
    else:
        st.success("✅ Loaded assembly reference data")

    system_prompt = f"""You are an expert at identifying Module 1 switchgear assemblies from quotes.

ASSEMBLY REFERENCE DATA:
{examples_text}

YOUR TASK:
1. Read the quote and identify ALL sections
2. For EACH section, extract specifications and calculate match quality
3. Calculate a match percentage (0-100%) based on how well specs align
4. If match is below 40%, suggest 2-3 closest assemblies instead

MATCH PERCENTAGE CALCULATION:
- Dimensions match exactly: +25% each (Height, Width, Depth = 75% total)
- Breaker type matches: +15%
- Breaker quantity matches: +10%
- 100% = perfect match, 75-99% = good match, 40-74% = partial match, <40% = no match

For each section, explain like this:

HIGH CONFIDENCE (≥75%):
"Section [X] matches Assembly [NUMBER] (XX% match):

Quote specifications:
- Dimensions: [what you found]
- Breaker: [what you found]
- Mount: [what you found]
- Access: [what you found]

This matches Assembly [NUMBER] which has these exact specifications."

LOW CONFIDENCE (<40%):
"Section [X] has no exact match (<40% confidence):

Quote specifications:
- Dimensions: [what you found]
- Breaker: [what you found]

Closest assemblies:
1. Assembly [NUMBER]: [specs] (XX% match - different [feature])
2. Assembly [NUMBER]: [specs] (XX% match - different [feature])
3. Assembly [NUMBER]: [specs] (XX% match - different [feature])"

CRITICAL: Extract ALL sections from the quote. Most quotes have multiple sections (Section 101, 102, 103, etc.)

Return JSON with ALL sections:
{{
  "sections": [
    {{
      "identifier": "Section 101",
      "dimensions": {{"height": "90", "width": "40", "depth": "60"}},
      "main_circuit_breaker": {{"type": "ABB SACE Emax 6.2", "quantity": 1}},
      "special_requirements": ["fixed mount", "front and rear access"],
      "matched_assembly": "123456-0100-101",
      "match_percentage": 100,
      "reasoning": "Section 101 has 90H x 40W x 60D dimensions with an Emax 6.2 breaker. This matches Assembly 123456-0100-101 perfectly."
    }},
    {{
      "identifier": "Section 104",
      "dimensions": {{"height": "90", "width": "50", "depth": "70"}},
      "main_circuit_breaker": {{"type": "Square D", "quantity": 1}},
      "special_requirements": [],
      "matched_assembly": null,
      "match_percentage": 35,
      "suggested_assemblies": [
        {{"assembly": "123456-0100-401", "reason": "Closest dimensions (78H x 42W x 33D)", "match_pct": 35}},
        {{"assembly": "123456-0100-302", "reason": "Similar width (42W)", "match_pct": 30}}
      ],
      "reasoning": "Section 104 has no exact match. The dimensions 90H x 50W x 70D don't match any available assembly. Closest option is Assembly 401 with 78H x 42W x 33D."
    }}
  ]
}}

IMPORTANT: 
- Calculate match_percentage accurately (0-100)
- If match_percentage < 40, set matched_assembly to null and provide suggested_assemblies
- Always include reasoning that explains the match quality"""

    user_prompt = f"""Analyze this quote and identify ALL sections. For each section, determine which assembly it matches and explain why.

Quote:
{text[:15000]}

Return complete JSON with all sections and natural explanations."""
    
    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=4000,
            timeout=40
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

def display_bom_card(bom_data, unique_id=None):
    """Display Module 1 BOM card with match explanations and match percentage"""
    
    status = bom_data.get('status')
    matched_assemblies = bom_data.get('matched_assemblies', [])
    extracted_features = bom_data.get('extracted_features', {})
    match_percentage = bom_data.get('match_percentage', None)  # NEW: Get match %
    
    # Show selection buttons if multiple/no exact match
    if status in ['ambiguous', 'no_match'] and matched_assemblies:
        # Show detected specs
        st.markdown("### 📋 Detected Specifications:")
        det_col1, det_col2, det_col3, det_col4 = st.columns(4)
        with det_col1:
            st.metric("Height", f"{extracted_features.get('height', '?')}\"")
        with det_col2:
            st.metric("Width", f"{extracted_features.get('width', '?')}\"")
        with det_col3:
            st.metric("Depth", f"{extracted_features.get('depth', '?')}\"")
        with det_col4:
            breaker = extracted_features.get('breaker_type', 'Not specified')
            st.metric("Breaker", breaker[:20] if len(breaker) > 20 else breaker)
        
        st.markdown("---")
        
        matcher = get_matcher()
        
        # Pre-filter: Calculate match scores and filter out <50%
        assemblies_with_scores = []
        for assembly_num in matched_assemblies:
            specs = matcher.assembly_specs[assembly_num]
            
            match_score = 0
            total_possible = 4
            
            if extracted_features.get('height') == specs['height']:
                match_score += 1
            if extracted_features.get('width') == specs['width']:
                match_score += 1
            if extracted_features.get('depth') == specs['depth']:
                match_score += 1
            
            if extracted_features.get('breaker_type'):
                breaker_match = extracted_features['breaker_type'].upper() in specs['breaker_type'].upper() or specs['breaker_type'].upper() in extracted_features['breaker_type'].upper()
                if breaker_match:
                    match_score += 1
            
            match_pct = int((match_score / total_possible) * 100)
            
            # Only include if 50% or higher
            if match_pct >= 50:
                assemblies_with_scores.append((assembly_num, match_pct, specs))
        
        # Sort by match percentage (highest first)
        assemblies_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        if not assemblies_with_scores:
            st.error("❌ No assemblies match at 50% or higher. Please check specifications.")
            return
        
        st.markdown(f"### 🔍 Select an assembly ({len(assemblies_with_scores)} matches ≥50%):")
        
        num_assemblies = min(len(assemblies_with_scores), 9)
        cols_per_row = 3
        
        for i in range(0, num_assemblies, cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < num_assemblies:
                    assembly_num, match_pct, specs = assemblies_with_scores[idx]
                    
                    with cols[j]:
                        # Button
                        if st.button(f"**{assembly_num}**\n{match_pct}% Match", key=f"select_{assembly_num}_{idx}", use_container_width=True):
                            selected_bom = matcher.generate_bom(assembly_num)
                            
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Show BOM for {assembly_num}"
                            })
                            
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"✅ Showing BOM for Assembly {assembly_num}",
                                "module1_result": {
                                    'status': 'exact_match',
                                    'bom': selected_bom,
                                    'message': f"✅ BOM for {assembly_num}"
                                },
                                "type": "module1"
                            })
                            
                            st.rerun()
                        
                        # Match details
                        height_match = extracted_features.get('height') == specs['height']
                        width_match = extracted_features.get('width') == specs['width']
                        depth_match = extracted_features.get('depth') == specs['depth']
                        breaker_match = False
                        if extracted_features.get('breaker_type'):
                            breaker_match = extracted_features['breaker_type'].upper() in specs['breaker_type'].upper() or specs['breaker_type'].upper() in extracted_features['breaker_type'].upper()
                        
                        st.caption("**Match Details:**")
                        st.caption(f"{'✅' if height_match else '❌'} Height: {specs['height']}\"")
                        st.caption(f"{'✅' if width_match else '❌'} Width: {specs['width']}\"")
                        st.caption(f"{'✅' if depth_match else '❌'} Depth: {specs['depth']}\"")
                        st.caption(f"{'✅' if breaker_match else '❌'} Breaker: {specs['breaker_type'][:20]}...")
                        st.caption(f"Mount: {specs['mount']}")
                        st.caption(f"Access: {specs['access']}")
        
        return  # Exit early
    
    # Show BOM card for exact match
    if not bom_data or 'bom' not in bom_data or not bom_data['bom']:
        return
    
    bom = bom_data['bom']
    
    # Create badge with match percentage if available
    if match_percentage is not None:
        badge_html = f'<span class="status-badge">✓ {match_percentage}% Match</span>'
    else:
        badge_html = '<span class="status-badge">✓ Matched</span>'
    
    st.markdown(f"""
    <div class="bom-card">
        <div class="bom-header">
            <div class="bom-title">🔧 Module 1 BOM</div>
            {badge_html}
        </div>
        <div style="font-size: 1.125rem; color: #e8e8e8; font-weight: 600;">
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
    
    # Export to CSV
    export_key = f"export_{bom['assembly_number']}" if not unique_id else f"export_{unique_id}"
    download_key = f"download_{bom['assembly_number']}" if not unique_id else f"download_{unique_id}"
    
    if st.button("📥 Export BOM to CSV", key=export_key):
        csv_buffer = io.StringIO()
        csv_buffer.write("Item,Part Number,Description,Quantity\n")
        
        for i, comp in enumerate(bom['components'], 1):
            part_num = comp['part_number'].replace(',', ';')
            desc = comp.get('description', '').replace(',', ';').replace('\n', ' ')
            qty = comp['quantity']
            csv_buffer.write(f"{i},{part_num},{desc},{qty}\n")
        
        csv_str = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download CSV",
            data=csv_str,
            file_name=f"{bom['assembly_number']}_BOM.csv",
            mime="text/csv",
            key=download_key
        )

# Top Left Controls - Fixed position like Grok
st.markdown('<div class="top-left-controls"></div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([0.7, 0.7, 0.8])
with col1:
    if st.button("👤", key="signout_top", help="Sign out"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()
with col2:
    if st.button("🗑️", key="clear_top", help="Clear chat"):
        st.session_state.messages = []
        st.rerun()
with col3:
    msg_count = len(st.session_state.messages)
    st.button(f"📊 {msg_count}", key="stats_top", disabled=True, help="Message count")

st.markdown("<div style='height: 5rem;'></div>", unsafe_allow_html=True)

# Centered Logo - Grok style
st.markdown("""
<div class="grok-logo">
    <h1>SAI Module 1</h1>
    <div class="grok-logo-badge">BOM Generator</div>
</div>
""", unsafe_allow_html=True)

# Chat input - main search bar
user_input = st.chat_input("What do you want to know?")

# Action buttons directly below search - integrated like Grok's DeepSearch/Voice buttons
col1, col2, col3, col4 = st.columns([1, 1, 1, 4])

with col1:
    if MODULE1_AVAILABLE and PDF_AVAILABLE:
        uploaded_pdf = st.file_uploader(
            "📁 Browse Files",
            type=['pdf'],
            key="pdf_uploader",
            label_visibility="visible"
        )
        
with col2:
    if MODULE1_AVAILABLE:
        if st.button("📋 List Assemblies", key="list_asm"):
            matcher = get_matcher()
            assembly_list = "**Available Module 1 Assemblies:**\n\n"
            for asm_num in sorted(matcher.assembly_specs.keys()):
                specs = matcher.assembly_specs[asm_num]
                assembly_list += f"**{asm_num}**: {specs['height']}\"H × {specs['width']}\"W × {specs['depth']}\"D - {specs['breaker_type']}\n\n"
            
            st.session_state.messages.append({"role": "user", "content": "List all assemblies"})
            st.session_state.messages.append({"role": "assistant", "content": assembly_list, "type": "text"})
            st.rerun()

with col3:
    # Generate BOM button appears when file is uploaded
    if 'uploaded_pdf' in locals() and uploaded_pdf is not None:
        if st.button("🔧 Generate", key="gen_bom"):
            # Trigger PDF processing
            st.session_state.trigger_pdf_process = True
            st.session_state.current_pdf = uploaded_pdf
            st.rerun()

st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

# Process PDF if triggered
if hasattr(st.session_state, 'trigger_pdf_process') and st.session_state.trigger_pdf_process:
    pdf_to_process = st.session_state.current_pdf
    st.session_state.trigger_pdf_process = False  # Reset trigger
    
    with st.spinner("📄 Reading PDF..."):
        text = extract_text_from_pdf(pdf_to_process)
        
        if text:
            with st.spinner("🤖 Analyzing sections..."):
                specs_json = extract_specs_from_text(text)
                
                if specs_json and 'sections' in specs_json:
                    # Process each section
                    all_boms = []
                    no_match_sections = []
                    
                    for section in specs_json['sections']:
                        section_id = section.get('identifier', 'Unknown')
                        matched_assembly = section.get('matched_assembly', None)
                        match_pct = section.get('match_percentage', 0)
                        reasoning = section.get('reasoning', '')
                        suggested = section.get('suggested_assemblies', [])
                        
                        if matched_assembly and match_pct >= 40:
                            try:
                                matcher = get_matcher()
                                section_bom = matcher.generate_bom(matched_assembly)
                                all_boms.append({
                                    'section_id': section_id,
                                    'assembly': matched_assembly,
                                    'bom': section_bom,
                                    'reasoning': reasoning,
                                    'match_percentage': match_pct
                                })
                            except Exception as e:
                                st.warning(f"⚠️ Error for {section_id}: {e}")
                        else:
                            no_match_sections.append({
                                'section_id': section_id,
                                'reasoning': reasoning,
                                'match_percentage': match_pct,
                                'suggested': suggested
                            })
                    
                    # Create messages
                    summary = f"📄 {pdf_to_process.name}\n\n"
                    if all_boms:
                        summary += f"✅ {len(all_boms)} section(s) matched\n"
                    if no_match_sections:
                        summary += f"⚠️ {len(no_match_sections)} section(s) with no match\n"
                    
                    st.session_state.messages.append({"role": "user", "content": summary})
                    
                    full_message = ""
                    if all_boms:
                        for bom in all_boms:
                            full_message += f"**{bom['section_id']}** → {bom['assembly']} ({bom['match_percentage']}%)\n\n"
                    if no_match_sections:
                        for nm in no_match_sections:
                            full_message += f"⚠️ **{nm['section_id']}** ({nm['match_percentage']}%)\n{nm['reasoning']}\n\n"
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_message,
                        "all_boms": all_boms,
                        "no_match_sections": no_match_sections,
                        "type": "multi_bom"
                    })
                    
                    st.rerun()
                else:
                    st.error("❌ Could not extract sections")
        else:
            st.error("❌ Could not read PDF")



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
            "content": "Module 1 matching not available.",
            "type": "error"
        })

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Handle single BOM
        if message.get("type") == "module1" and "module1_result" in message:
            display_bom_card(message["module1_result"])
        
        # Handle multiple BOMs (multi-section quotes)
        elif message.get("type") == "multi_bom":
            # Display matched BOMs
            if "all_boms" in message and message["all_boms"]:
                for idx, bom_data in enumerate(message["all_boms"]):
                    st.markdown(f"### 📦 {bom_data['section_id']}")
                    
                    # Create module1_result format for display with unique ID
                    module1_result = {
                        'status': 'exact_match',
                        'bom': bom_data['bom'],
                        'message': f"✅ {bom_data['section_id']}: Assembly {bom_data['assembly']}",
                        'match_percentage': bom_data.get('match_percentage', None)
                    }
                    
                    # Pass unique ID to avoid duplicate widget keys
                    unique_id = f"{bom_data['section_id']}_{bom_data['assembly']}_{idx}"
                    display_bom_card(module1_result, unique_id=unique_id)
                    st.markdown("---")
            
            # Display no-match sections with suggestions
            if "no_match_sections" in message and message["no_match_sections"]:
                st.markdown("### ⚠️ Sections Without Exact Match")
                
                for no_match in message["no_match_sections"]:
                    st.markdown(f"""
                    <div style="background: #2d2d2d; border: 2px solid #EF4444; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
                        <div style="font-size: 1.125rem; font-weight: 600; color: #EF4444; margin-bottom: 0.5rem;">
                            🔍 {no_match['section_id']}
                        </div>
                        <div style="color: #b0b0b0; margin-bottom: 1rem;">
                            Match Confidence: {no_match['match_percentage']}% (Below 40% threshold)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if no_match.get('suggested'):
                        st.markdown("**💡 Suggested Alternatives:**")
                        
                        for sugg in no_match['suggested'][:3]:
                            assembly_num = sugg['assembly']
                            reason = sugg['reason']
                            sugg_pct = sugg.get('match_pct', 0)
                            
                            st.markdown(f"""
                            <div style="background: #2d2d2d; border-left: 3px solid #F59E0B; padding: 1rem; margin: 0.5rem 0; border-radius: 6px;">
                                <div style="font-weight: 600; color: #F59E0B;">Assembly {assembly_num} ({sugg_pct}% match)</div>
                                <div style="color: #b0b0b0; font-size: 0.9rem; margin-top: 0.25rem;">{reason}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("---")

# Footer
st.markdown("""
<div class="footer-text">
    SAI Advanced Power Solutions • Module 1 BOM Generator v1.2
</div>
""", unsafe_allow_html=True)
