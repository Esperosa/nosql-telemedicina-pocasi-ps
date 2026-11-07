# 1. část — MongoDB (sharded cluster)

Semestrální práce z předmětu NoSQL databáze (NOSQL), Univerzita Hradec Králové.

---

## Úvod

Tématem této práce je **telemedicínský systém pro vzdálené kontinuální monitorování pacientů a sběr telemetrických dat z IoT biosenzorů** (náramkové monitory, EKG náplasti, kontinuální glukometry a pulzní oxymetry).

Čtenář se v tomto dokumentu dozví:
- Jak navrhnout, nasadit a zabezpečit plnohodnotný **MongoDB sharded cluster** podle minimální povinné topologie ze zadání (3 config servery v replikační sadě `cfgrs`, 3 shardy po 3 replikách `shard1rs`, `shard2rs`, `shard3rs` a dotazovací router `mongos1`).
- Jak realizovat interní autentizaci mezi uzly pomocí kryptografického **keyfile** generovaného automaticky při startu do Docker volume (bezpečnost bez úniku tajných klíčů do verzovacího systému Git) a autorizaci přístupu (RBAC) s rolí root administrátora a aplikačního uživatele s omezenými právy.
- Jak zvolit a obhájit **shard key** pro telemetrická data z hlediska kardinality, frekvence a monotónnosti a jak ověřit rovnoměrnou distribuci dat pomocí diagnostických příkazů `analyzeShardKey` a `$shardedDataDistribution`.
- Jak zajistit integritu databáze pomocí formálních validačních pravidel **$jsonSchema**.
- Jak nad rozsáhlým datasetem (8 000 odečtů, 500 pacientů, 800 intervencí) provádět netriviální analytické dotazy, korelace přes `$lookup`, okenní funkce `$setWindowFields`, segmentaci `$bucket`, vícerozměrné agregace `$facet` a distribuované ACID transakce napříč shardy.

**Co záměrně NENÍ součástí práce a proč:**
- **TLS/SSL šifrování na transportní vrstvě**: V rámci lokálního vývojového a testovacího prostředí běžícího na privátní Docker síti (Docker bridge) je komunikace izolována od vnějšího internetu. Zavedení plné PKI infrastruktury s certifikační autoritou by neúměrně zvýšilo režii lokálního běhu a nebylo požadováno zadáním (zadání výslovně předepisuje keyFile autentizaci).
- **Multi-datacenter replikace (geografická distribuce)**: Všech 13 uzlů běží v rámci jednoho hostitele v Docker Compose z důvodu hardwarových limitů studentského počítače (16 GB RAM).
- **Externí monitorovací agenti (MongoDB Ops Manager / Prometheus exporter)**: Metriky a diagnostika jsou sledovány přímo nativními příkazy databázového jádra (`$shardedDataDistribution`, `serverStatus`, `rs.status()`, `db.stats()`).

---

## a) Architektura

Topologie je navržena přesně podle povinné minimální konfigurace pro MongoDB sharded cluster:

```
                                  +-------------------+
                                  |   Klient / Aplikace|
                                  | (mongosh / Python)|
                                  +---------+---------+
                                            |
                                   port 27017 (auth)
                                            v
                                  +-------------------+
                                  |      mongos1      |
                                  |   (Query Router)  |
                                  +----+----+----+----+
                                       |    |    |
           +---------------------------+    |    +---------------------------+
           |                                |                                |
           v                                v                                v
+----------------------+        +----------------------+        +----------------------+
|   Config Replica Set |        |     Shard 1 Set      |        |     Shard 2 Set      |
|       "cfgrs"        |        |      "shard1rs"      |        |      "shard2rs"      |
|  (Metadata & Auth)   |        |    (Data 33.4 %)     |        |    (Data 33.2 %)     |
+----------------------+        +----------------------+        +----------------------+
| configsvr1 (PRIMARY) |        | shard1a (PRIMARY)    |        | shard2a (PRIMARY)    |
| configsvr2 (SEC)     |        | shard1b (SECONDARY)  |        | shard2b (SECONDARY)  |
| configsvr3 (SEC)     |        | shard1c (SECONDARY)  |        | shard2c (SECONDARY)  |
+----------------------+        +----------------------+        +----------------------+
           |                                |
           |                    +-----------+----------+
           |                    |
           v                    v
+------------------------------------------------------+
|                     Shard 3 Set                      |
|                      "shard3rs"                      |
|                    (Data 33.4 %)                     |
+------------------------------------------------------+
| shard3a (PRIMARY)                                    |
| shard3b (SECONDARY)                                  |
| shard3c (SECONDARY)                                  |
+------------------------------------------------------+
```

