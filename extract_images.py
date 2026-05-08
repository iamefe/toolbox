#!/usr/bin/env python3
"""
extract_images.py

Reads a Google Docs-exported markdown file that embeds images as base64 data
URIs, saves each image as a real file, and rewrites the markdown to reference
those files instead.

Usage:
    python extract_images.py input.md
    python extract_images.py input.md --out-dir ./images --md-out clean.md
"""

import argparse
import base64
import os
import re
import sys


def extract_images(md_path: str, out_dir: str, md_out: str) -> None:
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    os.makedirs(out_dir, exist_ok=True)

    # Match reference-style image definitions:
    # [imageN]: <data:image/png;base64,....>
    # Also handles without angle brackets.
    pattern = re.compile(
        r"^\[(?P<name>[^\]]+)\]:\s*<?data:(?P<mime>image/[a-zA-Z+]+);base64,(?P<data>[A-Za-z0-9+/=\s]+)>?",
        re.MULTILINE,
    )

    replacements = {}  # name -> relative file path
    matches = list(pattern.finditer(content))

    if not matches:
        print("No base64 images found in the file.")
        return

    for m in matches:
        name = m.group("name")
        mime = m.group("mime")           # e.g. "image/png"
        raw = m.group("data").replace("\n", "").replace(" ", "")
        ext = mime.split("/")[-1].replace("jpeg", "jpg")  # normalise jpeg→jpg

        filename = f"{name}.{ext}"
        filepath = os.path.join(out_dir, filename)

        with open(filepath, "wb") as img_file:
            img_file.write(base64.b64decode(raw))

        replacements[name] = os.path.relpath(filepath, os.path.dirname(os.path.abspath(md_out)))
        print(f"  Saved {name} → {filepath}")

    # Rewrite inline image references: ![][imageN] → ![imageN](path)
    def replace_inline(match):
        name = match.group(1)
        path = replacements.get(name)
        if path:
            return f"![{name}]({path})"
        return match.group(0)  # leave unchanged if not found

    clean = re.sub(r"!\[\]\[([^\]]+)\]", replace_inline, content)

    # Remove the original base64 definition lines
    clean = pattern.sub("", clean).strip()

    with open(md_out, "w", encoding="utf-8") as f:
        f.write(clean)

    print(f"\nDone. {len(matches)} image(s) extracted.")
    print(f"Clean markdown written to: {md_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract base64 images from a Google Docs markdown export.")
    parser.add_argument("input", help="Path to the exported .md file")
    parser.add_argument("--out-dir", default="images", help="Directory to save image files (default: ./images)")
    parser.add_argument("--md-out", default=None, help="Output markdown path (default: input_clean.md)")
    args = parser.parse_args()

    md_out = args.md_out or os.path.splitext(args.input)[0] + "_clean.md"
    extract_images(args.input, args.out_dir, md_out)
