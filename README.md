# Semestrální práce — NoSQL databáze (NOSQL)

Univerzita Hradec Králové (UHK), Fakulta informatiky a managementu.

Tento repozitář obsahuje kompletní vypracování semestrální práce dle oficiálního zadání (`ZADANI-plny-text.md`). Práce je rozdělena do dvou samostatných a reprodukovatelných částí využívajících Docker Compose.

---

## Struktura repozitáře

```text
.
├── 1 - NoSQL technologie/        # 1. část: MongoDB sharded cluster
│   ├── data/                     # Datové soubory (JSON), Jupyter notebook, generátor
│   │   ├── analyza_dat.ipynb     # Průzkumová analýza dat (EDA) v Pythonu
│   │   ├── generate_data.py      # Generátor syntetických dat s pevným seedem (42)
│   │   ├── medical_interventions.json (800 záznamů)
│   │   ├── patients.json         (500 záznamů)
│   │   ├── requirements.txt      # Python závislosti pro EDA
│   │   └── sensor_readings.json  (8 000 záznamů - hlavní kolekce)
│   ├── mongo-init/               # Idempotentní inicializační skripty
│   │   ├── add-shards.sh         # Registrace shardů na mongos routeru
│   │   ├── import-data.sh        # $jsonSchema validace, sharding a import dat
│   │   ├── init-configsvr.sh     # Inicializace cfgrs replikační sady a RBAC uživatelů
│   │   └── init-shard.sh         # Inicializace shard replica setů (shard1rs..shard3rs)
│   ├── scripts/
│   │   └── check.sh              # Kontrolní skript (spuštění: docker compose run --rm check)
│   ├── .env.example              # Vzor konfiguračních proměnných (porty, hesla, DB)
│   ├── docker-compose.yml        # Definice 13 uzlů MongoDB clusteru + init služeb
│   ├── HOWTO.md                  # Podrobný návod ke spuštění, testování a ověření
│   ├── queries.txt               # 15 netriviálních navazujících dotazů s vysvětlením
│   └── README.md                 # Kompletní technická dokumentace k 1. části
├── 2 - Elastic Stack/            # 2. část: Elastic Stack (Elasticsearch, Logstash, Kibana)
│   ├── data/                     # 6 CSV souborů ve 3 kolekcích, EDA notebook, generátor
│   │   ├── analyza_dat.ipynb     # Průzkumová analýza dat (EDA) v Pythonu
│   │   ├── generate_data.py      # Generátor syntetických ČHMÚ dat (seed 42)
│   │   ├── kvalita_ovzdusi_2023.csv (6 000 záznamů)
│   │   ├── kvalita_ovzdusi_2024.csv (6 000 záznamů)
│   │   ├── meteo_mereni_2023.csv    (6 000 záznamů)
│   │   ├── meteo_mereni_2024.csv    (6 000 záznamů)
│   │   ├── requirements.txt      # Python závislosti pro EDA
│   │   ├── stanice_cechy.csv     (20 stanic)
│   │   └── stanice_morava.csv    (20 stanic)
│   ├── elk/
│   │   ├── elasticsearch/config/ # Konfigurace Elasticsearch (single-node, X-Pack)
│   │   ├── kibana/config/        # Konfigurace Kibana
│   │   ├── logstash/
│   │   │   ├── config/           # pipelines.yml (6 paralelních ETL pipelines)
│   │   │   ├── pipeline/         # 6 Logstash konfigurací (01_stanice..06_kvalita)
│   │   │   └── template/         # 3 Composable Index Templates pro kolekce
│   │   ├── queries/
│   │   │   └── queries.txt       # 5 Query DSL + 1 ES|QL vs Query DSL porovnání
│   │   └── setup/                # Inicializace RBAC rolí, uživatelů a importu
│   ├── results/
│   │   ├── dashboard_export.ndjson # Export dashboardu a 8 vizualizací v Lens
│   │   ├── HOWTO.md              # Návod na import a správu v Kibaně
│   │   └── README.md             # Podrobný rozbor všech 8 vizualizací a heatmapy
│   ├── scripts/
│   │   └── check.sh              # Kontrolní testovací skript pro 2. část
│   ├── .env.example              # Vzor konfiguračních proměnných pro ELK 9.5.2
│   ├── docker-compose.yml        # Definice ELK stacku + setup + import služeb
│   ├── HOWTO.md                  # Kompletní návod ke zprovoznění a ověření
│   └── README.md                 # Podrobná technická dokumentace k 2. části
├── .gitignore                    # Ignorování .env, logů, cache a keyfile klíčů
├── README.md                     # Tento souhrnný popis repozitáře
└── ZADANI-plny-text.md           # Oficiální a závazné plné znění zadání kurzu
```