### Přehled kontejnerů a služeb v `docker-compose.yml`:
1. **`key-init`**: Jednorázová inicializační služba (`mongo:8.3.11`, spuštěna jako root). Před startem jakéhokoliv databázového uzlu zkontroluje, zda existuje interní autentizační klíč. Pokud ne, vygeneruje kryptograficky bezpečný klíč pomocí `openssl rand -base64 756 > /data/keyfile/mongo.key`, nastaví striktní oprávnění `chmod 400` a vlastníka `999:999` (`mongodb:mongodb`). Klíč je uložen v pojmenovaném svazku `keyfile-data`, který je připojen do všech databázových uzlů pouze pro čtení (`:ro`).
2. **Config Servery (`configsvr1`, `configsvr2`, `configsvr3`)**: 3členná replikační sada `cfgrs` běžící na portu `27019` s parametrem `--configsvr`. Spravuje metadata clusteru, směrovací tabulky chunků a centrální databázi uživatelů `admin.system.users`.
3. **`configsvr-init`**: Inicializuje replikační sadu `cfgrs` přes localhost exception (`network_mode: "service:configsvr1"`), počká na zvolení PRIMARY uzlu a vytvoří uživatele:
   - Root administrátora: `admin` s rolí `root` na databázi `admin`.
   - Aplikačního uživatele: `telemed_app` s rolí `readWrite` na databázi `telemedicina` a `clusterMonitor` na `admin`.
4. **Shardy (`shard1a..c`, `shard2a..c`, `shard3a..c`)**: Tři nezávislé replikační sady po 3 uzlech (`shard1rs`, `shard2rs`, `shard3rs`), celkem 9 uzlů běžících na portu `27018` s parametrem `--shardsvr`.
5. **Init služby shardů (`shard1-init`, `shard2-init`, `shard3-init`)**: Inicializují příslušnou replikační sadu shardu a vytvoří lokálního root administrátora přes localhost exception.
6. **Query Router (`mongos1`)**: Běží na portu `27017` s parametrem `--configdb cfgrs/...` a `--keyFile`. Zajišťuje transparentní směrování klientských dotazů na příslušné shardy na základě shard key.
7. **`cluster-init`**: Autentizuje se na `mongos1` jako administrátor, zaregistruje všechny 3 shardy (`sh.addShard()`) a povolí sharding pro databázi `telemedicina`.
8. **`data-import`**: Připojí se k `mongos1`, definuje validační schémata `$jsonSchema`, vytvoří hashovaný shard key `{ patient_id: "hashed" }` a idempotentně naimportuje data ze složky `data/`.
9. **`check`**: Kontrolní diagnostický kontejner spouštěný ručně příkazem `docker compose run --rm check`.

---

## b) Specifika konfigurace

