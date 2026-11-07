#!/usr/bin/env python3
"""
Generátor dat pro semestrální práci NoSQL (Elastic Stack).
Téma: Počasí a kvalita ovzduší v ČR (inspirováno otevřenými daty ČHMÚ).
Zajišťuje deterministickou reprodukovatelnost pomocí pevného náhodného seedu (SEED = 42).

Vytváří 3 kolekce, každá se 2 soubory (celkem 6 CSV souborů):
1. Kolekce stanice:
   - stanice_cechy.csv (20 stanic v Čechách)
   - stanice_morava.csv (20 stanic na Moravě a ve Slezsku)
2. Kolekce meteo_mereni:
   - meteo_mereni_2023.csv (6 000 záznamů)
   - meteo_mereni_2024.csv (6 000 záznamů)
3. Kolekce kvalita_ovzdusi:
   - kvalita_ovzdusi_2023.csv (6 000 záznamů)
   - kvalita_ovzdusi_2024.csv (6 000 záznamů)
"""

import csv
import math
import os
import random
from datetime import datetime, timedelta

SEED = 42
random.seed(SEED)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

STATIONS_CECHY = [
    {"station_id": "PHA-LIB", "station_name": "Praha 8-Libeň", "region": "Hlavní město Praha", "district": "Praha", "city": "Praha", "elevation": 195, "latitude": 50.1064, "longitude": 14.4756, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "PHA-SMO", "station_name": "Praha 5-Smíchov", "region": "Hlavní město Praha", "district": "Praha", "city": "Praha", "elevation": 205, "latitude": 50.0712, "longitude": 14.4047, "station_type": "dopravní", "owner": "ČHMÚ"},
    {"station_id": "PHA-KOB", "station_name": "Praha 8-Kobylisy", "region": "Hlavní město Praha", "district": "Praha", "city": "Praha", "elevation": 280, "latitude": 50.1258, "longitude": 14.4533, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "PHA-REP", "station_name": "Praha 6-Řepy", "region": "Hlavní město Praha", "district": "Praha", "city": "Praha", "elevation": 360, "latitude": 50.0655, "longitude": 14.2989, "station_type": "předměstská", "owner": "ČHMÚ"},
    {"station_id": "HK-SAL", "station_name": "Hradec Králové-Sukovy sady", "region": "Královéhradecký", "district": "Hradec Králové", "city": "Hradec Králové", "elevation": 235, "latitude": 50.2104, "longitude": 15.8252, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "HK-TRE", "station_name": "Hradec Králové-Třebeš", "region": "Královéhradecký", "district": "Hradec Králové", "city": "Hradec Králové", "elevation": 240, "latitude": 50.1856, "longitude": 15.8341, "station_type": "předměstská", "owner": "ČHMÚ"},
    {"station_id": "PCE-POL", "station_name": "Pardubice-Polabiny", "region": "Pardubický", "district": "Pardubice", "city": "Pardubice", "elevation": 218, "latitude": 50.0461, "longitude": 15.7602, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "PCE-DUK", "station_name": "Pardubice-Dukla", "region": "Pardubický", "district": "Pardubice", "city": "Pardubice", "elevation": 222, "latitude": 50.0253, "longitude": 15.7658, "station_type": "dopravní", "owner": "ČHMÚ"},
    {"station_id": "PLZ-SLO", "station_name": "Plzeň-Slovany", "region": "Plzeňský", "district": "Plzeň-město", "city": "Plzeň", "elevation": 326, "latitude": 49.7342, "longitude": 13.3986, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "PLZ-KRH", "station_name": "Plzeň-Koterovská", "region": "Plzeňský", "district": "Plzeň-město", "city": "Plzeň", "elevation": 335, "latitude": 49.7301, "longitude": 13.4112, "station_type": "dopravní", "owner": "ČHMÚ"},
    {"station_id": "UST-MES", "station_name": "Ústí nad Labem-město", "region": "Ústecký", "district": "Ústí nad Labem", "city": "Ústí nad Labem", "elevation": 150, "latitude": 50.6607, "longitude": 14.0322, "station_type": "průmyslová", "owner": "ČHMÚ"},
    {"station_id": "UST-VSE", "station_name": "Ústí nad Labem-Všebořice", "region": "Ústecký", "district": "Ústí nad Labem", "city": "Ústí nad Labem", "elevation": 280, "latitude": 50.6841, "longitude": 13.9984, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "LIB-VRA", "station_name": "Liberec-Vratislavice", "region": "Liberecký", "district": "Liberec", "city": "Liberec", "elevation": 380, "latitude": 50.7423, "longitude": 15.0901, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "LIB-SEV", "station_name": "Liberec-Sever", "region": "Liberecký", "district": "Liberec", "city": "Liberec", "elevation": 410, "latitude": 50.7812, "longitude": 15.0534, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "CB-ANT", "station_name": "České Budějovice-Antala Staška", "region": "Jihočeský", "district": "České Budějovice", "city": "České Budějovice", "elevation": 395, "latitude": 48.9744, "longitude": 14.4697, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "CB-ROZ", "station_name": "České Budějovice-Rooseveltova", "region": "Jihočeský", "district": "České Budějovice", "city": "České Budějovice", "elevation": 392, "latitude": 48.9665, "longitude": 14.4821, "station_type": "dopravní", "owner": "ČHMÚ"},
    {"station_id": "KV-CER", "station_name": "Karlovy Vary-Čankovská", "region": "Karlovarský", "district": "Karlovy Vary", "city": "Karlovy Vary", "elevation": 385, "latitude": 50.2372, "longitude": 12.8622, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "KLA-SIT", "station_name": "Kladno-Švermov", "region": "Středočeský", "district": "Kladno", "city": "Kladno", "elevation": 315, "latitude": 50.1658, "longitude": 14.1084, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "PRI-KOV", "station_name": "Příbram-Kovohutě", "region": "Středočeský", "district": "Příbram", "city": "Příbram", "elevation": 470, "latitude": 49.6892, "longitude": 14.0103, "station_type": "průmyslová", "owner": "ČHMÚ"},
    {"station_id": "KRN-SER", "station_name": "Krkonoše-Šerlich", "region": "Královéhradecký", "district": "Rychnov nad Kněžnou", "city": "Deštné v Orlických horách", "elevation": 1019, "latitude": 50.3283, "longitude": 16.3811, "station_type": "venkovská pozaďová", "owner": "ČHMÚ"},
]

