#!/usr/bin/env python3
"""
Generátor syntetických medicínských dat pro semestrální práci NoSQL (MongoDB).
Téma: Systém vzdáleného monitorování pacientů a telemetrie IoT biosenzorů (Telemedicína).
Reprodukovatelnost je zajištěna pevným náhodným seedem (SEED = 42).
"""

import json
import random
from datetime import datetime, timedelta

SEED = 42
random.seed(SEED)

FIRST_NAMES_M = ["Jan", "Petr", "Pavel", "Tomáš", "Martin", "Jiří", "Michal", "Josef", "František", "Karel", "Jakub", "Lukáš", "David"]
FIRST_NAMES_F = ["Marie", "Jana", "Eva", "Hana", "Anna", "Lenka", "Kateřina", "Věra", "Lucie", "Alena", "Petra", "Veronika", "Tereza"]
LAST_NAMES_M = ["Novák", "Svoboda", "Novotný", "Dvořák", "Černý", "Procházka", "Kučera", "Veselý", "Horák", "Němec", "Marek", "Pospíšil"]
LAST_NAMES_F = ["Nováková", "Svobodová", "Novotná", "Dvořáková", "Černá", "Procházková", "Kučerová", "Veselá", "Horáková", "Němcová", "Marková", "Pospíšilová"]

CITIES = ["Hradec Králové", "Pardubice", "Náchod", "Trutnov", "Jičín", "Rychnov nad Kněžnou", "Jaroměř", "Vrchlabí", "Dvůr Králové"]

DIAGNOSES = [
    ("Arteriální hypertenze II. stupně", "I10", "HIGH"),
    ("Diabetes mellitus 2. typu s komplikacemi", "E11", "HIGH"),
    ("Chronická ischemická choroba srdeční", "I25", "MEDIUM"),
    ("Fibrilace a flutter síní", "I48", "CRITICAL"),
    ("Chronické srdeční selhání", "I50", "CRITICAL"),
    ("Astma bronchiale perzistující", "J45", "MEDIUM"),
    ("Chronická obstrukční plicní nemoc", "J44", "HIGH"),
    ("Mírná hypertenze", "I10", "LOW"),
    ("Porucha glukózové tolerance", "R73", "LOW"),
]

DRUGS = [
    ("Ramipril", 5.0, "1x denně ráno"),
    ("Amlodipin", 10.0, "1x denně"),
    ("Metformin", 850.0, "2x denně po jídle"),
    ("Bisoprolol", 5.0, "1x denně ráno"),
    ("Warfarin", 3.0, "1x denně večer"),
    ("Furosemid", 40.0, "1x denně ráno"),
    ("Atorvastatin", 20.0, "1x denně večer"),
    ("Salbutamol", 0.1, "dle potřeby při dušnosti"),
]

def generate_patients(num_patients=500):
    patients = []
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, num_patients + 1):
        gender = random.choice(["M", "F"])
        if gender == "M":
            first = random.choice(FIRST_NAMES_M)
            last = random.choice(LAST_NAMES_M)
        else:
            first = random.choice(FIRST_NAMES_F)
            last = random.choice(LAST_NAMES_F)
            
        diag, code, base_risk = random.choice(DIAGNOSES)
        
        # 10% šance na posun rizika
        risk_cats = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        risk_idx = risk_cats.index(base_risk)
        if random.random() < 0.15 and risk_idx < 3:
            risk = risk_cats[risk_idx + 1]
        elif random.random() < 0.10 and risk_idx > 0:
            risk = risk_cats[risk_idx - 1]
        else:
            risk = base_risk
            
        birth_year = random.randint(1945, 1995)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        birth_date = f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}"
        
        city = random.choice(CITIES)
        phone = f"+420 {random.randint(600, 799)} {random.randint(100, 999)} {random.randint(100, 999)}"
        email = f"{first.lower()}.{last.lower()}{random.randint(1, 99)}@post.cz"
        
        reg_days = random.randint(0, 700)
        reg_date = (base_date + timedelta(days=reg_days, hours=random.randint(7, 18))).isoformat() + "Z"
        
        doctor_id = f"DOC-{random.randint(101, 115)}"
        active = random.random() > 0.08  # 92 % aktivních
        
        patient = {
            "patient_id": f"PAT-{i:04d}",
            "first_name": first,
            "last_name": last,
            "birth_date": birth_date,
            "gender": gender,
            "contact": {
                "phone": phone,
                "email": email,
                "city": city
            },
            "primary_diagnosis": diag,
            "diagnosis_code": code,
            "risk_category": risk,
            "assigned_doctor_id": doctor_id,
            "monitoring_active": active,
            "registered_at": reg_date
        }
        patients.append(patient)
        
    return patients

