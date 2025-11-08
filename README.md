# NAMC-ICD Medical Code Translator & ABDM Exchange Layer

A production-ready web application that bridges traditional Indian medicine (NAMC/AYUSH) and modern international medical coding (ICD-11) with JWT authentication, NLP semantic search, and ABDM compliance.

## Features

- **NAMC-to-ICD & ICD-to-NAMC Bidirectional Mapping** – Instant code translation  
- **NLP Semantic Search** – Find medical codes by clinical description using LangChain  
- **JWT Authentication** – ABDM-compliant token generation and validation (RSA-256)  
- **Patient Management** – ABHA registration, consent tracking, health record storage  
- **FHIR-Compatible Data** – Standards-based health information exchange  
- **Multi-System Support** – Siddha, Ayurveda, and Unani terminology  
- **Search Logging** – Audit trail of all medical code searches  
- **Semantic searching** – Robust search with scoring  
- **WHO API Integration** – Real-time ICD-11 code lookup  

---

## Project Structure

```
project/
├── main.py                    # Flask web server + API endpoints
├── agent.py                   # CLI tool for medical code search
├── extraFunctions.py          # WHO API integration for ICD codes
├── preprocess.py              # Vector store builder (one-time setup)
├── search.py                  # Excel-based NAMC search utility
├── private_key.pem            # RSA private key (token signing)
├── public_key.pem             # RSA public key (token verification)
├── Data/
│   ├── SiddhaJson.json        # Siddha medicine codes
│   ├── AyurvedaJson.json      # Ayurveda medicine codes
│   └── UnaniJson.json         # Unani medicine codes
├── templates/
│   ├── index2.html            # Web UI for code conversion
│   └── emr.html               # EMR interface
├── chroma_db_persistent/      # Vector database (auto-created)
└── search_log.txt             # Search audit log
```

---

## Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Step 1: Install Dependencies

```bash
pip install flask flask-cors flask-swagger-ui langchain langchain-huggingface langchain-chroma chromadb sentence-transformers jwt certifi requests python-Levenshtein thefuzz torch pandas openpyxl
```

### Step 2: Build Vector Database (First Time Only)

```bash
python preprocess.py
```

This creates a semantic search index from NAMC terminology. Takes 2-5 minutes on first run.

### Step 3: Start Flask Server

```bash
python main.py
```

Server runs at `http://127.0.0.1:5000`

---

## API Endpoints

### 1. **Generate JWT Token**
```bash
curl -X POST http://127.0.0.1:5000/api/generate-token \
  -H "Content-Type: application/json" \
  -d '{
    "abha_number": "12345678901234",
    "abha_address": "patient@sbx",
    "name": "John Doe"
  }'
```
**Response:** `{"token": "eyJ0eXAiOiJKV1QiLCJhbGc..."}` (24-hour validity)

---

### 2. **Get NAMC Code Suggestions**
```bash
curl -X GET "http://127.0.0.1:5000/api/suggestions?q=jaundice" \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Response:**
```json
[
  ["ABB1.1", "Siddha: Obstructive Jaundice", "Kambalai"],
  ["ABB1.2", "Siddha: Hemolytic Jaundice", "Manjal Karuttai"]
]
```

---

### 3. **Convert NAMC to ICD-11**
```bash
curl -X POST http://127.0.0.1:5000/api/submit \
  -H "Content-Type: application/json" \
  -d '{"term": "ABB1.1, Siddha: Obstructive Jaundice"}'
```

**Response:**
```json
[
  ["ME20.1", "Obstructive jaundice"],
  ["ME20.2", "Non-obstructive jaundice"]
]
```

---

### 4. **NLP Clinical Description Search**
```bash
curl -X POST http://127.0.0.1:5000/api/nlp_search \
  -H "Content-Type: application/json" \
  -d '{"query": "patient with yellow skin and itching for 2 weeks"}'
