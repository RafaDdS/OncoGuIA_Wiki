#!/usr/bin/env python3
"""
wikilink_generator.py

Scans a folder of Markdown wiki pages, builds a "term index" from each
page's title (YAML frontmatter `title`, falling back to the filename) and
its `aliases` list, then automatically inserts [[Wikilinks]] wherever those
terms appear as plain text in *other* pages.

Rules it follows:
  - A page never links to itself, even via one of its own aliases.
  - Text already inside a [[wikilink]], a markdown [link](url), inline
    `code`, or a fenced ```code block``` is left untouched.
  - Matching respects word boundaries (won't turn "Carcinoma" inside
    "Carcinomatose" into a link) using Unicode-aware boundaries, so
    accented Portuguese text works correctly.
  - When several terms could match the same span (e.g. "Carcinoma Ductal
    in Situ" vs "Carcinoma"), the longest term wins.
  - By default only the FIRST occurrence of each target page per file is
    linked (typical wiki convention), counting both new matches and any
    wikilink to that target already present in the file -- so running the
    script repeatedly is idempotent and won't keep "promoting" later
    occurrences on each run. Use --all-occurrences to link every
    occurrence instead.
  - Markdown heading lines (`# ...`, `## ...`, etc.) are left untouched --
    a page's own H1 title, and any other heading text, never gets wrapped
    in a wikilink.
  - Matching is case-insensitive by default (so "doença localmente
    avançada" links to [[Doença Localmente Avançada]]), while the original
    text's exact casing is preserved as the link's display text. Use
    --case-sensitive-terms if a handful of specific terms (e.g. ambiguous
    short acronyms) need exact-case matching instead.

  - Written for wikis using mkdocs-roamlinks-plugin, which resolves links
    by matching the *filename on disk*, not frontmatter titles. Since
    every category's index.md would otherwise collide (there's one per
    folder) and titles containing "/" get misparsed as paths by the
    plugin, the script automatically uses an explicit path like
    [[biomarcadores/index|Biomarcadores]] instead of a bare [[Biomarcadores]]
    in exactly those two cases, and a plain [[Title]] everywhere else.

Usage:
    python wikilink_generator.py --wiki-dir wiki --dry-run
    python wikilink_generator.py --wiki-dir wiki
    python wikilink_generator.py --wiki-dir wiki --all-occurrences
    python wikilink_generator.py --wiki-dir wiki --exclude "RE,RP,T,N,M,G1,G2,G3"
    python wikilink_generator.py --wiki-dir wiki --min-length 3
    python wikilink_generator.py --wiki-dir wiki --case-sensitive-terms "N,T,M"
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "This script requires PyYAML. Install with:\n"
        "    pip install pyyaml --break-system-packages",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Regexes for structural parsing / protection
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[.*?\]\]")
MDLINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
HEADING_RE = re.compile(r"^#{1,6}[ \t].*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class TermEntry:
    __slots__ = ("term", "target", "href", "source")

    def __init__(self, term, target, href, source):
        self.term = term
        self.target = target  # canonical page title (identity, for bookkeeping)
        self.href = href      # exact string to put inside [[ ]] so the
                               # mkdocs-roamlinks-plugin resolves it correctly
        self.source = source  # Path of the file that owns this term


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def split_frontmatter(text):
    """Return (meta_dict, frontmatter_block_text, body_text)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, "", text
    raw = m.group(1)
    try:
        meta = yaml.safe_load(raw) or {}
    except yaml.YAMLError as e:
        print(f"  [warn] could not parse frontmatter: {e}", file=sys.stderr)
        meta = {}
    return meta, m.group(0), text[m.end():]


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def compute_link_href(path, wiki_dir, title):
    """
    Decide what string should go inside [[ ]] for this page so that
    mkdocs-roamlinks-plugin actually resolves it.

    The plugin matches a bare [[Title]] link against files on disk by
    lowercasing and stripping hyphens/underscores/spaces from *filenames*
    -- it never looks at frontmatter. That's unsafe in two cases:

      1. index.md files: every category folder has one, so a bare
         [[<Category>]] link never matches an "index.md" file, and a bare
         [[index]] link would be ambiguous (many files share that name).
      2. Titles containing "/" (e.g. "PET/CT"): the plugin's link syntax
         treats "/" as a path separator, so a bare [[PET/CT]] gets
         silently misinterpreted as a relative path rather than a
         filename search -- producing a broken link with no warning.

    In both cases we fall back to an explicit path relative to the wiki
    root (e.g. "biomarcadores/index" or "estadiamento/PET-CT"), which the
    plugin resolves deterministically, and always pair it with an alias
    so the visible link text still reads naturally.
    """
    is_index_page = path.stem.lower() == "index"
    has_unsafe_slash = "/" in title or "\\" in title
    if is_index_page or has_unsafe_slash:
        return path.relative_to(wiki_dir).with_suffix("").as_posix()
    return title


