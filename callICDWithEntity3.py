import requests

token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
client_id = '42000a86-ed11-4082-8408-31fe933baa5a_a498c5fb-3ea8-4b0f-b221-05aaacb39be6'
client_secret = 'aeRcA/gMcEaKLkjxFhLBpbC9UmJmHyuYlK7YWhIPIxw='
scope = 'icdapi_access'
grant_type = 'client_credentials'


payload = {'client_id': client_id, 
       'client_secret': client_secret, 
       'scope': scope, 
       'grant_type': grant_type}
       
# make request
r = requests.post(token_endpoint, data=payload, verify=False).json()
token = r['access_token']

uri = "https://id.who.int/icd/release/11/2024-01/mms/search?q=fever"

# HTTP header fields to set
headers = {'Authorization':  'Bearer '+token, 
           'Accept': 'application/json', 
           'Accept-Language': 'en',
       'API-Version': 'v2'}


response = requests.get(uri, headers=headers)


# Raise error if request fails
response.raise_for_status()

# Parse JSON
data = response.json()

for entity in data.get("destinationEntities", []):
    print(entity.get("theCode"))
    print(entity.get("title"))


