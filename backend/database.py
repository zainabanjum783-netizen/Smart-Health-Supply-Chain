import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'smart_health.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. PHC table (No staff fields!)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS phcs (
        phc_id TEXT PRIMARY KEY,
        phc_name TEXT NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'Uttar Pradesh',
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        total_beds INTEGER NOT NULL DEFAULT 10
    );
    """)

    # 2. Medicines master table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        medicine_id TEXT PRIMARY KEY,
        medicine_name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit TEXT NOT NULL DEFAULT 'tablets'
    );
    """)

    # 3. Inventory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        phc_id TEXT NOT NULL,
        medicine_id TEXT NOT NULL,
        current_stock INTEGER NOT NULL,
        average_daily_usage REAL NOT NULL,
        expiry_date TEXT NOT NULL,
        PRIMARY KEY (phc_id, medicine_id),
        FOREIGN KEY (phc_id) REFERENCES phcs(phc_id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(medicine_id) ON DELETE CASCADE
    );
    """)

    # 4. Historical medicine usage
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicine_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phc_id TEXT NOT NULL,
        medicine_id TEXT NOT NULL,
        date TEXT NOT NULL,
        quantity_used INTEGER NOT NULL,
        FOREIGN KEY (phc_id) REFERENCES phcs(phc_id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(medicine_id) ON DELETE CASCADE
    );
    """)

    # 5. Patient footfall data (No staff fields!)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phc_id TEXT NOT NULL,
        date TEXT NOT NULL,
        opd_patients INTEGER NOT NULL,
        ipd_patients INTEGER NOT NULL,
        FOREIGN KEY (phc_id) REFERENCES phcs(phc_id) ON DELETE CASCADE
    );
    """)

    # 6. Actions & Redistribution audit table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT NOT NULL DEFAULT 'REDISTRIBUTION',
        source_phc_id TEXT NOT NULL,
        dest_phc_id TEXT NOT NULL,
        medicine_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'COMPLETED',
        timestamp TEXT NOT NULL,
        rationale TEXT NOT NULL,
        FOREIGN KEY (source_phc_id) REFERENCES phcs(phc_id),
        FOREIGN KEY (dest_phc_id) REFERENCES phcs(phc_id),
        FOREIGN KEY (medicine_id) REFERENCES medicines(medicine_id)
    );
    """)

    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_phc ON inventory(phc_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_med ON inventory(medicine_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_phc_med_date ON medicine_usage(phc_id, medicine_id, date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_phc_date ON patients(phc_id, date);")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database schema initialized successfully at:", DB_PATH)
