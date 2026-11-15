"""Catch broken element references when the page structure is reorganized."""
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


class PageElements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        element_id = dict(attrs).get("id")
        if element_id:
            self.ids.append(element_id)


def test_pages_keep_unique_element_identifiers():
    for name in ["index.html", "onboarding.html", "study.html"]:
        page = PageElements()
        page.feed((FRONTEND / name).read_text(encoding="utf-8"))
        assert all(count == 1 for count in Counter(page.ids).values()), name


def test_static_script_controls_are_present_or_created_dynamically():
    groups = [("index.html", ["app.js", "review_ui.js"]),
              ("onboarding.html", ["onboarding.js"]), ("study.html", ["study.js"])]
    for name, scripts in groups:
        page = PageElements()
        page.feed((FRONTEND / name).read_text(encoding="utf-8"))
        code = "\n".join((FRONTEND / "js" / script).read_text(encoding="utf-8") for script in scripts)
        created = set(re.findall(r'''\bid=["']([a-z][a-z0-9-]*)["']''', code))
        referenced = set(re.findall(r'''(?:getElementById|\$)\(["']([a-z][a-z0-9-]*)["']\)''', code))
        assert not referenced - set(page.ids) - created, (name, referenced - set(page.ids) - created)
