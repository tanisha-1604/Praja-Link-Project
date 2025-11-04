from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import os
import csv
import cv2
import numpy as np
from werkzeug.utils import secure_filename

# Initialize Flask app with updated folders
app = Flask(__name__, template_folder='templates_final', static_folder='static_final')

# Folder setup
UPLOAD_FOLDER = os.path.join('static_final', 'uploads_final')
ANALYZED_FOLDER = os.path.join('static_final', 'analyzed_final')
CSV_FILE = 'reports_final.csv'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ANALYZED_FOLDER, exist_ok=True)

# Disable caching (always show new changes)
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# -----------------------
# Helper: calculate severity
# -----------------------
def calculate_severity(polygon_points, image_path):
    """Calculate coverage area percentage and return severity level."""
    img = cv2.imread(image_path)
    if img is None:
        return 0, "Error"

    height, width, _ = img.shape
    mask = np.zeros((height, width), np.uint8)
    pts = np.array(polygon_points, np.int32)
    cv2.fillPoly(mask, [pts], 255)

    coverage = (cv2.countNonZero(mask) / (height * width)) * 100

    if coverage < 5:
        severity = "Low"
    elif coverage < 15:
        severity = "Medium"
    else:
        severity = "High"

    return round(coverage, 2), severity

# -----------------------
# Routes
# -----------------------

@app.route('/')
def index():
    return render_template('index_final.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    category = request.form['category']
    file = request.files['image']

    if not file:
        return "No file uploaded", 400

    filename = secure_filename(file.filename)
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(image_path)

    return render_template('analyze_final.html', image_name=filename, category=category)

@app.route('/process_polygon', methods=['POST'])
def process_polygon():
    data = request.get_json()
    points = data.get('points', [])
    image_name = data.get('image_name')
    category = data.get('category')

    if not points or not image_name:
        return jsonify({'error': 'Missing data'}), 400

    image_path = os.path.join(UPLOAD_FOLDER, image_name)
    analyzed_path = os.path.join(ANALYZED_FOLDER, f"analyzed_{image_name}")

    # Calculate severity
    coverage, severity = calculate_severity(points, image_path)

    # Save analyzed image with polygon overlay
    img = cv2.imread(image_path)
    pts = np.array(points, np.int32)
    overlay = img.copy()
    cv2.fillPoly(overlay, [pts], (0, 0, 255))
    alpha = 0.4
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    cv2.imwrite(analyzed_path, img)

    # Save details to CSV
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Category', 'Severity', 'Image Name', 'Timestamp'])
        writer.writerow([category, severity, image_name, timestamp])

    return jsonify({'coverage': coverage, 'severity': severity})

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou_final.html')

# Run app
if __name__ == '__main__':
    app.run(debug=True)
