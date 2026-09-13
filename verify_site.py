from html.parser import HTMLParser
from pathlib import Path


class PageParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.images: list[dict[str, str | None]] = []
        self.ids: list[str] = []
        self.text: list[str] = []
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID_TAGS:
            self.stack.append(tag)
        values = dict(attrs)
        if values.get("href"):
            self.links.append(values["href"] or "")
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "img":
            self.images.append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[index]

    def handle_data(self, data: str) -> None:
        self.text.append(data)


root = Path(__file__).resolve().parent
pages = [root / "index.html", root / "terms-of-service.html", root / "advertising-policy.html"]
expected_internal = {page.name for page in pages} | {"styles.css", "app_logo.png", "studio_logo.jpg"}

for page in pages:
    parser = PageParser()
    parser.feed(page.read_text(encoding="utf-8"))
    parser.close()
    assert not parser.stack, f"Unclosed tags in {page.name}: {parser.stack}"
    assert len(parser.ids) == len(set(parser.ids)), f"Duplicate id in {page.name}"
    content = " ".join(parser.text)
    for required in ("English", "Türkçe", "PerfectSky Studios", "perfectskystudios@gmail.com"):
        assert required in content, f"Missing {required!r} in {page.name}"
    for link in parser.links:
        target = link.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        assert target in expected_internal, f"Unexpected internal target {target!r} in {page.name}"
        assert (root / target).is_file(), f"Missing internal target {target!r} in {page.name}"

    for retired in ("13–15", "16–17", "local age/country profile", "yerel yaş/ülke profili", "App Hive", "AppHive"):
        assert retired not in content, f"Retired audience copy {retired!r} in {page.name}"
    studio_images = [image for image in parser.images if image.get("src") == "studio_logo.jpg"]
    assert len(studio_images) == 1, f"Missing or duplicate studio logo in {page.name}"
    assert studio_images[0].get("alt") == "PerfectSky Studios", f"Missing studio logo description in {page.name}"
    for image in parser.images:
        source = image.get("src")
        assert source in expected_internal and (root / source).is_file(), f"Missing image in {page.name}"

for policy_name in ("index.html", "advertising-policy.html"):
    policy = (root / policy_name).read_text(encoding="utf-8")
    assert "18 and over" in policy and "18 yaş ve üzeri" in policy
    assert "does not ask for, store or infer" in policy
    assert "sormaz, saklamaz ya da tahmin etmez" in policy
    assert "canRequestAds" not in policy  # public text uses plain language, not API jargon

print("Legal site static verification: PASS (3 bilingual pages, links and contact details)")
