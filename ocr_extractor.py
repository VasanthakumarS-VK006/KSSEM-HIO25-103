import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import pytesseract
import re

def process_image(image_path):
    """Extract text from image using Tesseract OCR"""
    try:
        # Check for Tesseract installation
        if os.name == 'nt':  # Windows
            default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path
            else:
                messagebox.showwarning(
                    "Tesseract Not Found",
                    "Please install Tesseract-OCR from:\nhttps://github.com/UB-Mannheim/tesseract/wiki\n"
                    "And ensure it's installed in the default location."
                )
                return None, None, None
        
        # Open and process image
        image = Image.open(image_path).convert('RGB')
        
        # Extract text from image
        text = pytesseract.image_to_string(
            image,
            config='--psm 6 --oem 3',
            lang='eng'
        )
        
        # Clean up the text
        text = text.replace('|', '').replace('=', ':').replace('_', ' ')
        text = text.strip()
        
        # Initialize result structure
        info = {
            "Report Type": "",
            "Date": "",
            "Patient Info": {
                "Name": "",
                "Age": "",
                "Sex": "",
                "Previous Hospital": "",
                "Symptoms": "",
                "Signs": ""
            },
            "Test Results": {},
            "Interpretation": "",
            "Summary": ""
        }
        
        lines = text.split('\n')
        test_results = {}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Extract Report Type
            if "LABORATORY REPORT" in line.upper():
                info["Report Type"] = line.strip()
            
            # Extract Date
            if "Date" in line:
                date_match = re.search(r'Date[:\s=]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
                if date_match:
                    info["Date"] = date_match.group(1).strip()
            
            # Extract Patient Info
            # Name (inline like 'Name: John Doe' or 'Patient Name: John Doe')
            if re.search(r'\b(?:Name|Patient Name|Patient)[:\s-]+', line, re.I):
                name_match = re.search(r'\b(?:Name|Patient Name|Patient)[:\s-]+(.+)', line, re.I)
                if name_match:
                    info["Patient Info"]["Name"] = name_match.group(1).strip()
                    continue
            # Previous Hospital / Referred from
            if re.search(r'\b(?:Previous Hospital|Referred from|Referring Hospital|Ref Hospital|Refd from)[:\s-]+', line, re.I):
                ph_match = re.search(r'\b(?:Previous Hospital|Referred from|Referring Hospital|Ref Hospital|Refd from)[:\s-]+(.+)', line, re.I)
                if ph_match:
                    info["Patient Info"]["Previous Hospital"] = ph_match.group(1).strip()
                    continue

            if "Age" in line:
                age_match = re.search(r'Age[:\s=]+(\d+)', line)
                if age_match:
                    info["Patient Info"]["Age"] = age_match.group(1).strip()
            elif "Sex" in line:
                sex_match = re.search(r'Sex[:\s=]+(\w+)', line)
                if sex_match:
                    info["Patient Info"]["Sex"] = sex_match.group(1).strip()
            # Symptoms: handle inline 'Symptoms: fever, cough' or multi-line lists
            elif re.search(r'\b(symptoms|presenting complaint|complaints)[:\s]*', line, re.I):
                # If inline after colon
                parts = re.split(r'[:]', line, maxsplit=1)
                if len(parts) == 2 and parts[1].strip():
                    info["Patient Info"]["Symptoms"] = parts[1].strip()
                else:
                    symptoms = []
                    j = i + 1
                    # stop when next section header likely appears (uppercase words followed by ':' or known keywords)
                    while j < len(lines):
                        nxt = lines[j].strip()
                        if not nxt:
                            break
                        if re.match(r'^[A-Z][A-Za-z ]{0,50}:', nxt) or any(k in nxt.lower() for k in ["signs", "interpretation", "summary", "test results", "date", "age", "sex"]):
                            break
                        symptoms.append(nxt)
                        j += 1
                    info["Patient Info"]["Symptoms"] = ", ".join(symptoms)
            elif "Signs" in line:
                signs = []
                j = i + 1
                while j < len(lines) and not any(key in lines[j].lower() for key in ["symptoms", "color", "consistency"]):
                    if lines[j].strip():
                        signs.append(lines[j].strip())
                    j += 1
                info["Patient Info"]["Signs"] = ", ".join(signs)
            
            # Extract Test Results
            if any(x in line.lower() for x in ["color", "consistency", "bacterial", "leukocytes", "blood", "parasites"]):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    test_results[key] = value
            
            # Extract Interpretation
            if "Interpretation" in line:
                interpretation_lines = []
                j = i + 1
                while j < len(lines) and lines[j].strip():
                    interpretation_lines.append(lines[j].strip())
                    j += 1
                info["Interpretation"] = " ".join(interpretation_lines)
            
            # Extract Summary
            if "summary" in line.lower():
                summary_lines = []
                j = i
                while j < len(lines) and lines[j].strip():
                    summary_lines.append(lines[j].strip())
                    j += 1
                info["Summary"] = " ".join(summary_lines)
        
        info["Test Results"] = test_results
        
        return info, image, text
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return None, None, None

def main():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Ask user to select an image file
    file_path = filedialog.askopenfilename(
        title="Select Medical Document Image",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.tif;*.tiff")]
    )
    
    if file_path:
        try:
            info, image, raw_text = process_image(file_path)
            
            if info:
                # Save results to JSON file
                output_path = os.path.splitext(file_path)[0] + "_results.json"
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(info, f, indent=2, ensure_ascii=False)
                
                print(f"Results saved to: {output_path}")
                print("\nExtracted Information:")
                print(json.dumps(info, indent=2, ensure_ascii=False))
                
                # Optionally display the image
                image.show()
                
                return 0  # Success
            else:
                print("Failed to extract information from the image.")
                return 1  # Error
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return 1  # Error
    
    else:
        print("No file selected.")
        return 1  # Error

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)