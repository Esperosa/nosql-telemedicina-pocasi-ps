# Zadání semestrální práce — NOSQL (plný text ze stránky kurzu)

Zdroj: https://kurzy.uhk.cz/mod/page/view.php?id=391355 (naposledy změněno 5. 11. 2026)

Šablona repozitáře (GIT repozitář s připravenou strukturou): https://kurzy.uhk.cz/mod/resource/view.php?id=397226
Odevzdání: https://kurzy.uhk.cz/mod/assign/view.php?id=397423

**Termín odevzdání: 3. 1. 2027 23:59:59. Po termínu se na aktivitu nebere zřetel.**

---

## Požadavky

Semestrální práce musí být vypracována dle předem připravené struktury, která je přístupná
formou GIT repozitáře, který je ke stažení zde v kurzu.

Při řešení obou částí semestrální práce je povinné využití Docker a Docker Compose. Obě
části práce musí být jednoduše reprodukovatelné (docker-compose.yml).

Semestrální práce má dvě části. V první části si studující zvolí jednu z NoSQL databází
probíraných na cvičení (Redis, MongoDB, Apache Cassandra), v druhé části bude pracovat s
Elastic Stackem (ELK – Elasticsearch, Logstash, Kibana).

Práce není považována za kompletní, pokud neobsahuje všechny požadované části. Nelze
vypracovat pouze část práce, taková nebude hodnocena.

Semestrální práci zpracovává každý student individuálně. Skupinové zpracování ani sdílení
řešení (konfigurace, skriptů, dotazů, dokumentace) mezi studenty není povoleno.

Práce musí být vlastním dílem autora, jinak nebude uznána. Odevzdané práce jsou
kontrolovány na plagiátorství, a to i vzájemně mezi sebou. V práci je nutné uvést veškeré
použité zdroje a nástroje. Student musí své práci rozumět.

Při obhajobě, která probíhá formou písemného testu (viz kapitola Obhajoba), je nutné přesně
vědět, jak funguje odevzdané řešení, a to z pohledu architektury, datových toků, každého
dotazu i každé konfigurační volby. Vše musí být reprodukovatelné/spustitelné z odevzdaného
repozitáře.

### Použití nástrojů umělé inteligence

Použití AI nástrojů (jazykové modely, asistenti v IDE, generátory kódu) je povoleno, ale je
povinné jej transparentně přiznat.

V každé části repozitáře uveďte v README.md sekci **Prohlášení o použití AI**, která obsahuje:
- které nástroje jste použili (název a verze/model, pokud je známa),
- k čemu konkrétně – např. generování testovacích dat, návrh agregační pipeline, ladění
  konfigurace, korektura textu,
- co jste na výstupu museli opravit – tedy kde se model mýlil.

Pokud jste AI nástroje v dané části nepoužili, uveďte to v dané sekci výslovně. Použité
nástroje uveďte také v abecedním seznamu v části Zdroje a nástroje.

Nepřiznané použití AI je posuzováno stejně jako nepřiznané použití cizího zdroje. Zároveň
platí, že odpovědnost za správnost je vždy Vaše. Porozumění odevzdanému řešení, včetně
částí vytvořených s pomocí AI, ověřuje písemný test při obhajobě.

### Společné požadavky na Docker Compose a reprodukovatelnost

Platí pro obě části semestrální práce.

- Obě části musí být spustitelné pomocí Docker Compose jediným příkazem: `docker compose up -d`
- Před prvním spuštěním vytvořte `.env` zkopírováním přiloženého vzoru `.env.example`
  (`cp .env.example .env`, ve Windows PowerShell `Copy-Item .env.example .env`). `.env`
  se do repozitáře neodevzdává (je v `.gitignore`).
- Po `docker compose up -d` musí být řešení plně funkční bez manuálního zásahu (init
  kontejnery, `depends_on`, entrypointy, služby `*-init`).
- `docker-compose.yml` musí odpovídat Compose Specification (bez atributu `version`).
- Povinně používejte `healthcheck` a `depends_on: condition: service_healthy` /
  `service_completed_successfully`. Žádné pevné `sleep` čekání. Inicializační skripty musí
  být idempotentní (znovuspuštění `docker compose up -d` nesmí chybovat ani duplikovat data).
- Konfigurovatelné hodnoty (verze obrazů, hesla, porty, cesty) přes `.env`, nikdy natvrdo.
- Verze obrazů explicitně (žádný `latest`), např. `mongo:8.3.11`.
- Před odevzdáním ověřit čisté spuštění: `docker compose down -v && docker compose up -d`.
- Součástí 1. části je kontrolní skript (např. `scripts/check.sh`) spouštěný uvnitř kontejneru
  (`docker compose exec <služba> /scripts/check.sh` nebo `docker compose run --rm check`),
  uveďte příkaz v HOWTO.md.
