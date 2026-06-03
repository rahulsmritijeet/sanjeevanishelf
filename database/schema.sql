-- Sanjeevani Shelf v1.1 Database Schema

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Godown Configuration
CREATE TABLE IF NOT EXISTS godown_config (
    id INTEGER PRIMARY KEY,
    godown_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    location TEXT,
    total_capacity_kg REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crop Capacity
CREATE TABLE IF NOT EXISTS crop_capacity (
    id INTEGER PRIMARY KEY,
    crop_type TEXT UNIQUE NOT NULL,
    allocated_capacity_kg REAL NOT NULL,
    current_stock_kg REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users (Operators, Managers)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    pin_hash TEXT NOT NULL,  -- bcrypt hash
    role TEXT NOT NULL CHECK(role IN ('operator', 'manager', 'admin')),
    full_name TEXT,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Farmers
CREATE TABLE IF NOT EXISTS farmers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    village TEXT,
    aadhaar_hash TEXT,  -- Hashed for privacy
    bank_account TEXT,
    ifsc TEXT,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_transactions INTEGER DEFAULT 0,
    current_balance REAL DEFAULT 0  -- For dues/advances
);

-- RFID Tags
CREATE TABLE IF NOT EXISTS rfid_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'available' CHECK(status IN ('available', 'assigned', 'damaged', 'lost')),
    assigned_to_batch_id INTEGER,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scan TIMESTAMP,
    FOREIGN KEY (assigned_to_batch_id) REFERENCES batches(id) ON DELETE SET NULL
);

-- Batches (Storage Units)
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_code TEXT UNIQUE NOT NULL,
    farmer_id INTEGER NOT NULL,
    crop_type TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    moisture_percent REAL NOT NULL,
    quality_grade TEXT CHECK(quality_grade IN ('A', 'B', 'C', 'REJECT')),
    rfid_uid TEXT,
    stack_location TEXT,
    storage_date DATE NOT NULL,
    expected_retrieval_date DATE,
    expiry_date DATE NOT NULL,
    status TEXT DEFAULT 'stored' CHECK(status IN ('stored', 'sold', 'withdrawn', 'confiscated', 'expired')),
    confiscation_reason TEXT,
    confiscation_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farmer_id) REFERENCES farmers(id),
    FOREIGN KEY (rfid_uid) REFERENCES rfid_tags(uid)
);

CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_expiry ON batches(expiry_date);
CREATE INDEX idx_batches_farmer ON batches(farmer_id);

-- Transactions (Storage, Selling, Buying)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_type TEXT NOT NULL CHECK(txn_type IN ('storage', 'selling', 'buying')),
    txn_code TEXT UNIQUE NOT NULL,
    farmer_id INTEGER NOT NULL,
    batch_id INTEGER,  -- NULL for buying (creates new batch)
    operator_id INTEGER NOT NULL,
    crop_type TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    amount REAL NOT NULL,  -- Positive = farmer pays, Negative = farmer receives
    payment_status TEXT DEFAULT 'pending' CHECK(payment_status IN ('pending', 'paid', 'failed', 'refunded')),
    payment_method TEXT CHECK(payment_method IN ('cash', 'upi', 'razorpay', 'simulation')),
    payment_ref TEXT,
    razorpay_qr_url TEXT,
    razorpay_order_id TEXT,
    txn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (farmer_id) REFERENCES farmers(id),
    FOREIGN KEY (batch_id) REFERENCES batches(id),
    FOREIGN KEY (operator_id) REFERENCES users(id)
);

CREATE INDEX idx_txn_farmer ON transactions(farmer_id);
CREATE INDEX idx_txn_date ON transactions(txn_date);
CREATE INDEX idx_txn_payment ON transactions(payment_status);

-- Payment Events (Audit Trail)
CREATE TABLE IF NOT EXISTS payment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('qr_generated', 'payment_initiated', 'payment_success', 'payment_failed', 'payout_initiated', 'payout_success', 'payout_failed')),
    amount REAL,
    payment_ref TEXT,
    razorpay_data TEXT,  -- JSON blob
    simulated INTEGER DEFAULT 0,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

