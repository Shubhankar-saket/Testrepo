from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pandas as pd
from pharmacy_services import allowed_file
from services.doctor_service import *
from services.nlp_service import *
import logging
import openai
from deep_translator import GoogleTranslator
import requests
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import os
from flask import send_from_directory

cardiologist = ["chest pain", "shortness of breath", "fatigue", "palpitations", "chest tightness", "arrhythmia"]
gastroenterologist = ["nausea", "vomiting", "diarrhea", "abdominal pain", "heartburn", "indigestion"]
neurologist = ["headache", "seizures", "numbness", "dizziness", "memory loss", "tremors"]
orthopedist = ["joint pain", "back pain", "arthritis", "fractures", "dislocations"]
dermatologist = ["rashes", "skin irritation", "acne", "eczema", "psoriasis"]
general_practitioner = ["fever", "cough", "cold", "fatigue", "sore throat", "runny nose"]

# Initialize Flask app
app = Flask(__name__)
CORS(app)

@app.route('/files/<path:filename>')
def download_file(filename):
    return send_from_directory('frontend', filename)


# Serve the frontend
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# Example API route
@app.route('/api/hello', methods=['GET'])
def api_hello():
    return {"message": "Hello from Flask!"}

@app.route('/chatbot')
def chatbot():
    return render_template('index.html')  # Ensure 'chatbot.html' exists in the templates folder

# Set your OpenAI API key (replace 'your-api-key' with your actual key)
openai.key = "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"

# Load doctor data from CSV
def load_doctors():
    return pd.read_csv('data/doctors.csv')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
