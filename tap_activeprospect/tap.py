"""ActiveProspect tap class."""

from __future__ import annotations

import sys

from singer_sdk import Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_activeprospect import streams

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class TapActiveProspect(Tap):
    """Singer tap for ActiveProspect."""

    name = "tap-activeprospect"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType(nullable=False),
            required=True,
            secret=True,  # Flag config as protected.
            title="Password",
            description="The ActiveProspect API Key",
        ),
        th.Property(
            "start_date",
            th.DateTimeType(nullable=False),
            required=True,
            description="The earliest record date to sync",
        ),
    ).to_dict()

    @override
    def discover_streams(self) -> list[streams.ActiveProspectStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            streams.DestinationsStream(self),
            streams.EventsStream(self),
            streams.FlowsStream(self),
        ]


if __name__ == "__main__":
    TapActiveProspect.cli()
