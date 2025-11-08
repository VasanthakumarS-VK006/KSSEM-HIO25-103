# This file converts csv or xls file into json file in complaint with FHIR format
import csv
import pandas
import json

# df = pandas.read_excel("Data/NATIONAL SIDDHA MORBIDITY CODES.xls")
# df.to_csv("Data/Siddha.csv", index=False)

data = []

with open("Data/Siddha.csv") as file:
    csv_reader = csv.DictReader(file)

    for row in csv_reader:
        data.append({
            "code": row["NAMC_CODE"],
            "display": row["Short_definition"],
            "definition": row["Long_definition"],
            "designation": [
                {
                    "language": "en",
                    "value": row["NAMC_TERM"]

                }
            ]
        })


codesystem = {
    "resourceType": "CodeSystem",
    "id": "namc",
    "url": "https://ndhm.gov.in/fhir/CodeSystem/namc",
    "version": "1.0.0",
    "name": "NAMCCodeSystem",
    "title": "National AYUSH Morbidity Codes (NAMC)",
    "status": "active",
    "content": "complete",
    "publisher": "Ministry of AYUSH",
    "description": "Standardized National AYUSH Morbidity Codes (NAMC) for Ayurveda, Siddha, and Unani disorders.",
    "concept": data
}


with open("Data/SiddhaJson.json", mode='w') as file:
    json.dump(codesystem, file, indent=4, ensure_ascii=False)
