# CompEU

The daily price of European sovereign GPU compute.

CompEU reads the public price lists of GPU cloud providers every day, classifies each
provider as **sovereign** or not by who controls it (legal seat and ultimate owner in
the EU or Switzerland, out of reach of the US CLOUD Act), and publishes:

- **CSX** indices: the median on-demand price per GPU-hour among sovereign providers
  (H100, H200, B200, A100, L40S);
- **CHX** indices: the same for US hyperscalers operating in Europe;
- **CSC-FRONTIER**: how many sovereign providers publicly list frontier GPUs at all.

No price is ever estimated, interpolated or carried forward. When there is not enough
fresh data, the index says so.

## The site

The pages are designed in Claude Design and the site runs those designs as they are:
each artboard in `site/design/` is read by `src/compeu/dc.py`, its data snapshot is
replaced with the live ledger, and `site/static/js/dcrun.js` draws it with Preact.
To change the design, change the canvas, copy its artboards into `site/design/`, build
and push: the Site workflow publishes it.

| Page | Address |
|---|---|
| Home: today's index and the 3D map first, then the board, the record, every quote, how it works, the ledger | `/` |
| Why sovereignty | `/why/` |
| Every fixing, its history and the raw prices | `/fixings/` |
| Method and rules | `/methodology/` |
| Data files (JSON, CSV) | `/data/` |

## How it works

```
registry/            who the providers are, the sovereignty rule, the index methodology
  providers.yaml     legal facts per provider (status is computed, never typed)
  rules/             sovereignty-v1.yaml, one file per rule version
  methodology/       index-v1.yaml, one file per methodology version
  gpus.yaml          canonical GPU models and the patterns that recognise them
src/compeu/
  collectors/        one module per provider: fetch() does I/O, parse() is pure
  collect.py         runs the collectors, writes observations and a run record
  fx.py              ECB euro reference rates
  index.py           observations -> daily fixings
  ledger.py          append-only files, hash chains, verification
  site.py            ledger + design -> static site in dist/
  dc.py              reads the Claude Design artboards the pages are made of
ledger/              the data: append-only, never edited (see below)
state/aws/           cache of AWS price-file versions (avoids re-downloading 180 MB files)
site/
  design/            the pages: Claude Design artboards (.dc.html), copied from the canvas
  static/            pictures, fonts (self-hosted), Preact and the page runtime dcrun.js
  templates/         the HTML shell around each page
.github/workflows/   daily.yml (05:20 UTC collection + deploy), site.yml (deploy on design
                     changes), ci.yml
```

### The ledger

Every price is a new line in `ledger/observations/YYYY/YYYY-MM.jsonl`. Each collection
run appends one record to `ledger/runs.jsonl` holding the SHA-256 of the lines it added
and the hash of the previous run. Fixings are chained the same way in
`ledger/fixings.jsonl`. Verbatim source records are stored once per content in
`ledger/snapshots/`. CI rejects any commit that changes an existing ledger line.

```bash
uv run compeu verify                      # recompute every hash
uv run compeu verify --against origin/main  # and check the ledger only grew
```

## Commands

```bash
uv sync                       # Python 3.12 environment
uv run compeu daily          # ECB rates + collection + today's fixings
uv run compeu collect --only scaleway,azure
uv run compeu classify       # sovereignty status of every provider, with the criteria
uv run compeu build          # static site in dist/
uv run compeu alerts         # providers failing 2+ runs in a row
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
| Hetzner | sovereign | public price file (per data centre) + GPU page |
| Verda (DataCrunch) | sovereign (provisional) | public instance-types API |
| Seeweb | sovereign (provisional) | GPU page + its price list |
| Lyceum | sovereign (provisional) | public pricing page |
| Exoscale | control under review, counted by decision (index/2) | public pricing JSON + instance-type API |
| Nebius | control under review, counted by decision (index/2) | public price page |
| AWS | not sovereign | Price List bulk API |
| Microsoft Azure | not sovereign | Retail Prices API |
| RunPod | not sovereign, global reference | public GraphQL API |
| STACKIT, Open Telekom Cloud | sovereign | collector planned |
| IONOS, Infomaniak, Safe Swiss Cloud, Hikube, Polarise, Swisscom, Phoenix (kvant), Sesterce | sovereign | no public price list yet |
| Gcore | under review | collector planned |
| Google Cloud, CoreWeave | not sovereign | planned / no public API |

Exchange rates: ECB euro foreign exchange reference rates.

## Adding a provider

1. Add its legal facts to `registry/providers.yaml`, with evidence links.
   `uv run compeu classify` shows the status the rule gives it.
2. Write `src/compeu/collectors/<id>.py` with `fetch()` and a pure `parse()`; register
   it in `collectors/__init__.py`.
3. Add a parse test on a trimmed real response in `tests/test_collectors.py`.

## Licence

Code: MIT. Data: CC BY 4.0. Preact (MIT) and the fonts Bodoni Moda, Cinzel, Geist and
Geist Mono (OFL) are vendored with their licences in `site/static/`. The engravings are
public-domain works by Boullée and Piranesi (BnF, via Wikimedia Commons). The statues in
`site/static/3d/` are point clouds made from public 3D scans: the Venus de Milo cast at
the SMK, Copenhagen (public domain) and the Augustus of the Musée Saint-Raymond,
Toulouse (CC0). The map uses Natural Earth (public domain).
