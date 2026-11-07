# HOWTO — Návod na zprovoznění a ověření (1. část: MongoDB sharded cluster)

Tento dokument popisuje přesný postup spuštění, konfigurace, ověření a testování MongoDB sharded clusteru pro semestrální práci z předmětu NoSQL databáze (UHK).

---

## 1. Požadavky na systém

- **RAM**: Doporučeno **16 GB RAM** (minimálně 8 GB volné paměti pro Docker kontejnery). Cluster se skládá z 13 kontejnerů MongoDB (3× config server, 9× shard node, 1× mongos).
- **CPU / Architektura**: x86_64 nebo ARM64 (Apple Silicon). Obraz `mongo:8.3.11` je multi-arch.
- **Software**: Docker Engine 24+ a Docker Compose v2 (v souladu s Compose Specification).
- **Čas nastartování**:
  - První spuštění (stažení obrazu `mongo:8.3.11`, inicializace replik, registrace shardů a import 8 000 záznamů): **2 až 4 minuty**.
  - Opakované spuštění s existujícími volumes: **30 až 60 sekund**.

---

## 2. Rychlé spuštění od začátku (jediným příkazem)

Otevřete terminál a přejděte do složky 1. části:

```bash
cd "1 - NoSQL technologie"

# Vytvoření konfiguračního souboru .env z přiloženého vzoru
cp .env.example .env
# Na Windows PowerShell: Copy-Item .env.example .env

# Spuštění celého clusteru a automatické inicializace
docker compose up -d
```

### Co se automaticky provede při startu:
1. Služba `key-init` vygeneruje zabezpečený sdílený autentizační soubor `mongo.key` s oprávněním `chmod 400` (vlastník `mongodb:mongodb`, UID 999) do Docker volume `keyfile-data`.
2. Nastartují se 3 config servery (`cfgrs`), 9 uzlů shardů (`shard1rs`, `shard2rs`, `shard3rs`) a query router `mongos1` — všechny s aktivním parametrem `--keyFile`.
3. Služby `configsvr-init` a `shard1-init`, `shard2-init`, `shard3-init` využijí localhost exception k inicializaci replikačních sad (`rs.initiate()`) a vytvoření root administrátora (`admin`) a aplikačního uživatele (`telemed_app`).
4. Služba `cluster-init` zaregistruje shardy na routeru `mongos1` (`sh.addShard()`) a povolí sharding pro databázi `telemedicina`.
5. Služba `data-import` vytvoří kolekce se striktní validací `$jsonSchema`, nakonfiguruje hashovaný shard key `{ patient_id: "hashed" }` pro kolekci `sensor_readings` a idempotentně naimportuje 500 pacientů, 8 000 odečtů a 800 intervencí.

---

## 3. Kontrolní seznam — Jak ověřit, že řešení běží správně

### Krok A: Kontrola stavu běžících kontejnerů
```bash
docker compose ps
```
Všechny databázové uzly (`configsvr1..3`, `shard1a..c`, `shard2a..c`, `shard3a..c`, `mongos1`) musí mít stav `Up (healthy)`. Jednorázové inicializační služby (`key-init`, `configsvr-init`, `shard*-init`, `cluster-init`, `data-import`) mají stav `Exited (0)`.

### Krok B: Spuštění automatického testovacího skriptu
Spusťte kontrolní skript uvnitř kontejneru:
```bash
docker compose run --rm check
```
Tento skript:
1. Zobrazí stav clusteru `sh.status()` — uvidíte 3 registrované shardy (`shard1rs`, `shard2rs`, `shard3rs`).
2. Vypíše počty záznamů v databázi `telemedicina`:
   - `patients: 500 dokumentů`
   - `sensor_readings: 8000 dokumentů`
   - `medical_interventions: 800 dokumentů`
3. Ověří rovnoměrné rozložení dat napříč shardy přes `$shardedDataDistribution`.
4. Otestuje přihlášení aplikačního uživatele `telemed_app` s omezenou rolí.

---

## 4. Připojení k databázi (mongosh)

### Připojení jako administrátor clusteru (přes mongos):
```bash
docker compose exec mongos1 mongosh -u admin -p ClusterSuperSecretAdminPassword2026! --authenticationDatabase admin
```

### Připojení jako aplikační uživatel (readWrite):
```bash
docker compose exec mongos1 mongosh -u telemed_app -p AppSecureVitalPass2026! --authenticationDatabase telemedicina
```

### Připojení z hostitelského stroje (např. MongoDB Compass):
Connection string:
```text
mongodb://admin:ClusterSuperSecretAdminPassword2026!@localhost:27017/telemedicina?authSource=admin
```

---

## 5. Spuštění dotazů z queries.txt

Všechny dotazy jsou uloženy v souboru `queries.txt`. Můžete je spouštět interaktivně v `mongosh` připojeném k routeru `mongos1`:
```bash
docker compose exec -i mongos1 mongosh -u admin -p ClusterSuperSecretAdminPassword2026! --authenticationDatabase admin < queries.txt
```

---

## 6. Spuštění Jupyter notebooku s analýzou dat

Analýza dat je připravena v souboru `data/analyza_dat.ipynb`.

```bash
cd data
pip install -r requirements.txt
jupyter notebook analyza_dat.ipynb
```
Notebook obsahuje popisné statistiky, kontrolu chybějících hodnot, ověření 100% referenční integrity a 2 grafy (distribuce vitálních funkcí a frekvence poplachů dle typu senzoru).

---

## 7. Čisté zastavení a restart (ověření čistého spuštění)

Pro ověření požadavku zadání na čisté spuštění od nuly:
```bash
# Zastavení a kompletní smazání všech svazků (volumes)
docker compose down -v

# Znovuspuštění na čistém prostředí
docker compose up -d

# Následná kontrola
docker compose run --rm check
```
Idempotence zajišťuje, že opakované spuštění bez `-v` zachová veškerá data a nepřepisuje již vytvořené entity.
