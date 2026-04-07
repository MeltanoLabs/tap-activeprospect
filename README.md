# tap-activeprospect

`tap-activeprospect` is a Singer tap for [ActiveProspect LeadConduit](https://activeprospect.com/leadconduit/).

> **Note:** ActiveProspect provides three separate APIs — **LeadConduit**, **TrustedForm**, and **SuppressionList**. This tap covers the **LeadConduit** API only.

Built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

## Streams

| Stream | Endpoint | Primary Key | Replication |
|--------|----------|-------------|-------------|
| `events` | [`GET /events`](https://activeprospect.redoc.ly/docs/leadconduit/api/tag/Leads/) | `id` | Incremental (`id`) |
| `flows` | [`GET /flows`](https://activeprospect.redoc.ly/docs/leadconduit/api/tag/Flows/) | `id` | Full table |
| `destinations` | [`GET /destinations`](https://activeprospect.redoc.ly/docs/leadconduit/api/tag/Destinations/) | `instance_id` | Full table |

## Configuration

### Accepted Config Options

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `api_key` | Yes | | LeadConduit API key. Used as the Basic Auth password; the username is ignored. Obtain yours from [ActiveProspect account settings](https://sso.activeprospect.com/account). |
| `start_date` | Yes | | Earliest date to sync events from (ISO 8601, e.g. `2024-01-01T00:00:00Z`). |

```bash
tap-activeprospect --about --format=markdown
```

### Configure using environment variables

```bash
TAP_ACTIVEPROSPECT_API_KEY=your_api_key_here
TAP_ACTIVEPROSPECT_START_DATE=2024-01-01T00:00:00Z
```

This Singer tap will automatically import any environment variables within the working directory's
`.env` if the `--config=ENV` is provided, such that config values will be considered if a matching
environment variable is set either in the terminal context or in the `.env` file.

### Source Authentication

The LeadConduit API uses HTTP Basic Auth. Pass your API key as the password; the username is
ignored (the tap uses `x` as a placeholder). The `Accept: application/json` header is also
required — the tap sets this automatically.

```bash
curl -u x:YOUR_API_KEY -H 'Accept: application/json' \
  https://app.leadconduit.com/flows
```

## Usage

You can easily run `tap-activeprospect` by itself or in a pipeline using [Meltano](https://meltano.com/).

### Executing the Tap Directly

```bash
tap-activeprospect --version
tap-activeprospect --help
tap-activeprospect --config CONFIG --discover > ./catalog.json
```

### Testing with [Meltano](https://www.meltano.com)

```bash
# Install meltano
uv tool install meltano

# Test invocation
meltano invoke tap-activeprospect --version

# Run a test EL pipeline
meltano run tap-activeprospect target-jsonl
```

## Developer Resources

### Initialize your Development Environment

Prerequisites:

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)

```bash
uv sync
```

### Create and Run Tests

```bash
uv run pytest
```

### SDK Dev Guide

See the [dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more instructions on how to use the SDK to
develop your own taps and targets.
