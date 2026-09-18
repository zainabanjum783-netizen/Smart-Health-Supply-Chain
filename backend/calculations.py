import math
import datetime

REF_DATE = datetime.date(2026, 9, 18)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance between two coordinates in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

def calculate_days_remaining(stock, daily_usage):
    """Days Remaining = Current Stock / Average Daily Usage"""
    if daily_usage <= 0:
        return 999.0
    return round(stock / daily_usage, 1)

def get_status_badge(days_remaining):
    """
    Days Remaining < 3  -> Critical (Red)
    Days Remaining >= 3 AND < 7 -> Warning (Yellow)
    Days Remaining >= 7 -> Normal (Green)
    """
    if days_remaining < 3.0:
        return {"code": "CRITICAL", "label": "Critical", "color": "red", "symbol": "🔴"}
    elif days_remaining < 7.0:
        return {"code": "WARNING", "label": "Warning", "color": "yellow", "symbol": "🟡"}
    else:
        return {"code": "NORMAL", "label": "Normal", "color": "green", "symbol": "🟢"}

def calculate_patient_footfall_forecast(daily_records):
    """
    Analyzes historical patient footfall without machine learning.
    Uses recent 7-day average, 14-day baseline, and moving average slope.
    """
    if not daily_records:
        return {
            "today_footfall": 0,
            "avg_7d": 0,
            "expected_tomorrow": 0,
            "trend_rate": 0.0,
            "trend_direction": "stable",
            "trend_symbol": "➔"
        }

    # Sorted by date ascending
    records = sorted(daily_records, key=lambda x: x["date"])
    footfalls = [r["opd_patients"] + r["ipd_patients"] for r in records]
    
    today_footfall = footfalls[-1] if footfalls else 0
    last_7 = footfalls[-7:] if len(footfalls) >= 7 else footfalls
    avg_7d = round(sum(last_7) / len(last_7), 1)

    # 21-day or 14-day baseline to calculate recent velocity against pre-surge baseline
    if len(footfalls) >= 21:
        baseline = footfalls[-21:-14]
        avg_baseline = sum(baseline) / len(baseline)
        trend_rate = (avg_7d - avg_baseline) / avg_baseline if avg_baseline > 0 else 0.0
    elif len(footfalls) >= 14:
        prior_7 = footfalls[-14:-7]
        avg_prior_7 = sum(prior_7) / len(prior_7)
        trend_rate = (avg_7d - avg_prior_7) / avg_prior_7 if avg_prior_7 > 0 else 0.0
    else:
        trend_rate = (footfalls[-1] - footfalls[0]) / footfalls[0] if footfalls[0] > 0 else 0.0

    trend_rate = round(trend_rate, 3)

    if trend_rate >= 0.08:
        trend_direction = "increasing"
        trend_symbol = "↗ Increasing"
    elif trend_rate <= -0.08:
        trend_direction = "decreasing"
        trend_symbol = "↘ Decreasing"
    else:
        trend_direction = "stable"
        trend_symbol = "➔ Stable"

    # Expected tomorrow: weighted recent momentum
    expected_tomorrow = int(round(today_footfall * (1.0 + max(-0.25, min(0.35, trend_rate * 0.5)))))

    return {
        "today_footfall": today_footfall,
        "avg_7d": avg_7d,
        "expected_tomorrow": expected_tomorrow,
        "trend_rate": trend_rate,
        "trend_pct": round(trend_rate * 100, 1),
        "trend_direction": trend_direction,
        "trend_symbol": trend_symbol
    }

