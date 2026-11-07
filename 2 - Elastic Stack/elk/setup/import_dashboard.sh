#!/usr/bin/env bash
set -e

echo "[kibana-import] Čekám na dostupnost Kibany (http://kibana:5601)..."
until curl -s -I http://kibana:5601/api/status | grep -q -E "HTTP/1\.[01] (200|302)"; do
  sleep 3
done
echo "[kibana-import] Kibana je dostupná."

echo "[kibana-import] Importuji dashboard a vizualizace z /results/dashboard_export.ndjson..."
IMPORT_RES=$(curl -s -X POST "http://kibana:5601/api/saved_objects/_import?overwrite=true" \
  -u "elastic:${ELASTIC_PASSWORD}" \
  -H "kbn-xsrf: true" \
  --form file=@/results/dashboard_export.ndjson)

echo "[kibana-import] Výsledek importu:"
echo "$IMPORT_RES"

# Skutečná kontrola výsledku - Kibana i při chybě vrací HTTP 200/500 s JSON
# tělem, curl samotné proto chybu nezachytí. "success":true je jediný
# spolehlivý signál, že import opravdu proběhl.
if echo "$IMPORT_RES" | grep -q '"success":true'; then
  echo "[kibana-import] Import úspěšně dokončen."
  exit 0
else
  echo "[kibana-import] CHYBA: import se NEPOVEDL, viz výstup výše."
  exit 1
fi
