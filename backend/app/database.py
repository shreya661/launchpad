import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "launchpad.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_light_migrations():
    """SQLite has no formal migration system here, and Base.metadata.create_all()
    only creates missing TABLES, not missing COLUMNS on existing tables. This adds
    any new columns introduced after a user's DB already exists, without touching
    their data. Safe to call on every startup — it's a no-op once columns exist."""
    from sqlalchemy import text
    added_columns = {
        "applications": [
            ("auto_applied", "INTEGER DEFAULT 0"),
            ("status_note", "TEXT DEFAULT ''"),
        ],
    }
    with engine.connect() as conn:
        for table, cols in added_columns.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for col_name, col_def in cols:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
        conn.commit()
