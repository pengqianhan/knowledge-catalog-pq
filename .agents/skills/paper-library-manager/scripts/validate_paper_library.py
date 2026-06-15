#!/usr/bin/env python3
"""Validate an OKF paper library.

This script is intentionally self-contained: it uses only the Python standard
library so the paper-library-manager skill can travel to other repositories.
It validates the paper-library profile layered on top of OKF v0.1.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RESERVED_NAMES = {"index.md", "log.md"}
PAPER_REQUIRED = {
    "type",
    "title",
    "description",
    "resource",
    "arxiv_id",
    "pdf_url",
    "doi",
    "authors",
    "submitted",
    "tags",
    "status",
    "priority",
    "timestamp",
}
TOPIC_REQUIRED = {"type", "title", "description", "tags", "timestamp"}
STATUS_VALUES = {"unread", "skimmed", "read", "summarized"}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)")
VIZ_DATA_RE = re.compile(
    r"<script[^>]+id=[\"']paper-library-viz-data[\"'][^>]*>(.*?)</script>",
    re.DOTALL,
)
VIZ_SCHEMA = "paper-library-viz/v1"


@dataclass
class Document:
    path: Path
    rel: Path
    frontmatter: dict[str, Any]
    body: str


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
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter opening delimiter")

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
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


def load_documents(root: Path) -> tuple[list[Document], list[str]]:
    docs: list[Document] = []
    errors: list[str] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if path.name in RESERVED_NAMES:
            continue
        try:
            frontmatter, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{rel}: invalid OKF frontmatter: {exc}")
            continue
        docs.append(Document(path=path, rel=rel, frontmatter=frontmatter, body=body))
    return docs, errors


def _missing(frontmatter: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(key for key in required if not frontmatter.get(key))


def _has_section(body: str, heading: str) -> bool:
    return any(line.strip() == heading for line in body.splitlines())


def _link_target(root: Path, source: Path, target: str) -> Path:
    target = target.split("#", 1)[0]
    if target.startswith("/"):
        return (root / target.lstrip("/")).resolve()
    return (source.parent / target).resolve()


def _validate_viz(root: Path, expected_concept_ids: set[str]) -> list[str]:
    errors: list[str] = []
    viz_path = root / "viz.html"
    legacy_path = root / "vis.html"
    if not viz_path.exists():
        if legacy_path.exists():
            errors.append("viz.html: missing required file; found vis.html, expected viz.html")
        else:
            errors.append("viz.html: missing required visualization file")
        return errors
    if not viz_path.is_file():
        return ["viz.html: expected a file"]

    text = viz_path.read_text(encoding="utf-8")
    if not text.strip():
        return ["viz.html: file is empty"]

    match = VIZ_DATA_RE.search(text)
    if not match:
        return [
            "viz.html: missing embedded paper-library graph data; run the bundled generate_viz.py script"
        ]

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return [f"viz.html: invalid embedded graph JSON: {exc}"]

    if data.get("schema") != VIZ_SCHEMA:
        errors.append(f"viz.html: expected schema {VIZ_SCHEMA!r}, got {data.get('schema')!r}")

    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        errors.append("viz.html: graph data field nodes must be a list")
        nodes = []
    node_ids = {
        str(node.get("id"))
        for node in nodes
        if isinstance(node, dict) and node.get("id")
    }
    missing_nodes = sorted(expected_concept_ids - node_ids)
    extra_nodes = sorted(node_ids - expected_concept_ids)
    if missing_nodes:
        errors.append(f"viz.html: missing concepts: {', '.join(missing_nodes)}")
    if extra_nodes:
        errors.append(f"viz.html: contains unknown concepts: {', '.join(extra_nodes)}")

    edges = data.get("edges")
    if not isinstance(edges, list):
        errors.append("viz.html: graph data field edges must be a list")
        return errors
    for idx, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            errors.append(f"viz.html: edge {idx} must be an object")
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids or target not in node_ids:
            errors.append(f"viz.html: edge {idx} references an unknown concept")

    return errors


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    if not root.exists():
        return [f"{root}: library root does not exist"]
    if not root.is_dir():
        return [f"{root}: library root is not a directory"]

    docs, load_errors = load_documents(root)
    errors.extend(load_errors)

    by_rel_no_suffix = {doc.rel.with_suffix("").as_posix(): doc for doc in docs}
    by_path = {doc.path.resolve(): doc for doc in docs}
    errors.extend(_validate_viz(root, set(by_rel_no_suffix)))

    for doc in docs:
        fm = doc.frontmatter
        if not fm.get("type"):
            errors.append(f"{doc.rel}: missing required OKF field type")
            continue

        if doc.rel.parts and doc.rel.parts[0] == "papers":
            missing = _missing(fm, PAPER_REQUIRED)
            if missing:
                errors.append(f"{doc.rel}: missing paper fields: {', '.join(missing)}")
            if fm.get("type") != "Paper":
                errors.append(f"{doc.rel}: expected type Paper, got {fm.get('type')!r}")
            if fm.get("arxiv_id") and fm.get("arxiv_id") != doc.path.stem:
                errors.append(
                    f"{doc.rel}: arxiv_id {fm.get('arxiv_id')!r} does not match filename"
                )
            if fm.get("status") and fm.get("status") not in STATUS_VALUES:
                errors.append(f"{doc.rel}: unexpected status {fm.get('status')!r}")
            for section in ["# Summary", "# Key Ideas", "# Notes", "# Related", "# Citations"]:
                if not _has_section(doc.body, section):
                    errors.append(f"{doc.rel}: missing body section {section}")

        elif doc.rel.parts and doc.rel.parts[0] == "topics":
            missing = _missing(fm, TOPIC_REQUIRED)
            if missing:
                errors.append(f"{doc.rel}: missing topic fields: {', '.join(missing)}")
            if fm.get("type") != "Topic":
                errors.append(f"{doc.rel}: expected type Topic, got {fm.get('type')!r}")
            for section in ["# Scope", "# Papers", "# Open Questions"]:
                if not _has_section(doc.body, section):
                    errors.append(f"{doc.rel}: missing body section {section}")

    paper_to_topics: set[tuple[str, str]] = set()
    topic_to_papers: set[tuple[str, str]] = set()

    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            if "://" in raw_target:
                continue
            target_path = _link_target(root, path, raw_target)
            try:
                target_path.relative_to(root)
            except ValueError:
                errors.append(f"{rel}: link escapes bundle: {raw_target}")
                continue
            if not target_path.exists():
                errors.append(f"{rel}: missing link target: {raw_target}")
                continue

            source_doc = by_path.get(path.resolve())
            target_doc = by_path.get(target_path)
            if source_doc is None or target_doc is None:
                continue
            source_id = source_doc.rel.with_suffix("").as_posix()
            target_id = target_doc.rel.with_suffix("").as_posix()
            source_type = source_doc.frontmatter.get("type")
            target_type = target_doc.frontmatter.get("type")
            if source_type == "Paper" and target_type == "Topic":
                paper_to_topics.add((source_id, target_id))
            elif source_type == "Topic" and target_type == "Paper":
                topic_to_papers.add((source_id, target_id))

    for paper_id, topic_id in sorted(paper_to_topics):
        if (topic_id, paper_id) not in topic_to_papers:
            errors.append(f"{paper_id}: links to {topic_id}, but topic does not link back")
    for topic_id, paper_id in sorted(topic_to_papers):
        if (paper_id, topic_id) not in paper_to_topics:
            errors.append(f"{topic_id}: links to {paper_id}, but paper does not link back")

    for required_index in ["papers/index", "topics/index"]:
        if required_index not in by_rel_no_suffix and not (root / f"{required_index}.md").exists():
            errors.append(f"{required_index}.md: missing index file")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an OKF paper library.")
    parser.add_argument(
        "library_root",
        nargs="?",
        default="paper-library",
        help="Path to the paper library root (default: paper-library).",
    )
    args = parser.parse_args()

    errors = validate(Path(args.library_root))
    if errors:
        print("paper-library validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("paper-library validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
