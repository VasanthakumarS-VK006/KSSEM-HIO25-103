import json
import os
from datetime import datetime, timedelta

import certifi
import jwt
import requests
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from langchain.docstore.document import Document
from langchain_chroma import Chroma
# --- LangChain Imports for Free, Local NLP Search ---
from langchain_huggingface import HuggingFaceEmbeddings
from thefuzz import process

# Force SSL certificate path
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

patients_db = {}
records_db = {}

PRIVATE_KEY = None
with open("private_key.pem", "r") as key_file:
    PRIVATE_KEY = key_file.read()

PUBLIC_KEY = open("public_key.pem", "r").read()
# --- Fallback for extraFunctions ---
# This ensures the app runs even if extraFunctions.py is missing,
# although the NAMC-to-ICD converter will return empty results.
try:
    from extraFunctions import getICDDetailsFromEnglishDefinition
except ImportError:
    print("Warning: 'extraFunctions.py' not found. The NAMC-to-ICD endpoint will not return ICD codes.")
    def getICDDetailsFromEnglishDefinition(term, code):
        return []

with open("private_key.pem", "r") as key_file:
    PRIVATE_KEY = key_file.read()


# =================================================================
# 1. FLASK APP INITIALIZATION & HELPERS
# =================================================================
app = Flask(__name__)
CORS(app)

DEFAULT_DOCTOR_CODE = "DR987654"
DEFAULT_PATIENT_CODE = "PAT123456"
LOG_FILE_NAME = "search_log.txt"

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



# NOTE: It creates a token and gives it to the frontend
@app.route("/api/generate-token", methods=["POST"])
def generate_token():
    data = request.get_json()
    abha_number = data.get("abha_number", "12345678901234")
    abha_address = data.get("abha_address", "patient@sbx")
    name = data.get("name", "User")
    
    payload = {
        "iss": "https://sandbox.abdm.gov.in",
        "sub": abha_number,
        "aud": "facility",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24),
        "abha_number": abha_number,
        "abha_address": abha_address,
        "name": name,
        "kycStatus": "VERIFIED"
    }
    
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    
    return jsonify({"token": token})

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



# --- Load all data ONCE at startup ---
ALL_NAMC_CONCEPTS = load_all_namc_data()

# =================================================================
# 2. LANGCHAIN NLP SETUP (with Persistent Storage)
# =================================================================
print("\nInitializing LangChain components...")

CHROMA_PERSIST_DIR = "chroma_db_persistent"
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = None
retriever = None

# Check if a persistent database already exists
if os.path.exists(CHROMA_PERSIST_DIR):
    try:
        print(f"🧠 Loading existing vector store from '{CHROMA_PERSIST_DIR}'...")
        vectorstore = Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embedding_function)
        print("✅ Vector store loaded successfully from disk.")
    except Exception as e:
        print(f"❌ Error loading from existing Chroma directory: {e}. Will attempt to rebuild.")
        vectorstore = None

# If loading failed or directory doesn't exist, create a new one
if not vectorstore:
    print("No valid vector store found. Creating a new one...")
    if ALL_NAMC_CONCEPTS:
        # Prepare documents for LangChain
        docs = [
            Document(
                # Embed both the display name and its definition for better semantic context
                page_content=f"{c.get('display')}: {c.get('designation')[0].get('value')}",
                metadata={
                    "code": c.get("code"),
                    "display": c.get("display"),
                    "system": c.get("system")
                }
            ) for c in ALL_NAMC_CONCEPTS if c.get('designation')
        ]
        
        print(f"⚙️ Creating vectors and saving to disk... (This may take a moment on the very first run)")
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embedding_function,
            persist_directory=CHROMA_PERSIST_DIR
        )
        print(f"✅ New vector store created and saved to '{CHROMA_PERSIST_DIR}'.")
    else:
        print("⚠️ CRITICAL: No NAMC data was loaded. Cannot create vector store for NLP search.")

