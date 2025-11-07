from numpy import ma
import urllib3
import json
import requests
import  re
from thefuzz import process


def getICDDetailsFromEnglishDefinition(definition, namc_code):

    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    client_id = '42000a86-ed11-4082-8408-31fe933baa5a_a498c5fb-3ea8-4b0f-b221-05aaacb39be6'
    client_secret = 'aeRcA/gMcEaKLkjxFhLBpbC9UmJmHyuYlK7YWhIPIxw='
    scope = 'icdapi_access'
    grant_type = 'client_credentials'

    payload = {'client_id': client_id,
               'client_secret': client_secret,
               'scope': scope,
               'grant_type': grant_type}


    print("The token request has been sent")
    r = requests.post(token_endpoint, data=payload).json()
    token = r['access_token']
    print(r['expires_in'])
    print("The token has been received")


    uri = f"https://id.who.int/icd/release/11/2025-01/mms/search?q={definition}"

    headers = {'Authorization':  'Bearer '+token,
               'Accept': 'application/json',
               'Accept-Language': 'en',
               'API-Version': 'v2'}

    print("The WHO api has been called")
    response = requests.get(uri, headers=headers)
    print("The WHO api responded")

    # Raise error if request fails
    response.raise_for_status()

    # Parse JSON
    data = response.json()
    res = [[item.get("theCode"), re.sub(r'<.*?>', '',item.get("title"))]
           for item in data.get("destinationEntities", [])] # Use empty list as default

    

    if not res:
        print("entered res")
        
        # NOTE: This fallback logic only uses SiddhaJson.json
        with open("Data/SiddhaJson.json", encoding="utf-8") as file:
            data = json.load(file)

            namc_code = namc_code[:2]
            
            definition = ""
            for item in data.get("concept", []):
                if item.get("code", "").lower() == namc_code.lower():
                    definition = item.get("display", "")
                    break

            r = requests.post(token_endpoint, data=payload).json()
            token = r['access_token']

            uri = f"https://id.who.int/icd/release/11/2025-01/mms/search?q={definition}"

            headers = {'Authorization':  'Bearer '+token,
                       'Accept': 'application/json',
                       'Accept-Language': 'en',
                       'API-Version': 'v2'}
            response = requests.get(uri, headers=headers)

            # Raise error if request fails
            response.raise_for_status()

            # Parse JSON
            data = response.json()
            res = [[item.get("theCode"), re.sub(r'<.*?>', '',item.get("title"))]
                   for item in data.get("destinationEntities", [])] # Use empty list as default

    return res




def getICDDetailsFromSiddhaDefinition(definition):

    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    client_id = '42000a86-ed11-4082-8408-31fe933baa5a_a498c5fb-3ea8-4b0f-b221-05aaacb39be6'
    client_secret = 'aeRcA/gMcEaKLkjxFhLBpbC9UmJmHyuYlK7YWhIPIxw='
    scope = 'icdapi_access'
    grant_type = 'client_credentials'

    payload = {'client_id': client_id,
               'client_secret': client_secret,
               'scope': scope,
               'grant_type': grant_type}

    r = requests.post(token_endpoint, data=payload).json()
    token = r['access_token']

    uri = f"https://id.who.int/icd/entity/search?q={definition}"

    headers = {'Authorization':  'Bearer '+token,
               'Accept': 'application/json',
               'Accept-Language': 'en',
               'API-Version': 'v2'}

    response = requests.get(uri, headers=headers)

    # Raise error if request fails
    response.raise_for_status()

    # Parse JSON
    data = response.json()

    print(data)

    for d in data.get("destinationEntities", []): # Use empty list as default
        print(d.get("id"))
        response = requests.get(d.get("id"), headers=headers)
        print(response.json())
        



def verifyABHAToken(token):
    # token_id = token.split(" ")[1]
    print(token)



def findNAMCTerm(term):
    """
    Finds the best matching NAMC terms and their codes from both 
    SiddhaJson.json and AyurvedaJson.json using thefuzz.
    """

    # Define the paths to the JSON files
    json_files = ["./Data/SiddhaJson.json", "./Data/AyurvedaJson.json"]
    all_concepts = []

    # Loop through each file path to read and aggregate the concepts
    for file_path in json_files:
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
                # Add the concepts from the current file to the main list
                all_concepts.extend(data.get("concept", []))
        except FileNotFoundError:
            print(f"Warning: File not found at {file_path}. Skipping.")
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {file_path}. Skipping.")

    # Proceed only if we have concepts to search
    if not all_concepts:
        return []
    
    # Create a list of all display names from the aggregated data to search against
    choices = [item.get("display") for item in all_concepts if item.get("display")]
    
    # Create a dictionary for quick lookup of a code by its display name
    display_to_code_map = {item.get("display"): item.get("code") for item in all_concepts}

    # Perform the fuzzy search using thefuzz on the combined list of choices
    matches = process.extract(term, choices, limit=20)

    # Prepare the results with code, term, and score
    results = []
    for match_term, score in matches:
        code = display_to_code_map.get(match_term)
        if code:
            results.append({"code": code, "term": match_term, "score": score})
            
    return results
