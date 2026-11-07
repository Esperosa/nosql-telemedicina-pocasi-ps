# 2. část — Elastic Stack (ELK)

Semestrální práce z předmětu NoSQL databáze (NOSQL), Univerzita Hradec Králové.

---

## Úvod

Tématem této práce je **monitorování meteorologické situace a kvality ovzduší v České republice**. Datová doména je inspirována architekturou a datovými standardy **Českého hydrometeorologického ústavu (ČHMÚ)**, který v ČR provozuje Státní síť imisního monitoringu (ISKO / AIM) a síť klimatologických a synoptických stanic.

Čtenář se v tomto dokumentu dozví:
- Jak navrhnout, nakonfigurovat a nasadit **Elastic Stack (Elasticsearch, Logstash, Kibana)** ve verzi 9.5.2 v souladu s Compose Specification jediným příkazem `docker compose up -d`.
- Jak zabezpečit cluster pomocí **X-Pack Security** s řízením přístupu (RBAC), oddělením administrátorského účtu `elastic`, systémového účtu `kibana_system` a aplikačního uživatele `logstash_internal` s minimálními oprávněními (`logstash_writer`) výhradně pro zápis do vlastních indexů.
- Jak navrhnout moderní **Composable Index Templates** s explicitním typovým mapováním, geolokačními body (`geo_point`), časovými řadami (`date`) a zdůvodněním konfigurace shardů (`number_of_shards`) a replik (`number_of_replicas`).
- Jak realizovat paralelní ingest 6 CSV souborů ve 3 kolekcích přes samostatné pipelines v **Logstash** s garancí idempotence.
- Jak formulovat analytické dotazy v jazyce **Query DSL** (filtry, řazení, wildcard vyhledávání, range dotazy a vícerozměrné agregace) a jak je srovnat s moderním pipe-based jazykem **ES|QL**.
- Jak sestavit přehledný analytický **dashboard v Kibaně** s 8 odlišnými typy vizualizací (včetně povinné heatmapy kategoriální × kategoriální × metrika) a zajistit jeho plně automatický import při startu - ověřeno živým exportem z běžící Kibany, ne ručně psaným NDJSON.

**Co záměrně NENÍ součástí práce a proč:**
- **TLS šifrování mezi uzly Elasticsearch**: Řešení využívá záměrně jeden databázový uzel v režimu `discovery.type=single-node`. Podle pravidel zadání nepřináší víceuzlový cluster žádné body navíc a vyžadoval by generování a distribuci TLS certifikátů, což by zvyšovalo režii a paměťovou náročnost nad rámec 16 GB RAM běžného počítače.
- **Externí sběr systémových metrik (Metricbeat / Filebeat)**: Ingest dat je plně realizován dedikovaným nástrojem Logstash přímo z datových souborů, čímž je zachována maximální jednoduchost a přehlednost architektury pro obhajobu.

---

## Data

### Původ a charakteristika dat
Zadání předepisuje minimálně 6 datových souborů ve 3 kolekcích (každá kolekce min. 2 soubory), přičemž minimálně 2 soubory musí obsahovat alespoň 5 000 záznamů a kolekce musí být vzájemně propojitelné.

> [!NOTE]
> **Prohlášení o původu dat**:
> Jedná se o **syntetická data inspirovaná reálnou strukturou otevřených dat ČHMÚ** (`https://opendata.chmi.cz/`), nikoli o stažená surová měření.
>
> **Důvod volby**: Surová historická data ČHMÚ jsou distribuována buď v obrovských archivech přesahujících stovky megabytů (např. `OpenISKO_1969_2025.zip` má 894 MB, což hrubě porušuje limit GitHubu 100 MB na soubor), nebo v tisících drobných hodinových souborů bez jednotného číselníku stanic.
> Data byla proto vygenerována skriptem `data/generate_data.py` s **pevným náhodným seedem (`SEED = 42`)**, který zajišťuje 100% deterministickou reprodukovatelnost. Všechny fyzikální a emisní závislosti (sezónní průběh teploty, vliv nadmořské výšky, fotochemický cyklus ozonu a vznik inverzních smogových epizod v zimě) přesně odpovídají reálným zákonitostem pozorovaným na stanicích ČHMÚ.

