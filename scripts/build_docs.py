"""Build the README and docs/ as linked HTML pages for a browser -> site/ (not committed).

    pip install markdown
    python scripts/build_docs.py              # then open site/index.html
    python scripts/build_docs.py --open       # build and open in the default browser
    python scripts/build_docs.py --src PATH   # build another checkout (e.g. a worktree)

"""
import argparse
import re
import shutil
import webbrowser
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
NAV = [("index.html", "Home"), ("readme.html", "README & roadmap"), ("gap.html", "The gap"),
       ("roadmap.html", "What is missing"), ("model_design.html", "Model design"),
       ("assumptions.html", "Assumptions")]
CSS = """
:root { --bg:#ffffff; --fg:#1d1d1b; --muted:#5f5e5a; --line:#e3e2dc; --link:#1f6fc9; --code:#f4f3ef; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg:#1b1b1a; --fg:#ecebe6; --muted:#a8a69e; --line:#3a3a37; --link:#7db4f0; --code:#262624; } }
body { background:var(--bg); color:var(--fg); margin:0; font:16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
nav { position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line); padding:10px 16px;
  display:flex; flex-wrap:wrap; gap:6px 18px; font-size:14px; z-index:1; }
nav a { color:var(--muted); text-decoration:none; } nav a.on { color:var(--fg); font-weight:600; }
main { max-width:960px; margin:0 auto; padding:16px 16px 64px; }
a { color:var(--link); } h1, h2, h3 { line-height:1.25; } h2 { border-bottom:1px solid var(--line); padding-bottom:4px; }
img { max-width:100%; height:auto; background:#fff; border-radius:4px; }
table { border-collapse:collapse; display:block; overflow-x:auto; font-size:14px; margin:12px 0; }
th, td { border:1px solid var(--line); padding:4px 8px; vertical-align:top; } th { text-align:left; }
code { background:var(--code); padding:1px 4px; border-radius:3px; font-size:90%; }
pre { background:var(--code); padding:12px; overflow-x:auto; border-radius:4px; } pre code { padding:0; }
footer { color:var(--muted); font-size:13px; margin-top:48px; }
"""


def page(title, body, current, up=""):
    links = " ".join(f'<a href="{up}{h}"{" class=on" if h == current else ""}>{t}</a>' for h, t in NAV)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>'
            f"<style>{CSS}</style></head><body><nav>{links}</nav><main>{body}"
            f"<footer>Built from the repository's Markdown by scripts/build_docs.py.</footer></main></body></html>")


def render(text, from_readme):
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)          # Jekyll front matter
    html = markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"])

    def fix(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"[a-z]+:|#", url):
            return m.group(0)
        if url.startswith("https://github.com/andrewlyden/pypsa-gb-abm#"):
            return f'{attr}="readme.html#{url.split("#", 1)[1]}"'
        path, _, frag = url.partition("#")
        if from_readme:
            if path.startswith("docs/"):
                path = path[5:]
            elif path == "README.md":
                path = "readme.html"
            elif not path.startswith("results/"):
                path = "../" + path
        elif path == "../README.md":
            path = "readme.html"
        elif path.startswith("../results/"):
            path = path[3:]
        if path.endswith(".md"):
            path = path[:-3] + ".html"
        return f'{attr}="{path}{"#" + frag if frag else ""}"'
    return re.sub(r'(href|src)="([^"]+)"', fix, html)


def build(src: Path, out: Path):
    docs = src / "docs"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(docs, out, ignore=shutil.ignore_patterns("*.md", "_config.yml"))   # figures, data files
    for md in sorted(docs.rglob("*.md")):
        rel = md.relative_to(docs).with_suffix(".html")
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        text = md.read_text(encoding="utf-8")
        title = next((l[2:] for l in text.splitlines() if l.startswith("# ")), md.stem)
        up = "../" * (len(rel.parts) - 1)
        target.write_text(page(title, render(text, False), rel.as_posix(), up), encoding="utf-8")
    for md in sorted((src / "results").glob("*.md")):              # result tables linked from the docs
        target = out / "results" / md.with_suffix(".html").name
        target.parent.mkdir(parents=True, exist_ok=True)
        body = render(md.read_text(encoding="utf-8"), False).replace('src="figures/', 'src="../figures/')
        target.write_text(page(md.stem, body, "", "../"), encoding="utf-8")
    readme = (src / "README.md").read_text(encoding="utf-8")
    (out / "readme.html").write_text(page("pypsa-gb-abm README", render(readme, True), "readme.html"), encoding="utf-8")
    return out / "index.html"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--src", type=Path, default=ROOT, help="checkout to build from (default: this one)")
    p.add_argument("--out", type=Path, default=ROOT / "site")
    p.add_argument("--open", action="store_true")
    a = p.parse_args()
    index = build(a.src.resolve(), a.out.resolve())
    print(f"built {index}")
    if a.open:
        webbrowser.open(index.as_uri())