STATIONS_MORAVA = [
    {"station_id": "BRN-ZVO", "station_name": "Brno-Zvonařka", "region": "Jihomoravský", "district": "Brno-město", "city": "Brno", "elevation": 204, "latitude": 49.1869, "longitude": 16.6174, "station_type": "dopravní", "owner": "ČHMÚ"},
    {"station_id": "BRN-KRO", "station_name": "Brno-Kroftova", "region": "Jihomoravský", "district": "Brno-město", "city": "Brno", "elevation": 245, "latitude": 49.2155, "longitude": 16.5786, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "BRN-LIZ", "station_name": "Brno-Líšeň", "region": "Jihomoravský", "district": "Brno-město", "city": "Brno", "elevation": 310, "latitude": 49.2081, "longitude": 16.6912, "station_type": "předměstská", "owner": "ČHMÚ"},
    {"station_id": "BRN-SVA", "station_name": "Brno-Svatoplukova", "region": "Jihomoravský", "district": "Brno-město", "city": "Brno", "elevation": 215, "latitude": 49.2052, "longitude": 16.6433, "station_type": "dopravní", "owner": "ČHMÚ"},
    {"station_id": "OST-FIF", "station_name": "Ostrava-Fifejdy", "region": "Moravskoslezský", "district": "Ostrava-město", "city": "Ostrava", "elevation": 220, "latitude": 49.8353, "longitude": 18.2689, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "OST-RAD", "station_name": "Ostrava-Radvanice", "region": "Moravskoslezský", "district": "Ostrava-město", "city": "Ostrava", "elevation": 248, "latitude": 49.8164, "longitude": 18.3241, "station_type": "průmyslová", "owner": "ČHMÚ"},
    {"station_id": "OST-POR", "station_name": "Ostrava-Poruba", "region": "Moravskoslezský", "district": "Ostrava-město", "city": "Ostrava", "elevation": 240, "latitude": 49.8271, "longitude": 18.1633, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "OST-PRI", "station_name": "Ostrava-Přívoz", "region": "Moravskoslezský", "district": "Ostrava-město", "city": "Ostrava", "elevation": 208, "latitude": 49.8562, "longitude": 18.2711, "station_type": "průmyslová", "owner": "ČHMÚ"},
    {"station_id": "KAR-KOS", "station_name": "Karviná-město", "region": "Moravskoslezský", "district": "Karviná", "city": "Karviná", "elevation": 230, "latitude": 49.8550, "longitude": 18.5412, "station_type": "průmyslová", "owner": "ČHMÚ"},
    {"station_id": "HAV-ZEL", "station_name": "Havířov-střed", "region": "Moravskoslezský", "district": "Karviná", "city": "Havířov", "elevation": 260, "latitude": 49.7794, "longitude": 18.4382, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "TRIN-KO", "station_name": "Třinec-Kosmos", "region": "Moravskoslezský", "district": "Frýdek-Místek", "city": "Třinec", "elevation": 310, "latitude": 49.6753, "longitude": 18.6697, "station_type": "průmyslová", "owner": "ČHMÚ"},
    {"station_id": "FM-MIST", "station_name": "Frýdek-Místek", "region": "Moravskoslezský", "district": "Frýdek-Místek", "city": "Frýdek-Místek", "elevation": 290, "latitude": 49.6833, "longitude": 18.3512, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "OLO-HEJ", "station_name": "Olomouc-Hejčín", "region": "Olomoucký", "district": "Olomouc", "city": "Olomouc", "elevation": 215, "latitude": 49.6022, "longitude": 17.2425, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "OLO-VEL", "station_name": "Olomouc-Velkomoravská", "region": "Olomoucký", "district": "Olomouc", "city": "Olomouc", "elevation": 212, "latitude": 49.5843, "longitude": 17.2612, "station_type": "dopravní", "owner": "ČHMÚ"},
    {"station_id": "PRER-SE", "station_name": "Přerov-Velká Dlážka", "region": "Olomoucký", "district": "Přerov", "city": "Přerov", "elevation": 210, "latitude": 49.4608, "longitude": 17.4489, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "PROS-SI", "station_name": "Prostějov-Sídliště", "region": "Olomoucký", "district": "Prostějov", "city": "Prostějov", "elevation": 225, "latitude": 49.4715, "longitude": 17.1154, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "ZLI-KVT", "station_name": "Zlín-Kúty", "region": "Zlínský", "district": "Zlín", "city": "Zlín", "elevation": 235, "latitude": 49.2286, "longitude": 17.6791, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "UHE-HRD", "station_name": "Uherské Hradiště", "region": "Zlínský", "district": "Uherské Hradiště", "city": "Uherské Hradiště", "elevation": 180, "latitude": 49.0713, "longitude": 17.4611, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "JIH-TER", "station_name": "Jihlava-Terezie Brzkové", "region": "Kraj Vysočina", "district": "Jihlava", "city": "Jihlava", "elevation": 520, "latitude": 49.3961, "longitude": 15.5802, "station_type": "městská pozaďová", "owner": "ČHMÚ"},
    {"station_id": "JES-CER", "station_name": "Jeseník-Červenohorské sedlo", "region": "Olomoucký", "district": "Jeseník", "city": "Loučná nad Desnou", "elevation": 1013, "latitude": 50.1244, "longitude": 17.1539, "station_type": "venkovská pozaďová", "owner": "ČHMÚ"},
]

