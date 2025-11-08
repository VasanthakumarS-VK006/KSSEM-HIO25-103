import json
import requests
import re
import time
from datetime import datetime, UTC
import concurrent.futures
import threading
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress only the InsecureRequestWarning from verify=False
warnings.simplefilter('ignore', InsecureRequestWarning)


# --- Configuration ---

# Set TEST_LIMIT to a small number (e.g., 20) to test the script first.
# Set TEST_LIMIT = None to run the full mapping.
TEST_LIMIT = None

# --- Multi-threading Configuration ---
# Number of parallel requests to make.
# Start low (e.g., 5) and increase if you don't get errors.
# Do NOT set this too high (e.g., > 15) or you risk an IP ban.
MAX_WORKERS = 8
# --- End of Multi-threading Config ---


OUTPUT_FILE = "Data/NAMC_to_ICD11_MultiThreaded_ConceptMap.json"
# We don't need a sleep delay here, as the MAX_WORKERS controls the rate.


# --- Global variables for thread-safe token management ---
g_api_token = None
g_token_lock = threading.Lock()


# --- Core Functions ---

def load_all_namc_data():
    """
    This function loads data for fuzzy matching and lookups from all 3 systems.
    """
    all_concepts = []
    # These are the 3 files you specified
    systems_to_load = {
        "Siddha": "Data/SiddhaJson.json",
        "Ayurveda": "Data/AyurvedaJson.json",
        "Unani": "Data/UnaniJson.json",
    }
    print("Loading all NAMC concepts from:")
    for system_name, file_path in systems_to_load.items():
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
                concepts = data.get("concept", [])
                for concept in concepts:
                    concept['system'] = system_name  # Add system name for context
                all_concepts.extend(concepts)
                print(f"  - Successfully loaded {len(concepts)} concepts from {file_path}")
        except FileNotFoundError:
            print(f"  - WARNING: File not found: {file_path}. Skipping.")
        except json.JSONDecodeError:
            print(f"  - WARNING: Could not decode JSON from {file_path}. Skipping.")
    
    print(f"\nTotal concepts loaded: {len(all_concepts)}")
    return all_concepts

def get_who_api_token():
    """Fetches a new access token from the WHO API. (Not thread-safe by itself)"""
    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    
    # --- FIX 1: Corrected the typo in client_id (removed extra '_') ---
    client_id = '42000a86-ed11-4082-8408-31fe933baa5a_a498c5fb-3ea8-4b0f-b221-05aaacb39be6'
    
    client_secret = 'aeRcA/gMcEaKLkjxFhLBpbC9UmJmHyuYlK7YWhIPIxw='
    payload = {
        'client_id': client_id, 'client_secret': client_secret,
        'scope': 'icdapi_access', 'grant_type': 'client_credentials'
    }
    try:
        r = requests.post(token_endpoint, data=payload, timeout=10, verify=False)
        r.raise_for_status()
        return r.json().get('access_token')
    except (requests.exceptions.RequestException, KeyError, json.JSONDecodeError) as e:
        print(f"  - ERROR (get_token): Failed to get WHO API token: {e}")
        return None

def refresh_api_token_thread_safe():
    """
    Thread-safe function to refresh the global API token.
    Uses a lock to ensure only one thread refreshes the token.
    """
    global g_api_token, g_token_lock
    
    with g_token_lock:
        # We've acquired the lock, but check if another thread
        # *just* refreshed the token while we were waiting.
        # We do this by checking a hypothetical expiry time (e.g., 50 mins).
        # For simplicity, we'll just re-fetch it if we get the lock.
        print("  - [Thread] Acquiring new WHO API token...")
        token = get_who_api_token()
        if token:
            g_api_token = token
            print("  - [Thread] New token acquired.")
            return True
        else:
            print("  - [Thread] FAILED to acquire new token.")
            # Release the old token so other threads retry
            g_api_token = None 
            return False

