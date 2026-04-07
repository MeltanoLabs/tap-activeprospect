# CLAUDE.md - AI Agent Development Guide for tap-activeprospect

## Project Overview

- **Source**: ActiveProspect **LeadConduit** API (`https://app.leadconduit.com`)
- **Authentication**: Basic Auth — API key as password, any username (see `client.py`)
- **Framework**: Meltano Singer SDK

> **ActiveProspect provides three separate APIs — LeadConduit, TrustedForm, and SuppressionList.**
> This tap covers **LeadConduit only**.

## Implemented Streams

| Stream | Endpoint | Primary Key | Replication |
|--------|----------|-------------|-------------|
| `events` | `GET /events` | `id` | Incremental (`id`, BSON ObjectId cursor) |
| `flows` | `GET /flows` | `id` | Full table |
| `destinations` | `GET /destinations` | `instance_id` | Full table |

## Adding a New Stream

1. Define a class in `tap_activeprospect/streams.py` extending `ActiveProspectStream`
2. Set `name`, `path`, `primary_keys`, and `replication_key` (`None` for full table)
3. Define `schema` using `th.PropertiesList`
4. Register it in `TapActiveProspect.discover_streams()` in `tap.py`
5. Update `meltano.yml` settings and `.env.example` if new config is needed

Minimal example (full-table, non-paginated):

```python
from singer_sdk.pagination import SinglePagePaginator
from tap_activeprospect.client import ActiveProspectStream
from singer_sdk import typing as th

class WidgetsStream(ActiveProspectStream):
    name = "widgets"
    path = "/widgets"
    primary_keys = ("id",)
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("name", th.StringType),
        th.Property("created_at", th.DateTimeType),
        th.Property("updated_at", th.DateTimeType),
    ).to_dict()

    def get_new_paginator(self):
        return SinglePagePaginator()
```

## Keeping `meltano.yml` in Sync

When adding or changing config properties, update all three files in the same commit:
`tap.py` (`config_jsonschema`) → `meltano.yml` (`settings`) → `.env.example`.

**Type mapping:**

| `singer_sdk.typing` | Meltano `kind` |
|---------------------|----------------|
| `StringType` | `string` |
| `IntegerType` | `integer` |
| `BooleanType` | `boolean` |
| `NumberType` | `number` |
| `DateTimeType` | `date_iso8601` |
| `ArrayType` | `array` |
| `ObjectType` | `object` |

Properties with `secret=True` → `sensitive: true` in `meltano.yml`.

## Bumping the Singer SDK Version

1. Check https://sdk.meltano.com/en/latest/deprecation.html for every version between current and target
2. Update `singer-sdk~=X.Y` in `pyproject.toml`
3. `uv sync && uv run pytest`
4. `uv run pytest -W error::DeprecationWarning`

## Reporting SDK Issues

File at https://github.com/meltano/sdk/issues/new/choose. Include SDK version (`uv run tap-activeprospect --version`), Python version, and a minimal reproduction case.

## API Particulars (Discovered from the Live API)

### Authentication

Basic Auth — any username, API key as password. Obtain the key from https://sso.activeprospect.com/account.

> **`Accept: application/json` is required.** Without it the API returns `403 {"error":"misconfigured csrf: check Accept header is set properly"}`.

### OpenAPI Specification

The full OpenAPI 3.1.0 spec is embedded in the Redoc page-data:

```python
import json, requests
data = requests.get(
    "https://activeprospect.redoc.ly/page-data/docs/leadconduit/api/tag/Events/page-data.json"
).json()
spec = json.loads(data["result"]["data"]["contentItem"]["data"]["redocStoreStr"])
paths = spec["definition"]["data"]["paths"]
schemas = spec["definition"]["data"]["components"]["schemas"]
```

### `/events` Pagination and Replication

- Cursor-based via `after_id` (the `id` of the last record). `limit` max 1000. Sort `asc` for incremental.
- Replication key is `id` (24-char BSON ObjectId hex). BSON ObjectIds are lexicographically monotonic → `is_sorted = True` is correct, and the last-seen ID is passed directly as `after_id` on the next run (exact resumption).
- `get_url_params` distinguishes two cases: `^[0-9a-f]{24}$` matches → prior sync ID → `after_id`; otherwise → ISO `start_date` string bootstrapped by SDK → `start` param.
- **Do not use `start_timestamp` as the replication key** — events from the same lead share near-identical millisecond timestamps in non-deterministic order, which causes `InvalidStreamSortException`.

### Undocumented Fields in `/events` Responses

These appear in live data but are absent from the OpenAPI spec:

| Field | Type |
|-------|------|
| `description` | string |
| `disabled_step_count` | integer |
| `flow_acceptance_criteria` | object |
| `flow_caps` | object |
| `flow_pricing` | object |
| `flow_pricing_service` | object |
| `pricing_service` | object |
| `recipient_record_id` | string |
| `recipient_revenue` | number |
| `source_caps` | object |

Integration-specific top-level keys (e.g. `suppressionlist`, `trustedform`, `briteverify`) are the step `key` values — account-specific and unpredictable. `EventsStream.post_process` merges them into `appended` so data is preserved.

### `transactions` field

Despite the singular name, `transactions` is an **array** of objects (not a plain object).
