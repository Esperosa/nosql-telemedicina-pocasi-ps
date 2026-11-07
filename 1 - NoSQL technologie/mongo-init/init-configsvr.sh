#!/usr/bin/env bash
set -euo pipefail

# POZOR: MongoDB "localhost exception" (dovolí vytvořit prvního uživatele bez
# autentizace) platí JEN pro spojení přes loopback (127.0.0.1), ne přes
# hostname/replica-set URI - a musí mířit na PRIMARY. Tenhle init kontejner
# sdílí síťový prostor jen s configsvr1 (network_mode: service:configsvr1),
# takže configsvr1 MUSÍ vyhrát volby PRIMARY, jinak loopback exception
# nepůjde využít. Proto má v rs.initiate() výrazně vyšší prioritu než
# configsvr2/3 - volby tak mají jen jeden možný výsledek.

ROOT_USER="${MONGO_ROOT_USER:-admin}"
ROOT_PASS="${MONGO_ROOT_PASSWORD:-ClusterSuperSecretAdminPassword2026!}"
APP_USER="${MONGO_APP_USER:-telemed_app}"
APP_PASS="${MONGO_APP_PASSWORD:-AppSecureVitalPass2026!}"
DB_NAME="${MONGO_DB_NAME:-telemedicina}"

echo ">>> [configsvr-init] Kontrola stavu cfgrs a autentizace..."
if mongosh --port 27019 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; then
  echo ">>> [configsvr-init] cfgrs je již inicializována a root uživatel existuje. Přeskakuji."
  exit 0
fi

echo ">>> [configsvr-init] Inicializace replikační sady cfgrs přes localhost exception (configsvr1 = vysoká priorita, vždy PRIMARY)..."
mongosh --port 27019 --quiet --eval '
  try {
    const res = rs.initiate({
      _id: "cfgrs",
      configsvr: true,
      members: [
        { _id: 0, host: "configsvr1:27019", priority: 10 },
        { _id: 1, host: "configsvr2:27019", priority: 1 },
        { _id: 2, host: "configsvr3:27019", priority: 1 },
      ],
    });
    print("cfgrs initiate issued: " + JSON.stringify(res));
  } catch (e) {
    if (e.codeName === "AlreadyInitialized" || /already initialized/i.test(e.message)) {
      print("cfgrs již byla inicializována.");
    } else {
      throw e;
    }
  }
'

echo ">>> [configsvr-init] Čekání na zvolení configsvr1 jako PRIMARY..."
for i in {1..60}; do
  IS_PRIMARY=$(mongosh --port 27019 --quiet --eval '
    try {
      print(db.hello().isWritablePrimary ? "true" : "false");
    } catch (e) {
      print("false");
    }
  ' 2>/dev/null || echo "false")
  if [ "$IS_PRIMARY" = "true" ]; then
    echo ">>> [configsvr-init] configsvr1 je PRIMARY (pokus $i)."
    break
  fi
  sleep 2
done

echo ">>> [configsvr-init] Vytváření root administrátora na cfgrs..."
mongosh --port 27019 --quiet --eval "
  try {
    const adminDb = db.getSiblingDB('admin');
    adminDb.createUser({
      user: '${ROOT_USER}',
      pwd: '${ROOT_PASS}',
      roles: [{ role: 'root', db: 'admin' }]
    });
    print('Root uživatel ${ROOT_USER} úspěšně vytvořen na cfgrs.');
  } catch (e) {
    if (e.codeName === 'UserAlreadyExists' || /already exists/i.test(e.message)) {
      print('Root uživatel již existuje.');
    } else {
      throw e;
    }
  }
"

echo ">>> [configsvr-init] Vytváření aplikačního uživatele ${APP_USER} na cfgrs..."
mongosh --port 27019 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "
  try {
    const targetDb = db.getSiblingDB('${DB_NAME}');
    targetDb.createUser({
      user: '${APP_USER}',
      pwd: '${APP_PASS}',
      roles: [
        { role: 'readWrite', db: '${DB_NAME}' },
        { role: 'clusterMonitor', db: 'admin' }
      ]
    });
    print('Aplikační uživatel ${APP_USER} úspěšně vytvořen na cfgrs.');
  } catch (e) {
    if (e.codeName === 'UserAlreadyExists' || /already exists/i.test(e.message)) {
      print('Aplikační uživatel již existuje.');
    } else {
      throw e;
    }
  }
"

echo ">>> [configsvr-init] Inicializace cfgrs úspěšně dokončena."
