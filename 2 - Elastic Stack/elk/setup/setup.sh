#!/usr/bin/env bash
set -e

echo "[setup] Čekám na dostupnost Elasticsearch..."
until curl -s -f -u "elastic:${ELASTIC_PASSWORD}" http://elasticsearch:9200/_cluster/health | grep -q '"status"'; do
  sleep 2
done
echo "[setup] Elasticsearch je dostupný."

echo "[setup] Nastavuji heslo pro interního uživatele kibana_system..."
curl -s -f -X POST -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  http://elasticsearch:9200/_security/user/kibana_system/_password \
  -d "{\"password\": \"${KIBANA_SYSTEM_PASSWORD}\"}"
echo ""

echo "[setup] Vytvářím roli logstash_writer (oprávnění pouze k vlastním indexům)..."
curl -s -f -X POST -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  http://elasticsearch:9200/_security/role/logstash_writer \
  -d @/setup/roles.json
echo ""

echo "[setup] Vytvářím uživatele logstash_internal..."
curl -s -f -X POST -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  http://elasticsearch:9200/_security/user/logstash_internal \
  -d "{\"password\": \"${LOGSTASH_INTERNAL_PASSWORD}\", \"roles\": [\"logstash_writer\"], \"full_name\": \"Logstash Ingestion Worker\"}"
echo ""

echo "[setup] Registruji composable index template pro stanice..."
curl -s -f -X PUT -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  http://elasticsearch:9200/_index_template/stanice_template \
  -d @/templates/stanice_template.json
echo ""

echo "[setup] Registruji composable index template pro meteo_mereni..."
curl -s -f -X PUT -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  http://elasticsearch:9200/_index_template/meteo_mereni_template \
  -d @/templates/meteo_mereni_template.json
echo ""

echo "[setup] Registruji composable index template pro kvalita_ovzdusi..."
curl -s -f -X PUT -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  http://elasticsearch:9200/_index_template/kvalita_ovzdusi_template \
  -d @/templates/kvalita_ovzdusi_template.json
echo ""

echo "[setup] Inicializace uživatelů, rolí a šablon úspěšně dokončena."
exit 0