def generate_sensor_readings(patients, num_readings=8000):
    readings = []
    active_patients = [p for p in patients if p["monitoring_active"]]
    
    start_time = datetime(2026, 1, 1, 0, 0, 0)
    
    device_types = [
        ("WEARABLE_MONITOR", "DEV-WM-"),
        ("ECG_PATCH", "DEV-ECG-"),
        ("GLUCOMETER", "DEV-GLU-"),
        ("PULSE_OXIMETER", "DEV-OXI-")
    ]
    
    for i in range(1, num_readings + 1):
        patient = random.choice(active_patients)
        pat_id = patient["patient_id"]
        risk = patient["risk_category"]
        
        dev_type, prefix = random.choice(device_types)
        dev_id = f"{prefix}{random.randint(1000, 9999)}"
        
        # Časový offset
        day_offset = random.randint(0, 100)
        sec_offset = random.randint(0, 86400)
        reading_dt = start_time + timedelta(days=day_offset, seconds=sec_offset)
        
        # Fyziologické hodnoty závislé na diagnóze a riziku
        base_hr = 72
        base_sys = 125
        base_dia = 80
        base_spo2 = 98.0
        base_glu = 5.5
        
        if risk == "CRITICAL":
            base_hr += random.randint(15, 45)
            base_sys += random.randint(25, 55)
            base_dia += random.randint(12, 30)
            base_spo2 -= random.uniform(3.0, 7.0)
            base_glu += random.uniform(2.0, 8.0)
        elif risk == "HIGH":
            base_hr += random.randint(8, 25)
            base_sys += random.randint(15, 35)
            base_dia += random.randint(8, 20)
            base_spo2 -= random.uniform(1.0, 4.0)
            base_glu += random.uniform(1.0, 4.5)
        elif risk == "MEDIUM":
            base_hr += random.randint(0, 15)
            base_sys += random.randint(5, 20)
            base_dia += random.randint(3, 10)
            
        hr = int(max(42, min(210, random.gauss(base_hr, 12))))
        sys_bp = int(max(85, min(235, random.gauss(base_sys, 15))))
        dia_bp = int(max(50, min(140, random.gauss(base_dia, 10))))
        spo2 = round(max(85.0, min(99.9, random.gauss(base_spo2, 2.0))), 1)
        glucose = round(max(3.0, min(24.0, random.gauss(base_glu, 1.8))), 1)
        body_temp = round(max(35.5, min(40.2, random.gauss(36.6, 0.45))), 1)
        
        # Detekce a klasifikace poplachu
        alert_type = "NONE"
        alert_triggered = False
        
        if sys_bp >= 170 or dia_bp >= 110:
            alert_type = "HYPERTENSIVE_CRISIS"
            alert_triggered = True
        elif hr >= 135:
            alert_type = "TACHYCARDIA"
            alert_triggered = True
        elif hr <= 48:
            alert_type = "BRADYCARDIA"
            alert_triggered = True
        elif spo2 <= 91.0:
            alert_type = "HYPOXIA"
            alert_triggered = True
        elif glucose >= 14.0:
            alert_type = "HYPERGLYCEMIA"
            alert_triggered = True
        elif glucose <= 3.8:
            alert_type = "HYPOGLYCEMIA"
            alert_triggered = True
            
        battery = random.randint(10, 100)
        fw = random.choice(["v2.3.8", "v2.4.1", "v2.5.0", "v3.0.1"])
        
        reading = {
            "reading_id": f"READ-{i:07d}",
            "patient_id": pat_id,
            "device_id": dev_id,
            "device_type": dev_type,
            "timestamp": reading_dt.isoformat() + "Z",
            "vitals": {
                "heart_rate": hr,
                "systolic_bp": sys_bp,
                "diastolic_bp": dia_bp,
                "spo2": spo2,
                "blood_glucose": glucose,
                "body_temp": body_temp
            },
            "battery_level": battery,
            "firmware_version": fw,
            "alert_triggered": alert_triggered,
            "alert_type": alert_type
        }
        readings.append(reading)
        
    return readings

