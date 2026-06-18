#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Generate the required paper-library viz.html artifact.

This script is intentionally self-contained so the skill can run after being
installed in Codex, Claude Code, or another Agent Skills-compatible client.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RESERVED_NAMES = {"index.md", "log.md"}
FRONTMATTER_DELIM = "---"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)")
TYPE_PALETTE = {
    "Paper": "#2563eb",
    "Topic": "#16a34a",
    "Reference": "#9333ea",
}
DEFAULT_NODE_COLOR = "#64748b"


@dataclass
class Concept:
    id: str
    type: str
    title: str
    description: str
    resource: str
    tags: list[str]
    body: str
    links_to: list[str] = field(default_factory=list)

    def to_node(self) -> dict[str, Any]:
        return {
            "data": {
                "id": self.id,
                "label": self.title or self.id,
                "type": self.type,
                "description": self.description,
                "resource": self.resource,
                "tags": self.tags,
                "color": TYPE_PALETTE.get(self.type, DEFAULT_NODE_COLOR),
                "size": 30 + min(60, len(self.body) // 200),
            }
        }


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_inline_list(value: str) -> list[str] | None:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_strip_quotes(part.strip()) for part in inner.split(",")]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return {}, text

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == FRONTMATTER_DELIM:
            end_idx = idx
            break
    if end_idx is None:
        raise ValueError("missing YAML frontmatter closing delimiter")

    frontmatter: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw in lines[1:end_idx]:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list_key:
            frontmatter.setdefault(current_list_key, []).append(_strip_quotes(stripped[2:]))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        inline_list = _parse_inline_list(value)
        if inline_list is not None:
            frontmatter[key] = inline_list
        elif value == "":
            frontmatter[key] = []
            current_list_key = key
        else:
            frontmatter[key] = _strip_quotes(value)

    body = "\n".join(lines[end_idx + 1 :])
    if body.startswith("\n"):
        body = body[1:]
    return frontmatter, body


def _target_to_concept_id(bundle_root: Path, source_path: Path, raw_target: str) -> str | None:
    target = raw_target.split("#", 1)[0]
    if "://" in target or target.startswith("mailto:"):
        return None
    if target.startswith("/"):
        resolved = (bundle_root / target.lstrip("/")).resolve()
    else:
        resolved = (source_path.parent / target).resolve()
    try:
        rel = resolved.relative_to(bundle_root.resolve())
    except ValueError:
        return None
    if rel.suffix != ".md":
        return None
    return rel.with_suffix("").as_posix()


def _extract_links(body: str, source_path: Path, bundle_root: Path) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw_target in LINK_RE.findall(body):
        concept_id = _target_to_concept_id(bundle_root, source_path, raw_target)
        if concept_id and concept_id not in seen:
            seen.add(concept_id)
            out.append(concept_id)
    return out


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def _walk_concepts(bundle_root: Path) -> list[Concept]:
    concepts: list[Concept] = []
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name in RESERVED_NAMES:
            continue
        rel = md_path.relative_to(bundle_root).with_suffix("")
        concept_id = rel.as_posix()
        frontmatter, body = parse_frontmatter(md_path.read_text(encoding="utf-8"))
        concept = Concept(
            id=concept_id,
            type=str(frontmatter.get("type") or "Unknown"),
            title=str(frontmatter.get("title") or concept_id),
            description=str(frontmatter.get("description") or ""),
            resource=str(frontmatter.get("resource") or ""),
            tags=_string_list(frontmatter.get("tags")),
            body=body or "",
            links_to=_extract_links(body or "", md_path, bundle_root),
        )
        concepts.append(concept)
    return concepts


def _build_graph(concepts: list[Concept]) -> dict[str, Any]:
    ids = {concept.id for concept in concepts}
    nodes = [concept.to_node() for concept in concepts]
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    for concept in concepts:
        for target in concept.links_to:
            if target == concept.id or target not in ids:
                continue
            key = (concept.id, target)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(
                {
                    "data": {
                        "id": f"{concept.id}__{target}",
                        "source": concept.id,
                        "target": target,
                    }
                }
            )
    return {
        "nodes": nodes,
        "edges": edges,
        "bodies": {concept.id: concept.body for concept in concepts},
        "types": sorted({concept.type for concept in concepts}),
        "palette": TYPE_PALETTE,
    }


def _render_html(bundle_name: str, graph: dict[str, Any]) -> str:
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__BUNDLE_NAME_TEXT__</title>
  <style>
    :root { color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: Canvas; color: CanvasText; }
    header { padding: 24px 28px 16px; border-bottom: 1px solid color-mix(in srgb, CanvasText 14%, transparent); }
    h1 { margin: 0 0 8px; font-size: 24px; line-height: 1.2; }
    .summary { margin: 0; color: color-mix(in srgb, CanvasText 70%, transparent); }
    main { display: grid; grid-template-columns: minmax(260px, 360px) 1fr; min-height: calc(100vh - 89px); }
    aside { border-right: 1px solid color-mix(in srgb, CanvasText 14%, transparent); padding: 18px; overflow: auto; }
    section { padding: 18px 24px; overflow: auto; }
    input { width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid color-mix(in srgb, CanvasText 18%, transparent); border-radius: 6px; background: Canvas; color: CanvasText; }
    .node { display: block; width: 100%; text-align: left; margin: 10px 0 0; padding: 10px 12px; border: 1px solid color-mix(in srgb, CanvasText 14%, transparent); border-left: 5px solid var(--node-color); border-radius: 6px; background: color-mix(in srgb, Canvas 94%, CanvasText 6%); color: CanvasText; cursor: pointer; }
    .node strong { display: block; font-size: 14px; }
    .node span { display: block; margin-top: 4px; font-size: 12px; color: color-mix(in srgb, CanvasText 68%, transparent); }
    .meta { display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 14px; }
    .pill { border: 1px solid color-mix(in srgb, CanvasText 16%, transparent); border-radius: 999px; padding: 4px 8px; font-size: 12px; color: color-mix(in srgb, CanvasText 70%, transparent); }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; border: 1px solid color-mix(in srgb, CanvasText 14%, transparent); border-radius: 6px; padding: 14px; background: color-mix(in srgb, Canvas 93%, CanvasText 7%); }
    @media (max-width: 760px) { main { grid-template-columns: 1fr; } aside { border-right: 0; border-bottom: 1px solid color-mix(in srgb, CanvasText 14%, transparent); } }
  </style>
