"""
Voltrix v2.2 - Box Number Generator with Persistent Memory
Extracts section info from quotes, generates box numbers, learns patterns
"""
import streamlit as st
import openai
import json
import re
import io
from datetime import datetime
import uuid

# PDF Processing
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Azure Blob Storage
try:
    from azure.storage.blob import BlobServiceClient
    BLOB_AVAILABLE = True
except ImportError:
    BLOB_AVAILABLE = False

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
AZURE_STORAGE_CONNECTION_STRING = get_secret("AZURE_STORAGE_CONNECTION_STRING")
MEMORY_CONTAINER = "persistent-memory"
MEMORY_BLOB_NAME = "voltrix_patterns.json"

openai.api_type = "azure"
openai.api_key = AZURE_OPENAI_KEY
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = "2024-02-01"

# ============================================
# PERSISTENT MEMORY (Azure Blob Storage)
# ============================================

def get_blob_client():
    """Get Azure Blob client for memory storage"""
    if not BLOB_AVAILABLE:
        st.error("❌ Azure Blob Storage library not installed. Run: pip install azure-storage-blob")
        return None
    
    if not AZURE_STORAGE_CONNECTION_STRING:
        st.error("❌ AZURE_STORAGE_CONNECTION_STRING not set in secrets")
        return None
    
    try:
        blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service.get_container_client(MEMORY_CONTAINER)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
            st.info(f"Created container: {MEMORY_CONTAINER}")
        except Exception as ce:
            # Container already exists - this is fine
            pass
        
        return container_client.get_blob_client(MEMORY_BLOB_NAME)
    except Exception as e:
        st.error(f"❌ Blob connection error: {e}")
        return None

def load_memory():
    """Load patterns from Azure Blob Storage"""
    blob_client = get_blob_client()
    if not blob_client:
        return {"patterns": [], "quotes": {}}
    
    try:
        data = blob_client.download_blob().readall()
        return json.loads(data)
    except Exception as e:
        # File doesn't exist yet - return empty structure
        return {"patterns": [], "quotes": {}}

def save_memory(memory):
    """Save patterns to Azure Blob Storage"""
    blob_client = get_blob_client()
    if not blob_client:
        st.error("❌ Could not get blob client - memory not saved")
        return False
    
    try:
        blob_client.upload_blob(json.dumps(memory, indent=2), overwrite=True)
        st.success(f"✅ Memory saved! ({len(memory.get('quotes', {}))} quotes)")
        return True
    except Exception as e:
        st.error(f"❌ Error saving memory: {e}")
        return False

def store_quote_patterns(quote_number, boards_data):
    """Store patterns from a processed quote - board level specs"""
    memory = load_memory()
    
    # Clean quote number for matching
    quote_key = quote_number.strip().upper()
    
    st.info(f"📝 Storing quote: {quote_key}")
    
    # Store quote reference
    memory["quotes"][quote_key] = {
        "processed_at": datetime.now().isoformat(),
        "original_quote_number": quote_number,
        "boards": []
    }
    
    boards_stored = 0
    sections_stored = 0
    
    for board in boards_data:
        board_name = board.get("board_name", "Unknown")
        board_features = board.get("board_features", {})
        sections = board.get("sections", [])
        
        # Extract board-level specs for matching
        board_specs = {
            "ul_type": board_features.get("ul_type"),
            "voltage": board_features.get("voltage"),
            "amperage": board_features.get("main_bus_amperage"),
            "nema_type": board_features.get("nema_type"),
            "paint_finish": board_features.get("paint_finish"),
            "seismic": check_seismic(str(board_features.get("seismic_inclusions", ""))),
            "section_count": len(sections)
        }
        
        # Collect all section box numbers
        section_box_numbers = []
        for section_item in sections:
            section = section_item.get("section", {})
            box_result = section_item.get("box_result", {})
            section_box_numbers.append({
                "section_id": section.get("identifier", "Unknown"),
                "height": section.get("height"),
                "width": section.get("width"),
                "depth": section.get("depth"),
                "box_number": box_result.get("box_number")
            })
            sections_stored += 1
        
        board_record = {
            "board_name": board_name,
            "specs": board_specs,
            "sections": section_box_numbers
        }
        
        memory["quotes"][quote_key]["boards"].append(board_record)
        boards_stored += 1
    
    st.info(f"📦 Prepared: {boards_stored} boards, {sections_stored} sections")
    
    if save_memory(memory):
        return len(memory["quotes"])
    return 0