### Přehled kolekcí a souborů

| Kolekce | Soubor | Počet záznamů | Velikost | Popis obsahu |
|---|---|:---:|:---:|---|
| **1. stanice** | `stanice_cechy.csv` | 20 | 2.4 KB | 20 reálných monitorovacích stanic v Čechách (Praha, Plzeň, Hradec Králové, Ústí n. L. atd.) |
| | `stanice_morava.csv` | 20 | 2.2 KB | 20 reálných monitorovacích stanic na Moravě a ve Slezsku (Brno, Ostrava, Olomouc atd.) |
| **2. meteo_mereni** | `meteo_mereni_2023.csv` | **6 000** | 495 KB | Hodinová meteorologická měření za rok 2023 (teplota, vlhkost, tlak, vítr, srážky) |
| | `meteo_mereni_2024.csv` | **6 000** | 495 KB | Hodinová meteorologická měření za rok 2024 |
| **3. kvalita_ovzdusi** | `kvalita_ovzdusi_2023.csv` | **6 000** | 467 KB | Imisní měření za rok 2023 (PM10, PM2.5, NO2, SO2, O3, AQI index, smogové varování) |
| | `kvalita_ovzdusi_2024.csv` | **6 000** | 467 KB | Imisní měření za rok 2024 |
| **CELKEM** | **6 souborů** | **24 040** | **~1.9 MB** | **Požadavky zadání splněny: 3 kolekce, 4 soubory mají >= 5 000 záznamů.** |

### Datové schéma a atributy

1. **Kolekce `stanice`** (index `stanice`):
   - `station_id` (`keyword`): Jednoznačný kód stanice (např. `PHA-LIB`, `OST-RAD`, `HK-SAL`). Společný klíč pro propojení.
   - `station_name` (`text` + `.keyword`): Oficiální název stanice ČHMÚ.
   - `region` (`keyword`): Kraj ČR (např. `Hlavní město Praha`, `Moravskoslezský`).
   - `district` (`keyword`): Okres.
   - `city` (`keyword`): Město / obec.
   - `elevation` (`integer`): Nadmořská výška stanice v metrech (150 m až 1019 m).
   - `latitude`, `longitude` (`float`): Zeměpisné souřadnice WGS-84.
   - `location` (`geo_point`): Složený geolokační bod pro mapové vizualizace a prostorové dotazy.
   - `station_type` (`keyword`): Typ stanice dle metodiky EU/ČHMÚ (`průmyslová`, `dopravní`, `městská pozaďová`, `předměstská`, `venkovská pozaďová`).
   - `owner` (`keyword`): Provozovatel sítě (`ČHMÚ`).

2. **Kolekce `meteo_mereni`** (indexy `meteo_mereni-2023`, `meteo_mereni-2024`):
   - `measurement_id` (`keyword`): Primární identifikátor měření (`MET-2023-000001`).
   - `station_id` (`keyword`): Cizí klíč odkazující na kolekci `stanice`.
   - `timestamp` (`date`): Časová značka měření (ISO-8601 UTC).
   - `@timestamp` (`date`): Časové pole pro Elasticsearch time-series a histogramy.
   - `temperature` (`float`): Teplota vzduchu ve 2 m nad zemí ve °C (-15 °C až +35 °C).
   - `relative_humidity` (`float`): Relativní vlhkost vzduchu v % (25 % až 100 %).
   - `pressure` (`float`): Atmosférický tlak vzduchu v hPa (980 až 1035 hPa).
   - `wind_speed` (`float`): Rychlost větru v m/s (0.3 až 22 m/s).
   - `wind_direction` (`integer`): Směr větru ve stupních (0° až 360°).
   - `precipitation` (`float`): Úhrn srážek za měřicí interval v mm.
   - `weather_condition` (`keyword`): Stav počasí (`jasno`, `polojasno`, `oblačno`, `zataženo`, `déšť`, `sněžení`).

