import os
import datetime
from flask import Flask, request, jsonify, send_from_directory
from database import get_connection, init_db, DB_PATH
import data_generator
import calculations

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

# Ensure DB exists
if not os.path.exists(DB_PATH):
    data_generator.seed_database()

# Helper to fetch PHCs as a dict
def get_phcs_dict(conn):
    rows = conn.execute("SELECT * FROM phcs").fetchall()
    return {r["phc_id"]: dict(r) for r in rows}

# Helper to fetch Medicines as a dict
def get_medicines_dict(conn):
    rows = conn.execute("SELECT * FROM medicines").fetchall()
    return {r["medicine_id"]: dict(r) for r in rows}

# Calculate overall status for all PHCs
def get_all_phc_summaries(conn):
    phcs = get_phcs_dict(conn)
    medicines = get_medicines_dict(conn)
    
    # Load inventory
    inv_rows = conn.execute("SELECT * FROM inventory").fetchall()
    inv_by_phc = {}
    for row in inv_rows:
        inv_by_phc.setdefault(row["phc_id"], []).append(dict(row))

    # Load patient stats for last 30 days
    ref_date = datetime.date(2026, 9, 18)
    start_date = (ref_date - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    patient_rows = conn.execute("""
        SELECT phc_id, date, opd_patients, ipd_patients 
        FROM patients 
        WHERE date >= ? 
        ORDER BY date ASC
    """, (start_date,)).fetchall()
    
    patients_by_phc = {}
    for r in patient_rows:
        patients_by_phc.setdefault(r["phc_id"], []).append(dict(r))

    phc_summaries = []
    
    for phc_id, phc in phcs.items():
        inv_list = inv_by_phc.get(phc_id, [])
        patient_list = patients_by_phc.get(phc_id, [])
        
        # Medicine metrics
        critical_meds = []
        warning_meds = []
        normal_meds = []
        nearing_expiry_meds = []
        min_days = 999.0

        for item in inv_list:
            days = calculations.calculate_days_remaining(item["current_stock"], item["average_daily_usage"])
            if days < min_days:
                min_days = days
            
            med_info = medicines.get(item["medicine_id"], {})
            item_data = {
                "medicine_id": item["medicine_id"],
                "medicine_name": med_info.get("medicine_name", item["medicine_id"]),
                "current_stock": item["current_stock"],
                "days_remaining": days,
                "expiry_date": item["expiry_date"]
            }

            if days < 3.0:
                critical_meds.append(item_data)
            elif days < 7.0:
                warning_meds.append(item_data)
            else:
                normal_meds.append(item_data)

            # Check expiry (within 60 days of 2026-09-18)
            try:
                exp_d = datetime.datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
                if (exp_d - ref_date).days <= 60:
                    nearing_expiry_meds.append(item_data)
            except Exception:
                pass

        # Patient forecast
        p_stats = calculations.calculate_patient_footfall_forecast(patient_list)

        # Overall Status logic
        # Critical if: any medicine < 3.0 days OR footfall surge >= 40%
        # Warning if: any medicine < 7.0 days OR footfall surge >= 20%
        # Normal otherwise
        if len(critical_meds) > 0 or p_stats["trend_pct"] >= 40.0:
            overall_code = "CRITICAL"
            overall_symbol = "🔴"
            overall_label = "Critical"
        elif len(warning_meds) > 0 or p_stats["trend_pct"] >= 20.0 or len(nearing_expiry_meds) > 0:
            overall_code = "WARNING"
            overall_symbol = "🟡"
            overall_label = "Warning"
        else:
            overall_code = "NORMAL"
            overall_symbol = "🟢"
            overall_label = "Normal"

        medicine_status_text = "Normal"
        if len(critical_meds) > 0:
            medicine_status_text = f"Critical ({len(critical_meds)})"
        elif len(warning_meds) > 0:
            medicine_status_text = f"Warning ({len(warning_meds)})"

        phc_summaries.append({
            "phc_id": phc["phc_id"],
            "phc_name": phc["phc_name"],
            "district": phc["district"],
            "state": phc["state"],
            "latitude": phc["latitude"],
            "longitude": phc["longitude"],
            "total_beds": phc["total_beds"],
            "today_footfall": p_stats["today_footfall"],
            "avg_footfall": p_stats["avg_7d"],
            "expected_tomorrow": p_stats["expected_tomorrow"],
            "footfall_trend_pct": p_stats["trend_pct"],
            "footfall_trend_symbol": p_stats["trend_symbol"],
            "medicine_status_text": medicine_status_text,
            "critical_med_count": len(critical_meds),
            "warning_med_count": len(warning_meds),
            "normal_med_count": len(normal_meds),
            "nearing_expiry_count": len(nearing_expiry_meds),
            "min_days_remaining": min_days if min_days != 999.0 else 0,
            "overall_status": overall_code,
            "overall_symbol": overall_symbol,
            "overall_label": overall_label
        })

    return phc_summaries

# -------------------------------------------------------------
# API ROUTES
# -------------------------------------------------------------

@app.route('/api/overview')
def api_overview():
    conn = get_connection()
    summaries = get_all_phc_summaries(conn)
    medicines = get_medicines_dict(conn)
    
    # Calculate global cards
    total_phcs = len(summaries)
    critical_phcs = sum(1 for s in summaries if s["overall_status"] == "CRITICAL")
    warning_phcs = sum(1 for s in summaries if s["overall_status"] == "WARNING")
    high_load_phcs = sum(1 for s in summaries if s["footfall_trend_pct"] >= 18.0)

    # Medicine risk & shortage calculation
    inv_rows = conn.execute("SELECT * FROM inventory").fetchall()
    meds_at_risk_set = set()
    predicted_shortages_count = 0

    for r in inv_rows:
        days = calculations.calculate_days_remaining(r["current_stock"], r["average_daily_usage"])
        if days < 7.0:
            meds_at_risk_set.add(r["medicine_id"])
        if days < 3.0:
            predicted_shortages_count += 1

    active_alerts = (critical_phcs * 2) + warning_phcs + high_load_phcs

    conn.close()

    return jsonify({
        "summary": {
            "total_phcs": total_phcs,
            "critical_phcs": critical_phcs,
            "warning_phcs": warning_phcs,
            "active_alerts": active_alerts,
            "medicines_at_risk": len(meds_at_risk_set),
            "high_patient_load": high_load_phcs,
            "predicted_shortages": predicted_shortages_count
        },
        "map_phcs": summaries
    })

@app.route('/api/phcs')
def api_phcs():
    conn = get_connection()
    summaries = get_all_phc_summaries(conn)
    conn.close()

    # Query params
    state = request.args.get('state', '').strip()
    district = request.args.get('district', '').strip()
    status = request.args.get('status', '').strip().upper()

    filtered = summaries
    if state:
        filtered = [p for p in filtered if p["state"].lower() == state.lower()]
    if district:
        filtered = [p for p in filtered if p["district"].lower() == district.lower()]
    if status and status != 'ALL':
        filtered = [p for p in filtered if p["overall_status"] == status]

    districts = sorted(list({p["district"] for p in summaries}))
    states = sorted(list({p["state"] for p in summaries}))

    return jsonify({
        "phcs": filtered,
        "districts": districts,
        "states": states,
        "total_count": len(filtered)
    })

@app.route('/api/phc/<phc_id>')
def api_phc_detail(phc_id):
    conn = get_connection()
    phc_row = conn.execute("SELECT * FROM phcs WHERE phc_id = ?", (phc_id,)).fetchone()
    if not phc_row:
        conn.close()
        return jsonify({"error": "PHC not found"}), 404

    phc = dict(phc_row)
    medicines = get_medicines_dict(conn)

    # 1. Patient footfall historical series (last 30 days)
    ref_date = datetime.date(2026, 9, 18)
    start_date = (ref_date - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    patient_rows = conn.execute("""
        SELECT date, opd_patients, ipd_patients 
        FROM patients 
        WHERE phc_id = ? AND date >= ? 
        ORDER BY date ASC
    """, (phc_id, start_date)).fetchall()

    patient_history = []
    footfalls = []
    for r in patient_rows:
        total = r["opd_patients"] + r["ipd_patients"]
        footfalls.append(total)
        # 7-day rolling average
        rolling = round(sum(footfalls[-7:]) / len(footfalls[-7:]), 1) if len(footfalls) >= 1 else total
        patient_history.append({
            "date": r["date"],
            "opd": r["opd_patients"],
            "ipd": r["ipd_patients"],
            "total": total,
            "moving_avg": rolling
        })

    p_stats = calculations.calculate_patient_footfall_forecast([dict(r) for r in patient_rows])

    # 30-day baseline comparison
    if len(patient_history) >= 28:
        first_14_avg = sum(p["total"] for p in patient_history[:14]) / 14.0
        last_14_avg = sum(p["total"] for p in patient_history[-14:]) / 14.0
        trend_30d_pct = round(((last_14_avg - first_14_avg) / first_14_avg) * 100, 1) if first_14_avg > 0 else 0.0
    else:
        trend_30d_pct = p_stats["trend_pct"]

    # 2. Medicine inventory status
    inv_rows = conn.execute("""
        SELECT i.*, m.medicine_name, m.category, m.unit 
        FROM inventory i 
        JOIN medicines m ON i.medicine_id = m.medicine_id 
        WHERE i.phc_id = ?
        ORDER BY (i.current_stock / i.average_daily_usage) ASC
    """, (phc_id,)).fetchall()

    inventory_items = []
    critical_count = 0
    warning_count = 0
    approaching_shortage = 0
    nearing_expiry_count = 0

    for r in inv_rows:
        days = calculations.calculate_days_remaining(r["current_stock"], r["average_daily_usage"])
        badge = calculations.get_status_badge(days)
        
        # Check expiry
        exp_d = datetime.datetime.strptime(r["expiry_date"], "%Y-%m-%d").date()
        is_expiring = (exp_d - ref_date).days <= 60
        if is_expiring:
            nearing_expiry_count += 1

        if days < 3.0:
            critical_count += 1
        elif days < 7.0:
            warning_count += 1
            approaching_shortage += 1

        inventory_items.append({
            "medicine_id": r["medicine_id"],
            "medicine_name": r["medicine_name"],
            "category": r["category"],
            "unit": r["unit"],
            "current_stock": r["current_stock"],
            "daily_usage": r["average_daily_usage"],
            "days_remaining": days,
            "expiry_date": r["expiry_date"],
            "is_expiring": is_expiring,
            "status": badge
        })

    # 3. Medicine consumption series (top 5 medicines for charts)
    top_med_ids = [item["medicine_id"] for item in inventory_items[:5]]
    usage_series = {}
    if top_med_ids:
        placeholders = ','.join('?' for _ in top_med_ids)
        usage_rows = conn.execute(f"""
            SELECT medicine_id, date, quantity_used 
            FROM medicine_usage 
            WHERE phc_id = ? AND medicine_id IN ({placeholders}) AND date >= ? 
            ORDER BY date ASC
        """, [phc_id] + top_med_ids + [start_date]).fetchall()
        for ur in usage_rows:
            usage_series.setdefault(ur["medicine_id"], []).append({
                "date": ur["date"],
                "quantity": ur["quantity_used"]
            })

    conn.close()

    return jsonify({
        "phc": phc,
        "patient_metrics": {
            "today_patients": p_stats["today_footfall"],
            "avg_daily_patients": p_stats["avg_7d"],
            "expected_tomorrow": p_stats["expected_tomorrow"],
            "trend_7d_pct": p_stats["trend_pct"],
            "trend_7d_symbol": p_stats["trend_symbol"],
            "trend_30d_pct": trend_30d_pct,
            "history_30d": patient_history
        },
        "medicine_metrics": {
            "total_medicines_in_stock": len(inventory_items),
            "approaching_shortage": approaching_shortage,
            "critical_medicines": critical_count,
            "warning_medicines": warning_count,
            "medicines_nearing_expiry": nearing_expiry_count,
            "inventory": inventory_items
        },
        "top_usage_series": usage_series
    })

@app.route('/api/inventory')
def api_inventory():
    conn = get_connection()
    med_query = request.args.get('search_medicine', '').strip().lower()
    phc_query = request.args.get('search_phc', '').strip().lower()
    status_filter = request.args.get('status', 'ALL').strip().upper()

    query = """
        SELECT i.phc_id, p.phc_name, p.district, p.state,
               i.medicine_id, m.medicine_name, m.category, m.unit,
               i.current_stock, i.average_daily_usage, i.expiry_date
        FROM inventory i
        JOIN phcs p ON i.phc_id = p.phc_id
        JOIN medicines m ON i.medicine_id = m.medicine_id
        ORDER BY (i.current_stock / i.average_daily_usage) ASC, p.phc_name ASC
    """
    rows = conn.execute(query).fetchall()
    ref_date = datetime.date(2026, 9, 18)

    results = []
    for r in rows:
        # Search filters
        if med_query and (med_query not in r["medicine_name"].lower() and med_query not in r["category"].lower()):
            continue
        if phc_query and (phc_query not in r["phc_name"].lower() and phc_query not in r["district"].lower()):
            continue

        days = calculations.calculate_days_remaining(r["current_stock"], r["average_daily_usage"])
        badge = calculations.get_status_badge(days)

        exp_d = datetime.datetime.strptime(r["expiry_date"], "%Y-%m-%d").date()
        days_to_expiry = (exp_d - ref_date).days
        is_nearing_expiry = days_to_expiry <= 60

        # Status filter
        if status_filter == 'CRITICAL' and badge["code"] != 'CRITICAL':
            continue
        elif status_filter == 'WARNING' and badge["code"] != 'WARNING':
            continue
        elif status_filter == 'NORMAL' and badge["code"] != 'NORMAL':
            continue
        elif status_filter == 'EXPIRING' and not is_nearing_expiry:
            continue

        results.append({
            "phc_id": r["phc_id"],
            "phc_name": r["phc_name"],
            "district": r["district"],
            "state": r["state"],
            "medicine_id": r["medicine_id"],
            "medicine_name": r["medicine_name"],
            "category": r["category"],
            "unit": r["unit"],
            "current_stock": r["current_stock"],
            "average_daily_usage": r["average_daily_usage"],
            "days_remaining": days,
            "expiry_date": r["expiry_date"],
            "days_to_expiry": days_to_expiry,
            "is_nearing_expiry": is_nearing_expiry,
            "status": badge
        })

    conn.close()
    return jsonify({
        "items": results,
        "total_count": len(results)
    })

@app.route('/api/predictions')
def api_predictions():
    phc_id = request.args.get('phc_id', 'PHC_VAR_01').strip()
    medicine_id = request.args.get('medicine_id', 'MED_AMOX').strip()
    forecast_days = int(request.args.get('forecast_days', 7))

    conn = get_connection()
    
    # Verify PHC and medicine
    phc_row = conn.execute("SELECT * FROM phcs WHERE phc_id = ?", (phc_id,)).fetchone()
    med_row = conn.execute("SELECT * FROM medicines WHERE medicine_id = ?", (medicine_id,)).fetchone()
    inv_row = conn.execute("SELECT * FROM inventory WHERE phc_id = ? AND medicine_id = ?", (phc_id, medicine_id)).fetchone()

    if not phc_row or not med_row or not inv_row:
        conn.close()
        return jsonify({"error": "PHC or Medicine inventory record not found"}), 404

    # Fetch last 30 days of patient data
    ref_date = datetime.date(2026, 9, 18)
    start_date = (ref_date - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    patient_rows = conn.execute("""
        SELECT date, opd_patients, ipd_patients 
        FROM patients 
        WHERE phc_id = ? AND date >= ? 
        ORDER BY date ASC
    """, (phc_id, start_date)).fetchall()

    # Fetch last 30 days of medicine usage
    usage_rows = conn.execute("""
        SELECT date, quantity_used 
        FROM medicine_usage 
        WHERE phc_id = ? AND medicine_id = ? AND date >= ? 
        ORDER BY date ASC
    """, (phc_id, medicine_id, start_date)).fetchall()

    conn.close()

    patient_records = [dict(r) for r in patient_rows]
    usage_records = [dict(r) for r in usage_rows]

    # Calculate coupled prediction
    prediction = calculations.calculate_coupled_medicine_prediction(
        current_stock=inv_row["current_stock"],
        usage_records=usage_records,
        patient_records=patient_records,
        forecast_days=forecast_days
    )

    # Build historical & forecast timeline for charts
    # 1. Patient footfall series (last 14 days + tomorrow forecast)
    p_timeline = []
    for r in patient_records[-14:]:
        p_timeline.append({
            "date": r["date"],
            "value": r["opd_patients"] + r["ipd_patients"],
            "type": "historical"
        })
    tomorrow_date = (ref_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    p_timeline.append({
        "date": tomorrow_date,
        "value": prediction["patient_stats"]["expected_tomorrow"],
        "type": "forecast"
    })

    # 2. Medicine consumption series (last 7 days breakdown + projected daily demand)
    last_7_usages = usage_records[-7:] if len(usage_records) >= 7 else usage_records
    usage_breakdown = [{"day": f"Day {idx+1}", "date": u["date"], "quantity": u["quantity_used"]} for idx, u in enumerate(last_7_usages)]

    # Stock depletion projection series
    depletion_series = []
    running_stock = inv_row["current_stock"]
    daily_decrement = prediction["adjusted_daily_demand"]
    for day_i in range(forecast_days + 1):
        proj_date = (ref_date + datetime.timedelta(days=day_i)).strftime("%d %b")
        depletion_series.append({
            "day_label": proj_date,
            "projected_stock": max(0, int(round(running_stock)))
        })
        running_stock -= daily_decrement

    return jsonify({
        "phc": dict(phc_row),
        "medicine": dict(med_row),
        "prediction": prediction,
        "usage_breakdown_7d": usage_breakdown,
        "patient_timeline": p_timeline,
        "depletion_series": depletion_series
    })

@app.route('/api/actions')
def api_actions():
    conn = get_connection()
    phcs = get_phcs_dict(conn)
    medicines = get_medicines_dict(conn)
    inv_rows = [dict(r) for r in conn.execute("SELECT * FROM inventory").fetchall()]

    # High patient load alerts
    ref_date = datetime.date(2026, 9, 18)
    start_date = (ref_date - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    p_rows = conn.execute("""
        SELECT phc_id, date, opd_patients, ipd_patients 
        FROM patients 
        WHERE date >= ? 
        ORDER BY date ASC
    """, (start_date,)).fetchall()
    
    patients_by_phc = {}
    for r in p_rows:
        patients_by_phc.setdefault(r["phc_id"], []).append(dict(r))

    patient_stats = {}
    for phc_id, p_list in patients_by_phc.items():
        patient_stats[phc_id] = calculations.calculate_patient_footfall_forecast(p_list)

    redistribution_recommendations = calculations.find_redistribution_recommendations(inv_rows, phcs, medicines)
    patient_load_alerts = calculations.find_high_patient_load_actions(patient_stats, phcs)

    # Action history
    action_rows = conn.execute("""
        SELECT a.*, 
               s.phc_name as source_phc_name, 
               d.phc_name as dest_phc_name,
               m.medicine_name, m.unit
        FROM actions a
        JOIN phcs s ON a.source_phc_id = s.phc_id
        JOIN phcs d ON a.dest_phc_id = d.phc_id
        JOIN medicines m ON a.medicine_id = m.medicine_id
        ORDER BY a.id DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    return jsonify({
        "redistributions": redistribution_recommendations,
        "patient_load_alerts": patient_load_alerts,
        "action_history": [dict(r) for r in action_rows]
    })

@app.route('/api/actions/transfer', methods=['POST'])
def api_transfer():
    data = request.get_json() or {}
    source_id = data.get('source_phc_id')
    dest_id = data.get('dest_phc_id')
    med_id = data.get('medicine_id')
    quantity = int(data.get('quantity', 0))

    if not source_id or not dest_id or not med_id or quantity <= 0:
        return jsonify({"error": "Invalid transfer parameters"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Check source inventory
    source_inv = cursor.execute("SELECT current_stock FROM inventory WHERE phc_id = ? AND medicine_id = ?", (source_id, med_id)).fetchone()
    dest_inv = cursor.execute("SELECT current_stock FROM inventory WHERE phc_id = ? AND medicine_id = ?", (dest_id, med_id)).fetchone()

    if not source_inv or not dest_inv:
        conn.close()
        return jsonify({"error": "Source or destination inventory record not found"}), 404

    if source_inv["current_stock"] < quantity:
        conn.close()
        return jsonify({"error": f"Insufficient source stock (available: {source_inv['current_stock']}, requested: {quantity})"}), 400

    new_source_stock = source_inv["current_stock"] - quantity
    new_dest_stock = dest_inv["current_stock"] + quantity

    # Atomic database update
    cursor.execute("UPDATE inventory SET current_stock = ? WHERE phc_id = ? AND medicine_id = ?", (new_source_stock, source_id, med_id))
    cursor.execute("UPDATE inventory SET current_stock = ? WHERE phc_id = ? AND medicine_id = ?", (new_dest_stock, dest_id, med_id))

    # Log action
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rationale = f"Approved administrative redistribution of {quantity} units to alleviate imminent shortage."
    cursor.execute("""
        INSERT INTO actions (action_type, source_phc_id, dest_phc_id, medicine_id, quantity, status, timestamp, rationale)
        VALUES ('REDISTRIBUTION', ?, ?, ?, ?, 'COMPLETED', ?, ?)
    """, (source_id, dest_id, med_id, quantity, timestamp, rationale))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Successfully transferred {quantity} units.",
        "new_source_stock": new_source_stock,
        "new_dest_stock": new_dest_stock
    })

@app.route('/api/emergency/simulate', methods=['POST'])
def api_emergency_simulate():
    data = request.get_json() or {}
    footfall_pct = float(data.get('footfall_increase_pct', 30.0))
    supply_pct = float(data.get('supply_reduction_pct', 20.0))

    conn = get_connection()
    phcs = get_phcs_dict(conn)
    medicines = get_medicines_dict(conn)
    inv_rows = [dict(r) for r in conn.execute("SELECT * FROM inventory").fetchall()]

    # Fetch 30-day patient footfall for dynamic high-load simulation
    ref_date = datetime.date(2026, 9, 18)
    start_date = (ref_date - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    p_rows = conn.execute("""
        SELECT phc_id, date, opd_patients, ipd_patients 
        FROM patients 
        WHERE date >= ? 
        ORDER BY date ASC
    """, (start_date,)).fetchall()
    
    patients_by_phc = {}
    for r in p_rows:
        patients_by_phc.setdefault(r["phc_id"], []).append(dict(r))

    patient_stats = {}
    for phc_id, p_list in patients_by_phc.items():
        patient_stats[phc_id] = calculations.calculate_patient_footfall_forecast(p_list)

    conn.close()

    sim_results = calculations.simulate_emergency_crisis(
        inventory_rows=inv_rows,
        phcs_map=phcs,
        medicines_map=medicines,
        footfall_increase_pct=footfall_pct,
        supply_reduction_pct=supply_pct,
        patient_stats_by_phc=patient_stats
    )

    return jsonify(sim_results)

@app.route('/api/reset', methods=['POST'])
def api_reset():
    data_generator.seed_database()
    return jsonify({"success": True, "message": "Database reset to initial demo state successfully."})

# -------------------------------------------------------------
# FRONTEND STATIC ROUTES
# -------------------------------------------------------------

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

if __name__ == '__main__':
    print("Starting Smart Health & Supply Chain server on port 5000...")
    app.run(host='127.0.0.1', port=5000, debug=True)
