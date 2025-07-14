import cv2
from PIL import Image, ImageTk
import os
from identification import extract_id_info, detect_id_card
import re
from test import IDVerificationApp
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import traceback
# Add for PDF support
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
    # User will be notified in the GUI if pdf2image is missing

class SimpleIDCardGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Identity Card Detection & Verification")
        self.root.geometry("800x700")
        self.uploaded_file = None
        self.second_file = None
        self.result = None
        self.compare_var = tk.BooleanVar()
        self.create_widgets()
        self.id_verifier = IDVerificationApp(tk.Tk())  # Hidden root for comparison logic
        self.id_verifier.root.withdraw()

    def create_widgets(self):
        # Title
        title = ttk.Label(self.root, text="Identity Card Detection & Verification", font=("Arial", 18, "bold"))
        title.pack(pady=(20, 10))

        # Upload area frame
        upload_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE, bg="#f8f8ff", height=200, width=600)
        upload_frame.pack(pady=10)
        upload_frame.pack_propagate(False)
        self.upload_frame = upload_frame

        # Upload icon and text
        icon = ttk.Label(upload_frame, text="📄", font=("Arial", 48))
        icon.pack(pady=(20, 0))
        upload_text = ttk.Label(upload_frame, text="Browse or Drag & Drop your files here", font=("Arial", 12))
        upload_text.pack(pady=(10, 0))
        formats = ttk.Label(upload_frame, text="Supported formats: PDF, JPEG", font=("Arial", 10, "italic"))
        formats.pack(pady=(0, 10))
        browse_btn = ttk.Button(upload_frame, text="Browse", command=self.browse_file)
        browse_btn.pack()
        upload_frame.bind("<Button-1>", lambda e: self.browse_file())

        # File name label
        self.file_label = ttk.Label(self.root, text="", font=("Arial", 10))
        self.file_label.pack(pady=(5, 0))

        # Checkbox for comparison
        compare_checkbox = ttk.Checkbutton(self.root, text="Compare with another ID card", variable=self.compare_var, command=self.toggle_compare)
        compare_checkbox.pack(pady=(10, 0))

        # Second file upload (initially disabled)
        self.second_browse_btn = ttk.Button(self.root, text="Browse Second ID Card", command=self.browse_second_file, state=tk.DISABLED)
        self.second_browse_btn.pack()
        self.second_file_label = ttk.Label(self.root, text="", font=("Arial", 10))
        self.second_file_label.pack(pady=(5, 0))

        # Process button
        self.process_btn = ttk.Button(self.root, text="Process", command=self.process_file, state=tk.DISABLED)
        self.process_btn.pack(pady=20)

        # Results area with scrollbar
        results_container = tk.Frame(self.root)
        results_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        self.results_canvas = tk.Canvas(results_container, borderwidth=0)
        self.results_scrollbar = ttk.Scrollbar(results_container, orient="vertical", command=self.results_canvas.yview)
        self.results_frame = tk.Frame(self.results_canvas)
        self.results_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )
        self.results_canvas.create_window((0, 0), window=self.results_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)
        self.results_canvas.pack(side="left", fill="both", expand=True)
        self.results_scrollbar.pack(side="right", fill="y")
        self.results_widgets = []

    def toggle_compare(self):
        if self.compare_var.get():
            self.second_browse_btn.config(state=tk.NORMAL)
        else:
            self.second_browse_btn.config(state=tk.DISABLED)
            self.second_file = None
            self.second_file_label.config(text="")

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("All Supported", "*.jpg *.jpeg *.png *.bmp *.gif *.pdf"),
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ]
        )
        if file_path:
            self.uploaded_file = file_path
            self.file_label.config(text=f"Selected: {os.path.basename(file_path)}")
            self.process_btn.config(state=tk.NORMAL)
            self.clear_results()

    def browse_second_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("All Supported", "*.jpg *.jpeg *.png *.bmp *.gif *.pdf"),
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ]
        )
        if file_path:
            self.second_file = file_path
            self.second_file_label.config(text=f"Second: {os.path.basename(file_path)}")
            self.clear_results()

    def process_file(self):
        self.clear_results()
        if not self.uploaded_file:
            messagebox.showwarning("No file", "Please upload a file first.")
            return
        ext = os.path.splitext(self.uploaded_file)[-1].lower()
        is_image = ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif"]
        is_pdf = ext == ".pdf"

        num_label = ttk.Label(self.results_frame, text="Processing uploaded document...", font=("Arial", 12, "bold"))
        num_label.pack(anchor=tk.W, pady=(0, 10))
        self.results_widgets.append(num_label)
        
        accessible = os.path.exists(self.uploaded_file)
        self.show_result_row("Confirm that the document is uploaded and accessible.", accessible)
        expected_format = is_image or is_pdf
        self.show_result_row("Check if the document is in the expected format (e.g. PDF, image, scanned document).", expected_format)

        infos = []
        info2 = None
        used_split = False
        num_cards_detected = 0
        temp_pdf_images = []
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if is_pdf:
                if convert_from_path is None:
                    raise ImportError("pdf2image is not installed. Please install it with 'pip install pdf2image' and ensure poppler is available.")
                try:
                    pages = convert_from_path(self.uploaded_file, poppler_path=r"ACTUAL_PATH_TO_BIN")
                    print(len(pages))
                except Exception as e:
                    traceback.print_exc()
                    error_label = tk.Label(self.results_frame, text=f"Error reading PDF: {str(e)}\nCheck if Poppler is installed and in PATH.", font=("Arial", 12), fg="red")
                    error_label.pack(anchor=tk.W, pady=(20, 10))
                    self.results_widgets.append(error_label)
                    return
                if not pages:
                    error_label = tk.Label(self.results_frame, text="No pages found in PDF.", font=("Arial", 12), fg="red")
                    error_label.pack(anchor=tk.W, pady=(20, 10))
                    self.results_widgets.append(error_label)
                    return
                for page_idx, pil_img in enumerate(pages):
                    temp_img_path = f"_temp_pdf_page_{page_idx}.jpg"
                    pil_img.save(temp_img_path, 'JPEG')
                    temp_pdf_images.append(temp_img_path)
                    img = cv2.imread(temp_img_path)
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                    if len(faces) >= 1:
                        for idx, (x, y, w, h) in enumerate(faces):
                            card_img = img[y:y+h, x:x+w]
                            temp_card_path = f"_temp_pdf_page_{page_idx}_card_{idx}.jpg"
                            cv2.imwrite(temp_card_path, card_img)
                            info = extract_id_info(temp_card_path)
                            infos.append(info)
                            os.remove(temp_card_path)
                    else:
                        info = extract_id_info(temp_img_path)
                        infos.append(info)
                num_cards_detected = len(infos)
            elif is_image and not self.second_file and self.compare_var.get():
                img = cv2.imread(self.uploaded_file)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                num_cards_detected = len(faces)
                if len(faces) >= 2:
                    infos = []
                    for idx, (x, y, w, h) in enumerate(faces):
                        card_img = img[y:y+h, x:x+w]
                        temp_path = f"_temp_card_{idx}.jpg"
                        cv2.imwrite(temp_path, card_img)
                        info = extract_id_info(temp_path)
                        infos.append(info)
                        os.remove(temp_path)
                    for idx, info in enumerate(infos):
                        id_type_label = tk.Label(self.results_frame, text=f"Detected ID Type (Card {idx+1}): {info['ID Type']}", 
                                               font=("Arial", 14, "bold"), fg="blue")
                        id_type_label.pack(anchor=tk.W, pady=(10, 0))
                        self.results_widgets.append(id_type_label)
                        sep = ttk.Separator(self.results_frame, orient='horizontal')
                        sep.pack(fill='x', pady=10)
                        self.results_widgets.append(sep)
                        self.show_extracted_info(info['Details'])
                else:
                    info2 = None
            else:
                info1 = extract_id_info(self.uploaded_file)
                infos.append(info1)
                num_cards_detected = 1
        except Exception as e:
            infos.append({'ID Type': 'Unknown', 'Details': {'Error': str(e)}, 'Raw Text': ''})
            num_cards_detected = 0
        finally:
            for temp_img_path in temp_pdf_images:
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)

        num_cards_label = ttk.Label(self.results_frame, text=f"Number of ID cards detected: {len(infos)}", font=("Arial", 12, "bold"))
        num_cards_label.pack(anchor=tk.W, pady=(0, 10))
        self.results_widgets.append(num_cards_label)

        doc_type_verified = all(info.get('ID Type', 'Unknown') != 'Unknown' for info in infos)
        self.show_result_row("Verify the document type (e.g., identity document, driving licence, etc.)", doc_type_verified)
        all_fields_present = all(bool(info.get('Details')) for info in infos)
        self.show_result_row("Verify that all mandatory sections/fields are present in the document.", all_fields_present)
        no_blank_fields = all(all(bool(v) for v in info.get('Details', {}).values()) for info in infos)
        self.show_result_row("Check for any blank or incomplete fields that require input.", no_blank_fields)

        # Show all detected cards (for PDF or multi-card image)
        for idx, info in enumerate(infos):
            sep = ttk.Separator(self.results_frame, orient='horizontal')
            sep.pack(fill='x', pady=10)
            self.results_widgets.append(sep)
            id_type = info.get('ID Type', 'Unknown')
            id_type_label = tk.Label(self.results_frame, text=f"Detected ID Type (Card {idx+1}): {id_type}", 
                                   font=("Arial", 14, "bold"), fg="blue")
            id_type_label.pack(anchor=tk.W, pady=(10, 0))
            self.show_extracted_info(info.get('Details', {}))
            if id_type == 'Unknown':
                error_label = tk.Label(self.results_frame, text=f"Could not detect ID card type for Card {idx+1}.", font=("Arial", 11), fg="red")
                error_label.pack(anchor=tk.W, pady=(0, 10))
                self.results_widgets.append(error_label)
        sep2 = ttk.Separator(self.results_frame, orient='horizontal')
        sep2.pack(fill='x', pady=10)
        self.results_widgets.append(sep2)

        # Improved comparison: compare first two detected cards if at least two are found
        if len(infos) >= 2:
            info1, info2 = infos[0], infos[1]
            sep3 = ttk.Separator(self.results_frame, orient='horizontal')
            sep3.pack(fill='x', pady=10)
            self.results_widgets.append(sep3)
            id_type_label2 = tk.Label(self.results_frame, text=f"Comparing Card 1 and Card 2", 
                                     font=("Arial", 14, "bold"), fg="purple")
            id_type_label2.pack(anchor=tk.W, pady=(10, 0))
            self.results_widgets.append(id_type_label2)
            try:
                comparison = self.id_verifier.compare_info(info1, info2)
                name_match = comparison.get('name_match', False)
                dob_match = comparison.get('dob_match', False)
                details1 = info1.get('Details', {})
                details2 = info2.get('Details', {})
                all_keys = set(details1.keys()) | set(details2.keys())
                match_count = 0
                mismatch_count = 0
                compare_frame = ttk.Frame(self.results_frame)
                compare_frame.pack(anchor=tk.W, pady=(10, 0))
                header = ttk.Label(compare_frame, text="Field Comparison:", font=("Arial", 12, "bold"))
                header.grid(row=0, column=0, columnspan=3, sticky="w")
                ttk.Label(compare_frame, text="Field", font=("Arial", 11, "bold")).grid(row=1, column=0, sticky="w")
                ttk.Label(compare_frame, text="Card 1", font=("Arial", 11, "bold")).grid(row=1, column=1, sticky="w")
                ttk.Label(compare_frame, text="Card 2", font=("Arial", 11, "bold")).grid(row=1, column=2, sticky="w")
                for i, k in enumerate(sorted(all_keys)):
                    v1 = details1.get(k, "")
                    v2 = details2.get(k, "")
                    match = (v1 == v2 and v1 != "")
                    if match:
                        fg = "green"
                        match_count += 1
                    else:
                        fg = "red"
                        mismatch_count += 1
                    ttk.Label(compare_frame, text=k, font=("Arial", 11)).grid(row=i+2, column=0, sticky="w")
                    ttk.Label(compare_frame, text=v1, font=("Arial", 11), foreground=fg if v1 else "black").grid(row=i+2, column=1, sticky="w")
                    ttk.Label(compare_frame, text=v2, font=("Arial", 11), foreground=fg if v2 else "black").grid(row=i+2, column=2, sticky="w")
                summary = ttk.Label(compare_frame, text=f"Fields matched: {match_count}, Fields mismatched: {mismatch_count}", font=("Arial", 11, "bold"))
                summary.grid(row=len(all_keys)+2, column=0, columnspan=3, sticky="w", pady=(10,0))
                self.results_widgets.append(compare_frame)
                if name_match and dob_match:
                    result_text = "✅ Both ID cards belong to the same person!"
                    color = "green"
                elif name_match or dob_match:
                    result_text = "⚠️ Partial match: Some fields match, please review."
                    color = "orange"
                else:
                    result_text = "❌ ID cards do NOT belong to the same person!"
                    color = "red"
                compare_label = tk.Label(self.results_frame, text=result_text, font=("Arial", 14, "bold"), fg=color)
                compare_label.pack(anchor=tk.W, pady=(20, 10))
                self.results_widgets.append(compare_label)
            except Exception as e:
                error_label = tk.Label(self.results_frame, text=f"Error comparing: {str(e)}", font=("Arial", 12), fg="red")
                error_label.pack(anchor=tk.W, pady=(20, 10))
                self.results_widgets.append(error_label)
        elif len(infos) == 1:
            info = infos[0]
            info_type = info.get('ID Type', 'Unknown')
            if info_type == 'Unknown':
                error_label = tk.Label(self.results_frame, text="Could not detect a valid ID card to compare.", font=("Arial", 12), fg="red")
                error_label.pack(anchor=tk.W, pady=(20, 10))
                self.results_widgets.append(error_label)

    def show_result_row(self, text, passed):
        row = ttk.Frame(self.results_frame)
        row.pack(fill=tk.X, pady=2)
        label = ttk.Label(row, text=text, font=("Arial", 11))
        label.pack(side=tk.LEFT, anchor=tk.W)
        status = ttk.Label(row, text="✔" if passed else "✖", foreground="green" if passed else "red", font=("Arial", 14, "bold"))
        status.pack(side=tk.RIGHT)
        self.results_widgets.append(row)

    def show_extracted_info(self, details):
        if not details:
            return
        sep = ttk.Separator(self.results_frame, orient='horizontal')
        sep.pack(fill='x', pady=8)
        self.results_widgets.append(sep)
        info_title = ttk.Label(self.results_frame, text="Extracted Information:", font=("Arial", 12, "bold"))
        info_title.pack(anchor=tk.W) 
        self.results_widgets.append(info_title)
        for k, v in details.items():
            info = ttk.Label(self.results_frame, text=f"{k}: {v}", font=("Arial", 11))
            info.pack(anchor=tk.W)
            self.results_widgets.append(info)

    def clear_results(self):
        for w in self.results_widgets:
            w.destroy()
        self.results_widgets = []

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleIDCardGUI(root)
    root.mainloop()