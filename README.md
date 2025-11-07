# KSSEM-HIO25-103
# AYUSH-ICD Terminology Integration: FHIR-Compliant EMR Micro-service

> A production-ready dual-coding terminology service harmonizing India's NAMASTE codes with WHO ICD-11 for traditional medicine digital health systems.

## 🎯 Project Summary

This hackathon solution implements a **lightweight FHIR R4-compliant terminology micro-service** that bridges India's **NAMASTE (National AYUSH Morbidity & Standardized Terminologies Electronic)** codes with **WHO ICD-11 (Traditional Medicine Module 2 & Biomedicine)** for seamless EMR integration. It enables clinicians to document traditional medicine diagnoses (Ayurveda, Siddha, Unani) while automatically mapping them to global ICD-11 identifiers—supporting **dual-coding, insurance claims**.

---

## 🏗️ Architecture Overview

### Backend Stack
- **Framework**: Flask (Python)
- **APIs**: REST endpoints with Swagger UI documentation
- **Terminology Integration**: WHO ICD-11 API, NAMASTE JSON datasets (Siddha/Ayurveda/Unani)
- **Matching Engine**: Fuzzy string matching (thefuzz library), semantic search-ready
- **Authentication**: WHO OAuth 2.0 token management, ABHA verification stubs
- **Logging**: Comprehensive audit trails with doctor ID, patient ID, timestamps

### Frontend Stack
- **UI Framework**: Bootstrap 5.3.8
- **Terminology Search**: Real-time autocomplete with system-specific filtering
- **ECT Widget Integration**: WHO ICD-11 Embedded Coding Tool (native ICD picker)
- **Dual-Coding Interface**: Simultaneous NAMC ↔ ICD bidirectional mapping
- **FHIR Output**: Generate FHIR Condition resources with single-click export

---


## 🚀 Key Features

- **NAMASTE** codes are standarized set of morbidity codes and terminologies specifically for the traditional medicine systems of Ayurveda, Siddha, Unani.
- **ICD-11** codes are standarized set of morbidity codes and terminologies specifically for the traditional medicine systems of Ayurveda, Siddha, Unani.
### 1. **NAMC → ICD-11 Mapping**
- Search NAMASTE codes (Siddha, Ayurveda, Unani) via autocomplete
- Automatically fetch corresponding ICD-11 (TM2 & Biomedicine) codes from WHO API
- Returns both traditional medicine and biomedical classifications
- Fuzzy matching for handling terminology variations

### 2. **ICD-11 → NAMC Reverse Mapping**
- Enter an ICD-11 code or description
- Receive top 10 ranked NAMC matches from Siddha & Ayurveda systems
- Similarity scores show mapping confidence
- Separate results per traditional medicine system

### 3. **Dual-Coding FHIR Output**
- Generate FHIR R4 Condition resources with both code systems
- Supports multiple coding arrays (NAMASTE + ICD-11)
- Includes metadata: version tracking, timestamps, ABHA identifier links
- Compliant with India's 2016 EHR Standards (FHIR R4, ISO 22600)

### 4. **Real-time Autocomplete**
- Type NAMC term or code → instant suggestions
- System-aware filtering (Siddha/Ayurveda/Unani prefixes)
- Display name + designation in vernacular & English
- Debounced search (800ms) for performance

### 5. **WHO ICD-11 ECT Integration**
- Native WHO Embedded Coding Tool widget
- Browse & search ICD-11 hierarchy directly in UI
- Select from TM2 (Traditional Medicine) or Biomedicine chapters
- Real-time token refresh with WHO OAuth 2.0

### 6. **Audit Logging & Compliance**
- Every search logged with timestamp, doctor ID, patient ID
- Format: `[Timestamp] [Doctor] [Patient] [SearchTerm] [Result]`
- Supports India's mandatory audit trail requirements
- Exportable for compliance audits

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js (optional, only if customizing frontend)
- WHO ICD-11 API credentials (free sandbox account)

### Backend Setup

