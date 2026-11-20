import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import config

def get_db_connection() -> sqlite3.Connection:
    """Creates a new SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(str(config.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initializes SQLite tables if they do not already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        incident_type TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        confidence REAL NOT NULL,
        description TEXT NOT NULL,
        location_tag TEXT DEFAULT 'Camera Junction Alpha',
        objects_involved TEXT DEFAULT '[]',
        bounding_boxes TEXT DEFAULT '[]',
        snapshot_path TEXT,
        status TEXT DEFAULT 'ACTIVE',
        simulated_dispatch_status TEXT DEFAULT 'STANDBY',
        simulated_dispatch_notes TEXT DEFAULT 'No emergency vehicle requested.'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        details TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def insert_incident(
    incident_type: str,
    risk_level: str,
    confidence: float,
    description: str,
    location_tag: str = "Camera Junction Alpha",
    objects_involved: Optional[List[str]] = None,
    bounding_boxes: Optional[List[Dict[str, Any]]] = None,
    snapshot_path: Optional[str] = None,
    status: str = "ACTIVE",
    simulated_dispatch_status: str = "STANDBY",
    simulated_dispatch_notes: str = "No emergency vehicle requested."
) -> int:
    """Inserts an incident record into the database and returns the new ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    now_iso = datetime.now(timezone.utc).isoformat()
    objects_json = json.dumps(objects_involved or [])
    boxes_json = json.dumps(bounding_boxes or [])

    cursor.execute("""
        INSERT INTO incidents (
            timestamp, incident_type, risk_level, confidence, description,
            location_tag, objects_involved, bounding_boxes, snapshot_path,
            status, simulated_dispatch_status, simulated_dispatch_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_iso, incident_type, risk_level, round(confidence, 4), description,
        location_tag, objects_json, boxes_json, snapshot_path,
        status, simulated_dispatch_status, simulated_dispatch_notes
    ))

    incident_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return incident_id

def get_incidents(
    limit: int = 50,
    risk_level: Optional[str] = None,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves list of incidents, optionally filtered by risk_level or status."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM incidents"
    params = []
    conditions = []

    if risk_level:
        conditions.append("risk_level = ?")
        params.append(risk_level.upper())

    if status:
        conditions.append("status = ?")
        params.append(status.upper())

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["objects_involved"] = json.loads(item.get("objects_involved") or "[]")
        except Exception:
            item["objects_involved"] = []
        try:
            item["bounding_boxes"] = json.loads(item.get("bounding_boxes") or "[]")
        except Exception:
            item["bounding_boxes"] = []
        results.append(item)

    return results

def get_incident_by_id(incident_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single incident by its primary key ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    try:
        item["objects_involved"] = json.loads(item.get("objects_involved") or "[]")
    except Exception:
        item["objects_involved"] = []
    try:
        item["bounding_boxes"] = json.loads(item.get("bounding_boxes") or "[]")
    except Exception:
        item["bounding_boxes"] = []

    return item

def update_incident_status(
    incident_id: int,
    status: Optional[str] = None,
    simulated_dispatch_status: Optional[str] = None,
    simulated_dispatch_notes: Optional[str] = None
) -> bool:
    """Updates status or simulated dispatch attributes of an existing incident."""
    conn = get_db_connection()
    cursor = conn.cursor()

    fields = []
    params = []

    if status is not None:
        fields.append("status = ?")
        params.append(status.upper())

    if simulated_dispatch_status is not None:
        fields.append("simulated_dispatch_status = ?")
        params.append(simulated_dispatch_status.upper())

    if simulated_dispatch_notes is not None:
        fields.append("simulated_dispatch_notes = ?")
        params.append(simulated_dispatch_notes)

    if not fields:
        conn.close()
        return False

    params.append(incident_id)
    query = f"UPDATE incidents SET {', '.join(fields)} WHERE id = ?"

    cursor.execute(query, params)
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def get_incident_stats() -> Dict[str, Any]:
    """Computes summary statistics for the dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM incidents")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE risk_level = 'HIGH'")
    high_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE risk_level = 'MEDIUM'")
    medium_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE risk_level = 'LOW'")
    low_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'ACTIVE'")
    active_incidents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents WHERE simulated_dispatch_status = 'SIMULATED_DISPATCHED'")
    simulated_dispatched = cursor.fetchone()[0]

    conn.close()

    return {
        "total_incidents": total,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "active_incidents": active_incidents,
        "simulated_dispatched": simulated_dispatched
    }

# Automatically initialize database schema when imported
init_db()