- Každá část má `HOWTO.md`: kroky od `git clone` po funkční řešení, min. požadavky na RAM
  (16 GB, x86_64; ARM64 vítáno) a čas nastartování, kontrolní seznam jak poznat, že řešení
  běží správně.
- README každé části popisuje `docker-compose.yml`: služby (obraz, verze, účel), porty,
  volumes, proměnné prostředí, sítě, závislosti/healthchecky, inicializační skripty, omezení
  prostředků (paměť a velikost haldy u služeb s JVM — Cassandra, Elasticsearch, Logstash).

### Datové soubory v repozitáři

Ve složce `data`, aby bylo řešení reprodukovatelné i bez internetu. Jeden soubor max 100 MB
(limit GitHubu) — rozdělit, zkomprimovat, nebo nechat stáhnout/vygenerovat init službou s
pevným seedem / kontrolním součtem.

### Pravidlo pro volbu verzí (k 1. 10. 2026)

| Technologie | Aktuální verze | Nejstarší přípustná |
|---|---|---|
| Redis | 8.10 | 8.4 |
| MongoDB | 8.3 | 8.0 |
| Apache Cassandra | 5.0 | 5.0 (řada 4.x = starší major) |
| Elasticsearch/Logstash/Kibana | 9.5 | 9.2 |

---

## 1. část — zvolená NoSQL databáze (25 bodů)

Vyberte **jednu**: Redis / MongoDB / Apache Cassandra.

Povinné náležitosti:
- **Úvod**: téma, co se čtenář dozví, co záměrně není součástí práce a proč.
- Verze databáze dle pravidla výše, zvolené Docker Hub obrazy a zdůvodnění (oficiální
  preferovat; u Redisu **redis/redisinsight**, ne zastaralé `redis/redis-stack-server`; u
  MongoDB `haohanyang/compass-web`; **Bitnami obrazy nepoužívat** — od 28.8.2025 legacy).
- **a) Architektura** — schéma (např. draw.io) + popis a zdůvodnění.
- **b) Specifika konfigurace**:
  - cluster (min. 1), uzly (min. 3), sharding/partitioning (min. 3), replikace (min. 3 kopie),
    perzistence dat, distribuce dat, zabezpečení (autentizace + autorizace; u MongoDB keyfile
    generovaný při startu, ne uložený v repu; hesla jen přes `.env`).
  - Minimální topologie: **Redis** Cluster 3 primární + 2 repliky ke každému = 9 uzlů. **MongoDB**
    3 shardy × replikační sada 3 členů (9 uzlů) + config servery (3) + alespoň 1 `mongos`.
    **Cassandra** 3 uzly v 1 DC, `replication_factor: 3`, sharding přes vnodes.
- **c) Případ užití** — proč tahle databáze pro tenhle účel.
- **d) Výhody a nevýhody**.
- **e) CAP teorém a PACELC** — jaké garance splňuje nasazení a proč (doložit konkrétním
  nastavením: MongoDB `writeConcern`/`readConcern`/`readPreference`, Cassandra consistency
  level, Redis async replikace + failover). Kategorie PACELC (PA/EL, PC/EC) + alespoň jedno
  měření/pozorování.
- **f) Další specifika** vlastního řešení (nebo konstatovat, že žádná nejsou).
- Specifické požadavky dle databáze (Redis Functions a hash tagy; MongoDB shard key přes
  `analyzeShardKey`, `$jsonSchema` validace, chunk size; Cassandra `user_defined_functions_enabled`,
  Storage-Attached Indexes).

### Dotazy (1. část)

- Data: 3 datové soubory (vlastní nebo generovaná), alespoň jeden ≥ 5000 záznamů.
- Analýza dat v Pythonu (Jupyter notebook, Pandas/NumPy/Matplotlib): počty, typy, chybějící
  hodnoty, statistiky, min. 1 graf, ověření propojitelnosti souborů. Uložit do
  `data/analyza_dat.ipynb`, knihovny do `data/requirements.txt`.
- **15 netriviálních navazujících dotazů** s řešením a vysvětlením, číslovaných, v `queries.txt`
  i v dokumentaci (zadání v přirozeném jazyce, přesný příkaz, výstup z konzole, vysvětlení,
  interpretace). Žádné prosté CRUD. Konkrétní povinnosti dle databáze — viz plné znění níže.
