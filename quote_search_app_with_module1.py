"""
Voltrix v2.1 - Box Number Generator
Extracts section info from quotes and generates box numbers
"""
import streamlit as st
import openai
import json
import re
import io

# PDF Processing
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Configuration - safely load secrets
def get_secret(key, default=""):
    try:
        value = st.secrets[key]
        return str(value) if value else default
    except:
        return default

AZURE_OPENAI_ENDPOINT = get_secret("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = get_secret("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = get_secret("AZURE_OPENAI_DEPLOYMENT")

openai.api_type = "azure"
openai.api_key = AZURE_OPENAI_KEY
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = "2024-02-01"

# ============================================
# KNOWLEDGE BASE
# ============================================

@st.cache_data
def load_knowledge_base():
    """Load BoxKnowledge.json"""
    try:
        with open("BoxKnowledge.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("BoxKnowledge.json not found!")
        return None
    except Exception as e:
        st.error(f"Error loading knowledge base: {e}")
        return None

# ============================================
# BOX NUMBER GENERATION
# ============================================

def get_dimension_code(dimension_type, value, kb):
    """Get letter code for dimension"""
    if not kb or not value:
        return "Z"
    
    mappings = kb.get("dimension_mappings", {}).get(dimension_type, {})
    str_value = str(value).replace('"', '').replace("'", '').strip()
    
    # Try exact match
    if str_value in mappings:
        return mappings[str_value]
    
    # Try numeric match
    try:
        num_value = float(str_value)
        for key, code in mappings.items():
            if key == "CUSTOM":
                continue
            try:
                if float(key) == num_value:
                    return code
            except:
                continue
    except:
        pass
    
    return "Z"  # Custom

def get_front_cornerpost_code(section_data, has_seismic, kb):
    """
    Determine front cornerpost code based on:
    - Breaker manufacturer (ABB/Schneider)
    - Mounting type (Fixed/Drawout)
    - Seismic requirements
    """
    if not kb:
        return "S"
    
    # Safely get values, handle None
    breaker_mfr = section_data.get("breaker_manufacturer") or ""
    breaker_mfr = str(breaker_mfr).upper()
    
    mounting = section_data.get("mounting_type") or ""
    mounting = str(mounting).upper()
    
    has_breaker = bool(breaker_mfr and breaker_mfr not in ["NONE", "N/A", "", "NULL"])
    
    # No breaker mentioned
    if not has_breaker:
        if has_seismic:
            return "2"  # Seismic Short
        else:
            return "S"  # Short
    
    # Determine manufacturer
    is_abb = False
    is_schneider = False
    
    abb_keywords = ["ABB", "EMAX", "SACE", "E2", "E4", "E6", "XT"]
    schneider_keywords = ["SCHNEIDER", "SQUARE D", "MASTERPACT", "NW", "NT", "MTZ", "COMPACT"]
    
    for kw in abb_keywords:
        if kw in breaker_mfr:
            is_abb = True
            break
    
    for kw in schneider_keywords:
        if kw in breaker_mfr:
            is_schneider = True
            break
    
    # Determine mounting (default to Fixed)
    is_drawout = False
    drawout_keywords = ["DRAWOUT", "DRAW-OUT", "DO", "DRAW OUT", "WITHDRAWABLE"]
    for kw in drawout_keywords:
        if kw in mounting:
            is_drawout = True
            break
    
    # Return appropriate code
    if is_abb:
        return "D" if is_drawout else "C"
    elif is_schneider:
        return "B" if is_drawout else "A"
    else:
        # Unknown manufacturer - default to Short
        if has_seismic:
            return "2"
        return "S"

def get_hardware_code(hardware_text):
    """Get hardware code (first letter)"""
    if not hardware_text:
        return "L"  # Default to Locknut
    
    hw_upper = str(hardware_text).upper()
    if "BELLEVILLE" in hw_upper:
        return "B"
    elif "LOCKNUT" in hw_upper or "LOCK" in hw_upper:
        return "L"
    
    return "L"  # Default

def get_seismic_code(has_seismic):
    """Get seismic code"""
    return "S" if has_seismic else "X"

def check_seismic(text):
    """Check if seismic is mentioned"""
    if not text:
        return False
    
    text_upper = str(text).upper()
    seismic_keywords = ["SEISMIC", "IBC", "SEISMIC BRACING", "SEISMIC ANCHORING", "SEISMIC ZONE"]
    
    for kw in seismic_keywords:
        if kw in text_upper:
            return True
    return False

def get_finish_code(finish_text, kb):
    """Get paint/finish code"""
    if not kb or not finish_text:
        return "99"
    
    finish_upper = str(finish_text).upper()
    finish_matching = kb.get("finish_matching", {}).get("matches", {})
    
    for keyword, code in finish_matching.items():
        if keyword.upper() in finish_upper:
            return code
    
    # Try finish_codes directly
    finish_codes = kb.get("finish_codes", {})
    for code, name in finish_codes.items():
        if name.upper() in finish_upper or finish_upper in name.upper():
            return code
    
    return "99"  # Other

def generate_box_number(section_data, board_features, kb):
    """Generate complete box number for a section"""
    
    # Get dimension codes
    height_code = get_dimension_code("height", section_data.get("height"), kb)
    width_code = get_dimension_code("width", section_data.get("width"), kb)
    depth_code = get_dimension_code("depth", section_data.get("depth"), kb)
    
    # Check seismic from board features
    seismic_text = board_features.get("seismic_inclusions", "") or ""
    has_seismic = check_seismic(seismic_text) or check_seismic(str(board_features))
    
    # Get front cornerpost
    front_code = get_front_cornerpost_code(section_data, has_seismic, kb)
    
    # Get hardware code
    hardware_code = get_hardware_code(section_data.get("hardware", ""))
    
    # Get seismic code
    seismic_code = get_seismic_code(has_seismic)
    
    # Get finish code
    finish_text = board_features.get("paint_finish", "") or board_features.get("finish", "")
    finish_code = get_finish_code(finish_text, kb)
    
    # Assemble box number
    box_number = f"APBX{height_code}{width_code}{depth_code}{front_code}{front_code}{hardware_code}{seismic_code}-G01-{finish_code}"
    
    return {
        "box_number": box_number,
        "breakdown": {
            "prefix": "APBX",
            "height": f"{height_code} (from {section_data.get('height', '?')}\")",
            "width": f"{width_code} (from {section_data.get('width', '?')}\")",
            "depth": f"{depth_code} (from {section_data.get('depth', '?')}\")",
            "front_cornerpost": f"{front_code} ({get_cornerpost_description(front_code)})",
            "hardware": f"{hardware_code} ({section_data.get('hardware', 'Locknut')})",
            "seismic": f"{seismic_code} ({'Seismic' if has_seismic else 'No Seismic'})",
            "static": "-G01-",
            "finish": f"{finish_code} ({finish_text or 'Unknown'})"
        }
    }

def get_cornerpost_description(code):
    """Get human-readable cornerpost description"""
    descriptions = {
        "S": "Short",
        "2": "Seismic Short",
        "A": "Schneider Fixed",
        "B": "Schneider Drawout",
        "C": "ABB Fixed",
        "D": "ABB Drawout",
        "E": "Schneider DO no Cuts",
        "F": "ABB DO no Cuts",
        "1": "12\" Stretch",
        "Z": "Custom"
    }
    return descriptions.get(code, "Unknown")

# ============================================
# PDF & AI EXTRACTION
# ============================================

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"PDF error: {e}")
        return None

def extract_quote_data(text):
    """Use AI to extract structured data from quote"""
    
    # For very long quotes, we may need to process in chunks
    # First, let's try to get all boards
    
    # Limit text length but keep more for better coverage
    max_chars = 25000
    original_length = len(text)
    truncated = False
    
    if len(text) > max_chars:
        truncated = True
        # Keep more from beginning (where board descriptions usually are)
        text = text[:int(max_chars*0.7)] + "\n\n... [TRUNCATED FOR LENGTH] ...\n\n" + text[-int(max_chars*0.3):]
    
    prompt = f"""Analyze this switchboard/switchgear quote and extract structured information.

IMPORTANT RULES:
1. FIRST identify ALL BOARDS in the quote. Boards are separated by bolded lines with "switchboard" or "switchgear" in the name.
2. Each board has a NAME (e.g., "UL891 Switchboard", "Main Distribution Switchboard", "UL1558 Switchgear")
3. Each board has SECTIONS underneath it (e.g., Section 101, Section 102, etc.)
4. Board-level features are shared across all sections in that board
5. EXTRACT ALL BOARDS - do not stop early!

QUOTE TEXT:
{text}

Extract and return as JSON:

1. For EACH BOARD found, extract:
   - board_name: The name/title of the board (e.g., "UL891 Switchboard")
   - board_features: Shared features for this board
   - sections: List of sections belonging to this board

2. BOARD FEATURES (shared across all sections in a board):
   - ul_type: UL listing (e.g., "UL891", "UL1558")
   - phase: Phase configuration (e.g., "3 phase", "3PH")
   - wires: Wire count (e.g., "4 wire", "4W")
   - voltage: Voltage (e.g., "480Y/277V", "480V")
   - main_bus_amperage: Main bus amps (e.g., "2000A")
   - ka_rating: Short circuit rating (e.g., "65kAIC@480V")
   - nema_type: NEMA enclosure (e.g., "NEMA 3R")
   - paint_finish: Paint/finish (e.g., "ANSI 61 gray")
   - seismic_inclusions: Seismic requirements (e.g., "seismic bracing", or null)
   - cable_entry: Cable entry type (e.g., "top or bottom cable entry")
   - access_type: Access type (e.g., "front and rear access")

3. For EACH SECTION within a board:
   - identifier: Section ID (e.g., "Section 101")
   - height: Height in inches (number only)
   - width: Width in inches (number only)
   - depth: Depth in inches (number only)
   - breaker_manufacturer: Breaker brand (e.g., "ABB", "Schneider", or null)
   - breaker_type: Breaker model (e.g., "Emax2", "TMAX XT")
   - mounting_type: Mounting (e.g., "Fixed", "Drawout", or null)
   - hardware: Hardware type if mentioned (or null)
   - description: Brief description of section contents

CRITICAL: Make sure to capture ALL boards and ALL sections. Do not truncate the response.

Return ONLY valid JSON in this format:
{{
    "boards": [
        {{
            "board_name": "Board Name Here",
            "board_features": {{
                "ul_type": "...",
                "phase": "...",
                "wires": "...",
                "voltage": "...",
                "main_bus_amperage": "...",
                "ka_rating": "...",
                "nema_type": "...",
                "paint_finish": "...",
                "seismic_inclusions": "...",
                "cable_entry": "...",
                "access_type": "..."
            }},
            "sections": [
                {{
                    "identifier": "Section 101",
                    "height": 72,
                    "width": 42,
                    "depth": 56,
                    "breaker_manufacturer": "ABB",
                    "breaker_type": "Emax2",
                    "mounting_type": "Fixed",
                    "hardware": null,
                    "description": "Description here"
                }}
            ]
        }}
    ]
}}

Return ONLY the JSON, no other text:"""

    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=16000
        )
        
        result = response.choices[0].message["content"].strip()
        
        # Clean up JSON
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        # Try to fix common JSON issues
        # Remove trailing commas before } or ]
        result = re.sub(r',\s*}', '}', result)
        result = re.sub(r',\s*]', ']', result)
        
        # Try parsing
        try:
            return json.loads(result)
        except json.JSONDecodeError as je:
            # Try to find and extract valid JSON
            st.warning(f"JSON parse issue, attempting recovery...")
            
            # Find the last complete object
            brace_count = 0
            last_valid_pos = 0
            for i, char in enumerate(result):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_valid_pos = i + 1
            
            if last_valid_pos > 0:
                truncated = result[:last_valid_pos]
                try:
                    return json.loads(truncated)
                except:
                    pass
            
            st.error(f"AI extraction error: {je}")
            return None
        
    except Exception as e:
        st.error(f"AI extraction error: {e}")
        return None