---

## 1. část — MongoDB sharded cluster

- **Zvolená technologie**: MongoDB 8.3 (obraz `mongo:8.3.11`).
- **Topologie clusteru**: 13 kontejnerů — 3 config servery (`cfgrs`), 3 shardy po 3 uzlech (`shard1rs`, `shard2rs`, `shard3rs`) a 1 dotazovací router (`mongos1`).
- **Zabezpečení**: Interní autentizace clusteru pomocí sdíleného `keyFile` generovaného automaticky při startu do Docker volume (bezpečné bez uložení v Gitu). Řízení přístupu (RBAC) s rolí administrátora (`admin`) a aplikačního uživatele (`telemed_app`).
- **Doména a data**: Systém vzdáleného monitorování pacientů a telemetrie IoT biosenzorů (Telemedicína). Tři reprodukovatelné datové soubory s pevným seedem (8 000 odečtů, 500 pacientů, 800 intervencí).
- **Sharding a validace**: Hashovaný shard key `{ patient_id: "hashed" }` zajišťující rovnoměrné rozložení zátěže zápisů bez vzniku hotspots. Striktní validace schématu `$jsonSchema` chránící fyziologické meze vitálních funkcí.
- **Dotazy**: 15 netriviálních navazujících dotazů v `queries.txt` (distribuce přes `$shardedDataDistribution`, simulace výpadku uzlu a volba primary, měření replikačního zpoždění, `$lookup`, `$facet`, `$setWindowFields`, segmentace `$bucket`, vyhledání kriticky nebezpečných hodnot podle pevných klinických mezí a distribuované multi-dokumentové ACID transakce).
- **Rychlé spuštění**:
  ```bash
  cd "1 - NoSQL technologie"
  cp .env.example .env
  docker compose up -d
  docker compose run --rm check
  ```

---

## 2. část — Elastic Stack

- **Zvolená technologie**: Elastic Stack 9.5 (oficiální obrazy `elasticsearch:9.5.2`, `logstash:9.5.2`, `kibana:9.5.2`).
- **Topologie a architektura**: Jednouzlový Elasticsearch uzel (`discovery.type=single-node`) s paměťovým limitem JVM haldy 1 GB, webová analytika Kibana 9.5.2, paralelní ETL ingest Logstash a jednorázové služby pro automatický setup a import.
- **Zabezpečení**: Aktivní X-Pack Security (`xpack.security.enabled=true`). Bezpečné oddělení administrátora `elastic`, systémového účtu `kibana_system` a dedikovaného uživatele `logstash_internal` s rolí `logstash_writer` omezující zápis výhradně na vlastní indexy (`stanice*`, `meteo_mereni*`, `kvalita_ovzdusi*`).
- **Doména a data**: Počasí a kvalita ovzduší v ČR inspirovaná strukturou Státní sítě imisního monitoringu (ISKO) a klimatologických dat ČHMÚ. 6 datových souborů ve 3 kolekcích (celkem 24 040 záznamů, 4 soubory mají po 6 000 záznamech). Vzájemná propojitelnost přes `station_id` a `timestamp`.
- **Index Templates & Sharding**: Composable Index Templates (`_index_template/*`) pro každou kolekci s explicitními typy (`geo_point`, `date`, `float`, `keyword`). Konfigurace `number_of_shards: 1` a `number_of_replicas: 1` se zdůvodněním očekávaného stavu `yellow` z důvodu `UNASSIGNED` replik na jednouzlovém clusteru.
- **Ingest**: 6 nezávislých Logstash pipeline registrovaných v `pipelines.yml` zajišťujících idempotentní zpracování CSV souborů bez duplikace dat.
- **Dotazy**: 5 Query DSL dotazů (`term` filtr, sestupné třídění, `wildcard` maska, vícenásobný inverzní `range & bool` filtr, vícerozměrný měsíční `date_histogram` s `extended_stats`) a 1 srovnávací dotaz v novém jazyce **ES|QL** s detailním rozborem syntaxe, čitelnosti a vektorizovaného exekučního enginu.
- **Kibana Dashboard**: 8 Lens vizualizací odlišných typů (KPI karty, Line chart, Bar chart, Donut chart, **povinná heatmapa** typ stanice × smogové varování × průměr PM10, Area chart, Datová tabulka TOP stanic a Markdown informační panel) s automatickým importem přes Kibana Saved Objects API při startu kontejneru.
- **Rychlé spuštění**:
  ```bash
  cd "2 - Elastic Stack"
  cp .env.example .env
  docker compose up -d
  docker compose run --rm check
  ```