```bash
# 1. Clone repository
git clone https://github.com/YourUsername/AYUSH-ICD-Terminology
cd AYUSH-ICD-Terminology

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Place data files
mkdir -p Data/
# Add SiddhaJson.json, AyurvedaJson.json, UnaniJson.json to Data/ folder

# 5. Run server
python main.py
```

**Output:**
```
 * Running on http://127.0.0.1:5000
 * Open http://localhost:5000 in browser
```

---

## 📊 API Endpoints

### 1. **Real-time NAMC Suggestions**
```bash
GET /api/suggestions?q=jaundice
```
**Response:**
```json
[
  {
    "code": "ABB1.1",
    "display": "Siddha: Jaundice caused by increased azhal",
    "designation": "കമ്പിലോ"
  }
]
```

### 2. **NAMC → ICD Conversion (Swagger)**
```bash
POST /api/convert
Content-Type: application/json

{
  "code": {
    "coding": [
      {"code": "ABB1.1"}
    ]
  }
}
```
**Response:** ICD-11 matches with confidence scores

### 3. **NAMC → ICD Conversion (Query)**
```bash
POST /api/submit
Content-Type: application/json

{
  "term": "ABB1.1, Jaundice caused by increased azhal"
}
```
**Response:** ICD-11 code + display from WHO API

### 4. **ICD → NAMC Reverse Mapping**
```bash
GET /api/ICDtoNAMC?q=ME20.1,%20Obstructive%20jaundice
```
**Response:**
```json
[
  {
    "code": "ABB1.1",
    "term": "Siddha: Jaundice caused by increased azhal",
    "score": 92,
    "definition": "കമ്പിലോ"
  }
]
```

### 5. **Generate FHIR Condition**
```bash
POST /api/returnJson
Content-Type: application/json

{
  "namc": "ABB1.1, Jaundice caused by increased azhal",
  "icd": "ME20.1, Obstructive jaundice"
}
```
**Response:** Complete FHIR R4 Condition resource (logged to searchlog.txt)

### 6. **WHO Token Management**
```bash
GET /api/newToken
```
**Response:**
```json
{
  "token": "eyJhbGc..."
}
```

---

## 🎛️ Usage Walkthrough

### Scenario: Clinician Creating NAMC → ICD Mapping

1. **Open Web UI** → `http://localhost:5000`
2. **Type NAMC term** (left panel, top):
   - Search box auto-suggests: "Jaundice", "Jaundice caused by increased azhal", etc.
3. **Select suggestion** → Submit button enables
4. **Click Convert** → Backend calls WHO API → ICD-11 matches appear (right panel)
5. **Pick ICD code** → WHO ECT widget opens for refinement
6. **Click Return** → FHIR Condition JSON generated & logged

### Scenario: Researcher Mapping ICD → NAMC

1. **Open Web UI**
2. **Lower section** → Enter ICD code (right panel): "ME20.1"
3. **Click Convert** → Top 10 NAMC matches displayed with scores
4. **Select NAMC** → Subject gets logged
5. **Export** → Copy FHIR resource to EMR system

---

## 🔐 Security & Compliance

### Implemented
- ✅ **FHIR R4 API** compliance
- ✅ **OAuth 2.0** token handling (WHO ICD-11 API)
- ✅ **Audit logging** with timestamps & user tracking
- ✅ **CORS support** for cross-origin requests
- ✅ **Error handling** for network failures & invalid inputs

### To Implement (For Production)
- 🔲 **ABHA token verification** (stub present in extraFunctions.py)
- 🔲 **SSL/TLS** enforcement (HTTPS only)
- 🔲 **Rate limiting** (prevent API abuse)
- 🔲 **Database** for persistent audit logs (currently file-based)
- 🔲 **JWT validation** for API requests

See `ABHA_local_verification.md` for ABHA implementation guide.

---

## 📝 Data Format Examples

### NAMASTE JSON Structure
```json
{
  "concept": [
    {
      "code": "ABB1.1",
      "display": "Jaundice caused by increased azhal",
      "designation": [
        {"value": "കമ്പിലോ", "language": "ml"}
      ]
    }
  ]
}
```