- **Cluster**: 1 sharded cluster propojený přes konfigurační sadu `cfgrs`.
- **Uzly**: Celkem 13 běžících instancí `mongo:8.3.11` (3 config servery + 9 shard nodů + 1 mongos router).
- **Sharding**: 3 shardy (`shard1rs`, `shard2rs`, `shard3rs`). Hlavní telemetrická kolekce `sensor_readings` je shardována pomocí hashovaného klíče `{ patient_id: "hashed" }`.
  - **Zdůvodnění shard key**:
    1. *Kardinalita*: Pole `patient_id` obsahuje 500 unikátních hodnot (`PAT-0001` až `PAT-0500`), což poskytuje dostatečný počet unikátních hodnot pro jemné rozdělení na chunky.
    2. *Frekvence*: Každý aktivní pacient generuje průběžné odečty (průměrně 16 odečtů na pacienta v datasetu). Žádný pacient netvoří více než 1 % celkového objemu dat.
    3. *Monotónnost*: Kdybychom shardovali podle časové značky `timestamp`, šlo by o striktně monotónně rostoucí klíč. Všechny nové zápisy z IoT senzorů by směřovaly na jediný shard (tzv. *monolithic write bottleneck*). Použitím **hashovaného klíče** MongoDB spočte pseudonáhodný MD5 hash z `patient_id`, čímž se zápisy nových dat rovnoměrně rozptýlí mezi všechny 3 shardy.
    4. *Lokalita dotazů na pacienta*: Dotazy filtrované podle `patient_id` (např. zobrazení karty konkrétního pacienta lékařem) jsou směrovány přímo na konkrétní shard (*targeted query*), protože router `mongos` spočte hash a ví přesně, na kterém shardu data leží.
- **Replikace**: Každý shard i config server má 3 repliky (1 PRIMARY + 2 SECONDARY), což garantuje toleranci vůči výpadku 1 uzlu v libovolné replikační sadě bez přerušení provozu.
- **Perzistence dat**: Každý uzel má svůj dedikovaný pojmenovaný Docker volume (např. `shard1a-data:/data/db`), data tedy přežijí restart kontejnerů.
- **Zabezpečení (Autentizace a Autorizace)**:
  - Interní komunikace mezi všemi uzly clusteru (mongos, config servery, shard servery) je zabezpečena pomocí sdíleného kryptografického klíče (`--keyFile /data/keyfile/mongo.key`).
  - Klíč je generován při prvním spuštění službou `key-init` do svazku `keyfile-data`, nikdy se neukládá v repozitáři (soubory klíčů jsou v `.gitignore`).
  - Nastavení oprávnění je striktně `chmod 400` s vlastníkem `mongodb:mongodb` (UID 999).
  - Řízení přístupu (RBAC):
    - Uživatel `admin` s rolí `root` na databázi `admin` pro správu clusteru.
    - Uživatel `telemed_app` s rolí `readWrite` na databázi `telemedicina` a `clusterMonitor` na `admin` pro provoz klientské aplikace a čtení telemetrie bez zbytečných administrátorských privilegií.
  - Všechna hesla a porty jsou konfigurovány výhradně přes proměnné prostředí v `.env` (v repozitáři je pouze vzor `.env.example`).
- **Distribuce dat**: Zjištěno dotazem `$shardedDataDistribution`:
  - `shard1rs`: 2 674 dokumentů (1,31 MB) — 33,4 %
  - `shard2rs`: 2 658 dokumentů (1,30 MB) — 33,2 %
  - `shard3rs`: 2 668 dokumentů (1,31 MB) — 33,4 %
  Rozdělení vykazuje dokonalou rovnoměrnost s odchylkou do 0,2 %.

---

## c) Případ užití

**Systém vzdáleného monitorování pacientů v domácí péči (Remote Patient Monitoring & Biosensor IoT Telemetry)**.

Proč byla pro tento účel zvolena dokumentová databáze MongoDB v sharded architektuře:
1. **Semi-strukturovaná telemetrická data**: Různé typy biosenzorů (náramkové monitory, EKG svody, kontinuální glukometry, pulzní oxymetry) měří odlišné sady fyziologických parametrů. Dokumentový model BSON umožňuje ukládat polymorfní vnořené objekty (`vitals`) bez nutnosti řídkých tabulek s desítkami prázdných NULL sloupců v relačních databázích.
2. **Vysoká propustnost zápisů (Write Scalability)**: Stovky pacientů se senzory odesílají telemetrické odečty v krátkých intervalech. Díky horizontálnímu shardingu se zátěž zápisů rozkládá paralelně na 3 primární uzly jednotlivých shardů.
3. **Časové řady a okenní analýza**: Nativní podpora okenních agregačních operátorů (`$setWindowFields`) umožňuje přímo v databázovém stroji počítat plovoucí průměry vitálních funkcí, detekovat trendy a odhalovat arytmie v reálném čase.
4. **Distribuované transakce s vysokou integritou**: Při detekci život ohrožujícího stavu je nutné atomicky zapsat poplachový odečet, eskalovat status pacienta v kartotéce a vystavit žádanku o urgentní zásah v jedné multi-dokumentové transakci napříč shardy.