ALL_STATIONS = STATIONS_CECHY + STATIONS_MORAVA
STATION_MAP = {s["station_id"]: s for s in ALL_STATIONS}

def save_csv(filename, fieldnames, rows):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Uloženo {len(rows)} záznamů do {filename}")

def calculate_aqi(pm10, pm2_5, no2, o3):
    """
    Kalkulace Indexu kvality ovzduší dle metodiky ČHMÚ (1 - velmi dobrá až 6 - velmi špatná).
    """
    sub_indices = []
    # PM10 (1h / 24h meze: 0-20=1, 20-40=2, 40-70=3, 70-100=4, 100-150=5, >150=6)
    if pm10 < 20: sub_indices.append(1)
    elif pm10 < 40: sub_indices.append(2)
    elif pm10 < 70: sub_indices.append(3)
    elif pm10 < 100: sub_indices.append(4)
    elif pm10 < 150: sub_indices.append(5)
    else: sub_indices.append(6)

    # PM2.5 (0-10=1, 10-25=2, 25-40=3, 40-60=4, 60-100=5, >100=6)
    if pm2_5 < 10: sub_indices.append(1)
    elif pm2_5 < 25: sub_indices.append(2)
    elif pm2_5 < 40: sub_indices.append(3)
    elif pm2_5 < 60: sub_indices.append(4)
    elif pm2_5 < 100: sub_indices.append(5)
    else: sub_indices.append(6)

    # NO2 (0-25=1, 25-50=2, 50-100=3, 100-150=4, 150-200=5, >200=6)
    if no2 < 25: sub_indices.append(1)
    elif no2 < 50: sub_indices.append(2)
    elif no2 < 100: sub_indices.append(3)
    elif no2 < 150: sub_indices.append(4)
    elif no2 < 200: sub_indices.append(5)
    else: sub_indices.append(6)

    # O3 (0-33=1, 33-65=2, 65-120=3, 120-180=4, 180-240=5, >240=6)
    if o3 < 33: sub_indices.append(1)
    elif o3 < 65: sub_indices.append(2)
    elif o3 < 120: sub_indices.append(3)
    elif o3 < 180: sub_indices.append(4)
    elif o3 < 240: sub_indices.append(5)
    else: sub_indices.append(6)

    return max(sub_indices)