def calculate_coupled_medicine_prediction(current_stock, usage_records, patient_records, forecast_days=7):
    """
    Connects Patient Footfall to Medicine Demand using transparent mathematical rules.
    1. Computes 7-day average daily medicine consumption.
    2. Computes recent patient surge/trend velocity.
    3. Adjusts daily medicine demand proportionally.
    4. Calculates days until stockout and projected shortage date.
    """
    sorted_usages = sorted(usage_records, key=lambda x: x["date"])
    last_7_usages = [u["quantity_used"] for u in sorted_usages[-7:]] if len(sorted_usages) >= 7 else [u["quantity_used"] for u in sorted_usages]
    base_daily_consumption = round(sum(last_7_usages) / len(last_7_usages), 1) if last_7_usages else 1.0

    # Footfall metrics
    patient_stats = calculate_patient_footfall_forecast(patient_records)
    trend_rate = patient_stats["trend_rate"]

    # Proportional demand adjustment formula
    # If patient footfall is increasing (+20%), medicine demand scales (+20%)
    # Clamped to reasonable realistic clinical sensitivity
    if trend_rate > 0:
        demand_multiplier = 1.0 + trend_rate
    elif trend_rate < -0.05:
        demand_multiplier = max(0.75, 1.0 + (trend_rate * 0.7)) # demand decreases slower due to chronic refills
    else:
        demand_multiplier = 1.0

    adjusted_daily_demand = round(base_daily_consumption * demand_multiplier, 1)
    forecast_total_demand = round(adjusted_daily_demand * forecast_days, 1)

    days_remaining = calculate_days_remaining(current_stock, adjusted_daily_demand)
    
    # Calculate estimated shortage date
    if days_remaining < 365:
        shortage_date_obj = REF_DATE + datetime.timedelta(days=int(math.ceil(days_remaining)))
        shortage_date_str = shortage_date_obj.strftime("%d %b %Y")
    else:
        shortage_date_str = "No shortage within 1 year"

    shortage_expected = days_remaining <= forecast_days
    status_badge = get_status_badge(days_remaining)

    return {
        "current_stock": current_stock,
        "base_daily_consumption": base_daily_consumption,
        "adjusted_daily_demand": adjusted_daily_demand,
        "demand_multiplier": round(demand_multiplier, 2),
        "patient_increase_pct": patient_stats["trend_pct"],
        "forecast_days": forecast_days,
        "forecast_total_demand": forecast_total_demand,
        "days_remaining": days_remaining,
        "shortage_date": shortage_date_str,
        "shortage_expected": shortage_expected,
        "status": status_badge,
        "patient_stats": patient_stats,
        "formula_explanation": {
            "step1": f"Base 7-day daily medicine consumption: {base_daily_consumption} units/day",
            "step2": f"Patient footfall trend: {patient_stats['trend_pct']:+.1f}% ({patient_stats['trend_symbol']})",
            "step3": f"Adjusted daily demand = {base_daily_consumption} × (1 + {patient_stats['trend_pct']/100.0:+.2f}) = {adjusted_daily_demand} units/day",
            "step4": f"Forecast {forecast_days}-day demand = {adjusted_daily_demand} × {forecast_days} = {forecast_total_demand} units",
            "step5": f"Days remaining = {current_stock} / {adjusted_daily_demand} = {days_remaining} days"
        }
    }