def get_icd_details_from_who_api(concept, retry_count=0):
    """
    Thread-safe function to be called by each worker thread.
    Handles its own token expiry and retries.
    """
    global g_api_token
    
    term = concept.get("display")
    
    if not g_api_token:
        print(f"  - [{term}] No token found, waiting for refresh...")
        # This will block until the token is refreshed
        refresh_api_token_thread_safe() 
        
    if not g_api_token:
         # Refresh failed
        return concept, [{"error": "Failed to acquire WHO API access token."}]

    # Use a specific, stable release version
    base_uri = "https://id.who.int/icd/release/11/2024-01/mms/search"
    
    try:
        headers = {
            # Use the global token
            'Authorization': f'Bearer {g_api_token}', 
            'Accept': 'application/json',
            'Accept-Language': 'en', 'API-Version': 'v2'
        }
        
        # --- 1. Primary Search Only ---
        uri = f"{base_uri}?q={term}"
        response = requests.get(uri, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()
        
        results = []
        primary_entities = data.get("destinationEntities", [])
        for item in primary_entities:
            title = item.get("title")
            code = item.get("theCode")
            if title and code:
                results.append({
                    "icd_code": code,
                    "title": re.sub(r'<.*?>', '', title) # Clean HTML tags
                })

        return concept, results[:20] # Return the original concept and the results

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401 and retry_count == 0:
             print(f"  - [{term}] Token expired. Triggering refresh...")
             # Trigger a refresh and retry ONCE
             refresh_api_token_thread_safe()
             return get_icd_details_from_who_api(concept, retry_count=1)
        
        if e.response.status_code == 429:
             print(f"  - [{term}] HIT RATE LIMIT (429)! Sleeping for 10s...")
             time.sleep(10) # Back off
             return get_icd_details_from_who_api(concept, retry_count=1) # Retry

        print(f"  - ERROR [{term}]: API request failed: {e}")
        return concept, [{"error": f"API request failed: {e}"}]
    except (requests.exceptions.RequestException, KeyError, json.JSONDecodeError) as e:
        print(f"  - ERROR [{term}]: Failed to parse API response: {e}")
        return concept, [{"error": "Failed to parse API response."}]


# --- Main Mapping Function ---

def build_concept_map():
    """
    Iterates through all NAMC codes using a thread pool and builds a
    FHIR ConceptMap resource.
    """
    
    all_namc_concepts = load_all_namc_data()
    
    if not all_namc_concepts:
        print("No NAMC concepts loaded. Exiting. Check your 'Data' folder.")
        return

    # This is the list that will hold all our mapping elements
    map_elements = []
    
    # Counter for skipped codes
    skipped_codes_count = 0

    print(f"\n--- Starting to Map NAMC codes to ICD-11 (Multi-Threaded) ---")
    print(f"Max Workers: {MAX_WORKERS}")
    print(f"Test limit set to: {TEST_LIMIT or 'ALL'}")
    
    # Apply the test limit if one is set
    concepts_to_process = all_namc_concepts[:TEST_LIMIT] if TEST_LIMIT else all_namc_concepts
    total = len(concepts_to_process)
    
    # Get the first token
    print("\nAcquiring initial WHO API token...")
    if not refresh_api_token_thread_safe():
        print("Failed to get initial API token. Exiting.")
        return

    # Use ThreadPoolExecutor to manage parallel requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        
        # Submit all jobs to the pool
        # We pass the full 'concept' object to the worker
        future_to_concept = {
            executor.submit(get_icd_details_from_who_api, concept): concept
            for concept in concepts_to_process
            if concept.get("code") and concept.get("display")
        }

        print(f"\nSubmitted {len(future_to_concept)} jobs to {MAX_WORKERS} workers...")
        
        # Process results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(future_to_concept)):
            
            original_concept, icd_matches = future.result()
            
            namc_code = original_concept.get("code")
            namc_display = original_concept.get("display")
            namc_system = original_concept.get("system", "unknown")

            # --- FIX 2: Construct the correct display key ---
            # This key MUST match the logic in main.py's /api/suggestions endpoint
            # The key is "System: DisplayName"
            correct_display_key = f"{namc_system}: {namc_display}"

            print(f"\n[{i+1}/{total}] Processed: [{namc_system}] {namc_code} - '{namc_display}'")

            targets = []
            if icd_matches and "error" not in icd_matches[0]:
                for match in icd_matches:
                    icd_code = match.get("icd_code")
                    icd_title = match.get("title")
                    
                    if icd_code and icd_title:
                        targets.append({
                            "code": icd_code,
                            "display": icd_title,
                            "equivalence": "relatedto" 
                        })

            # --- Only add if we found matches ---
            if targets:
                print(f"  > Found {len(targets)} ICD-11 match(es). Adding to map.")
                map_elements.append({
                    "code": namc_code,
                    "display": correct_display_key, # <-- Use the correct key here
                    "target": targets
                })
            else:
                print(f"  > No ICD-11 matches found. Skipping.")
                skipped_codes_count += 1
            

    # --- Assemble the final FHIR ConceptMap Resource ---
    
    print("\n--- Mapping complete. Assembling final FHIR ConceptMap. ---")
    
    # Sort the final map by NAMC code for consistency
    map_elements.sort(key=lambda x: x.get('code', ''))
    
    fhir_concept_map = {
        "resourceType": "ConceptMap",
        "id": "namc-to-icd11-multithreaded",
        "url": "http://your-domain.org/fhir/ConceptMap/namc-to-icd11-multithreaded",
        "name": "NAMC_to_ICD11_MultiThreaded_ConceptMap",
        "title": "NAMC (Ayurveda, Siddha, Unani) to ICD-11 ConceptMap (Multi-Threaded)",
        "status": "draft",
        "experimental": True,
        "date": f"{datetime.now(UTC).isoformat()}",
        "publisher": "Your Organization Name",
        "description": f"A draft concept map linking NAMC codes to ICD-11 codes. Generated from {len(map_elements)} NAMC codes that had at least one match. {skipped_codes_count} codes were skipped due to no match. (Used {MAX_WORKERS} workers).",
        "sourceUri": "https://ndhm.gov.in/fhir/CodeSystem/namc", # Generic NAMC system
        "targetUri": "http://id.who.int/icd11/mms",
        "group": [
            {
                "source": "https://ndhm.gov.in/fhir/CodeSystem/namc",
                "target": "http://id.who.int/icd11/mms",
                "element": map_elements  # This is our list of all mappings
            }
        ]
    }

    # --- Save the final JSON file ---
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(fhir_concept_map, f, indent=4, ensure_ascii=False)
        print(f"\n--- SUCCESS ---")
        print(f"Concept map successfully saved to: {OUTPUT_FILE}")
        print(f"Mapped {len(map_elements)} NAMC codes.")
        print(f"Skipped {skipped_codes_count} NAMC codes (no matches found).")
    except IOError as e:
        print(f"\n--- ERROR ---")
        print(f"Failed to write output file: {e}")


# --- Run the script ---
if __name__ == "__main__":
    build_concept_map()