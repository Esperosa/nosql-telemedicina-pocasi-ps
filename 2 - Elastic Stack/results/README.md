# Výsledky vizualizací v Kibaně (results)

Tento adresář obsahuje analytický dashboard a vizualizace, postavené a ověřené přímo proti
běžícímu clusteru (Saved Objects API) a exportované rovnou z Kibany (`_export` endpoint) -
`dashboard_export.ndjson` tedy není ručně psaný soubor, ale skutečný export, který se dá
stejně tak zpátky naimportovat (ověřeno: čistý `docker compose down -v && up -d` naimportuje
všech 12 objektů bez chyby).

## 1. Exportní soubor

`dashboard_export.ndjson` obsahuje:
- 3 Data Views (Index Patterns): `stanice`, `meteo_mereni-*`, `kvalita_ovzdusi-*`
- 8 vizualizací (klasický typ `visualization`, ne Lens — jednodušší na sestavení i obhajobu)
- 1 dashboard **"CHMU - Pocasi a kvalita ovzdusi v CR"**

**Důležité omezení (ověřeno přímo na datech):** `stanice` a `kvalita_ovzdusi`/`meteo_mereni`
jsou oddělené indexy, Logstash je při importu nijak nepropojuje. Kibana klasická vizualizace
umí pracovat jen s jedním indexem/data view najednou, takže žádná vizualizace nekombinuje pole
z `stanice` s poli z `kvalita_ovzdusi` nebo `meteo_mereni` (např. "typ stanice × smogové
varování" by vyžadovalo buď enrichment v Logstash pipeline, nebo ES|QL `LOOKUP JOIN` v novější
vizualizaci typu ESQL — ani jedno není součástí tohoto dashboardu). Každá vizualizace proto
pracuje jen s poli z jedné datové sady.

## 2. Přehled a specifikace 8 vizualizací

Podle požadavků zadání: minimálně 8 vizualizací, každá jiného typu, minimálně 4 jsou grafy
a minimálně 1 je heatmapa (kategoriální × kategoriální × metrika).

| Č. | Název panelu | Typ | Zdroj dat | Dimenze 1 | Dimenze 2 | Metrika |
|:---:|---|---|---|---|---|---|
| **1** | Heatmapa: smog × AQI × PM10 (**POVINNÁ**) | **Heatmap** | `kvalita_ovzdusi-*` | smog_warning | aqi_index (1–6) | avg(pm10) |
| **2** | Průměrná teplota podle stavu počasí | **Bar Chart** | `meteo_mereni-*` | weather_condition | — | avg(temperature) |
| **3** | Trend PM10 v čase | **Line Chart** | `kvalita_ovzdusi-*` | @timestamp (měsíčně) | — | avg(pm10) |
| **4** | Rozložení záznamů podle stavu počasí | **Pie Chart** | `meteo_mereni-*` | weather_condition | — | count |
| **5** | Počet stanic podle kraje | **Bar Chart** | `stanice` | region | — | count |
| **6** | Počet stanic podle kraje a typu | **Data Table** | `stanice` | region | station_type | count |
| **7** | Celkový průměrný AQI index | **Metric** | `kvalita_ovzdusi-*` | — | — | avg(aqi_index) |
| **8** | Trend rychlosti větru v čase | **Area Chart** | `meteo_mereni-*` | @timestamp (týdně) | — | avg(wind_speed) |

## 3. Podrobný rozbor povinné heatmapy (Vizualizace č. 1)

Zadání výslovně předepisuje: 1 heatmapa kategoriální × kategoriální × metrika.

- **Dimenze 1 (segment)**: `smog_warning` — 3 diskrétní stavy smogového hlášení
  (`normal`, `upozorneni`, `regulace`).
- **Dimenze 2 (group)**: `aqi_index` — index kvality ovzduší ČHMÚ, celá čísla 1 až 6.
- **Metrika (barva)**: `avg(pm10)` — průměrná koncentrace částic PM10.

Ověřeno přímo agregačním dotazem nad Elasticsearch (ne odhadem): vyšší hodnoty `aqi_index`
mají systematicky vyšší průměrné PM10, což odpovídá očekávané fyzikální závislosti v datech
generátoru (horší kvalita ovzduší = vyšší koncentrace částic).

## 4. Jak dashboard ověřit sám/sama

```bash
cd "2 - Elastic Stack"
cp .env.example .env
docker compose up -d
# po chvíli (logy: docker compose logs kibana-import) by mělo být vidět
# "successCount":12,"success":true
```

Otevři `http://localhost:5601` (přihlášení `elastic` / heslo z `.env`), Dashboards →
**CHMU - Pocasi a kvalita ovzdusi v CR**.
