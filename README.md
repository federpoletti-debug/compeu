# Ceresio Index

The daily price of European sovereign GPU compute.

Ceresio reads the public price lists of GPU cloud providers every day, classifies each
provider as **sovereign** or not by who controls it (legal seat and ultimate owner in
the EU or Switzerland, out of reach of the US CLOUD Act), and publishes:

- **CSX** indices: the median on-demand price per GPU-hour among sovereign providers
  (H100, H200, B200, A100, L40S);
- **CHX** indices: the same for US hyperscalers operating in Europe;
- **CSC-FRONTIER**: how many sovereign providers publicly list frontier GPUs at all.

No price is ever estimated, interpolated or carried forward. When there is not enough
fresh data, the index says so.

Published from Lugano, Switzerland.

## How it works

```
registry/            who the providers are, the sovereignty rule, the index methodology
  providers.yaml     legal facts per provider (status is computed, never typed)
  rules/             sovereignty-v1.yaml, one file per rule version
  methodology/       index-v1.yaml, one file per methodology version
  gpus.yaml          canonical GPU models and the patterns that recognise them
src/ceresio/
  collectors/        one module per provider: fetch() does I/O, parse() is pure
  collect.py         runs the collectors, writes observations and a run record
  fx.py              ECB euro reference rates
  index.py           observations -> daily fixings
  ledger.py          append-only files, hash chains, verification
  site.py            ledger -> static site in dist/
ledger/              the data: append-only, never edited (see below)
state/aws/           cache of AWS price-file versions (avoids re-downloading 180 MB files)
site/                templates, CSS, JS (3D map: three.js), fonts (self-hosted)
.github/workflows/   daily.yml (05:20 UTC collection + deploy), ci.yml
```

### The ledger

Every price is a new line in `ledger/observations/YYYY/YYYY-MM.jsonl`. Each collection
run appends one record to `ledger/runs.jsonl` holding the SHA-256 of the lines it added
and the hash of the previous run. Fixings are chained the same way in
`ledger/fixings.jsonl`. Verbatim source records are stored once per content in
`ledger/snapshots/`. CI rejects any commit that changes an existing ledger line.

```bash
uv run ceresio verify                      # recompute every hash
uv run ceresio verify --against origin/main  # and check the ledger only grew
```

## Commands

```bash
uv sync                       # Python 3.12 environment
uv run ceresio daily          # ECB rates + collection + today's fixings
uv run ceresio collect --only scaleway,azure
uv run ceresio classify       # sovereignty status of every provider, with the criteria
uv run ceresio build          # static site in dist/
uv run ceresio build --single # one self-contained HTML file (for previews)
uv run ceresio alerts         # providers failing 2+ runs in a row
uv run pytest
uv run ruff check . && uv run ruff format .
```

On Windows behind a TLS-inspecting antivirus, add `--system-certs` to `uv sync`; the
collectors already use the operating system's certificate store.

## Sources

| Provider | Status | Source |
|---|---|---|
| Scaleway | sovereign | public product catalogue API |
| OVHcloud | sovereign | public order catalogue API |
| Hetzner | sovereign | GPU product page (structured price elements) |
| Verda (DataCrunch) | sovereign (provisional) | public instance-types API |
| Exoscale | under review | public pricing JSON + instance-type API |
| AWS | not sovereign | Price List bulk API |
| Microsoft Azure | not sovereign | Retail Prices API |
| RunPod | not sovereign, global reference | public GraphQL API |
| IONOS, Infomaniak, Safe Swiss Cloud, Hikube, Polarise | sovereign | no public price list yet |
| Nebius, Google Cloud, CoreWeave | various | planned / no public API |

Exchange rates: ECB euro foreign exchange reference rates.

## Adding a provider

1. Add its legal facts to `registry/providers.yaml`, with evidence links.
   `uv run ceresio classify` shows the status the rule gives it.
2. Write `src/ceresio/collectors/<id>.py` with `fetch()` and a pure `parse()`; register
   it in `collectors/__init__.py`.
3. Add a parse test on a trimmed real response in `tests/test_collectors.py`.

## Licence

Code: MIT. Data: CC BY 4.0. three.js (MIT), Schibsted Grotesk and JetBrains Mono (OFL)
are vendored with their licences in `site/static/`.