def build_index(wiki_dir):
    """
    Walk wiki_dir for *.md files and build:
      - entries: list[TermEntry] (titles + aliases -> target page)
      - file_targets: dict[Path -> canonical title] (a page's own identity)
    """
    entries = []
    file_targets = {}
    seen_terms = {}  # term_lower -> source path, to warn on collisions

    for path in sorted(wiki_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, _, _ = split_frontmatter(text)

        title = meta.get("title") or path.stem
        title = str(title).strip().strip('"').strip("'")
        file_targets[path] = title
        href = compute_link_href(path, wiki_dir, title)

        aliases = meta.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]

        for raw_term in [title] + list(aliases):
            term = str(raw_term).strip()
            if not term:
                continue
            key = term.lower()
            if key in seen_terms and seen_terms[key] != path:
                print(
                    f"  [warn] term '{term}' is claimed by both "
                    f"{seen_terms[key]} and {path} -- keeping the first one",
                    file=sys.stderr,
                )
                continue
            seen_terms[key] = path
            entries.append(TermEntry(term, title, href, path))

    # Maps whatever string might legitimately appear inside [[ ]] for a
    # page -- either its plain title (old-style links, or normal pages)
    # or its path-based href (index pages / slash-titles) -- back to that
    # page's canonical title. Used to recognize links already present in
    # a file regardless of which style wrote them.
    href_to_target = {}
    for entry in entries:
        href_to_target[entry.target] = entry.target
        href_to_target[entry.href] = entry.target

    return entries, file_targets, href_to_target


# ---------------------------------------------------------------------------
# Pattern building / matching
# ---------------------------------------------------------------------------

def build_pattern(term, case_sensitive_terms):
    """
    Build a compiled regex for `term` with sensible boundaries:
    only assert a word-boundary on an edge if that edge is itself an
    alphanumeric character (so terms ending in punctuation like
    "TC (Docetaxel + Ciclofosfamida)" still match correctly).

    Matching is case-insensitive by default. Pass a term (exact string)
    in `case_sensitive_terms` to force exact-case matching for it.
    """
    escaped = re.escape(term)
    left = r"(?<![^\W_])" if term[0].isalnum() else ""
    right = r"(?![^\W_])" if term[-1].isalnum() else ""
    pattern = left + escaped + right

    flags = 0 if term in case_sensitive_terms else re.IGNORECASE
    return re.compile(pattern, flags)


def find_protected_spans(body):
    """Spans of text that must never be touched: existing links/code/headings."""
    spans = []
    for regex in (FENCED_CODE_RE, INLINE_CODE_RE, WIKILINK_RE, MDLINK_RE, HEADING_RE):
        for m in regex.finditer(body):
            spans.append((m.start(), m.end()))
    return spans


def is_protected(start, end, protected_spans):
    for s, e in protected_spans:
        if start < e and end > s:
            return True
    return False


def existing_linked_targets(body, href_to_target):
    """Canonical titles that already have a [[wikilink]] somewhere in this body."""
    targets = set()
    for m in WIKILINK_RE.finditer(body):
        inner = m.group(0)[2:-2]  # strip the surrounding [[ ]]
        href = inner.split("|", 1)[0].strip()
        target = href_to_target.get(href)
        if target:
            targets.add(target)
    return targets


# ---------------------------------------------------------------------------
# Core per-file processing
# ---------------------------------------------------------------------------

