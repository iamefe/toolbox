# 🧰 toolbox

![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square&logo=python&logoColor=white)
![Scripts](https://img.shields.io/badge/scripts-2-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-blueviolet?style=flat-square)

General-purpose utility scripts. Mostly for wrangling files before feeding them to LLMs.

---

## Folder structure

```
toolbox/
├── extract_images.py      # Google Docs Markdown export cleaner
├── parse_gdocs_html.py    # Google Docs HTML export converter
└── README.md
```

---

## Scripts

| Script | What it does |
|--------|-------------|
| [`parse_gdocs_html.py`](#parse_gdocs_htmlpy) | Converts a Google Docs HTML export to clean text or Markdown |
| [`extract_images.py`](#extract_imagespy) | Cleans up a Google Docs Markdown export by extracting embedded base64 images as real files and rewriting the document to reference them |

---

## Setup

These scripts use third-party Python libraries. The safest way to install them is inside a **virtual environment** — an isolated Python sandbox that won't interfere with your system.

### 1. Create a virtual environment

```bash
# Creates a folder called .venv in your home directory
python3 -m venv ~/.venvs/toolbox
```

> **Why not `pip3 install` directly?** On macOS (Sonoma and later), the system Python is externally managed — pip will refuse to install packages globally to protect Homebrew. A venv sidesteps this entirely.

### 2. Activate it

```bash
# macOS / Linux
source ~/.venvs/toolbox/bin/activate

# Windows (PowerShell)
.\.venvs\toolbox\Scripts\Activate.ps1
```

Your prompt will change to show `(toolbox)` when the venv is active.

### 3. Install dependencies

```bash
pip install beautifulsoup4 html2text
```

### 4. Run any script

```bash
python parse_gdocs_html.py MyDoc.html --format markdown --out clean.md
```

### Deactivating

```bash
deactivate
```

### Without activating (one-off)

If you don't want to activate the venv each time, call the venv's Python directly:

```bash
~/.venvs/toolbox/bin/python parse_gdocs_html.py MyDoc.html
```

---

## `parse_gdocs_html.py`

Converts a **Google Docs HTML export** into clean, readable text or Markdown. Strips browser-extension injections, minified CSS, hidden aria elements, and Google Docs navigation chrome — leaving only the document content.

When writing to a different directory, it automatically copies the sibling `_files/` images folder alongside the output so all image references stay intact.

### When to use this

Export your Google Doc via **File → Download → Web page (.html, zipped)**. Unzip it — you'll get a `.html` file and a `_files/` folder containing the images. Point this script at the `.html`.

### Usage

```bash
python parse_gdocs_html.py <input.html> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--format` | `text` | Output format: `text` or `markdown` |
| `--out` | stdout | Write output to this file |
| `--images` | — | Extract any embedded base64 images to this directory |

### Examples

**Plain text to terminal** — good for a quick read or piping to another tool:
```bash
python parse_gdocs_html.py Bugs.html
```

**Markdown to a file** — preserves headings, lists, links, and image references:
```bash
python parse_gdocs_html.py Bugs.html --format markdown --out bugs_clean.md
```

**Output to a different folder** — images are copied automatically:
```bash
python parse_gdocs_html.py Bugs.html --format markdown --out ~/Desktop/bugs_clean.md
# ~/Desktop/Bugs_files/ is created automatically alongside the markdown
```

**Feed directly to an LLM via clipboard** (macOS):
```bash
python parse_gdocs_html.py Bugs.html | pbcopy
# Now paste into Qwen, ChatGPT, etc.
```

### Output structure

```
Desktop/                        # wherever --out points
├── bugs_clean.md               # clean Markdown or text file
└── Bugs_files/                 # copied automatically from alongside the HTML
    ├── unnamed.png
    ├── unnamed(1).png
    └── ...
```

### How it works

Google Docs HTML exports contain several layers of noise:

1. **Browser extension injections** — tags like `<plasmo-csui>` inserted by extensions such as Plasmo. These appear before the actual document and can contain thousands of lines of minified CSS.
2. **Hidden aria elements** — Google injects invisible `<span aria-hidden="true">` elements for screen readers. They pollute plain-text extraction.
3. **Minified `<style>` blocks** — large amounts of CSS that are useless once you strip the HTML.
4. **Google Docs chrome** — header banners, navigation bars, and footer elements that wrap the published document.

The script removes all of these in sequence, then narrows focus to `<div id="contents">` (the actual document body), and either walks the text nodes directly (plain text) or pipes the cleaned HTML through `html2text` (Markdown).

---

## `extract_images.py`

Extracts base64-encoded images from a **Google Docs Markdown export** and rewrites the file to reference real image files instead.

### When to use this

Export your Google Doc via **File → Download → Markdown**. The `.md` file embeds every image as a giant base64 string, making it unreadable and far too large to paste into an LLM. This script fixes that.

### Usage

```bash
python extract_images.py <input.md> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--out-dir` | `./images` | Directory to save extracted image files |
| `--md-out` | `<input>_clean.md` | Path for the rewritten Markdown file |

### Examples

**Basic — output to default locations:**
```bash
python extract_images.py "Mobile App Brief.md"
# Saves images to ./images/
# Writes Mobile App Brief_clean.md
```

**Custom output directory and file:**
```bash
python extract_images.py "Mobile App Brief.md" --out-dir ./brief_images --md-out brief_clean.md
```

**Keep everything in one folder** (recommended):
```bash
mkdir brief_output
python extract_images.py "Mobile App Brief.md" \
  --out-dir ./brief_output \
  --md-out ./brief_output/brief_clean.md
# Both the markdown and images are in brief_output/
# Image references become: ![image1](image1.png)
```

### Output structure

```
brief_output/                   # wherever --out-dir and --md-out point
├── brief_clean.md              # rewritten Markdown with real image references
├── image001.png
├── image002.png
└── ...
```

### How it works

Google Docs Markdown exports use [reference-style image links](https://spec.commonmark.org/0.31.2/#link-reference-definitions):

```markdown
![][image1]

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...>
```

The script:
1. Finds all `[imageN]: <data:image/...;base64,...>` definitions using a regex
2. Decodes each blob and writes it to a real image file (`image1.png`, `image2.png`, etc.)
3. Rewrites `![][imageN]` inline references to `![imageN](path/to/image1.png)`
4. Strips the original base64 definition lines
5. Writes the clean Markdown to the output file

Image paths are always written **relative** to the output Markdown file, so the file is portable.

---

## Which script do I need?

```
Exported as...          Use
──────────────────────────────────────────────────
Web page (.html)   →    parse_gdocs_html.py
Markdown (.md)     →    extract_images.py
```

---

## License

MIT
