import urllib.request
import json
import sys

# Ensure UTF-8 stdout on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=" * 60)
print("VERIFYING LIVE SERVER HTTP RESPONSES")
print("=" * 60)

# 1. Check index.html
with urllib.request.urlopen('http://127.0.0.1:5000/') as resp:
    html = resp.read().decode('utf-8')
    assert 'Formula Applied' not in html, "Raw formula still present in HTML"
    assert 'Demand = Base Demand' in html, "Clean demand formula not found"
    assert 'API KEY' not in html, "API key text found"
    assert 'Search medicine...' in html, "Search medicine placeholder not found"
    print("[OK] index.html verified: Clean formulas, correct placeholders, no raw LaTeX.")

# 2. Check map.js
with urllib.request.urlopen('http://127.0.0.1:5000/js/map.js') as resp:
    map_js = resp.read().decode('utf-8')
    assert 'cartocdn' not in map_js, "Carto CDN found in map.js"
    assert 'tile.openstreetmap.org' in map_js, "OpenStreetMap tile server not found in map.js"
    print("[OK] map.js verified: OpenStreetMap tiles active, zero Carto / API key references.")

# 3. Check /api/emergency/simulate
req = urllib.request.Request(
    'http://127.0.0.1:5000/api/emergency/simulate',
    data=json.dumps({'footfall_increase_pct': 30, 'supply_reduction_pct': 20}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    imp = data['impact_summary']
    assert 'high_patient_load_count' in imp, "high_patient_load_count missing"
    assert len(data['emergency_recommendations']) > 0, "No emergency recommendations"
    rec = data['emergency_recommendations'][0]
    assert 'reason' in rec and 'urgency' in rec and 'distance_km' in rec, "Missing fields in emergency recommendation"
    print(f"[OK] /api/emergency/simulate live response verified:")
    print(f"     High load PHCs under +30% crisis: {imp['high_patient_load_count']}")
    print(f"     Critical stockouts before/after:   {imp['critical_stockouts_before']} -> {imp['critical_stockouts_after']}")
    print(f"     First crisis action: {rec['action_summary']}")
    print(f"     Crisis Reason: {rec['reason']}")

print("\nALL LIVE HTTP CHECKS PASSED WITH 100% SUCCESS!")
