import sqlite3
import random
import datetime
from database import get_connection, init_db

# 30 Realistic PHCs across key districts of Uttar Pradesh
PHCS_DATA = [
    # Varanasi District
    {"id": "PHC_VAR_01", "name": "PHC Varanasi Central (Shivpur)", "district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.3582, "lng": 82.9739, "beds": 12},
    {"id": "PHC_VAR_02", "name": "PHC Kashi Vidyapeeth", "district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.3176, "lng": 82.9873, "beds": 10},
    {"id": "PHC_VAR_03", "name": "PHC Pindra Rural", "district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.4851, "lng": 82.8122, "beds": 8},
    {"id": "PHC_VAR_04", "name": "PHC Cholapur Community", "district": "Varanasi", "state": "Uttar Pradesh", "lat": 25.4389, "lng": 83.0561, "beds": 10},
    
    # Prayagraj District
    {"id": "PHC_PRY_01", "name": "PHC Prayagraj North (Phaphamau)", "district": "Prayagraj", "state": "Uttar Pradesh", "lat": 25.5218, "lng": 81.8597, "beds": 12},
    {"id": "PHC_PRY_02", "name": "PHC Prayagraj East (Naini)", "district": "Prayagraj", "state": "Uttar Pradesh", "lat": 25.3850, "lng": 81.8682, "beds": 14},
    {"id": "PHC_PRY_03", "name": "PHC Soraon Rural", "district": "Prayagraj", "state": "Uttar Pradesh", "lat": 25.5891, "lng": 81.8499, "beds": 8},
    {"id": "PHC_PRY_04", "name": "PHC Karchhana Outpost", "district": "Prayagraj", "state": "Uttar Pradesh", "lat": 25.2917, "lng": 81.9360, "beds": 10},

    # Lucknow District
    {"id": "PHC_LKO_01", "name": "PHC Chinhat Metro", "district": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8795, "lng": 81.0267, "beds": 16},
    {"id": "PHC_LKO_02", "name": "PHC Kakori Semi-Urban", "district": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8722, "lng": 80.7938, "beds": 10},
    {"id": "PHC_LKO_03", "name": "PHC Mohanlalganj South", "district": "Lucknow", "state": "Uttar Pradesh", "lat": 26.6710, "lng": 80.9984, "beds": 12},
    {"id": "PHC_LKO_04", "name": "PHC Bakshi Ka Talab", "district": "Lucknow", "state": "Uttar Pradesh", "lat": 27.0142, "lng": 80.9192, "beds": 10},

    # Gorakhpur District
    {"id": "PHC_GKP_01", "name": "PHC Gorakhpur City North", "district": "Gorakhpur", "state": "Uttar Pradesh", "lat": 26.7606, "lng": 83.3732, "beds": 14},
    {"id": "PHC_GKP_02", "name": "PHC Bhathat Primary", "district": "Gorakhpur", "state": "Uttar Pradesh", "lat": 26.8523, "lng": 83.4831, "beds": 8},
    {"id": "PHC_GKP_03", "name": "PHC Sahjanwa Industrial", "district": "Gorakhpur", "state": "Uttar Pradesh", "lat": 26.7699, "lng": 83.1873, "beds": 10},

    # Kanpur Nagar
    {"id": "PHC_KNP_01", "name": "PHC Kalyanpur West", "district": "Kanpur", "state": "Uttar Pradesh", "lat": 26.4952, "lng": 80.2642, "beds": 15},
    {"id": "PHC_KNP_02", "name": "PHC Bithoor Riverside", "district": "Kanpur", "state": "Uttar Pradesh", "lat": 26.6133, "lng": 80.2741, "beds": 8},
    {"id": "PHC_KNP_03", "name": "PHC Ghatampur Rural", "district": "Kanpur", "state": "Uttar Pradesh", "lat": 26.1557, "lng": 80.1681, "beds": 10},

    # Ayodhya
    {"id": "PHC_AYD_01", "name": "PHC Ayodhya Dham Central", "district": "Ayodhya", "state": "Uttar Pradesh", "lat": 26.7922, "lng": 82.1998, "beds": 14},
    {"id": "PHC_AYD_02", "name": "PHC Sohawal Belt", "district": "Ayodhya", "state": "Uttar Pradesh", "lat": 26.7410, "lng": 82.0234, "beds": 8},
    {"id": "PHC_AYD_03", "name": "PHC Bikapur South", "district": "Ayodhya", "state": "Uttar Pradesh", "lat": 26.6021, "lng": 82.1389, "beds": 10},

    # Jhansi
    {"id": "PHC_JHN_01", "name": "PHC Jhansi Sadar", "district": "Jhansi", "state": "Uttar Pradesh", "lat": 25.4484, "lng": 78.5685, "beds": 12},
    {"id": "PHC_JHN_02", "name": "PHC Babina Cantonment", "district": "Jhansi", "state": "Uttar Pradesh", "lat": 25.2476, "lng": 78.4729, "beds": 8},

    # Agra
    {"id": "PHC_AGR_01", "name": "PHC Agra Cantt", "district": "Agra", "state": "Uttar Pradesh", "lat": 27.1574, "lng": 78.0081, "beds": 14},
    {"id": "PHC_AGR_02", "name": "PHC Fatehabad Rural", "district": "Agra", "state": "Uttar Pradesh", "lat": 27.0210, "lng": 78.3090, "beds": 8},

    # Meerut
    {"id": "PHC_MRT_01", "name": "PHC Meerut City South", "district": "Meerut", "state": "Uttar Pradesh", "lat": 28.9845, "lng": 77.7064, "beds": 14},
    {"id": "PHC_MRT_02", "name": "PHC Mawana Sub-District", "district": "Meerut", "state": "Uttar Pradesh", "lat": 29.1023, "lng": 77.9221, "beds": 10},

    # Bareilly
    {"id": "PHC_BRL_01", "name": "PHC Bareilly Civil Lines", "district": "Bareilly", "state": "Uttar Pradesh", "lat": 28.3670, "lng": 79.4304, "beds": 12},
    {"id": "PHC_BRL_02", "name": "PHC Faridpur Agricultural", "district": "Bareilly", "state": "Uttar Pradesh", "lat": 28.2110, "lng": 79.5440, "beds": 8},
]

MEDICINES_DATA = [
    {"id": "MED_AMOX", "name": "Amoxicillin 500mg", "category": "Antibiotics", "unit": "capsules"},
    {"id": "MED_PARA", "name": "Paracetamol 500mg", "category": "Analgesics & Antipyretics", "unit": "tablets"},
    {"id": "MED_ORS", "name": "Oral Rehydration Salts (ORS)", "category": "Electrolytes", "unit": "sachets"},
    {"id": "MED_AZI", "name": "Azithromycin 500mg", "category": "Antibiotics", "unit": "tablets"},
    {"id": "MED_METF", "name": "Metformin 500mg", "category": "Antidiabetic", "unit": "tablets"},
    {"id": "MED_AMLO", "name": "Amlodipine 5mg", "category": "Antihypertensive", "unit": "tablets"},
    {"id": "MED_IBUP", "name": "Ibuprofen 400mg", "category": "Analgesics & Anti-inflammatory", "unit": "tablets"},
    {"id": "MED_CEFT", "name": "Ceftriaxone 1g Injection", "category": "Injectables", "unit": "vials"},
    {"id": "MED_SALB", "name": "Salbutamol Inhaler 100mcg", "category": "Respiratory", "unit": "inhalers"},
    {"id": "MED_IFA", "name": "Iron & Folic Acid (IFA)", "category": "Nutritional Supplements", "unit": "tablets"},
    {"id": "MED_RAB", "name": "Anti-Rabies Vaccine", "category": "Vaccines & Biologicals", "unit": "vials"},
    {"id": "MED_ASV", "name": "Polyvalent Anti-Snake Venom", "category": "Emergency Antidotes", "unit": "vials"},
]

def seed_database():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing tables for fresh seed
    cursor.execute("DELETE FROM actions;")
    cursor.execute("DELETE FROM patients;")
    cursor.execute("DELETE FROM medicine_usage;")
    cursor.execute("DELETE FROM inventory;")
    cursor.execute("DELETE FROM medicines;")
    cursor.execute("DELETE FROM phcs;")

    # Insert PHCs
    for phc in PHCS_DATA:
        cursor.execute("""
            INSERT INTO phcs (phc_id, phc_name, district, state, latitude, longitude, total_beds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (phc["id"], phc["name"], phc["district"], phc["state"], phc["lat"], phc["lng"], phc["beds"]))

    # Insert Medicines
    for med in MEDICINES_DATA:
        cursor.execute("""
            INSERT INTO medicines (medicine_id, medicine_name, category, unit)
            VALUES (?, ?, ?, ?)
        """, (med["id"], med["name"], med["category"], med["unit"]))

    # Base reference date: 2026-09-18
    ref_date = datetime.date(2026, 9, 18)
    num_days = 60

    # Base footfall configurations for PHCs to reflect varied epidemiological profiles
    # Varanasi Central (PHC_VAR_01): Surging viral load (320 -> 490/day)
    # Prayagraj North (PHC_PRY_01): Rising load (280 -> 410/day)
    # Prayagraj East (PHC_PRY_02): Stable surplus hub (310/day)
    # Lucknow Chinhat (PHC_LKO_01): Large urban center (420/day stable)
    # Rural PHCs: 140 - 220/day
    
    random.seed(42) # Deterministic for reproducible hackathon demonstration

    # Generate 60 days of historical patient data
    patient_records = []
    daily_footfall_map = {} # (phc_id, day_offset) -> total_footfall

    for phc in PHCS_DATA:
        phc_id = phc["id"]
        
        # Profile assignment
        if phc_id == "PHC_VAR_01":
            profile = "surging_high" # +50% surge matching prompt example
            base_opd = 310
        elif phc_id == "PHC_PRY_01":
            profile = "rising_fast"       # +35% rise
            base_opd = 270
        elif phc_id == "PHC_GKP_01":
            profile = "rising"            # +25% rise
            base_opd = 260
        elif phc_id == "PHC_LKO_02":
            profile = "decreasing"        # slight dip
            base_opd = 180
        elif "Central" in phc["name"] or "Metro" in phc["name"] or "City" in phc["name"]:
            profile = "urban_stable"
            base_opd = random.randint(230, 290)
        else:
            profile = "rural_baseline"
            base_opd = random.randint(110, 180)

        for day_offset in range(num_days, 0, -1):
            cur_date = ref_date - datetime.timedelta(days=day_offset - 1)
            date_str = cur_date.strftime("%Y-%m-%d")

            # Day of week seasonality (Monday/Tuesday peaks)
            dow = cur_date.weekday()
            dow_mult = 1.15 if dow in (0, 1) else (0.90 if dow == 6 else 1.0)

            # Trend progression
            days_from_start = num_days - day_offset
            if profile == "surging_high":
                # Accelerated surge in last 14 days up to ~1.55x (+50-55%)
                if day_offset <= 14:
                    surge_factor = 1.0 + ((15 - day_offset) / 14.0) * 0.55
                else:
                    surge_factor = 1.0
            elif profile == "rising_fast":
                if day_offset <= 14:
                    surge_factor = 1.0 + ((15 - day_offset) / 14.0) * 0.38
                else:
                    surge_factor = 1.0
            elif profile == "rising":
                if day_offset <= 14:
                    surge_factor = 1.0 + ((15 - day_offset) / 14.0) * 0.28
                else:
                    surge_factor = 1.0
            elif profile == "decreasing":
                surge_factor = 1.0 - (days_from_start / 60.0) * 0.20
            else:
                surge_factor = 1.0 + random.uniform(-0.03, 0.03)

            noise = random.randint(-12, 14)
            opd = max(30, int(base_opd * dow_mult * surge_factor) + noise)
            ipd = max(2, int(opd * random.uniform(0.06, 0.12)))

            patient_records.append((phc_id, date_str, opd, ipd))
            daily_footfall_map[(phc_id, date_str)] = opd + ipd

    cursor.executemany("""
        INSERT INTO patients (phc_id, date, opd_patients, ipd_patients)
        VALUES (?, ?, ?, ?)
    """, patient_records)

    # Generate 60 days of Medicine Usage and Current Inventory
    usage_records = []
    inventory_records = []

    # Medicine prescription ratios per 100 patients
    med_ratios = {
        "MED_AMOX": 0.28,   # 28% of patients prescribed Amoxicillin
        "MED_PARA": 0.65,   # 65% of patients need Paracetamol
        "MED_ORS": 0.35,    # 35% need ORS
        "MED_AZI": 0.18,    # 18% Azithromycin
        "MED_METF": 0.22,   # 22% Metformin
        "MED_AMLO": 0.20,   # 20% Amlodipine
        "MED_IBUP": 0.24,   # 24% Ibuprofen
        "MED_CEFT": 0.08,   # 8% Ceftriaxone injection
        "MED_SALB": 0.07,   # 7% Inhalers
        "MED_IFA": 0.30,    # 30% IFA
        "MED_RAB": 0.03,    # 3% Anti-Rabies
        "MED_ASV": 0.015,   # 1.5% Snake venom antidote
    }

    # Custom inventory profiles to guarantee precise hackathon requirements:
    # 1. PHC_VAR_01 (Varanasi Central):
    #    - Amoxicillin: Shortage! Current Stock = 340, Avg Usage = 95/day (~3.6 days remaining) -> Critical!
    #    - Paracetamol: Low (3.2 days remaining) -> Warning!
    # 2. PHC_PRY_02 (Prayagraj East):
    #    - Amoxicillin: Surplus! Current Stock = 900, Avg Usage = 48/day (~18.8 days remaining) -> Surplus source!
    # 3. PHC_GKP_01:
    #    - ORS: Critical shortage (2.1 days remaining)
    # 4. PHC_LKO_01:
    #    - ORS: Surplus (22 days remaining)
    # 5. Some medicines nearing expiry (< 60 days)

    for phc in PHCS_DATA:
        phc_id = phc["id"]
        for med in MEDICINES_DATA:
            med_id = med["id"]
            ratio = med_ratios[med_id]

            # Generate 60 days of consumption directly coupled to patient footfall
            recent_7d_usages = []
            for day_offset in range(num_days, 0, -1):
                cur_date = ref_date - datetime.timedelta(days=day_offset - 1)
                date_str = cur_date.strftime("%Y-%m-%d")
                footfall = daily_footfall_map.get((phc_id, date_str), 200)

                # Base usage directly proportional to footfall + clinical dosage variance
                expected_units = int(footfall * ratio * random.uniform(0.92, 1.08))
                qty_used = max(1, expected_units)

                usage_records.append((phc_id, med_id, date_str, qty_used))
                if day_offset <= 7:
                    recent_7d_usages.append(qty_used)

            # Average daily usage over recent 7 days
            avg_daily = round(sum(recent_7d_usages) / len(recent_7d_usages), 1)

            # Assign stock according to demo scenario requirements
            if phc_id == "PHC_VAR_01" and med_id == "MED_AMOX":
                current_stock = 340
                avg_daily = 95.0
                expiry_date = "2026-12-15" # Expiry warning scenario!
            elif phc_id == "PHC_PRY_02" and med_id == "MED_AMOX":
                current_stock = 900
                avg_daily = 48.0
                expiry_date = "2027-11-20"
            elif phc_id == "PHC_VAR_01" and med_id == "MED_PARA":
                current_stock = 620
                avg_daily = 190.0 # ~3.2 days remaining (Warning)
                expiry_date = "2027-08-10"
            elif phc_id == "PHC_PRY_01" and med_id == "MED_PARA":
                current_stock = 2600
                avg_daily = 110.0 # ~23.6 days remaining (Surplus)
                expiry_date = "2027-09-14"
            elif phc_id == "PHC_GKP_01" and med_id == "MED_ORS":
                current_stock = 170
                avg_daily = 82.0 # 2.1 days remaining (Critical)
                expiry_date = "2026-11-05" # Approaching expiry (< 60 days)
            elif phc_id == "PHC_LKO_01" and med_id == "MED_ORS":
                current_stock = 2100
                avg_daily = 95.0 # ~22 days remaining (Surplus)
                expiry_date = "2028-01-30"
            elif phc_id == "PHC_KNP_01" and med_id == "MED_AZI":
                current_stock = 95
                avg_daily = 42.0 # 2.2 days remaining (Critical)
                expiry_date = "2027-05-18"
            elif phc_id == "PHC_LKO_03" and med_id == "MED_AZI":
                current_stock = 650
                avg_daily = 30.0 # 21.6 days remaining (Surplus)
                expiry_date = "2027-06-25"
            else:
                # Controlled distribution of days remaining:
                # 15% critical (<3d), 25% warning (3-7d), 40% normal (7-15d), 20% surplus (>15d)
                p = random.random()
                if p < 0.12:
                    days_target = random.uniform(1.2, 2.8)
                elif p < 0.32:
                    days_target = random.uniform(3.2, 6.5)
                elif p < 0.80:
                    days_target = random.uniform(7.5, 14.5)
                else:
                    days_target = random.uniform(16.0, 26.0)

                current_stock = max(10, int(avg_daily * days_target))

                # Expiry date distribution: 10% near expiry (< 60 days), 90% normal (1 to 2.5 years)
                if random.random() < 0.12:
                    exp_days = random.randint(18, 55)
                else:
                    exp_days = random.randint(180, 750)
                expiry_date = (ref_date + datetime.timedelta(days=exp_days)).strftime("%Y-%m-%d")

            inventory_records.append((phc_id, med_id, current_stock, avg_daily, expiry_date))

    cursor.executemany("""
        INSERT INTO medicine_usage (phc_id, medicine_id, date, quantity_used)
        VALUES (?, ?, ?, ?)
    """, usage_records)

    cursor.executemany("""
        INSERT INTO inventory (phc_id, medicine_id, current_stock, average_daily_usage, expiry_date)
        VALUES (?, ?, ?, ?, ?)
    """, inventory_records)

    # Sample prior logged action for demonstration
    cursor.execute("""
        INSERT INTO actions (action_type, source_phc_id, dest_phc_id, medicine_id, quantity, status, timestamp, rationale)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'REDISTRIBUTION',
        'PHC_LKO_01',
        'PHC_KNP_01',
        'MED_PARA',
        400,
        'COMPLETED',
        '2026-09-17 14:30:00',
        'Routine district buffer balance: Transferred 400 tablets from Lucknow Chinhat surplus to Kanpur Kalyanpur.'
    ))

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic synthetic data.")
    print(f"Generated {len(PHCS_DATA)} PHCs, {len(MEDICINES_DATA)} Medicines, {len(inventory_records)} Inventory rows, {len(usage_records)} Usage rows, {len(patient_records)} Patient rows.")

if __name__ == '__main__':
    seed_database()
