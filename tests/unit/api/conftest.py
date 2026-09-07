"""Cliente HTTP de pruebas sobre la app FastAPI con el contenedor de fakes."""

from types import SimpleNamespace

import httpx
import pytest

from chathce.adapters.memory import ScriptedTurn
from chathce.api.app import create_app
from chathce.domain.identity import Principal
from tests.fakes.container_factory import build_test_container
from tests.fakes.mimic_fixtures import fixtures_available, load_manifest

SUBJECT = load_manifest()["subject_ids"][0] if fixtures_available() else 10001217


def _settings():
    return SimpleNamespace(api=SimpleNamespace(cors_allowed_origins=["http://localhost:8501"], docs_enabled=True, sse_ping_s=1,
                                               ready_cache_s=0, environment="dev"))


@pytest.fixture
def api(request):
    turns = getattr(request, "param", None) or [ScriptedTurn(text="Hola desde la API")]
    container = build_test_container(turns)
    clinician = Principal(user_id="clin-1", roles=frozenset({"clinician"}), display_name="Dra. Test")
    researcher = Principal(user_id="res-1", roles=frozenset({"researcher"}), display_name="Investigador")
    container.identity.tokens["tok-clinician"] = clinician
    container.identity.tokens["tok-researcher"] = researcher
    app = create_app(container, settings=_settings())
    return SimpleNamespace(app=app, container=container, subject=SUBJECT)


@pytest.fixture
async def client(api):
    transport = httpx.ASGITransport(app=api.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


def auth(token: str = "tok-clinician") -> dict:
    return {"Authorization": f"Bearer {token}"}
