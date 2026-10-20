"""The ledger: append-only files that hold every price ever observed.

Layout (all under ledger/):

    observations/YYYY/YYYY-MM.jsonl   one line per offer per run
    runs.jsonl                        one line per collection run, hash-chained
    fixings.jsonl                     one line per published index value, hash-chained
    fx/ecb.jsonl                      ECB reference rates, one line per day
    snapshots/<provider>/<hash>.json.gz   verbatim source records, stored once per content

Nothing here ever rewrites a line. A run record stores the SHA-256 of the
observation lines it added, and the hash of the previous run record, so editing
or deleting any past line breaks `verify()`. `verify_append_only()` adds a second
check against git: every ledger file must start with its previous content.
"""

from __future__ import annotations

import gzip
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from .util import canonical_json, read_jsonl, root, sha256_bytes, sha256_text

GENESIS = "sha256:" + "0" * 64


def ledger_dir() -> Path:
    return root() / "ledger"


def observations_file(month: str) -> Path:
    """month is 'YYYY-MM'."""
    return ledger_dir() / "observations" / month[:4] / f"{month}.jsonl"


def runs_file() -> Path:
    return ledger_dir() / "runs.jsonl"


def fixings_file() -> Path:
    return ledger_dir() / "fixings.jsonl"


# ------------------------------------------------------------------ writing


def _append_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        with path.open("rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                raise ValueError(f"{path} does not end with a newline: refusing to append")
    with path.open("ab") as f:
        f.write(data)


def append_lines(path: Path, records: list[dict]) -> str:
    """Append records as canonical JSON lines; return the SHA-256 of the bytes added."""
    data = "".join(canonical_json(r) + "\n" for r in records).encode("utf-8")
    _append_bytes(path, data)
    return sha256_bytes(data)


def last_hash(path: Path) -> str:
    rows = read_jsonl(path)
    return rows[-1]["hash"] if rows else GENESIS


def chain_hash(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return sha256_text(canonical_json(body))


def append_chained(path: Path, record: dict) -> dict:
    """Append one record linked to the previous one (fields `prev` and `hash`)."""
    record = dict(record)
    record["prev"] = last_hash(path)
    record["hash"] = chain_hash(record)
    append_lines(path, [record])
    return record


def write_snapshot(provider: str, payload: dict) -> str:
    """Store verbatim source records once per content; return their content hash."""
    text = canonical_json(payload)
    digest = sha256_text(text)
    path = ledger_dir() / "snapshots" / provider / (digest.split(":")[1][:20] + ".json.gz")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # mtime=0 keeps the gzip bytes identical for identical content.
        path.write_bytes(gzip.compress(text.encode("utf-8"), mtime=0))
    return digest


def read_snapshot(provider: str, digest: str) -> dict:
    path = ledger_dir() / "snapshots" / provider / (digest.split(":")[1][:20] + ".json.gz")
    return json.loads(gzip.decompress(path.read_bytes()))


# ------------------------------------------------------------------ reading


def all_observation_files() -> list[Path]:
    base = ledger_dir() / "observations"
    return sorted(base.glob("*/*.jsonl")) if base.exists() else []


def iter_observations():
    for path in all_observation_files():
        yield from read_jsonl(path)


def runs() -> list[dict]:
    return read_jsonl(runs_file())


def fixings() -> list[dict]:
    return read_jsonl(fixings_file())


# ------------------------------------------------------------------ verification


def verify_chain(path: Path) -> list[str]:
    errors, prev = [], GENESIS
    for n, rec in enumerate(read_jsonl(path), start=1):
        if rec.get("prev") != prev:
            errors.append(f"{path.name} line {n}: prev does not match the line before")
        if rec.get("hash") != chain_hash(rec):
            errors.append(f"{path.name} line {n}: hash does not match its content")
        prev = rec.get("hash")
    return errors


def verify() -> list[str]:
    """Check both hash chains and that every run's observations are intact."""
    errors = verify_chain(runs_file()) + verify_chain(fixings_file())
    lines_by_run: dict[str, list[str]] = defaultdict(list)
    for path in all_observation_files():
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    lines_by_run[json.loads(line)["run"]].append(line)
    for run in runs():
        expected = run.get("observations", {})
        got = lines_by_run.pop(run["run"], [])
        digest = sha256_bytes("".join(got).encode("utf-8"))
        if len(got) != expected.get("count", 0) or (got and digest != expected.get("sha256")):
            errors.append(f"run {run['run']}: observation lines differ from what the run recorded")
    for orphan in lines_by_run:
        errors.append(f"observations for run {orphan} have no run record")
    return errors


def verify_append_only(base_ref: str) -> list[str]:
    """Every ledger file tracked at `base_ref` must be a prefix of its current content."""
    repo = root()
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", base_ref, "ledger/"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    errors = []
    for rel in listed:
        if rel.endswith(".gz"):
            old = subprocess.run(
                ["git", "show", f"{base_ref}:{rel}"], cwd=repo, capture_output=True, check=True
            ).stdout
            new = (repo / rel).read_bytes() if (repo / rel).exists() else None
            if new != old:
                errors.append(f"{rel}: snapshot changed or deleted")
            continue
        old = subprocess.run(
            ["git", "show", f"{base_ref}:{rel}"], cwd=repo, capture_output=True, check=True
        ).stdout
        path = repo / rel
        if not path.exists():
            errors.append(f"{rel}: deleted")
        elif not path.read_bytes().startswith(old):
            errors.append(f"{rel}: existing lines were changed (only appending is allowed)")
    return errors