def find_quote_in_memory(quote_reference):
    """Find a quote in memory by reference number"""
    memory = load_memory()
    
    if not quote_reference:
        return None
    
    # Clean and normalize
    search_key = quote_reference.strip().upper()
    
    # Try exact match
    if search_key in memory.get("quotes", {}):
        return memory["quotes"][search_key]
    
    # Try without revision (e.g., "250321SAI02-R04" -> "250321SAI02")
    base_key = search_key.split("-R")[0] if "-R" in search_key else search_key
    
    for key, value in memory.get("quotes", {}).items():
        if key.startswith(base_key) or base_key in key:
            return value
    
    return None

def get_memory_stats():
    """Get statistics about stored memory"""
    memory = load_memory()
    quotes = memory.get("quotes", {})
    
    total_boards = sum(len(q.get("boards", [])) for q in quotes.values())
    total_sections = sum(
        sum(len(b.get("sections", [])) for b in q.get("boards", []))
        for q in quotes.values()
    )
    
    return {
        "total_quotes": len(quotes),
        "total_boards": total_boards,
        "total_sections": total_sections,
        "quote_numbers": list(quotes.keys())
    }

# ============================================
# ORDER PROCESSING
# ============================================

def extract_order_info(text):
    """Use AI to extract order information"""
    
    prompt = f"""Analyze this order/order acknowledgement and extract key information.

ORDER TEXT:
{text[:8000]}

Extract:
1. job_number: The job/order number (e.g., "E22831")
2. quote_reference: The SAI quote number referenced (look for patterns like "250321SAI02-R04")
3. customer: Customer name
4. description: Product description
5. specs: Extract any specs:
   - ul_type (e.g., "UL891")
   - voltage (e.g., "480/277V")
   - amperage (e.g., "5000A")
   - nema_type (e.g., "NEMA 3R")
   - paint_finish (e.g., "ANSI 61 gray")
   - seismic (true/false)
   - section_count (number)
6. quantity: Units ordered

Return ONLY valid JSON:
{{
    "job_number": "...",
    "quote_reference": "...",
    "customer": "...",
    "description": "...",
    "specs": {{
        "ul_type": "...",
        "voltage": "...",
        "amperage": "...",
        "nema_type": "...",
        "paint_finish": "...",
        "seismic": true,
        "section_count": 5
    }},
    "quantity": 24
}}

Return ONLY the JSON:"""

    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000
        )
        
        result = response.choices[0].message["content"].strip()
        
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        return json.loads(result)
    except Exception as e:
        st.error(f"Error extracting order info: {e}")
        return None

