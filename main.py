import json
import os
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from thefuzz import process
import requests
from werkzeug.utils import secure_filename 

# --- EasyOCR Imports (REVERTED from Tesseract) ---
import easyocr 
# ---------------------------------------------------

# --- LangChain Imports for Free, Local NLP Search ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

# --- Fallback for extraFunctions ---
try:
    from extraFunctions import getICDDetailsFromEnglishDefinition
except ImportError:
    print("Warning: 'extraFunctions.py' not found. The NAMC-to-ICD endpoint will not return ICD codes.")
    def getICDDetailsFromEnglishDefinition(term, code):
        return []

# =================================================================
# 1. FLASK APP INITIALIZATION & HELPERS
# =================================================================
app = Flask(__name__)
CORS(app)

DEFAULT_DOCTOR_CODE = "DR987654"
DEFAULT_PATIENT_CODE = "PAT123456"
LOG_FILE_NAME = "search_log.txt"
CONCEPT_MAP_FILE = "Data/NAMC_to_ICD11_MultiThreaded_ConceptMap.json" 

# --- OCR Configuration ---
# Use a temporary directory for file uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp_uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # EasyOCR works best with image formats
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# --- End OCR Configuration ---

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_search_activity(search_term, result_summary):
    """Logs search activity to a text file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (
        f"Timestamp: {timestamp} | DoctorID: {DEFAULT_DOCTOR_CODE} | "
        f"PatientID: {DEFAULT_PATIENT_CODE} | SearchTerm: {search_term} | "
        f"Result: {result_summary}\n"
    )
    try:
        with open(LOG_FILE_NAME, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log file: {e}")

def load_all_namc_data():
    """Loads and combines concept data from Siddha, Ayurveda, and Unani JSON files."""
    all_concepts = []
    systems_to_load = {
        "Siddha": "Data/SiddhaJson.json",
        "Ayurveda": "Data/AyurvedaJson.json",
        "Unani": "Data/UnaniJson.json"
    }
    for system_name, file_path in systems_to_load.items():
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
                concepts = data.get("concept", [])
                for concept in concepts:
                    concept['system'] = system_name
                all_concepts.extend(concepts)
                print(f"✅ Successfully loaded {len(concepts)} concepts from {file_path}")
        except FileNotFoundError:
            print(f"⚠️ Warning: The file {file_path} was not found. Skipping.")
        except json.JSONDecodeError as e:
            print(f"❌ Error: Could not parse {file_path}. Error: {e}")
    return all_concepts


# --- ConceptMap Loading ---
def load_and_process_concept_map(file_path):
    """
    Loads the FHIR ConceptMap and processes it into a simple
    dictionary { namc_display: { namc_code: "...", targets: [...] } }
    """
    print(f"Loading ConceptMap for conversion ({file_path})...")
    processed_map = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        elements = data.get("group", [{}])[0].get("element", [])
        
        for item in elements:
            namc_display = item.get("display") # This is the KEY, e.g., "Siddha: Jaundice"
            namc_code = item.get("code")
            targets = item.get("target", [])
            
            simple_targets = []
            for t in targets:
                simple_targets.append({
                    "code": t.get("code"),
                    "display": t.get("display")
                })
            
            if namc_display:
                processed_map[namc_display] = {
                    "namc_code": namc_code,
                    "targets": simple_targets
                }
        print(f"✅ Successfully processed {len(processed_map)} NAMC terms from ConceptMap.")
        return processed_map
        
    except FileNotFoundError:
        print(f"--- ❌ ERROR: {file_path} not found. Local conversion will fail. ---")
        return {}
    except Exception as e:
        print(f"--- ❌ ERROR: Failed to parse {file_path}: {e} ---")
        return {}

# --- ICD -> NAMC reverse map ---
def create_icd_to_namc_map(processed_concept_map, all_namc_concepts):
    """
    Creates a reverse lookup map from ICD Code -> [NAMC Concepts]
    for fast ICD-to-NAMC conversion.
    """
    print("Building ICD-to-NAMC reverse map...")
    icd_to_namc_map = {}
    
    # Create a quick lookup for vernacular definitions
    definition_lookup = {}
    for concept in all_namc_concepts:
        if concept.get('display') and concept.get('designation'):
            designation_list = concept.get('designation', [])
            if designation_list:
                definition_lookup[concept.get('display')] = designation_list[0].get('value', '')

    # Iterate through the ConceptMap and build the reverse map
    for namc_display, data in processed_concept_map.items():
        namc_code = data.get("namc_code")
        # namc_system_display IS the key, e.g., "Siddha: Jaundice"
        namc_system_display = namc_display 
        
        # We need to find the original concept to get the definition
        namc_definition = ""
        for concept in all_namc_concepts:
             if f"{concept.get('system')}: {concept.get('display')}" == namc_system_display:
                designation_list = concept.get('designation', [])
                if designation_list:
                    namc_definition = designation_list[0].get('value', '')
                break
        
        for target in data.get("targets", []):
            icd_code = target.get("code")
            if not icd_code:
                continue
                
            if icd_code not in icd_to_namc_map:
                icd_to_namc_map[icd_code] = []
                
            # Add the NAMC term to this ICD code's list
            icd_to_namc_map[icd_code].append({
                "code": namc_code,
                "term": namc_system_display,
                "score": 101, # Mark as a high-quality map result
                "definition": namc_definition
            })
            
    print(f"✅ Reverse map built. {len(icd_to_namc_map)} ICD codes mapped.")
    return icd_to_namc_map


# --- WHO API Helpers (for Flexisearch) ---
def _get_who_api_token_helper():
    """Internal helper to get a WHO token for server-side calls."""
    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    client_id = '42000a86-ed11-4082-8408-31fe933baa5a_a498c5fb-3ea8-4b0f-b221-05aaacb39be6'
    client_secret = 'aeRcA/gMcEaKLkjxFhLBpbC9UmJmHyuYlK7YWhIPIxw='
    payload = {'client_id': client_id, 'client_secret': client_secret, 'scope': 'icdapi_access', 'grant_type': 'client_credentials'}
    try:
        r = requests.post(token_endpoint, data=payload, timeout=10)
        r.raise_for_status()
        return r.json().get('access_token')
    except Exception as e:
        print(f"Error getting WHO token: {e}")
        return None

def get_icd_details_from_who_api(term):
    """This is the 'Server Search' (Flexisearch) fallback from server.py."""
    token = _get_who_api_token_helper()
    if not token:
        return [{"error": "Failed to acquire WHO API access token."}]
    try:
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json', 'Accept-Language': 'en', 'API-Version': 'v2'}
        uri = f"https://id.who.int/icd/release/11/2024-01/mms/search?q={term}&useFlexisearch=true&flatResults=true"
        
        print(f"Performing WHO flexissearch for: {term}")
        response = requests.get(uri, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        flexi_entities = data if isinstance(data, list) else data.get("destinationEntities", [])
        
        for item in flexi_entities:
            title = item.get("title")
            code = item.get("theCode")
            if title and code:
                results.append({
                    "icd_code": code,
                    "title": re.sub(r'<.*?>', '', title)
                })
        
        print(f"Found {len(results)} flexisearch results.")
        return results[:20]

    except Exception as e:
        print(f"Error in WHO API search: {e}")
        return [{"error": f"API request failed: {e}"}]


# --- Token endpoint (for client-side calls) ---
@app.route("/api/newToken")
def new_token():
    """Fetches a new access token from the WHO ICD API with error handling."""
    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    client_id = '42000a86-ed11-4082-8408-31fe933baa5a_a498c5fb-3ea8-4b0f-b221-05aaacb39be6'
    client_secret = 'aeRcA/gMcEaKLkjxFhLBpbC9UmJmHyuYlK7YWhIPIxw='
    payload = {
        'client_id': client_id, 'client_secret': client_secret,
        'scope': 'icdapi_access', 'grant_type': 'client_credentials'
    }
    try:
        response = requests.post(token_endpoint, data=payload)
        response.raise_for_status()
        token_data = response.json()
        return jsonify({"token": token_data['access_token']})
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error from WHO server: {err.response.status_code} - {err.response.text}")
        return jsonify({"error": "Failed to authenticate with WHO API."}), err.response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Network error connecting to WHO server: {e}")
        return jsonify({"error": "Cannot connect to the token service."}), 503
    except (KeyError, json.JSONDecodeError):
        print("Unexpected response from WHO server: 'access_token' not found or invalid JSON.")
        return jsonify({"error": "Invalid response from token service."}), 500
    
# --- EasyOCR Function (REVERTED) ---
# Initialize EasyOCR reader once globally for efficiency
# This line can be moved inside process_image if you encounter issues
# but globally is generally more efficient for Flask apps.
print("Initializing EasyOCR reader (this may take a moment)...")
reader = easyocr.Reader(['en']) # 'en' for English. Add more languages if needed, e.g., ['en', 'hi']
print("EasyOCR reader initialized.")


def process_image(image_path):
    """
    Extract text from image using EasyOCR and parse relevant medical info.

    Args:
        image_path (str): The path to the image file.

    Returns:
        tuple: (extracted_info_dict, None, raw_text) or (None, error_message, None) on error.
    """
    try:
        # EasyOCR performs OCR on the image and returns bounding box detections
        print(f"Starting EasyOCR on {image_path}...")
        results = reader.readtext(image_path)
        print("EasyOCR completed.")

        # Join all detected text into a single string for parsing
        full_text = " ".join([res[1] for res in results])
        
        # Clean up the text
        text = full_text.replace('|', '').replace('=', ':').replace('_', ' ')
        text = text.strip()
        
        # --- Start of original data parsing logic (Remains the same) ---
        # Initialize result structure
        info = {
            "Report Type": "",
            "Date": "",
            "Patient Info": {
                "Name": "",
                "Age": "",
                "Sex": "",
                "Previous Hospital": "",
                "Symptoms": "",
                "Signs": ""
            },
            "Test Results": {},
            "Interpretation": "",
            "Summary": ""
        }
        
        lines = text.split('\n')
        test_results = {}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Extract Report Type
            if "LABORATORY REPORT" in line.upper():
                info["Report Type"] = line.strip()
            
            # Extract Date
            if "Date" in line:
                # Common regex for date formats (d/m/yy, dd-mm-yyyy, etc.)
                date_match = re.search(r'Date[:\s=]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
                if date_match:
                    info["Date"] = date_match.group(1).strip()
            
            # Extract Patient Info
            # Name (inline like 'Name: John Doe' or 'Patient Name: John Doe')
            if re.search(r'\b(?:Name|Patient Name|Patient)[:\s-]+', line, re.I):
                name_match = re.search(r'\b(?:Name|Patient Name|Patient)[:\s-]+(.+)', line, re.I)
                if name_match:
                    info["Patient Info"]["Name"] = name_match.group(1).strip()
                    continue
            # Previous Hospital / Referred from
            if re.search(r'\b(?:Previous Hospital|Referred from|Referring Hospital|Ref Hospital|Refd from)[:\s-]+', line, re.I):
                ph_match = re.search(r'\b(?:Previous Hospital|Referred from|Referring Hospital|Ref Hospital|Refd from)[:\s-]+(.+)', line, re.I)
                if ph_match:
                    info["Patient Info"]["Previous Hospital"] = ph_match.group(1).strip()
                    continue

            if "Age" in line:
                age_match = re.search(r'Age[:\s=]+(\d+)', line)
                if age_match:
                    info["Patient Info"]["Age"] = age_match.group(1).strip()
            elif "Sex" in line:
                sex_match = re.search(r'Sex[:\s=]+(\w+)', line)
                if sex_match:
                    info["Patient Info"]["Sex"] = sex_match.group(1).strip()
            # Symptoms: handle inline 'Symptoms: fever, cough' or multi-line lists
            elif re.search(r'\b(symptoms|presenting complaint|complaints)[:\s]*', line, re.I):
                # If inline after colon
                parts = re.split(r'[:]', line, maxsplit=1)
                if len(parts) == 2 and parts[1].strip():
                    info["Patient Info"]["Symptoms"] = parts[1].strip()
                else:
                    symptoms = []
                    j = i + 1
                    # stop when next section header likely appears (uppercase words followed by ':' or known keywords)
                    while j < len(lines):
                        nxt = lines[j].strip()
                        if not nxt:
                            break
                        if re.match(r'^[A-Z][A-Za-z ]{0,50}:', nxt) or any(k in nxt.lower() for k in ["signs", "interpretation", "summary", "test results", "date", "age", "sex"]):
                            break
                        symptoms.append(nxt)
                        j += 1
                    info["Patient Info"]["Symptoms"] = ", ".join(symptoms)
            elif "Signs" in line:
                signs = []
                j = i + 1
                while j < len(lines) and not any(key in lines[j].lower() for key in ["symptoms", "color", "consistency"]):
                    if lines[j].strip():
                        signs.append(lines[j].strip())
                    j += 1
                info["Patient Info"]["Signs"] = ", ".join(signs)
            
            # Extract Test Results
            if any(x in line.lower() for x in ["color", "consistency", "bacterial", "leukocytes", "blood", "parasites"]):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    test_results[key] = value
            
            # Extract Interpretation
            if "Interpretation" in line:
                interpretation_lines = []
                j = i + 1
                # Stop if next line is empty or looks like another section
                while j < len(lines) and lines[j].strip() and not re.search(r'^[A-Z][A-Za-z ]{0,50}:', lines[j].strip()):
                    interpretation_lines.append(lines[j].strip())
                    j += 1
                info["Interpretation"] = " ".join(interpretation_lines)
            
            # Extract Summary
            if "summary" in line.lower():
                summary_lines = []
                j = i
                # Stop if next line is empty or looks like another section
                while j < len(lines) and lines[j].strip() and not re.search(r'^[A-Z][A-Za-z ]{0,50}:', lines[j].strip()):
                    summary_lines.append(lines[j].strip())
                    j += 1
                info["Summary"] = " ".join(summary_lines)
        
        info["Test Results"] = test_results
        
        # Fallback for simple name extraction if not found in specific searches
        if not info["Patient Info"]["Name"] and len(lines) > 0:
            name_match = re.search(r'Patient\s+Name[:\s]*([A-Za-z\s]+)', text, re.I)
            if name_match:
                info["Patient Info"]["Name"] = name_match.group(1).strip()

        return info, None, text
        
    except Exception as e:
        print(f"Error processing image with EasyOCR: {e}")
        return None, f"Error during OCR processing: {e}", None


# =================================================================
# 2. LOAD DATA & INITIALIZE NLP
# =================================================================

# --- Load all data ONCE at startup ---
ALL_NAMC_CONCEPTS = load_all_namc_data()
PROCESSED_CONCEPT_MAP = load_and_process_concept_map(CONCEPT_MAP_FILE)
ICD_TO_NAMC_MAP = create_icd_to_namc_map(PROCESSED_CONCEPT_MAP, ALL_NAMC_CONCEPTS)


# --- LangChain NLP Setup (with Persistent Storage) ---
print("\nInitializing LangChain components...")

CHROMA_PERSIST_DIR = "chroma_db_persistent"
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = None
retriever = None

if os.path.exists(CHROMA_PERSIST_DIR):
    try:
        print(f"🧠 Loading existing vector store from '{CHROMA_PERSIST_DIR}'...")
        vectorstore = Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embedding_function)
        print("✅ Vector store loaded successfully from disk.")
    except Exception as e:
        print(f"❌ Error loading from existing Chroma directory: {e}. Will attempt to rebuild.")
        vectorstore = None

if not vectorstore:
    print("No valid vector store found. Creating a new one...")
    if ALL_NAMC_CONCEPTS:
        docs = []
        for c in ALL_NAMC_CONCEPTS:
             if c.get('designation'):
                designation_list = c.get('designation', [])
                if designation_list:
                    docs.append(Document(
                        page_content=f"{c.get('display')}: {designation_list[0].get('value')}",
                        metadata={
                            "code": c.get("code"),
                            "display": c.get("display"),
                            "system": c.get("system")
                        }
                    ))
        
        print(f"⚙️ Creating vectors from {len(docs)} documents and saving to disk...")
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embedding_function,
            persist_directory=CHROMA_PERSIST_DIR
        )
        print(f"✅ New vector store created and saved to '{CHROMA_PERSIST_DIR}'.")
    else:
        print("⚠️ CRITICAL: No NAMC data was loaded. Cannot create vector store for NLP search.")

if vectorstore:
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) 
    print("✅ NLP semantic search is ready to use.")
else:
    retriever = None

# =================================================================
# 3. API ENDPOINTS
# =================================================================

# --- Swagger UI Setup ---
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "EMR API"})
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)

@app.route("/static/swagger.json")
def swagger_spec():
    spec = {"openapi": "3.0.0", "info": {"title": "EMR API", "version": "1.0"}, "paths": {}}
    return jsonify(spec)

# --- Main Application Route ---
@app.route("/")
def home():
    # Assuming frontend.html is in the 'templates' folder
    return render_template("index.html") 

# --- New OCR Upload Endpoint ---
@app.route('/api/ocr_upload', methods=['POST'])
def ocr_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or no selected file"}), 400

    filepath = None
    try:
        # Securely save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the image using EasyOCR
        extracted_info, error_message, _ = process_image(filepath)
        
        if extracted_info:
            return jsonify(extracted_info)
        elif error_message:
            return jsonify({"error": error_message}), 500
        else:
            return jsonify({"error": "OCR failed to extract structured data."}), 500
            
    except Exception as e:
        print(f"Error in OCR upload: {e}")
        return jsonify({"error": f"Internal server error during OCR: {str(e)}"}), 500
    finally:
        # Clean up the temporary file
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            print(f"Cleaned up temporary file: {filepath}")

# --- LangChain NLP Search Endpoint ---
@app.route("/api/nlp_search", methods=["POST"])
def nlp_search():
    if not retriever:
        return jsonify({"error": "NLP Search is not available due to a server setup error. Check logs."}), 500
    
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing 'query' in request body."}), 400

    relevant_docs = retriever.invoke(query)
    
    results = [{
        "code": doc.metadata.get("code"),
        "display": doc.metadata.get("display"),
        "system": doc.metadata.get("system"),
        "full_definition": doc.page_content,
    } for doc in relevant_docs]

    log_search_activity(f"NLP Search: '{query}'", f"Found {len(results)} results.")
    return jsonify(results)

# --- Autocomplete Suggestions Endpoint ---
@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Provides simple autocomplete suggestions for the NAMC-to-ICD converter."""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    suggestions = []
    for item in ALL_NAMC_CONCEPTS:
        # Check display, code, and vernacular
        display_name = item.get("display", "").lower()
        code = item.get("code", "").lower()
        definition = ""
        designation_list = item.get("designation", [])
        if designation_list:
            definition = designation_list[0].get("value", "")
        
        vernacular = definition.lower()

        if query in display_name or query in code or query in vernacular:
            suggestions.append([
                item.get("code"),
                f'{item.get("system")}: {item.get("display")}',
                definition
            ])
    return jsonify(suggestions[:50])

