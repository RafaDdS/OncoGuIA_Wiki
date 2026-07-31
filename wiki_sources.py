#!/usr/bin/env python3
"""
wiki_sources.py

Reads CSV data and generates a self-contained interactive HTML page that can
include any combination of:
  - One or more sortable/searchable/filterable data tables (Tabulator)
  - A state-machine graph (vis.js) built from a "states" CSV + "transitions" CSV

In graph mode the states and transitions CSVs are automatically rendered as
data tables below the diagram, so the same page gives both visual and tabular
navigation of the data.

HTML templates live in templates/:
  - page.html   : page shell (header, CSS, shared JS libs)
  - graph.html  : graph section + vis.js script
  - table.html  : one data-table section + Tabulator script

Usage:
    # Table only
    python wiki_sources.py --csv data/fontes.csv --output wiki/dados/fontes.html

    # Graph + tables for both CSVs
    python wiki_sources.py --states data/estados.csv --transitions data/transicoes.csv \
        --output wiki/dados/fluxo.html --graph-title "Fluxo Clínico"

    # Graph + tables + an extra table from another CSV
    python wiki_sources.py --states data/estados.csv --transitions data/transicoes.csv \
        --csv data/recomendations.csv --output wiki/dados/fluxo.html

    # Multiple extra tables
    python wiki_sources.py --csv data/a.csv --csv data/b.csv --output wiki/dados/tab.html

Convention:
    - Source CSV files live in data/ (repo root).
    - Generated HTML tables and their .md wrapper pages live in wiki/dados/.
    - The .md page embeds the generated HTML with a relative iframe:
          <iframe src="tabela.html" style="width: 100%; border: none;"></iframe>
"""

import argparse
import csv
import json
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def load_template(name):
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def render(template, **kwargs):
    for key, value in kwargs.items():
        template = template.replace(f"__{key}__", str(value))
    return template


# ---------------------------------------------------------------------------
# Graph (state machine) definitions
# ---------------------------------------------------------------------------

# Disease-phase order -> columns of the layered diagram.
PHASE_ORDER = [
    "Diagnóstico",
    "Pré-neoadjuvância",
    "Pós-neoadjuvância",
    "Pós-cirurgia upfront",
    "Seguimento",
    "Metastático 1ª linha",
    "Metastático progressão",
    "Metastático tardio",
    "Terminal",
]

SUBTYPE_COLORS = {
    "TNBC": "#e45756",
    "HER2+": "#f58518",
    "RH+/HER2-": "#4c78a8",
    "Geral": "#9d755d",
    "Qualquer": "#b279a2",
}

SUB_ORDER = ["Geral", "TNBC", "HER2+", "RH+/HER2-", "Qualquer"]

ID_TOKEN_LABELS = {
    "diag": "Diagnóstico",
    "estadiamento": "Estadiamento",
    "neoadj": "Neoadjuvância",
    "candidata": "Candidata",
    "pos": "Pós",
    "pcr": "pCR",
    "residual": "Doença Residual",
    "adj": "Adjuvância",
    "upfront": "Upfront",
    "seguimento": "Seguimento",
    "curto": "Curto",
    "prazo": "Prazo",
    "longo": "Longo",
    "meta": "Metastático",
    "1l": "1ª Linha",
    "progressao": "Progressão",
    "linhas": "Linhas",
    "tardias": "Tardias",
    "obito": "Óbito",
    "rhpos": "RH+",
    "her2": "HER2+",
    "tnbc": "TNBC",
    "geral": "Geral",
    "qualquer": "Qualquer",
}


def norm(s):
    """Normalize unicode hyphens so phase names match PHASE_ORDER."""
    return s.replace("\u2011", "-").replace("\u2010", "-").replace("\u00ad", "-").strip()


def prettify_state_id(sid):
    return " ".join(ID_TOKEN_LABELS.get(t, t) for t in sid.split("_"))


def phase_index(phase):
    p = norm(phase)
    for i, known in enumerate(PHASE_ORDER):
        if norm(known) == p:
            return i
    return len(PHASE_ORDER)


