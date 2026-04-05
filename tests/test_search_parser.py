from pathlib import Path
from scripts.libgen.search import parse_search_results, SearchResult

FIXTURE = Path(__file__).parent / "fixtures" / "libgen_search.html"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_returns_list_of_results():
    results = parse_search_results(load_fixture())
    assert isinstance(results, list)
    assert len(results) >= 10, f"expected many results, got {len(results)}"
    assert all(isinstance(r, SearchResult) for r in results)


def test_parse_extracts_required_fields():
    results = parse_search_results(load_fixture())
    first = results[0]
    assert first.title, "title must be non-empty"
    assert first.extension.lower() in {"pdf", "epub", "djvu", "mobi", "azw3"}
    assert first.mirror_urls, "mirror_urls must be non-empty"


def test_parse_year_is_int_or_none():
    results = parse_search_results(load_fixture())
    for r in results:
        assert r.year is None or isinstance(r.year, int)


def test_parse_pages_is_int_or_none():
    results = parse_search_results(load_fixture())
    for r in results:
        assert r.pages is None or isinstance(r.pages, int)


def test_parse_md5_when_available():
    results = parse_search_results(load_fixture())
    # At least one result should have an md5 extracted from its mirror URLs
    with_md5 = [r for r in results if r.md5]
    assert len(with_md5) > 0, "expected at least one result with md5"
    # md5 is a 32-char hex string
    for r in with_md5:
        assert len(r.md5) == 32
        assert all(c in "0123456789abcdef" for c in r.md5)
