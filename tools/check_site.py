"""Check the site before it ships: metadata, links, assets, sitemap, robots, structured data, JS.

Static checks read docs/ as GitHub Pages will serve it (a directory serves its index.html). Then a
local HTTP server serves docs/ and every page and every local file a page uses is fetched for real.

Run: python tools/check_site.py          (Python standard library; uses node for the JS syntax check
                                          when it is installed)
Exit status 1 when anything fails.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
DOCS = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "docs"  # another copy, for testing the checks
SITE = "https://7antsgames.com"
DOMAIN = "7antsgames.com"
REQUIRED_META = ["og:type", "og:site_name", "og:title", "og:description", "og:url", "og:image",
                 "twitter:card", "twitter:image"]
# Pages that must exist (the site's public URLs).
EXPECTED_PAGES = ["/", "/fuck-off/", "/fuck-off/momentum-physics/", "/slot-theory/", "/slot-theory/how-to-play/"]

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.titles: list[str] = []
        self.meta: dict[str, list[str]] = {}
        self.links: list[tuple[str, str]] = []      # (rel, href) of <link>
        self.refs: list[tuple[str, str, str]] = []   # (tag, attr, value) local resources and links
        self.anchors: list[str] = []                 # <a href>
        self.ids: set[str] = set()
        self.h: list[tuple[int, str]] = []
        self.imgs: list[dict[str, str | None]] = []
        self.jsonld: list[str] = []
        self.text: list[str] = []
        self._in: list[str] = []
        self._heading: tuple[int, list[str]] | None = None
        self._title: list[str] | None = None
        self._script_type: str | None = None
        self._script: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"] or "")
        if tag == "title":
            self._title = []
        elif tag == "meta":
            key = a.get("property") or a.get("name")
            if key:
                self.meta.setdefault(key, []).append(a.get("content") or "")
        elif tag == "link":
            self.links.append((a.get("rel") or "", a.get("href") or ""))
            if a.get("href"):
                self.refs.append((tag, "href", a["href"] or ""))
        elif tag == "a" and a.get("href"):
            self.anchors.append(a["href"] or "")
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "script":
            self._script_type = a.get("type") or "text/javascript"
            self._script = []
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = (int(tag[1]), [])
        if tag == "img" and a.get("alt"):
            if self._heading:
                self._heading[1].append(a["alt"] or "")
        for attr in ("src", "poster", "data-full"):
            if a.get(attr):
                self.refs.append((tag, attr, a[attr] or ""))
        if a.get("srcset"):
            for part in (a["srcset"] or "").split(","):
                if part.strip():
                    self.refs.append((tag, "srcset", part.strip().split()[0]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._title is not None:
            self.titles.append("".join(self._title).strip())
            self._title = None
        elif tag == "script":
            if self._script_type == "application/ld+json":
                self.jsonld.append("".join(self._script))
            self._script_type = None
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading:
            self.h.append((self._heading[0], re.sub(r"\s+", " ", "".join(self._heading[1])).strip()))
            self._heading = None

    def handle_data(self, data: str) -> None:
        if self._title is not None:
            self._title.append(data)
        if self._script_type is not None:
            self._script.append(data)
            return
        if self._heading:
            self._heading[1].append(data)
        self.text.append(data)


def url_of(path: Path) -> str:
    rel = path.relative_to(DOCS).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def local_file(url_path: str) -> Path | None:
    """The file GitHub Pages serves for a site path, or None."""
    p = unquote(url_path.split("#")[0].split("?")[0])
    target = DOCS / p.lstrip("/")
    if p.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target if target.is_file() else None


def resolve(base: str, ref: str) -> str | None:
    """A reference made absolute against the page URL; None when it leaves the site."""
    if ref.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    full = urljoin(SITE + base, ref)
    u = urlparse(full)
    if u.netloc != DOMAIN:
        return None
    return u.path + (("#" + u.fragment) if u.fragment else "")


def main() -> int:
    pages: dict[str, Page] = {}
    for f in sorted(DOCS.rglob("*.html")):
        p = Page()
        p.feed(f.read_text(encoding="utf-8"))
        pages[url_of(f)] = p

    indexable = {u: p for u, p in pages.items() if "noindex" not in " ".join(p.meta.get("robots", []))}
    print(f"pages: {len(pages)} ({len(indexable)} indexable): {', '.join(sorted(pages))}")

    # ---------- deployment basics ----------
    cname = (DOCS / "CNAME").read_text(encoding="utf-8").strip() if (DOCS / "CNAME").exists() else ""
    if cname != DOMAIN:
        fail(f"docs/CNAME is {cname!r}, expected {DOMAIN!r}")
    if not (DOCS / ".nojekyll").exists():
        fail("docs/.nojekyll is missing")
    for u in EXPECTED_PAGES:
        if u not in indexable:
            fail(f"{u}: expected public page is missing or noindex")

    # ---------- per-page metadata ----------
    descriptions: dict[str, str] = {}
    titles: dict[str, str] = {}
    for u, p in pages.items():
        where = u
        if len(p.titles) != 1 or not p.titles[0]:
            fail(f"{where}: {len(p.titles)} <title> elements")
        h1 = [t for lvl, t in p.h if lvl == 1]
        if len(h1) != 1:
            fail(f"{where}: {len(h1)} h1 elements {h1}")
        elif not h1[0]:
            fail(f"{where}: the h1 has no text")
        # headings must not skip a level going down
        prev = 0
        for lvl, text in p.h:
            if prev and lvl > prev + 1:
                fail(f"{where}: heading h{lvl} {text!r} follows h{prev}")
            prev = lvl
        for img in p.imgs:
            if "alt" not in img:
                fail(f"{where}: <img src={img.get('src')}> has no alt attribute")
        text = "".join(p.text)
        if "—" in text or "–" in text:
            fail(f"{where}: an em or en dash in the copy")
        if u not in indexable:
            continue
        desc = (p.meta.get("description") or [""])[0]
        if not 50 <= len(desc) <= 170:
            fail(f"{where}: meta description is {len(desc)} characters")
        if desc in descriptions.values():
            fail(f"{where}: meta description repeats another page's")
        descriptions[u] = desc
        if p.titles and p.titles[0] in titles.values():
            fail(f"{where}: title repeats another page's")
        titles[u] = p.titles[0] if p.titles else ""
        canon = [h for rel, h in p.links if rel == "canonical"]
        if canon != [SITE + u]:
            fail(f"{where}: canonical {canon}, expected {[SITE + u]}")
        for key in REQUIRED_META:
            if not p.meta.get(key) or not p.meta[key][0]:
                fail(f"{where}: meta {key} missing")
        if p.meta.get("og:url", [""])[0] != SITE + u:
            fail(f"{where}: og:url {p.meta.get('og:url')} is not the canonical URL")
        for key in ("og:image", "twitter:image"):
            img = p.meta.get(key, [""])[0]
            if not img.startswith(SITE + "/"):
                fail(f"{where}: {key} {img!r} is not an absolute {SITE} URL")
            elif not local_file(urlparse(img).path):
                fail(f"{where}: {key} {img} does not exist in docs/")
        if p.meta.get("robots") and "noindex" in p.meta["robots"][0]:
            fail(f"{where}: noindex on an indexable page")

    # ---------- local references and internal links ----------
    used_files: set[str] = set()
    for u, p in pages.items():
        for tag, attr, ref in p.refs:
            path = resolve(u, ref)
            if path is None:
                continue
            if not local_file(path):
                fail(f"{u}: <{tag} {attr}={ref!r}> does not exist")
            else:
                used_files.add(path.split("#")[0].split("?")[0])
        for href in p.anchors:
            path = resolve(u, href)
            if path is None:
                continue
            page_path, _, frag = path.partition("#")
            target = local_file(page_path)
            if not target:
                fail(f"{u}: link {href!r} goes nowhere")
                continue
            if target.suffix == ".html" and not page_path.endswith((".html", "/")) and page_path != "":
                fail(f"{u}: link {href!r} lacks the trailing slash (a redirect on GitHub Pages)")
            if frag:
                target_url = url_of(target)
                if frag not in pages[target_url].ids:
                    fail(f"{u}: link {href!r}: no id {frag!r} on {target_url}")
            else:
                used_files.add(page_path)
    # url(...) in the stylesheet
    css = (DOCS / "style.css").read_text(encoding="utf-8")
    for ref in re.findall(r"url\(\"?([^\")]+)\"?\)", css):
        path = resolve("/style.css", ref)
        if path and not local_file(path):
            fail(f"style.css: url({ref}) does not exist")
        elif path:
            used_files.add(path)
    js = (DOCS / "app.js").read_text(encoding="utf-8")
    for ref in re.findall(r"\"(/assets/[^\"]+)\"", js):
        if not local_file(ref):
            fail(f"app.js: {ref} does not exist")
        used_files.add(ref)

    # ---------- sitemap and robots ----------
    sitemap_urls: list[str] = []
    try:
        tree = ET.parse(DOCS / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        if tree.getroot().tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
            fail("sitemap.xml: the root is not a sitemaps.org urlset")
        sitemap_urls = [e.text.strip() for e in tree.getroot().findall("s:url/s:loc", ns) if e.text]
    except (ET.ParseError, FileNotFoundError) as e:
        fail(f"sitemap.xml: {e}")
    if len(sitemap_urls) != len(set(sitemap_urls)):
        fail("sitemap.xml: duplicate URLs")
    for loc in sitemap_urls:
        if not loc.startswith(SITE + "/"):
            fail(f"sitemap.xml: {loc} is not on {SITE}")
    expected = sorted(SITE + u for u in indexable)
    if sorted(sitemap_urls) != expected:
        fail(f"sitemap.xml lists {sorted(sitemap_urls)}, the indexable pages are {expected}")
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8") if (DOCS / "robots.txt").exists() else ""
    if f"Sitemap: {SITE}/sitemap.xml" not in robots:
        fail("robots.txt: no Sitemap line for the sitemap")
    if re.search(r"(?im)^\s*Disallow:\s*/\s*$", robots):
        fail("robots.txt disallows the whole site")

    # ---------- structured data ----------
    nodes: dict[str, list[tuple[str, dict]]] = {}
    refs: list[tuple[str, str]] = []

    def walk(u: str, obj: object, top: bool) -> None:
        if isinstance(obj, dict):
            if "@id" in obj and len(obj) > 1:
                nodes.setdefault(obj["@id"], []).append((u, obj))
            elif "@id" in obj:
                refs.append((u, obj["@id"]))
            for k, v in obj.items():
                if k != "@id":
                    walk(u, v, False)
        elif isinstance(obj, list):
            for v in obj:
                walk(u, v, False)

    for u, p in pages.items():
        if u in indexable and not p.jsonld:
            fail(f"{u}: no JSON-LD")
        for block in p.jsonld:
            try:
                data = json.loads(block)
            except json.JSONDecodeError as e:
                fail(f"{u}: JSON-LD does not parse: {e}")
                continue
            if data.get("@context") != "https://schema.org":
                fail(f"{u}: JSON-LD @context is {data.get('@context')!r}")
            graph = data.get("@graph", [data])
            ids_here = [n.get("@id") for n in graph if isinstance(n, dict)]
            if len(ids_here) != len(set(ids_here)):
                fail(f"{u}: a JSON-LD @id appears twice on the page")
            walk(u, data, True)
            types = {n.get("@type") for n in graph if isinstance(n, dict)}
            if u in indexable and "WebPage" not in types:
                fail(f"{u}: JSON-LD has no WebPage")
            for n in graph:
                if isinstance(n, dict) and n.get("@type") == "WebPage" and n.get("url") != SITE + u:
                    fail(f"{u}: WebPage url {n.get('url')} is not the page")
    for node_id, defs in nodes.items():
        for key in ("@type", "name", "url"):
            vals = {json.dumps(d.get(key)) for _, d in defs if key in d}
            if len(vals) > 1:
                fail(f"JSON-LD {node_id}: {key} differs between pages: {sorted(vals)}")
        for u, d in defs:
            if d.get("url", "").startswith(SITE) and not local_file(urlparse(d["url"]).path):
                fail(f"JSON-LD {node_id} on {u}: url {d['url']} does not exist")
            if not node_id.startswith(SITE + "/"):
                fail(f"JSON-LD @id {node_id} is not on {SITE}")
    for u, ref in refs:
        if ref not in nodes:
            fail(f"{u}: JSON-LD refers to {ref}, defined nowhere on the site")
    for u, p in pages.items():
        for block in p.jsonld:
            for img in re.findall(rf"\"({re.escape(SITE)}/assets/[^\"]+)\"", block):
                if not local_file(urlparse(img).path):
                    fail(f"{u}: JSON-LD image {img} does not exist")
    game_pub = [d.get("publisher") for defs in nodes.values() for _, d in defs if d.get("@type") == "VideoGame" and "description" in d]
    if not game_pub or any(pub != {"@id": SITE + "/#organization"} for pub in game_pub):
        fail("JSON-LD: every full VideoGame needs publisher 7 Ants Games (#organization)")

    # ---------- JavaScript ----------
    node = shutil.which("node")
    if node:
        r = subprocess.run([node, "--check", str(DOCS / "app.js")], capture_output=True, text=True)
        if r.returncode:
            fail(f"app.js: {r.stderr.strip()}")
    else:
        notes.append("node not found: app.js syntax not checked")

    # ---------- served for real ----------
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    fetched = 0
    try:
        for path in sorted(set(pages) | used_files | {"/robots.txt", "/sitemap.xml"}):
            # Pages and text are read in full; media only by HEAD.
            method = "GET" if path.endswith(("/", ".html", ".css", ".js", ".txt", ".xml")) else "HEAD"
            try:
                with urllib.request.urlopen(urllib.request.Request(base + path, method=method)) as r:
                    r.read()
                    if r.status != 200:
                        fail(f"{method} {path}: {r.status}")
                    fetched += 1
            except urllib.error.HTTPError as e:
                fail(f"{method} {path}: {e.code}")
        # A directory without its slash is redirected to it, as GitHub Pages does.
        for u in EXPECTED_PAGES[1:]:
            req = urllib.request.Request(base + u.rstrip("/"))
            with urllib.request.urlopen(req) as r:
                r.read()
                if not r.url.endswith(u):
                    fail(f"GET {u.rstrip('/')}: ended at {r.url}")
    finally:
        server.shutdown()
    print(f"served: {fetched} paths fetched over HTTP")

    for n in notes:
        print("note:", n)
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
