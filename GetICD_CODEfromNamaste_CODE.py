import urllib3
import json
import requests



def getDetailsFromICD(defintion):
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



    uri = f"https://id.who.int/icd/release/11/2025-01/mms/search?q=Manjal"

    headers = {'Authorization':  'Bearer '+token, 
               'Accept': 'application/json', 
               'Accept-Language': 'en',
           'API-Version': 'v2'}
               
    response = requests.get(uri, headers=headers)

    # Raise error if request fails
    response.raise_for_status()

    # Parse JSON
    data = response.json()

    if data.get("destinationEntities", None):
        for entity in data.get("destinationEntities", []):
            print("ICD-11 Code: " , entity.get("theCode"), "  Title: " , entity.get("title"))

    else:
        print("No Related Entries")



NAMCcode = input("Enter the NAMC code: ")
with open("Data/SiddhaJson.json", mode='r') as file:
    data = json.load(file)


for code in data.get("concept", []):
    # If the NAMC code exists in our database then we will call the WHO api
    if code.get("code", "") == NAMCcode:
        print("The Definition for the given code: ", code.get("display"))
        getDetailsFromICD(code.get("display")) # "Short_descrption" contains the english equivalent term for the disease


