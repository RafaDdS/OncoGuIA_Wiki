#!/usr/bin/env python3
"""
compile_wiki.py

Compile the whole wiki into a single text file suitable for feeding an LLM:
only prose content, with metadata, wikilinks, markdown links, macros, HTML
and navigation scaffolding removed. Source .md files are never modified; the
result goes to one new output file.

What each page becomes:
  - YAML frontmatter stripped entirely.
  - [[wikilinks]] collapsed to their display text (via wikilink_collapse),
    and any remaining [[https://...]] external link removed outright.
  - Markdown links [text](url) reduced to the visible text.
  - Images ![alt](url) reduced to the alt text.
  - {{ macro() }} calls, inline `code` delimiters, and HTML (<iframe>,
    <script>, anything) removed.
  - The generated footer line "*Página gerada a partir de N termo(s)...*"
    removed.
  - Navigation/index pages (index.md or tagged "indice") keep only their
    intro text; macro blocks, link lists and backlinks are dropped.

The wikilink-collapse logic is imported from wikilink_collapse.py instead of
being re-implemented here.

Usage:
    python compile_wiki.py --wiki-dir wiki --output wiki_llm.txt
    python compile_wiki.py --dry-run
    python compile_wiki.py --no-index
"""

import argparse
import re
import sys
from pathlib import Path

from wikilink_collapse import FRONTMATTER_RE, collapse_body

MDLINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
MACRO_RE = re.compile(r"\{\{.*?\}\}", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`]*)`")
HTML_BLOCK_RE = re.compile(r"<(?:script|style|iframe)\b.*?(?:</(?:script|style|iframe)>|$)", re.DOTALL | re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
EXTERNAL_WIKILINK_RE = re.compile(r"\[\[[^\]]*://[^\]]*\]\]")
FOOTER_RE = re.compile(r"^.*P[aá]gina gerada a partir de.*$\n?", re.MULTILINE)
BACKLINK_RE = re.compile(r"^\[[^\]]*[Vv]oltar ao [ií]ndice[^\]]*\]\([^)]*\)\s*$\n?", re.MULTILINE)
H1_RE = re.compile(r"^#\s+.*$\n?", re.MULTILINE)
HR_RE = re.compile(r"^-{3,}\s*$\n?", re.MULTILINE)

EXCLUDE_RE = re.compile(r"^exclude_from_data\s*:\s*true", re.MULTILINE)

INDEX_TAGS = ("indice", "indice-de-categoria")


def split_frontmatter(text):
    """Return (frontmatter_block, title_from_fm, body_text)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", "", text
    title = ""
    for line in m.group(1).splitlines():
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip().strip('"').strip("'")
            break
    return m.group(0), title, text[m.end():]


def collapse_wikilinks(text):
    """Reduce [[Target|Display]] to Display and [[Target]] to Target, reusing
    wikilink_collapse's own collapse logic so behavior stays consistent."""
    collapsed, _ = collapse_body(text)
    return collapsed


def clean_body(body):
    """Collapse/remove all non-prose structure in a content page body."""
    # 1. Unwrap inline code to plain text (keeping `code` content worth keeping).
    body = INLINE_CODE_RE.sub(r"\1", body)
    # 2. Remove whole <script>/<style>/<iframe> blocks (not just the tags).
    body = HTML_BLOCK_RE.sub("", body)
    body = HTML_TAG_RE.sub("", body)
    # 3. Wikilinks -> display text (reuse from wikilink_collapse) and drop the
    #    bare external ones collapse_body leaves intact.
    body = collapse_wikilinks(body)
    body = EXTERNAL_WIKILINK_RE.sub("", body)
    # 4. Markdown links / images -> visible text.
    body = MDLINK_RE.sub(lambda m: m.group(1).strip(), body)
    # 5. Macros, footers, backlinks, headings, horizontal rules.
    body = MACRO_RE.sub("", body)
    body = FOOTER_RE.sub("", body)
    body = BACKLINK_RE.sub("", body)
    body = H1_RE.sub("", body)
    body = HR_RE.sub("", body)
    # 6. Any wikilink/navigation brackets that survived (e.g. inside list
    #    markers) are removed too.
    body = EXTERNAL_WIKILINK_RE.sub("", body)
    body = re.sub(r"\[\[[^\]]*\]\]", lambda m: m.group(0)[2:-2].split("|", 1)[-1].split("#", 1)[0].strip(), body)
    body = re.sub(r"[ \t]+$", "", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def clean_index_text(body):
    """Reduce a navigation/index page to just its intro prose."""
    body = INLINE_CODE_RE.sub(r"\1", body)
    body = HTML_BLOCK_RE.sub("", body)
    body = HTML_TAG_RE.sub("", body)
    body = collapse_wikilinks(body)
    body = MACRO_RE.sub("", body)
    body = FOOTER_RE.sub("", body)
    body = BACKLINK_RE.sub("", body)
    body = H1_RE.sub("", body)
    body = HR_RE.sub("", body)
    body = re.sub(r"[ \t]+$", "", body, flags=re.MULTILINE)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def process_file(path, wiki_dir):
    """Return (skipped:bool, lines:list[str], is_index:bool, reason:str)."""
    text = path.read_text(encoding="utf-8")
    fm, title, body = split_frontmatter(text)
    if not title:
        title = path.stem

    is_index = (
        path.name.lower() == "index.md"
        or any(str(tag) in fm for tag in INDEX_TAGS)
    )

    if EXCLUDE_RE.search(fm):
        return True, [], is_index, "excluded from data"

    if is_index:
        cleaned = clean_index_text(body)
    else:
        cleaned = clean_body(body)

    if not cleaned:
        return True, [], is_index, "no content"

    relative = path.relative_to(wiki_dir).as_posix()
    lines = [f"<!-- {relative} -->", "", f"# {title}", cleaned, ""]
    return False, lines, is_index, ""


def compile_wiki(wiki_dir, output, no_index, dry_run):
    pages_written = 0
    pages_skipped = 0
    written_index = 0
    total_chars = 0

    out = []
    for path in sorted(wiki_dir.rglob("*.md")):
        skipped, lines, is_index, reason = process_file(path, wiki_dir)
        rel = path.relative_to(wiki_dir)
        if no_index and is_index:
            pages_skipped += 1
            continue
        if skipped:
            pages_skipped += 1
            print(f"  [skip] {rel} ({reason})")
            continue
        if is_index:
            written_index += 1
        pages_written += 1
        total_chars += sum(len(l) for l in lines)
        out.extend(lines)
        print(f"  {rel}")

    text = "\n".join(out).rstrip() + "\n"
    print(f"\nPages written: {pages_written} "
          f"(including {written_index} index page(s)); skipped: {pages_skipped}")
    print(f"Output: {len(text)} bytes, {total_chars} chars of content lines")

    if dry_run:
        print(f"[dry run] Not writing; would write to {output}")
        return

    output.write_text(text, encoding="utf-8")
    print(f"Written to {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Compile the wiki into a single LLM-training text file."
    )
    parser.add_argument("--wiki-dir", type=Path, default=Path("wiki"),
                        help="Root folder of the .md wiki pages (default: wiki).")
    parser.add_argument("--output", type=Path, default=Path("wiki_llm.txt"),
                        help="Output file path (default: wiki_llm.txt).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report stats without writing the output file.")
    parser.add_argument("--no-index", action="store_true",
                        help="Skip navigation/index pages entirely.")
    args = parser.parse_args()

    if not args.wiki_dir.is_dir():
        print(f"Error: {args.wiki_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    compile_wiki(args.wiki_dir, args.output, args.no_index, args.dry_run)


if __name__ == "__main__":
    main()