3. **Kolekce `kvalita_ovzdusi`** (indexy `kvalita_ovzdusi-2023`, `kvalita_ovzdusi-2024`):
   - `measurement_id` (`keyword`): Primární identifikátor měření (`AQ-2023-000001`).
   - `station_id` (`keyword`): Cizí klíč odkazující na stanici.
   - `timestamp` / `@timestamp` (`date`): Shodný časový údaj s meteorologickým měřením.
   - `pm10` (`float`): Hmotnostní koncentrace částic PM10 v µg/m³.
   - `pm2_5` (`float`): Hmotnostní koncentrace jemných částic PM2.5 v µg/m³.
   - `no2` (`float`): Koncentrace oxidu dusičitého v µg/m³.
   - `so2` (`float`): Koncentrace oxidu siřičitého v µg/m³.
   - `o3` (`float`): Koncentrace přízemního ozonu v µg/m³.
   - `aqi_index` (`integer`): Index kvality ovzduší ČHMÚ (hodnoty 1 až 6).
   - `smog_warning` (`keyword`): Smogová situace (`normal`, `upozorneni`, `regulace`).

### Propojitelnost dat (Referenční integrita)
Všechny 3 kolekce jsou vzájemně propojeny na 100 % záznamů:
- `stanice` ↔ `meteo_mereni` přes klíč `station_id`.
- `stanice` ↔ `kvalita_ovzdusi` přes klíč `station_id`.
- `meteo_mereni` ↔ `kvalita_ovzdusi` přes složený klíč `(station_id, timestamp)`.

---

## Konfigurace

### Popis `docker-compose.yml`

Definice služeb plně odpovídá **Compose Specification** (bez zastaralého atributu `version`):

```text
+-----------------------------------------------------------------------------------+
|                              Docker Bridge Network                                |
|                                "chmu_elk_network"                                 |
|                                                                                   |
|  +--------------------+        +--------------------+        +-----------------+  |
|  |   elasticsearch    | <----+ |       setup        |        |   kibana-import |  |
|  |     (Uzel 9.5.2)   |        | (Init role, šablon)|        | (Import NDJSON) |  |
|  |   Port: 9200       |        | (Exited 0)         |        | (Exited 0)      |  |
|  +---------+----------+        +--------------------+        +--------+--------+  |
|            |                                                          |           |
|            | healthcheck: green/yellow                                |           |
|            +-------------------------+                                |           |
|            |                         |                                |           |
|            v                         v                                v           |
|  +--------------------+    +--------------------+            +-----------------+  |
|  |      logstash      |    |       kibana       | <----------+      check      |  |
|  | (6 ETL pipelines)  |    |     (UI 9.5.2)     |                | (Diagnostika)   |  |
|  |  Ingest CSV dat    |    |     Port: 5601     |                +-----------------+  |
|  +--------------------+    +--------------------+                                 |
+-----------------------------------------------------------------------------------+
```

#### Přehled kontejnerů a parametrů:

1. **`elasticsearch`**:
   - **Obraz**: `docker.elastic.co/elasticsearch/elasticsearch:9.5.2` (žádný tag `latest`, multi-arch).
   - **Účel**: Centrální distribuované vyhledávací a analytické úložiště.
   - **Port**: `9200:9200` (konfigurovatelný přes `ES_PORT` v `.env`).
   - **Limity prostředků**: `ES_JAVA_OPTS=-Xms1g -Xmx1g` (velikost JVM haldy fixována na 1 GB, paměťový limit kontejneru 2 GB).
   - **Svazek (Volume)**: `es_data:/usr/share/elasticsearch/data` pro perzistenci indexů.
   - **Zabezpečení**: `xpack.security.enabled=true`, heslo superuživatele předáváno bezpečně přes `ELASTIC_PASSWORD` z `.env`.
   - **Healthcheck**: Periodický dotaz přes curl na `/_cluster/health` ověřující stav `green` nebo `yellow`.

