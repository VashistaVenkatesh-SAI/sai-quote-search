"""
Voltrix BOM Generator v2.0
- JSON Knowledge Base for box selection
- 12 Feature Extraction from quotes
- Order Upload with Persistent Memory (Azure Blob)
"""
import streamlit as st
import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import BlobServiceClient
import pandas as pd
import json
import re
import io
from datetime import datetime

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

# Azure Blob Storage for Persistent Memory
try:
    AZURE_STORAGE_CONNECTION_STRING = st.secrets["AZURE_STORAGE_CONNECTION_STRING"]
    MEMORY_CONTAINER = "persistent-memory"
    MEMORY_BLOB_NAME = "voltrix_memory.json"
    BLOB_AVAILABLE = True
except:
    BLOB_AVAILABLE = False

openai.api_type = "azure"
openai.api_key = AZURE_OPENAI_KEY
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = "2024-02-01"

# ============================================
# KNOWLEDGE BASE FUNCTIONS
# ============================================

@st.cache_data
def load_knowledge_base():
    """Load BoxKnowledge.json for box selection logic"""
    try:
        with open("BoxKnowledge.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning("BoxKnowledge.json not found - using default logic")
        return None
    except Exception as e:
        st.error(f"Error loading knowledge base: {e}")
        return None

def get_dimension_code(dimension_type, value, knowledge_base):
    """Get letter code for dimension from knowledge base"""
    if not knowledge_base:
        return "Z"
    
    mappings = knowledge_base.get("dimension_mappings", {}).get(dimension_type, {})
    
    # Try exact match first
    str_value = str(value)
    if str_value in mappings:
        return mappings[str_value]
    
    # Try numeric match
    try:
        num_value = float(value)
        for key, code in mappings.items():
            try:
                if float(key) == num_value:
                    return code
            except:
                continue
    except:
        pass
    
    return "Z"  # Custom

def get_finish_code(finish_name, knowledge_base):
    """Get finish code from knowledge base"""
    if not knowledge_base:
        return "99"
    
    finish_codes = knowledge_base.get("finish_codes", {})
    finish_lower = finish_name.lower()
    
    for code, name in finish_codes.items():
        if name.lower() in finish_lower or finish_lower in name.lower():
            return code
    
    return "99"  # Other

def identify_product_line(features, knowledge_base):
    """Identify product line (S1/S2/S3/Switchgear/SlimVAC) from features"""
    if not knowledge_base:
        return "Unknown"
    
    ul_type = features.get("ul_type", "").upper()
    breaker_info = features.get("breaker_type", "").upper()
    description = features.get("description", "").upper()
    
    # Check for SlimVAC
    if "SLIMVAC" in description:
        return "SlimVAC"
    
    # Check for Switchgear (UL1558)
    if "1558" in ul_type:
        return "Switchgear (UL1558)"
    
    # Check for Switchboard types (UL891)
    if "891" in ul_type:
        # Check breaker types
        mccb_indicators = ["MCCB", "TMAX", "MASTERPACT"]
        iccb_indicators = ["ICCB", "EMAX", "NW"]
        
        has_mccb = any(ind in breaker_info or ind in description for ind in mccb_indicators)
        has_iccb = any(ind in breaker_info or ind in description for ind in iccb_indicators)
        
        if has_mccb and has_iccb:
            return "S2 (MCCB + ICCB)"
        elif has_iccb:
            return "S3 (ICCB)"
        elif has_mccb:
            return "S1 (MCCB/Panelboard)"
        else:
            return "Switchboard (UL891)"
    
    return "Unknown"

# ============================================
# PERSISTENT MEMORY FUNCTIONS
# ============================================

def get_blob_client():
    """Get Azure Blob client for memory storage"""
    if not BLOB_AVAILABLE:
        return None
    try:
        blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service.get_container_client(MEMORY_CONTAINER)
        return container_client.get_blob_client(MEMORY_BLOB_NAME)
    except Exception as e:
        st.error(f"Blob connection error: {e}")
        return None

def load_memory():
    """Load persistent memory from Azure Blob"""
    blob_client = get_blob_client()
    if not blob_client:
        return {"patterns": [], "last_updated": None}
    
    try:
        blob_data = blob_client.download_blob().readall()
        return json.loads(blob_data)
    except Exception:
        # Memory doesn't exist yet, return empty
        return {"patterns": [], "last_updated": None}

def save_memory(memory_data):
    """Save persistent memory to Azure Blob"""
    blob_client = get_blob_client()
    if not blob_client:
        return False
    
    try:
        memory_data["last_updated"] = datetime.now().isoformat()
        blob_client.upload_blob(json.dumps(memory_data, indent=2), overwrite=True)
        return True
    except Exception as e:
        st.error(f"Error saving memory: {e}")
        return False

def store_pattern_in_memory(features, box_number, source_type="quote"):
    """Store a successful feature-to-box pattern in memory"""
    memory = load_memory()
    
    # Create pattern entry
    pattern = {
        "features": features,
        "box_number": box_number,
        "source_type": source_type,
        "timestamp": datetime.now().isoformat(),
        "match_count": 1
    }
    
    # Check if similar pattern exists
    for existing in memory["patterns"]:
        if features_match(existing["features"], features):
            existing["match_count"] += 1
            existing["timestamp"] = datetime.now().isoformat()
            save_memory(memory)
            return
    
    # Add new pattern
    memory["patterns"].append(pattern)
    save_memory(memory)

def features_match(features1, features2, threshold=0.7):
    """Check if two feature sets match above threshold"""
    if not features1 or not features2:
        return False
    
    matches = 0
    total = 0
    
    for key in features1:
        if key in features2 and features1[key] and features2[key]:
            total += 1
            if str(features1[key]).upper() == str(features2[key]).upper():
                matches += 1
    
    if total == 0:
        return False
    
    return (matches / total) >= threshold

def find_matching_patterns(features, min_matches=3):
    """Find patterns in memory that match given features"""
    memory = load_memory()
    matches = []
    
    for pattern in memory["patterns"]:
        match_score = 0
        matched_features = []
        
        for key, value in features.items():
            if value and key in pattern["features"]:
                if str(pattern["features"][key]).upper() == str(value).upper():
                    match_score += 1
                    matched_features.append(key)
        
        if match_score >= min_matches:
            matches.append({
                "pattern": pattern,
                "score": match_score,
                "matched_features": matched_features,
                "times_seen": pattern.get("match_count", 1)
            })
    
    # Sort by score and times seen
    matches.sort(key=lambda x: (x["score"], x["times_seen"]), reverse=True)
    return matches

# ============================================
# FEATURE EXTRACTION
# ============================================

# The 12 features to extract
BOARD_FEATURES = [
    "ul_type",
    "board_phase", 
    "board_wires",
    "voltage",
    "main_bus_amperage",
    "ka_rating",
    "nema_type",
    "paint_finish",
    "seismic_inclusions",
    "wireway_trolley",
    "control_access",
    "cabling_entry"
]

def extract_features_from_text(text):
    """Extract the 12 board features from quote/order text using AI"""
    knowledge_base = load_knowledge_base()
    
    prompt = f"""Extract board/switchboard features from this text. Return ONLY a JSON object with these exact keys.
If a feature is not found, set its value to null.

Features to extract:
1. ul_type - UL listing type (e.g., "UL891", "UL1558", "UL891+")
2. board_phase - Phase configuration (e.g., "3PH", "1PH", "3 Phase")
3. board_wires - Wire configuration (e.g., "4W", "3W", "4 Wire")
4. voltage - Voltage rating (e.g., "480/277V", "480V", "208V")
5. main_bus_amperage - Main bus amp rating (e.g., "5000A", "4000A", "2000A")
6. ka_rating - Short circuit rating (e.g., "100kAIC", "65kAIC", "100kAIC@480V")
7. nema_type - NEMA enclosure type (e.g., "NEMA 3R", "NEMA 1", "NEMA 3R outdoor")
8. paint_finish - Paint/finish type (e.g., "ANSI 61 gray", "ANSI 49 grey", "black")
9. seismic_inclusions - Seismic requirements (e.g., "seismic bracing", "seismic zone 4", null if none)
10. wireway_trolley - Wireway/trolley provisions (e.g., "wireway", "trolley track", null if none)
11. control_access - Control access type (e.g., "front access only", "front and rear access")
12. cabling_entry - Cable entry type (e.g., "bottom cable entry", "top entry", "top and bottom")

Also extract if present:
13. breaker_type - Type of breakers mentioned (e.g., "MCCB", "ICCB", "EMAX", "TMAX")
14. section_count - Number of sections (e.g., "5 sections", "3 sections")
15. dimensions - Any H/W/D dimensions found

Text to analyze:
{text}

Return ONLY valid JSON, no other text:"""

    try:
        client = openai.AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-01",
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean up JSON response
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        features = json.loads(result)
        
        # Add product line identification
        features["product_line"] = identify_product_line(features, knowledge_base)
        
        return features
        
    except Exception as e:
        st.error(f"Feature extraction error: {e}")
        return {}

def display_features_card(features):
    """Display extracted features in a nice card format"""
    st.markdown("""
    <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
        <div style="font-size: 1.1rem; font-weight: 600; color: #fff; margin-bottom: 1rem; border-bottom: 1px solid #333; padding-bottom: 0.5rem;">
            Extracted Features
        </div>
    """, unsafe_allow_html=True)
    
    # Feature display mapping
    feature_labels = {
        "ul_type": "UL Type",
        "board_phase": "Phase",
        "board_wires": "Wires",
        "voltage": "Voltage",
        "main_bus_amperage": "Main Bus Amperage",
        "ka_rating": "kA Rating",
        "nema_type": "NEMA Type",
        "paint_finish": "Paint/Finish",
        "seismic_inclusions": "Seismic",
        "wireway_trolley": "Wireway/Trolley",
        "control_access": "Control Access",
        "cabling_entry": "Cable Entry",
        "product_line": "Product Line",
        "breaker_type": "Breaker Type",
        "section_count": "Sections"
    }
    
    cols = st.columns(3)
    col_idx = 0
    
    for key, label in feature_labels.items():
        value = features.get(key)
        if value:  # Only show features that have values
            with cols[col_idx % 3]:
                st.markdown(f"""
                <div style="margin-bottom: 0.75rem;">
                    <div style="color: #6b6b6b; font-size: 0.75rem; text-transform: uppercase;">{label}</div>
                    <div style="color: #fff; font-size: 0.95rem;">{value}</div>
                </div>
                """, unsafe_allow_html=True)
            col_idx += 1
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================
# ORDER PROCESSING
# ============================================

def process_order(order_text):
    """Process an order using memory patterns"""
    # Extract features from order
    features = extract_features_from_text(order_text)
    
    if not features:
        return {
            "status": "error",
            "message": "Could not extract features from order"
        }
    
    # Find matching patterns in memory
    matches = find_matching_patterns(features, min_matches=2)
    
    if matches:
        best_match = matches[0]
        return {
            "status": "memory_match",
            "features": features,
            "suggested_box": best_match["pattern"]["box_number"],
            "confidence": best_match["score"],
            "matched_features": best_match["matched_features"],
            "times_seen": best_match["times_seen"],
            "all_matches": matches[:5]  # Top 5 matches
        }
    else:
        # No memory match - try direct matching with available info
        return {
            "status": "no_match",
            "features": features,
            "message": "No matching patterns found in memory. Process more quotes to build knowledge."
        }

# ============================================
# PDF EXTRACTION
# ============================================

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return None

def extract_specs_from_text(text):
    """Use AI to extract structured specs from quote text"""
    knowledge_base = load_knowledge_base()
    kb_context = ""
    
    if knowledge_base:
        kb_context = f"""
Use this knowledge base for reference:
- Product Lines: {json.dumps(knowledge_base.get('product_line_identification', {}), indent=2)}
- Section Labels: {json.dumps(knowledge_base.get('section_characteristics', {}).get('section_labels', []))}
- Breaker Identification: {json.dumps(knowledge_base.get('breaker_identification', {}))}
"""
    
    prompt = f"""Analyze this switchboard/switchgear quote and extract structured information.

{kb_context}

QUOTE TEXT:
{text}

For each SECTION found, extract:
1. Section identifier (e.g., "Section 1", "101", "Main")
2. Dimensions (Height, Width, Depth in inches)
3. Breaker type (MCCB/ICCB/etc) and frame info
4. Section label type (Transition/Distribution/Tie/Control/Auxiliary/Pass-Through)
5. Match percentage confidence (0-100) for matching to a standard assembly

Also extract BOARD-LEVEL features (shared across sections):
- UL Type (891, 1558)
- Phase and Wires
- Voltage
- Main Bus Amperage
- kA Rating
- NEMA type
- Paint/Finish
- Seismic requirements
- Wireway/Trolley provisions
- Control Access type
- Cable Entry type

Return as JSON:
{{
    "board_features": {{
        "ul_type": "...",
        "board_phase": "...",
        "board_wires": "...",
        "voltage": "...",
        "main_bus_amperage": "...",
        "ka_rating": "...",
        "nema_type": "...",
        "paint_finish": "...",
        "seismic_inclusions": "...",
        "wireway_trolley": "...",
        "control_access": "...",
        "cabling_entry": "..."
    }},
    "sections": [
        {{
            "identifier": "Section 1",
            "height": 90,
            "width": 24,
            "depth": 36,
            "breaker_type": "ICCB",
            "breaker_frame": "EMAX E2",
            "section_label": "Distribution",
            "matched_assembly": "401",
            "match_percentage": 85,
            "reasoning": "Dimensions and breaker type align",
            "suggested_assemblies": [
                {{"assembly": "401", "match_pct": 85, "reason": "Best match"}},
                {{"assembly": "402", "match_pct": 70, "reason": "Similar dimensions"}}
            ]
        }}
    ]
}}

Return ONLY valid JSON:"""

    try:
        client = openai.AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-01",
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean up response
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        return json.loads(result)
        
    except Exception as e:
        st.error(f"AI extraction error: {e}")
        return None

# ============================================
# BOM DISPLAY
# ============================================

def display_bom_card(module1_result, unique_id=None):
    """Display BOM results in a card format"""
    if module1_result.get('status') == 'exact_match':
        bom = module1_result['bom']
        
        # Match percentage badge
        match_pct = module1_result.get('match_percentage')
        if match_pct:
            badge_html = f'<span class="status-badge"> {match_pct}% Match</span>'
        else:
            badge_html = '<span class="status-badge">Matched</span>'
        
        st.markdown(f"""
        <div class="bom-card">
            <div class="bom-header">
                <div class="bom-title">Module 1 BOM</div>
                {badge_html}
            </div>
            <div class="bom-assembly">Assembly: {bom['assembly_number']}</div>
            <div class="bom-specs">{bom['height']}"H × {bom['width']}"W × {bom['depth']}"D</div>
            <div class="bom-specs">Breaker: {bom['breaker_type']}</div>
            <div class="bom-specs">Total Parts: {bom['total_parts']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Expandable component list
        export_key = f"export_{unique_id}" if unique_id else "export_bom"
        expander_key = f"components_{unique_id}" if unique_id else "components"
        
        with st.expander(f"View all {bom['total_parts']} components", expanded=False):
            for category, items in bom['components'].items():
                if items:
                    st.markdown(f"**{category}**")
                    for item in items:
                        st.markdown(f"""
                        <div class="component-item">
                            <span class="component-number">{item['part_number']}</span> - 
                            {item['description']} (Qty: {item['quantity']})
                        </div>
                        """, unsafe_allow_html=True)
        
        # Export button
        if st.button("Export BOM to CSV", key=export_key):
            csv_data = []
            for category, items in bom['components'].items():
                for item in items:
                    csv_data.append({
                        'Category': category,
                        'Part Number': item['part_number'],
                        'Description': item['description'],
                        'Quantity': item['quantity']
                    })
            
            df = pd.DataFrame(csv_data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            
            st.download_button(
                label="Download CSV",
                data=csv_buffer.getvalue(),
                file_name=f"BOM_{bom['assembly_number']}.csv",
                mime="text/csv",
                key=f"download_{export_key}"
            )

def display_order_result(result):
    """Display order processing result"""
    if result["status"] == "memory_match":
        st.markdown(f"""
        <div style="background: #1a2e1a; border: 2px solid #22c55e; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
            <div style="font-size: 1.25rem; font-weight: 600; color: #22c55e; margin-bottom: 0.5rem;">
                Pattern Match Found
            </div>
            <div style="color: #a0a0a0; margin-bottom: 1rem;">
                Matched {result['confidence']} features | Seen {result['times_seen']} time(s) before
            </div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #fff;">
                Suggested Box: {result['suggested_box']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Matched Features:**")
        for feat in result['matched_features']:
            st.markdown(f"- {feat}: {result['features'].get(feat, 'N/A')}")
        
        if len(result['all_matches']) > 1:
            st.markdown("**Other Possible Matches:**")
            for match in result['all_matches'][1:]:
                st.markdown(f"- {match['pattern']['box_number']} ({match['score']} features matched)")
    
    elif result["status"] == "no_match":
        st.markdown(f"""
        <div style="background: #2d2d2d; border: 2px solid #f59e0b; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
            <div style="font-size: 1.25rem; font-weight: 600; color: #f59e0b; margin-bottom: 0.5rem;">
                No Pattern Match
            </div>
            <div style="color: #a0a0a0;">
                {result['message']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Always show extracted features
    if result.get("features"):
        display_features_card(result["features"])

# ============================================
# PAGE CONFIG & STYLES
# ============================================

st.set_page_config(
    page_title="VOLTRIX",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --bg-dark: #0a0a0a;
        --surface: #1a1a1a;
        --surface-hover: #222222;
        --border: #2a2a2a;
        --text: #ffffff;
        --text-secondary: #6b6b6b;
        --accent: #303030;
    }
    
    * {
        font-family: 'Consolas', 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stApp {
        background: #000000 !important;
        color: var(--text);
    }
    
    .main, .block-container, [data-testid="stAppViewContainer"] {
        background: #0a0a0a !important;
    }
    
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    .main .block-container {
        max-width: 900px;
        padding: 1rem 2rem 4rem 2rem;
        margin: 0 auto;
    }
    
    .app-logo {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .app-logo h1 {
        color: var(--text);
        margin: 0;
        font-size: 2.5rem;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    .app-logo-badge {
        color: var(--text-secondary);
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 0.5rem;
    }
    
    .stChatInput > div {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 50px !important;
        padding: 0.25rem 0.5rem;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        border: none !important;
        color: var(--text) !important;
        padding: 1rem 1.5rem !important;
        font-size: 1rem !important;
    }
    
    .user-message {
        background: var(--surface);
        border: 1px solid var(--border);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: var(--text);
    }
    
    .assistant-message {
        background: transparent;
        padding: 1rem 0;
        color: var(--text);
        line-height: 1.6;
    }
    
    .bom-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .bom-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border);
    }
    
    .bom-title {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .status-badge {
        background: var(--accent);
        color: var(--text);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .bom-assembly {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 0.5rem;
    }
    
    .bom-specs {
        color: var(--text-secondary);
        font-size: 0.95rem;
        margin: 0.25rem 0;
    }
    
    .component-item {
        background: transparent;
        border: 1px solid var(--border);
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .component-number {
        font-family: 'Courier New', monospace;
        color: var(--text);
        font-weight: 500;
    }
    
    .stButton > button {
        background: var(--surface);
        border: 1px solid var(--border);
        color: var(--text-secondary);
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: var(--surface-hover);
        color: var(--text);
        border-color: #404040;
    }
    
    .footer-text {
        text-align: center;
        color: var(--text-secondary);
        font-size: 0.8rem;
        padding: 2rem 0;
    }
    
    .memory-badge {
        background: #1a2e1a;
        border: 1px solid #22c55e;
        color: #22c55e;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 500;
    }
    
    /* Compact file uploaders */
    .stFileUploader {
        margin-bottom: 0 !important;
    }
    
    .stFileUploader > div {
        padding: 0 !important;
    }
    
    .stFileUploader section {
        padding: 0.5rem !important;
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    
    .stFileUploader section > div {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        padding: 0.5rem !important;
        min-height: auto !important;
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }
    
    .stFileUploader button {
        padding: 0.25rem 0.75rem !important;
        font-size: 0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# AUTHENTICATION
# ============================================

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

def check_auth(username, password):
    users = AUTHORIZED_USERS.split(',')
    return f"{username}:{password}" in users

def login_page():
    st.markdown("""
    <div class="app-logo">
        <h1>Voltrix</h1>
        <div class="app-logo-badge">BOM Generator</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Sign In")
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")
        
        if st.button("Sign In", use_container_width=True):
            if check_auth(username, password):
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.rerun()
            else:
                st.error("Invalid credentials")

# ============================================
# MAIN APP
# ============================================

if not st.session_state.authenticated:
    login_page()
else:
    # Top controls
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Sign out", key="signout"):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
    with col2:
        if st.button("Clear", key="clear"):
            st.session_state.messages = []
            st.rerun()
    with col3:
        # Show memory status
        memory = load_memory()
        pattern_count = len(memory.get("patterns", []))
        st.button(f"Memory: {pattern_count}", key="memory_status", disabled=True)
    
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    # Logo
    st.markdown("""
    <div class="app-logo">
        <h1>Voltrix</h1>
        <div class="app-logo-badge">BOM Generator v2.0</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Process Quote PDF if triggered
    if hasattr(st.session_state, 'trigger_quote_process') and st.session_state.trigger_quote_process:
        pdf_to_process = st.session_state.current_quote_pdf
        st.session_state.trigger_quote_process = False
        
        with st.spinner("Reading quote PDF..."):
            text = extract_text_from_pdf(pdf_to_process)
            
            if text:
                with st.spinner("Analyzing quote..."):
                    specs_json = extract_specs_from_text(text)
                    
                    if specs_json:
                        board_features = specs_json.get("board_features", {})
                        sections = specs_json.get("sections", [])
                        
                        all_boms = []
                        no_match_sections = []
                        
                        for section in sections:
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
                                    
                                    # Store in memory
                                    section_features = {**board_features, **section}
                                    store_pattern_in_memory(section_features, matched_assembly, "quote")
                                    
                                except Exception as e:
                                    st.warning(f"Error for {section_id}: {e}")
                            else:
                                no_match_sections.append({
                                    'section_id': section_id,
                                    'reasoning': reasoning,
                                    'match_percentage': match_pct,
                                    'suggested': suggested
                                })
                        
                        # Create messages
                        summary = f"Quote: {pdf_to_process.name}\n\n"
                        if all_boms:
                            summary += f"{len(all_boms)} section(s) matched\n"
                        if no_match_sections:
                            summary += f"{len(no_match_sections)} section(s) need review\n"
                        
                        st.session_state.messages.append({"role": "user", "content": summary})
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "Quote analyzed. See results below.",
                            "board_features": board_features,
                            "all_boms": all_boms,
                            "no_match_sections": no_match_sections,
                            "type": "quote_result"
                        })
                        
                        st.rerun()
                    else:
                        st.error("Could not analyze quote")
            else:
                st.error("Could not read PDF")
    
    # Process Order PDF if triggered
    if hasattr(st.session_state, 'trigger_order_process') and st.session_state.trigger_order_process:
        pdf_to_process = st.session_state.current_order_pdf
        st.session_state.trigger_order_process = False
        
        with st.spinner("Reading order PDF..."):
            text = extract_text_from_pdf(pdf_to_process)
            
            if text:
                with st.spinner("Searching memory for patterns..."):
                    result = process_order(text)
                    
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": f"Order: {pdf_to_process.name}"
                    })
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Order analyzed using memory patterns.",
                        "order_result": result,
                        "type": "order_result"
                    })
                    
                    st.rerun()
            else:
                st.error("Could not read PDF")
    
    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
            
            # Handle quote results
            if message.get("type") == "quote_result":
                # Display board features
                if message.get("board_features"):
                    display_features_card(message["board_features"])
                
                # Display matched BOMs
                if message.get("all_boms"):
                    for idx, bom_data in enumerate(message["all_boms"]):
                        st.markdown(f"### {bom_data['section_id']}")
                        module1_result = {
                            'status': 'exact_match',
                            'bom': bom_data['bom'],
                            'message': f"{bom_data['section_id']}: Assembly {bom_data['assembly']}",
                            'match_percentage': bom_data.get('match_percentage', None)
                        }
                        unique_id = f"{bom_data['section_id']}_{bom_data['assembly']}_{idx}"
                        display_bom_card(module1_result, unique_id=unique_id)
                        st.markdown("---")
                
                # Display no-match sections
                if message.get("no_match_sections"):
                    st.markdown("### Sections Without Exact Match")
                    for no_match in message["no_match_sections"]:
                        st.markdown(f"""
                        <div style="background: #2d2d2d; border: 2px solid #EF4444; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
                            <div style="font-size: 1.125rem; font-weight: 600; color: #EF4444;">{no_match['section_id']}</div>
                            <div style="color: #b0b0b0;">Match: {no_match['match_percentage']}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if no_match.get('suggested'):
                            cols = st.columns(len(no_match['suggested'][:3]))
                            for idx, sugg in enumerate(no_match['suggested'][:3]):
                                with cols[idx]:
                                    if st.button(f"{sugg['assembly']} ({sugg['match_pct']}%)", 
                                                 key=f"sel_{no_match['section_id']}_{sugg['assembly']}"):
                                        try:
                                            matcher = get_matcher()
                                            selected_bom = matcher.generate_bom(sugg['assembly'])
                                            st.session_state.messages.append({
                                                "role": "assistant",
                                                "content": f"Generated BOM for {sugg['assembly']}",
                                                "module1_result": {
                                                    'status': 'exact_match',
                                                    'bom': selected_bom,
                                                    'message': f"BOM for {sugg['assembly']}"
                                                },
                                                "type": "module1"
                                            })
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")
                                    st.caption(sugg['reason'])
            
            # Handle order results
            elif message.get("type") == "order_result":
                display_order_result(message["order_result"])
            
            # Handle single BOM
            elif message.get("type") == "module1" and "module1_result" in message:
                display_bom_card(message["module1_result"])
    
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    # Action buttons - compact side by side
    col1, col2, col3, col_space = st.columns([1, 1, 1, 4])
    
    with col1:
        if MODULE1_AVAILABLE and PDF_AVAILABLE:
            st.markdown("<p style='color: #6b6b6b; font-size: 0.75rem; margin-bottom: 0.25rem;'>Quote PDF</p>", unsafe_allow_html=True)
            uploaded_quote = st.file_uploader("", type=['pdf'], key="quote_uploader", 
                                              label_visibility="collapsed")
    
    with col2:
        if MODULE1_AVAILABLE and PDF_AVAILABLE:
            st.markdown("<p style='color: #6b6b6b; font-size: 0.75rem; margin-bottom: 0.25rem;'>Order PDF</p>", unsafe_allow_html=True)
            uploaded_order = st.file_uploader("", type=['pdf'], key="order_uploader",
                                              label_visibility="collapsed")
    
    # Process buttons
    with col3:
        if 'uploaded_quote' in locals() and uploaded_quote is not None:
            if st.button("Process Quote", key="proc_quote"):
                st.session_state.trigger_quote_process = True
                st.session_state.current_quote_pdf = uploaded_quote
                st.rerun()
        
        if 'uploaded_order' in locals() and uploaded_order is not None:
            if st.button("Process Order", key="proc_order"):
                st.session_state.trigger_order_process = True
                st.session_state.current_order_pdf = uploaded_order
                st.rerun()
    
    # Chat input
    user_input = st.chat_input("Type specifications or ask a question...")
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        if MODULE1_AVAILABLE:
            with st.spinner("Analyzing..."):
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
        st.rerun()
    
    # Footer
    st.markdown("""
    <div class="footer-text">
        SAI Advanced Power Solutions • Voltrix v2.0
    </div>
    """, unsafe_allow_html=True)