---

## d) Výhody a nevýhody

### Výhody nasazení MongoDB v této doméně:
- **Horizontální škálovatelnost bez výpadku**: Přidání nového shardu (`shard4rs`) do běžícího clusteru je otázkou jednoho příkazu `sh.addShard()`; balancer automaticky přerozdělí chunky bez přerušení čtení a zápisu.
- **Vysoká dostupnost (HA)**: Výpadek kteréhokoliv fyzického uzlu v replikační sadě je automaticky detekován a do 10 sekund je zvolen nový PRIMARY uzel. Klientská aplikace přes mongos router nepocítí výpadek.
- **Flexibilita schématu kombinovaná se zárukami ($jsonSchema)**: Umožňuje verzování datových struktur různých generací senzorů, přičemž striktní validační pravidla spolehlivě odmítnou fyziologicky nesmyslná data (např. záporný tlak nebo tep 500 bpm).
- **Výkonné agregační rozhraní**: Možnost realizovat komplexní analytické dotazy, korelace (`$lookup`), vícedimenzionální dashboardy (`$facet`) a segmentace (`$bucket`) přímo v databázi bez nutnosti tahat miliony surových dat do aplikační vrstvy.

### Nevýhody a úskalí:
- **Vysoké paměťové nároky (RAM overhead)**: Storage engine WiredTiger alokuje pro každý mongod proces významnou část RAM pro svou interní cache (ve výchozím stavu ~50 % volné RAM - 1 GB). Provoz 13 kontejnerů na jednom stroji vyžaduje alespoň 16 GB paměti.
- **Režie distribuovaných transakcí**: Dvoufázový commit (2PC) napříč shardy zavádí síťovou latenci a zámky. Distribuované transakce by se měly využívat pouze pro kritické klinické eskalace, ne pro běžný ingest dat.
- **Riziko neoptimálního shard key**: Špatná volba klíče (např. monotónní timestamp) vede k vytvoření jediného přetíženého shardu, přičemž změna shard key na živé produkční kolekci byla v minulosti extrémně obtížná.
- **Náročnost na správu a monitoring**: Sharded cluster vyžaduje dohled nad stavem balanceru, velikostí oplogu, replikačním zpožděním a dostupností config serverů.

---

## e) CAP teorém a PACELC

### CAP teorém:
V klasifikaci CAP teorému je MongoDB v sharded cluster konfiguraci **CP systém** (Consistency + Partition Tolerance):
- **Partition Tolerance (P)**: Cluster je navržen tak, aby spolehlivě fungoval i v případě síťového rozdělení (Network Partition).
- **Consistency (C) na úkor Availability (A)**: Pokud dojde k rozdělení sítě a uzel ztratí spojení s většinou replikační sady (např. menšinový segment 1 uzlu ze 3), uzel se vzdá role PRIMARY a přepne se do režimu SECONDARY. V menšinové partition **nejsou povoleny zápisy**. Systém upřednostní konzistenci před dostupností — odmítne přijímat zápisy v izolovaném segmentu, aby zabránil stavu *split-brain* a vzniku nekonzistentních větví historie.

### PACELC teorém:
PACELC rozšiřuje CAP o chování systému za normálního stavu bez výpadku sítě:
- **P / C**: *If Partitioned (P)* -> zvolena *Consistency (C)* nad *Availability (A)* (viz výše).
- **E / C (nebo E / L v závislosti na konfiguraci)**: *Else (E)* -> výchozí chování MongoDB při zápisu je upřednostnění **Konzistence (C)** před **Latencí (L)**:
  - Při použití výchozího potvrzení `writeConcern: { w: "majority" }` musí být zápis potvrzen většinou uzlů v replikační sadě (2 ze 3), než je klientovi vrácena odpověď OK. Klient platí vyšší latencí výměnou za garanci trvalosti dat i při havárii primárního uzlu.
  - V naší aplikaci je systém nakonfigurován diferencovaně:
    1. **Kritické zápisy (poplachy, změny medikace, transakce)**: `writeConcern: { w: "majority", j: true }` a `readConcern: "snapshot"` -> kategorie **PC / EC** (striktní konzistence jak při rozdělení, tak za běžného provozu).
    2. **Běžné čtení analytických přehledů a historie**: `readPreference: "secondaryPreferred"` s `causalConsistency: true` -> kategorie **PC / EL** (čtení je odbavováno ze sekundárních replik s minimální latencí, odlehčuje primární uzel).

