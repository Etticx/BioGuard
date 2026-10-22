"""Private local report records, role accounts and session tokens."""
from contextlib import closing, contextmanager
from hashlib import scrypt, sha256
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import time
from uuid import uuid4
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def password_hash(password, salt):
    return scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


class RecordConflict(ValueError):
    pass


class BaseRecords:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.database = self.directory / "bioguard.sqlite3"

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.database, timeout=15)) as connection, connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection

    def initialize(self, seed=True):
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL, role TEXT NOT NULL,
                    salt TEXT NOT NULL, password_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                    expires_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY, reporter_id TEXT NOT NULL REFERENCES users(id),
                    assigned_team_id TEXT REFERENCES users(id), status TEXT NOT NULL,
                    revision INTEGER NOT NULL, request_key TEXT NOT NULL, digest TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, data TEXT NOT NULL,
                    UNIQUE(reporter_id, request_key));
                CREATE TABLE IF NOT EXISTS photos (
                    id TEXT PRIMARY KEY, report_id TEXT NOT NULL REFERENCES reports(id),
                    kind TEXT NOT NULL, mime TEXT NOT NULL, content BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS login_failures (
                    username TEXT PRIMARY KEY, attempts INTEGER NOT NULL, blocked_until REAL NOT NULL);
            """)
            empty = db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        if seed and empty:
            accounts = []
            for username, display, role in (("grounds", "Ground team", "ground"),
                                             ("ecology", "Ecology field team", "ecology"),
                                             ("management", "Management", "management")):
                password = secrets.token_urlsafe(15)
                self.add_user(username, password, display, role)
                accounts.append({"username": username, "password": password,
                                 "display_name": display, "role": role})
            (self.directory / "local-accounts.json").write_text(json.dumps(accounts, indent=2), "utf-8")

    def add_user(self, username, password, display_name, role):
        if role not in {"ground", "ecology", "management"}:
            raise ValueError("Unknown role")
        identifier, salt = uuid4().hex, secrets.token_hex(16)
        with self.connect() as db:
            db.execute("INSERT INTO users VALUES (?,?,?,?,?,?)",
                       (identifier, username, display_name, role, salt, password_hash(password, salt)))
        return identifier

    @staticmethod
    def public_user(row):
        return {key: row[key] for key in ("id", "username", "display_name", "role")}

    def login(self, username, password):
        with self.connect() as db:
            failure = db.execute("SELECT * FROM login_failures WHERE username=?", (username,)).fetchone()
            if failure and failure["blocked_until"] > time.time():
                return None
            row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            # Use the same costly password check even when the account does not exist.
            salt = row["salt"] if row else "00" * 16
            valid = hmac.compare_digest(password_hash(password, salt), row["password_hash"] if row else "00" * 64)
            if not row or not valid:
                attempts = (failure["attempts"] if failure else 0) + 1
                blocked = time.time() + 300 if attempts >= 5 else 0
                db.execute("INSERT OR REPLACE INTO login_failures VALUES (?,?,?)", (username, attempts % 5, blocked))
                return None
            db.execute("DELETE FROM login_failures WHERE username=?", (username,))
            db.execute("DELETE FROM sessions WHERE expires_at<?", (time.time(),))
            token = secrets.token_urlsafe(32)
            db.execute("INSERT INTO sessions VALUES (?,?,?)",
                       (sha256(token.encode()).hexdigest(), row["id"], time.time() + 8 * 3600))
            return {"token": token, "user": self.public_user(row)}

    def session_user(self, token):
        if not token:
            return None
        with self.connect() as db:
            row = db.execute("""SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id
                WHERE token_hash=? AND expires_at>?""", (sha256(token.encode()).hexdigest(), time.time())).fetchone()
            return self.public_user(row) if row else None

    def logout(self, token):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (sha256(token.encode()).hexdigest(),))

    def teams(self):
        with self.connect() as db:
            return [self.public_user(row) for row in db.execute("SELECT * FROM users WHERE role='ecology' ORDER BY display_name")]

    def create_report(self, user, details, prediction, provenance, photos, request_key, digest):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT id,digest FROM reports WHERE reporter_id=? AND request_key=?",
                                  (user["id"], request_key)).fetchone()
            if existing:
                if existing["digest"] != digest:
                    raise RecordConflict("This submission key was already used for a different report.")
                return self.get_report(existing["id"], user)
            identifier, timestamp = uuid4().hex, now()
            data = {**details, "prediction": prediction, "model": provenance,
                    "reporter_name": user["display_name"], "review": None,
                    "history": [{"at": timestamp, "action": "submitted", "by": user["display_name"]}]}
            db.execute("INSERT INTO reports(id,reporter_id,assigned_team_id,status,revision,request_key,digest,created_at,updated_at,data) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (identifier, user["id"], None, "submitted", 1, request_key, digest,
                        timestamp, timestamp, json.dumps(data)))
            for kind, mime, content in photos:
                db.execute("INSERT INTO photos(id,report_id,kind,mime,content) VALUES (?,?,?,?,?)", (uuid4().hex, identifier, kind, mime, content))
        return self.get_report(identifier, user)

    def get_report(self, identifier, user):
        with self.connect() as db:
            row = db.execute("SELECT * FROM reports WHERE id=?", (identifier,)).fetchone()
            if row is None or not self.can_access(row, user):
                return None
            data = json.loads(row["data"])
            data.update({key: row[key] for key in ("id", "status", "revision", "created_at", "updated_at", "reporter_id", "assigned_team_id")})
            data["reference"] = "BG-" + identifier[:8].upper()
            data["photos"] = [{"id": photo["id"], "kind": photo["kind"], "url": f"/reports/{identifier}/photos/{photo['id']}"}
                              for photo in db.execute("SELECT id,kind FROM photos WHERE report_id=? ORDER BY rowid", (identifier,))]
            return data

    def list_reports(self, user):
        with self.connect() as db:
            if user["role"] == "management":
                rows = db.execute("SELECT id FROM reports ORDER BY created_at DESC").fetchall()
            else:
                rows = db.execute("SELECT id FROM reports WHERE reporter_id=? OR assigned_team_id=? ORDER BY created_at DESC",
                                  (user["id"], user["id"])).fetchall()
        return [self.get_report(row["id"], user) for row in rows]

    def get_photo(self, report_id, photo_id, user):
        if not self.get_report(report_id, user):
            return None
        with self.connect() as db:
            row = db.execute("SELECT mime,content FROM photos WHERE id=? AND report_id=?", (photo_id, report_id)).fetchone()
            return (row["mime"], row["content"]) if row else None

    def review_report(self, identifier, user, review):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM reports WHERE id=?", (identifier,)).fetchone()
            if not row:
                return None
            if row["revision"] != review["revision"] or row["status"] not in {"submitted", "needs_info"}:
                raise RecordConflict("This report has changed. Refresh it before reviewing.")
            team_id = review.get("assigned_team_id") if review["decision"] == "assign" else None
            if team_id and not db.execute("SELECT id FROM users WHERE id=? AND role='ecology'", (team_id,)).fetchone():
                raise ValueError("Choose an existing ecology team.")
            status = {"assign": "assigned", "no_action": "closed", "request_info": "needs_info"}[review["decision"]]
            timestamp, data = now(), json.loads(row["data"])
            data["review"] = {**review, "reviewer_name": user["display_name"], "reviewed_at": timestamp}
            if team_id:
                data["review"]["assigned_team_name"] = db.execute("SELECT display_name FROM users WHERE id=?", (team_id,)).fetchone()[0]
            data["history"].append({"at": timestamp, "action": status, "by": user["display_name"], "notes": review["notes"]})
            db.execute("UPDATE reports SET assigned_team_id=?,status=?,revision=revision+1,updated_at=?,data=? WHERE id=?",
                       (team_id, status, timestamp, json.dumps(data), identifier))
        return self.get_report(identifier, user)

    def add_information(self, identifier, user, content, mime, notes, revision):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM reports WHERE id=? AND reporter_id=?", (identifier, user["id"])).fetchone()
            if not row:
                return None
            if row["status"] != "needs_info" or row["revision"] != revision:
                raise RecordConflict("This report has changed. Refresh it before adding information.")
            timestamp, data = now(), json.loads(row["data"])
            data["history"].append({"at": timestamp, "action": "information_added", "by": user["display_name"], "notes": notes})
            db.execute("INSERT INTO photos(id,report_id,kind,mime,content) VALUES (?,?,?,?,?)", (uuid4().hex, identifier, "additional", mime, content))
            db.execute("UPDATE reports SET status='submitted',revision=revision+1,updated_at=?,data=? WHERE id=?",
                       (timestamp, json.dumps(data), identifier))
        return self.get_report(identifier, user)


from operations import OperationsMixin


from inspection_results import InspectionResultsMixin


class Records(InspectionResultsMixin, OperationsMixin, BaseRecords):
    """Versioned reports, work visits, staff accounts and restoration evidence."""