# ============================================
# DISPLAY FUNCTIONS
# ============================================

def display_board_features(features):
    """Display extracted board features"""
    st.markdown("""
    <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
        <div style="font-size: 1.1rem; font-weight: 600; color: #fff; margin-bottom: 1rem; border-bottom: 1px solid #333; padding-bottom: 0.5rem;">
            📋 Board Features
        </div>
    """, unsafe_allow_html=True)
    
    feature_labels = {
        "ul_type": "UL Type",
        "phase": "Phase",
        "wires": "Wires", 
        "voltage": "Voltage",
        "main_bus_amperage": "Main Bus",
        "ka_rating": "kA Rating",
        "nema_type": "NEMA",
        "paint_finish": "Finish",
        "seismic_inclusions": "Seismic",
        "cable_entry": "Cable Entry",
        "access_type": "Access"
    }
    
    cols = st.columns(4)
    col_idx = 0
    
    for key, label in feature_labels.items():
        value = features.get(key)
        if value:
            with cols[col_idx % 4]:
                st.markdown(f"""
                <div style="margin-bottom: 0.75rem;">
                    <div style="color: #6b6b6b; font-size: 0.7rem; text-transform: uppercase;">{label}</div>
                    <div style="color: #fff; font-size: 0.9rem;">{value}</div>
                </div>
                """, unsafe_allow_html=True)
            col_idx += 1
    
    st.markdown("</div>", unsafe_allow_html=True)

