import json
from datetime import datetime
import requests
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from thefuzz import process

# Assuming this function exists in an 'extraFunctions.py' file, but it's only used for one endpoint now.
from extraFunctions import getICDDetailsFromEnglishDefinition

app = Flask(__name__)
CORS(app)

# --- Default Codes and Log File ---
DEFAULT_DOCTOR_CODE = "DR987654"
DEFAULT_PATIENT_CODE = "PAT123456"
LOG_FILE_NAME = "search_log.txt"


# --- Helper Functions ---
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
    """Loads and combines concept data from both Siddha and Ayurveda JSON files."""
    all_concepts = []
    systems_to_load = {
        "Siddha": "Data/SiddhaJson.json",
        "Ayurveda": "Data/AyurvedaJson.json"
    }
    for system_name, file_path in systems_to_load.items():
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
                concepts = data.get("concept", [])
                for concept in concepts:
                    concept['system'] = system_name  # Add system origin to each item
                all_concepts.extend(concepts)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load or parse {file_path}. Error: {e}")
    return all_concepts


# --- PERFORMANCE FIX: Load all data ONCE at startup ---
ALL_NAMC_CONCEPTS = load_all_namc_data()
# --------------------------------------------------------

# --- Swagger UI Setup ---
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "EMR API"})
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)


@app.route("/static/swagger.json")
def swagger_spec():
    spec = {"openapi": "3.0.0", "info": {"title": "EMR API", "version": "1.0"}, "paths": {}}
    return jsonify(spec)


# --- Main Application Routes ---

@app.route("/")
def home():
    return render_template("index.html")


@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Provides real-time search suggestions with system prefixes."""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    suggestions = []
    for item in ALL_NAMC_CONCEPTS:
        display_text = item.get("display", "")
        code_text = item.get("code", "")
        if query in display_text.lower() or query in code_text.lower():
            system = item.get("system", "NAMC")
            suggestions.append([
                code_text,
                f'{system}: {display_text}',
                item.get("designation")[0].get("value")
            ])
    return jsonify(suggestions[:50])


@app.route('/api/suggestions/post', methods=['POST'])
def get_suggestions_via_post():
    """Provides real-time search suggestions for the Swagger UI."""
    query = request.get_json() or {}
    if "code" not in query or "coding" not in query["code"]:
        return jsonify({"error": "Missing code.coding in body"}), 400
    namc_code = query["code"]["coding"][0].get("code", "").lower()

    suggestions = []
    for item in ALL_NAMC_CONCEPTS:
        if item.get("code", "").lower().startswith(namc_code):
            system = item.get("system", "NAMC")
            suggestions.append({
                "code": item.get("code"),
                "display": f'{system}: {item.get("display")}',
                "designation": item.get("designation")[0].get("value")
            })
    return jsonify(suggestions[:20])


@app.route("/api/submit", methods=["POST"])
def submit_term():
    """Converts a selected NAMC term to its ICD-11 equivalent."""
    request_data = request.get_json()
    items = request_data.get("term", "").split(",")
    namc_code = items[0].strip()
    # Remove the system prefix for the API call
    english_term_full = items[1].strip()
    english_term = english_term_full.split(": ", 1)[-1]

    data = getICDDetailsFromEnglishDefinition(english_term, namc_code)
    result_summary = f"Found {len(data)} result(s)"
    if data:
        result_summary += f" (e.g., '{data[0][0]}')"
    log_search_activity(f"'{english_term}'", result_summary)
    return jsonify(data)


@app.route('/api/convert/post', methods=['POST'])
def convert():
    """Converts a NAMC code to ICD-11 for the Swagger UI."""
    query = request.get_json() or {}
    if "code" not in query or "coding" not in query["code"]:
        return jsonify({"error": "Missing code.coding in body"}), 400
    namc_code = query["code"]["coding"][0].get("code", "").lower()
    definition = ""
    for item in ALL_NAMC_CONCEPTS:
        if item.get("code", "").lower() == namc_code:
            definition = item.get("display", "")
            break
    data = []
    if definition:
        search_term_info = f"{namc_code} -> '{definition}'"
        data = getICDDetailsFromEnglishDefinition(definition, namc_code)
        result_summary = f"Found {len(data)} result(s)"
        if data:
            result_summary += f" (e.g., '{data[0][0]}')"
        log_search_activity(search_term_info, result_summary)
    else:
        log_search_activity(f"'{namc_code}'", "Failed: No definition found")
    return jsonify(data)


@app.route("/api/returnJson", methods=["POST"])
def return_json():
    """Formats the selected NAMC and ICD codes into a FHIR Condition resource."""
    data = request.get_json()
    icd = data.get("icd")
    namc = data.get("namc")
    namc_code, namc_display_full = [x.strip() for x in namc.split(',', 1)]
    icd_code, icd_display = [x.strip() for x in icd.split(',', 1)]
    # Remove system prefix from the display term for the final JSON
    namc_display = namc_display_full.split(": ", 1)[-1]

    json_payload = {
        "resourceType": "Condition", "id": "cond-123", "meta": {"...": "..."},
        "code": {"coding": [
            {"system": "https://ndhm.gov.in/fhir/CodeSystem/namc", "code": namc_code, "display": namc_display},
            {"system": "http://id.who.int/icd11/mms", "code": icd_code, "display": icd_display}
        ]}, "subject": {"...": "..."}
    }
    activity_description = f"FHIR Resource Generated (NAMC: {namc_code}, ICD: {icd_code})"
    log_search_activity(activity_description, json.dumps(json_payload, indent=2))
    return jsonify({"message": "Success, JSON logged."})


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


@app.route("/api/ICDtoNAMC")
def icd_to_namc():
    """Finds the top 10 NAMC term matches from Siddha and Ayurveda for a given ICD term."""
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Query parameter 'q' is missing."}), 400
    try:
        term = query.split(",")[1].strip()
    except IndexError:
        term = query.strip()

    # --- Separate concepts and create choice lists for each system ---
    siddha_concepts = [c for c in ALL_NAMC_CONCEPTS if c.get("system") == "Siddha"]
    ayurveda_concepts = [c for c in ALL_NAMC_CONCEPTS if c.get("system") == "Ayurveda"]

    siddha_display_map = {c.get("display"): c for c in siddha_concepts if c.get("display")}
    ayurveda_display_map = {c.get("display"): c for c in ayurveda_concepts if c.get("display")}

    # --- Get top 10 fuzzy matches for each system ---
    siddha_matches = process.extract(term, siddha_display_map.keys(), limit=10)
    ayurveda_matches = process.extract(term, ayurveda_display_map.keys(), limit=10)

    results = []
    # --- Process and format Siddha matches ---
    for match_term, score in siddha_matches:
        concept = siddha_display_map.get(match_term)
        if concept:
            results.append({
                "code": concept.get("code"),
                "term": f"Siddha: {match_term}",
                "score": score,
                "definition": concept.get("designation")[0].get("value")
            })

    # --- Process and format Ayurveda matches ---
    for match_term, score in ayurveda_matches:
        concept = ayurveda_display_map.get(match_term)
        if concept:
            results.append({
                "code": concept.get("code"),
                "term": f"Ayurveda: {match_term}",
                "score": score,
                "definition": concept.get("designation")[0].get("value")
            })
            
    # --- Sort the combined list by score for better presentation ---
    results.sort(key=lambda x: x['score'], reverse=True)
            
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True)