def process_order(text):
    """Process an order and find matching patterns from memory by SPECS"""
    
    # Extract order info
    order_info = extract_order_info(text)
    if not order_info:
        return {"error": "Could not extract order information"}
    
    result = {
        "order_info": order_info,
        "match_method": None,
        "matches": [],
        "box_numbers": []
    }
    
    # Get specs from order
    order_specs = order_info.get("specs", {})
    
    # Search memory for matching specs
    memory = load_memory()
    
    matches = []
    for quote_num, quote_data in memory.get("quotes", {}).items():
        for board in quote_data.get("boards", []):
            board_specs = board.get("specs", {})
            
            # Calculate match score
            score = 0
            match_details = []
            
            # UL Type (must match)
            if order_specs.get("ul_type") and board_specs.get("ul_type"):
                if order_specs["ul_type"].upper() in board_specs["ul_type"].upper() or \
                   board_specs["ul_type"].upper() in order_specs["ul_type"].upper():
                    score += 30
                    match_details.append(f"UL Type: {board_specs['ul_type']}")
            
            # Voltage (must match)
            if order_specs.get("voltage") and board_specs.get("voltage"):
                order_v = order_specs["voltage"].replace(" ", "").upper()
                board_v = str(board_specs["voltage"]).replace(" ", "").upper()
                if order_v == board_v or order_v in board_v or board_v in order_v:
                    score += 25
                    match_details.append(f"Voltage: {board_specs['voltage']}")
            
            # Amperage
            if order_specs.get("amperage") and board_specs.get("amperage"):
                order_a = order_specs["amperage"].replace(" ", "").upper()
                board_a = str(board_specs["amperage"]).replace(" ", "").upper()
                if order_a == board_a:
                    score += 20
                    match_details.append(f"Amperage: {board_specs['amperage']}")
            
            # NEMA Type
            if order_specs.get("nema_type") and board_specs.get("nema_type"):
                order_n = order_specs["nema_type"].replace(" ", "").upper()
                board_n = str(board_specs["nema_type"]).replace(" ", "").upper()
                if order_n in board_n or board_n in order_n:
                    score += 10
                    match_details.append(f"NEMA: {board_specs['nema_type']}")
            
            # Seismic
            order_seismic = order_specs.get("seismic", False)
            board_seismic = board_specs.get("seismic", False)
            if order_seismic == board_seismic:
                score += 10
                match_details.append(f"Seismic: {'Yes' if board_seismic else 'No'}")
            
            # Section count
            if order_specs.get("section_count") and board_specs.get("section_count"):
                if order_specs["section_count"] == board_specs["section_count"]:
                    score += 5
                    match_details.append(f"Sections: {board_specs['section_count']}")
            
            # If score is above threshold, it's a match
            if score >= 50:  # At least UL + Voltage match
                matches.append({
                    "score": score,
                    "from_quote": quote_num,
                    "board_name": board.get("board_name"),
                    "board_specs": board_specs,
                    "match_details": match_details,
                    "sections": board.get("sections", [])
                })
    
    # Sort by score (best match first)
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    if matches:
        result["match_method"] = "specs_match"
        result["matches"] = matches
        
        # Use best match for box numbers
        best_match = matches[0]
        result["best_match"] = best_match
        
        for section in best_match.get("sections", []):
            result["box_numbers"].append({
                "section": section.get("section_id"),
                "dimensions": f"{section.get('height')}×{section.get('width')}×{section.get('depth')}",
                "box_number": section.get("box_number")
            })
    else:
        result["match_method"] = "no_match"
        result["message"] = "No matching board specs found in memory. Process more quotes to build the knowledge base."
    
    return result

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

def extract_board_names(text):
    """First pass: Just identify board names in the quote"""
    
    prompt = f"""Look at the SCOPE OF WORK section of this quote and identify the board names.

RULES:
1. ONLY look in the "SCOPE OF WORK" section of the quote
2. A board is a product being quoted with sections (Section 101, 102, etc.) listed underneath
3. Board names typically include project-specific names like:
   - "EEWRC 12kV SlimVAC Metal Enclosed Main Switchgear"
   - "Substation 1 – 1500kVA"
   - "Main Distribution Switchboard"

DO NOT INCLUDE:
- Generic product names from marketing pages (like just "UL891 Switchboard" or "UL1558 Switchgear" without a project name)
- "Transformer Section" - this is a component within a substation
- "Factory Testing and Services" 
- "Included Accessories"
- Anything from the last few pages that looks like marketing material

QUOTE TEXT:
{text[:50000]}

Return ONLY a JSON array of board names from the SCOPE OF WORK:
["Board Name 1", "Board Name 2"]

Return ONLY the JSON array:

Return ONLY a JSON array of board names found:
["Board Name 1", "Board Name 2", "Board Name 3"]

Return ONLY the JSON array, nothing else:"""

    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        result = response.choices[0].message["content"].strip()
        
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        return json.loads(result)
    except Exception as e:
        st.warning(f"Could not extract board names: {e}")
        return []

