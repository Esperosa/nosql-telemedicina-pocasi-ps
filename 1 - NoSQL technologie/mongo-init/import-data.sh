#!/usr/bin/env bash
set -euo pipefail

ROOT_USER="${MONGO_ROOT_USER:-admin}"
ROOT_PASS="${MONGO_ROOT_PASSWORD:-ClusterSuperSecretAdminPassword2026!}"
DB_NAME="${MONGO_DB_NAME:-telemedicina}"
DATA_DIR="/import-data"

echo ">>> [data-import] Čekání na mongos1 s autentizací..."
for i in {1..30}; do
  if mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; then
    echo ">>> [data-import] mongos1 je připraven (pokus $i)."
    break
  fi
  sleep 2
done

echo ">>> [data-import] Konfigurace schémat, indexů, shard key a validace \$jsonSchema..."
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "
  const db = db.getSiblingDB('${DB_NAME}');

  // 1. Kolekce patients s validací
  if (!db.getCollectionNames().includes('patients')) {
    db.createCollection('patients', {
      validator: {
        \$jsonSchema: {
          bsonType: 'object',
          required: ['patient_id', 'first_name', 'last_name', 'birth_date', 'gender', 'primary_diagnosis', 'diagnosis_code', 'risk_category', 'monitoring_active'],
          properties: {
            patient_id: { bsonType: 'string', pattern: '^PAT-[0-9]{4}\$' },
            first_name: { bsonType: 'string', minLength: 1 },
            last_name: { bsonType: 'string', minLength: 1 },
            birth_date: { bsonType: 'string', pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}\$' },
            gender: { enum: ['M', 'F', 'OTHER'] },
            contact: {
              bsonType: 'object',
              required: ['city'],
              properties: {
                phone: { bsonType: 'string' },
                email: { bsonType: 'string' },
                city: { bsonType: 'string' }
              }
            },
            primary_diagnosis: { bsonType: 'string' },
            diagnosis_code: { bsonType: 'string' },
            risk_category: { enum: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] },
            assigned_doctor_id: { bsonType: 'string' },
            monitoring_active: { bsonType: 'bool' },
            registered_at: { bsonType: 'string' }
          }
        }
      },
      validationLevel: 'strict',
      validationAction: 'error'
    });
    print('Kolekce patients vytvořena se schématem.');
  }

  // 2. Kolekce sensor_readings s validací
  if (!db.getCollectionNames().includes('sensor_readings')) {
    db.createCollection('sensor_readings', {
      validator: {
        \$jsonSchema: {
          bsonType: 'object',
          required: ['reading_id', 'patient_id', 'device_id', 'device_type', 'timestamp', 'vitals', 'alert_triggered', 'alert_type'],
          properties: {
            reading_id: { bsonType: 'string', pattern: '^READ-[0-9]{7}\$' },
            patient_id: { bsonType: 'string', pattern: '^PAT-[0-9]{4}\$' },
            device_id: { bsonType: 'string' },
            device_type: { enum: ['WEARABLE_MONITOR', 'ECG_PATCH', 'GLUCOMETER', 'PULSE_OXIMETER'] },
            timestamp: { bsonType: 'string' },
            vitals: {
              bsonType: 'object',
              required: ['heart_rate', 'systolic_bp', 'diastolic_bp', 'spo2'],
              properties: {
                heart_rate: { bsonType: ['int', 'long', 'double'], minimum: 30, maximum: 240 },
                systolic_bp: { bsonType: ['int', 'long', 'double'], minimum: 50, maximum: 260 },
                diastolic_bp: { bsonType: ['int', 'long', 'double'], minimum: 30, maximum: 160 },
                spo2: { bsonType: ['double', 'int'], minimum: 50.0, maximum: 100.0 },
                blood_glucose: { bsonType: ['double', 'int'], minimum: 1.0, maximum: 35.0 },
                body_temp: { bsonType: ['double', 'int'], minimum: 32.0, maximum: 43.0 }
              }
            },
            battery_level: { bsonType: ['int', 'long', 'double'], minimum: 0, maximum: 100 },
            firmware_version: { bsonType: 'string' },
            alert_triggered: { bsonType: 'bool' },
            alert_type: { enum: ['NONE', 'TACHYCARDIA', 'BRADYCARDIA', 'HYPERTENSIVE_CRISIS', 'HYPOXIA', 'HYPERGLYCEMIA', 'HYPOGLYCEMIA'] }
          }
        }
      },
      validationLevel: 'strict',
      validationAction: 'error'
    });
    print('Kolekce sensor_readings vytvořena se schématem.');
  }

  // 3. Kolekce medical_interventions s validací
  if (!db.getCollectionNames().includes('medical_interventions')) {
    db.createCollection('medical_interventions', {
      validator: {
        \$jsonSchema: {
          bsonType: 'object',
          required: ['intervention_id', 'patient_id', 'doctor_id', 'timestamp', 'trigger_type', 'severity', 'notes'],
          properties: {
            intervention_id: { bsonType: 'string', pattern: '^INT-[0-9]{5}\$' },
            patient_id: { bsonType: 'string', pattern: '^PAT-[0-9]{4}\$' },
            doctor_id: { bsonType: 'string' },
            timestamp: { bsonType: 'string' },
            trigger_type: { enum: ['VITAL_ALERT', 'ROUTINE_CHECK', 'EMERGENCY_CALL', 'MEDICATION_ADJUSTMENT'] },
            severity: { enum: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] },
            notes: { bsonType: 'string', minLength: 5 },
            medication_change: {
              bsonType: 'object',
              properties: {
                prescribed_drug: { bsonType: 'string' },
                dosage_mg: { bsonType: ['double', 'int'] },
                frequency: { bsonType: 'string' }
              }
            },
            hospitalization_required: { bsonType: 'bool' },
            follow_up_days: { bsonType: ['int', 'long', 'double'], minimum: 1, maximum: 365 }
          }
        }
      },
      validationLevel: 'strict',
      validationAction: 'error'
    });
    print('Kolekce medical_interventions vytvořena se schématem.');
  }

  // Indexy
  db.patients.createIndex({ patient_id: 1 }, { unique: true });
  db.patients.createIndex({ risk_category: 1 });
  db.patients.createIndex({ assigned_doctor_id: 1 });

  // reading_id NENÍ unikátní index v DB (jen běžný index pro vyhledávání):
  // shard key je { patient_id: "hashed" } a MongoDB nedovolí unikátní index,
  // který nemá shard key jako prefix (uniqueness by přes shardy nešla
  // zaručit). Unikátnost reading_id garantuje už generátor dat při vzniku.
  db.sensor_readings.createIndex({ reading_id: 1 });
  db.sensor_readings.createIndex({ patient_id: 1, timestamp: -1 });
  db.sensor_readings.createIndex({ alert_triggered: 1, alert_type: 1 });
  db.sensor_readings.createIndex({ timestamp: 1 });

  db.medical_interventions.createIndex({ intervention_id: 1 }, { unique: true });
  db.medical_interventions.createIndex({ patient_id: 1, timestamp: -1 });
  db.medical_interventions.createIndex({ severity: 1 });

  // Sharding hlavní kolekce podle hashovaného shard key { patient_id: 'hashed' }
  try {
    sh.shardCollection('${DB_NAME}.sensor_readings', { patient_id: 'hashed' });
    print('Kolekce sensor_readings byla úspěšně shardována (shard key: { patient_id: \"hashed\" }).');
  } catch(e) {
    print('shardCollection info: ' + e.message);
  }
