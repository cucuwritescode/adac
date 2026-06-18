#conftest
#author: Facundo Franchino
"""shared pytest configuration.

tests under integration/ drive the real faust toolchain end-to-end, so
they are marked integration and excluded from the default run (see the
addopts in pyproject.toml). marking by location keeps the individual
test files free of per-test decorators.
"""

from __future__ import annotations


def pytest_collection_modifyitems(items):
    import pytest

    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
