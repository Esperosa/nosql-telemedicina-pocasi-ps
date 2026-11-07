#!/usr/bin/env bash
set -euo pipefail

ROOT_USER="${MONGO_ROOT_USER:-admin}"
ROOT_PASS="${MONGO_ROOT_PASSWORD:-ClusterSuperSecretAdminPassword2026!}"
DB_NAME="${MONGO_DB_NAME:-telemedicina}"

echo ">>> [cluster-init] Čekání na dostupnost a autentizaci na mongos1..."
for i in {1..40}; do
  if mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; then
    echo ">>> [cluster-init] Spojení s mongos1 navázáno a ověřeno (pokus $i)."
    break
  fi
  sleep 2
done

echo ">>> [cluster-init] Registrace shardů do clusteru přes mongos1..."
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval '
  const registerShard = (shardConn) => {
    try {
      const res = sh.addShard(shardConn);
      print("addShard: " + JSON.stringify(res));
    } catch (e) {
      if (e.codeName === "AlreadyInitialized" || /already exists/i.test(e.message) || /is already/i.test(e.message)) {
        print("Shard " + shardConn + " je již registrován.");
      } else {
        print("addShard poznámka/chyba: " + e.message);
      }
    }
  };

  registerShard("shard1rs/shard1a:27018,shard1b:27018,shard1c:27018");
  registerShard("shard2rs/shard2a:27018,shard2b:27018,shard2c:27018");
  registerShard("shard3rs/shard3a:27018,shard3b:27018,shard3c:27018");
'

echo ">>> [cluster-init] Povolení shardingu pro databázi ${DB_NAME}..."
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval "
  try {
    sh.enableSharding('${DB_NAME}');
    print('Sharding úspěšně povolen pro databázi ${DB_NAME}.');
  } catch (e) {
    if (/already/i.test(e.message)) {
      print('Sharding pro databázi ${DB_NAME} byl již dříve povolen.');
    } else {
      print('enableSharding info: ' + e.message);
    }
  }
"

echo ">>> [cluster-init] Cluster je úspěšně zinicializován. Aktuální stav shardů:"
mongosh --host mongos1 --port 27017 -u "$ROOT_USER" -p "$ROOT_PASS" --authenticationDatabase admin --quiet --eval 'printjson(sh.status())'