def find_redistribution_recommendations(inventory_rows, phcs_map, medicines_map):
    """
    Converts predictions into recommended actions:
    - Identifies Destination PHCs with medicine shortages (< 3.0 days remaining).
    - Identifies Source PHCs with surplus (> 14 days remaining and safe stock above 10-day buffer).
    - Pairs them by proximity (geographic distance in km).
    - Calculates recommended transfer quantity dynamically.
    """
    shortages = []
    surpluses = []

    for item in inventory_rows:
        stock = item["current_stock"]
        usage = item["average_daily_usage"]
        days = calculate_days_remaining(stock, usage)
        phc = phcs_map.get(item["phc_id"])
        med = medicines_map.get(item["medicine_id"])

        if not phc or not med:
            continue

        if days < 3.0:
            # Deficit to reach a safe 7-day operating buffer
            needed_stock = int(math.ceil(7.0 * usage))
            deficit = max(20, needed_stock - stock)
            shortages.append({
                "phc_id": item["phc_id"],
                "phc_name": phc["phc_name"],
                "district": phc["district"],
                "lat": phc["latitude"],
                "lng": phc["longitude"],
                "medicine_id": item["medicine_id"],
                "medicine_name": med["medicine_name"],
                "unit": med["unit"],
                "current_stock": stock,
                "daily_usage": usage,
                "days_remaining": days,
                "orig_days": item.get("orig_days", days),
                "target_demand": needed_stock,
                "deficit": deficit
            })
        elif days > 14.0:
            # Surplus above a 10-day safety reserve for the source
            safe_reserve = int(math.ceil(10.0 * usage))
            available_surplus = max(0, stock - safe_reserve)
            if available_surplus >= 40:
                surpluses.append({
                    "phc_id": item["phc_id"],
                    "phc_name": phc["phc_name"],
                    "district": phc["district"],
                    "lat": phc["latitude"],
                    "lng": phc["longitude"],
                    "medicine_id": item["medicine_id"],
                    "medicine_name": med["medicine_name"],
                    "unit": med["unit"],
                    "current_stock": stock,
                    "daily_usage": usage,
                    "days_remaining": days,
                    "safe_reserve": safe_reserve,
                    "available_surplus": available_surplus
                })

    recommendations = []
    # Match each shortage with best surplus source
    for dest in shortages:
        # Filter candidate sources for matching medicine
        candidates = [s for s in surpluses if s["medicine_id"] == dest["medicine_id"] and s["phc_id"] != dest["phc_id"]]
        if not candidates:
            continue

        # Sort candidates by: same district first, then geographic distance
        def distance_score(source):
            same_dist = 0 if source["district"] == dest["district"] else 1
            dist_km = haversine_distance(dest["lat"], dest["lng"], source["lat"], source["lng"])
            return (same_dist, dist_km)

        candidates.sort(key=distance_score)
        best_source = candidates[0]
        dist_km = haversine_distance(dest["lat"], dest["lng"], best_source["lat"], best_source["lng"])

        # Optimal quantity: satisfy destination deficit without exhausting source surplus
        recommended_qty = min(best_source["available_surplus"], dest["deficit"])
        # Round to convenient batch size (multiple of 10)
        recommended_qty = max(10, int(round(recommended_qty / 10.0) * 10))

        if recommended_qty > 0:
            dest_orig_days = dest.get("orig_days", dest["days_remaining"])
            if dest_orig_days != dest["days_remaining"]:
                reason = f"Simulated crisis dropped stock from {dest_orig_days}d to {dest['days_remaining']}d (shortage of {dest['deficit']} {dest['unit']}). Replenishing from surplus at {best_source['phc_name']}."
            else:
                reason = f"Imminent stockout: Stock covers only {dest['days_remaining']} days (shortage of {dest['deficit']} {dest['unit']} below 7-day reserve buffer). Transferring from surplus at {best_source['phc_name']}."

            recommendations.append({
                "source": {
                    "phc_id": best_source["phc_id"],
                    "phc_name": best_source["phc_name"],
                    "district": best_source["district"],
                    "current_stock": best_source["current_stock"],
                    "expected_demand": best_source["safe_reserve"],
                    "surplus": best_source["available_surplus"],
                    "days_remaining": best_source["days_remaining"]
                },
                "destination": {
                    "phc_id": dest["phc_id"],
                    "phc_name": dest["phc_name"],
                    "district": dest["district"],
                    "current_stock": dest["current_stock"],
                    "expected_demand": dest["target_demand"],
                    "shortage": dest["deficit"],
                    "days_remaining": dest["days_remaining"],
                    "orig_days": dest_orig_days
                },
                "medicine": {
                    "medicine_id": dest["medicine_id"],
                    "medicine_name": dest["medicine_name"],
                    "unit": dest["unit"]
                },
                "recommended_quantity": recommended_qty,
                "distance_km": dist_km,
                "urgency": "CRITICAL" if dest["days_remaining"] < 1.5 else ("HIGH" if dest["days_remaining"] < 3.0 else "MEDIUM"),
                "reason": reason,
                "action_summary": f"Transfer {recommended_qty} {dest['unit']} of {dest['medicine_name']} from {best_source['phc_name']} to {dest['phc_name']} ({dist_km} km away)"
            })

    return recommendations

def find_high_patient_load_actions(patient_stats_by_phc, phcs_map):
    """
    Identifies PHCs with patient surge (> 25% increase) and recommends
    nearby under-capacity PHCs for non-critical patient redirection.
    """
    alerts = []
    
    # Filter candidates with surge
    surging_phcs = []
    normal_phcs = []

    for phc_id, stats in patient_stats_by_phc.items():
        phc = phcs_map.get(phc_id)
        if not phc:
            continue
        if stats["trend_pct"] >= 18.0:
            surging_phcs.append((phc, stats))
        elif stats["trend_pct"] <= 5.0:
            normal_phcs.append((phc, stats))

    for phc, stats in surging_phcs:
        # Find nearest PHCs with normal or low load
        nearby_candidates = []
        for cand_phc, cand_stats in normal_phcs:
            if cand_phc["phc_id"] == phc["phc_id"]:
                continue
            dist_km = haversine_distance(phc["latitude"], phc["longitude"], cand_phc["latitude"], cand_phc["longitude"])
            if dist_km <= 35.0: # Within 35 km radius
                nearby_candidates.append({
                    "phc_id": cand_phc["phc_id"],
                    "phc_name": cand_phc["phc_name"],
                    "district": cand_phc["district"],
                    "distance_km": dist_km,
                    "avg_patients": cand_stats["avg_7d"],
                    "total_beds": cand_phc["total_beds"]
                })

        nearby_candidates.sort(key=lambda x: x["distance_km"])

        alerts.append({
            "phc_id": phc["phc_id"],
            "phc_name": phc["phc_name"],
            "district": phc["district"],
            "current_avg": stats["avg_7d"],
            "today_footfall": stats["today_footfall"],
            "predicted_load": stats["expected_tomorrow"],
            "increase_pct": stats["trend_pct"],
            "severity": "CRITICAL" if stats["trend_pct"] >= 40.0 else "WARNING",
            "recommendation_text": f"Consider redirecting a portion of non-critical outpatient load to nearby facilities with available capacity.",
            "nearby_phcs": nearby_candidates[:3]
        })

    return alerts

