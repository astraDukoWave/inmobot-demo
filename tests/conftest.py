import pytest
from fastapi.testclient import TestClient

from app.catalog import Catalog
from app.config import Settings
from app.leads import LeadStore
from app.llm.fake import FakeLLM
from app.main import create_app


@pytest.fixture
def catalog():
    return Catalog.load("properties.json")


@pytest.fixture
def leads(tmp_path):
    return LeadStore(str(tmp_path / "test.db"))


@pytest.fixture
def settings(tmp_path):
    return Settings(llm_provider="fake", admin_token="test-admin-token", whatsapp_number="5210000000000",
                    db_path=str(tmp_path / "app.db"))


@pytest.fixture
def make_client(settings, catalog, tmp_path):
    def _make(script=None, **overrides):
        s = Settings(**{**settings.__dict__, **overrides})
        llm = FakeLLM(script or [])
        app = create_app(settings=s, llm=llm, catalog=catalog, leads=LeadStore(s.db_path))
        client = TestClient(app)
        client.llm = llm
        return client
    return _make
