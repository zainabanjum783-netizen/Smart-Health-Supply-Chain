import os
import sys

# Ensure UTF-8 stdout on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import data_generator
from app import app

def run_e2e_tests():
    print("=" * 70)
    print("RUNNING END-TO-END VERIFICATION: SMART HEALTH & SUPPLY CHAIN")
    print("=" * 70)

    # 1. Fresh seed
    data_generator.seed_database()
    client = app.test_client()

    # STEP 1: Overview
    print("\n--- STEP 1: Overview Verification ---")
    res = client.get('/api/overview')
    assert res.status_code == 200, f"Failed: {res.status_code}"
    ov = res.get_json()
    summary = ov["summary"]
    print(f"[OK] Overview Loaded: Total PHCs: {summary['total_phcs']}, Critical: {summary['critical_phcs']}, Alerts: {summary['active_alerts']}")
    assert summary["total_phcs"] == 29
    assert summary["critical_phcs"] > 0
    assert len(ov["map_phcs"]) == 29
    print(f"[OK] Map markers verified: {len(ov['map_phcs'])} locations geolocated across Uttar Pradesh.")

    # STEP 2: Dashboard
    print("\n--- STEP 2: Dashboard Facility Drilldown ---")
    res = client.get('/api/phcs?district=Varanasi')
    assert res.status_code == 200
    phcs_varanasi = res.get_json()["phcs"]
    print(f"[OK] Varanasi District PHCs filtered: {len(phcs_varanasi)} facilities found.")
    assert len(phcs_varanasi) >= 4

    # Select Varanasi Central
    res = client.get('/api/phc/PHC_VAR_01')
    assert res.status_code == 200
    var_detail = res.get_json()
    pm = var_detail["patient_metrics"]
    mm = var_detail["medicine_metrics"]
    print(f"[OK] Selected PHC: {var_detail['phc']['phc_name']}")
    print(f"     Patient Today: {pm['today_patients']}, 7-day Avg: {pm['avg_daily_patients']}, 7d Trend: {pm['trend_7d_pct']}% ({pm['trend_7d_symbol']})")
    print(f"     Medicines: Total: {mm['total_medicines_in_stock']}, Critical: {mm['critical_medicines']}, Approaching Shortage: {mm['approaching_shortage']}")
    assert pm["trend_7d_pct"] > 20.0, "Varanasi Central should reflect surging patient load"

    # STEP 3: Inventory
    print("\n--- STEP 3: Inventory Search & Rules Verification ---")
    res = client.get('/api/inventory?search_medicine=Amoxicillin&search_phc=Varanasi')
    assert res.status_code == 200
    inv_items = res.get_json()["items"]
    print(f"[OK] Found {len(inv_items)} inventory records for Amoxicillin in Varanasi.")
    var_amox = next(i for i in inv_items if i["phc_id"] == "PHC_VAR_01")
    print(f"     PHC: {var_amox['phc_name']}")
    print(f"     Stock: {var_amox['current_stock']} {var_amox['unit']}, Daily Usage: {var_amox['average_daily_usage']}/day")
    print(f"     Days Remaining: {var_amox['days_remaining']} days, Status: {var_amox['status']['symbol']} {var_amox['status']['label']}")
    print(f"     Expiry: {var_amox['expiry_date']} (Expiring Soon: {var_amox['is_nearing_expiry']})")
    assert var_amox["current_stock"] == 340
    assert var_amox["days_remaining"] < 4.0

    # STEP 4: Predictions
    print("\n--- STEP 4: Statistical Forecast & Demand Coupling ---")
    res = client.get('/api/predictions?phc_id=PHC_VAR_01&medicine_id=MED_AMOX&forecast_days=7')
    assert res.status_code == 200
    pred_data = res.get_json()
    p = pred_data["prediction"]
    print(f"[OK] Prediction generated without ML:")
    print(f"     Base 7-day Consumption: {p['base_daily_consumption']} units/day")
    print(f"     Patient Increase Factor: +{p['patient_increase_pct']}%")
    print(f"     Adjusted Daily Demand: {p['adjusted_daily_demand']} units/day")
    print(f"     Days Until Stockout: {p['days_remaining']} days")
    print(f"     Estimated Shortage Date: {p['shortage_date']}")
    print(f"     Shortage Expected Flag: {p['shortage_expected']}")
    assert p["shortage_expected"] is True
    assert p["days_remaining"] > 0
    assert "days" in p["formula_explanation"]["step5"]

    # STEP 5: Actions & Live Stock Redistribution
    print("\n--- STEP 5: Proactive Medicine Redistribution ---")
    res = client.get('/api/actions')
    assert res.status_code == 200
    actions_data = res.get_json()
    redists = actions_data["redistributions"]
    patient_alerts = actions_data["patient_load_alerts"]
    print(f"[OK] Active Redistribution Recommendations: {len(redists)}")
    print(f"[OK] High Patient Load Alerts: {len(patient_alerts)}")
    assert len(redists) > 0
    assert len(patient_alerts) > 0

    # Find candidate transfer involving Amoxicillin
    amox_transfer = next((r for r in redists if r["medicine"]["medicine_id"] == "MED_AMOX"), redists[0])
    src_id = amox_transfer["source"]["phc_id"]
    dst_id = amox_transfer["destination"]["phc_id"]
    med_id = amox_transfer["medicine"]["medicine_id"]
    qty = amox_transfer["recommended_quantity"]
    src_stock_before = amox_transfer["source"]["current_stock"]
    dst_stock_before = amox_transfer["destination"]["current_stock"]

    print(f"     Executing Action: Transfer {qty} units of {amox_transfer['medicine']['medicine_name']}")
    print(f"     From: {amox_transfer['source']['phc_name']} (Stock: {src_stock_before})")
    print(f"     To:   {amox_transfer['destination']['phc_name']} (Stock: {dst_stock_before})")

    # Execute transfer via POST
    tx_res = client.post('/api/actions/transfer', json={
        "source_phc_id": src_id,
        "dest_phc_id": dst_id,
        "medicine_id": med_id,
        "quantity": qty
    })
    assert tx_res.status_code == 200
    tx_result = tx_res.get_json()
    print(f"[OK] Transfer Transaction Success: {tx_result['message']}")
    print(f"     Source New Stock: {tx_result['new_source_stock']} (Expected: {src_stock_before - qty})")
    print(f"     Dest New Stock:   {tx_result['new_dest_stock']} (Expected: {dst_stock_before + qty})")
    assert tx_result["new_source_stock"] == src_stock_before - qty
    assert tx_result["new_dest_stock"] == dst_stock_before + qty

    # Verify audit log updated
    res2 = client.get('/api/actions')
    audit_history = res2.get_json()["action_history"]
    assert len(audit_history) > 0
    print(f"[OK] Audit trail verified: Action recorded with timestamp {audit_history[0]['timestamp']}")

    # STEP 6: Emergency Simulation
    print("\n--- STEP 6: Emergency Simulation Center ---")
    sim_res = client.post('/api/emergency/simulate', json={
        "footfall_increase_pct": 30.0,
        "supply_reduction_pct": 20.0
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.get_json()
    impact = sim_data["impact_summary"]
    print(f"[OK] Simulation executed successfully (+30% footfall, -20% supply):")
    print(f"     PHCs at Risk: {impact['phcs_at_risk_count']}")
    print(f"     Critical Stockouts Before: {impact['critical_stockouts_before']} -> After: {impact['critical_stockouts_after']} (+{impact['delta_critical']})")
    print(f"     Warning Stockouts Before:  {impact['warning_stockouts_before']} -> After: {impact['warning_stockouts_after']}")
    print(f"     Emergency Crisis Actions Generated: {len(sim_data['emergency_recommendations'])}")
    assert impact["critical_stockouts_after"] > impact["critical_stockouts_before"]
    assert "high_patient_load_count" in impact
    assert impact["high_patient_load_count"] > 0
    print(f"     High Load PHCs under crisis: {impact['high_patient_load_count']} PHCs")
    assert len(sim_data["emergency_recommendations"]) > 0
    first_crisis_action = sim_data["emergency_recommendations"][0]
    assert "reason" in first_crisis_action and len(first_crisis_action["reason"]) > 0
    assert "distance_km" in first_crisis_action
    assert "urgency" in first_crisis_action
    print(f"[OK] Crisis action fields validated: Reason='{first_crisis_action['reason'][:60]}...', Urgency={first_crisis_action['urgency']}")

    # STEP 7: Reset Demo Data
    print("\n--- STEP 7: Reset Demo State ---")
    reset_res = client.post('/api/reset')
    assert reset_res.status_code == 200
    print("[OK] Reset endpoint confirmed database restored to initial state.")

    # Re-check initial stock restored
    inv_check = client.get('/api/inventory?search_medicine=Amoxicillin&search_phc=Varanasi').get_json()["items"]
    var_restored = next(i for i in inv_check if i["phc_id"] == "PHC_VAR_01")
    assert var_restored["current_stock"] == 340
    print(f"[OK] Varanasi Central Amoxicillin stock restored to initial: {var_restored['current_stock']}")

    print("\n" + "=" * 70)
    print("ALL 7 END-TO-END DEMO TEST SCENARIOS PASSED WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == '__main__':
    run_e2e_tests()