### Pozorování a měření z dotazů (queries.txt):
- **Dotaz 3 (Simulace výpadku)**: Po zastavení primárního uzlu `shard1a` byl uzel `shard1b` automaticky zvolen novým PRIMARY za ~3 sekundy. Zápis s `w: "majority"` během výpadku úspěšně prošel, protože zbývající 2 uzly tvoří nadpoloviční většinu.
- **Dotaz 4 (Replikační zpoždění)**: Příkaz `rs.printSecondaryReplicationInfo()` naměřil zpoždění replikace 0 sekund za normálního provozu, což prokazuje, že sekundární uzly jsou prakticky synchronní.

---

## f) Další specifika vlastního řešení

1. **Striktní validace schématu ($jsonSchema)**:
   - Kolekce `patients`, `sensor_readings` a `medical_interventions` mají nastaveno `validationLevel: "strict"` a `validationAction: "error"`.
   - Všechny dokumenty jsou validovány na formát identifikátorů pomocí regulárních výrazů (`^PAT-[0-9]{4}$`, `^READ-[0-9]{7}$`, `^INT-[0-9]{5}$`), povolené číselníky přes `enum` a fyziologické rozsahy (tep 30–240 bpm, SpO2 50–100 %, tlak 50–260 mmHg). Nevalidní zápis je odmítnut chybou `DocumentValidationFailure` (kód 121, ověřeno v dotazu 14).
2. **Kombinované indexy**:
   - Vytvořen složený index `{ patient_id: 1, timestamp: -1 }` na kolekci `sensor_readings`, který umožňuje bleskové dotazování na historii měření pacienta v obráceném chronologickém pořadí.
   - Indexy na `{ alert_triggered: 1, alert_type: 1 }` pro real-time filtrování poplachů na dispečinku.
3. **Idempotentní import dat**:
   - Inicializační skript `mongo-init/import-data.sh` před importem kontroluje `countDocuments()`. Data jsou naimportována pouze tehdy, je-li kolekce prázdná, takže opakovaný start clusteru nezpůsobí duplicity ani chyby.

---

## Dataset

Data byla vygenerována syntetickým generátorem `data/generate_data.py` s **pevným náhodným seedem (SEED = 42)** pro zajištění 100% reprodukovatelnosti:

1. **`patients.json`**: 500 záznamů (264 KB)
   - Obsahuje demografické údaje, kontakty v 9 městech Královéhradeckého a Pardubického kraje, diagnózy dle MKN-10 (hypertenze, diabetes, astma, CHOPN, srdeční selhání), rizikové kategorie (LOW, MEDIUM, HIGH, CRITICAL) a přiřazené lékaře.
2. **`sensor_readings.json`**: **8 000 záznamů** (3,92 MB) — *hlavní kolekce (splňuje požadavek >= 5 000)*
   - Obsahuje telemetrické odečty ze 4 typů zařízení (náramkové monitory, EKG náplasti, glukometry, pulzní oxymetry) pokrývající období od ledna do dubna 2026. Zahrnuje tepovou frekvenci, systolický/diastolický tlak, SpO2, glykémii, tělesnou teplotu, stav baterie a automatickou klasifikaci poplachů.
3. **`medical_interventions.json`**: 800 záznamů (422 KB)
   - Obsahuje klinické záznamy lékařů, důvody zásahu, úpravy farmakoterapie (Ramipril, Metformin, Bisoprolol, Warfarin atd.), hospitalizace a plánované kontroly.

