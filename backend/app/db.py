from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL

# Configure connection pool with optimized settings for PostgreSQL
# SQLite doesn't support these pool parameters, so we only apply them for PostgreSQL
# pool_size: number of persistent connections (default was 5)
# max_overflow: number of additional connections when pool is full (default was 10)
# pool_timeout: seconds to wait for connection before raising error (default was 30)
# pool_recycle: recycle connections after this many seconds (prevents stale connections)
# pool_pre_ping: validate connections before using them

if DATABASE_URL.startswith("postgresql"):
    # PostgreSQL connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=40,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
else:
    # SQLite (for tests) - use default pooling
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
