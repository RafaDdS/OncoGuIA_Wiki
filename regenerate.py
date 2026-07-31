#!/usr/bin/env python3
"""
regenerate.py

One-command regeneration of every generated artifact in the repo:

  1. Data table pages (wiki/dados/*.html) from the CSVs in data/
     via wiki_sources.py  (fontes, fluxo, recomendations)
  2. Wikilinks: collapse then regenerate every [[link]] across the wiki
     (wikilink_collapse.py + wikilink_generator.py)
  3. Interactive wiki graph (wiki/graph.html) via wiki_graph.py

Usage:
    python regenerate.py
    python regenerate.py --dry-run           # preview wikilink changes only
    python regenerate.py --no-graph          # skip the wiki graph step
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd, **kwargs):
    print(f"\n$ {cmd}", flush=True)
    return subprocess.run(cmd, shell=True, cwd=ROOT, **kwargs)


def step(name):
    print("\n" + "=" * 60)
    print(f"STEP: {name}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Regenerate all wiki artifacts.")
    parser.add_argument("--no-graph", action="store_true",
                        help="Skip the wiki graph step (wiki_graph.py).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what the wikilink generator would change "
                             "without writing files.")
    args = parser.parse_args()

    rc = 0

    # --- 1. Data table pages -------------------------------------------------
    step("Data table pages (wiki_sources.py)")
    table_cmds = [
        ("python3 wiki_sources.py --csv data/fontes.csv "
         "--output wiki/dados/fontes.html --title \"Fontes Revisadas\""),
        ("python3 wiki_sources.py --states data/estados.csv "
         "--transitions data/transicoes.csv --output wiki/dados/fluxo.html "
         "--graph-title \"Fluxo Clínico\""),
        ("python3 wiki_sources.py --csv data/recomendations.csv "
         "--output wiki/dados/recomendations.html --title \"Recomendações\""),
        ("python3 wiki_sources.py --csv data/negative_classes.csv "
         "--output wiki/dados/negative_classes.html --title \"Classes Excluídas\""),
    ]
    for cmd in table_cmds:
        r = run(cmd)
        rc = r.returncode if r.returncode else rc

    # --- 2. Wikilinks --------------------------------------------------------
    step("Collapse wikilinks")
    r = run("python3 wikilink_collapse.py --wiki-dir wiki")
    rc = r.returncode if r.returncode else rc

    step("Regenerate wikilinks")
    generator_cmd = "python3 wikilink_generator.py --wiki-dir wiki"
    if args.dry_run:
        generator_cmd += " --dry-run"
    r = run(generator_cmd)
    rc = r.returncode if r.returncode else rc

    # --- 3. Wiki graph -------------------------------------------------------
    if not args.no_graph:
        step("Wiki graph (wiki_graph.py)")
        r = run("python3 wiki_graph.py --wiki-dir wiki")
        rc = r.returncode if r.returncode else rc

    print("\n" + "=" * 60)
    if rc == 0:
        print("Done. Everything regenerated successfully.")
    else:
        print(f"Finished with errors (last exit code: {rc}).")
    print("=" * 60)
    sys.exit(rc)


if __name__ == "__main__":
    main()
