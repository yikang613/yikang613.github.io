"""Dependency-free structural and disclosure checks for the static portfolio."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.stylesheets: list[str] = []
        self.html_lang: str | None = None
        self.title_depth = 0
        self.title_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang")
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(values["href"] or "")
        if tag == "title":
            self.title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.title_depth = max(0, self.title_depth - 1)

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_text.append(data)


def main() -> int:
    html_path = ROOT / "index.html"
    css_path = ROOT / "styles.css"
    html = html_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(html)

    errors: list[str] = []
    duplicate_ids = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    if duplicate_ids:
        errors.append(f"duplicate HTML ids: {', '.join(duplicate_ids)}")
    missing_anchors = sorted(
        href[1:] for href in parser.hrefs if href.startswith("#") and href[1:] not in parser.ids
    )
    if missing_anchors:
        errors.append(f"missing internal anchors: {', '.join(missing_anchors)}")
    if parser.html_lang != "en":
        errors.append("html lang must be en")
    if not "".join(parser.title_text).strip():
        errors.append("document title is missing")
    for stylesheet in parser.stylesheets:
        if stylesheet.startswith(("http://", "https://")):
            errors.append("external stylesheet is not permitted")
        elif not (ROOT / stylesheet).is_file():
            errors.append(f"missing stylesheet: {stylesheet}")
    if css.count("{") != css.count("}"):
        errors.append("CSS braces are unbalanced")

    sensitive_patterns = {
        "API credential": r"(?:sk-ant-|sk-proj-|ghp_)[A-Za-z0-9_-]{20,}",
        "NACC-shaped identifier": r"NACC[0-9]{4,}",
        "ADNI-shaped identifier": r"\b[0-9]{3}_S_[0-9]{3,}\b",
    }
    for label, pattern in sensitive_patterns.items():
        if re.search(pattern, html):
            errors.append(f"public HTML contains {label}")

    unpublished_copath_details = (
        "autopsy",
        "postmortem",
        "five-axis",
        "tdp-43",
        "cerebral amyloid angiopathy",
    )
    lowered = html.lower()
    for term in unpublished_copath_details:
        if term in lowered:
            errors.append(f"public HTML contains restricted CopathAgent detail: {term}")

    if errors:
        print("Site validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        f"Site validation passed: {len(parser.ids)} ids, "
        f"{len(parser.hrefs)} links, {len(parser.stylesheets)} stylesheet."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
