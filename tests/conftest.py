"""Configure test suite."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest."""
    if sys.version_info < (3, 11):
        config.addinivalue_line(
            "filterwarnings",
            "ignore:Python 3.10 will reach its end of life on 2026-10. The Singer SDK will "
            "drop support for it in an upcoming release. Please plan to upgrade to a "
            "supported Python version.:FutureWarning",
        )
