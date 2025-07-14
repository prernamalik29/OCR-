import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import re
import pytesseract
from datetime import datetime

class IDVerificationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ID Card Verification System")
        self.root.geometry("1200x800")
        
        # Store uploaded images and their extracted information
        self.uploaded_images = []
        self.extracted_info = []
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Upload buttons
        self.upload_frame = ttk.LabelFrame(self.main_frame, text="Upload ID Cards", padding="10")
        self.upload_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(self.upload_frame, text="Upload ID Card", command=self.upload_image).grid(row=0, column=0, padx=5)
        ttk.Button(self.upload_frame, text="Verify IDs", command=self.verify_ids).grid(row=0, column=1, padx=5)
        ttk.Button(self.upload_frame, text="Clear All", command=self.clear_all).grid(row=0, column=2, padx=5)
        
        # Create scrollable frames
        self.create_scrollable_frames()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
    def create_scrollable_frames(self):
        # Image display area with scrollbar
        self.image_frame = ttk.LabelFrame(self.main_frame, text="Uploaded Images", padding="10")
        self.image_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Create canvas and scrollbar for images
        self.image_canvas = tk.Canvas(self.image_frame)
        self.image_scrollbar = ttk.Scrollbar(self.image_frame, orient="vertical", command=self.image_canvas.yview)
        self.image_scrollable_frame = ttk.Frame(self.image_canvas)
        
        self.image_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
        )
        self.image_canvas.create_window((0, 0), window=self.image_scrollable_frame, anchor="nw")
        self.image_canvas.configure(yscrollcommand=self.image_scrollbar.set)
        
        self.image_canvas.pack(side="left", fill="both", expand=True)
        self.image_scrollbar.pack(side="right", fill="y")
        
        # Results area with scrollbar
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Verification Results", padding="10")
        self.results_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Create canvas and scrollbar for results
        self.results_canvas = tk.Canvas(self.results_frame)
        self.results_scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_canvas.yview)
        self.results_scrollable_frame = ttk.Frame(self.results_canvas)
        
        self.results_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )
        self.results_canvas.create_window((0, 0), window=self.results_scrollable_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)
        
        self.results_canvas.pack(side="left", fill="both", expand=True)
        self.results_scrollbar.pack(side="right", fill="y")
        
    def upload_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if file_path:
            # Extract information from the image
            try:
                result = self.extract_id_info(file_path)
                
                # Store the image and its information
                self.uploaded_images.append(file_path)
                self.extracted_info.append(result)
                
                # Display the image
                self.display_image(file_path)
                
                # Display extracted information
                self.display_info(result)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process image: {str(e)}")
    
    def display_image(self, image_path):
        # Create a frame for the new image
        img_frame = ttk.Frame(self.image_scrollable_frame)
        img_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        try:
            # Load and resize image
            img = Image.open(image_path)
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Display image
            label = ttk.Label(img_frame, image=photo)
            label.image = photo  # Keep a reference
            label.pack()
            
            # Add image path label
            ttk.Label(img_frame, text=os.path.basename(image_path)).pack()
        except Exception as e:
            ttk.Label(img_frame, text=f"Error loading image: {os.path.basename(image_path)}").pack()
    
    def display_info(self, info):
        # Create a frame for the information
        info_frame = ttk.Frame(self.results_scrollable_frame)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Display ID type
        ttk.Label(info_frame, text=f"ID Type: {info.get('ID Type', 'Unknown')}", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        # Display extracted details
        details = info.get('Details', {})
        for key, value in details.items():
            ttk.Label(info_frame, text=f"{key}: {value}").pack(anchor=tk.W)
        
        ttk.Separator(info_frame, orient='horizontal').pack(fill='x', pady=5)
    
    def verify_ids(self):
        if len(self.extracted_info) < 2:
            messagebox.showwarning("Warning", "Please upload at least 2 ID cards for verification")
            return
        
        # Clear previous verification results
        for widget in self.results_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Compare all pairs of IDs
        all_comparisons = []
        for i in range(len(self.extracted_info)):
            for j in range(i + 1, len(self.extracted_info)):
                comparison = self.compare_info(self.extracted_info[i], self.extracted_info[j])
                all_comparisons.append(comparison)
                self.display_comparison(self.extracted_info[i], self.extracted_info[j], comparison)
        
        # Determine overall verification result
        overall_result = self.determine_overall_result(all_comparisons)
        
        # Display overall verification result at the top of results
        result_frame = ttk.Frame(self.results_scrollable_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        if overall_result == "match":
            result_text = "✅ All ID cards belong to the same person!"
            color = "green"
        elif overall_result == "partial":
            result_text = "⚠️ Some ID cards match but not all. Please review carefully."
            color = "orange"
        else:
            result_text = "❌ ID cards do not belong to the same person!"
            color = "red"
            
        ttk.Label(result_frame, text=result_text, font=('Arial', 12, 'bold'), foreground=color).pack(anchor=tk.W)
        ttk.Separator(result_frame, orient='horizontal').pack(fill='x', pady=5)
    
    def compare_info(self, info1, info2):
        comparison = {
            'name_match': False,
            'dob_match': False,
            'card_match': False,
            'total_fields': 0,
            'matching_fields': 0
        }
        
        # Helper function to clean and standardize values
        def clean_value(value):
            if not value:
                return ""
            # Remove extra spaces and convert to uppercase
            cleaned = ' '.join(str(value).strip().upper().split())
            # Remove special characters except spaces and dots
            cleaned = re.sub(r'[^A-Z\s\.]', '', cleaned)
            return cleaned
        
        # Compare name
        name1 = clean_value(info1.get('Details', {}).get('Name'))
        name2 = clean_value(info2.get('Details', {}).get('Name'))
        if name1 and name2:
            comparison['total_fields'] += 1
            # Compare names after cleaning
            comparison['name_match'] = name1 == name2
            if comparison['name_match']:
                comparison['matching_fields'] += 1
        
        # Compare date of birth
        dob1 = info1.get('Details', {}).get('Date of Birth')
        dob2 = info2.get('Details', {}).get('Date of Birth')
        if dob1 and dob2:
            comparison['total_fields'] += 1
            # Standardize both dates before comparison
            std_dob1 = self.standardize_date(dob1)
            std_dob2 = self.standardize_date(dob2)
            comparison['dob_match'] = std_dob1 == std_dob2
            if comparison['dob_match']:
                comparison['matching_fields'] += 1
        
        # Compare card numbers
        card1 = info1.get('Details', {}).get('Card Number')
        card2 = info2.get('Details', {}).get('Card Number')
        if card1 and card2:
            comparison['total_fields'] += 1
            comparison['card_match'] = card1 == card2
            if comparison['card_match']:
                comparison['matching_fields'] += 1
        
        return comparison
    
    def display_comparison(self, info1, info2, comparison):
        # Create a frame for the comparison
        comp_frame = ttk.LabelFrame(self.results_scrollable_frame, 
                                  text=f"Comparing {info1.get('ID Type', 'ID 1')} with {info2.get('ID Type', 'ID 2')}")
        comp_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Determine match status - Updated to consider DOB or card number match as sufficient
        if comparison['dob_match'] or comparison['card_match']:
            pair_status = "✅ ID cards belong to the same person (DOB or Card Number matches)"
            color = "green"
        elif comparison['name_match']:
            pair_status = "⚠️ ID cards may belong to the same person (Name matches)"
            color = "orange"
        else:
            pair_status = "❌ ID cards do not belong to the same person"
            color = "red"
        
        # Display match status
        ttk.Label(comp_frame, text=pair_status, font=('Arial', 12, 'bold'), foreground=color).pack(anchor=tk.W)
        
        # Display detailed comparison
        details_frame = ttk.Frame(comp_frame)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Name comparison with cleaned values
        name1 = info1.get('Details', {}).get('Name', 'Not found')
        name2 = info2.get('Details', {}).get('Name', 'Not found')
        name_status = "✅" if comparison['name_match'] else "❌"
        ttk.Label(details_frame, text=f"Name: {name_status}").pack(anchor=tk.W)
        ttk.Label(details_frame, text=f"  ID 1: {name1}").pack(anchor=tk.W)
        ttk.Label(details_frame, text=f"  ID 2: {name2}").pack(anchor=tk.W)
        if comparison['name_match']:
            cleaned_name = ' '.join(name1.strip().upper().split())
            ttk.Label(details_frame, text=f"  Standardized Name: {cleaned_name}").pack(anchor=tk.W)
        
        # DOB comparison
        dob1 = info1.get('Details', {}).get('Date of Birth', 'Not found')
        dob2 = info2.get('Details', {}).get('Date of Birth', 'Not found')
        dob_status = "✅" if comparison['dob_match'] else "❌"
        ttk.Label(details_frame, text=f"Date of Birth: {dob_status}").pack(anchor=tk.W)
        ttk.Label(details_frame, text=f"  ID 1: {dob1}").pack(anchor=tk.W)
        ttk.Label(details_frame, text=f"  ID 2: {dob2}").pack(anchor=tk.W)
        if comparison['dob_match']:
            std_dob1 = self.standardize_date(dob1)
            ttk.Label(details_frame, text=f"  Standardized Date: {std_dob1}").pack(anchor=tk.W)
        
        # Card number comparison
        card1 = info1.get('Details', {}).get('Card Number', 'Not found')
        card2 = info2.get('Details', {}).get('Card Number', 'Not found')
        card_status = "✅" if comparison['card_match'] else "❌"
        ttk.Label(details_frame, text=f"Card Number: {card_status}").pack(anchor=tk.W)
        ttk.Label(details_frame, text=f"  ID 1: {card1}").pack(anchor=tk.W)
        ttk.Label(details_frame, text=f"  ID 2: {card2}").pack(anchor=tk.W)
        
        ttk.Separator(comp_frame, orient='horizontal').pack(fill='x', pady=5)
    
    def determine_overall_result(self, all_comparisons):
        if not all_comparisons:
            return "no_match"
        
        # Check if any comparison has DOB or card number match
        for comp in all_comparisons:
            if comp['dob_match'] or comp['card_match']:
                return "match"
        
        # Check if any comparison has name match
        for comp in all_comparisons:
            if comp['name_match']:
                return "partial"
        
        return "no_match"
    
    def clear_all(self):
        # Clear all stored data
        self.uploaded_images = []
        self.extracted_info = []
        
        # Clear all displayed widgets
        for widget in self.image_scrollable_frame.winfo_children():
            widget.destroy()
        for widget in self.results_scrollable_frame.winfo_children():
            widget.destroy()

    def detect_id_card(self, text):
        # Check for Aadhaar card patterns
        if re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text) or "आधार" in text or "AADHAAR" in text.upper():
            return "Aadhaar Card"
        
        # Check for PAN card patterns
        elif re.search(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", text) or "INCOME TAX DEPARTMENT" in text or "PERMANENT ACCOUNT NUMBER" in text:
            return "PAN Card"
        
        # Check for Passport patterns
        elif re.search(r"[A-Z]{1}[0-9]{7}", text) or "PASSPORT" in text.upper() or "REPUBLIC OF INDIA" in text.upper() or "Government of India" in text:
            return "Passport"
        
        # Check for Driving License patterns
        elif re.search(r"[A-Z]{2}\d{2}\s?\d{11}\s?\d{4}", text) or "DRIVING LICENCE" in text.upper() or "DRIVING LICENSE" in text.upper():
            return "Driving License"
        
        # Check for Voter ID patterns
        elif re.search(r"[A-Z]{3}\d{7}", text) or "ELECTION COMMISSION OF INDIA" in text.upper() or "VOTER ID" in text.upper():
            return "Voter ID"
        
        else:
            return "Unknown ID Type"

    def extract_id_info(self, image_path):
        # Load image
        img = Image.open(image_path)
        
        # Perform OCR
        text = pytesseract.image_to_string(img, lang='eng+hin')
        
        # Detect ID type
        id_type = self.detect_id_card(text)
        
        # Extract specific details based on ID type
        details = {}
        
        # Extract name with improved patterns for different ID types
        name_patterns = {
            "Aadhaar Card": [
                r"(?:Name|Name of Applicant)'[:\s]+([A-Za-z\s\.]+)(?:\n|$)",
                r"([A-Za-z\s\.]+)(?:\n|$)(?=.*DOB|.*Date of Birth)"
            ],
            "PAN Card": [
                r"(?:Name of Applicant|Name)[:\s]*([a-zA-Z\s\.]+)(?=\s*Permanent Account Number|\s*PAN|\s*DOB)",
                r"([A-Za-z\s\.]+)(?=\s*Permanent Account Number|\s*PAN|\s*DOB)",
                r"([A-Za-z\s\.]+)(?=\s*Father's Name|\s*Mother's Name)"
            ],
            "Passport": [
                r"(?:Name|Name of Applicant)[:\s]+([A-Za-z\s\.]+)(?:\n|$)",
                r"([A-Za-z\s\.]+)(?:\n|$)(?=.*Passport No|.*DOB)"
            ],
            "Driving License": [
                r"(?:Name|Name of Applicant)[:\s]+([A-Za-z\s\.]+)(?:\n|$)",
                r"([A-Za-z\s\.]+)(?:\n|$)(?=.*DL No|.*DOB)"
            ],
            "Voter ID": [
                r"(?:Name|Name of Applicant)[:\s]+([A-Za-z\s\.]+)(?:\n|$)",
                r"([A-Za-z\s\.]+)(?:\n|$)(?=.*EPIC No|.*DOB)"
            ]
        }
        
        # Try to extract name using ID-specific patterns
        patterns = name_patterns.get(id_type, name_patterns["Aadhaar Card"])
        for pattern in patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
                name = re.sub(r'[^A-Za-z\s\.]', '', name)  # Remove special characters except spaces and dots
                name = name.strip()  # Remove leading/trailing spaces
                if name:  # Only store if name is not empty after cleaning
                    details["Name"] = name
                    break
        
        # Extract date of birth with improved patterns
        dob_patterns = [
            r"(?:DOB|Date of Birth|Birth Date)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})",
            r"(?:DOB|Date of Birth|Birth Date)[:\s]+(\d{2}\.\d{2}\.\d{4})",
            r"(?:DOB|Date of Birth|Birth Date)[:\s]+(\d{4}[/-]\d{2}[/-]\d{2})",
            r"(?:DOB|Date of Birth|Birth Date)[:\s]*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            r"(?:DOB|Date of Birth|Birth Date)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"(?:Birth|Born)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"(?:Birth|Born)[:\s]*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
            r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b"
        ]
        
        # Extract card numbers based on ID type
        if id_type == "Aadhaar Card":
            # Extract Aadhaar number
            aadhaar_patterns = [
                r"\b\d{4}\s?\d{4}\s?\d{4}\b",
                r"Aadhaar No[:\s]+(\d{4}\s?\d{4}\s?\d{4})"
            ]
            for pattern in aadhaar_patterns:
                aadhaar_match = re.search(pattern, text, re.IGNORECASE)
                if aadhaar_match:
                    aadhaar_no = aadhaar_match.group() if len(aadhaar_match.groups()) == 0 else aadhaar_match.group(1)
                    details["Card Number"] = aadhaar_no.replace(" ", "")
                    break
            
            # Extract DOB for Aadhaar using specific patterns
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
        
        elif id_type == "PAN Card":
            # Extract PAN number
            pan_patterns = [
                r"[A-Z]{5}[0-9]{4}[A-Z]{1}",
                r"Permanent Account Number[:\s]+([A-Z]{5}[0-9]{4}[A-Z]{1})"
            ]
            for pattern in pan_patterns:
                pan_match = re.search(pattern, text, re.IGNORECASE)
                if pan_match:
                    pan_no = pan_match.group() if len(pan_match.groups()) == 0 else pan_match.group(1)
                    details["Card Number"] = pan_no
                    break
            
            # Extract DOB for PAN
            pan_dob_patterns = [
                r"(\d{2})[/-](\d{2})[/-](\d{4})",    # 15/01/1990
                r"(\d{2})[/-](\d{2})[/-](\d{2})"     # 15/01/90
            ]
            
            for pattern in pan_dob_patterns:
                dob_match = re.search(pattern, text, re.IGNORECASE)
                if dob_match:
                    groups = dob_match.groups()
                    if len(groups) == 3:
                        day = groups[0]
                        month = groups[1]
                        year = groups[2]
                        
                        if len(year) == 2:
                            year = '19' + year if int(year) > 50 else '20' + year
                        
                        details["Date of Birth"] = f"{day}/{month}/{year}"
                        break
        
        elif id_type == "Passport":
            # Extract Passport number
            passport_patterns = [
                r"[A-Z]{1}[0-9]{7}",
                r"Passport No[:\s]+([A-Z]{1}[0-9]{7})"
            ]
            for pattern in passport_patterns:
                passport_match = re.search(pattern, text, re.IGNORECASE)
                if passport_match:
                    passport_no = passport_match.group() if len(passport_match.groups()) == 0 else passport_match.group(1)
                    details["Card Number"] = passport_no
                    break
            
            # Extract DOB for Passport
            for pattern in dob_patterns:
                dob_match = re.search(pattern, text, re.IGNORECASE)
                if dob_match:
                    dob = dob_match.group(1)
                    try:
                        date_obj = datetime.strptime(dob, "%d/%m/%Y")
                        details["Date of Birth"] = date_obj.strftime("%d/%m/%Y")
                    except:
                        details["Date of Birth"] = dob
                    break
        
        elif id_type == "Driving License":
            # Extract DL number
            dl_patterns = [
                r"[A-Z]{2}\d{2}\s?\d{11}\s?\d{4}",
                r"DL No[:\s]+([A-Z]{2}\d{2}\s?\d{11}\s?\d{4})"
            ]
            for pattern in dl_patterns:
                dl_match = re.search(pattern, text, re.IGNORECASE)
                if dl_match:
                    dl_no = dl_match.group() if len(dl_match.groups()) == 0 else dl_match.group(1)
                    details["Card Number"] = dl_no.replace(" ", "")
                    break
            
            # Extract DOB for DL
            for pattern in dob_patterns:
                dob_match = re.search(pattern, text, re.IGNORECASE)
                if dob_match:
                    dob = dob_match.group(1)
                    try:
                        date_obj = datetime.strptime(dob, "%d/%m/%Y")
                        details["Date of Birth"] = date_obj.strftime("%d/%m/%Y")
                    except:
                        details["Date of Birth"] = dob
                    break
        
        elif id_type == "Voter ID":
            # Extract Voter ID number
            voter_patterns = [
                r"[A-Z]{3}\d{7}",
                r"EPIC No[:\s]+([A-Z]{3}\d{7})"
            ]
            for pattern in voter_patterns:
                voter_match = re.search(pattern, text, re.IGNORECASE)
                if voter_match:
                    voter_no = voter_match.group() if len(voter_match.groups()) == 0 else voter_match.group(1)
                    details["Card Number"] = voter_no
                    break
            
            # Extract DOB for Voter ID
            for pattern in dob_patterns:
                dob_match = re.search(pattern, text, re.IGNORECASE)
                if dob_match:
                    dob = dob_match.group(1)
                    try:
                        date_obj = datetime.strptime(dob, "%d/%m/%Y")
                        details["Date of Birth"] = date_obj.strftime("%d/%m/%Y")
                    except:
                        details["Date of Birth"] = dob
                    break
        
        return {
            "ID Type": id_type,
            "Details": details,
            "Raw Text": text
        }

    def standardize_date(self, date_str):
        if not date_str:
            return None
            
        # Try different date formats
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%Y-%m-%d",
            "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",  # Month names
            "%d/%m/%y", "%d-%m-%y", "%y/%m/%d", "%y-%m-%d"   # 2-digit years
        ]
        
        # Try parsing with datetime
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y")
            except:
                continue
        
        # If all parsing fails, try to extract numbers and reconstruct
        numbers = re.findall(r'\d+', date_str)
        if len(numbers) >= 3:
            day = numbers[0].zfill(2)
            month = numbers[1].zfill(2)
            year = numbers[2]
            if len(year) == 2:
                year = '19' + year if int(year) > 50 else '20' + year
            try:
                return f"{day}/{month}/{year}"
            except:
                pass
        
        return date_str

    def preprocess_text(self, text):
        # Remove extra spaces and normalize separators
        text = re.sub(r'\s+', ' ', text)
        # Normalize different types of dashes and slashes
        text = text.replace('–', '-').replace('—', '-').replace('\\', '/')
        return text

if __name__ == "__main__":
    root = tk.Tk()
    app = IDVerificationApp(root)
    root.mainloop()