# --- NAMC-to-ICD Endpoint (Map -> Flexisearch) ---
@app.route("/api/submit", methods=["POST"])
def namc_to_icd():
    """
    NAMC to ICD conversion endpoint with ConceptMap -> Flexisearch fallback.
    Returns a JSON object with 'source' and 'data'.
    """
    request_data = request.get_json()
    # The term is the full string from the suggestion box
    # e.g., ["AA8","Siddha: Hepatic disease...","Azhuman ceyarkai..."]
    term_parts = request_data.get("term", "").split(",")
    
    if len(term_parts) < 2:
        return jsonify({"error": "Invalid term format. Expected 'CODE,System: Display,...'"}), 400

    namc_code = term_parts[0].strip()
    # The display key is the second part
    namc_display_key = term_parts[1].strip() 
    
    data = []
    source = "none"
    
    # --- Step 1: Check the local ConceptMap first ---
    map_result = PROCESSED_CONCEPT_MAP.get(namc_display_key)
    
    if map_result and map_result.get("targets"):
        # Found in ConceptMap!
        print(f"ConceptMap HIT for: {namc_display_key}")
        targets = map_result.get("targets", [])
        data = [[target.get("code"), target.get("display")] for target in targets]
        source = "map"
        log_search_activity(f"NAMC->ICD (Map): '{namc_display_key}'", f"Found {len(data)} map results.")
        
    else:
        # --- Step 2: Not in map, try WHO Flexisearch automatically ---
        print(f"ConceptMap MISS. Falling back to WHO Flexisearch for: {namc_display_key}")
        
        # Get the part after "System: ", e.g., "Hepatic disease..."
        english_term_only = namc_display_key.split(": ", 1)[-1]
        
        flexi_results = get_icd_details_from_who_api(english_term_only)
        
        data = [
            [result.get("icd_code"), result.get("title")] 
            for result in flexi_results 
            if "error" not in result and result.get("icd_code")
        ]
        
        if data:
            source = "flexi"
            log_search_activity(f"NAMC->ICD (Flexi): '{english_term_only}'", f"Found {len(data)} flexi results.")

    return jsonify({"source": source, "data": data})

# --- ICD-to-NAMC Endpoint (Map-Only) ---
@app.route("/api/ICDtoNAMC")
def icd_to_namc():
    """
    ICD to NAMC conversion endpoint.
    Uses *only* the pre-built ConceptMap for fast lookups.
    NO fuzzy search fallback.
    """
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Query parameter 'q' is missing."}), 400
    
    icd_code = ""
    results = []
    
    try:
        # Parse code, e.g., "DB44, Type 1 diabetes" or just "DB44"
        icd_code = query.split(",")[0].strip()
    except Exception:
        pass

    # --- Step 1: Check the ConceptMap using the ICD code ---
    if icd_code:
        results = ICD_TO_NAMC_MAP.get(icd_code, []) 
    
    if results:
        print(f"ReverseMap HIT for ICD code: {icd_code}")
        log_search_activity(f"ICD->NAMC (Map): '{icd_code}'", f"Found {len(results)} map results.")
    else:
        print(f"ReverseMap MISS for ICD code: {icd_code}")
        log_search_activity(f"ICD->NAMC (Map): '{icd_code}'", "No map results found.")
            
    return jsonify(results)

# =================================================================
# 4. RUN THE APPLICATION
# =================================================================
if __name__ == "__main__":
    app.run(debug=True)