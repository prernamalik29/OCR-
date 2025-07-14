from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import cv2
from PIL import Image
import re
import pytesseract
import base64
import tempfile
import traceback
from werkzeug.utils import secure_filename
import json

# Import your existing functions
from identification import extract_id_info, detect_id_card

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the file
            result = process_id_card(filepath)
            
            # Clean up the uploaded file
            os.remove(filepath)
            
            return jsonify(result)
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/compare', methods=['POST'])
def compare_cards():
    try:
        data = request.get_json()
        card1_info = data.get('card1')
        card2_info = data.get('card2')
        
        if not card1_info or not card2_info:
            return jsonify({'error': 'Both cards required for comparison'}), 400
        
        comparison_result = compare_id_info(card1_info, card2_info)
        return jsonify(comparison_result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_id_card(filepath):
    """Process an ID card image and extract information, and return checklist flags"""
    try:
        # Use your existing extract_id_info function
        result = extract_id_info(filepath)
        id_type = result.get('ID Type', 'Unknown')
        details = result.get('Details', {})
        raw_text = result.get('Raw Text', '')

        # Checklist logic
        accessible = os.path.exists(filepath)
        ext = os.path.splitext(filepath)[-1].lower()
        is_image = ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        is_pdf = ext == '.pdf'
        expected_format = is_image or is_pdf
        type_verified = id_type != 'Unknown'
        all_fields_present = bool(details)
        no_blank_fields = all(bool(v) for v in details.values()) if details else False

        checklist = {
            'uploaded': accessible,
            'expected_format': expected_format,
            'type_verified': type_verified,
            'all_fields_present': all_fields_present,
            'no_blank_fields': no_blank_fields
        }

        return {
            'success': True,
            'id_type': id_type,
            'details': details,
            'raw_text': raw_text,
            'checklist': checklist
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'id_type': 'Unknown',
            'details': {},
            'raw_text': '',
            'checklist': {
                'uploaded': False,
                'expected_format': False,
                'type_verified': False,
                'all_fields_present': False,
                'no_blank_fields': False
            }
        }

def compare_id_info(info1, info2):
    """Compare two ID card information sets"""
    comparison = {
        'name_match': False,
        'dob_match': False,
        'card_match': False,
        'total_fields': 0,
        'matching_fields': 0,
        'field_comparisons': []
    }
    
    def clean_value(value):
        if not value:
            return ""
        cleaned = ' '.join(str(value).strip().upper().split())
        cleaned = re.sub(r'[^A-Z\s\.]', '', cleaned)
        return cleaned
    
    # Compare name
    name1 = clean_value(info1.get('details', {}).get('Name'))
    name2 = clean_value(info2.get('details', {}).get('Name'))
    if name1 and name2:
        comparison['total_fields'] += 1
        comparison['name_match'] = name1 == name2
        if comparison['name_match']:
            comparison['matching_fields'] += 1
        comparison['field_comparisons'].append({
            'field': 'Name',
            'value1': name1,
            'value2': name2,
            'match': comparison['name_match']
        })
    
    # Compare date of birth
    dob1 = clean_value(info1.get('details', {}).get('Date of Birth'))
    dob2 = clean_value(info2.get('details', {}).get('Date of Birth'))
    if dob1 and dob2:
        comparison['total_fields'] += 1
        comparison['dob_match'] = dob1 == dob2
        if comparison['dob_match']:
            comparison['matching_fields'] += 1
        comparison['field_comparisons'].append({
            'field': 'Date of Birth',
            'value1': dob1,
            'value2': dob2,
            'match': comparison['dob_match']
        })
    
    # Compare all other fields
    all_keys = set(info1.get('details', {}).keys()) | set(info2.get('details', {}).keys())
    for key in all_keys:
        if key not in ['Name', 'Date of Birth']:
            value1 = clean_value(info1.get('details', {}).get(key))
            value2 = clean_value(info2.get('details', {}).get(key))
            if value1 and value2:
                comparison['total_fields'] += 1
                field_match = value1 == value2
                if field_match:
                    comparison['matching_fields'] += 1
                comparison['field_comparisons'].append({
                    'field': key,
                    'value1': value1,
                    'value2': value2,
                    'match': field_match
                })
    
    # Determine overall match
    if comparison['name_match'] and comparison['dob_match']:
        comparison['overall_result'] = 'match'
        comparison['result_text'] = '✅ Both ID cards belong to the same person!'
        comparison['result_color'] = 'green'
    elif comparison['name_match'] or comparison['dob_match']:
        comparison['overall_result'] = 'partial'
        comparison['result_text'] = '⚠️ Partial match: Some fields match, please review.'
        comparison['result_color'] = 'orange'
    else:
        comparison['overall_result'] = 'no_match'
        comparison['result_text'] = '❌ ID cards do NOT belong to the same person!'
        comparison['result_color'] = 'red'
    
    return comparison

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)