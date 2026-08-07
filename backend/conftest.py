import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    """Evita que el throttling de DRF (p.ej. login) se acumule entre tests."""
    cache.clear()
    yield
