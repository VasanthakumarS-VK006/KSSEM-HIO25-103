# This file calls the WHO api after getting the according English term for the NAMC code from the database
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



    uri = f'https://id.who.int/icd/entity/search?q={defintion}'

    headers = {'Authorization':  'Bearer '+token, 
               'Accept': 'application/json', 
               'Accept-Language': 'en',
           'API-Version': 'v2'}
               
    r = requests.get(uri, headers=headers, verify=False)

    for text in r.text.split(','):
        print(text)



NAMCcode = "AB" # NAMC for Jaundice
with open("Data/SiddhaJson.json", mode='r') as file:
    data = json.load(file)


for code in data.get("concept", []):
    # If the NAMC code exists in our database then we will call the WHO api
    if code.get("code", "") == NAMCcode:
        print(code)
        getDetailsFromICD(code.get("Short_description")) # "Short_descrption" contains the english equivalent term for the disease


