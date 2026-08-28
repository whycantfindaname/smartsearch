import smart_search.providers.base  # noqa: F401  (must load before utils; utils imports through it)
from smart_search.utils import format_extra_sources


def test_tavily_duplicates_are_removed():
    tavily = [
        {"title": "First", "url": "https://example.com/a", "content": "alpha"},
        {"title": "Dup", "url": "https://example.com/a", "content": "alpha again"},
        {"title": "Second", "url": "https://example.com/b", "content": "beta"},
    ]
    rendered = format_extra_sources(tavily_results=tavily, firecrawl_results=None)
    assert rendered.count("https://example.com/a") == 1
    assert "https://example.com/b" in rendered
    assert "alpha again" not in rendered


def test_tavily_urls_already_seen_in_firecrawl_are_skipped():
    firecrawl = [{"title": "FC", "url": "https://example.com/a", "description": "desc"}]
    tavily = [{"title": "TV", "url": "https://example.com/a", "content": "dup"}]
    rendered = format_extra_sources(tavily_results=tavily, firecrawl_results=firecrawl)
    assert rendered.count("https://example.com/a") == 1