Všechny tři soubory jsou propojeny přes cizí klíč `patient_id`.

Analýza dat je zpracována v Jupyter notebooku **`data/analyza_dat.ipynb`** (ověřeny počty záznamů, datové typy, nulové chybějící hodnoty, popisné statistiky, 100% referenční integrita a 2 grafy). Knihovny jsou specifikovány v `data/requirements.txt`.

---

## Dotazy

Kompletní sada 15 netriviálních, číslovaných a vzájemně navazujících dotazů je podrobně popsána v souboru **`queries.txt`**. Každý dotaz obsahuje zadání v přirozeném jazyce, mongosh příkaz, reprezentativní konzolový výstup, vysvětlení chování a věcnou interpretaci:

1. **Dotaz 1**: Fyzická distribuce dat na shardy přes `$shardedDataDistribution` *(povinný dotaz pro MongoDB)*.
2. **Dotaz 2**: Diagnostika a hodnocení kvality shard key pomocí `analyzeShardKey`.
3. **Dotaz 3**: Simulace výpadku primárního uzlu shardu (Cluster Failover) — stavy PŘED, BĚHEM a PO obnově uzlu *(cluster dotaz)*.
4. **Dotaz 4**: Měření replikačního zpoždění a vyvážení čtení s `readPreference: "secondaryPreferred"` *(cluster dotaz)*.
5. **Dotaz 5**: Detekce kritických poplachů a korelace s pacienty pomocí `$lookup` joinu.
6. **Dotaz 6**: Vícedimenzionální analytický přehled monitoringu přes `$facet`.
7. **Dotaz 7**: Výpočet klouzavého průměru krevního tlaku a detekce trendů pomocí okenních funkcí `$setWindowFields`.
8. **Dotaz 8**: Automatická segmentace glykémie do klinických pásem pomocí operátoru `$bucket`.
9. **Dotaz 9**: Follow-up vyhodnocení klinického efektu lékařských intervencí na krevní tlak přes korelovaný `$lookup`.
10. **Dotaz 10**: Cirkadiánní profil poplachů v průběhu 24 hodin dne (ranní špička hypertenze).
11. **Dotaz 11**: Vyhodnocení pracovní zátěže lékařů a spádových oblastí.
12. **Dotaz 12**: Zařízení s nejčastějším záchytem kriticky nebezpečných hodnot podle pevných klinických mezí (bez statistiky).
13. **Dotaz 13**: Inkrementální materializace denního souhrnu pacientů pomocí `$merge`.
14. **Dotaz 14**: Ověření vynucování schématu `$jsonSchema` (test odmítnutí nevalidního dokumentu).
15. **Dotaz 15**: Distribuovaná multi-dokumentová ACID transakce napříč shardy s izolací `snapshot` a `w: "majority"`.

---

## Závěr


---

## Prohlášení o použití AI


---

## Zdroje

1. CHODOROW, Kristina. *MongoDB: The Definitive Guide: Powerful and Scalable Data Storage*. 3. vydání. O'Reilly Media, 2020. ISBN 978-1491954461.
2. COPE, G. *MongoDB Data Modeling and Architecture*. Packt Publishing, 2023. ISBN 978-1803248462.
3. MongoDB Documentation: *Sharded Cluster Architecture & Components*. [online]. Dostupné z: https://www.mongodb.com/docs/manual/core/sharded-cluster-components/
4. MongoDB Documentation: *Deploy Sharded Cluster with Keyfile Authentication*. [online]. Dostupné z: https://www.mongodb.com/docs/manual/tutorial/deploy-sharded-cluster-with-keyfile-access-control/
5. MongoDB Documentation: *Schema Validation using $jsonSchema*. [online]. Dostupné z: https://www.mongodb.com/docs/manual/core/schema-validation/specify-json-schema/
6. MongoDB Documentation: *Aggregations: $shardedDataDistribution*. [online]. Dostupné z: https://www.mongodb.com/docs/manual/reference/operator/aggregation/shardedDataDistribution/
7. Docker Documentation: *Compose Specification*. [online]. Dostupné z: https://docs.docker.com/compose/compose-file/
