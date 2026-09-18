import os
import sys

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import data_generator
from app import app

def main():
    print("=" * 70)
    print(" SMART HEALTH & SUPPLY CHAIN - PRIMARY HEALTH CENTRE SURVEILLANCE")
    print(" College Hackathon Demonstration System")
    print("=" * 70)
    
    # Initialize DB if needed
    if not os.path.exists(database.DB_PATH):
        print("\n[*] Initializing database schema...")
        database.init_db()
        print("[*] Generating 60-day synthetic operational dataset...")
        data_generator.seed_database()
    else:
        # Check if tables have records
        conn = database.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM phcs").fetchone()[0]
        conn.close()
        if count == 0:
            print("[*] Seeding database with demo facilities and inventory...")
            data_generator.seed_database()

    print("\n[+] Database initialized successfully.")
    print("[+] Core Concept Flow: Patient Footfall -> Medicine Demand -> Stock Prediction -> Shortage Detection -> Recommended Action")
    print("[+] Zero ML models, zero scikit-learn, zero staff data - transparent statistical rules only.")
    print("\n" + "=" * 70)
    print(" >> Application running at: http://127.0.0.1:5000")
    print(" >> Press CTRL+C to terminate the server.")
    print("=" * 70 + "\n")

    app.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == '__main__':
    main()
