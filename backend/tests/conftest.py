import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def test_engine():
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    root = Path(__file__).resolve().parents[2]
    os.environ["LESSON_MANIFEST_PATH"] = str(root / "web" / "lessons" / "manifest.json")
    os.environ["LINK_OVERRIDES_PATH"] = str(root / "data" / "test-link-overrides.json")
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="session")
def app(test_engine):
    from backend.app import db as db_module
    from backend.app import main as main_module
    from backend.app import models

    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    db_module.engine = test_engine
    db_module.SessionLocal = TestingSessionLocal
    main_module.engine = test_engine
    main_module.SessionLocal = TestingSessionLocal

    models.Base.metadata.create_all(bind=test_engine)
    return main_module.app


@pytest.fixture(autouse=True)
def reset_db(test_engine):
    from backend.app import models

    models.Base.metadata.drop_all(bind=test_engine)
    models.Base.metadata.create_all(bind=test_engine)
    overrides_path = Path(os.environ["LINK_OVERRIDES_PATH"])
    if overrides_path.exists():
        overrides_path.unlink()
    yield


@pytest.fixture()
def db_session():
    from backend.app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(app):
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
