import json
import sys
import argparse
import os
import re
import uuid
from datetime import datetime, UTC

# --- Dependency Imports ---
# pip install torch sentence-transformers langchain langchain-huggingface langchain-chroma chromadb requests python-Levenshtein thefuzz
try:
    import requests
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from thefuzz import process
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# --- Global Configuration ---
# These must match the directories used in preprocess_model.py
CHROMA_PERSIST_DIR = "chroma_db_persistent_cli"
MODELS_DIR = "models"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_PATH = os.path.join(MODELS_DIR, MODEL_NAME.replace('/', '_'))

# --- Data Loading ---
def load_all_namc_data():
    """This is a lightweight function to load data for fuzzy matching and lookups."""
    all_concepts = []
    systems_to_load = {
        "Siddha": "Data/SiddhaJson.json",
        "Ayurveda": "Data/AyurvedaJson.json",
        "Unani": "Data/UnaniJson.json",
    }
    for system_name, file_path in systems_to_load.items():
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
                concepts = data.get("concept", [])
                for concept in concepts:
                    concept['system'] = system_name
                all_concepts.extend(concepts)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return all_concepts

# --- Core Functions ---
def get_who_api_token():
    """Fetches a new access token from the WHO API for each run."""
    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    client_id = '42000a86-ed11-4082-8408-31fe933baa5a_a498c5fb-3ea8-4b0f-b221-05aaacb39be6'
    client_secret = 'aeRcA/gMcEaKLkjxFhLBpbC9UmJmHyuYlK7YWhIPIxw='
    payload = {
        'client_id': client_id, 'client_secret': client_secret,
        'scope': 'icdapi_access', 'grant_type': 'client_credentials'
    }
    try:
        r = requests.post(token_endpoint, data=payload, timeout=10)
        r.raise_for_status()
        return r.json().get('access_token')
    except (requests.exceptions.RequestException, KeyError, json.JSONDecodeError):
        return None