```

**Response:** Top 5 matching medical codes with confidence scores

---

### 5. **Convert ICD-11 to NAMC (Reverse Lookup)**
```bash
curl -X GET "http://127.0.0.1:5000/api/ICDtoNAMC?q=ME20.1,Obstructive%20jaundice"
```

**Response:** Fuzzy-matched NAMC terms with similarity scores

---

## ABDM Exchange Layer Endpoints

### Patient Registration
```bash
curl -X POST http://127.0.0.1:5000/register \
  -H "Content-Type: application/json" \
  -d '{"abha": "12345678901234", "name": "John Doe"}'
```

### Give Consent
```bash
curl -X POST http://127.0.0.1:5000/consent \
  -H "Content-Type: application/json" \
  -d '{"abha": "12345678901234"}'
```

### Save Health Record (NAMC + ICD)
```bash
curl -X POST http://127.0.0.1:5000/save-diagnosis \
  -H "Content-Type: application/json" \
  -d '{
    "abha": "12345678901234",
    "diagnosis": "Jaundice",
    "namc_code": "ABB1.1",
    "icd_code": "ME20.1"
  }'
```

### Retrieve Patient Health Data (FHIR Format)
```bash
curl -X GET "http://127.0.0.1:5000/get-health-data?abha=12345678901234"
```

---

## CLI Usage

### Search by Description (Semantic)
```bash
python agent.py "find NAMC patient with fever and body aches"
```

### Search by Code
```bash
python agent.py "find namc ABB1"
```

### Convert to ICD
```bash
python agent.py "convert Siddha: Obstructive Jaundice to icd"
```

### Convert from ICD
```bash
python agent.py "icd to namc ME20.1"
```

---

## Configuration

### Modify Search Parameters (in main.py)
```python
# Vector store location
CHROMA_PERSIST_DIR = "chroma_db_persistent"

# Embedding model
HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Top results returned
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
```

### Adjust JWT Expiry
```python
# In generate_token() function
"exp": datetime.utcnow() + timedelta(hours=24)  # Change 24 to desired hours
```

---

## Data Format

### NAMC/AYUSH Code Structure
```json
{
  "code": "ABB1.1",
  "display": "Obstructive Jaundice",
  "system": "Siddha",
  "designation": [{"value": "Kambalai"}]
}
```

### ICD-11 Code Structure (WHO API)
```json
{
  "theCode": "ME20.1",
  "title": "Obstructive jaundice",
  "id": "http://id.who.int/icd/entity/..."
}
```

### FHIR Condition Resource
```json
{
  "resourceType": "Condition",
  "id": "cond-uuid",
  "code": {
    "coding": [
      {"system": "https://ndhm.gov.in/fhir/CodeSystem/namc/Siddha", "code": "ABB1.1"},
      {"system": "http://id.who.int/icd11/mms", "code": "ME20.1"}
    ]
  }
}
```

---

## Authentication

All endpoints require ABDM-compliant JWT tokens with the following claims:
```
{
  "iss": "https://sandbox.abdm.gov.in",
  "sub": "12345678901234",  // ABHA number
  "aud": "facility",
  "kycStatus": "VERIFIED",
  "exp": 1701085733
}
```

Token validation happens in the `get_suggestions` and `csvUpload` endpoints.

---

## Performance

- **Search Time:** <100ms for exact matches, <200ms for fuzzy/semantic
- **Vector Store:** Loads from disk in <2 seconds
- **Concurrent Users:** Tested up to 50 simultaneous API calls

---

## Troubleshooting

### "chroma_db_persistent not found"
```bash
python preprocess.py  # Rebuild vector database
```

### "WHO API authentication failed"
Check WHO API credentials in `extraFunctions.py` – regenerate if expired

### Token validation errors
Ensure `public_key.pem` matches `private_key.pem` used for token generation

### CORS errors
CORS is enabled via `CORS(app)` in main.py – check that frontend calls match API domain

---



