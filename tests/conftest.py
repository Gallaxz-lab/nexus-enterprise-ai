import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database.connection import Base, get_db
from app.main import app

SQLITE_URL = "sqlite:///./test_infrastructure.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """Builds a fresh database schema before each test case runs."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Provides a thread-isolated transactional database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def test_client():
    """Overrides dependencies to inject the test database context into API routes."""
    def _get_test_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
