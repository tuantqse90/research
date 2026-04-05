from scripts.libgen.slug import slugify, dated_dirname


def test_slugify_ascii_lowercases_and_dashes():
    assert slugify("Artificial Intelligence") == "artificial-intelligence"


def test_slugify_strips_diacritics():
    assert slugify("săn bắn") == "san-ban"


def test_slugify_removes_punctuation():
    assert slugify("hunt, track & kill!") == "hunt-track-kill"


def test_slugify_collapses_whitespace():
    assert slugify("   multi   space  ") == "multi-space"


def test_dated_dirname_basic():
    assert dated_dirname("2026-04-06", "hunt") == "2026-04-06_hunt"
