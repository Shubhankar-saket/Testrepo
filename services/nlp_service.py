import re
import requests
import pandas as pd
from deep_translator import GoogleTranslator
import openai
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from services.doctor_service import *
patient_name = None

symptoms_keywords = [
                    "pain", "fever", "headache", "cough", "fatigue", "nausea", "dizziness", 
                    "chest pain", "shortness of breath", "vomiting", "diarrhea", "chest tightness", 
                    "palpitations", "irregular heartbeat", "swelling in legs", "heartburn", 
                    "high blood pressure", "fainting"
                ]

def send_email(subject, body, to_email):
    """
    Send an email to the specified recipient with the given subject and body content.
    """
    from_email = 'kasthurisid10@gmail.com'  # Replace with your email
    from_password = 'iahv vtgo ajxo tjcn'  # Replace with your email password or app password
    
    try:
        # Set up the SMTP server and port (example is Gmail's SMTP server)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade the connection to secure
        
        # Log in to the email account
        server.login(from_email, from_password)
        
        # Create the email message
        message = MIMEMultipart()
        message['From'] = from_email
        message['To'] = to_email  # Doctor's email address
        message['Subject'] = subject
        
        # Attach the body to the email
        message.attach(MIMEText(body, 'plain'))
        
        # Send the email
        server.sendmail(from_email, to_email, message.as_string())
        
        # Close the server connection
        server.quit()
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        print(f"Error sending email: {e}")

def extract_symptoms(text):
    """
    This function will extract symptoms from the given text.
    It checks if any of the symptom keywords are in the text.
    """
    extracted_symptoms = []
    text = text.lower()  # Make the input lowercase for case-insensitive matching

    # Update the symptoms keywords list to support multiple languages if needed
    symptoms_keywords = [
        "pain", "fever", "headache", "cough", "fatigue", "nausea", "dizziness", 
        "chest pain", "shortness of breath", "vomiting", "diarrhea", "chest tightness", 
        "palpitations", "irregular heartbeat", "swelling in legs", "heartburn", 
        "high blood pressure", "fainting", "सिरदर्द"  # Add Hindi words
    ]

    # Check for symptoms based on the keywords
    for symptom in symptoms_keywords:
        if re.search(r'\b' + re.escape(symptom) + r'\b', text):  # Match whole words
            extracted_symptoms.append(symptom)

    return extracted_symptoms

import requests

def translate_text(text, target_language='en'):
    try:
        # Use deep-translator's GoogleTranslator for translation
        translated_text = GoogleTranslator(source='auto', target=target_language).translate(text)
        return translated_text
    except Exception as e:
        print(f"Error during translation: {e}")
        return text  # Return the original text if translation fails
def extract_doctor_name(message):
    """
    Extracts the doctor's name from the user input.
    Supports formats like 'Dr. Emily', 'dr. emily', etc.
    """
    try:
        message = message.strip().lower()
        # Match pattern for "Dr. <Name>" (handling partial names)
        doctor_name_match = re.search(r"\bdr\.\s*([a-zA-Z\s]+)", message.strip())
        if doctor_name_match:
            # Extract and clean name
            full_name = doctor_name_match.group(1).strip().title()
            return full_name
        return None  # Explicitly return None if no match
    except Exception as e:
        print(f"Error extracting doctor name: {e}")
        return None

def get_patient_name(message: str) -> str:
    """
    Extracts the patient's name from the message, looking for common patterns like
    "My name is [name]" or "I am [name]".
    
    Args:
    - message (str): The message from the user.
    
    Returns:
    - str: The extracted name or an empty string if no name is found.
    """
    # Define common patterns for detecting the name
    name_patterns = [
        r"my name is (\w+)",  # Matches "my name is Mayank"
        r"i am (\w+)",        # Matches "i am Mayank"
        r"call me (\w+)",     # Matches "call me Mayank"
        r"i go by (\w+)"      # Matches "i go by Mayank"
    ]
    
    # Try to match each pattern and return the first match found
    for pattern in name_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)  # Return the captured name
    
    return ""
    
