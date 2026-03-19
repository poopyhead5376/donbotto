from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


@dataclass(slots=True)
class VideoResult:
    title: str
    url: str


def _get_text(url: str, timeout: float = 20.0) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def youtube_search(query: str, limit: int = 5) -> list[VideoResult]:
    q = quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={q}"
    text = _get_text(url)

    watch_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', text)
    titles = re.findall(r'"title":\{"runs":\[\{"text":"(.*?)"\}\]', text)

    seen: set[str] = set()
    results: list[VideoResult] = []
    for idx, vid in enumerate(watch_ids):
        if vid in seen:
            continue
        seen.add(vid)
        title = titles[idx] if idx < len(titles) else f"YouTube video {vid}"
        clean_title = title.replace("\\u0026", "&")
        results.append(VideoResult(title=clean_title, url=f"https://www.youtube.com/watch?v={vid}"))
        if len(results) >= limit:
            break
    return results


def make_feature_queries(features: list[str]) -> list[str]:
    queries: list[str] = []
    for feature in features:
        queries.append(f"minecraft {feature} mod tutorial")
        queries.append(f"minecraft {feature} automation guide")
        queries.append(f"minecraft {feature} build tutorial")
    return queries