def subtype_index(sub):
    s = norm(sub)
    for i, known in enumerate(SUB_ORDER):
        if norm(known) == s:
            return i
    return len(SUB_ORDER)


def build_graph_section(states_path, transitions_path, title, spacing_x=250, spacing_y=180):
    with open(states_path, encoding="utf-8-sig") as f:
        states = list(csv.DictReader(f))
    with open(transitions_path, encoding="utf-8-sig") as f:
        transitions = list(csv.DictReader(f))

    if not states:
        print("Error: states CSV is empty.", file=sys.stderr)
        sys.exit(1)

    # --- nodes ---
    nodes = []
    for s in states:
        sid = str(s["id_estado"]).strip()
        phase = str(s.get("fase_doenca", "")).strip()
        sub = str(s.get("subtipo", "")).strip()
        desc = str(s.get("descricao", "")).strip()
        nodes.append({
            "id": sid,
            "label": prettify_state_id(sid),
            "phase": phase,
            "phase_idx": phase_index(phase),
            "subtype": sub,
            "sub_idx": subtype_index(sub),
            "description": desc,
        })

    known_ids = {n["id"] for n in nodes}

    # --- edges ---
    edges = []
    in_deg = {n["id"]: 0 for n in nodes}
    out_deg = {n["id"]: 0 for n in nodes}
    for t in transitions:
        src = str(t.get("estado_origem", "")).strip()
        dst = str(t.get("estado_destino", "")).strip()
        if src not in known_ids or dst not in known_ids:
            print(f"  [warn] transition references unknown state: {src} -> {dst}",
                  file=sys.stderr)
            continue
        cond = str(t.get("condicao", "")).strip()
        try:
            weight = float(str(t.get("peso", "0")).replace(",", "."))
        except ValueError:
            weight = 0.0
        label = f"{cond} · {weight:.0%}" if cond else f"{weight:.0%}"
        edges.append({"from": src, "to": dst, "label": label,
                      "arrows": "to", "title": f"{cond or 'transição'}<br>{weight:.0%}"})
        in_deg[dst] += 1
        out_deg[src] += 1

    # --- layered layout: column per phase, rows inside a phase ---
    nodes.sort(key=lambda n: (n["phase_idx"], n["sub_idx"], n["label"]))
    row_counter = {}
    offset_x, offset_y = 80, 80
    for n in nodes:
        pi = n["phase_idx"]
        row = row_counter.get(pi, 0)
        row_counter[pi] = row + 1
        n["x"] = pi * spacing_x + offset_x
        n["y"] = row * spacing_y + offset_y

    max_phase = max(nodes, key=lambda n: n["phase_idx"])["phase_idx"]
    max_rows = max(row_counter.values())
    canvas_w = (max_phase + 1) * spacing_x + 2 * offset_x
    canvas_h = max_rows * spacing_y + 2 * offset_y

    # --- vis.js node payload ---
    subtypes_present = sorted({n["subtype"] for n in nodes}, key=subtype_index)
    vis_nodes = []
    for n in nodes:
        color = SUBTYPE_COLORS.get(n["subtype"], "#999999")
        tooltip = (
            f"<b>{n['label']}</b><br>"
            f"Fase: {n['phase']}<br>"
            f"Subtipo: {n['subtype']}<br>"
            f"{n['description']}<br>"
            f"Entradas: {in_deg.get(n['id'], 0)} &middot; Saídas: {out_deg.get(n['id'], 0)}"
        )
        vis_nodes.append({
            "id": n["id"],
            "label": n["label"],
            "x": n["x"],
            "y": n["y"],
            "color": {"background": color, "border": color, "highlight": "#4051b5", "hover": "#4051b5"},
            "title": tooltip,
            "borderWidth": 2,
            "size": 22,
        })

    legend_html = ""
    if subtypes_present:
        items = "".join(
            f'<span><span class="dot" style="background:{SUBTYPE_COLORS.get(s, "#999999")}"></span>{s}</span>'
            for s in subtypes_present
        )
        legend_html = f'<div class="legend">{items}</div>'

    return render(load_template("graph.html"),
                  GRAPH_TITLE=title,
                  LEGEND=legend_html,
                  GRAPH_WIDTH=canvas_w,
                  GRAPH_HEIGHT=canvas_h,
                  GRAPH_NODES=json.dumps(vis_nodes, ensure_ascii=False),
                  GRAPH_EDGES=json.dumps(edges, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def is_url(value):
    value = value.strip()
    return value.startswith("10.") or value.startswith("http://") or value.startswith("https://")


def format_cell(value, col_name):
    value = value.strip()
    if not value or value == "N/A":
        return ""
    if is_url(value):
        href = f"https://doi.org/{value}" if value.startswith("10.") else value
        display = value[:50] + "..." if len(value) > 50 else value
        return f'<a href="{href}" target="_blank" rel="noopener">{display}</a>'
    return value


def col_type(values):
    numeric = 0
    for v in values:
        v = v.strip()
        if v and v != "N/A":
            try:
                float(v.replace(",", "."))
                numeric += 1
            except ValueError:
                pass
    if numeric > len(values) * 0.7:
        return "number"
    return "string"


def build_column_def(col_name, ctype):
    base = {
        "title": col_name,
        "field": col_name,
        "sorter": "number" if ctype == "number" else "string",
        "headerFilter": "input" if ctype == "string" else False,
    }
    if ctype == "number":
        base["headerFilter"] = "number"
    if col_name.lower() in ("título", "titulo", "title", "nome", "name"):
        base["width"] = 300
    elif col_name.lower() in ("autores", "authors"):
        base["width"] = 250
    elif col_name.lower() in ("detalhes_publicação", "detalhes_publicacao", "details"):
        base["width"] = 180
    elif col_name.lower() in ("doi", "url", "link"):
        base["width"] = 200
        base["formatter"] = "html"
    elif col_name.lower() in ("ano", "year"):
        base["width"] = 80
    elif col_name.lower() in ("revista", "journal"):
        base["width"] = 200
    return base


def find_filter_candidates(rows, col_names, max_distinct=20):
    candidates = []
    for col in col_names:
        values = [r.get(col, "").strip() for r in rows if r.get(col, "").strip()]
        distinct = set(values)
        if 2 <= len(distinct) <= max_distinct:
            candidates.append(col)
    return candidates


def build_table_section(csv_path, table_title, table_id, filter_columns=None, sort=None):
    """Render a single data table. Returns (html_section, n_rows, n_cols)."""
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("Error: CSV file is empty.", file=sys.stderr)
        sys.exit(1)

    col_names = list(rows[0].keys())
    typed_rows = []
    for r in rows:
        typed_rows.append({
            k: format_cell(v, k) for k, v in r.items()
        })

    col_defs = []
    for col in col_names:
        vals = [r.get(col, "") for r in rows]
        ctype = col_type(vals)
        col_defs.append(build_column_def(col, ctype))

    if filter_columns:
        filter_cols = [c.strip() for c in filter_columns.split(",")]
    else:
        filter_cols = find_filter_candidates(rows, col_names)

    filter_html = ""
    for col in filter_cols:
        values = sorted(set(
            r.get(col, "").strip() for r in rows if r.get(col, "").strip()
        ))
        opts = "".join(f'<option value="{v}">{v}</option>' for v in values)
        filter_html += (
            f'<label>{col}: '
            f'<select id="{table_id}-filter-{col}">'
            f'<option value="">Todos</option>{opts}'
            f'</select></label>'
        )

    sort_col = sort or col_names[0]
    sort_dir = "desc" if "|desc" in sort_col else "asc"
    sort_col = sort_col.replace("|desc", "")

    section = render(
        load_template("table.html"),
        TABLE_TITLE=table_title,
        TABLE_ID=table_id,
        FILTER_HTML=filter_html,
        JSON_DATA=json.dumps(typed_rows, ensure_ascii=False),
        JSON_COLUMNS=json.dumps(col_defs, ensure_ascii=False),
        JSON_FILTER_COLS=json.dumps(filter_cols, ensure_ascii=False),
        INITIAL_SORT=json.dumps({"column": sort_col, "dir": sort_dir}, ensure_ascii=False),
    )
    return section, len(rows), len(col_names)


def human_title(name):
    return name.replace("_", " ").replace("-", " ").title()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate an interactive HTML page (tables and/or graph) from CSV data."
    )
    parser.add_argument("--csv", type=Path, action="append", default=None,
                        help="CSV file(s) rendered as data tables. May be repeated.")
    parser.add_argument("--states", type=Path, default=None,
                        help="Path to a CSV of graph states (node list).")
    parser.add_argument("--transitions", type=Path, default=None,
                        help="Path to a CSV of graph transitions (edges). "
                             "Must be used together with --states.")
    parser.add_argument("--output", required=True, type=Path,
                        help="Path for the output HTML file.")
    parser.add_argument("--title", type=str, default=None,
                        help="Page title (default: output filename without extension).")
    parser.add_argument("--graph-title", type=str, default="Fluxo Clínico",
                        help="Heading for the graph section (default: 'Fluxo Clínico').")
    parser.add_argument("--filter-columns", type=str, default=None,
                        help="Comma-separated column names to show as dropdown "
                             "filters (default: auto-detect low-cardinality columns).")
    parser.add_argument("--sort", type=str, default=None,
                        help="Initial sort column (default: first column). "
                             "Add '|desc' suffix for descending order.")
    parser.add_argument("--table-titles", type=str, default=None,
                        help="Comma-separated titles for the tables, in order. "
                             "When graph mode is on, states and transitions come "
                             "first, then any --csv tables.")
    args = parser.parse_args()

    tables = list(args.csv or [])
    if args.states or args.transitions:
        if not (args.states and args.transitions):
            print("Error: --states and --transitions must be used together.",
                  file=sys.stderr)
            sys.exit(1)
        # Graph mode: states and transitions CSVs are also rendered as tables.
        tables = [args.states, args.transitions] + tables

    if not tables and not args.states:
        print("Error: provide --csv and/or both --states and --transitions.",
              file=sys.stderr)
        sys.exit(1)

    for p in tables + [args.states, args.transitions]:
        if p and not p.is_file():
            print(f"Error: {p} not found.", file=sys.stderr)
            sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    title = args.title or human_title(args.output.stem)

    content = ""

    if args.states:
        print("  Graph:", args.states.name, "+", args.transitions.name)
        content += build_graph_section(args.states, args.transitions, args.graph_title)

    if tables:
        if args.table_titles:
            titles = [t.strip() for t in args.table_titles.split(",")]
            if len(titles) != len(tables):
                print(f"Error: {len(titles)} --table-titles given for "
                      f"{len(tables)} tables.", file=sys.stderr)
                sys.exit(1)
        else:
            titles = [human_title(p.stem) for p in tables]

        total_rows = 0
        total_cols = 0
        for i, (csv_path, table_title) in enumerate(zip(tables, titles)):
            section, nrows, ncols = build_table_section(
                csv_path, table_title, f"table-{i}",
                filter_columns=args.filter_columns, sort=args.sort,
            )
            content += section
            total_rows += nrows
            total_cols += ncols
            print(f"  Table: {csv_path.name} ({nrows} rows, {ncols} columns)")

    # Header stats
    parts = []
    if args.states:
        with open(args.states, encoding="utf-8-sig") as f:
            nstates = len(list(csv.DictReader(f)))
        with open(args.transitions, encoding="utf-8-sig") as f:
            ntrans = len(list(csv.DictReader(f)))
        parts.append(f"{nstates} estados &middot; {ntrans} transições")
    if tables:
        nrows = sum(len(list(csv.DictReader(open(p, encoding='utf-8-sig')))) for p in tables)
        parts.append(f"{nrows} registros em tabelas")
    stats = " &middot; ".join(parts) if parts else ""

    html = render(load_template("page.html"),
                  TITLE=title,
                  STATS=stats,
                  CONTENT=content)
    args.output.write_text(html, encoding="utf-8")
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