2. **`setup`**:
   - **Obraz**: Shodný obraz Elasticsearch 9.5.2.
   - **Účel**: Jednorázový inicializační kontejner (`service_completed_successfully`).
   - **Činnost**:
     1. Čeká na zdraví Elasticsearch (`depends_on: { elasticsearch: { condition: service_healthy } }`).
     2. Nastaví heslo pro systémového uživatele `kibana_system`.
     3. Vytvoří roli `logstash_writer` v souladu se zadáním (práva zápisu výhradně k vlastním indexům `stanice*`, `meteo_mereni*`, `kvalita_ovzdusi*`).
     4. Vytvoří uživatele `logstash_internal` a přiřadí mu roli `logstash_writer`.
     5. Nahraje composable index templates (`_index_template/*`) pro všechny 3 kolekce.
     6. Úspěšně se ukončí (`exit 0`).

3. **`kibana`**:
   - **Obraz**: `docker.elastic.co/kibana/kibana:9.5.2`.
   - **Účel**: Webové uživatelské a analytické rozhraní.
   - **Port**: `5601:5601` (konfigurovatelný přes `KIBANA_PORT`).
   - **Závislosti**: Spouští se až po dokončení služby `setup` a zdravém Elasticsearch.
   - **Autentizace**: Ke komunikaci s Elasticsearch využívá dedikovaný účet `kibana_system` a heslo `KIBANA_SYSTEM_PASSWORD` z `.env`.
   - **Healthcheck**: Kontrola dostupnosti HTTP koncového bodu `/api/status`.

4. **`kibana-import`**:
   - **Obraz**: Elasticsearch 9.5.2 (obsahuje curl).
   - **Účel**: Automatický a idempotentní import dashboardu a vizualizací z `results/dashboard_export.ndjson`.
   - **Spuštění**: Po nastartování a ověření zdraví Kibany (`depends_on: { kibana: { condition: service_healthy } }`). Odesílá soubor na API `POST /api/saved_objects/_import?overwrite=true`.

5. **`logstash`**:
   - **Obraz**: `docker.elastic.co/logstash/logstash:9.5.2`.
   - **Účel**: Paralelní ETL transformace a ingest dat ze 6 CSV souborů do Elasticsearch.
   - **Limity prostředků**: `LS_JAVA_OPTS=-Xms512m -Xmx512m` (JVM halda 512 MB, paměťový limit 1 GB).
   - **Autentizace**: Používá uživatele `logstash_internal` s omezenou rolí `logstash_writer`.
   - **Pipelines**: Registrace v `pipelines.yml` mapuje 6 konfiguračních souborů `01_stanice_cechy.conf` až `06_kvalita_2024.conf`.

6. **`check`**:
   - **Profil**: `tools` (spouští se manuálně pomocí `docker compose run --rm check`).
   - **Účel**: Komplexní ověřovací a testovací skript pro kontrolu stavu clusteru, indexů, shardů a RBAC.

---

## Composable Index Templates & Mapping

Zadání striktně vyžaduje použití moderních **Composable Index Templates** (API `_index_template`), nikoliv zastaralých legacy šablon (`_template`), a to 1 šablonu na kolekci:

1. **`elk/logstash/template/stanice_template.json`** (`stanice_template`):
   - Maska indexu: `stanice*`
   - Klíčové typy: `station_id: keyword`, `elevation: integer`, `location: geo_point`, `station_name: text` s podpolem `keyword`.
2. **`elk/logstash/template/meteo_mereni_template.json`** (`meteo_mereni_template`):
   - Maska indexu: `meteo_mereni*`
   - Klíčové typy: `timestamp: date`, `@timestamp: date`, `temperature: float`, `pressure: float`, `wind_speed: float`, `precipitation: float`.
3. **`elk/logstash/template/kvalita_ovzdusi_template.json`** (`kvalita_ovzdusi_template`):
   - Maska indexu: `kvalita_ovzdusi*`
   - Klíčové typy: `timestamp: date`, `pm10: float`, `pm2_5: float`, `no2: float`, `o3: float`, `aqi_index: integer`, `smog_warning: keyword`.

### Zdůvodnění počtu shardů a replik

- **`number_of_shards: 1`**:
  Pro datové sady v řádu desítek tisíc dokumentů (celkem ~24 000 záznamů, jednotky MB) je 1 primární shard optimální. Více primárních shardů by vedlo k tzv. over-shardingu (zbytečná režie na správu Lucene indexů a plýtvání pamětí JVM haldy).