def extract_single_board(text, board_name):
    """Extract details for a single board"""
    
    # Limit text length
    if len(text) > 35000:
        text = text[:35000]
    
    prompt = f"""Extract information for ONLY the board named "{board_name}" from this quote.

QUOTE TEXT:
{text}

Extract for this board:
1. BOARD FEATURES:
   - ul_type, phase, wires, voltage, main_bus_amperage, ka_rating
   - nema_type, paint_finish, seismic_inclusions, cable_entry, access_type

2. ALL SECTIONS belonging to this board (Section 101, 102, etc.):
   - identifier, height, width, depth
   - breaker_manufacturer, breaker_type, mounting_type, hardware, description

Return ONLY valid JSON:
{{
    "board_name": "{board_name}",
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
            "description": "..."
        }}
    ]
}}

Return ONLY the JSON:"""

    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=8000
        )
        
        result = response.choices[0].message["content"].strip()
        
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        # Clean up JSON
        result = re.sub(r',\s*}', '}', result)
        result = re.sub(r',\s*]', ']', result)
        
        return json.loads(result)
    except Exception as e:
        st.warning(f"Could not extract board '{board_name}': {e}")
        return None

def extract_quote_data(text):
    """Use AI to extract structured data from quote - chunked approach for large quotes"""
    
    # Step 1: Get all board names
    st.info("Step 1: Identifying boards...")
    board_names = extract_board_names(text)
    
    if not board_names:
        st.warning("No boards found, trying single extraction...")
        # Fallback to single extraction
        return extract_quote_data_single(text)
    
    st.info(f"Found {len(board_names)} board(s): {', '.join(board_names)}")
    
    # Step 2: Extract each board separately
    boards = []
    for i, board_name in enumerate(board_names):
        st.info(f"Step 2: Extracting board {i+1}/{len(board_names)}: {board_name}...")
        board_data = extract_single_board(text, board_name)
        if board_data:
            boards.append(board_data)
    
    return {"boards": boards}

def extract_quote_data_single(text):
    """Fallback: Single extraction for smaller quotes"""
    
    max_chars = 25000
    if len(text) > max_chars:
        text = text[:int(max_chars*0.7)] + "\n\n... [TRUNCATED] ...\n\n" + text[-int(max_chars*0.3):]
    
    prompt = f"""Analyze this switchboard/switchgear quote and extract structured information.

IMPORTANT: Identify ALL BOARDS and ALL SECTIONS.

QUOTE TEXT:
{text}

Return JSON with this structure:
{{
    "boards": [
        {{
            "board_name": "Board Name",
            "board_features": {{
                "ul_type": "...", "phase": "...", "wires": "...", "voltage": "...",
                "main_bus_amperage": "...", "ka_rating": "...", "nema_type": "...",
                "paint_finish": "...", "seismic_inclusions": "...", "cable_entry": "...", "access_type": "..."
            }},
            "sections": [
                {{
                    "identifier": "Section 101", "height": 72, "width": 42, "depth": 56,
                    "breaker_manufacturer": "ABB", "breaker_type": "Emax2",
                    "mounting_type": "Fixed", "hardware": null, "description": "..."
                }}
            ]
        }}
    ]
}}

Return ONLY the JSON:"""

    try:
        response = openai.ChatCompletion.create(
            engine=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=16000
        )
        
        result = response.choices[0].message["content"].strip()
        
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        result = re.sub(r',\s*}', '}', result)
        result = re.sub(r',\s*]', ']', result)
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Try to recover
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
                return json.loads(result[:last_valid_pos])
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
        <h1 style="color: #fff; font-size: 2.5rem;">Pulse AI</h1>
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
    page_title="Pulse AI",
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
if 'mode' not in st.session_state:
    st.session_state.mode = "quote"
