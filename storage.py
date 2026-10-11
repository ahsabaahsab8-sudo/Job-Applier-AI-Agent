import sqlite3
import csv
from datetime import datetime
from pathlib import Path
from config import DB_PATH, CSV_PATH

class ApplicationStorage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    title TEXT,
                    company TEXT,
                    location TEXT,
                    job_url TEXT,
                    target_email TEXT,
                    email_confidence TEXT,
                    match_percentage INTEGER,
                    status TEXT,
                    cover_letter TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def is_already_processed(self, job_id: str, title: str = "", company: str = "") -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if job_id:
                cursor.execute("SELECT 1 FROM applications WHERE job_id = ?", (str(job_id),))
                if cursor.fetchone():
                    return True
            # Secondary check by title and company to avoid duplicate postings
            if title and company:
                cursor.execute(
                    "SELECT 1 FROM applications WHERE LOWER(title) = LOWER(?) AND LOWER(company) = LOWER(?)",
                    (title, company)
                )
                return cursor.fetchone() is not None
            return False

    def is_applied(self, job_id: str, title: str = "", company: str = "") -> bool:
        return self.is_already_processed(job_id, title, company)

    def record_application(self, data: dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO applications 
                (job_id, title, company, location, job_url, target_email, email_confidence, match_percentage, status, cover_letter)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(data.get("job_id", "")),
                data.get("title", ""),
                data.get("company", ""),
                data.get("location", ""),
                data.get("job_url", ""),
                data.get("target_email", ""),
                data.get("email_confidence", "unknown"),
                data.get("match_percentage", 0),
                data.get("status", "pending"),
                data.get("cover_letter", "")
            ))
            conn.commit()
        self.export_csv()

    def export_csv(self, export_path: Path = CSV_PATH):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            if not rows:
                return

            with open(export_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(rows[0].keys())
                for row in rows:
                    writer.writerow(list(row))

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM applications")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'sent'")
            sent = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'dry_run_preview'")
            previews = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'failed'")
            failed = cursor.fetchone()[0]

            return {
                "total_applications": total,
                "sent": sent,
                "dry_run_previews": previews,
                "failed": failed
            }