# Create a retriever from the vector store if it exists
if vectorstore:
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) # Retrieve top 5 results
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

PUBLIC_KEY = open("public_key.pem", "r").read()

@app.route("/static/swagger.json")
def swagger_spec():
    spec = {"openapi": "3.0.0", "info": {"title": "EMR API", "version": "1.0"}, "paths": {}}
    return jsonify(spec)

# --- Main Application Route ---
@app.route("/")
def home():
    return render_template("index2.html")


@app.route('/register', methods=['POST'])
def register_patient():
    """
    Register a patient with ABHA number
    
    curl -X POST http://localhost:5000/register \
      -H "Content-Type: application/json" \
      -d '{"abha": "12345678901234", "name": "John Doe"}'
    """
    data = request.get_json()
    abha = data['abha']
    name = data['name']
    
    # Store patient
    patients_db[abha] = {
        'abha': abha,
        'name': name,
        'consent': False  # Not consented yet
    }
    
    return jsonify({
        'message': 'Patient registered',
        'abha': abha,
        'name': name
    }), 201


@app.route('/consent', methods=['POST'])
def give_consent():
    """
    Patient gives consent to share data
    
    curl -X POST http://localhost:5000/consent \
      -H "Content-Type: application/json" \
      -d '{"abha": "12345678901234"}'
    """
    data = request.get_json()
    abha = data['abha']
    
    if abha not in patients_db:
        return jsonify({'error': 'Patient not found'}), 404
    
    # Activate consent
    patients_db[abha]['consent'] = True
    
    return jsonify({
        'message': 'Consent given',
        'abha': abha,
        'consent_status': 'ACTIVE'
    }), 200


@app.route('/save-diagnosis', methods=['POST'])
def save_diagnosis():
    """
    Save patient diagnosis with NAMC and ICD-11 codes
    
    curl -X POST http://localhost:5000/save-diagnosis \
      -H "Content-Type: application/json" \
      -d '{
        "abha": "12345678901234",
        "diagnosis": "Jaundice",
        "namc_code": "ABB1.1",
        "icd_code": "ME20.1"
      }'
    """
    data = request.get_json()
    abha = data['abha']
    
    # Check if patient exists and has consent
    if abha not in patients_db:
        return jsonify({'error': 'Patient not found'}), 404
    
    if not patients_db[abha]['consent']:
        return jsonify({'error': 'No consent given'}), 403
    
    # Save record
    record = {
        'diagnosis': data['diagnosis'],
        'namc_code': data['namc_code'],
        'icd_code': data['icd_code'],
        'date': datetime.now().isoformat()
    }
    
    if abha not in records_db:
        records_db[abha] = []
    
    records_db[abha].append(record)
    
    return jsonify({
        'message': 'Diagnosis saved',
        'namc': data['namc_code'],
        'icd': data['icd_code']
    }), 201


@app.route('/get-health-data', methods=['GET'])
def get_health_data():
    """
    Retrieve patient health data
    
    curl -X GET "http://localhost:5000/get-health-data?abha=12345678901234"
    """
    abha = request.args.get('abha')
    
    # Check if patient exists and has consent
    if abha not in patients_db:
        return jsonify({'error': 'Patient not found'}), 404
    
    if not patients_db[abha]['consent']:
        return jsonify({'error': 'No consent'}), 403
    
    # Get records
    records = records_db.get(abha, [])
    
    # Build simple FHIR-like response
    response = {
        'patient': {
            'id': abha,
            'name': patients_db[abha]['name']
        },
        'diagnoses': records,
        'total_records': len(records)
    }
    
    return jsonify(response), 200


@app.route('/patients', methods=['GET'])
def get_all_patients():
    """Just for debugging"""
    return jsonify(patients_db), 200