def generate_year_data(year, num_records=6000):
    meteo_records = []
    air_records = []
    
    start_date = datetime(year, 1, 1, 0, 0, 0)
    
    # Stanice vybereme náhodně s opakováním napříč celým rokem
    # Každý časový bod odpovídá měření na jedné stanici
    for i in range(1, num_records + 1):
        station = random.choice(ALL_STATIONS)
        station_id = station["station_id"]
        station_type = station["station_type"]
        elevation = station["elevation"]
        
        # Náhodný čas v průběhu roku
        day_of_year = random.randint(0, 364)
        hour = random.randint(0, 23)
        minute = 0
        current_time = start_date + timedelta(days=day_of_year, hours=hour, minutes=minute)
        ts_str = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # --- FYZIKÁLNĚ KORELOVANÉ METEO HODNOTY ---
        # Sezónní sinusový průběh teploty (červenec maximum, leden minimum)
        season_phase = 2 * math.pi * (day_of_year - 20) / 365.0
        base_temp = 9.5 + 11.5 * math.sin(season_phase)
        
        # Denní cyklus (odpoledne tepleji, k ránu chladněji)
        diurnal_cycle = 4.0 * math.sin(2 * math.pi * (hour - 8) / 24.0)
        
        # Vliv nadmořské výšky: -0.65 °C na 100 m
        elev_effect = -((elevation - 200) / 100.0) * 0.65
        
        # Šum
        noise_temp = random.gauss(0, 2.5)
        temperature = round(base_temp + diurnal_cycle + elev_effect + noise_temp, 1)
        
        # Rychlost a směr větru
        wind_speed = round(max(0.3, random.gauss(3.5, 2.0) + (1.5 if elevation > 500 else 0)), 1)
        wind_direction = random.randint(0, 360)
        
        # Tlak vzduchu (závislý na nadmořské výšce)
        base_pressure = 1013.25 * math.exp(-elevation / 8400.0)
        pressure = round(base_pressure + random.gauss(0, 6.0), 1)
        
        # Srážky a vlhkost
        is_raining = random.random() < 0.18
        if is_raining:
            precipitation = round(random.exponential(2.5) if hasattr(random, "exponential") else random.expovariate(1/2.5), 1)
            precipitation = min(35.0, precipitation)
            relative_humidity = round(min(100.0, max(75.0, random.gauss(88.0, 6.0))), 1)
            weather_condition = "sněžení" if temperature < 0 else "déšť"
        else:
            precipitation = 0.0
            rh_base = 72.0 - (temperature * 0.8) # v létě při vyšších teplotách nižší rel. vlhkost
            relative_humidity = round(min(98.0, max(28.0, rh_base + random.gauss(0, 10.0))), 1)
            if relative_humidity > 80:
                weather_condition = "zataženo"
            elif relative_humidity > 60:
                weather_condition = "oblačno"
            elif relative_humidity > 45:
                weather_condition = "polojasno"
            else:
                weather_condition = "jasno"

        met_id = f"MET-{year}-{i:06d}"
        meteo_records.append({
            "measurement_id": met_id,
            "station_id": station_id,
            "timestamp": ts_str,
            "temperature": temperature,
            "relative_humidity": relative_humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "precipitation": precipitation,
            "weather_condition": weather_condition,
        })
        
        # --- KORELOVANÁ KVALITA OVZDUŠÍ ---
        # Faktory znečištění:
        # 1. Typ stanice: průmyslová a dopravní mají vyšší emise
        station_bias = 1.0
        if station_type == "průmyslová": station_bias = 1.85
        elif station_type == "dopravní": station_bias = 1.55
        elif station_type == "městská pozaďová": station_bias = 1.15
        elif station_type == "venkovská pozaďová": station_bias = 0.45
        
        # 2. Teplotní inverze a rozptylové podmínky (zima + nízký vítr = vysoké PM)
        is_inversion = (temperature < 4.0 and wind_speed < 1.8)
        inversion_mult = 2.4 if is_inversion else 1.0
        
        # PM10 a PM2.5
        base_pm10 = (16.0 + 8.0 * math.cos(season_phase)) * station_bias * inversion_mult
        pm10 = round(max(3.0, random.gauss(base_pm10, base_pm10 * 0.25)), 1)
        pm2_5_ratio = random.uniform(0.62, 0.78)
        pm2_5 = round(max(2.0, pm10 * pm2_5_ratio), 1)
        
        # NO2 (hlavně doprava a průmysl, dopravní špičky ráno a odpoledne)
        rush_hour_boost = 1.4 if (7 <= hour <= 9 or 16 <= hour <= 19) else 1.0
        base_no2 = 18.0 * (2.2 if station_type == "dopravní" else station_bias) * rush_hour_boost
        no2 = round(max(4.0, random.gauss(base_no2, base_no2 * 0.22)), 1)
        
        # SO2 (průmyslová zátěž a zimní vytápění uhlím)
        so2_heat = 1.6 if temperature < 5.0 else 1.0
        base_so2 = 6.0 * (2.5 if station_type == "průmyslová" else 1.0) * so2_heat
        so2 = round(max(1.0, random.gauss(base_so2, 3.0)), 1)
        
        # O3 (přízemní ozon vzniká fotochemicky při vysoké teplotě a slunci v létě)
        if temperature > 18.0 and 11 <= hour <= 17 and not is_raining:
            o3_base = 70.0 + (temperature - 18.0) * 3.5
        else:
            o3_base = max(15.0, 42.0 - (no2 * 0.25))
        o3 = round(max(5.0, random.gauss(o3_base, 10.0)), 1)
        
        # Index kvality ovzduší a varování před smogem
        aqi_index = calculate_aqi(pm10, pm2_5, no2, o3)
        if aqi_index >= 6 or pm10 > 150.0:
            smog_warning = "regulace"
        elif aqi_index >= 5 or pm10 > 100.0:
            smog_warning = "upozorneni"
        else:
            smog_warning = "normal"
            
        aq_id = f"AQ-{year}-{i:06d}"
        air_records.append({
            "measurement_id": aq_id,
            "station_id": station_id,
            "timestamp": ts_str,
            "pm10": pm10,
            "pm2_5": pm2_5,
            "no2": no2,
            "so2": so2,
            "o3": o3,
            "aqi_index": aqi_index,
            "smog_warning": smog_warning,
        })
        
    return meteo_records, air_records

