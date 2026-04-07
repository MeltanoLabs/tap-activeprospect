"""Tests standard tap features using the built-in SDK tests library."""

import os
from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv
from singer_sdk.testing import SuiteConfig, get_tap_test_class

from tap_activeprospect.tap import TapActiveProspect

load_dotenv()  # populate os.environ from .env before pytestmark is evaluated

pytestmark = pytest.mark.skipif(
    not os.environ.get("TAP_ACTIVEPROSPECT_API_KEY"),
    reason="TAP_ACTIVEPROSPECT_API_KEY not set",
)


def _one_week_ago() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")


# Run standard built-in tap tests from the SDK:
TestTapActiveProspect = get_tap_test_class(
    tap_class=TapActiveProspect,
    config={
        "api_key": os.environ.get("TAP_ACTIVEPROSPECT_API_KEY") or "placeholder",
        "start_date": _one_week_ago(),
    },
    suite_config=SuiteConfig(ignore_no_records=True),
)
