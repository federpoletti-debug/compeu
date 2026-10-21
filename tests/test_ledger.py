import json
import subprocess

from compeu import ledger


def _run_with(n_obs: int, run_id: str):
    path = ledger.observations_file("2026-10")
    obs = [{"run": run_id, "offer": f"o{i}", "price": "1"} for i in range(n_obs)]
    digest = ledger.append_lines(path, obs)
    ledger.append_chained(
        ledger.runs_file(),
        {
            "run": run_id,
            "started_at": "2026-10-20T05:00:00Z",
            "results": [],
            "observations": {"file": "x", "count": n_obs, "sha256": digest},
        },
    )


def test_clean_ledger_verifies(tmp_root):
    _run_with(3, "r1")
    _run_with(2, "r2")
    assert ledger.verify() == []


def test_editing_a_past_price_is_detected(tmp_root):
    _run_with(3, "r1")
    _run_with(2, "r2")
    path = ledger.observations_file("2026-10")
    text = path.read_text(encoding="utf-8").replace('"price":"1"', '"price":"2"', 1)
    path.write_text(text, encoding="utf-8")
    assert any("r1" in e for e in ledger.verify())


def test_deleting_a_run_breaks_the_chain(tmp_root):
    for r in ("r1", "r2", "r3"):
        _run_with(1, r)
    lines = ledger.runs_file().read_text(encoding="utf-8").splitlines(keepends=True)
    ledger.runs_file().write_text(lines[0] + lines[2], encoding="utf-8")
    errors = ledger.verify()
    assert any("prev does not match" in e for e in errors)


def test_snapshot_is_content_addressed(tmp_root):
    a = ledger.write_snapshot("p", {"records": [1, 2]})
    b = ledger.write_snapshot("p", {"records": [1, 2]})
    assert a == b
    assert ledger.read_snapshot("p", a) == {"records": [1, 2]}


def test_refuses_to_append_to_a_file_without_final_newline(tmp_root):
    path = ledger.observations_file("2026-10")
    path.parent.mkdir(parents=True)
    path.write_text('{"run":"x"}', encoding="utf-8")
    try:
        ledger.append_lines(path, [{"run": "y"}])
    except ValueError:
        return
    raise AssertionError("append should have been refused")


def test_git_append_only_check(tmp_root):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_root, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    _run_with(2, "r1")
    git("add", "-A")
    git("commit", "-qm", "base")
    _run_with(1, "r2")
    assert ledger.verify_append_only("HEAD") == []
    path = ledger.observations_file("2026-10")
    first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    first["price"] = "9"
    rest = path.read_text(encoding="utf-8").splitlines(keepends=True)[1:]
    path.write_text(json.dumps(first) + "\n" + "".join(rest), encoding="utf-8")
    assert any("only appending" in e for e in ledger.verify_append_only("HEAD"))