def record_symptoms_and_book(message, entities):
    """
    Handles the process of recording symptoms, checking the doctor availability,
    and displaying the booking link based on the specialization.
    """

    global patient_name

    if 'symptoms' in entities:
        # Extract symptoms
        symptoms = entities.get('symptoms', [])
        
        # Translate the symptoms if needed
        translated_symptoms = translate_text(' '.join(symptoms)) if symptoms else "No symptoms provided."

        if not patient_name:
            # Prompt for the name if not available
            return 'get_name', "Can you please provide your name?"
        
        # Show the symptoms recorded
        response = f"Symptoms recorded: {translated_symptoms}"

        # Map symptoms to specialization
        symptom_specialization_map = {
            "cough": "Pulmonologist",
            "cold": "Pulmonologist",
            "fever": "General Physician",
            "nausea": "Gastroenterologist",
            "headache": "Neurologist",
            "chest pain": "Cardiologist",
            "fatigue": "General Physician",
            "dizziness": "Neurologist",
            "vomiting": "Gastroenterologist",
            "diarrhea": "Gastroenterologist",
            "shortness of breath": "Cardiologist",
            "chest tightness": "Cardiologist",
            "palpitations": "Cardiologist",
            "irregular heartbeat": "Cardiologist",
            "swelling in legs": "Cardiologist",
            "heartburn": "Cardiologist",
            "high blood pressure": "Cardiologist",
            "fainting": "Cardiologist"
        }

        # Check which specialization corresponds to the symptoms
        matched_specializations = set()
        for symptom in symptoms:
            symptom = symptom.lower()
            if symptom in symptom_specialization_map:
                matched_specializations.add(symptom_specialization_map[symptom])

        # Check if we found any matching specializations
        if matched_specializations:
            specialization = matched_specializations.pop()  # Pick the first specialization
            doctor_details = get_specialist_doctor(specialization)
            if doctor_details:
                response += f"\n\nFor {specialization}, here is the doctor available:\n{doctor_details}"
            else:
                response += f"\n\nNo doctors found for specialization: {specialization}."
        else:
            response += "\n\nNo matching specialization found for the symptoms."

        return response




def parse_user_message(message: str) -> tuple:
    """
    Parses the user message to detect the intent and extract entities like symptoms.
    
    Args:
    - message (str): The user's input message.
    
    Returns:
    - tuple: Detected intent and extracted entities (symptoms, name, etc.)
    """
    # Initialize the doctor matches as an empty dictionary
    doctor_matches = {}

    # Load doctors data (you can also refactor this part if needed)
    doctors_df = pd.read_csv('data/doctors.csv')
    doctor_names = doctors_df['name'].str.lower().tolist()

    # Define the intents and keywords
    intents = {
        'greeting': ['hi', 'hello', 'hey', 'good morning', 'good evening'],
        'check_availability': ['availability', 'available', 'doctor'],
        'book_appointment': ['book', 'appointment'],
        'reschedule': ['reschedule', 'change', 'modify'],
        'specialization_query': ['cardiologist', 'neurosurgeon', 'orthopedist', 'dermatologist', 'surgeon', 'physician', 'pediatrician'],
        'record_symptoms': [
                    "pain", "fever", "headache", "cough", "fatigue", "nausea", "dizziness", 
                    "chest pain", "shortness of breath", "vomiting", "diarrhea", "chest tightness", 
                    "palpitations", "irregular heartbeat", "swelling in legs", "heartburn", 
                    "high blood pressure", "fainting"
                ],
        'get_name': ['my name is', 'I am', 'call me', 'I go by']
    }

    # Global variable for patient name (or use a better session-based approach)
    global patient_name
    if not patient_name:
        patient_name = get_patient_name(message)

    # Initialize entities dictionary
    entities = {}
    detected_intent = None
    translated_message = translate_text(message)  # Translate the message to English

    # Log the translated message for debugging
    print(f"Translated message: {translated_message}")

    # Check for each intent and associated entities
    for intent, keywords in intents.items():
        if any(keyword in translated_message.lower() for keyword in keywords):
            detected_intent = intent

            if intent == 'specialization_query':
                # Extract specialization if it's a specialization query
                entities['specialization'] = next((keyword for keyword in keywords if keyword in translated_message.lower()), None)

    # If the intent is to check availability, extract the doctor's name if mentioned
    if detected_intent == 'check_availability':
        # Translate the message for better understanding
        doctor_name = extract_doctor_name(translated_message)
        if doctor_name:
            entities['doctor_name'] = doctor_name

    elif detected_intent == 'get_name':
        # Extract the patient's name from their message
        patient_name = get_patient_name(message)
    
        if patient_name:
            # Send the personalized greeting after capturing the name
            response = f"Hello {patient_name}, type 'book', 'availability', 'reschedule' for booking, checking availability of doctors, and rescheduling your appointment. You can also type in your symptoms if there are any."
            return 'get_name', {"response": response}  # Wrap the response in a dictionary
        else:
            return 'get_name', {"response": "I couldn't catch your name. Could you please repeat it?"}  # Wrap the response in a dictionary

    return detected_intent, entities




