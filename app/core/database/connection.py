from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.encoded_database_url, 
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency yielding a clean database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
