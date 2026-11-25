from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

url = settings.database_url
if url.startswith('sqlite:////'):
    db_path = Path(url[len('sqlite:///'):])
    db_path.parent.mkdir(parents=True, exist_ok=True)
elif url.startswith('sqlite:///'):
    db_path = Path(url[len('sqlite:///'):])
    if str(db_path.parent) not in ('', '.'):
        db_path.parent.mkdir(parents=True, exist_ok=True)
connect_args = {'check_same_thread': False, 'timeout': 30} if url.startswith('sqlite') else {}
engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()

def init_db():
    # Ensure the persistent mount is writable and fail startup loudly if it is not.
    if url.startswith('sqlite'):
        with engine.begin() as conn:
            conn.execute(text('PRAGMA journal_mode=WAL'))
            conn.execute(text('PRAGMA foreign_keys=ON'))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY, system_prompt TEXT, created_at TEXT NOT NULL)'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT, created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id))'''))
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)'))
    else:
        with engine.begin() as conn:
            conn.execute(text('''CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY, system_prompt TEXT, created_at TEXT NOT NULL)'''))
            conn.execute(text('''CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT, created_at TEXT NOT NULL)'''))
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)'))
