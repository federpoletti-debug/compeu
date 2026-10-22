"""Claude Design artboards (.dc.html) as pages of the static site.

The site is designed in Claude Design (canvas linked in CLAUDE.md). Each page is an
artboard file in site/design/: markup with {{holes}}, <sc-for> and <sc-if> blocks,
events, refs, and one logic class that computes the values (renderVals). This module
reads such a file into the parts the build ships:

- the template, as a JSON tree that site/static/js/dcrun.js renders with Preact;
- the logic script, with its data and image constants replaced by the build;
- the head: the helmet's <style>, plus CSS for the style-hover attributes.

Only the subset of the format the CompEU artboards use is supported. The parser keeps
the case of tags and attributes (SVG needs viewBox, the logic needs onClick), which
Python's html.parser would lower.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field

VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}

TOKEN = re.compile(
    r"<!--.*?-->"
    r"|<(?P<close>/?)(?P<tag>[A-Za-z][\w:.-]*)(?P<attrs>(?:\s+[^\s=/>]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?)*)\s*(?P<self>/?)>"
    r"|(?P<text>[^<]+)",
    re.S,
)
ATTR = re.compile(r"([^\s=/>]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+)))?")
SECTION = re.compile(r"<x-dc>(?P<body>.*)</x-dc>", re.S)
HELMET = re.compile(r"<helmet>(?P<body>.*?)</helmet>", re.S)
STYLE = re.compile(r"<style>(?P<css>.*?)</style>", re.S)
LINK = re.compile(r"<link\b[^>]*>")
TITLE = re.compile(r"<title>(?P<t>.*?)</title>", re.S)
SCRIPT = re.compile(
    r"<script type=\"text/x-dc\" data-dc-script data-props='(?P<props>[^']*)'>(?P<js>.*?)</script>",
    re.S,
)
URL_ATTRS = ("href", "src")


class ParseError(ValueError):
    pass


@dataclass
class Artboard:
    title: str
    style: str
    links: list[str]
    template: list
    logic: str
    props: dict
    hover_css: str = ""
    hover_count: int = field(default=0)


def _attrs(text: str) -> dict[str, str]:
    out = {}
    for m in ATTR.finditer(text):
        name = m.group(1)
        value = next((g for g in m.groups()[1:] if g is not None), "")
        out[name] = html.unescape(value)
    return out


def tree(markup: str) -> list:
    """Nodes of a markup fragment: ["tag", {attrs}, [children]] or a text string."""
    root: list = []
    stack: list[tuple[str, list]] = [("#root", root)]
    for m in TOKEN.finditer(markup):
        if m.group("text") is not None:
            text = m.group("text")
            if not text.strip() and "\n" in text:
                continue  # layout whitespace between elements
            stack[-1][1].append(html.unescape(text))
            continue
        tag = m.group("tag")
        if tag is None:
            continue  # comment
        if m.group("close"):
            if stack[-1][0] != tag:
                raise ParseError(f"</{tag}> closes <{stack[-1][0]}>")
            stack.pop()
            continue
        kids: list = []
        stack[-1][1].append([tag, _attrs(m.group("attrs")), kids])
        if not m.group("self") and tag.lower() not in VOID:
            stack.append((tag, kids))
    if len(stack) != 1:
        raise ParseError(f"<{stack[-1][0]}> is never closed")
    return root


def parse(text: str) -> Artboard:
    section = SECTION.search(text)
    script = SCRIPT.search(text)
    if not section or not script:
        raise ParseError("not a .dc.html artboard: <x-dc> or the logic script is missing")
    body = section.group("body")
    helmet = HELMET.search(body)
    style, links = "", []
    if helmet:
        style = "\n".join(s.group("css").strip() for s in STYLE.finditer(helmet.group("body")))
        links = LINK.findall(helmet.group("body"))
        body = body[: helmet.start()] + body[helmet.end() :]
    title = TITLE.search(text)
    return Artboard(
        title=html.unescape(title.group("t")).strip() if title else "",
        style=style,
        links=links,
        template=tree(body),
        logic=script.group("js"),
        props=json.loads(html.unescape(script.group("props"))),
    )


def _important(decls: str) -> str:
    parts = [d.strip() for d in decls.split(";") if d.strip()]
    return ";".join(p if p.endswith("!important") else p + " !important" for p in parts)


def hover_classes(board: Artboard, prefix: str = "h") -> Artboard:
    """Turn style-hover="..." attributes into classes with :hover rules.

    Inline styles win over class rules, so the hover declarations are !important.
    """
    classes: dict[str, str] = {}

    def walk(nodes: list) -> None:
        for n in nodes:
            if isinstance(n, str):
                continue
            attrs = n[1]
            hover = attrs.pop("style-hover", None)
            if hover:
                name = classes.setdefault(hover, f"{prefix}{len(classes) + 1}")
                attrs["class"] = (attrs.get("class", "") + " " + name).strip()
            walk(n[2])

    walk(board.template)
    board.hover_css = "\n".join(f".{name}:hover{{{_important(d)}}}" for d, name in classes.items())
    board.hover_count = len(classes)
    return board


def map_urls(board: Artboard, fn) -> Artboard:
    """Rewrite href and src values: fn(value) returns the new value (or the same)."""

    def walk(nodes: list) -> None:
        for n in nodes:
            if isinstance(n, str):
                continue
            for a in URL_ATTRS:
                if a in n[1]:
                    n[1][a] = fn(n[1][a])
            walk(n[2])

    walk(board.template)
    return board


def elements(nodes: list):
    """Every element node, depth first."""
    for n in nodes:
        if isinstance(n, str):
            continue
        yield n
        yield from elements(n[2])


def replace_const(logic: str, name: str, value) -> str:
    """Replace `const NAME = <json>;` (one line) in the logic with a new JSON value."""
    pattern = re.compile(rf"^const {name} = .*?;$", re.M)
    if not pattern.search(logic):
        raise ParseError(f"const {name} not found in the logic")
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return pattern.sub(lambda _: f"const {name} = {payload};", logic, count=1)
