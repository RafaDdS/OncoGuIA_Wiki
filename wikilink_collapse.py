#!/usr/bin/env python3
"""
wikilink_collapse.py

Companion to wikilink_generator.py. Strips every [[wikilink]] in the wiki
back down to its plain display text, so that wikilink_generator.py can
relink everything from scratch based on the *current* file structure.

Why this exists: mkdocs-roamlinks-plugin resolves [[Links]] by matching
filenames at MkDocs build time. When pages get renamed or moved to a
different category, previously-correct links can silently start pointing
nowhere (or nowhere useful) with no error at generation time. Rather than
re-implementing the plugin's own resolution/ambiguity rules just to detect
which links are now "broken," it's simpler and more robust to reset every
link to plain text and let wikilink_generator.py rebuild the whole set
consistently from the wiki's current title/alias index.

Recommended workflow after any reorganization (moving/renaming pages,
folders, or changing categories):

    python wikilink_collapse.py --wiki-dir wiki
    python wikilink_generator.py --wiki-dir wiki --dry-run
    python wikilink_generator.py --wiki-dir wiki

What it leaves untouched:
  - Frontmatter (never touched).
  - Fenced ```code blocks``` and inline `code` (protected, same as the
    generator).
  - Embeds, e.g. ![[image.png]] (the leading "!" marks these as file/image
    embeds, not page links -- collapsing them would just break the embed).
  - External links whose target contains "://" (e.g. [[https://...]]),
    left exactly as-is.

Everything else -- [[Target]] and [[Target|Display text]] -- is replaced
with just its display text (the alias if present, otherwise the target
name with any "#anchor" suffix stripped), turning it back into plain,
unlinked prose.

Usage:
    python wikilink_collapse.py --wiki-dir wiki --dry-run
    python wikilink_collapse.py --wiki-dir wiki
"""

import argparse
import re
import sys
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
CODE_RE = re.compile(r"(```.*?```|`[^`]*`)", re.DOTALL)
# Negative lookbehind for "!" so embeds (![[file.png]]) are left alone.
WIKILINK_RE = re.compile(r"(?<!\!)\[\[([^\]]+)\]\]")


def redact_code(text):
    """Replace fenced/inline code with placeholder tokens so links inside
    code are never touched, then give back a way to restore them."""
    blocks = {}

    def repl(m):
        key = f"\x00CODE{len(blocks)}\x00"
        blocks[key] = m.group(0)
        return key

    return CODE_RE.sub(repl, text), blocks


def restore_code(text, blocks):
    for key, block in blocks.items():
        text = text.replace(key, block)
    return text


def collapse_body(body):
    """Return (new_body, count_collapsed)."""
    redacted, blocks = redact_code(body)
    count = 0

    def repl(m):
        nonlocal count
        inner = m.group(1)
        parts = inner.split("|")
        href = parts[0].strip()

        if "://" in href:
            return m.group(0)  # leave external links alone

        count += 1
        if len(parts) > 1 and parts[1].strip():
            display = parts[1].strip()
        else:
            display = href.split("#")[0].strip()
        return display

    new_redacted = WIKILINK_RE.sub(repl, redacted)
    new_body = restore_code(new_redacted, blocks)
    return new_body, count


def process_file(path):
    text = path.read_text(encoding="utf-8")
    fm_match = FRONTMATTER_RE.match(text)
    if fm_match:
        frontmatter_block = fm_match.group(0)
        body = text[fm_match.end():]
    else:
        frontmatter_block = ""
        body = text

    new_body, count = collapse_body(body)
    new_text = frontmatter_block + new_body
    changed = new_text != text
    return new_text, changed, count


def main():
    parser = argparse.ArgumentParser(
        description="Strip [[wikilinks]] back to plain text across a Markdown "
                    "wiki, so wikilink_generator.py can rebuild them cleanly."
    )
    parser.add_argument("--wiki-dir", required=True, type=Path,
                        help="Root folder containing the .md wiki pages.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing files.")
    args = parser.parse_args()

    wiki_dir = args.wiki_dir
    if not wiki_dir.is_dir():
        print(f"Error: {wiki_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning wiki pages under {wiki_dir} ...")

    total_links = 0
    total_changed_files = 0

    for path in sorted(wiki_dir.rglob("*.md")):
        new_text, changed, count = process_file(path)
        if changed:
            total_changed_files += 1
            total_links += count
            rel = path.relative_to(wiki_dir)
            print(f"  {rel}: -{count} link(s)")
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")

    print()
    if args.dry_run:
        print(f"[dry run] Would modify {total_changed_files} file(s), "
              f"collapsing {total_links} link(s) total.")
    else:
        print(f"Modified {total_changed_files} file(s), "
              f"collapsed {total_links} link(s) total.")
        print("\nNow run wikilink_generator.py to rebuild links from the "
              "current wiki structure.")


if __name__ == "__main__":
    main()