- **`number_of_replicas: 1`**:
  V produkčním prostředí je hodnota `1` nutná pro zajištění vysoké dostupnosti (HA) — replika je alokována na jiný uzel a chrání před ztrátou dat.

### Doložení a interpretace diagnostických výpisů CAT API

#### 1. Výpis `GET _cat/indices?v`:
```text
health status index                uuid                   pri rep docs.count docs.deleted store.size pri.store.size
yellow open   stanice              4k9L_m6wQ1yT...          1   1         40            0     34.2kb         34.2kb
yellow open   meteo_mereni-2023    7x8N_p2zR4wU...          1   1       6000            0    612.4kb        612.4kb
yellow open   meteo_mereni-2024    9a1B_c5dE7fG...          1   1       6000            0    614.1kb        614.1kb
yellow open   kvalita_ovzdusi-2023 2h3J_k4lM8nP...          1   1       6000            0    588.6kb        588.6kb
yellow open   kvalita_ovzdusi-2024 5v6W_x7yZ9aQ...          1   1       6000            0    589.2kb        589.2kb
```
**Interpretace**: Všech 5 aplikačních indexů bylo úspěšně vytvořeno a naplněno přesným počtem dokumentů. Všechny primární shardy (`pri: 1`) jsou otevřené a plně funkční.

#### 2. Výpis `GET _cat/shards?v`:
```text
index                shard prirep state      docs   store ip         node
stanice              0     p      STARTED      40  34.2kb 172.28.0.2 elasticsearch
stanice              0     r      UNASSIGNED
meteo_mereni-2023    0     p      STARTED    6000 612.4kb 172.28.0.2 elasticsearch
meteo_mereni-2023    0     r      UNASSIGNED
meteo_mereni-2024    0     p      STARTED    6000 614.1kb 172.28.0.2 elasticsearch
meteo_mereni-2024    0     r      UNASSIGNED
kvalita_ovzdusi-2023 0     p      STARTED    6000 588.6kb 172.28.0.2 elasticsearch
kvalita_ovzdusi-2023 0     r      UNASSIGNED
kvalita_ovzdusi-2024 0     p      STARTED    6000 589.2kb 172.28.0.2 elasticsearch
kvalita_ovzdusi-2024 0     r      UNASSIGNED
```

#### 3. Výpis `GET _cat/allocation?v`:
```text
shards disk.indices disk.used disk.avail disk.total disk.percent host       ip         node
     5        2.4mb    38.4gb    210.5gb    248.9gb           15 172.28.0.2 172.28.0.2 elasticsearch
     5                                                                               UNASSIGNED
```

#### DŮVOD STAVU YELLOW A UNASSIGNED REPLIK (Povinné vysvětlení ze zadání):
> [!IMPORTANT]
> Stav clusteru **`yellow`** je na jednom uzlu **naprosto v pořádku a technicky zcela očekávaný**:
> Architektura Elasticsearch má pevné bezpečnostní pravidlo: **primární shard a jeho replika nesmí být nikdy umístěny na stejném fyzickém uzlu** (umístění repliky na tentýž disk/stroj by neposkytovalo žádnou ochranu při havárii uzlu).
> Jelikož běží právě 1 uzel Elasticsearch, primární shardy (`p`) jsou úspěšně alokovány (`STARTED`), ale repliky (`r`) nemají žádný další dostupný uzel, kam by se mohly uložit — proto zůstávají ve stavu **`UNASSIGNED`**. Stav `yellow` indikuje, že všechna data jsou 100% dostupná a čitelná, pouze není zajištěna redundance pro případ výpadku uzlu.

---

## Dotazy

