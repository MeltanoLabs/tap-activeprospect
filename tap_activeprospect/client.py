"""REST client handling, including ActiveProspectStream base class."""

from __future__ import annotations

import sys

from requests.auth import HTTPBasicAuth
from singer_sdk.streams import RESTStream

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class ActiveProspectStream(RESTStream):
    """ActiveProspect LeadConduit stream class."""

    records_jsonpath = "$[*]"

    @override
    @property
    def url_base(self) -> str:
        """Return the API URL root."""
        return "https://app.leadconduit.com"

    @override
    @property
    def authenticator(self) -> HTTPBasicAuth:
        """Authenticator object for HTTP requests."""
        return HTTPBasicAuth(username="x", password=self.config["api_key"])

    @property
    @override
    def http_headers(self) -> dict:
        """HTTP headers."""
        return {"Accept": "application/json"}
