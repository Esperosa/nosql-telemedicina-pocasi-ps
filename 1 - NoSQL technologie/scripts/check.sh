#!/usr/bin/env bash
set -euo pipefail

ROOT_USER="${MONGO_ROOT_USER:-admin}"
ROOT_PASS="${MONGO_ROOT_PASSWORD:-ClusterSuperSecretAdminPassword2026!}"
DB_NAME="${MONGO_DB_NAME:-telemedicina}"

echo "======================================================================"
echo " 1. KONTROLA STAVU CLUSTERU: sh.status()"
echo "======================================================================"
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval 'printjson(sh.status())'

echo ""
echo "======================================================================"
echo " 2. POČTY ZÁZNAMŮ V KOLEKCÍCH DATABÁZE '${DB_NAME}'"
echo "======================================================================"
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "
  const d = db.getSiblingDB('${DB_NAME}');
  d.getCollectionNames().sort().forEach(c => {
    print(' - ' + c + ': ' + d[c].countDocuments() + ' dokumentů');
  });
"

echo ""
echo "======================================================================"
echo " 3. DISTRIBUCE SHARDOVANÝCH DAT: \$shardedDataDistribution"
echo "======================================================================"
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "
  // \$shardedDataDistribution se musí spouštět nad databází 'admin' (ne nad
  // cílovou databází) a bez parametrů - vrátí distribuci přes všechny
  // shardované kolekce v clusteru, zde jen jedna: telemedicina.sensor_readings.
  const adminDb = db.getSiblingDB('admin');
  printjson(adminDb.aggregate([ { \$shardedDataDistribution: {} } ]).toArray());
"

echo ""
echo "======================================================================"
echo " 4. KONTROLA APLIKAČNÍHO UŽIVATELE (ROLE-BASED ACCESS CONTROL)"
echo "======================================================================"
APP_USER="${MONGO_APP_USER:-telemed_app}"
APP_PASS="${MONGO_APP_PASSWORD:-AppSecureVitalPass2026!}"
mongosh --host mongos1 --port 27017 -u "$APP_USER" -p "$APP_PASS" --authenticationDatabase "${DB_NAME}" --quiet --eval "
  const d = db.getSiblingDB('${DB_NAME}');
  print('Aplikační uživatel ' + '${APP_USER}' + ' úspěšně přihlášen.');
  print('Ověření čtení: počet pacientů = ' + d.patients.countDocuments());
"

echo ""
echo ">>> Kontrola clusteru a databáze proběhla úspěšně! <<<"