def process_file(path, entries, file_targets, href_to_target, args):
    text = path.read_text(encoding="utf-8")
    fm_match = FRONTMATTER_RE.match(text)
    if fm_match:
        frontmatter_block = fm_match.group(0)
        body = text[fm_match.end():]
    else:
        frontmatter_block = ""
        body = text

    own_target = file_targets.get(path)
    protected = find_protected_spans(body)

    candidates = []
    for entry in entries:
        if entry.target == own_target:
            continue  # never link a page to itself
        if len(entry.term) < args.min_length:
            continue
        if entry.term.lower() in args.exclude_set:
            continue

        pattern = build_pattern(entry.term, args.case_sensitive_terms)
        for m in pattern.finditer(body):
            if is_protected(m.start(), m.end(), protected):
                continue
            candidates.append((m.start(), m.end(), entry.target, entry.href, m.group(0)))

    # Resolve overlaps: longest match wins, then earliest position.
    candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0]))

    accepted = []
    accepted_spans = []
    # Seed with targets that are already linked elsewhere in this file (from
    # a previous run, or written by hand) so re-running the script is a
    # no-op instead of "promoting" the next unlinked occurrence each time.
    linked_targets = (
        set() if args.all_occurrences
        else existing_linked_targets(body, href_to_target)
    )

    for start, end, target, href, matched_text in candidates:
        if not args.all_occurrences and target in linked_targets:
            continue
        if any(start < e and end > s for s, e in accepted_spans):
            continue
        accepted.append((start, end, href, matched_text))
        accepted_spans.append((start, end))
        linked_targets.add(target)

    # Apply replacements right-to-left so earlier offsets stay valid.
    accepted.sort(key=lambda c: -c[0])
    new_body = body
    for start, end, href, matched_text in accepted:
        if matched_text == href:
            replacement = f"[[{href}]]"
        else:
            replacement = f"[[{href}|{matched_text}]]"
        new_body = new_body[:start] + replacement + new_body[end:]

    new_text = frontmatter_block + new_body
    changed = new_text != text
    return new_text, changed, len(accepted)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Auto-insert [[wikilinks]] across a Markdown wiki based on "
                    "page titles and aliases."
    )
    parser.add_argument("--wiki-dir", required=True, type=Path,
                        help="Root folder containing the .md wiki pages.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing files.")
    parser.add_argument("--all-occurrences", action="store_true",
                        help="Link every occurrence of a term, not just the first "
                             "per target page in each file.")
    parser.add_argument("--min-length", type=int, default=2,
                        help="Skip terms shorter than this many characters "
                             "(default: 2).")
    parser.add_argument("--case-sensitive-terms", type=str, default="",
                        help="Comma-separated list of exact terms to match "
                             "case-sensitively instead of the default "
                             "case-insensitive matching, e.g. 'N,T,M' if those "
                             "single letters are too ambiguous otherwise.")
    parser.add_argument("--exclude", type=str, default="",
                        help="Comma-separated list of terms to never auto-link "
                             "(case-insensitive), e.g. 'RE,RP,T,N,M'.")
    args = parser.parse_args()

    args.exclude_set = {t.strip().lower() for t in args.exclude.split(",") if t.strip()}
    args.case_sensitive_terms = {t.strip() for t in args.case_sensitive_terms.split(",") if t.strip()}

    wiki_dir = args.wiki_dir
    if not wiki_dir.is_dir():
        print(f"Error: {wiki_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Indexing wiki pages under {wiki_dir} ...")
    entries, file_targets, href_to_target = build_index(wiki_dir)
    print(f"  {len(file_targets)} pages, {len(entries)} linkable terms "
          f"(titles + aliases)\n")

    total_links = 0
    total_changed_files = 0

    for path in sorted(wiki_dir.rglob("*.md")):
        new_text, changed, n_links = process_file(
            path, entries, file_targets, href_to_target, args
        )
        if changed:
            total_changed_files += 1
            total_links += n_links
            rel = path.relative_to(wiki_dir)
            print(f"  {rel}: +{n_links} link(s)")
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")

    print()
    if args.dry_run:
        print(f"[dry run] Would modify {total_changed_files} file(s), "
              f"adding {total_links} link(s) total.")
    else:
        print(f"Modified {total_changed_files} file(s), "
              f"added {total_links} link(s) total.")


if __name__ == "__main__":
    main()