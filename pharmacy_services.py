import logging
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os
from flask_cors import CORS

pharmacy_app = Flask(__name__)
CORS(pharmacy_app, origins=["http://127.0.0.1:5500"])

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
SECRET_KEY = Fernet.generate_key()
cipher = Fernet(SECRET_KEY)

# Initialize Flask app
pharmacy_app = Flask(__name__)
pharmacy_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@pharmacy_app.route('/upload-prescription', methods=['POST'])
def upload_prescription():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(pharmacy_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Encrypt the file
        with open(filepath, 'rb') as f:
            encrypted_data = cipher.encrypt(f.read())
        with open(filepath, 'wb') as f:
            f.write(encrypted_data)

        return jsonify({'message': 'Prescription uploaded successfully', 'filename': filename}), 200
    return jsonify({'error': 'Invalid file type'}), 400

@pharmacy_app.route('/recommend-medicine', methods=['POST'])
def recommend_medicine():
    data = request.json
    logging.debug(f"Received data: {data}")  # Log incoming data
    prescription_details = data.get('prescription_details', '')

    if not prescription_details:
        return jsonify({'error': 'Prescription details are required'}), 400

    # Simulate fetching recommendations based on prescription
    mock_data = {
        "fever": [
            {'medicine': 'Paracetamol', 'alternative': 'Ibuprofen', 'availability': 'In stock'}
        ],
        "infection": [
            {'medicine': 'Amoxicillin', 'alternative': 'Cephalexin', 'availability': 'Limited stock'}
        ],
        "pain": [
            {'medicine': 'Aspirin', 'alternative': 'Naproxen', 'availability': 'In stock'}
        ]
    }

    recommendations = []
    for condition, meds in mock_data.items():
        if condition in prescription_details.lower():
            recommendations.extend(meds)

    if not recommendations:
        return jsonify({'recommendations': []}), 200

    return jsonify({'recommendations': recommendations}), 200
@pharmacy_app.route('/recommend-medicine-by-symptoms', methods=['POST'])
def recommend_medicine_by_symptoms():
    """
    Recommend medicines based on symptoms provided by the user.
    """
    data = request.json
    symptoms = data.get('symptoms', '')

    if not symptoms:
        return jsonify({'error': 'Symptoms are required'}), 400

    # Mock data for symptom-based recommendations
    symptom_to_medicine = {
        "fever": [
            {'medicine': 'Paracetamol', 'alternative': 'Ibuprofen', 'availability': 'In stock'}
        ],
        "headache": [
            {'medicine': 'Aspirin', 'alternative': 'Acetaminophen', 'availability': 'In stock'}
        ],
        "nausea": [
            {'medicine': 'Ondansetron', 'alternative': 'Promethazine', 'availability': 'In stock'}
        ],
        "cough": [
            {'medicine': 'Dextromethorphan', 'alternative': 'Guaifenesin', 'availability': 'Limited stock'}
        ],
        "pain": [
            {'medicine': 'Ibuprofen', 'alternative': 'Naproxen', 'availability': 'In stock'}
        ]
    }

    recommendations = []
    for symptom, meds in symptom_to_medicine.items():
        if symptom in symptoms.lower():
            recommendations.extend(meds)

    if not recommendations:
        return jsonify({'recommendations': []}), 200

    return jsonify({'recommendations': recommendations}), 200

if __name__ == '__main__':
    pharmacy_app.run(port=5001, debug=True)
    print(pharmacy_app.url_map)