def display_section_box_number(section, box_result):
    """Display section with generated box number"""
    section_id = section.get("identifier", "Unknown")
    height = section.get("height", "?")
    width = section.get("width", "?")
    depth = section.get("depth", "?")
    breaker_mfr = section.get("breaker_manufacturer", "None")
    breaker_type = section.get("breaker_type", "")
    mounting = section.get("mounting_type", "Fixed")
    description = section.get("description", "")
    
    box_number = box_result.get("box_number", "ERROR")
    breakdown = box_result.get("breakdown", {})
    
    st.markdown(f"""
    <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div style="font-size: 1.25rem; font-weight: 600; color: #fff;">{section_id}</div>
            <div style="background: #22c55e; color: #000; padding: 0.5rem 1rem; border-radius: 8px; font-family: monospace; font-size: 1.1rem; font-weight: 700;">
                {box_number}
            </div>
        </div>
        <div style="color: #b0b0b0; margin-bottom: 0.5rem;">
            <strong>Dimensions:</strong> {height}"H × {width}"W × {depth}"D
        </div>
        <div style="color: #b0b0b0; margin-bottom: 0.5rem;">
            <strong>Breaker:</strong> {breaker_mfr or 'None'} {breaker_type or ''} ({mounting or 'Fixed'})
        </div>
        <div style="color: #888; font-size: 0.85rem; margin-bottom: 1rem;">
            {description}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Breakdown expander
    with st.expander("View Box Number Breakdown"):
        for part, value in breakdown.items():
            st.markdown(f"**{part}:** {value}")

# ============================================
# AUTHENTICATION
# ============================================

def check_auth(username, password):
    if not username or not password:
        return False
    try:
        if hasattr(st.secrets, "AUTHORIZED_USERS"):
            auth_dict = st.secrets["AUTHORIZED_USERS"]
            if hasattr(auth_dict, 'get') or isinstance(auth_dict, dict):
                stored_password = auth_dict.get(username)
                if stored_password and str(stored_password) == password:
                    return True
        return False
    except:
        return False

def login_page():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="color: #fff; font-size: 2.5rem;">Voltrix</h1>
        <p style="color: #6b6b6b;">Box Number Generator</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Sign In", use_container_width=True):
            if check_auth(username, password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid credentials")

# ============================================
# PAGE CONFIG & STYLES
# ============================================

st.set_page_config(
    page_title="VOLTRIX",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Consolas', 'Inter', sans-serif !important; }
    
    .stApp { background: #0a0a0a !important; color: #fff; }
    .main, .block-container, [data-testid="stAppViewContainer"] { background: #0a0a0a !important; }
    
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    
    .main .block-container {
        max-width: 1000px;
        padding: 1rem 2rem 4rem 2rem;
        margin: 0 auto;
    }
    
    .stButton > button {
        background: #1a1a1a;
        border: 1px solid #333;
        color: #fff;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    
    .stButton > button:hover {
        background: #2a2a2a;
        border-color: #444;
    }
    
    .stFileUploader > div { padding: 0 !important; }
    .stFileUploader section {
        padding: 0.5rem !important;
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# MAIN APP
# ============================================

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'results' not in st.session_state:
    st.session_state.results = None

if not st.session_state.authenticated:
    login_page()
else:
    # Header
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("Sign out"):
            st.session_state.authenticated = False
            st.session_state.results = None
            st.rerun()
    with col3:
        if st.button("Clear"):
            st.session_state.results = None
            st.rerun()
    
    # Logo
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h1 style="color: #fff; font-size: 2.5rem; margin: 0;">Voltrix</h1>
        <p style="color: #6b6b6b; font-size: 0.9rem;">Box Number Generator v2.1</p>
    </div>
    """, unsafe_allow_html=True)
    
    # File upload
    st.markdown("<p style='color: #888; margin-bottom: 0.5rem;'>Upload Quote PDF</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader("", type=['pdf'], label_visibility="collapsed")
    with col2:
        process_btn = st.button("Generate Box Numbers", use_container_width=True, disabled=not uploaded_file)
    
    # Process
    if process_btn and uploaded_file:
        kb = load_knowledge_base()
        
        if not kb:
            st.error("Cannot load BoxKnowledge.json")
        else:
            with st.spinner("Reading PDF..."):
                text = extract_text_from_pdf(uploaded_file)
            
            if text:
                with st.spinner("Analyzing quote with AI..."):
                    quote_data = extract_quote_data(text)
                
                if quote_data:
                    boards = quote_data.get("boards", [])
                    
                    # Check for incomplete data
                    incomplete_boards = [b for b in boards if not b.get("sections")]
                    if incomplete_boards:
                        st.warning(f"⚠️ {len(incomplete_boards)} board(s) may have incomplete data. Very long quotes may be truncated.")
                    
                    # Generate box numbers for each section in each board
                    all_boards = []
                    for board in boards:
                        board_name = board.get("board_name", "Unknown Board")
                        board_features = board.get("board_features", {})
                        sections = board.get("sections", [])
                        
                        # Skip boards with no sections (incomplete)
                        if not sections:
                            st.info(f"Board '{board_name}' has no sections - may be truncated")
                        
                        section_results = []
                        for section in sections:
                            box_result = generate_box_number(section, board_features, kb)
                            section_results.append({
                                "section": section,
                                "box_result": box_result
                            })
                        
                        all_boards.append({
                            "board_name": board_name,
                            "board_features": board_features,
                            "sections": section_results
                        })
                    
                    st.session_state.results = {
                        "filename": uploaded_file.name,
                        "boards": all_boards
                    }
                    st.rerun()
                else:
                    st.error("Could not extract data from quote")
            else:
                st.error("Could not read PDF")
    
    # Display results
    if st.session_state.results:
        results = st.session_state.results
        
        st.markdown(f"### 📄 {results['filename']}")
        
        total_sections = sum(len(b['sections']) for b in results['boards'])
        st.markdown(f"**{len(results['boards'])} board(s), {total_sections} section(s) found**")
        
        # Loop through each board
        for board_idx, board in enumerate(results['boards']):
            board_name = board.get('board_name', 'Unknown Board')
            board_features = board.get('board_features', {})
            sections = board.get('sections', [])
            
            # Board header
            st.markdown(f"""
            <div style="background: #252525; border-left: 4px solid #3b82f6; padding: 1rem 1.5rem; margin: 1.5rem 0 1rem 0; border-radius: 0 8px 8px 0;">
                <div style="font-size: 1.3rem; font-weight: 700; color: #3b82f6;">📋 {board_name}</div>
                <div style="color: #888; font-size: 0.85rem;">{len(sections)} section(s)</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Board features
            display_board_features(board_features)
            
            st.markdown("#### 📦 Sections")
            
            # Each section in this board
            for item in sections:
                display_section_box_number(item['section'], item['box_result'])
            
            # Summary table for this board
            st.markdown(f"**{board_name} - Summary**")
            
            summary_data = []
            for item in sections:
                summary_data.append({
                    "Section": item['section'].get('identifier', 'Unknown'),
                    "Dimensions": f"{item['section'].get('height', '?')}×{item['section'].get('width', '?')}×{item['section'].get('depth', '?')}",
                    "Box Number": item['box_result'].get('box_number', 'ERROR')
                })
            
            st.table(summary_data)
            
            if board_idx < len(results['boards']) - 1:
                st.markdown("---")
        
        # Export all button
        st.markdown("---")
        if st.button("Export All to CSV"):
            import pandas as pd
            all_data = []
            for board in results['boards']:
                board_name = board.get('board_name', 'Unknown')
                for item in board['sections']:
                    all_data.append({
                        "Board": board_name,
                        "Section": item['section'].get('identifier', 'Unknown'),
                        "Height": item['section'].get('height', '?'),
                        "Width": item['section'].get('width', '?'),
                        "Depth": item['section'].get('depth', '?'),
                        "Box Number": item['box_result'].get('box_number', 'ERROR')
                    })
            
            df = pd.DataFrame(all_data)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                f"box_numbers_{results['filename'].replace('.pdf', '')}.csv",
                "text/csv"
            )
    
    # Footer
    st.markdown("""
    <div style="text-align: center; color: #6b6b6b; font-size: 0.8rem; padding: 2rem 0;">
        SAI Advanced Power Solutions • Voltrix v2.1
    </div>
    """, unsafe_allow_html=True)
