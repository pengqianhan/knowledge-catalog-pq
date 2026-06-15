#!/usr/bin/env python3
"""Generate the required viz.html artifact for an OKF paper library.

The script is intentionally dependency-free so the paper-library-manager skill
can be copied to another repository and still generate a useful static graph.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

from validate_paper_library import LINK_RE, _link_target, load_documents

VIZ_SCHEMA = "paper-library-viz/v1"


def _concept_id(doc_rel: Path) -> str:
    return doc_rel.with_suffix("").as_posix()


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value:
        return [str(value)]
    return []


def build_graph(root: Path) -> dict[str, Any]:
    root = root.resolve()
    docs, load_errors = load_documents(root)
    if load_errors:
        joined = "\n".join(f"- {error}" for error in load_errors)
        raise ValueError(f"cannot generate viz.html from invalid documents:\n{joined}")

    by_path = {doc.path.resolve(): doc for doc in docs}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()

    for doc in docs:
        fm = doc.frontmatter
        nodes.append(
            {
                "id": _concept_id(doc.rel),
                "path": doc.rel.as_posix(),
                "type": str(fm.get("type") or "Concept"),
                "title": str(fm.get("title") or doc.path.stem),
                "description": str(fm.get("description") or ""),
                "resource": str(fm.get("resource") or ""),
                "tags": _as_list(fm.get("tags")),
            }
        )

    for doc in docs:
        source_id = _concept_id(doc.rel)
        text = doc.path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            if "://" in raw_target:
                continue
            target_doc = by_path.get(_link_target(root, doc.path, raw_target))
            if target_doc is None:
                continue
            target_id = _concept_id(target_doc.rel)
            if source_id == target_id:
                continue
            edge_key = (source_id, target_id)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append({"source": source_id, "target": target_id})

    return {
        "schema": VIZ_SCHEMA,
        "library": root.name,
        "nodes": nodes,
        "edges": edges,
    }


def render_html(graph: dict[str, Any], bundle_name: str) -> str:
    data_json = json.dumps(graph, indent=2, sort_keys=True).replace("</", "<\\/")
    title = html.escape(bundle_name, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} Graph</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #18202b;
      --muted: #667085;
      --line: #d6dbe3;
      --paper: #2563eb;
      --topic: #059669;
      --concept: #7c3aed;
      --edge: #9aa4b2;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
      font-weight: 700;
    }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      min-height: calc(100vh - 65px);
    }}
    .graph-wrap {{
      min-height: calc(100vh - 65px);
      background: #fbfcfe;
    }}
    svg {{
      display: block;
      width: 100%;
      height: calc(100vh - 65px);
    }}
    aside {{
      border-left: 1px solid var(--line);
      background: var(--panel);
      min-height: calc(100vh - 65px);
      overflow: auto;
    }}
    .tools {{
      position: sticky;
      top: 0;
      z-index: 1;
      padding: 14px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    input {{
      width: 100%;
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      color: var(--ink);
      font: inherit;
      outline: none;
    }}
    input:focus {{
      border-color: #4f46e5;
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.14);
    }}
    .list {{
      display: grid;
      gap: 10px;
      padding: 14px;
    }}
    .item {{
      display: block;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: inherit;
      text-decoration: none;
      background: #fff;
    }}
    .item:hover {{
      border-color: #aab4c3;
      background: #f8fafc;
    }}
    .item strong {{
      display: block;
      font-size: 13px;
      line-height: 1.3;
    }}
    .item span {{
      display: block;
      margin-top: 5px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      height: 18px;
      margin-bottom: 6px;
      padding: 0 7px;
      border-radius: 999px;
      color: #fff;
      font-size: 11px;
      font-weight: 650;
    }}
    .pill.Paper {{ background: var(--paper); }}
    .pill.Topic {{ background: var(--topic); }}
    .pill.Concept {{ background: var(--concept); }}
    .edge {{
      stroke: var(--edge);
      stroke-width: 1.2;
      stroke-opacity: 0.55;
    }}
    .node circle {{
      stroke: #fff;
      stroke-width: 2;
      filter: drop-shadow(0 2px 5px rgba(15, 23, 42, 0.18));
    }}
    .node text {{
      fill: var(--ink);
      font-size: 12px;
      paint-order: stroke;
      stroke: #fbfcfe;
      stroke-width: 4px;
      stroke-linejoin: round;
    }}
    .node.dim, .edge.dim, .label.dim {{
      opacity: 0.16;
    }}
    @media (max-width: 820px) {{
      header {{
        align-items: flex-start;
        flex-direction: column;
      }}
      .meta {{
        white-space: normal;
      }}
      main {{
        grid-template-columns: 1fr;
      }}
      aside {{
        border-left: 0;
        border-top: 1px solid var(--line);
        min-height: auto;
      }}
      svg {{
        height: 62vh;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="meta" id="counts"></div>
  </header>
  <main>
    <section class="graph-wrap">
      <svg id="graph" role="img" aria-label="{title} concept graph"></svg>
    </section>
    <aside>
      <div class="tools">
        <input id="filter" type="search" placeholder="Filter papers and topics" autocomplete="off">
      </div>
      <div class="list" id="list"></div>
    </aside>
  </main>
  <script type="application/json" id="paper-library-viz-data">
{data_json}
  </script>
  <script>
    (() => {{
      const data = JSON.parse(document.getElementById("paper-library-viz-data").textContent);
      const svg = document.getElementById("graph");
      const list = document.getElementById("list");
      const filter = document.getElementById("filter");
      const counts = document.getElementById("counts");
      const palette = {{ Paper: "#2563eb", Topic: "#059669", Concept: "#7c3aed" }};
      const nodes = data.nodes || [];
      const edges = data.edges || [];
      const byId = new Map(nodes.map((node) => [node.id, node]));
      counts.textContent = `${{nodes.length}} concepts, ${{edges.length}} links`;

      function matches(node, query) {{
        if (!query) return true;
        const haystack = [node.id, node.title, node.description, node.type, ...(node.tags || [])]
          .join(" ")
          .toLowerCase();
        return haystack.includes(query);
      }}

      function layout(width, height) {{
        const groups = {{
          Topic: nodes.filter((node) => node.type === "Topic"),
          Paper: nodes.filter((node) => node.type === "Paper"),
          Concept: nodes.filter((node) => node.type !== "Topic" && node.type !== "Paper"),
        }};
        const positions = new Map();
        const placeColumn = (items, x) => {{
          const step = height / (items.length + 1 || 1);
          items.forEach((node, index) => positions.set(node.id, {{ x, y: step * (index + 1) }}));
        }};
        placeColumn(groups.Topic, Math.max(120, width * 0.25));
        placeColumn(groups.Paper, Math.min(width - 160, width * 0.68));
        placeColumn(groups.Concept, width * 0.48);
        return positions;
      }}

      function el(name, attrs = {{}}, text = "") {{
        const node = document.createElementNS("http://www.w3.org/2000/svg", name);
        for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
        if (text) node.textContent = text;
        return node;
      }}

      function render() {{
        const query = filter.value.trim().toLowerCase();
        const width = Math.max(svg.clientWidth, 640);
        const height = Math.max(svg.clientHeight, 420);
        const positions = layout(width, height);
        svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
        svg.replaceChildren();

        for (const edge of edges) {{
          const source = positions.get(edge.source);
          const target = positions.get(edge.target);
          const sourceNode = byId.get(edge.source);
          const targetNode = byId.get(edge.target);
          if (!source || !target || !sourceNode || !targetNode) continue;
          const dim = !(matches(sourceNode, query) || matches(targetNode, query));
          svg.appendChild(el("line", {{
            class: `edge${{dim ? " dim" : ""}}`,
            x1: source.x,
            y1: source.y,
            x2: target.x,
            y2: target.y,
          }}));
        }}

        for (const node of nodes) {{
          const pos = positions.get(node.id);
          if (!pos) continue;
          const dim = !matches(node, query);
          const link = el("a", {{ href: node.path }});
          const group = el("g", {{ class: `node${{dim ? " dim" : ""}}` }});
          const color = palette[node.type] || palette.Concept;
          group.appendChild(el("circle", {{ cx: pos.x, cy: pos.y, r: node.type === "Paper" ? 13 : 11, fill: color }}));
          group.appendChild(el("text", {{ x: pos.x + 18, y: pos.y + 4 }}, node.title || node.id));
          const titleNode = el("title", {{}}, `${{node.type}}: ${{node.title || node.id}}`);
          group.appendChild(titleNode);
          link.appendChild(group);
          svg.appendChild(link);
        }}

        const visible = nodes.filter((node) => matches(node, query));
        list.replaceChildren(...visible.map((node) => {{
          const item = document.createElement("a");
          item.className = "item";
          item.href = node.path;
          const pill = document.createElement("span");
          pill.className = `pill ${{node.type || "Concept"}}`;
          pill.textContent = node.type || "Concept";
          const titleEl = document.createElement("strong");
          titleEl.textContent = node.title || node.id;
          const desc = document.createElement("span");
          desc.textContent = node.description || node.path;
          item.append(pill, titleEl, desc);
          return item;
        }}));
      }}

      filter.addEventListener("input", render);
      window.addEventListener("resize", render);
      render();
    }})();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate paper-library/viz.html.")
    parser.add_argument(
        "library_root",
        nargs="?",
        default="paper-library",
        help="Path to the paper library root (default: paper-library).",
    )
    parser.add_argument(
        "--output",
        help="Output HTML path (default: <library_root>/viz.html).",
    )
    parser.add_argument(
        "--bundle-name",
        default="Paper Library",
        help="Title shown in the generated visualization.",
    )
    args = parser.parse_args()

    root = Path(args.library_root)
    output = Path(args.output) if args.output else root / "viz.html"
    try:
        graph = build_graph(root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_html(graph, args.bundle_name), encoding="utf-8")
    except Exception as exc:
        print(f"failed to generate viz.html: {exc}", file=sys.stderr)
        return 1

    print(f"generated {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