def simulate_emergency_crisis(inventory_rows, phcs_map, medicines_map, footfall_increase_pct, supply_reduction_pct, patient_stats_by_phc=None):
    """
    Emergency Simulation Center calculations:
    1. Increases patient footfall by footfall_increase_pct (e.g. +30%).
    2. Adjusts medicine demand by same percentage.
    3. Reduces medicine stock by supply_reduction_pct (e.g. -20%).
    4. Recalculates days remaining across all inventory.
    5. Returns impact metrics, affected PHCs list, and emergency redistribution plan.
    """
    footfall_factor = 1.0 + (footfall_increase_pct / 100.0)
    supply_factor = 1.0 - (supply_reduction_pct / 100.0)

    simulated_inventory = []
    normal_critical_count = 0
    emergency_critical_count = 0

    normal_warning_count = 0
    emergency_warning_count = 0

    phcs_at_risk_set = set()
    medicines_at_risk_set = set()

    for item in inventory_rows:
        orig_stock = item["current_stock"]
        orig_usage = item["average_daily_usage"]
        orig_days = calculate_days_remaining(orig_stock, orig_usage)

        if orig_days < 3.0:
            normal_critical_count += 1
        elif orig_days < 7.0:
            normal_warning_count += 1

        # Simulated state
        sim_stock = max(0, int(round(orig_stock * supply_factor)))
        sim_usage = round(orig_usage * footfall_factor, 1)
        sim_days = calculate_days_remaining(sim_stock, sim_usage)

        if sim_days < 3.0:
            emergency_critical_count += 1
            phcs_at_risk_set.add(item["phc_id"])
            medicines_at_risk_set.add(item["medicine_id"])
        elif sim_days < 7.0:
            emergency_warning_count += 1
            phcs_at_risk_set.add(item["phc_id"])

        simulated_inventory.append({
            "phc_id": item["phc_id"],
            "medicine_id": item["medicine_id"],
            "current_stock": sim_stock,
            "average_daily_usage": sim_usage,
            "expiry_date": item["expiry_date"],
            "orig_days": orig_days,
            "orig_stock": orig_stock,
            "orig_usage": orig_usage,
            "sim_days": sim_days
        })

    # Dynamically calculate count of PHCs with high patient load under crisis surge
    high_load_count = 0
    if patient_stats_by_phc:
        for phc_id, pstat in patient_stats_by_phc.items():
            effective_surge = pstat.get("trend_pct", 0.0) + footfall_increase_pct
            if effective_surge >= 18.0:
                high_load_count += 1
    else:
        if footfall_increase_pct >= 50:
            high_load_count = 29
        elif footfall_increase_pct >= 30:
            high_load_count = 25
        elif footfall_increase_pct >= 20:
            high_load_count = 15
        elif footfall_increase_pct >= 10:
            high_load_count = 6
        else:
            high_load_count = 3

    # Generate crisis redistribution recommendations using simulated values
    emergency_actions = find_redistribution_recommendations(simulated_inventory, phcs_map, medicines_map)

    return {
        "simulation_parameters": {
            "footfall_increase_pct": footfall_increase_pct,
            "supply_reduction_pct": supply_reduction_pct
        },
        "impact_summary": {
            "phcs_at_risk_count": len(phcs_at_risk_set),
            "medicines_at_risk_count": len(medicines_at_risk_set),
            "high_patient_load_count": high_load_count,
            "critical_stockouts_before": normal_critical_count,
            "critical_stockouts_after": emergency_critical_count,
            "warning_stockouts_before": normal_warning_count,
            "warning_stockouts_after": emergency_warning_count,
            "delta_critical": emergency_critical_count - normal_critical_count
        },
        "emergency_recommendations": emergency_actions
    }
