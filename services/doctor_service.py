import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

symptom_specialization_map = {
    "cough": "Pulmonologist",
    "cold": "Pulmonologist",
    "fever": "General Physician",
    "nausea": "Gastroenterologist",
    "headache": "Neurosurgeon",
    "chest pain": "Cardiologist",
    "fatigue": "General Physician",
    "dizziness": "Neurologist",
    "vomiting": "Gastroenterologist",
    "diarrhea": "Gastroenterologist",
    "shortness of breath": "Cardiologist",
    "chest tightness": "Cardiologist",  # New addition for Cardiologist
    "palpitations": "Cardiologist",     # New addition for Cardiologist
    "irregular heartbeat": "Cardiologist",  # New addition for Cardiologist
    "swelling in legs": "Cardiologist",  # New addition for Cardiologist
    "heartburn": "Cardiologist",        # New addition for Cardiologist
    "high blood pressure": "Cardiologist",  # New addition for Cardiologist
    "fainting": "Cardiologist"          # New addition for Cardiologist
}

def get_doctors_for_multiple_symptoms(symptoms):
    """
    Fetch doctors available for the provided symptoms.
    """
    doctor_matches = {}

    # Load doctors data
    df = pd.read_csv('data/doctors.csv')

    for symptom in symptoms:
        specialization = symptom_specialization_map.get(symptom.lower())
        
        if specialization:
            # Find doctors matching the specialization
            doctors_in_specialization = df[df['specialization'].str.contains(specialization, case=False, na=False)]
            
            if specialization not in doctor_matches:
                doctor_matches[specialization] = []
            
            # Add doctors to the match list for that specialization
            doctor_matches[specialization].extend(doctors_in_specialization.to_dict(orient='records'))

    return doctor_matches



def get_specialist_doctor(specialization):
    # Load doctor data from CSV
    df = pd.read_csv('data/doctors.csv')
    
    # Find doctors with the specified specialization (case insensitive)
    doctors = df[df['Specialization'].str.contains(specialization, case=False)]
    
    # If no doctors are found, return a message
    if doctors.empty:
        return f"No doctor found for specialization: {specialization}"
    
    # Build the response with doctors' information
    response = "Here are the doctors available:\n"
    for _, row in doctors.iterrows():
        response += f"""
        Name: {row['Name']}
        Specialization: {row['Specialization']}
        Location: {row['Location']}
        Contact: {row['Contact']}
        Available: {row['Available Days']} at {row['Available Time']}
        """
    return response

def check_doctor_availability(doctor_name, data_source='data/doctors.csv'):
    try:
        df = pd.read_csv(data_source)
        doctor_name = doctor_name.strip().lower()

        # Match doctor names
        doctor_row = df[df['name'].str.lower().str.contains(doctor_name, na=False)]
        if not doctor_row.empty:
            return doctor_row.iloc[0].to_dict()  # Return first match as a dictionary
    except Exception as e:
        print(f"Error reading doctor data: {e}")
    return None



def get_doctor_details_by_name(doctor_name, data_source='data/doctors.csv'):
    # Load doctor data
    df = pd.read_csv(data_source)
    doctor_name = doctor_name.lower().strip()  
    doctor = df[df['Name'].str.lower().str.contains(doctor_name)]
    # Return the doctor details if found
    if not doctor.empty:
        return doctor
    return None

def get_doctor_details_by_specialization(specialization, data_source='data/doctors.csv'):
    """
    Fetch doctor details by specialization from the data source.
    """
    df = pd.read_csv(data_source)
    doctor = df[df['Specialization'].str.contains(specialization, case=False, na=False)]
    return doctor if not doctor.empty else None

def get_reschedule_details(data_source='data/doctors.csv'):
    """
    Get a list of doctors available for rescheduling, if they have a reschedule link.
    """
    df = pd.read_csv(data_source)
    reschedule_doctors = df[df['reschedule_link'].notnull()]  # Filter doctors who have a reschedule link
    return reschedule_doctors