"

echo ">>> [data-import] Kontrola a import datových souborů..."
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "
  const fs = require('fs');
  const db = db.getSiblingDB('${DB_NAME}');

  const importFileIfEmpty = (colName, filePath) => {
    const count = db[colName].countDocuments();
    if (count > 0) {
      print('Kolekce ' + colName + ' již obsahuje ' + count + ' záznamů. Přeskakuji import.');
      return;
    }
    if (!fs.existsSync(filePath)) {
      print('Soubor ' + filePath + ' nenalezen, přeskakuji.');
      return;
    }
    print('Importuji ' + filePath + ' do kolekce ' + colName + '...');
    const raw = fs.readFileSync(filePath, 'utf8');
    const docs = EJSON.parse(raw);
    
    // Dávkový import po 1000 dokumentech
    const batchSize = 1000;
    for (let i = 0; i < docs.length; i += batchSize) {
      const batch = docs.slice(i, i + batchSize);
      db[colName].insertMany(batch, { ordered: false });
    }
    print('Úspěšně importováno ' + docs.length + ' dokumentů do ' + colName + '.');
  };

  importFileIfEmpty('patients', '${DATA_DIR}/patients.json');
  importFileIfEmpty('sensor_readings', '${DATA_DIR}/sensor_readings.json');
  importFileIfEmpty('medical_interventions', '${DATA_DIR}/medical_interventions.json');

  print('=== Souhrnný stav kolekcí v databázi ${DB_NAME} ===');
  db.getCollectionNames().forEach(c => {
    print(c + ': ' + db[c].countDocuments() + ' dokumentů');
  });
"

echo ">>> [data-import] Import dat a konfigurace dokončeny!"
