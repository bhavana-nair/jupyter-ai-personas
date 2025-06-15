import pytest
from unittest.mock import patch

# Apply this patch to all tests to prevent the TypeError in PersonaAwareness._start_heartbeat
@pytest.fixture(autouse=True, scope="session")
def patch_persona_awareness():
    with patch('jupyter_ai.personas.persona_awareness.PersonaAwareness._start_heartbeat', return_value=None):
        yield