</head>
<body>
  <header>
    <h1 id="bundle-name"></h1>
    <p class="summary" id="summary"></p>
  </header>
  <main>
    <aside>
      <input id="search" type="search" placeholder="Filter papers and topics">
      <div id="nodes"></div>
    </aside>
    <section>
      <div class="meta" id="meta"></div>
      <h2 id="title"></h2>
      <p id="description"></p>
      <pre id="body"></pre>
    </section>
  </main>
  <script>
    window.BUNDLE = __BUNDLE_DATA__;
    window.BUNDLE_NAME = __BUNDLE_NAME_JSON__;
    const bundle = window.BUNDLE;
    const nodesEl = document.getElementById("nodes");
    const searchEl = document.getElementById("search");
    const titleEl = document.getElementById("title");
    const descEl = document.getElementById("description");
    const bodyEl = document.getElementById("body");
    const metaEl = document.getElementById("meta");
    document.getElementById("bundle-name").textContent = window.BUNDLE_NAME;
    document.getElementById("summary").textContent = `${bundle.nodes.length} concepts, ${bundle.edges.length} links`;

    function showNode(node) {
      const data = node.data;
      titleEl.textContent = data.label || data.id;
      descEl.textContent = data.description || "";
      bodyEl.textContent = bundle.bodies[data.id] || "";
      metaEl.innerHTML = "";
      [data.type, data.resource, ...(data.tags || [])].filter(Boolean).forEach(value => {
        const pill = document.createElement("span");
        pill.className = "pill";
        pill.textContent = value;
        metaEl.appendChild(pill);
      });
    }

    function render() {
      const query = searchEl.value.toLowerCase();
      nodesEl.innerHTML = "";
      bundle.nodes
        .filter(node => JSON.stringify(node.data).toLowerCase().includes(query))
        .sort((a, b) => (a.data.label || a.data.id).localeCompare(b.data.label || b.data.id))
        .forEach(node => {
          const button = document.createElement("button");
          button.className = "node";
          button.style.setProperty("--node-color", node.data.color || "#64748b");
          button.innerHTML = `<strong>${node.data.label || node.data.id}</strong><span>${node.data.type || "Concept"} · ${node.data.id}</span>`;
          button.addEventListener("click", () => showNode(node));
          nodesEl.appendChild(button);
        });
    }

    searchEl.addEventListener("input", render);
    render();
    if (bundle.nodes[0]) showNode(bundle.nodes[0]);
  </script>
</body>
</html>
"""
    return (
        template.replace("__BUNDLE_NAME_TEXT__", bundle_name)
        .replace("__BUNDLE_NAME_JSON__", json.dumps(bundle_name, ensure_ascii=False))
        .replace("__BUNDLE_DATA__", json.dumps(graph, ensure_ascii=False))
    )


def generate_visualization(
    bundle_root: Path,
    out_path: Path,
    *,
    bundle_name: str | None = None,
) -> dict[str, int]:
    bundle_root = Path(bundle_root).expanduser().resolve()
    out_path = Path(out_path).expanduser()
    if not bundle_root.is_dir():
        raise FileNotFoundError(f"paper library directory not found: {bundle_root}")
    if not out_path.is_absolute():
        out_path = (Path.cwd() / out_path).resolve()

    concepts = _walk_concepts(bundle_root)
    graph = _build_graph(concepts)
    name = bundle_name or bundle_root.name
    html = _render_html(name, graph)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    return {
        "concepts": len(concepts),
        "edges": len(graph["edges"]),
        "bytes": len(html.encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate paper-library/viz.html as a self-contained OKF graph."
    )
    parser.add_argument(
        "library_root",
        nargs="?",
        default="paper-library",
        help="Path to the paper library bundle root (default: paper-library).",
    )
    parser.add_argument(
        "--output",
        help="Output HTML path (default: <library_root>/viz.html).",
    )
    parser.add_argument(
        "--bundle-name",
        default="Paper Library",
        help="Display name shown in the generated viewer.",
    )
    args = parser.parse_args()

    library_root = Path(args.library_root).expanduser().resolve()
    output = Path(args.output).expanduser() if args.output else library_root / "viz.html"

    stats = generate_visualization(
        library_root,
        output,
        bundle_name=args.bundle_name,
    )
    print(
        f"generated {output}: "
        f"{stats['concepts']} concept(s), {stats['edges']} edge(s), {stats['bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
