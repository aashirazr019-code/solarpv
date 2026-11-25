import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'solar_pv.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT,
            customer_name TEXT,
            site_name TEXT,
            location TEXT,
            status TEXT,
            installation_type TEXT,
            target_ac_kw REAL,
            data_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_revisions (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            revision_number INTEGER,
            data_json TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS panels (
            id TEXT PRIMARY KEY,
            manufacturer TEXT,
            model TEXT,
            rated_power_wp REAL,
            data_json TEXT,
            source TEXT,
            verification_status TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inverters (
            id TEXT PRIMARY KEY,
            manufacturer TEXT,
            model TEXT,
            rated_ac_power_kw REAL,
            data_json TEXT,
            source TEXT,
            verification_status TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS design_results (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            revision INTEGER,
            result_json TEXT,
            status TEXT,
            created_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    ''')
    conn.commit()
    conn.close()

def save_project(project_dict):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Check if project exists
    c.execute('SELECT id FROM projects WHERE id = ?', (project_dict['id'],))
    exists = c.fetchone()
    
    if exists:
        c.execute('''
            UPDATE projects SET
                name=?, customer_name=?, site_name=?, location=?, status=?,
                installation_type=?, target_ac_kw=?, data_json=?, updated_at=?
            WHERE id=?
        ''', (
            project_dict.get('name', ''),
            project_dict.get('customer_name', ''),
            project_dict.get('site_name', ''),
            project_dict.get('location', ''),
            project_dict.get('status', 'draft'),
            project_dict.get('installation_type', ''),
            project_dict.get('target_ac_kw', 0.0),
            json.dumps(project_dict),
            now,
            project_dict['id']
        ))
    else:
        c.execute('''
            INSERT INTO projects (
                id, name, customer_name, site_name, location, status,
                installation_type, target_ac_kw, data_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_dict['id'],
            project_dict.get('name', ''),
            project_dict.get('customer_name', ''),
            project_dict.get('site_name', ''),
            project_dict.get('location', ''),
            project_dict.get('status', 'draft'),
            project_dict.get('installation_type', ''),
            project_dict.get('target_ac_kw', 0.0),
            json.dumps(project_dict),
            now,
            now
        ))
    conn.commit()
    conn.close()

def get_project(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT data_json FROM projects WHERE id = ?', (project_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row['data_json'])
    return None

def list_projects(status_filter=None):
    conn = get_connection()
    c = conn.cursor()
    if status_filter:
        c.execute('SELECT data_json FROM projects WHERE status = ?', (status_filter,))
    else:
        c.execute('SELECT data_json FROM projects WHERE status != "archived"')
    rows = c.fetchall()
    conn.close()
    return [json.loads(row['data_json']) for row in rows]

def delete_project(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()

def duplicate_project(project_id, new_name):
    project = get_project(project_id)
    if not project:
        return None
    import uuid
    project['id'] = str(uuid.uuid4())
    project['name'] = new_name
    save_project(project)
    return project['id']

def archive_project(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE projects SET status = "archived", updated_at = ? WHERE id = ?', (datetime.now().isoformat(), project_id))
    conn.commit()
    conn.close()

def save_project_revision(project_id, data_json, notes='', created_by=''):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    import uuid
    rev_id = str(uuid.uuid4())
    
    c.execute('SELECT MAX(revision_number) as max_rev FROM project_revisions WHERE project_id = ?', (project_id,))
    row = c.fetchone()
    rev_num = (row['max_rev'] or 0) + 1
    
    c.execute('''
        INSERT INTO project_revisions (id, project_id, revision_number, data_json, notes, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (rev_id, project_id, rev_num, data_json, notes, created_by, now))
    conn.commit()
    conn.close()
    return rev_num

def get_project_revisions(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM project_revisions WHERE project_id = ? ORDER BY revision_number DESC', (project_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_panel(panel_dict):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('SELECT id FROM panels WHERE id = ?', (panel_dict['id'],))
    exists = c.fetchone()
    
    if exists:
        c.execute('''
            UPDATE panels SET
                manufacturer=?, model=?, rated_power_wp=?, data_json=?, source=?, verification_status=?
            WHERE id=?
        ''', (
            panel_dict.get('manufacturer', ''),
            panel_dict.get('model', ''),
            panel_dict.get('rated_power_wp', 0.0),
            json.dumps(panel_dict),
            panel_dict.get('source', 'manual'),
            panel_dict.get('verification_status', 'unverified'),
            panel_dict['id']
        ))
    else:
        c.execute('''
            INSERT INTO panels (id, manufacturer, model, rated_power_wp, data_json, source, verification_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            panel_dict['id'],
            panel_dict.get('manufacturer', ''),
            panel_dict.get('model', ''),
            panel_dict.get('rated_power_wp', 0.0),
            json.dumps(panel_dict),
            panel_dict.get('source', 'manual'),
            panel_dict.get('verification_status', 'unverified'),
            now
        ))
    conn.commit()
    conn.close()

def get_panel(panel_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT data_json FROM panels WHERE id = ?', (panel_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row['data_json'])
    return None

def list_panels():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT data_json FROM panels')
    rows = c.fetchall()
    conn.close()
    return [json.loads(row['data_json']) for row in rows]

def delete_panel(panel_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM panels WHERE id = ?', (panel_id,))
    conn.commit()
    conn.close()

def save_inverter(inverter_dict):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('SELECT id FROM inverters WHERE id = ?', (inverter_dict['id'],))
    exists = c.fetchone()
    
    if exists:
        c.execute('''
            UPDATE inverters SET
                manufacturer=?, model=?, rated_ac_power_kw=?, data_json=?, source=?, verification_status=?
            WHERE id=?
        ''', (
            inverter_dict.get('manufacturer', ''),
            inverter_dict.get('model', ''),
            inverter_dict.get('rated_ac_power_kw', 0.0),
            json.dumps(inverter_dict),
            inverter_dict.get('source', 'manual'),
            inverter_dict.get('verification_status', 'unverified'),
            inverter_dict['id']
        ))
    else:
        c.execute('''
            INSERT INTO inverters (id, manufacturer, model, rated_ac_power_kw, data_json, source, verification_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inverter_dict['id'],
            inverter_dict.get('manufacturer', ''),
            inverter_dict.get('model', ''),
            inverter_dict.get('rated_ac_power_kw', 0.0),
            json.dumps(inverter_dict),
            inverter_dict.get('source', 'manual'),
            inverter_dict.get('verification_status', 'unverified'),
            now
        ))
    conn.commit()
    conn.close()

def get_inverter(inverter_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT data_json FROM inverters WHERE id = ?', (inverter_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row['data_json'])
    return None

def list_inverters():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT data_json FROM inverters')
    rows = c.fetchall()
    conn.close()
    return [json.loads(row['data_json']) for row in rows]

def delete_inverter(inverter_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM inverters WHERE id = ?', (inverter_id,))
    conn.commit()
    conn.close()

def save_design_result(project_id, revision, result_json, status):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    import uuid
    res_id = str(uuid.uuid4())
    c.execute('''
        INSERT INTO design_results (id, project_id, revision, result_json, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (res_id, project_id, revision, result_json, status, now))
    conn.commit()
    conn.close()

def get_design_results(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM design_results WHERE project_id = ? ORDER BY created_at DESC', (project_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_project_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as cnt FROM projects')
    total_projects = c.fetchone()['cnt']
    c.execute('SELECT COUNT(*) as cnt FROM projects WHERE status = "draft"')
    draft_count = c.fetchone()['cnt']
    c.execute('SELECT COUNT(*) as cnt FROM projects WHERE status = "approved"')
    approved_count = c.fetchone()['cnt']
    c.execute('SELECT COUNT(*) as cnt FROM projects WHERE status = "archived"')
    archived_count = c.fetchone()['cnt']
    c.execute('SELECT COUNT(*) as cnt FROM panels')
    total_panels = c.fetchone()['cnt']
    c.execute('SELECT COUNT(*) as cnt FROM inverters')
    total_inverters = c.fetchone()['cnt']
    conn.close()
    return {
        'total_projects': total_projects,
        'draft_count': draft_count,
        'approved_count': approved_count,
        'archived_count': archived_count,
        'total_panels': total_panels,
        'total_inverters': total_inverters
    }

init_db()
