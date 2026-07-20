#!/usr/bin/env python3
"""
wiki_graph.py

Builds a graph of a Markdown wiki: pages are nodes, [[wikilinks]] between
them are edges. Produces an interactive, self-contained HTML visualization
(and optionally a static PNG overview).

It reuses the same frontmatter/title conventions as wikilink_generator.py:
  - A page's node id is its frontmatter `title` (or filename if absent).
  - Nodes are colored by the frontmatter `category` field, if present.
  - Edges are parsed from `[[Target]]` and `[[Target|Display text]]` links
    found anywhere in the page body (frontmatter itself is ignored).
  - A link that points to a title not found anywhere in the wiki is
    reported as "dangling" (printed to the console) but not silently
    dropped from the count -- it's just excluded from the rendered graph
    since there's no node to draw it to.

Usage:
    python wiki_graph.py --wiki-dir wiki
    python wiki_graph.py --wiki-dir wiki --output graph.html
    python wiki_graph.py --wiki-dir wiki --static overview.png
    python wiki_graph.py --wiki-dir wiki --undirected
    python wiki_graph.py --wiki-dir wiki --no-physics-ui
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    print("This script requires PyYAML: pip install pyyaml --break-system-packages",
          file=sys.stderr)
    sys.exit(1)

try:
    import networkx as nx
except ImportError:
    print("This script requires networkx: pip install networkx --break-system-packages",
          file=sys.stderr)
    sys.exit(1)


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

# A reasonably distinct, readable palette. Extra categories cycle through it.
PALETTE = [
    "#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B",
    "#EECA3B", "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC",
    "#8C6D31", "#3CB44B", "#F032E6", "#469990", "#DCBEFF",
]


def split_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"  [warn] could not parse frontmatter: {e}", file=sys.stderr)
        meta = {}
    return meta, text[m.end():]


def build_graph(wiki_dir):
    """Returns (graph, category_of_node, dangling_links) """
    graph = nx.DiGraph()
    category_of = {}
    dangling = []  # (source_title, target_text, path)

    paths = sorted(wiki_dir.rglob("*.md"))

    # Pass 1: register every page as a node.
    for path in paths:
        text = path.read_text(encoding="utf-8")
        meta, _ = split_frontmatter(text)
        title = str(meta.get("title") or path.stem).strip().strip('"').strip("'")
        category = str(meta.get("category") or "Sem categoria").strip().strip('"').strip("'")
        graph.add_node(title, category=category, path=str(path))
        category_of[title] = category

    known_titles = set(graph.nodes)

    # Pass 2: parse links now that we know every valid title.
    for path in paths:
        text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        title = str(meta.get("title") or path.stem).strip().strip('"').strip("'")

        for m in WIKILINK_RE.finditer(body):
            target = m.group(1).strip()
            if target == title:
                continue  # ignore accidental self-links
            if target not in known_titles:
                dangling.append((title, target, path))
                continue
            if graph.has_edge(title, target):
                continue  # de-dupe repeated links to the same page
            graph.add_edge(title, target)

    return graph, category_of, dangling


def assign_colors(category_of):
    categories = sorted(set(category_of.values()))
    color_map = {cat: PALETTE[i % len(PALETTE)] for i, cat in enumerate(categories)}
    return color_map


def render_html(graph, category_of, color_map, output_path, directed, physics_ui):
    from pyvis.network import Network

    net = Network(
        height="900px",
        width="100%",
        directed=directed,
        bgcolor="#ffffff",
        font_color="#222222",
        select_menu=True,
        filter_menu=True,
        cdn_resources="in_line",  # fully self-contained single HTML file
    )

    in_degree = dict(graph.in_degree())
    out_degree = dict(graph.out_degree())

    for node in graph.nodes:
        category = category_of.get(node, "Sem categoria")
        degree = in_degree.get(node, 0) + out_degree.get(node, 0)
        size = 10 + 3 * degree
        title_tooltip = (
            f"{node}<br>Categoria: {category}<br>"
            f"Links recebidos: {in_degree.get(node, 0)}<br>"
            f"Links enviados: {out_degree.get(node, 0)}"
        )
        net.add_node(
            node,
            label=node,
            title=title_tooltip,
            color=color_map.get(category, "#999999"),
            size=size,
            group=category,
        )

    for source, target in graph.edges:
        net.add_edge(source, target, arrows="to" if directed else "")

    net.set_options("""
    {
      "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -60,
          "springLength": 120,
          "springConstant": 0.05,
          "avoidOverlap": 0.5
        },
        "stabilization": { "iterations": 250 }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": %s,
        "keyboard": true
      }
    }
    """ % ("true" if physics_ui else "false"))

    net.write_html(str(output_path), notebook=False, open_browser=False)


def render_static(graph, category_of, color_map, output_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(20, 20))
    pos = nx.spring_layout(graph, k=0.5, iterations=100, seed=42)

    degrees = dict(graph.degree())
    node_sizes = [80 + 25 * degrees.get(n, 0) for n in graph.nodes]
    node_colors = [color_map.get(category_of.get(n, ""), "#999999") for n in graph.nodes]

    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color="#cccccc",
                            arrows=True, arrowsize=8, width=0.6, alpha=0.6)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=node_sizes,
                            node_color=node_colors, linewidths=0.5,
                            edgecolors="#444444")
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=6)

    categories = sorted(set(category_of.values()))
    legend_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=color_map[c],
               markersize=10, label=c)
        for c in categories
    ]
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8, frameon=True)

    ax.set_title("Grafo do Wiki", fontsize=16)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def print_stats(graph, dangling):
    print(f"\nPages (nodes): {graph.number_of_nodes()}")
    print(f"Links (edges): {graph.number_of_edges()}")

    isolated = list(nx.isolates(graph))
    print(f"Isolated pages (no links in or out): {len(isolated)}")
    if isolated:
        for n in sorted(isolated)[:15]:
            print(f"    - {n}")
        if len(isolated) > 15:
            print(f"    ... and {len(isolated) - 15} more")

    in_degree = dict(graph.in_degree())
    top_referenced = Counter(in_degree).most_common(10)
    print("\nMost-referenced pages (highest in-degree):")
    for name, count in top_referenced:
        if count == 0:
            break
        print(f"    {count:3d}  {name}")

    if dangling:
        print(f"\nDangling links (target title not found in wiki): {len(dangling)}")
        for source, target, path in dangling[:20]:
            print(f'    {path.name if hasattr(path, "name") else path}: '
                  f'"{source}" -> "{target}" (no matching page)')
        if len(dangling) > 20:
            print(f"    ... and {len(dangling) - 20} more")


def main():
    parser = argparse.ArgumentParser(
        description="Render a graph of a Markdown wiki (pages=nodes, wikilinks=edges)."
    )
    parser.add_argument("--wiki-dir", required=True, type=Path,
                        help="Root folder containing the .md wiki pages.")
    parser.add_argument("--output", type=Path, default=Path("wiki_graph.html"),
                        help="Path for the interactive HTML output "
                             "(default: wiki_graph.html).")
    parser.add_argument("--static", type=Path, default=None,
                        help="Also export a static PNG overview to this path.")
    parser.add_argument("--undirected", action="store_true",
                        help="Draw edges without direction/arrows.")
    parser.add_argument("--no-physics-ui", action="store_true",
                        help="Hide the on-canvas navigation/physics buttons.")
    args = parser.parse_args()

    wiki_dir = args.wiki_dir
    if not wiki_dir.is_dir():
        print(f"Error: {wiki_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning wiki pages under {wiki_dir} ...")
    graph, category_of, dangling = build_graph(wiki_dir)
    color_map = assign_colors(category_of)

    print_stats(graph, dangling)

    print(f"\nWriting interactive graph to {args.output} ...")
    render_html(
        graph, category_of, color_map, args.output,
        directed=not args.undirected,
        physics_ui=not args.no_physics_ui,
    )
    print("Done. Open the HTML file in a browser to explore it.")

    if args.static:
        print(f"Writing static overview to {args.static} ...")
        render_static(graph, category_of, color_map, args.static)
        print("Done.")


if __name__ == "__main__":
    main()