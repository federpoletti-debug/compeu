import json
import re
from pathlib import Path

import pytest
import yaml

from compeu import dc

REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / "site" / "design"

BOARD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Test &amp; board</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link href="https://fonts.googleapis.com/css2?family=Geist&amp;display=swap" rel="stylesheet">
<style>
body{margin:0}
</style>
</helmet>
<div ref="{{setRoot}}" style="padding: {{L.gutter}}">
<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M0 0h10"></path></svg>
<sc-for list="{{items}}" as="it" hint-placeholder-count="2">
<button type="button" onClick="{{it.pick}}" style="color: red"
  style-hover="color: blue; background: #fff">{{it.label}} <span>x</span></button>
</sc-for>
<img src="/_blob/0123456789abcdef0123456789abcdef" alt="A &quot;quoted&quot; picture">
<a href="Why.dc.html#test">Why</a>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":1440,"height":900}}'>
const IMG = {"hero":"/_blob/0123456789abcdef0123456789abcdef"};
const D = {"a":1};
class Component extends DCLogic {
  renderVals() { return {}; }
}
</script>
</body>
</html>
"""


def test_parse_keeps_case_holes_and_parts():
    b = dc.parse(BOARD)
    assert b.title == "Test & board"
    assert b.style == "body{margin:0}"
    assert b.links and "fonts.googleapis.com" in b.links[0]
    assert b.props["$preview"] == {"width": 1440, "height": 900}
    assert "class Component extends DCLogic" in b.logic
    (root,) = b.template
    tag, attrs, kids = root
    assert tag == "div" and attrs["ref"] == "{{setRoot}}"
    svg = kids[0]
    assert svg[0] == "svg" and svg[1]["viewBox"] == "0 0 10 10"  # case kept
    loop = kids[1]
    assert loop[0] == "sc-for" and loop[1]["as"] == "it"
    button = loop[2][0]
    assert button[1]["onClick"] == "{{it.pick}}"
    # the space between a hole and an inline element is kept
    assert button[2][0] == "{{it.label}} "
    img = kids[2]
    assert img[0] == "img" and img[2] == [] and img[1]["alt"] == 'A "quoted" picture'


def test_layout_whitespace_is_dropped():
    nodes = dc.tree("<div>\n  <span>a</span>\n  <span>b</span>\n</div>")
    assert nodes == [["div", {}, [["span", {}, ["a"]], ["span", {}, ["b"]]]]]


def test_badly_nested_markup_is_refused():
    with pytest.raises(dc.ParseError):
        dc.tree("<div><span></div>")
    with pytest.raises(dc.ParseError):
        dc.tree("<div><span>open")


def test_style_hover_becomes_an_important_hover_rule():
    b = dc.hover_classes(dc.parse(BOARD))
    button = b.template[0][2][1][2][0]
    assert "style-hover" not in button[1]
    assert button[1]["class"] == "h1"
    assert b.hover_css == ".h1:hover{color: blue !important;background: #fff !important}"


def test_urls_and_constants_are_replaced():
    b = dc.parse(BOARD)
    dc.map_urls(b, lambda v: v.replace("/_blob/", "static/").replace("Why.dc.html", "why/"))
    hrefs = [
        e[1].get("href") or e[1].get("src") for e in dc.elements(b.template) if e[0] in ("a", "img")
    ]
    assert hrefs == ["static/0123456789abcdef0123456789abcdef", "why/#test"]
    logic = dc.replace_const(b.logic, "D", {"b": "</script>"})
    assert 'const D = {"b":"</script>"};' in logic
    with pytest.raises(dc.ParseError):
        dc.replace_const(b.logic, "MISSING", 1)


@pytest.mark.parametrize("path", sorted(DESIGN.glob("*.dc.html")), ids=lambda p: p.name)
def test_site_artboards_are_complete(path):
    """Every artboard parses, carries its data and pictures, and links only to pages."""
    from compeu.site import PAGES

    text = path.read_text(encoding="utf-8")
    board = dc.parse(text)
    assert board.title
    assert re.search(r"^const D = \{.*\};$", board.logic, re.M)
    img = json.loads(re.search(r"^const IMG = (.*?);$", board.logic, re.M).group(1))
    assets = yaml.safe_load((DESIGN / "assets.yaml").read_text(encoding="utf-8"))
    for blob in re.findall(r"/_blob/([0-9a-f]{32})", text):
        assert blob in assets, f"{path.name}: /_blob/{blob} missing from assets.yaml"
        assert (REPO / "site" / "static" / assets[blob]["file"]).exists()
    assert all(v.startswith("/_blob/") for v in img.values())
    pages = {name for name, _, _ in PAGES}
    for el in dc.elements(board.template):
        href = el[1].get("href", "")
        if href.endswith(".dc.html") or ".dc.html#" in href:
            assert href.split("#")[0] in pages
