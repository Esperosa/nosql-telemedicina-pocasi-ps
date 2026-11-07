#!/usr/bin/env bash
set -e

echo "================================================================================"
echo " KONTROLNÍ SKRIPT — Elastic Stack (Elasticsearch, Logstash, Kibana)"
echo " Téma: Počasí a kvalita ovzduší v ČR (ČHMÚ data)"
echo "================================================================================"

ES_URL="http://elasticsearch:9200"
AUTH="elastic:${ELASTIC_PASSWORD}"

echo ""
echo "[1/6] Kontrola zdraví clusteru (Cluster Health):"
HEALTH=$(curl -s -u "${AUTH}" "${ES_URL}/_cluster/health?pretty")
echo "${HEALTH}"
STATUS=$(echo "${HEALTH}" | grep '"status"' | awk -F '"' '{print $4}')
echo "Stav clusteru: ${STATUS}"
if [ "${STATUS}" == "yellow" ]; then
  echo "INFO: Stav yellow je na 1-uzlovém clusteru s number_of_replicas=1 očekávaný"
  echo "      (repliky zůstávají ve stavu UNASSIGNED, protože primár i replika nesmí běžet na stejném uzlu)."
fi

echo ""
echo "[2/6] Výpis indexů (_cat/indices?v):"
curl -s -u "${AUTH}" "${ES_URL}/_cat/indices?v&s=index"

echo ""
echo "[3/6] Ověření počtu dokumentů v indexech:"
for idx in stanice meteo_mereni-2023 meteo_mereni-2024 kvalita_ovzdusi-2023 kvalita_ovzdusi-2024; do
  COUNT=$(curl -s -u "${AUTH}" "${ES_URL}/${idx}/_count" | grep -o '"count":[0-9]*' | cut -d':' -f2)
  echo "  - Index ${idx}: ${COUNT:-0} dokumentů"
done

echo ""
echo "[4/6] Výpis alokace shardů (_cat/shards?v):"
curl -s -u "${AUTH}" "${ES_URL}/_cat/shards?v&s=index"

echo ""
echo "[5/6] Test oprávnění uživatele logstash_internal (RBAC):"
LOGSTASH_AUTH="logstash_internal:${LOGSTASH_INTERNAL_PASSWORD}"
LS_TEST=$(curl -s -u "${LOGSTASH_AUTH}" "${ES_URL}/stanice/_search?size=1" | grep -o '"timed_out":false')
if [ -n "${LS_TEST}" ]; then
  echo "  OK: Uživatel logstash_internal má správný přístup k indexům stanice*."
else
  echo "  CHYBA: Uživatel logstash_internal nemůže číst index stanice."
fi

# Ověření, že logstash_internal NEMÁ přístup k systémovým indexům
LS_DENIED=$(curl -s -u "${LOGSTASH_AUTH}" "${ES_URL}/.security*/_search" | grep -o 'security_exception')
if [ -n "${LS_DENIED}" ]; then
  echo "  OK: Uživatel logstash_internal má správně omezená práva (přístup k .security je odepřen)."
fi

echo ""
echo "[6/6] Kontrola dostupnosti Kibany:"
KIBANA_STATUS=$(curl -s -I http://kibana:5601/api/status | head -n 1)
echo "  Kibana API: ${KIBANA_STATUS:-Nedostupná}"

echo ""
echo "================================================================================"
echo " VŠECHNY KONTROLY DOKONČENY"
echo "================================================================================"
