# HOWTO — Návod na zprovoznění a ověření (2. část: Elastic Stack)

Tento dokument popisuje přesný postup spuštění, konfigurace, ověření a testování prostředí **Elastic Stack (ELK — Elasticsearch, Logstash, Kibana)** pro 2. část semestrální práce z předmětu NoSQL databáze (UHK).

---

## 1. Požadavky na systém

- **RAM**: Doporučeno **16 GB RAM** (minimálně 6–8 GB volné paměti pro Docker kontejnery).
  - Elasticsearch: JVM halda omezena na `-Xms1g -Xmx1g` (paměťový limit kontejneru 2 GB).
  - Logstash: JVM halda omezena na `-Xms512m -Xmx512m` (paměťový limit kontejneru 1 GB).
  - Kibana: paměťový limit kontejneru 1 GB.
- **CPU / Architektura**: x86_64 nebo ARM64 (Apple Silicon). Všechny oficiální obrazy Elastic verze 9.5.2 jsou multi-platformní.
- **Software**: Docker Engine 24+ a Docker Compose v2 (v souladu s Compose Specification, bez atributu `version`).
- **Čas nastartování**:
  - První spuštění (stažení obrazů 9.5.2, inicializace clusteru, vytvoření uživatelů a rolí, paralelní ingest 24 040 záznamů přes 6 pipeline a import dashboardu): **2 až 4 minuty**.
  - Opakované spuštění s existujícími volumes: **30 až 60 sekund**.

---

## 2. Rychlé spuštění od začátku (jediným příkazem)

Otevřete terminál a přejděte do složky 2. části:

```bash
cd "2 - Elastic Stack"

# Vytvoření konfiguračního souboru .env z přiloženého vzoru
cp .env.example .env
# Ve Windows PowerShell: Copy-Item .env.example .env

# Spuštění kompletního stacku na pozadí
docker compose up -d
```

### Co se automaticky provede při startu:
1. Nastartuje se uzel **Elasticsearch** v režimu single-node s aktivním X-Pack zabezpečením (`xpack.security.enabled=true`).
2. Služba **`setup`** vyčká na zdraví Elasticsearch (`condition: service_healthy`) a provede:
   - Nastavení hesla pro systémového uživatele `kibana_system`.
   - Vytvoření role `logstash_writer` s minimálními oprávněními výhradně k vlastním indexům (`stanice*`, `meteo_mereni*`, `kvalita_ovzdusi*`).
   - Vytvoření uživatele `logstash_internal` pro bezpečný příjem dat.
   - Registraci tří moderních **composable index templates** (`stanice_template`, `meteo_mereni_template`, `kvalita_ovzdusi_template`).
3. Nastartuje se **Logstash** a spustí 6 paralelních ETL pipelines definovaných v `pipelines.yml` (jedna pipeline na každý CSV soubor). Všech 24 040 záznamů je idempotentně zaindexováno pod svými ID.
4. Nastartuje se **Kibana** a po dosažení zdravého stavu služba **`kibana-import`** automaticky naimportuje Data Views, 8 vizualizací a analytický dashboard z `results/dashboard_export.ndjson`.

---

## 3. Kontrolní seznam — Jak ověřit, že řešení běží správně

### Krok A: Kontrola stavu běžících kontejnerů
```bash
docker compose ps
```
- Dlouhodobě běžící služby (`elasticsearch`, `kibana`, `logstash`) mají stav `Up (healthy)`.
- Jednorázové inicializační služby (`setup`, `kibana-import`) mají stav `Exited (0)`.

### Krok B: Spuštění automatického kontrolního skriptu
Spusťte kontrolní skript uvnitř kontejneru:
```bash
docker compose run --rm check
```
Tento skript automaticky ověří:
1. **Zdraví clusteru (`_cluster/health`)**: Vypíše stav `yellow` a zdůvodní, proč je stav yellow na 1-uzlovém clusteru s `number_of_replicas=1` očekávaný (repliky jsou ve stavu `UNASSIGNED`).
2. **Přehled indexů (`_cat/indices?v`)**: Vypíše všechny vytvořené indexy a jejich velikost.
3. **Počty dokumentů**:
   - `stanice`: **40** dokumentů (20 Čechy + 20 Morava)
   - `meteo_mereni-2023`: **6 000** dokumentů
   - `meteo_mereni-2024`: **6 000** dokumentů
   - `kvalita_ovzdusi-2023`: **6 000** dokumentů
   - `kvalita_ovzdusi-2024`: **6 000** dokumentů
   - **Celkem**: **24 040** dokumentů.
4. **Alokace shardů (`_cat/shards?v`)**: Zobrazí primární shardy jako `STARTED` na uzlu `elasticsearch` a repliky jako `UNASSIGNED`.
5. **RBAC oprávnění**: Ověří, že uživatel `logstash_internal` má přístup k aplikačním indexům a nemá přístup k systémovým indexům `.security*`.
6. **Dostupnost Kibany**: Ověří HTTP 200/302 odpověď.

---

## 4. Přístup k webovému rozhraní (Kibana)

- **URL**: `http://localhost:5601`
- **Uživatelské jméno**: `elastic`
- **Heslo**: hodnota z `.env` (`ElasticSuperSecretAdminPassword2026!`)

### Zobrazení naimportovaného dashboardu:
1. Po přihlášení klikněte v levém menu na **Analytics** → **Dashboard**.
2. Otevřete dashboard **"Kvalita ovzduší a meteorologická situace v ČR (ČHMÚ)"**.
3. Uvidíte všech 8 interaktivních vizualizací rozložených v mřížce (včetně povinné heatmapy).

---

## 5. Spuštění dotazů z queries.txt

Všechny dotazy (5 Query DSL + 1 ES|QL) jsou připraveny v souboru `elk/queries/queries.txt`.

### Možnost 1: V Kibana Dev Tools (doporučeno pro obhajobu)
1. V Kibaně přejděte v levém menu na **Management** → **Dev Tools** (Console).
2. Zkopírujte libovolný dotaz z `elk/queries/queries.txt` a klikněte na zelené tlačítko **Play** (Odeslat dotaz).

### Možnost 2: Přes REST API (curl z terminálu)
```bash
# Příklad: Spuštění dotazu 1 (filtr stanic v Jihomoravském kraji)
curl -s -u elastic:ElasticSuperSecretAdminPassword2026! \
  -H "Content-Type: application/json" \
  http://localhost:9200/stanice/_search \
  -d '{"query": {"term": {"region": "Jihomoravský"}}}'
```

---

## 6. Spuštění Jupyter notebooku s analýzou dat (EDA)

Notebook s průzkumovou analýzou dat je umístěn v `data/analyza_dat.ipynb`.

```bash
cd data
pip install -r requirements.txt
jupyter notebook analyza_dat.ipynb
```
Notebook obsahuje ověření požadavků zadání, popisné statistiky, kontrolu chybějících hodnot, ověření 100% referenční integrity napříč soubory a 2 analytické grafy (sezónní vliv teploty na PM10 a emisní zátěž podle typu stanice).

---

## 7. Čisté zastavení a restart (ověření požadavku na čisté spuštění)

Pro ověření požadavku zadání na čisté spuštění od nuly:

```bash
# Zastavení kontejnerů a smazání všech svazků (volumes)
docker compose down -v

# Znovuspuštění na čistém prostředí
docker compose up -d

# Následná kontrola
docker compose run --rm check
```
Idempotence celého řešení zajišťuje, že opakované spuštění `docker compose up -d` (bez `-v`) nikdy nezpůsobí chybu ani duplikaci zaindexovaných dat.
