#!/usr/bin/env python3
"""
parse_gdocs_html.py

Converts a Google Docs HTML export (or "saved from URL" page) into clean,
readable text or Markdown. Strips browser-extension injections, minified CSS,
and Google Docs boilerplate so you can feed the result to an LLM like Qwen.

Dependencies:
    pip install beautifulsoup4 html2text

Usage:
    # Plain text output (default)
    python parse_gdocs_html.py Bugs.html

    # Markdown output
    python parse_gdocs_html.py Bugs.html --format markdown

    # Write to file instead of stdout
    python parse_gdocs_html.py Bugs.html --format markdown --out clean.md

    # Also extract embedded base64 images to a directory
    python parse_gdocs_html.py Bugs.html --format markdown --out clean.md --images ./images
"""

import argparse
import base64
import os
import re
import shutil
import sys

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    sys.exit("Missing dependency: run  pip install beautifulsoup4")

try:
    import html2text
except ImportError:
    html2text = None  # markdown output will warn but text still works


# ---------------------------------------------------------------------------
# Cleaning helpers
# ---------------------------------------------------------------------------

def _remove_browser_extension_nodes(soup: BeautifulSoup) -> None:
    """Remove tags injected by browser extensions (Plasmo, etc.)."""
    for tag in soup.find_all(["plasmo-csui", "plasmo-overlay"]):
        tag.decompose()
    # Also remove any <div> whose id starts with "plasmo-" or "crxjs-"
    for tag in soup.find_all(id=re.compile(r"^(plasmo|crxjs)-")):
        tag.decompose()


def _remove_hidden_and_script_nodes(soup: BeautifulSoup) -> None:
    """Remove scripts, styles, comments, and hidden elements."""
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    # Google Docs injects hidden spans for screen-reader content
    for tag in soup.find_all(attrs={"aria-hidden": "true"}):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        tag.decompose()


def _remove_gdocs_chrome(soup: BeautifulSoup) -> None:
    """Remove Google Docs navigation, header banners, and footer chrome."""
    # Published Docs wrap content in <div id="contents">; everything outside is nav
    for tag in soup.find_all(id=re.compile(r"^(header|footer|nav|sidebar|doc-header)", re.I)):
        tag.decompose()
    # The top banner shown when viewing a published doc
    for tag in soup.find_all("div", class_=re.compile(r"(kix-page-header|docs-titlebar|docs-toolbar)", re.I)):
        tag.decompose()


def _extract_images(soup: BeautifulSoup, out_dir: str) -> dict:
    """
    Find <img src="data:image/...;base64,..."> tags, save each to out_dir,
    replace src with the relative file path, and return a name→path map.
    """
    os.makedirs(out_dir, exist_ok=True)
    saved = {}
    counter = 1
    for img in soup.find_all("img"):
        src = img.get("src", "")
        m = re.match(r"data:(?P<mime>image/[a-zA-Z+]+);base64,(?P<data>.+)", src, re.DOTALL)
        if not m:
            continue
        mime = m.group("mime")
        raw = m.group("data").replace("\n", "").replace(" ", "")
        ext = mime.split("/")[-1].replace("jpeg", "jpg")
        filename = f"image{counter:03d}.{ext}"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(raw))
        img["src"] = filepath
        alt = img.get("alt") or filename
        img["alt"] = alt
        saved[filename] = filepath
        print(f"  Saved image → {filepath}", file=sys.stderr)
        counter += 1
    return saved


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def _get_content_root(soup: BeautifulSoup):
    """
    Return the narrowest container that holds the document body text.
    Google Docs published pages use <div id="contents"> or <body>.
    """
    for id_ in ("contents", "doc-content", "body-content"):
        node = soup.find(id=id_)
        if node:
            return node
    return soup.body or soup


def _copy_images_folder(html_path: str, out_path: str) -> str | None:
    """
    Google Docs HTML exports save images in a sibling folder named <stem>_files/.
    If that folder exists and --out points to a different directory, copy it there
    and return the new folder path (relative to out_path's directory).
    """
    html_dir = os.path.dirname(os.path.abspath(html_path))
    stem = os.path.splitext(os.path.basename(html_path))[0]
    src_folder = os.path.join(html_dir, f"{stem}_files")
    if not os.path.isdir(src_folder):
        return None

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if os.path.abspath(src_folder) == os.path.join(out_dir, f"{stem}_files"):
        return None  # already in the same directory

    dest_folder = os.path.join(out_dir, f"{stem}_files")
    shutil.copytree(src_folder, dest_folder, dirs_exist_ok=True)
    print(f"  Copied images folder → {dest_folder}", file=sys.stderr)
    return dest_folder


def parse(html_path: str, fmt: str, out_path: str | None, images_dir: str | None) -> None:
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    soup = BeautifulSoup(raw, "html.parser")

    # Strip noise
    _remove_browser_extension_nodes(soup)
    _remove_hidden_and_script_nodes(soup)
    _remove_gdocs_chrome(soup)

    # Optionally extract embedded base64 images
    if images_dir:
        saved = _extract_images(soup, images_dir)
        print(f"  {len(saved)} image(s) extracted.", file=sys.stderr)

    # Auto-copy the _files/ sibling folder when writing to a different directory
    if out_path:
        _copy_images_folder(html_path, out_path)

    content = _get_content_root(soup)

    if fmt == "markdown":
        if html2text is None:
            sys.exit("Missing dependency for markdown output: run  pip install html2text")
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0        # no hard line-wrapping
        h.protect_links = True
        h.unicode_snob = True
        result = h.handle(str(content))
    else:
        # Plain text: get_text preserves block structure via separator
        lines = []
        for elem in content.descendants:
            if isinstance(elem, str):
                text = elem.strip()
                if text:
                    lines.append(text)
        result = "\n".join(lines)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Output written to: {out_path}", file=sys.stderr)
    else:
        print(result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a Google Docs HTML export to clean text or Markdown."
    )
    parser.add_argument("input", help="Path to the .html file")
    parser.add_argument(
        "--format", choices=["text", "markdown"], default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--out", default=None,
        help="Write output to this file instead of stdout"
    )
    parser.add_argument(
        "--images", default=None, metavar="DIR",
        help="Extract embedded base64 images to this directory"
    )
    args = parser.parse_args()
    parse(args.input, args.format, args.out, args.images)