# --- New LangChain NLP Search Endpoint ---
@app.route("/api/nlp_search", methods=["POST"])
def nlp_search():
    if not retriever:
        return jsonify({"error": "NLP Search is not available due to a server setup error. Check logs."}), 500
    
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing 'query' in request body."}), 400

    # Use the retriever to find relevant documents
    relevant_docs = retriever.invoke(query)
    
    # Format results for the frontend
    results = [{
        "code": doc.metadata.get("code"),
        "display": doc.metadata.get("display"),
        "system": doc.metadata.get("system"),
        "full_definition": doc.page_content,
    } for doc in relevant_docs]

    log_search_activity(f"NLP Search: '{query}'", f"Found {len(results)} results.")
    return jsonify(results)

# --- Original Converter Endpoints (Unchanged) ---
@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Provides simple autocomplete suggestions for the NAMC-to-ICD converter."""

    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header[7:]

    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer="https://sandbox.abdm.gov.in",
            audience="facility"
        )
        # Check custom claim
        if payload.get("kycStatus") != "VERIFIED":
            return jsonify({"error": "KYC not verified"}), 403


    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401


    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    suggestions = []
    for item in ALL_NAMC_CONCEPTS:
        if query in item.get("display", "").lower() or query in item.get("code", "").lower():
            suggestions.append([
                item.get("code"),
                f'{item.get("system")}: {item.get("display")}',
                item.get("designation")[0].get("value")
            ])
    return jsonify(suggestions[:50])

@app.route("/api/submit", methods=["POST"])
def namc_to_icd():
    """NAMC to ICD conversion endpoint."""

    auth_header = request.headers.get('Authorization')
    if auth_header:
        print(auth_header)
    request_data = request.get_json()
    items = request_data.get("term", "").split(",")
    namc_code = items[0].strip()
    english_term_full = items[1].strip()
    english_term = english_term_full.split(": ", 1)[-1]
    
    data = getICDDetailsFromEnglishDefinition(english_term, namc_code)
    
    result_summary = f"Found {len(data)} result(s)"
    if data:
        result_summary += f" (e.g., '{data[0][0]}')"
    log_search_activity(f"NAMC->ICD: '{english_term}'", result_summary)
    return jsonify(data)

@app.route("/api/ICDtoNAMC")
def icd_to_namc():
    """ICD to NAMC conversion endpoint."""
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Query parameter 'q' is missing."}), 400
    try:
        # Extract the descriptive term from the ICD input
        term = query.split(",")[1].strip()
    except IndexError:
        term = query.strip()
    
    # Use fuzzy string matching to find the best NAMC terms
    choices = {f"{c.get('system')}: {c.get('display')}": c for c in ALL_NAMC_CONCEPTS}
    matches = process.extract(term, choices.keys(), limit=10)
    
    results = []
    for match_term, score in matches:
        concept = choices[match_term]
        results.append({
            "code": concept.get("code"),
            "term": match_term,
            "score": score,
            "definition": concept.get("designation")[0].get("value")
        })
    log_search_activity(f"ICD->NAMC: '{term}'", f"Found {len(results)} fuzzy matches.")
    return jsonify(results)


@app.route("/emr")
def emr():
    return render_template("emr.html")

@app.route("/csvUpload", methods=['POST', 'GET'])
def csvUpload():
    if request.method == "POST":
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header[7:]

        try:
            payload = jwt.decode(
                token,
                PUBLIC_KEY,
                algorithms=["RS256"],
                issuer="https://sandbox.abdm.gov.in",
                audience="facility"
            )
            # Check custom claim
            if payload.get("kycStatus") != "VERIFIED":
                return jsonify({"error": "KYC not verified"}), 403


        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # After the token validation is valid
        if 'csv_file' in request.files:
            file = request.files['csv_file']
            hfr_id = request.form.get("hfr_id", "IN1234534343")
            filename = os.path.join("Data", hfr_id + ".csv")
            file.save(filename)
            print("received")
            return jsonify({"message" : "success"})

    

# =================================================================
# 4. RUN THE APPLICATION
# =================================================================
if __name__ == "__main__":
    app.run(debug=True)
