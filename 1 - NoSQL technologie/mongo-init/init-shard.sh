#!/usr/bin/env bash
set -euo pipefail

# Použití: init-shard.sh <replSetName> <host1> <host2> <host3>
#
# POZOR: MongoDB "localhost exception" (dovolí vytvořit prvního uživatele bez
# autentizace) platí JEN pro spojení přes loopback (127.0.0.1) a musí mířit
# na PRIMARY. Tenhle init kontejner sdílí síťový prostor jen s H1
# (network_mode: service:<H1>), takže H1 MUSÍ vyhrát volby PRIMARY - proto
# má v rs.initiate() výrazně vyšší prioritu než H2/H3.
RS_NAME="$1"
H1="$2"
H2="$3"
H3="$4"

ROOT_USER="${MONGO_ROOT_USER:-admin}"
ROOT_PASS="${MONGO_ROOT_PASSWORD:-ClusterSuperSecretAdminPassword2026!}"

echo ">>> [${RS_NAME}-init] Kontrola stavu sady ${RS_NAME} a autentizace..."
if mongosh --port 27018 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; then
  echo ">>> [${RS_NAME}-init] Sada ${RS_NAME} je již inicializována a root uživatel existuje. Přeskakuji."
  exit 0
fi

echo ">>> [${RS_NAME}-init] Inicializace replikační sady ${RS_NAME} přes localhost exception (${H1} = vysoká priorita, vždy PRIMARY)..."
mongosh --port 27018 --quiet --eval "
  try {
    const res = rs.initiate({
      _id: '${RS_NAME}',
      members: [
        { _id: 0, host: '${H1}:27018', priority: 10 },
        { _id: 1, host: '${H2}:27018', priority: 1 },
        { _id: 2, host: '${H3}:27018', priority: 1 },
      ],
    });
    print('${RS_NAME} initiate issued: ' + JSON.stringify(res));
  } catch (e) {
    if (e.codeName === 'AlreadyInitialized' || /already initialized/i.test(e.message)) {
      print('${RS_NAME} již byla dříve inicializována.');
    } else {
      throw e;
    }
  }
"

echo ">>> [${RS_NAME}-init] Čekání na zvolení ${H1} jako PRIMARY..."
for i in {1..60}; do
  IS_PRIMARY=$(mongosh --port 27018 --quiet --eval '
    try {
      print(db.hello().isWritablePrimary ? "true" : "false");
    } catch (e) {
      print("false");
    }
  ' 2>/dev/null || echo "false")
  if [ "$IS_PRIMARY" = "true" ]; then
    echo ">>> [${RS_NAME}-init] ${H1} je PRIMARY (pokus $i)."
    break
  fi
  sleep 2
done

echo ">>> [${RS_NAME}-init] Vytváření root administrátora na ${RS_NAME}..."
mongosh --port 27018 --quiet --eval "
  try {
    const adminDb = db.getSiblingDB('admin');
    adminDb.createUser({
      user: '${ROOT_USER}',
      pwd: '${ROOT_PASS}',
      roles: [{ role: 'root', db: 'admin' }]
    });
    print('Root uživatel ${ROOT_USER} úspěšně vytvořen na ${RS_NAME}.');
  } catch (e) {
    if (e.codeName === 'UserAlreadyExists' || /already exists/i.test(e.message)) {
      print('Root uživatel na ${RS_NAME} již existuje.');
    } else {
      throw e;
    }
  }
"

echo ">>> [${RS_NAME}-init] Inicializace ${RS_NAME} úspěšně dokončena."