def get_icd_details_from_who_api(term):
    """Handles the WHO API calls to get all related ICD-11 details, with a flexisearch fallback."""
    token = get_who_api_token()
    if not token:
        return [{"error": "Failed to acquire WHO API access token."}]

    try:
        headers = {
            'Authorization': f'Bearer {token}', 'Accept': 'application/json',
            'Accept-Language': 'en', 'API-Version': 'v2'
        }
        
        # --- Primary Search ---
        uri = f"https://id.who.int/icd/release/11/2024-01/mms/search?q={term}"
        response = requests.get(uri, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        # The primary search returns a dictionary with 'destinationEntities'
        primary_entities = data.get("destinationEntities", [])
        for item in primary_entities:
            title = item.get("title")
            code = item.get("theCode")
            if title and code:
                results.append({
                    "icd_code": code,
                    "title": re.sub(r'<.*?>', '', title)
                })

        # --- Flexisearch Fallback with new URL structure ---
        if not results:
            print("\nStandard search found no results. Trying a broader flexisearch...")
            flexi_uri = f"{uri}&useFlexisearch=true&flatResults=true"
            flexi_response = requests.get(flexi_uri, headers=headers, timeout=10)
            flexi_response.raise_for_status()
            flexi_data = flexi_response.json()
            
            # **FIX**: The API's "flatResults" might be a dict or a list. This handles both.
            flexi_entities = flexi_data if isinstance(flexi_data, list) else flexi_data.get("destinationEntities", [])
            
            for item in flexi_entities:
                title = item.get("title")
                code = item.get("theCode")
                if title and code:
                    results.append({
                        "icd_code": code,
                        "title": re.sub(r'<.*?>', '', title)
                    })

        return results[:20] # Limit final results to a maximum of 20

    except requests.exceptions.RequestException as e:
        return [{"error": f"API request failed: {e}"}]
    except (KeyError, json.JSONDecodeError):
        return [{"error": "Failed to parse API response."}]


def find_namc_by_code_or_term(term, all_concepts):
    """
    Searches for NAMC concepts by both code (direct prefix match) and term (fuzzy match).
    Prioritizes code matches.
    """
    term_lower = term.lower()
    code_matches = []
    matched_codes = set()

    # 1. Find direct code matches (case-insensitive prefix)
    for concept in all_concepts:
        if concept['code'].lower().startswith(term_lower):
            vernacular_term = concept.get("designation")[0].get("value")
            display_term = concept.get("display")
            code = concept.get("code")
            system = concept.get("system")
            full_display_string = f"{code}, {system}: {display_term}, {vernacular_term}"
            
            code_matches.append({
                "score": 101,  # Prioritize code matches over fuzzy matches
                "code": code,
                "system": system,
                "display": display_term,
                "full_display": full_display_string
            })
            matched_codes.add(code)

    # 2. Find fuzzy term matches
    choices = {f"{c.get('system')}: {c.get('display')}": c for c in all_concepts}
    fuzzy_matches_raw = process.extract(term, choices.keys(), limit=10)
    
    fuzzy_matches = []
    for match_term, score in fuzzy_matches_raw:
        concept = choices[match_term]
        if concept['code'] not in matched_codes:  # De-duplicate
            vernacular_term = concept.get("designation")[0].get("value")
            display_term = concept.get("display")
            code = concept.get("code")
            system = concept.get("system")
            full_display_string = f"{code}, {system}: {display_term}, {vernacular_term}"

            fuzzy_matches.append({
                "score": score,
                "code": code,
                "system": system,
                "display": display_term,
                "full_display": full_display_string
            })
            matched_codes.add(code) # Also add to prevent re-adding

    # 3. Combine and sort
    all_matches = code_matches + fuzzy_matches
    all_matches.sort(key=lambda x: x.get('score', 0), reverse=True)

    return all_matches[:10] # Return top 10 combined results


def perform_nlp_search(query, vector_store, all_concepts):
    """Performs a semantic search to find the top 10 NAMC terms."""
    if not vector_store:
        return [{"error": "Vector store not initialized."}]
    
    concept_map = {c['code']: c for c in all_concepts}
    relevant_docs = vector_store.similarity_search(query, k=10)
    
    final_results = []
    for doc in relevant_docs:
        code = doc.metadata.get("code")
        full_concept = concept_map.get(code)
        if full_concept:
            vernacular_term = full_concept.get("designation")[0].get("value")
            display_term = full_concept.get("display")
            system = full_concept.get("system")
            full_display_string = f"{code}, {system}: {display_term}, {vernacular_term}"

            final_results.append({
                "system": system,
                "code": code,
                "display": display_term,
                "full_display": full_display_string
            })
    return final_results

def format_as_fhir_condition(namc_coding, icd_coding):
    """Builds the final FHIR-like Condition JSON object."""
    all_codings = []
    if namc_coding:
        all_codings.append(namc_coding)
    if icd_coding:
        all_codings.append(icd_coding)

    if not all_codings:
        return {"error": "No coding information found to generate a FHIR resource."}

    return {
        "resourceType": "Condition",
        "id": f"cond-{uuid.uuid4()}",
        "meta": {"lastUpdated": f"{datetime.now(UTC).isoformat()}"},
        "code": {"coding": all_codings},
        "subject": {"reference": "Patient/example", "display": "Example Patient"}
    }

def handle_interactive_selection(matches, title, display_key):
    """Generic function to display a list and get user selection."""
    if not matches:
        print(f"\nNo matches found.")
        return None
    
    print(f"\n{title}")
    for i, match in enumerate(matches):
        print(f"{i+1}. {match.get(display_key, 'N/A')}")

    while True:
        try:
            choice = input(f"\nEnter a number (1-{len(matches)}) or 0 to exit: ")
            choice_num = int(choice)
            if 0 <= choice_num <= len(matches):
                return matches[choice_num - 1] if choice_num > 0 else None
            else:
                print("Invalid choice. Please try again.")
        except (ValueError, IndexError):
            print("Invalid input. Please enter a number.")

# --- Main Execution Logic ---
def main():
    parser = argparse.ArgumentParser(description="Intelligent CLI for medical code search.")
    parser.add_argument("query", type=str, nargs='+', help="Your search query in natural language.")
    args = parser.parse_args()

    full_query = " ".join(args.query).lower()
    all_namc_concepts = load_all_namc_data()

    selected_namc = None
    selected_icd = None
    
    # --- Step 1: Determine Workflow ---
    is_icd_to_namc = "icd to namc" in full_query
    is_keyword_search = "find namc" in full_query or "convert" in full_query or "to icd" in full_query
    
    # --- WORKFLOW: ICD to NAMC ---
    if is_icd_to_namc:
        search_term = re.sub(r'(convert|icd to namc|to namc|of|for)', '', full_query).strip()
        print("\nContacting WHO ICD-11 API for matches...")
        icd_candidates = get_icd_details_from_who_api(search_term)

        if icd_candidates and 'error' in icd_candidates[0]:
            print(f"\nAn error occurred: {icd_candidates[0]['error']}")
        else:
            selected_icd = handle_interactive_selection(icd_candidates, "Matching ICD-11 terms:", 'title')
            if selected_icd:
                print("\nSearching local NAMC data for related terms...")
                namc_candidates = find_namc_by_code_or_term(selected_icd['title'], all_namc_concepts)
                selected_namc = handle_interactive_selection(namc_candidates, "Matching NAMC codes:", 'full_display')
    
    # --- WORKFLOW: NAMC to ICD / General Search ---
    else:
        namc_candidates = []
        if is_keyword_search:
            search_term = re.sub(r'(find namc|convert|namc to icd|of|for)', '', full_query).strip()
            print("\nSearching local NAMC data...")
            namc_candidates = find_namc_by_code_or_term(search_term, all_namc_concepts)
        else: # Default to NLP
            if not LANGCHAIN_AVAILABLE:
                print(json.dumps({"error": "LangChain libraries not installed."}, indent=4))
                return
            if not os.path.exists(MODEL_PATH) or not os.path.exists(CHROMA_PERSIST_DIR):
                print(json.dumps({"error": "Model or DB not found.", "message": "Run preprocess_model.py"}, indent=4))
                return
            
            print("\nPerforming semantic search...")
            embedding_function = HuggingFaceEmbeddings(model_name=MODEL_PATH)
            vector_store = Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embedding_function)
            namc_candidates = perform_nlp_search(full_query, vector_store, all_namc_concepts)
        
        selected_namc = handle_interactive_selection(namc_candidates, "matching namc code", 'full_display')

        if selected_namc:
            print("\nContacting WHO ICD-11 API for matches...")
            icd_results = get_icd_details_from_who_api(selected_namc['display'])
            if icd_results and 'error' in icd_results[0]:
                 print(f"\nAn error occurred: {icd_results[0]['error']}")
            else:
                selected_icd = handle_interactive_selection(icd_results, "Matching ICD-11 terms:", 'title')

    # --- Step 2: Format and Print the Final Result ---
    if selected_namc and selected_icd:
        namc_system = selected_namc.get('system')
        namc_coding = {
            "system": f"https://ndhm.gov.in/fhir/CodeSystem/namc/{namc_system}",
            "code": selected_namc.get('code'),
            "display": selected_namc.get('display')
        }
        icd_coding = {
            "system": "http://id.who.int/icd11/mms",
            "code": selected_icd.get("icd_code"),
            "display": selected_icd.get("title")
        }
        final_result = format_as_fhir_condition(namc_coding, icd_coding)
        print("\n--- Final FHIR Condition ---")
        print(json.dumps(final_result, indent=4))
    else:
        # This handles cases where the user exits or no matches are found
        print("\nOperation cancelled or no valid selection made.")

if __name__ == "__main__":
    main()

