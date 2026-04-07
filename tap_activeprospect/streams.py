"""Stream type classes for tap-activeprospect."""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING, Any

from singer_sdk import typing as th
from singer_sdk.pagination import SinglePagePaginator

from tap_activeprospect.client import ActiveProspectStream

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

if TYPE_CHECKING:
    from singer_sdk.helpers.types import Context

# Freeform object type for dynamic/open-ended fields
_OBJECT = th.ObjectType()

# Pattern for a 24-character BSON ObjectId (hex string)
_BSON_ID_RE = re.compile(r"^[0-9a-f]{24}$")


class EventsStream(ActiveProspectStream):
    """Events stream for ActiveProspect LeadConduit.

    Each event is a snapshot of what happened to a lead at a particular step
    in a flow. Event types include: source, recipient, filter,
    feedback-received, feedback-sent, and retry.

    Incremental sync is supported using the event ``id`` (a BSON ObjectId) as
    the replication key. BSON ObjectIds are lexicographically monotonic, so
    ``is_sorted = True`` is safe and resumption after an interruption is exact:
    the last-seen ID is passed directly as ``after_id`` on the next run.

    On the first sync (no prior state), the ``start_date`` config value is
    used as a ``start`` query parameter to filter events.

    Pagination uses a cursor based on the event ``id`` field.

    Any integration-specific fields not present in the static schema (e.g.
    ``suppressionlist``, ``trustedform``, step ``key`` values) are merged into
    the ``appended`` field by ``post_process`` so that no data is silently
    dropped.
    """

    name = "events"
    path = "/events"
    primary_keys = ("id",)
    replication_key = "id"
    is_sorted = True

    # Get id from the last record
    next_page_token_jsonpath = "$[-1].id"  # noqa: S105

    # The maximum number of events to return (maximum limit is 1000, default 100)
    LIMIT = 1_000

    schema = th.PropertiesList(
        # ── Base EventProperties ──────────────────────────────────────────────
        th.Property("id", th.StringType, required=True),
        th.Property("type", th.StringType, required=True),
        th.Property("outcome", th.StringType, required=True),
        th.Property("reason", th.StringType),
        th.Property("vars", _OBJECT),
        th.Property("host", th.StringType),
        th.Property("start_timestamp", th.IntegerType),
        th.Property("end_timestamp", th.IntegerType),
        th.Property("ms", th.IntegerType),
        th.Property("wait_ms", th.IntegerType),
        th.Property("overhead_ms", th.IntegerType),
        th.Property("lag_ms", th.IntegerType),
        th.Property("total_ms", th.IntegerType),
        th.Property("handler_version", th.StringType),
        th.Property("version", th.StringType),
        th.Property("cap_reached", th.BooleanType),
        th.Property("flow_ping_limits", _OBJECT),
        th.Property("source_ping_limits", _OBJECT),
        th.Property("ping_limit_reached", th.BooleanType),
        th.Property("expires_at", th.DateTimeType),
        th.Property("firehose", _OBJECT),
        # ── source-event ─────────────────────────────────────────────────────
        th.Property("module_id", th.StringType),
        th.Property("package_version", th.StringType),
        th.Property("acceptance_criteria", _OBJECT),
        th.Property("step_count", th.IntegerType),
        th.Property("appended", _OBJECT),
        th.Property("request", _OBJECT),
        th.Property("response", _OBJECT),
        # ── recipient / retry-event ───────────────────────────────────────────
        th.Property("step_id", th.StringType),
        th.Property("caps", th.ArrayType(_OBJECT)),
        th.Property("caps_reached", th.BooleanType),
        th.Property("key", th.StringType),
        th.Property("cost", th.NumberType),
        th.Property("purchase_price", th.NumberType),
        th.Property("sale_price", th.NumberType),
        th.Property("revenue", th.NumberType),
        th.Property("credential", _OBJECT),
        th.Property("credential_updated", th.BooleanType),
        th.Property("rule_set", _OBJECT),
        th.Property("mappings", th.ArrayType(th.ObjectType())),
        th.Property("pricing", _OBJECT),
        th.Property("transactions", th.ArrayType(th.ObjectType())),
        # ── retry-event ───────────────────────────────────────────────────────
        th.Property("retry_status", th.StringType),
        # ── feedback-received / feedback-sent events ──────────────────────────
        th.Property("recipient_event_id", th.StringType),
        th.Property("feedback", _OBJECT),
        # ── undocumented fields observed in live API responses ─────────────────
        th.Property("description", th.StringType),
        th.Property("disabled_step_count", th.IntegerType),
        th.Property("flow_acceptance_criteria", _OBJECT),
        th.Property("flow_caps", _OBJECT),
        th.Property("flow_pricing", _OBJECT),
        th.Property("flow_pricing_service", _OBJECT),
        th.Property("pricing_service", _OBJECT),
        th.Property("recipient_record_id", th.StringType),
        th.Property("recipient_revenue", th.NumberType),
        th.Property("source_caps", _OBJECT),
    ).to_dict()

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: str | None,
    ) -> dict[str, Any]:
        """Return URL query parameters for the events endpoint.

        Pagination within a sync uses ``after_id`` (the ID of the last record
        from the previous page). On the first page of a subsequent incremental
        sync, the last-seen event ``id`` from state is used as ``after_id``
        directly (exact resumption). On the very first sync, the ``start_date``
        config value is passed as the ``start`` query parameter.

        Args:
            context: The stream context.
            next_page_token: The cursor from the previous page (event ID).

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict[str, Any] = {
            "limit": self.LIMIT,
            "sort": "asc",
        }

        if next_page_token:
            return {
                **params,
                "after_id": next_page_token,
            }

        starting_value: str | None = self.get_starting_replication_key_value(context)
        if starting_value and _BSON_ID_RE.match(starting_value):
            # Last-seen event ID from a prior incremental sync — resume exactly
            return {
                **params,
                "after_id": starting_value,
            }

        if starting_value is not None:
            # SDK bootstraps state with the start_date ISO string on first sync
            return {
                **params,
                "start": starting_value,
            }

        return params

    @override
    def post_process(
        self,
        row: dict,
        context: Context | None = None,
    ) -> dict | None:
        """Merge integration-specific fields into ``appended``.

        Recipient events carry integration output under a dynamic key matching
        the step's ``key`` field (e.g. ``suppressionlist``, ``trustedform``).
        These keys are account-specific and cannot be statically declared in
        the schema. Rather than silently dropping them, this method merges any
        unrecognised top-level fields into the ``appended`` object so the data
        is preserved for downstream use.

        Args:
            row: An individual record from the stream.
            context: The stream context.

        Returns:
            The updated record dictionary.
        """
        known_fields = self.schema["properties"].keys()
        extra = {k: v for k, v in row.items() if k not in known_fields}
        if extra:
            appended = row.get("appended") or {}
            appended.update(extra)
            row["appended"] = appended
            for k in extra:
                del row[k]
        return row


class DestinationsStream(ActiveProspectStream):
    """Destinations stream for ActiveProspect LeadConduit.

    Destinations are Prismatic integration instances configured in the
    LeadConduit app. This endpoint returns all destinations for the account
    in a single page; there is no server-side pagination or time filtering.
    """

    name = "destinations"
    path = "/destinations"
    primary_keys = ("instance_id",)
    replication_key = None

    schema = th.PropertiesList(
        th.Property("instance_id", th.StringType, required=True),
        th.Property("name", th.StringType),
        th.Property("integration_name", th.StringType),
        th.Property("integration_icon_url", th.StringType),
        th.Property(
            "actions",
            th.ArrayType(
                th.ObjectType(
                    th.Property("name", th.StringType),
                    th.Property("action_id", th.StringType),
                    th.Property("webhook_url", th.StringType),
                )
            ),
        ),
        # Included only when the request is made with include=flow_usages
        th.Property("flow_usages", _OBJECT),
    ).to_dict()

    @override
    def get_new_paginator(self) -> SinglePagePaginator:
        """Return a single-page paginator (the endpoint returns all records at once)."""
        return SinglePagePaginator()


class FlowsStream(ActiveProspectStream):
    """Flows stream for ActiveProspect LeadConduit.

    A flow defines the complete processing pipeline for lead submissions,
    from data ingestion through delivery. This endpoint returns all flows for
    the account in a single page; there is no server-side pagination or time
    filtering.

    Full-table replication is used so that flows last modified before
    ``start_date`` are not silently omitted on the initial sync.
    """

    name = "flows"
    path = "/flows"
    primary_keys = ("id",)
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("name", th.StringType, required=True),
        th.Property("enabled", th.BooleanType),
        th.Property("fields", th.ArrayType(th.StringType)),
        th.Property("sources", th.ArrayType(th.ObjectType())),
        th.Property("steps", th.ArrayType(th.ObjectType())),
        th.Property("destinations", th.ArrayType(th.ObjectType())),
        th.Property("caps", _OBJECT),
        th.Property("acceptance_criteria", _OBJECT),
        th.Property("pricing", _OBJECT),
        th.Property("list_checks", _OBJECT),
        th.Property("ping_enabled", th.BooleanType),
        th.Property("ping_limits", _OBJECT),
        th.Property("pricing_service", _OBJECT),
        th.Property("firehose", _OBJECT),
        th.Property("errors", _OBJECT),
        th.Property("level", th.StringType),
        th.Property("created_at", th.DateTimeType),
        th.Property("updated_at", th.DateTimeType),
    ).to_dict()

    @override
    def get_new_paginator(self) -> SinglePagePaginator:
        """Return a single-page paginator (the endpoint returns all records at once)."""
        return SinglePagePaginator()
