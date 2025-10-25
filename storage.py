import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

class JobStorage:
    """Persistent storage for provisioning jobs using SQLite"""
    
    def __init__(self, db_path='jobs.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                ip TEXT,
                app TEXT,
                message TEXT,
                result TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for faster queries
        conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON jobs(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)')
        
        conn.commit()
        conn.close()
    
    def save_job(self, job_id, data):
        """Save or update job data"""
        conn = sqlite3.connect(self.db_path)
        
        # Convert result dict to JSON string
        result_json = json.dumps(data.get('result')) if data.get('result') else None
        
        conn.execute('''
            INSERT OR REPLACE INTO jobs 
            (job_id, status, progress, ip, app, message, result, error, 
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM jobs WHERE job_id = ?), ?),
                    ?)
        ''', (
            job_id,
            data.get('status'),
            data.get('progress', 0),
            data.get('ip'),
            data.get('app'),
            data.get('message'),
            result_json,
            data.get('error'),
            job_id,
            datetime.now(),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_job(self, job_id):
        """Get job by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            job = dict(row)
            # Parse JSON result back to dict
            if job['result']:
                try:
                    job['result'] = json.loads(job['result'])
                except:
                    pass
            return job
        
        return None
    
    def list_jobs(self, limit=100, status=None):
        """List recent jobs"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        if status:
            cursor = conn.execute(
                'SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?',
                (status, limit)
            )
        else:
            cursor = conn.execute(
                'SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?',
                (limit,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            job = dict(row)
            if job['result']:
                try:
                    job['result'] = json.loads(job['result'])
                except:
                    pass
            jobs.append(job)
        
        return jobs
    
    def cleanup_old_jobs(self, max_age_hours=24):
        """Remove jobs older than specified hours"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        cursor = conn.execute(
            'DELETE FROM jobs WHERE created_at < ? AND status IN ("completed", "failed")',
            (cutoff,)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_stats(self):
        """Get job statistics"""
        conn = sqlite3.connect(self.db_path)
        
        stats = {}
        
        # Total jobs
        cursor = conn.execute('SELECT COUNT(*) as total FROM jobs')
        stats['total'] = cursor.fetchone()[0]
        
        # Jobs by status
        cursor = conn.execute('SELECT status, COUNT(*) as count FROM jobs GROUP BY status')
        stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Jobs by app
        cursor = conn.execute('SELECT app, COUNT(*) as count FROM jobs GROUP BY app')
        stats['by_app'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return stats
