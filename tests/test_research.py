from sima2_bazzite.research import make_feature_queries, youtube_search


def test_make_feature_queries_contains_build_and_mod_learning() -> None:
    queries = make_feature_queries(["machines"])
    assert "minecraft machines build tutorial" in queries
    assert "minecraft machines automation guide" in queries


def test_youtube_search_parses_results(monkeypatch) -> None:
    fake_html = (
        '"videoId":"abcdefghijk"'
        '"title":{"runs":[{"text":"Create & Expand Base"}]}'
        '"videoId":"lmnopqrstuv"'
        '"title":{"runs":[{"text":"Mod Progression Guide"}]}'
    )

    monkeypatch.setattr("sima2_bazzite.research._get_text", lambda *args, **kwargs: fake_html)
    results = youtube_search("minecraft mod tutorial", limit=2)
    assert len(results) == 2
    assert results[0].url.endswith("abcdefghijk")
    assert "Create" in results[0].title