- Alespoň **3 z 15** dotazů musí pracovat s clusterem (distribuce dat, výpadek uzlu, konzistence/
  replikace), včetně simulace výpadku uzlu (před/během/po).
- Povinný dotaz dle databáze: Redis → `CLUSTER KEYSLOT`/`COUNTKEYSINSLOT`; MongoDB →
  `$shardedDataDistribution`; Cassandra → SAI vs. denormalizovaná tabulka s `TRACING ON`.

---

## 2. část — Elastic Stack (25 bodů)

- Data: nové téma, odlišné od 1. části. Min. **6 datových souborů** ve **3 kolekcích** (každá
  kolekce min. 2 soubory), min. 2 soubory ≥ 5000 záznamů, kolekce propojitelné přes společný
  identifikátor. Zdroje a licence uvést. Ukázkové řešení a IMDb (a podobné) jsou **zakázané**.
- Analýza dat v Pythonu stejně jako v 1. části.
- Elastic Stack verze dle pravidla výše, všechny komponenty stejná verze. 1 uzel Elasticsearch
  stačí (více uzlů = TLS povinné, žádné body navíc).
- Import přes **Logstash** (`elk/logstash/pipeline/*.conf`, 1 pipeline na datový soubor,
  registrace v `pipelines.yml`), vizualizace v **Kibaně**.
- Composable index templates (ne legacy `_template`), vlastní mapping, `number_of_shards`/
  `number_of_replicas` zdůvodněné. Zabezpečení zapnuté (`xpack.security.enabled`), hesla
  přes `.env` + setup službu.
- Doložit `GET _cat/indices?v`, `_cat/shards?v`, `_cat/allocation?v` a interpretovat (u 1 uzlu
  vysvětlit `UNASSIGNED` repliky → stav yellow).
- Min. **5 dotazů v Query DSL** (filtr, třídění, wildcard, 2× pokročilé — agregace/nested/range/
  fulltext) + min. **1 dotaz v ES|QL** porovnaný s ekvivalentem v Query DSL. Uložit do
  `elk/queries/queries.txt`.
- **Dashboard s min. 8 vizualizacemi** v editoru Lens, export jako NDJSON do `results/`,
  automatický import při startu. Každá vizualizace jiný typ, min. 4 grafy + 1 heatmapa
  (kategoriální × kategoriální × metrika).

### Obsah GIT repozitáře (základní struktura je předpřipravená)

```
1 - NoSQL technologie/
  data/                 (datové soubory, Jupyter notebook, requirements.txt)
  docker-compose.yml
  HOWTO.md
  queries.txt
  scripts/              (init skripty, check.sh)
  README.md             (Úvod, Architektura, Specifika konfigurace, Případ užití,
                          Výhody a nevýhody, CAP/PACELC, Další specifika, Dataset,
                          Závěr, Prohlášení o použití AI, Zdroje)
2 - Elastic Stack/
  data/
  docker-compose.yml
  elk/                   (elasticsearch/, kibana/, logstash/ config + pipeline + template + setup + queries)
  HOWTO.md
  README.md              (Úvod, Data, Konfigurace, Dotazy, Vizualizace, Závěr,
                           Prohlášení o použití AI, Zdroje)
  results/                (NDJSON export + obrázky vizualizací, HOWTO.md, README.md)
README.md                 (základní info o adresáři)
.env.example (v obou částech)
.gitignore (min. .env)
```

---

## Obhajoba

Povinná, v zadaných termínech (samotné odevzdání nestačí). Písemný test, 10 otázek nad
vlastním odevzdaným řešením (architektura, konfigurace, datové toky, zabezpečení, chování
při výpadku, data, dotazy, vizualizace). Odpovědi musí vycházet z konkrétního řešení
(skutečné názvy služeb/polí/indexů), obecná odpověď se nepočítá. Ukázkové otázky jsou na
stránce kurzu.

## Hodnocení

Povinné, ale 0 bodů (bez nich práce není úplná): Docker Compose požadavky, HOWTO.md +
check skript, popis docker-compose.yml, Python analýza v obou částech, Úvod/Závěr/Další
specifika, Prohlášení o AI, zdroje.

1. část (25 b): architektura 0–2,5, specifika konfigurace 0–10, případ užití 0–1, výhody/
nevýhody 0–1, CAP/PACELC 0–0,5, dotazy 0–10 (z toho cluster dotazy max 2,5).

2. část (25 b): data 0–5, import 0–2, načtení do indexu 0–2, dotazy (Query DSL + ES|QL) 0–3,
vizualizace 0–8 (heatmapa max 2, grafy max 4, tabulky max 1,5, propojení v dashboardu max
0,5), popis práce 0–5.
