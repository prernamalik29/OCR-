import re
import pytesseract
from PIL import Image

def detect_id_card(text):
    # Convert text to uppercase for better matching
    text_upper = text.upper()
    
    # Check for Aadhaar card patterns
    aadhaar_patterns = [
        r"\b\d{4}\s?\d{4}\s?\d{4}\b",  # 12-digit number pattern
        r"AADHAAR",
        r"आधार",
        r"UNIQUE IDENTIFICATION AUTHORITY OF INDIA",
        r"UIDAI",
        r"BHARAT SARKAR",
        r"GOVERNMENT OF INDIA"
    ]
    
    aadhaar_score = 0
    for pattern in aadhaar_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            aadhaar_score += 1
    
    # Check for PAN card patterns
    pan_patterns = [
        r"[A-Z]{5}[0-9]{4}[A-Z]{1}",  # PAN number pattern
        r"INCOME TAX DEPARTMENT",
        r"PERMANENT ACCOUNT NUMBER",
        r"PAN",
        r"INCOME TAX",
        r"TAX DEPARTMENT"
    ]
    
    pan_score = 0
    for pattern in pan_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            pan_score += 1
    
    # Check for Passport patterns
    passport_patterns = [
        r"[A-Z]{1}[0-9]{7}",  # Passport number pattern
        r"PASSPORT",
        r"REPUBLIC OF INDIA",
        r"GOVERNMENT OF INDIA",
        r"MINISTRY OF EXTERNAL AFFAIRS",
        r"PASSPORT OFFICE",
        r"PASSPORT AUTHORITY"
    ]
    
    passport_score = 0
    for pattern in passport_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            passport_score += 1
    
    # Check for Driving License patterns
    dl_patterns = [
        r"[A-Z]{2}\d{2}\s?\d{11}\s?\d{4}",  # DL number pattern
        r"DRIVING LICENCE",
        r"DRIVING LICENSE",
        r"LEARNER'S LICENCE",
        r"MOTOR VEHICLES ACT",
        r"RTO",
        r"TRANSPORT DEPARTMENT",
        r"LICENCE AUTHORITY"
    ]
    
    dl_score = 0
    for pattern in dl_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            dl_score += 1
    
    # Check for Voter ID patterns
    voter_patterns = [
        r"[A-Z]{3}\d{7}",  # Voter ID number pattern
        r"ELECTION COMMISSION OF INDIA",
        r"VOTER ID",
        r"ELECTORAL PHOTO IDENTITY CARD",
        r"EPIC",
        r"ELECTION COMMISSION"
    ]
    
    voter_score = 0
    for pattern in voter_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            voter_score += 1
    
    # Determine the ID type based on highest score
    scores = {
        "Aadhaar Card": aadhaar_score,
        "PAN Card": pan_score,
        "Passport": passport_score,
        "Driving License": dl_score,
        "Voter ID": voter_score
    }
    
    # Find the type with highest score
    max_score = max(scores.values())
    if max_score > 0:
        # Return the type with highest score
        for id_type, score in scores.items():
            if score == max_score:
                return id_type
    
    # If no clear match, try additional heuristics
    if re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text):
        return "Aadhaar Card"
    elif re.search(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", text):
        return "PAN Card"
    elif re.search(r"[A-Z]{1}[0-9]{7}", text):
        return "Passport"
    elif re.search(r"[A-Z]{2}\d{2}\s?\d{11}\s?\d{4}", text):
        return "Driving License"
    elif re.search(r"[A-Z]{3}\d{7}", text):
        return "Voter ID"
    
    return "Unknown ID Type"

def extract_id_info(image_path):
    # Load image
    img = Image.open(image_path)
    
    # Perform OCR
    text = pytesseract.image_to_string(img, lang='eng+hin')
    
    # Detect ID type
    id_type = detect_id_card(text)
    
    # Extract specific details based on ID type
    details = {}
    
    # Common date patterns in Indian ID cards
    date_patterns = [
        r'\b\d{2}[/-]\d{2}[/-]\d{4}\b',  # DD/MM/YYYY or DD-MM-YYYY
        r'\b\d{2}\.\d{2}\.\d{4}\b',      # DD.MM.YYYY
        r'\b\d{4}[/-]\d{2}[/-]\d{2}\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\bDOB[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})\b',  # DOB: DD/MM/YYYY
        r'\bDate of Birth[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})\b'  # Date of Birth: DD/MM/YYYY
    ]
    
    # Try to find date of birth using various patterns
    for pattern in date_patterns:
        dob_match = re.search(pattern, text, re.IGNORECASE)
        if dob_match:
            # Extract the date part from the match
            dob = dob_match.group(1) if len(dob_match.groups()) > 0 else dob_match.group(0)
            details["Date of Birth"] = dob
            break
    
    # Extract name patterns
    name_patterns = [
        r"(?:Name|Name of Applicant|Name of Holder)'[:\s]+([A-Za-z\s\.]+)(?:\n|$)",
        r"([A-Za-z\s\.]+)(?:\n|$)(?=.*DOB|.*Date of Birth|.*Birth)",
        r"(?:Name|Name of Applicant|Name of Holder)[:\s]*([A-Za-z\s\.]+)(?=\s*DOB|\s*Date|\s*Birth|\s*Father|\s*Mother)",
        r"([A-Za-z\s\.]+)(?=\s*DOB|\s*Date|\s*Birth|\s*Father|\s*Mother|\s*Permanent|\s*PAN|\s*Passport|\s*DL|\s*EPIC)"
    ]
    
    for pattern in name_patterns:
        name_match = re.search(pattern, text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            # Clean up the name
            name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
            name = re.sub(r'[^A-Za-z\s\.]', '', name)  # Remove special characters except spaces and dots
            name = name.strip()  # Remove leading/trailing spaces
            if name and len(name) > 2:  # Only store if name is not empty and has reasonable length
                details["Name"] = name
                break
    
    if id_type == "Aadhaar Card":
        aadhaar_no = re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text)
        if aadhaar_no:
            details["Aadhaar Number"] = aadhaar_no.group().replace(" ", "")
    
    elif id_type == "PAN Card":
        pan_no = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", text)
        if pan_no:
            details["PAN Number"] = pan_no.group()
    
    elif id_type == "Passport":
        passport_no = re.search(r"[A-Z]{1}[0-9]{7}", text)
        if passport_no:
            details["Passport Number"] = passport_no.group()
    
    elif id_type == "Driving License":
        dl_no = re.search(r"[A-Z]{2}\d{2}\s?\d{11}\s?\d{4}", text)
        if dl_no:
            details["DL Number"] = dl_no.group().replace(" ", "")
    
    elif id_type == "Voter ID":
        voter_id = re.search(r"[A-Z]{3}\d{7}", text)
        if voter_id:
            details["Voter ID Number"] = voter_id.group()
    
    return {
        "ID Type": id_type,
        "Details": details,
        "Raw Text": text
    }

if __name__ == "__main__":
    result = extract_id_info("ac4.jpg")
    print("--------------------------------")
    print(f"Detected ID Type: {result['ID Type']}")
    print("--------------------------------")
    print("Extracted Details:")
    for key, value in result['Details'].items():
        print(f"{key}: {value}")



#dl1 , dl3 , dl5 , dl6 , dl7 , dl10 , dl_b&w