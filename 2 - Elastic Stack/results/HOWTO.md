# HOWTO — Import a správa vizualizací v Kibaně

Tento dokument popisuje způsoby importu a ověření dashboardu a vizualizací v Kibaně.

---

## 1. Automatický import (výchozí)

Při spuštění projektu příkazem `docker compose up -d` se dashboard a všech 8 vizualizací naimportují **zcela automaticky** prostřednictvím pomocné služby `kibana-import`.

Služba `kibana-import`:
1. Počká na plnou připravenost Kibany (`http://kibana:5601/api/status`).
2. Odešle HTTP požadavek na Kibana Saved Objects API:
   ```bash
   curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
     -u "elastic:${ELASTIC_PASSWORD}" \
     -H "kbn-xsrf: true" \
     --form file=@results/dashboard_export.ndjson
   ```
3. Zkontroluje návratový kód (`success: true`) a ukončí se.

---

## 2. Manuální import přes webové rozhraní Kibany

Pokud si přejete dashboard naimportovat ručně přes webový prohlížeč:

1. Otevřete prohlížeč a přejděte na adresu: `http://localhost:5601`
2. Přihlaste se jako uživatel `elastic` s heslem z `.env` (`ElasticSuperSecretAdminPassword2026!`).
3. V levém navigačním menu rozklikněte **Management** → **Stack Management**.
4. V sekci **Kibana** zvolte **Saved Objects**.
5. V pravém horním rohu klikněte na tlačítko **Import**.
6. Přetáhněte nebo vyberte soubor `results/dashboard_export.ndjson`.
7. Ponechte zaškrtnutou volbu **Automatically overwrite conflicts** a klikněte na **Import**.
8. Kliknutím na **Done** dokončete import.
9. V hlavním menu přejděte do **Analytics** → **Dashboard** a otevřete dashboard **CHMU - Pocasi a kvalita ovzdusi v CR**.

---

## 3. Manuální export dashboardu

Chcete-li po případných úpravách exportovat aktuální verzi dashboardu zpět do repozitáře:

1. V **Stack Management** → **Saved Objects** vyhledejte objekt s názvem `CHMU - Pocasi a kvalita ovzdusi v CR` (id `chmu-dashboard`).
2. Zaškrtněte dashboard a v horní liště klikněte na **Export**.
3. Zaškrtněte volbu **Include related objects** (zahrne všech 8 vizualizací a 3 Data Views).
4. Klikněte na **Export** a uložený soubor přejmenujte na `dashboard_export.ndjson` v tomto adresáři `results/`.