if 'order_results' not in st.session_state:
    st.session_state.order_results = None

if not st.session_state.authenticated:
    login_page()
else:
    # Header
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("Sign out"):
            st.session_state.authenticated = False
            st.session_state.results = None
            st.session_state.order_results = None
            st.rerun()
    with col3:
        if st.button("Clear"):
            st.session_state.results = None
            st.session_state.order_results = None
            st.rerun()
    
    # Logo
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h1 style="color: #fff; font-size: 2.5rem; margin: 0;">Pulse AI</h1>
        <p style="color: #6b6b6b; font-size: 0.9rem;">Box Number Generator v2.2</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mode selector
    st.markdown("<p style='color: #888; margin-bottom: 0.5rem;'>Select Mode</p>", unsafe_allow_html=True)
    mode = st.radio("", ["📄 Process Quote", "📦 Process Order", "🧠 View Memory"], 
                    horizontal=True, label_visibility="collapsed")
    
    st.markdown("---")
    
    # ========== QUOTE MODE ==========
    if mode == "📄 Process Quote":
        st.markdown("<p style='color: #888; margin-bottom: 0.5rem;'>Upload Quote PDF</p>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_file = st.file_uploader("", type=['pdf'], label_visibility="collapsed", key="quote_upload")
        with col2:
            process_btn = st.button("Generate Box Numbers", use_container_width=True, disabled=not uploaded_file)
        
        # Process Quote
        if process_btn and uploaded_file:
            kb = load_knowledge_base()
            
            if not kb:
                st.error("Cannot load BoxKnowledge.json")
            else:
                with st.spinner("Reading PDF..."):
                    text = extract_text_from_pdf(uploaded_file)
                
                if text:
                    # Extract quote number from filename or text
                    quote_number = uploaded_file.name.replace(".pdf", "").replace("_", "-")
                    
                    with st.spinner("Analyzing quote with AI..."):
                        quote_data = extract_quote_data(text)
                    
                    if quote_data:
                        boards = quote_data.get("boards", [])
                        
                        # Check for incomplete data
                        incomplete_boards = [b for b in boards if not b.get("sections")]
                        if incomplete_boards:
                            st.warning(f"⚠️ {len(incomplete_boards)} board(s) may have incomplete data.")
                        
                        # Generate box numbers for each section
                        all_boards = []
                        for board in boards:
                            board_name = board.get("board_name", "Unknown Board")
                            board_features = board.get("board_features", {})
                            sections = board.get("sections", [])
                            
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
                        
                        # Save to memory
                        with st.spinner("Saving to memory..."):
                            stored = store_quote_patterns(quote_number, all_boards)
                            if stored:
                                st.success(f"✅ Saved {quote_number} to memory!")
                        
                        st.session_state.results = {
                            "filename": uploaded_file.name,
                            "quote_number": quote_number,
                            "boards": all_boards
                        }
                        st.rerun()
                    else:
                        st.error("Could not extract data from quote")
                else:
                    st.error("Could not read PDF")
        
        # Display Quote Results
        if st.session_state.results:
            results = st.session_state.results
            
            st.markdown(f"### 📄 {results['filename']}")
            
            total_sections = sum(len(b['sections']) for b in results['boards'])
            st.markdown(f"**{len(results['boards'])} board(s), {total_sections} section(s) found**")
            
            for board_idx, board in enumerate(results['boards']):
                board_name = board.get('board_name', 'Unknown Board')
                board_features = board.get('board_features', {})
                sections = board.get('sections', [])
                
                st.markdown(f"""
                <div style="background: #252525; border-left: 4px solid #3b82f6; padding: 1rem 1.5rem; margin: 1.5rem 0 1rem 0; border-radius: 0 8px 8px 0;">
                    <div style="font-size: 1.3rem; font-weight: 700; color: #3b82f6;">📋 {board_name}</div>
                    <div style="color: #888; font-size: 0.85rem;">{len(sections)} section(s)</div>
                </div>
                """, unsafe_allow_html=True)
                
                display_board_features(board_features)
                
                st.markdown("#### 📦 Sections")
                
                for item in sections:
                    display_section_box_number(item['section'], item['box_result'])
                
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
    
    # ========== ORDER MODE ==========
    elif mode == "📦 Process Order":
        st.markdown("<p style='color: #888; margin-bottom: 0.5rem;'>Upload Order PDF</p>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            order_file = st.file_uploader("", type=['pdf'], label_visibility="collapsed", key="order_upload")
        with col2:
            order_btn = st.button("Find Box Numbers", use_container_width=True, disabled=not order_file)
        
        # Process Order
        if order_btn and order_file:
            with st.spinner("Reading order PDF..."):
                text = extract_text_from_pdf(order_file)
            
            if text:
                with st.spinner("Analyzing order and searching memory..."):
                    order_result = process_order(text)
                
                st.session_state.order_results = order_result
                st.rerun()
            else:
                st.error("Could not read PDF")
        
        # Display Order Results
        if st.session_state.order_results:
            result = st.session_state.order_results
            order_info = result.get("order_info", {})
            
            st.markdown("### 📦 Order Information")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Job Number:** {order_info.get('job_number', 'N/A')}")
                st.markdown(f"**Customer:** {order_info.get('customer', 'N/A')}")
                st.markdown(f"**Quantity:** {order_info.get('quantity', 'N/A')}")
            
            specs = order_info.get('specs', {})
            with col2:
                st.markdown(f"**UL Type:** {specs.get('ul_type', 'N/A')}")
                st.markdown(f"**Voltage:** {specs.get('voltage', 'N/A')}")
                st.markdown(f"**Amperage:** {specs.get('amperage', 'N/A')}")
            
            # Show extracted specs
            st.markdown("#### 🔍 Specs Extracted from Order")
            specs_cols = st.columns(6)
            with specs_cols[0]:
                st.markdown(f"**UL Type**<br>{specs.get('ul_type', 'N/A')}", unsafe_allow_html=True)
            with specs_cols[1]:
                st.markdown(f"**Voltage**<br>{specs.get('voltage', 'N/A')}", unsafe_allow_html=True)
            with specs_cols[2]:
                st.markdown(f"**Amperage**<br>{specs.get('amperage', 'N/A')}", unsafe_allow_html=True)
            with specs_cols[3]:
                st.markdown(f"**NEMA**<br>{specs.get('nema_type', 'N/A')}", unsafe_allow_html=True)
            with specs_cols[4]:
                st.markdown(f"**Seismic**<br>{'Yes' if specs.get('seismic') else 'No'}", unsafe_allow_html=True)
            with specs_cols[5]:
                st.markdown(f"**Sections**<br>{specs.get('section_count', 'N/A')}", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Show match results
            if result.get("match_method") == "specs_match":
                best_match = result.get("best_match", {})
                
                st.success(f"✅ Found matching board! Score: {best_match.get('score', 0)}/100")
                
                # Show what matched
                st.markdown("**Matched on:** " + " • ".join(best_match.get("match_details", [])))
                st.markdown(f"**Source Board:** {best_match.get('board_name', 'Unknown')}")
                st.markdown(f"**From Quote:** {best_match.get('from_quote', 'Unknown')}")
                
                st.markdown("### 📋 Box Numbers")
                
                box_numbers = result.get("box_numbers", [])
                if box_numbers:
                    for bn in box_numbers:
                        st.markdown(f"""
                        <div style="background: #1a2e1a; border: 1px solid #2d5a2d; border-radius: 8px; padding: 1rem; margin: 0.5rem 0;">
                            <div style="color: #4ade80; font-weight: 600;">{bn.get('section', 'Unknown Section')}</div>
                            <div style="color: #888; font-size: 0.9rem;">Dimensions: {bn.get('dimensions', 'N/A')}</div>
                            <div style="color: #fff; font-size: 1.3rem; font-family: monospace; margin-top: 0.5rem;">{bn.get('box_number', 'N/A')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Summary table
                    st.markdown("### Summary")
                    summary = [{"Section": bn.get("section"), "Dimensions": bn.get("dimensions"), "Box Number": bn.get("box_number")} for bn in box_numbers]
                    st.table(summary)
                
                # Show other matches
                other_matches = result.get("matches", [])[1:5]  # Next 4 matches
                if other_matches:
                    with st.expander("Other Potential Matches"):
                        for match in other_matches:
                            st.markdown(f"**{match.get('board_name')}** (Score: {match.get('score')}) - From: {match.get('from_quote')}")
            
            elif result.get("match_method") == "no_match":
                st.error(f"❌ {result.get('message', 'No matching specs found in memory')}")
                st.info("💡 **Tip:** Process more quotes to build the knowledge base. The system learns from every quote you process.")
    
    # ========== MEMORY VIEW MODE ==========
    elif mode == "🧠 View Memory":
        st.markdown("### 🧠 Persistent Memory")
        
        # Connection status
        st.markdown("#### Connection Status")
        col1, col2 = st.columns(2)
        with col1:
            if BLOB_AVAILABLE:
                st.success("✅ Azure Blob library installed")
            else:
                st.error("❌ Azure Blob library NOT installed")
        with col2:
            if AZURE_STORAGE_CONNECTION_STRING:
                st.success("✅ Connection string configured")
            else:
                st.error("❌ Connection string NOT configured")
        
        st.markdown("---")
        
        # Stats
        stats = get_memory_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Quotes Stored", stats.get("total_quotes", 0))
        with col2:
            st.metric("Total Boards", stats.get("total_boards", 0))
        with col3:
            st.metric("Total Sections", stats.get("total_sections", 0))
        
        st.markdown("---")
        st.markdown("#### Stored Quotes")
        
        quote_numbers = stats.get("quote_numbers", [])
        if quote_numbers:
            for qn in quote_numbers:
                st.markdown(f"- `{qn}`")
        else:
            st.info("No quotes stored yet. Process a quote to add it to memory.")
        
        st.markdown("---")
        
        # Manual lookup
        st.markdown("#### 🔍 Quick Lookup")
        lookup_quote = st.text_input("Enter quote number to lookup:")
        if st.button("Search") and lookup_quote:
            found = find_quote_in_memory(lookup_quote)
            if found:
                st.success(f"Found! Processed: {found.get('processed_at', 'Unknown')}")
                for board in found.get("boards", []):
                    st.markdown(f"**{board.get('board_name')}**")
                    st.markdown(f"Specs: {board.get('specs', {})}")
                    for section in board.get("sections", []):
                        st.markdown(f"  - {section.get('section_id')}: `{section.get('box_number')}`")
            else:
                st.error("Quote not found in memory")
        
        # Test connection button
        st.markdown("---")
        if st.button("🧪 Test Blob Connection"):
            blob_client = get_blob_client()
            if blob_client:
                try:
                    # Try to read existing data
                    memory = load_memory()
                    st.success(f"✅ Connection works! Found {len(memory.get('quotes', {}))} quotes in memory.")
                except Exception as e:
                    st.error(f"❌ Test failed: {e}")
    
    # Footer
    st.markdown("""
    <div style="text-align: center; color: #6b6b6b; font-size: 0.8rem; padding: 2rem 0;">
        SAI Advanced Power Solutions • Powerd By Baby Goats
    </div>
    """, unsafe_allow_html=True)
