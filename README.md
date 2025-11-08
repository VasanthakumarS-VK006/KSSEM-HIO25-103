# **EMR Assistant & Medical Code Converter**

**Bridging Traditional Wisdom with Modern Medicine.** This project provides a robust Flask API for Electronic Medical Record (EMR) assistance, combining Optical Character Recognition (OCR), Natural Language Processing (NLP), and advanced Medical Code Mapping to streamline healthcare data management.

## **Features At a Glance**

* **OCR-Powered EMR Digitization:** Upload scanned medical documents and instantly extract structured patient information, test results, and clinical notes.  
* **NAMC ↔️ ICD-11 Code Conversion:** Seamlessly convert between National AYUSH Morbidity Codes (NAMC) and WHO ICD-11 codes using a sophisticated ConceptMap and a dynamic WHO Flexi-search fallback.  
* **Local Semantic Search (NLP):** Leverage cutting-edge HuggingFace embeddings for intelligent, context-aware searching of NAMC definitions, even offline.  
* **High-Performance & Scalable:** Built with Flask, designed for rapid responses and easy deployment.  
* **Secure & Logged:** All search activities are logged for auditing and compliance.  
* **Intuitive Web Interface:** A user-friendly frontend (index.html) to interact with all API functionalities.

## **How It Works (The Tech Stack)**

### **OCR (Optical Character Recognition)**

* **Technology:** **EasyOCR** is utilized for accurate and fast text extraction from uploaded image files (PNG, JPG, JPEG, GIF).  
* **Workflow:** Image Upload ➡️ EasyOCR Text Extraction ➡️ Regex-based Information Parsing ➡️ Structured JSON Output. It processes documents to pull out key information like patient demographics, symptoms, test results, and more.

### **Medical Code Conversion**

#### **NAMC ➡️ ICD-11**

1. **Local ConceptMap:** A pre-processed FHIR ConceptMap (NAMC\_to\_ICD11\_MultiThreaded\_ConceptMap.json) provides direct, high-confidence mappings for common terms.  
2. **WHO Flexi-search Fallback:** If a direct mapping isn't found, the API intelligently queries the official **WHO ICD-11 API** using its "Flexi-search" capability to find relevant ICD-11 codes based on the English NAMC term. This ensures comprehensive coverage.

#### **ICD-11 ➡️ NAMC**

* A fast, in-memory **reverse lookup map** built from the ConceptMap allows for quick and accurate conversion from ICD-11 codes back to relevant NAMC terms and their definitions.

### **Natural Language Processing (NLP) Search**

* **Embeddings:** **LangChain** and **HuggingFace Embeddings** (specifically, all-MiniLM-L6-v2) are used to create semantic embeddings of all NAMC concepts.  
* **Vector Store:** These embeddings are stored and queried in a persistent local vector database (**Chroma Vector Store** in the chroma\_db\_persistent directory).  
* **Functionality:** This enables powerful semantic search, allowing users to find relevant NAMC concepts even with nuanced or vaguely worded queries.  
* **Offline Capability:** Once the vector store is built, NLP search functions entirely offline, without relying on external LLM APIs.

### **Backend & API**

* **Framework:** **Flask** (lightweight Python web framework).  
* **Dependencies:** Flask-CORS (for frontend integration), requests (for secure external API calls to WHO), and thefuzz / python-Levenshtein (for robust string matching and autocomplete).

## **Getting Started**

### **1\. Prerequisites**

* Python 3.8+  
* pip (Python package installer)

### **2\. Installation**

Clone the repository:

git clone \[your-repo-link\]  
cd EMR-Assistant

Install Python Dependencies:

pip install \-r requirements.txt

**Important for EasyOCR:** EasyOCR requires torch. If pip install easyocr doesn't automatically set up torch correctly for your system (especially if you need GPU support), you might need to install torch manually first. For most CPU-only setups, use the following command *before* installing requirements.txt:

pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 \--index-url \[https://download.pytorch.org/whl/cpu\](https://download.pytorch.org/whl/cpu)

### **3\. Data Files**

Ensure the Data/ directory contains the following crucial files for the project's functionality:

* SiddhaJson.json  
* AyurvedaJson.json  
* UnaniJson.json  
* NAMC\_to\_ICD11\_MultiThreaded\_ConceptMap.json

### **4\. Run the Application**

python main.py

The server will start on http://127.0.0.1:5000 (or localhost:5000).

### **5\. Access the Interface**

* **Web UI:** Open your browser and go to http://127.0.0.1:5000  
* **API Documentation (Swagger UI):** Explore the API endpoints at http://127.0.0.1:5000/swagger

## **API Endpoints**

| Method | Endpoint | Description |
| :---- | :---- | :---- |
| GET | / | Serves the main web interface (index.html). |
| POST | /api/ocr\_upload | Upload an image for OCR and structured data extraction. |
| POST | /api/nlp\_search | Perform semantic search on NAMC concepts. |
| GET | /api/suggestions | Get autocomplete suggestions for NAMC terms. |
| POST | /api/submit | Convert NAMC code to ICD-11 (using map & flexi-search). |
| GET | /api/ICDtoNAMC | Convert ICD-11 code to NAMC (using reverse map). |
| GET | /api/newToken | Acquire a WHO API access token (for client-side ICD calls). |

## **Contributing**

Contributions are welcome\! Feel free to open issues, submit pull requests, or suggest improvements.