SECRET_KEY = Fernet.generate_key()
cipher = Fernet(SECRET_KEY)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload-prescription', methods=['POST'])
def upload_prescription():
    """
    Endpoint to handle prescription file uploads.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        # Secure and save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Encrypt the file
        try:
            with open(filepath, 'rb') as f:
                encrypted_data = cipher.encrypt(f.read())
            with open(filepath, 'wb') as f:
                f.write(encrypted_data)

            return jsonify({'message': 'Prescription uploaded successfully', 'filename': filename}), 200
        except Exception as e:
            # Handle any encryption errors
            return jsonify({'error': f'Failed to encrypt the file: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/availability')
def availability():
    """
    Return all available doctors in a table with 'Book Appointment' buttons.
    """
    doctors = load_doctors().to_dict(orient='records')
    return render_template('availability.html', doctors=doctors)



@app.route('/specialization_availability', methods=['POST'])
def specialization_availability():
    """
    When user asks for a specific specialization, show available doctors for that specialization.
    """
    specialization = request.json.get('specialization', '').lower()
    if not specialization:
        return jsonify({"response": "Please specify a specialization (e.g., cardiologist, neurologist)."})
    
    doctors = load_doctors()
    filtered_doctors = doctors[doctors['specialization'].str.contains(specialization, case=False)]

    if not filtered_doctors.empty:
        response = f"<h2>Here are the available {specialization}s:</h2>"
        for _, row in filtered_doctors.iterrows():
            response += f"<div class='doctor-card'><h3>{row['name']}</h3><p><strong>Available:</strong> {row['availability']}</p><a href='{row['calendly_link']}' target='_blank' class='book-appointment'>Book Appointment</a></div>"
    else:
        response = f"Sorry, we don't have any {specialization}s available right now."

    return jsonify({"response": response})


def handle_appointment_request(user_input):
    doctor_name = extract_doctor_name(user_input)
    if not doctor_name:
        return "I couldn't recognize the doctor's name. Please ensure you type it correctly (e.g., 'Dr. Emily Carter')."

    doctor_details = check_doctor_availability(doctor_name)
    if doctor_details is not None:
        return (
            f"Doctor {doctor_details['name']} is available.\n"
            f"Specialization: {doctor_details['specialization']}.\n"
            f"Availability: {doctor_details['availability']}.\n"
            f"Book here: {doctor_details['calendly_link']}"
        )
    else:
        return (
            f"Sorry, no doctor named '{doctor_name}' is available. "
            "Please check the name or try searching for another doctor."
        )


def chatbot_response(user_input):
    doctor_name = extract_doctor_name(user_input)
    if doctor_name:
        
        doctor = check_doctor_availability(doctor_name)
        if doctor is not None:
            return (
                f"Doctor {doctor['name']} is available.\n"
                f"Specialization: {doctor['specialization']}.\n"
                f"Availability: {doctor['availability']}.\n"
                f"Book here: {doctor['calendly_link']}"
            )
        else:
            return f"Sorry, no doctor named '{doctor_name}' is available. Please check the spelling or try another name."
    return "Please provide the doctor's name in your request (e.g., 'Dr. Emily')."

@app.route('/', methods=['GET', 'POST'])
def translate_view():
    translated_text = None
    if request.method == 'POST':
        hindi_text = request.form.get('hindi_text')
        if hindi_text:
            try:
                translated_text = GoogleTranslator(source='auto', target='en').translate(hindi_text)
            except Exception as e:
                translated_text = f"Translation error: {e}"
    return render_template('index.html', translated_text=translated_text)

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    """
    Book an appointment for the user by selecting a doctor and time slot.
    """
    doctor_name = request.json.get('doctor_name', None)
    time_slot = request.json.get('time_slot', None)
    
    if doctor_name and time_slot:
        response = f"Booking appointment for {doctor_name} at {time_slot}."
        # Here you can integrate your calendly API or other booking systems
        # book_appointment_with_calendly(doctor_name, time_slot)
    else:
        response = "Please provide both the doctor's name and time slot."
    
    return jsonify({"response": response})

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

symptom_to_specialization = {
    "cardiologist": ["chest pain", "shortness of breath", "fatigue", "palpitations", "chest tightness", "arrhythmia"],
    "gastroenterologist": ["nausea", "vomiting", "diarrhea", "abdominal pain", "heartburn", "indigestion"],
    "neurologist": ["headache", "seizures", "numbness", "dizziness", "memory loss", "tremors"],
    "orthopedist": ["joint pain", "back pain", "arthritis", "fractures", "dislocations"],
    "dermatologist": ["rashes", "skin irritation", "acne", "eczema", "psoriasis"],
    "general practitioner": ["fever", "cough", "cold", "fatigue", "sore throat", "runny nose"]
}

session_data = {}

@app.route('/pharmacy')
def pharmacy_page():
    return render_template('pharmacy.html')

# Surescripts API Configuration
OPENFDA_API_URL = "https://api.fda.gov/drug/event.json"
OPENFDA_API_LIMIT = 5  # Number of results to fetch

@app.route('/search-drug', methods=['POST'])
def search_drug():
    """
    Search for drug information using OpenFDA API.
    """
    data = request.json
    drug_name = data.get('drug_name', '').strip()

    # Validate input
    if not drug_name:
        return jsonify({'error': 'Drug name is required'}), 400

    # Build the OpenFDA API query
    params = {
        'search': f'patient.drug.medicinalproduct:"{drug_name}"',
        'limit': OPENFDA_API_LIMIT
    }

    try:
        logging.info(f"Searching for drug: {drug_name} with params: {params}")
        response = requests.get(OPENFDA_API_URL, params=params)

        if response.status_code == 200:
            data = response.json()

            # Log the structure of the response to help debug the issue
            logging.info(f"OpenFDA Response: {data}")

            # Check if 'results' key exists and if it contains data
            results = data.get('results', [])
            if not results:
                return jsonify({'message': 'No results found'}), 404

            # Filter results to only include the requested drug (case-insensitive)
            filtered_results = []
            for result in results:
                try:
                    # Access the nested fields
                    drug_product = result['patient']['drug'][0]['medicinalproduct']
                    if drug_name.lower() in drug_product.lower():
                        filtered_results.append(result)
                except (KeyError, IndexError) as e:
                    # Handle cases where the expected structure is not found
                    logging.warning(f"Skipping result due to missing or malformed data: {e}")

            if not filtered_results:
                return jsonify({'message': f'No results found for {drug_name}'}), 404

            return jsonify({'results': filtered_results})

        logging.error(f"Failed to fetch data from OpenFDA. Status code: {response.status_code}")
        return jsonify({'error': 'Failed to fetch data from OpenFDA'}), response.status_code

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    


@app.route('/chat', methods=['POST'])
def chat():
    
    try:
        user_message = request.json.get("message", "").strip()
        session_id = request.json.get('session_id', '').strip()
        if not user_message:
            return jsonify({"response": "Please enter a valid message."})

        # Example of translation in the chat logic
        translated_message = GoogleTranslator(source='auto', target='en').translate(user_message)
        response = f"Translated message: {translated_message}"

    except Exception as e:
        logging.error(f"Error: {e}")
        response = "An error occurred while processing your request. Please try again later."

    
    try:
        user_message = request.json.get("message", "").strip()
        session_id = request.json.get('session_id', '').strip()
        if not user_message:
            return jsonify({"response": "Please enter a valid message."})
        
        patient_name = session_data.get(session_id, {}).get('patient_name', None)

        # Parse user message
        intent, entities = parse_user_message(user_message)
        logging.debug(f"Intent: {intent}, Entities: {entities}")
        doctor_name = entities.get('doctor_name')

        if intent == 'get_name':
            # Store the patient's name in the session and confirm
            patient_name = user_message.strip()
            patient_name = get_patient_name(user_message)
            if session_id not in session_data:
                session_data[session_id] = {}
            session_data[session_id]['patient_name'] = patient_name

            return jsonify({"response": f"Hi {patient_name}, type 'book', 'availability', or 'reschedule' to manage appointments, or select 'Urgent Care' or 'AI Translation' to share your symptoms."})

        # Handle different intents
        elif intent == 'record_symptoms':
        # Extract doctor name and symptoms from the message
            message = entities.get('symptoms', '')
            doctor_name = extract_doctor_name(message)  # Extract doctor's name if present
            symptoms = message if not doctor_name else message.replace(doctor_name, '').strip()

            if isinstance(symptoms, list):
                symptoms = ", ".join(symptoms)
        # Translate the symptoms if needed
            translated_symptoms = translate_text(symptoms) if symptoms else "No symptoms provided."

        # Record the symptoms (for now, just show the response)
            response = f"Symptoms recorded: {translated_symptoms}"

            if translated_symptoms.lower() in cardiologist:  # Cardiologist-related symptoms
                specialization = "Cardiologist"
            elif translated_symptoms.lower() in orthopedist:  
                specialization = "Orthopedist"
            elif translated_symptoms.lower() in neurologist:  # Neurologist-related symptoms
                specialization = "Neurosurgeon"
            else:
                specialization = "General Practitioner"  # Default specialization

            # Now, find the doctors with the correct specialization
            doctors = load_doctors()  # This should be a function that loads doctor data
            filtered_doctors = doctors[doctors['specialization'].str.contains(specialization, case=False)]

            if not filtered_doctors.empty:
                response += f"\nDoctors available for {specialization}:"
                for _, row in filtered_doctors.iterrows():
                    # Generate HTML card for each doctor
                    response += f"""
                    <div class="doctor-card" style="border: 1px solid #ddd; padding: 15px; margin: 10px;">
                        <h3>{row['name']}</h3>
                        <p><strong>Specialization:</strong> {row['specialization']}</p>
                        <p><strong>Availability:</strong> {row['availability']}</p>
                        <a href="{row['calendly_link']}" target="_blank" class="btn btn-primary">Book Appointment</a>
                    </div>
                    """
            else:
                response += f"\nSorry, no {specialization} available at the moment."

            # If no doctor name is provided, just return the symptom message
        elif intent == 'greeting':
            response = "Hello! Welcome to DocEase. Whats your name?"

        elif intent == 'check_availability':
            doctor_name = entities.get('doctor_name', None)  # Extract the doctor name from the user's input
            specialization = entities.get('specialization', None)  # Extract the specialization if mentioned
            doctors = load_doctors()  # Load the list of available doctors

            if doctor_name:
                # Filter for the specific doctor's data
                doctor_data = doctors[doctors['name'].str.lower().str.contains(doctor_name.lower(), na=False)]
                if not doctor_data.empty:
                    # Display details for the specified doctor
                    doctor = doctor_data.iloc[0]
                    response = (
                        f"<div class='card' style='width: 18rem; margin: 10px;'>"
                        f"  <div class='card-body'>"
                        f"    <h5 class='card-title'>{doctor['name']}</h5>"
                        f"    <h6 class='card-subtitle mb-2 text-muted'>{doctor['specialization']}</h6>"
                        f"    <p class='card-text'><strong>Availability:</strong> {doctor['availability']}</p>"
                        f"    <a href='{doctor['calendly_link']}' target='_blank' class='btn btn-primary'>Book Appointment</a>"
                        f"  </div>"
                        f"</div>"
                    )
                else:
                    # Handle case where the doctor is not found
                    response = (
                        f"Sorry, {doctor_name} is not available or does not exist in our records. "
                        "Please try searching for another doctor."
                    )
            
            elif specialization:
                # If a specialization is mentioned, filter doctors by that specialization
                filtered_doctors = doctors[doctors['specialization'].str.contains(specialization, case=False, na=False)]
                if not filtered_doctors.empty:
                    response = f"<h2>Here are the available {specialization}s:</h2>"
                    for _, row in filtered_doctors.iterrows():
                        response += f"<div class='doctor-card'><h3>{row['name']}</h3><p><strong>Available:</strong> {row['availability']}</p><a href='{row['calendly_link']}' target='_blank' class='book-appointment'>Book Appointment</a></div>"
                else:
                    response = f"Sorry, we don't have any {specialization}s available right now."
            
            else:
                # If neither doctor name nor specialization is provided, show all available doctors
                response = "<h2>Available Doctors</h2><table class='table table-bordered table-hover'>"
                response += "<thead class='thead-dark'><tr><th>Name</th><th>Specialization</th><th>Availability</th><th>Action</th></tr></thead><tbody>"

                for _, doctor in doctors.iterrows():
                    response += (
                        f"<tr>"
                        f"<td>{doctor['name']}</td>"
                        f"<td>{doctor['specialization']}</td>"
                        f"<td>{doctor['availability']}</td>"
                        f"<td><a href='{doctor['calendly_link']}' target='_blank' class='btn btn-success'>Book Appointment</a></td>"
                        f"</tr>"
                    )
                response += "</tbody></table>"

        elif intent == 'book_appointment':
            doctors = load_doctors()  # Load all doctor data
            response = (
                "<h4>Sure! I'll provide you the list of available doctors. From there, you can book the appointment easily.</h4>"
            )
            response += "<br>"
            response += "<h2>Book Appointment</h2><table class='table table-bordered table-hover'>"
            response += "<thead class='thead-dark'><tr><th>Name</th><th>Specialization</th><th>Availability</th><th>Action</th></tr></thead><tbody>"

            # Generate table rows for each doctor
            for _, doctor in doctors.iterrows():
                response += (
                    f"<tr>"
                    f"<td>{doctor['name']}</td>"
                    f"<td>{doctor['specialization']}</td>"
                    f"<td>{doctor['availability']}</td>"
                    f"<td><a href='{doctor['calendly_link']}' target='_blank' class='btn btn-success'>Book Appointment</a></td>"
                    f"</tr>"
                )
            response += "</tbody></table>"


         # Handle specialization queries (e.g., "I want a cardiologist")
        elif intent == 'specialization_query':
            specialization = entities.get('specialization', None)
            if specialization:
                doctors = load_doctors()
                filtered_doctors = doctors[doctors['specialization'].str.contains(specialization, case=False)]
                
                if not filtered_doctors.empty:
                    response = f"<h2>Here are the available {specialization}s:</h2>"
                    for _, row in filtered_doctors.iterrows():
                        response += f"<div class='doctor-card'><h3>{row['name']}</h3><p><strong>Available:</strong> {row['availability']}</p><a href='{row['calendly_link']}' target='_blank' class='book-appointment'>Book Appointment</a></div>"
                else:
                    response = f"Sorry, we don't have any {specialization}s available right now."
            else:
                response = "Please specify the specialization you're looking for (e.g., cardiologist, neurosurgeon, orthopedist)."

        elif intent == 'reschedule':
            doctors = load_doctors()  # Load all doctor data
            response = (
                "<h4>Sure! I'll provide you the list of available doctors. From there, you can Reschedule the appointment easily.</h4>"
            )
            response += "<br>"
            response += "<h2>Reschedule Appointment</h2><table class='table table-bordered table-hover'>"
            response += "<thead class='thead-dark'><tr><th>Name</th><th>Specialization</th><th>Availability</th><th>Action</th></tr></thead><tbody>"

            # Generate table rows for each doctor
            for _, doctor in doctors.iterrows():
                response += (
                    f"<tr>"
                    f"<td>{doctor['name']}</td>"
                    f"<td>{doctor['specialization']}</td>"
                    f"<td>{doctor['availability']}</td>"
                    f"<td><a href='{doctor['reschedule_link']}' target='_blank' class='btn btn-success'>Reschedule Appointment</a></td>"
                    f"</tr>"
                )
            response += "</tbody></table>"

        else:
            response = "I'm sorry, I couldn't understand your request. Please try again."

    except Exception as e:
        logging.error(f"Error: {e}")
        response = "An error occurred while processing your request. Please try again later."

    return jsonify({"response": response})


PHARMACY_SERVICE_URL = "http://localhost:5001"

@app.route('/pharmacy/upload-prescription', methods=['POST'])
def proxy_upload_prescription():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    response = requests.post(f"{PHARMACY_SERVICE_URL}/upload-prescription", files={'file': file})
    return jsonify(response.json())



@app.route('/pharmacy/recommend-medicine', methods=['POST'])
def recommend_medicine():
    data = request.json
    logging.debug(f"Received data: {data}")  # Log incoming data
    prescription_details = data.get('prescription_details', '')

    if not prescription_details:
        return jsonify({'error': 'Prescription details are required'}), 400

    # Simulate fetching recommendations based on prescription
    mock_data = {
    "fever": [
        {'medicine': 'Paracetamol', 'alternative': 'Ibuprofen', 'availability': 'In stock', 'Price': "45"},
        {'medicine': 'Aspirin', 'alternative': 'Acetaminophen', 'availability': 'In stock', 'Price' : "70"}
    ],
    "infection": [
        {'medicine': 'Amoxicillin', 'alternative': 'Cephalexin', 'availability': 'Limited stock'},
        {'medicine': 'Azithromycin', 'alternative': 'Clarithromycin', 'availability': 'In stock'}
    ],
    "pain": [
        {'medicine': 'Aspirin', 'alternative': 'Naproxen', 'availability': 'In stock'},
        {'medicine': 'Ibuprofen', 'alternative': 'Diclofenac', 'availability': 'In stock'}
    ],
    "headache": [
        {'medicine': 'Ibuprofen', 'alternative': 'Acetaminophen', 'availability': 'In stock'},
        {'medicine': 'Excedrin', 'alternative': 'Advil', 'availability': 'In stock'}
    ],
    "nausea": [
        {'medicine': 'Ondansetron', 'alternative': 'Promethazine', 'availability': 'In stock'},
        {'medicine': 'Dramamine', 'alternative': 'Meclizine', 'availability': 'In stock'}
    ],
    "cold": [
        {'medicine': 'Diphenhydramine', 'alternative': 'Loratadine', 'availability': 'In stock'},
        {'medicine': 'Pseudoephedrine', 'alternative': 'Phenylephrine', 'availability': 'Limited stock'}
    ],
    "cough": [
        {'medicine': 'Dextromethorphan', 'alternative': 'Guaifenesin', 'availability': 'Limited stock'},
        {'medicine': 'Codeine', 'alternative': 'Bromhexine', 'availability': 'In stock'}
    ],
    "allergy": [
        {'medicine': 'Cetirizine', 'alternative': 'Loratadine', 'availability': 'In stock'},
        {'medicine': 'Diphenhydramine', 'alternative': 'Fexofenadine', 'availability': 'In stock'}
    ],
    "insomnia": [
        {'medicine': 'Melatonin', 'alternative': 'Zolpidem', 'availability': 'In stock'},
        {'medicine': 'Trazodone', 'alternative': 'Lorazepam', 'availability': 'Limited stock'}
    ],
    "arthritis": [
        {'medicine': 'Methotrexate', 'alternative': 'Sulfasalazine', 'availability': 'In stock'},
        {'medicine': 'Ibuprofen', 'alternative': 'Naproxen', 'availability': 'In stock'}
    ],
    "anxiety": [
        {'medicine': 'Alprazolam', 'alternative': 'Diazepam', 'availability': 'In stock'},
        {'medicine': 'Lorazepam', 'alternative': 'Clonazepam', 'availability': 'Limited stock'}
    ],
    "diabetes": [
        {'medicine': 'Metformin', 'alternative': 'Glibenclamide', 'availability': 'In stock'},
        {'medicine': 'Insulin', 'alternative': 'Gliclazide', 'availability': 'Limited stock'}
    ],
    "hypertension": [
        {'medicine': 'Amlodipine', 'alternative': 'Losartan', 'availability': 'In stock'},
        {'medicine': 'Lisinopril', 'alternative': 'Enalapril', 'availability': 'In stock'}
    ],
    "depression": [
        {'medicine': 'Fluoxetine', 'alternative': 'Sertraline', 'availability': 'In stock'},
        {'medicine': 'Citalopram', 'alternative': 'Paroxetine', 'availability': 'Limited stock'}
    ],
    "asthma": [
        {'medicine': 'Albuterol', 'alternative': 'Salbutamol', 'availability': 'In stock'},
        {'medicine': 'Fluticasone', 'alternative': 'Budesonide', 'availability': 'In stock'}
    ],
    "eczema": [
        {'medicine': 'Hydrocortisone', 'alternative': 'Betamethasone', 'availability': 'In stock'},
        {'medicine': 'Triamcinolone', 'alternative': 'Mometasone', 'availability': 'In stock'}
    ]
}


    recommendations = []
    for condition, meds in mock_data.items():
        if condition in prescription_details.lower():
            recommendations.extend(meds)

    if not recommendations:
        return jsonify({'recommendations': []}), 200

    return jsonify({'recommendations': recommendations}), 200

@app.route('/translate-text', methods=['POST'])
def translate_text():
    data = request.json
    name = data.get('name', 'Anonymous')  # Default to 'Anonymous' if no name provided
    age = data.get('age', 'Unknown')  # Default to 'Unknown' if no age provided
    text = data.get('text', '')
    recipient_email = data.get('email', 'target-email@example.com')  # Default email

    if not text:
        return jsonify({'error': 'Text is required for translation'}), 400

    try:
        # Translate text
        translated_text = GoogleTranslator(source='auto', target='en').translate(text)

        # Email content includes name and age
        email_content = (
            f"Patient : {name}, "  " \n\n"

            f"Translated Prescription :  \n\n{translated_text}, "   "\n\n"

            f"Patient details :\nName: {name} ,\nAge: {age}"
        )

        # Send email
        send_email_with_mailgun(email_content, recipient_email)

        return jsonify({'translated_text': translated_text, 'message': 'Translated text sent to email successfully!'}), 200
    except Exception as e:
        return jsonify({'error': f"Translation or email sending failed: {str(e)}"}), 500



        # Send email
MAILGUN_API_KEY = '2801924d8ff68c9243844464404800d4-7113c52e-61dcb560'  # Replace with your Mailgun API key
MAILGUN_DOMAIN = 'sandboxb528cd79ed724bd5a9975023e1b728d0.mailgun.org'  # Replace with your Mailgun domain

def send_email_with_mailgun(content, recipient_email):
    url = f'https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages'
    
    data = {
        'from': 'DocEase AI Translator <shubhankarsaket@gmail.com>',  # Replace with your email
        'to': recipient_email,
        'subject': 'AI Translated Text with Details',
        'html': content  # The content of the email
    }

    response = requests.post(
        url,
        auth=('api', MAILGUN_API_KEY),  # Use your Mailgun API Key for authentication
        data=data
    )

    if response.status_code == 200:
        print('Email sent successfully!')
    else:
        print(f"Failed to send email. Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        
# Doctor data (mocked)
doctors = [
    {"name": "Dr. Emily Carter", "specialty": "Cardiologist"},
    {"name": "Dr. John Smith", "specialty": "General Practitioner"},
    {"name": "Dr. Sarah Brown", "specialty": "Neurologist"},
]


urgent_cases = []

def assign_doctor(symptoms):
    """
    Assign a doctor based on symptoms using a mapping.
    If no match is found, return a default general practitioner.
    """
    doctor_mapping = {
        "breathlessness": "Dr. Emily Carter",
        "chest pain": "Dr. John Smith",
        "seizures": "Dr. Sarah Brown",
        # Add more mappings as necessary...
    }

    for keyword, doctor in doctor_mapping.items():
        if keyword in symptoms.lower():
            return doctor
    return "General Practitioner"

calendly_link = "https://calendly.com/shubhankarsaket/doc-meeting"

def add_calendly_link(case):
   
    if case["urgency"] == "Critical":
        case["Urgent meeting"] = calendly_link
        print(f"Added Calendly link to critical case: {case}")
    else:
        print(f"No Calendly link added for non-critical case: {case}")
    return case

# Sample Calendly link for scheduling meetings
@app.route("/api/report-case", methods=["POST"])
def report_case():
    data = request.json
    name = data.get("name", "Unknown")
    age = data.get("age", "Unknown")
    symptoms = data.get("symptoms", "")

    if not symptoms:
        return jsonify({"error": "Symptoms are required"}), 400

    # Determine urgency
    critical_keywords = [
        "chest pain", "seizures", "heart attack", 
        "accident", "unconsciousness", "breathlessness"
    ]
    urgency = (
        "Critical"
        if any(keyword in symptoms.lower() for keyword in critical_keywords)
        else "Non-Urgent"
    )

    # Assign a doctor
    assigned_doctor = assign_doctor(symptoms)

    # Create the case
    case = {
        "name": name,
        "age": age,
        "symptoms": symptoms,
        "urgency": urgency,
        "doctor": assigned_doctor,
    }
    case = add_calendly_link(case)

    # Store the case
    urgent_cases.append(case)

    # Include the Calendly link in the response
    return jsonify({
        "message": "Case reported successfully",
        "case": case  # This will now include 'Urgent meeting' if applicable
    }), 201

@app.route("/api/urgent-cases", methods=["GET"])
def get_urgent_cases():
    return jsonify(urgent_cases), 200


if __name__ == '__main__':
    app.run(debug=True)