-- WhatsApp Alerts Queue
CREATE TABLE IF NOT EXISTS whatsapp_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_phone TEXT NOT NULL,
    message TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    template_name TEXT,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'failed', 'simulated')),
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    error TEXT
);

CREATE INDEX idx_whatsapp_status ON whatsapp_queue(status);

-- Sessions (for rollback/recovery)
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    operator_id INTEGER NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('storage', 'selling', 'buying')),
    farmer_id INTEGER,
    status TEXT DEFAULT 'open' CHECK(status IN ('open', 'committed', 'rolled_back')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    snapshot_data TEXT,  -- JSON of session state for rollback
    FOREIGN KEY (operator_id) REFERENCES users(id),
    FOREIGN KEY (farmer_id) REFERENCES farmers(id)
);

-- Event Log (Full Audit Trail)
CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    event_type TEXT NOT NULL,
    entity_type TEXT,  -- batch, transaction, rfid, etc.
    entity_id INTEGER,
    old_value TEXT,  -- JSON
    new_value TEXT,  -- JSON
    operator_id INTEGER,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (operator_id) REFERENCES users(id)
);

CREATE INDEX idx_event_session ON event_log(session_id);
CREATE INDEX idx_event_time ON event_log(occurred_at);

-- Stack Allocation (Physical Storage Locations)
CREATE TABLE IF NOT EXISTS stack_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_code TEXT UNIQUE NOT NULL,
    crop_type TEXT,
    capacity_kg REAL NOT NULL,
    current_weight_kg REAL DEFAULT 0,
    status TEXT DEFAULT 'available' CHECK(status IN ('available', 'full', 'maintenance')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Moisture Readings (Historical for quality tracking)
CREATE TABLE IF NOT EXISTS moisture_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    rfid_uid TEXT,
    sensor_id INTEGER,  -- 1-4 for the 4 sensors
    moisture_percent REAL NOT NULL,
    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id),
    FOREIGN KEY (rfid_uid) REFERENCES rfid_tags(uid)
);

-- System Health / Logs
CREATE TABLE IF NOT EXISTS system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component TEXT NOT NULL,  -- rfid, weight, moisture, db, whatsapp, etc.
    status TEXT NOT NULL CHECK(status IN ('ok', 'warning', 'error')),
    message TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial Data Seeds
INSERT OR IGNORE INTO godown_config (id, godown_id, name, location, total_capacity_kg)
VALUES (1, 'GODOWN001', 'Panchayat Central Storage', 'Village XYZ, District ABC', 100000);

INSERT OR IGNORE INTO crop_capacity (crop_type, allocated_capacity_kg, current_stock_kg)
VALUES 
    ('rice', 40000, 0),
    ('wheat', 30000, 0),
    ('maize', 15000, 0),
    ('pulses', 15000, 0);

-- Default users (PIN: 1234 for all, bcrypt hash below)
-- Hash for '1234': $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2h8VYj8G0u
INSERT OR IGNORE INTO users (id, username, pin_hash, role, full_name, active)
VALUES 
    (1, 'operator', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2h8VYj8G0u', 'operator', 'Demo Operator', 1),
    (2, 'manager', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aq2h8VYj8G0u', 'manager', 'Demo Manager', 1);

-- Sample Stack Locations
INSERT OR IGNORE INTO stack_locations (location_code, crop_type, capacity_kg, current_weight_kg, status)
VALUES 
    ('A1-RICE', 'rice', 5000, 0, 'available'),
    ('A2-RICE', 'rice', 5000, 0, 'available'),
    ('B1-WHEAT', 'wheat', 5000, 0, 'available'),
    ('B2-WHEAT', 'wheat', 5000, 0, 'available'),
    ('C1-MAIZE', 'maize', 3000, 0, 'available'),
    ('D1-PULSES', 'pulses', 3000, 0, 'available');

-- Sample RFID tags for testing
INSERT OR IGNORE INTO rfid_tags (uid, status)
VALUES 
    ('0A1B2C3D', 'available'),
    ('1A2B3C4D', 'available'),
    ('2A3B4C5D', 'available'),
    ('3A4B5C6D', 'available'),
    ('4A5B6C7D', 'available');