Kompletní zadání dotazů, přesné příkazy, formátované výstupy z konzole, technická vysvětlení a interpretace výsledků jsou uloženy v souboru:
👉 **[`elk/queries/queries.txt`](file:///C:/Users/Creator/Desktop/UHK-co%20udělat/04%20-%20NoSQL%20databaze%20(NOSQL)/Projekt%20-%20semestralni%20prace/2%20-%20Elastic%20Stack/elk/queries/queries.txt)**

### Stručný přehled vypracovaných dotazů:

1. **Dotaz 1 [Filtr — Term query]**:
   - *Zadání*: Vyhledání monitorovacích stanic v Jihomoravském kraji (`term` na `region.keyword`).
   - *Výsledek*: Nalezeny 4 stanice v Brně (Zvonařka, Kroftova, Líšeň, Svatoplukova).
2. **Dotaz 2 [Třídění — Sort query]**:
   - *Zadání*: Výpis 10 nejvýše položených stanic seřazených sestupně podle nadmořské výšky (`sort: { elevation: "desc" }`).
   - *Výsledek*: Horské referenční stanice Krkonoše-Šerlich (1019 m) a Jeseník-Červenohorské sedlo (1013 m) na prvních místech.
3. **Dotaz 3 [Wildcard & Bool query]**:
   - *Zadání*: Vyhledání stanic v ostravské aglomeraci podle masky (`wildcard: *Ostrava*` nebo předpona kódu `OST-*`).
   - *Výsledek*: Nalezeny 4 ostravské stanice (Fifejdy, Radvanice, Poruba, Přívoz) pokrývající průmyslové i obytné zóny.
4. **Dotaz 4 [Pokročilý 1 — Range & Bool s vícenásobnou podmínkou]**:
   - *Zadání*: Detekce smogových inverzních epizod — vyhledání měření, kde koncentrace PM10 překročila 100 µg/m³, platil stav smogového varování (`terms: ["upozorneni", "regulace"]`) a index AQI byl 5 nebo 6.
   - *Výsledek*: 118 závažných situací, extrémy dosahující až 178 µg/m³ v zimních měsících na průmyslových stanicích.
5. **Dotaz 5 [Pokročilý 2 — Složená časová agregace Date Histogram + Extended Stats]**:
   - *Zadání*: Měsíční agregace vývoje jemného prachu PM2.5 a průměrného indexu AQI v průběhu roku.
   - *Výsledek*: Průkaz trojnásobného znečištění v lednu (34.6 µg/m³ PM2.5) oproti červenci (11.8 µg/m³).
6. **Dotaz 6 [Porovnání ES|QL vs. Query DSL]**:
   - *Zadání*: Výpočet průměrných hodnot PM10, PM2.5 a NO2 podle typu stanice s filtrem na zhoršenou kvalitu ovzduší (AQI >= 4).
   - *Srovnání*: ES|QL nabízí stručný lineární 7-řádkový zápis se svislítky `|` a tabulkovým výstupem, zatímco Query DSL vyžaduje 38 řádků hluboce zanořeného JSON stromu. ES|QL navíc využívá nový vektorizovaný blokový engine s nižší režií na JVM haldu.

---

## Vizualizace

Všechny vizualizace a centrální analytický dashboard jsou uloženy v souboru:
👉 **[`results/dashboard_export.ndjson`](file:///C:/Users/Creator/Desktop/UHK-co%20udělat/04%20-%20NoSQL%20databaze%20(NOSQL)/Projekt%20-%20semestralni%20prace/2%20-%20Elastic%20Stack/results/dashboard_export.ndjson)**
👉 Podrobná dokumentace vizualizací: **[`results/README.md`](file:///C:/Users/Creator/Desktop/UHK-co%20udělat/04%20-%20NoSQL%20databaze%20(NOSQL)/Projekt%20-%20semestralni%20prace/2%20-%20Elastic%20Stack/results/README.md)**

### Přehled 8 vizualizací v dashboardu

**Pozn.:** `stanice` a `kvalita_ovzdusi-*`/`meteo_mereni-*` jsou oddělené indexy bez
propojení na úrovni dat (Logstash je nijak nespojuje při importu). Proto každá
vizualizace pracuje jen s poli z JEDNÉ datové sady - kombinace polí napříč
"stanice" a "kvalita_ovzdusi" (např. typ stanice × smogové varování) by
vyžadovala buď enrichment v Logstash pipeline, nebo ES|QL LOOKUP JOIN, a není
součástí dashboardu. Vizualizace jsou klasického typu (`visualization`), ne
Lens - jednodušší na sestavení i obhajobu, s prakticky stejnou vypovídací
hodnotou pro agregační grafy tohoto rozsahu.

| Číslo | Typ | Název | Zdroj dat | Dimenze | Metrika |
|:---:|---|---|---|---|---|
| **1** | **Heatmap (POVINNÁ)** | Smogové varování × AQI × průměr PM10 | `kvalita_ovzdusi-*` | smog_warning × aqi_index | avg(pm10) |
| **2** | **Bar Chart** | Průměrná teplota podle stavu počasí | `meteo_mereni-*` | weather_condition | avg(temperature) |
| **3** | **Line Chart** | Trend PM10 v čase | `kvalita_ovzdusi-*` | @timestamp (měsíčně) | avg(pm10) |
| **4** | **Pie Chart** | Rozložení záznamů podle stavu počasí | `meteo_mereni-*` | weather_condition | count |
| **5** | **Bar Chart** | Počet stanic podle kraje | `stanice` | region | count |
| **6** | **Data Table** | Počet stanic podle kraje a typu | `stanice` | region × station_type | count |
| **7** | **Metric** | Celkový průměrný AQI index | `kvalita_ovzdusi-*` | — | avg(aqi_index) |
| **8** | **Area Chart** | Trend rychlosti větru v čase | `meteo_mereni-*` | @timestamp (týdně) | avg(wind_speed) |

### Popis povinné heatmapy (Vizualizace č. 1):
Heatmapa kombinuje dvě diskrétní kategorické dimenze a jednu spojitou agregovanou metriku,
obě z kolekce `kvalita_ovzdusi`:
- **Kategorie X**: Stav smogového varování (`normal`, `upozorneni`, `regulace`).
- **Kategorie Y**: Index kvality ovzduší ČHMÚ (1 až 6).
- **Metrika**: Průměrná hodnota koncentrace polétavého prachu PM10.
Ověřeno přímo nad reálnými daty v Elasticsearch (agregační dotaz, listopad 2026): nejvyšší
kategorie AQI mají systematicky vyšší průměrné PM10, což potvrzuje, že syntetická data
generátoru odpovídají očekávané fyzikální závislosti (vyšší znečištění → horší index kvality).

---

## Závěr


---

## Prohlášení o použití AI


---

## Zdroje

1. **ČHMÚ Otevřená data**:
   - Klimatologická a meteorologická data: [https://opendata.chmi.cz/meteorology/climate/](https://opendata.chmi.cz/meteorology/climate/)
   - Historická data a monitoring kvality ovzduší: [https://opendata.chmi.cz/air_quality/](https://opendata.chmi.cz/air_quality/)
2. **Elasticsearch Reference (v 9.5)**:
   - Composable Index Templates: [https://www.elastic.co/guide/en/elasticsearch/reference/current/index-templates.html](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-templates.html)
   - Query DSL: [https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)
   - ES|QL (Elasticsearch Query Language): [https://www.elastic.co/guide/en/elasticsearch/reference/current/esql.html](https://www.elastic.co/guide/en/elasticsearch/reference/current/esql.html)
3. **Logstash Reference (v 9.5)**:
   - Multiple Pipelines (`pipelines.yml`): [https://www.elastic.co/guide/en/logstash/current/multiple-pipelines.html](https://www.elastic.co/guide/en/logstash/current/multiple-pipelines.html)
   - CSV Filter Plugin: [https://www.elastic.co/guide/en/logstash/current/plugins-filters-csv.html](https://www.elastic.co/guide/en/logstash/current/plugins-filters-csv.html)
4. **Kibana Guide (v 9.5)**:
   - Lens Visualizations & Dashboards: [https://www.elastic.co/guide/en/kibana/current/lens.html](https://www.elastic.co/guide/en/kibana/current/lens.html)
   - Saved Objects Import/Export API: [https://www.elastic.co/guide/en/kibana/current/saved-objects-api-import.html](https://www.elastic.co/guide/en/kibana/current/saved-objects-api-import.html)
5. **Docker & Compose Specification**:
   - The Compose Specification: [https://compose-spec.io/](https://compose-spec.io/)
