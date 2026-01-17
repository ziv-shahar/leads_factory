"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Union

from src.config import DATABASE_URL, USE_SUPABASE_CLIENT

# Import Supabase wrapper if needed
if USE_SUPABASE_CLIENT:
    from src.db.supabase_wrapper import SupabaseSession, get_supabase_session
else:
    from src.db.models import Base

    # Create engine
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,
        max_overflow=20
    )

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    if USE_SUPABASE_CLIENT:
        print("✓ Using Supabase client - tables managed in Supabase dashboard")
        print("  Run supabase_migration.sql in Supabase SQL Editor if tables don't exist")
    else:
        from src.db.models import Base
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")


def drop_db():
    """Drop all database tables (use with caution)."""
    if USE_SUPABASE_CLIENT:
        print("⚠️  Cannot drop tables via Supabase client")
        print("   Use Supabase dashboard to manage tables")
    else:
        from src.db.models import Base
        Base.metadata.drop_all(bind=engine)
        print("✓ Database tables dropped")


@contextmanager
def get_db() -> Generator[Union[Session, SupabaseSession], None, None]:
    """Get database session with automatic cleanup."""
    if USE_SUPABASE_CLIENT:
        db = get_supabase_session()
    else:
        db = SessionLocal()

    try:
        yield db
        if hasattr(db, 'commit'):
            db.commit()
    except Exception:
        if hasattr(db, 'rollback'):
            db.rollback()
        raise
    finally:
        if hasattr(db, 'close'):
            db.close()


def get_db_session() -> Union[Session, SupabaseSession]:
    """Get a new database session (caller must close)."""
    if USE_SUPABASE_CLIENT:
        return get_supabase_session()
    else:
        return SessionLocal()