### FHIR Condition Output
```json
{
  "resourceType": "Condition",
  "id": "cond-123",
  "code": {
    "coding": [
      {
        "system": "https://ndhm.gov.in/fhir/CodeSystem/namc",
        "code": "ABB1.1",
        "display": "Jaundice caused by increased azhal"
      },
      {
        "system": "http://id.who.int/icd11/mms",
        "code": "ME20.1",
        "display": "Obstructive jaundice"
      }
    ]
  }
}
```

---

## 🧪 Testing

### Unit Testing
```bash
# Test NAMC search
curl "http://localhost:5000/api/suggestions?q=fever"

# Test ICD conversion
curl -X POST http://localhost:5000/api/submit \
  -H "Content-Type: application/json" \
  -d '{"term":"ABB1.1,Jaundice"}'

# Test reverse mapping
curl "http://localhost:5000/api/ICDtoNAMC?q=ME20.1,Obstructive%20jaundice"
```

### Integration Testing
1. Load web UI
2. Search for a condition (e.g., "fever")
3. Select suggestion → Verify ICD appears
4. Select ICD code → Verify FHIR JSON logged
5. Check `searchlog.txt` for audit entry

---

## 🔧 Configuration & Customization

### WHO API Credentials
Edit `extraFunctions.py` and `main.py`:
```python
CLIENT_ID = "your-who-client-id"
CLIENT_SECRET = "your-who-client-secret"
```

### Default EMR Codes
Edit `main.py`:
```python
DEFAULT_DOCTOR_CODE = "DR987654"
DEFAULT_PATIENT_CODE = "PAT123456"
```

### Add New Terminology System
1. Place JSON file in `Data/` folder
2. Add to `load_all_namc_data()` in main.py:
```python
systems_to_load = {
    "Siddha": "Data/SiddhaJson.json",
    "Ayurveda": "Data/AyurvedaJson.json",
    "Unani": "Data/UnaniJson.json", # Add here
}
```

---

## 📚 Dependencies

```
Flask==2.3.2
flask-cors==4.0.0
flask-swagger-ui==4.11.1
requests==2.31.0
thefuzz==0.19.0
python-Levenshtein==0.21.0
PyJWT==2.8.1
cryptography==41.0.0
```

Install all:
```bash
pip install -r requirements.txt
```

---

## 🚧 Known Limitations & Future Work

### Current Limitations
- **File-based audit logs** (not persistent DB)
- **Mock ABHA verification** (no real token validation)
- **Single-threaded Flask** (not production-ready)
- **No caching** for WHO API responses

### Roadmap
- [ ] PostgreSQL backend for scalable audit logs
- [ ] Real ABHA token verification with ABDM
- [ ] ConceptMap FHIR resources for formalized mappings
- [ ] Multilingual UI (Tamil, Sanskrit, Arabic)
- [ ] Advanced analytics dashboard
- [ ] CI/CD pipeline with Docker deployment

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/NAMC-search`
3. Commit changes: `git commit -m "Add fuzzy search improvement"`
4. Push: `git push origin feature/NAMC-search`
5. Open Pull Request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🎓 References & Standards

- **FHIR R4**: https://www.hl7.org/fhir/r4/
- **WHO ICD-11 API**: https://icd.who.int/icdapi
- **India EHR Standards 2016**: https://abdm.gov.in/
- **NAMASTE Coding**: https://www.ccim.gov.in/
- **ABHA (Ayushman Bharat Health Account)**: https://abha.abdm.gov.in/

---

## 📞 Support

**Issues?** Open a GitHub Issue with:
- Error message & traceback
- Steps to reproduce
- Expected vs actual behavior

**Questions?** Check existing issues or email team.

---

## 🏆 Hackathon Submission Checklist

- ✅ Dual NAMC ↔ ICD mapping functionality
- ✅ FHIR R4 Condition resource generation
- ✅ Real-time autocomplete interface
- ✅ WHO ICD-11 API integration
- ✅ Audit logging for compliance
- ✅ Multi-system support (Siddha/Ayurveda/Unani)
- ✅ Swagger API documentation
- ✅ Production-ready error handling
- ✅ India EHR Standards alignment

---

**Last Updated**: November 2025  
**Repository**: [Your GitHub URL]  
**Demo**: [Live link if available]