def generate_interventions(patients, readings, num_interventions=800):
    interventions = []
    alert_readings = [r for r in readings if r["alert_triggered"]]
    
    triggers = ["VITAL_ALERT", "ROUTINE_CHECK", "EMERGENCY_CALL", "MEDICATION_ADJUSTMENT"]
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    clinical_notes = {
        "HYPERTENSIVE_CRISIS": "Zaznamenána hypertenzní špička. Provedena akutní titrace antihypertenziv.",
        "TACHYCARDIA": "Epizoda supraventrikulární tachykardie. Naordinován klid na lůžku a úprava beta-blokátorů.",
        "BRADYCARDIA": "Výrazná sinusová bradykardie. Doporučeno 24h Holterovo monitorování EKG.",
        "HYPOXIA": "Desaturace kyslíku. Zahájena inhalační terapie a doporučeno plicní vyšetření.",
        "HYPERGLYCEMIA": "Dekompenzace diabetu s hyperglykemií. Úprava inzulinového režimu.",
        "HYPOGLYCEMIA": "Hypoglykemická příhoda. Pacient poučen o dietním režimu a sacharidových korekcích.",
        "ROUTINE": "Pravidelná telemedicínská kontrola. Stav pacienta stabilizován, laboratorní nálezy v normě."
    }
    
    for i in range(1, num_interventions + 1):
        if random.random() < 0.65 and alert_readings:
            # Intervence navázaná na poplach
            ref_reading = random.choice(alert_readings)
            pat_id = ref_reading["patient_id"]
            pat = next((p for p in patients if p["patient_id"] == pat_id), patients[0])
            a_type = ref_reading["alert_type"]
            trigger = "VITAL_ALERT" if random.random() < 0.75 else "EMERGENCY_CALL"
            severity = "CRITICAL" if a_type in ["HYPERTENSIVE_CRISIS", "HYPOXIA"] else "HIGH"
            notes = clinical_notes.get(a_type, clinical_notes["ROUTINE"])
            reading_dt = datetime.fromisoformat(ref_reading["timestamp"].replace("Z", ""))
            interv_dt = reading_dt + timedelta(minutes=random.randint(15, 360))
        else:
            pat = random.choice(patients)
            pat_id = pat["patient_id"]
            trigger = random.choice(["ROUTINE_CHECK", "MEDICATION_ADJUSTMENT"])
            severity = random.choice(["LOW", "MEDIUM"])
            notes = clinical_notes["ROUTINE"]
            base_dt = datetime(2026, 1, 15)
            interv_dt = base_dt + timedelta(days=random.randint(0, 90), hours=random.randint(8, 16))
            
        doc_id = pat.get("assigned_doctor_id", f"DOC-{random.randint(101, 115)}")
        drug_name, dose, freq = random.choice(DRUGS)
        hosp = True if severity == "CRITICAL" and random.random() < 0.35 else False
        follow_up = random.choice([7, 14, 21, 30, 60])
        
        intervention = {
            "intervention_id": f"INT-{i:05d}",
            "patient_id": pat_id,
            "doctor_id": doc_id,
            "timestamp": interv_dt.isoformat() + "Z",
            "trigger_type": trigger,
            "severity": severity,
            "notes": notes,
            "medication_change": {
                "prescribed_drug": drug_name,
                "dosage_mg": dose,
                "frequency": freq
            },
            "hospitalization_required": hosp,
            "follow_up_days": follow_up
        }
        interventions.append(intervention)
        
    return interventions

def main():
    print(">>> Generuji data s pevným seedem:", SEED)
    patients = generate_patients(500)
    print(f"-> Vytvořeno {len(patients)} pacientů.")
    
    sensor_readings = generate_sensor_readings(patients, 8000)
    print(f"-> Vytvořeno {len(sensor_readings)} odečtů senzorů (hlavní kolekce >= 5000).")
    
    interventions = generate_interventions(patients, sensor_readings, 800)
    print(f"-> Vytvořeno {len(interventions)} lékařských intervencí.")
    
    with open("patients.json", "w", encoding="utf-8") as f:
        json.dump(patients, f, ensure_ascii=False, indent=2)
    with open("sensor_readings.json", "w", encoding="utf-8") as f:
        json.dump(sensor_readings, f, ensure_ascii=False, indent=2)
    with open("medical_interventions.json", "w", encoding="utf-8") as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
        
    print(">>> Všechny 3 soubory úspěšně uloženy do JSON.")

if __name__ == "__main__":
    main()