def main():
    print("Spouštím generování dat ČHMÚ...")
    
    # 1. Kolekce stanic
    station_fields = ["station_id", "station_name", "region", "district", "city", "elevation", "latitude", "longitude", "station_type", "owner"]
    save_csv("stanice_cechy.csv", station_fields, STATIONS_CECHY)
    save_csv("stanice_morava.csv", station_fields, STATIONS_MORAVA)
    
    # 2. Kolekce meteo měření a 3. Kolekce kvalita ovzduší pro rok 2023 (6 000 záznamů)
    meteo_fields = ["measurement_id", "station_id", "timestamp", "temperature", "relative_humidity", "pressure", "wind_speed", "wind_direction", "precipitation", "weather_condition"]
    air_fields = ["measurement_id", "station_id", "timestamp", "pm10", "pm2_5", "no2", "so2", "o3", "aqi_index", "smog_warning"]
    
    meteo_2023, air_2023 = generate_year_data(2023, 6000)
    save_csv("meteo_mereni_2023.csv", meteo_fields, meteo_2023)
    save_csv("kvalita_ovzdusi_2023.csv", air_fields, air_2023)
    
    # 3. Měření pro rok 2024 (6 000 záznamů)
    meteo_2024, air_2024 = generate_year_data(2024, 6000)
    save_csv("meteo_mereni_2024.csv", meteo_fields, meteo_2024)
    save_csv("kvalita_ovzdusi_2024.csv", air_fields, air_2024)
    
    print("\nVšechna data byla úspěšně vygenerována:")
    print("  - 2 soubory stanic (Čechy: 20, Morava: 20)")
    print("  - 2 soubory meteo měření (2023: 6 000, 2024: 6 000)")
    print("  - 2 soubory kvality ovzduší (2023: 6 000, 2024: 6 000)")
    print("  - Celkem 24 040 záznamů ve 3 kolekcích (6 souborů).")

if __name__ == "__main__":
    main()
