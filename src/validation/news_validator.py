from __future__ import annotations

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from ..models import OutbreakReport, NewsValidation


NEWS_SOURCES = [
    "Reuters health",
    "AP news disease outbreak",
    "BBC health epidemic",
    "CIDRAP outbreak",
    "ProMED mail",
    "WHO disease outbreak news",
    "Eurosurveillance",
    "MMWR CDC",
]


class NewsValidator:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "GlobalEpidemicTracker/1.0"})

    def validate_outbreak(self, outbreak: OutbreakReport) -> NewsValidation:
        query = self._build_query(outbreak)
        articles = self._search_news(query)
        validation = NewsValidation(
            outbreak_id=outbreak.outbreak_id,
            query=query,
            articles_found=len(articles),
            sources_matched=[a.get("source", "") for a in articles],
        )

        if len(articles) >= 2:
            validation.consistent = True
            validation.summary = self._summarize_findings(articles, outbreak)
            extra = self._extract_extra_data(articles)
            if extra.get("cases"):
                validation.additional_cases = extra["cases"]
            if extra.get("deaths"):
                validation.additional_deaths = extra["deaths"]
        elif len(articles) == 1:
            validation.consistent = True
            validation.summary = f"Single source confirmation: {articles[0].get('title', '')[:100]}"
        else:
            validation.consistent = False
            validation.summary = "No independent news sources found to verify this outbreak."

        return validation

    def validate_batch(self, outbreaks: list[OutbreakReport], max_validations: int = 20) -> dict[str, NewsValidation]:
        results = {}
        priority = sorted(outbreaks, key=lambda o: (-o.cases, -o.deaths))[:max_validations]
        for outbreak in priority:
            try:
                results[outbreak.outbreak_id] = self.validate_outbreak(outbreak)
            except Exception:
                results[outbreak.outbreak_id] = NewsValidation(
                    outbreak_id=outbreak.outbreak_id,
                    query="",
                    summary="Validation failed due to network error.",
                )
        return results

    def _build_query(self, outbreak: OutbreakReport) -> str:
        parts = [outbreak.disease, outbreak.location]
        if outbreak.date_reported.year >= 2024:
            parts.append(str(outbreak.date_reported.year))
        return " ".join(parts)

    def _search_news(self, query: str) -> list[dict]:
        articles = []
        try:
            articles.extend(self._search_bing_news(query))
        except Exception:
            pass
        try:
            articles.extend(self._search_google_news(query))
        except Exception:
            pass
        try:
            articles.extend(self._search_reddit(query))
        except Exception:
            pass
        return self._deduplicate(articles)

    def _search_bing_news(self, query: str) -> list[dict]:
        url = "https://www.bing.com/news/search"
        params = {"q": query, "format": "rss", "count": 10}
        resp = self._session.get(url, params=params, timeout=15)
        articles = []
        items = re.findall(r"<item>(.*?)</item>", resp.text, re.DOTALL)
        for item in items[:5]:
            title = re.search(r"<title>(.*?)</title>", item)
            link = re.search(r"<link>(.*?)</link>", item)
            desc = re.search(r"<description>(.*?)</description>", item, re.DOTALL)
            pub = re.search(r"<pubDate>(.*?)</pubDate>", item)
            articles.append({
                "title": title.group(1) if title else "",
                "url": link.group(1) if link else "",
                "description": re.sub(r"<[^>]+>", "", desc.group(1)) if desc else "",
                "published": pub.group(1) if pub else "",
                "source": "Bing News",
            })
        return articles

    def _search_google_news(self, query: str) -> list[dict]:
        url = "https://news.google.com/rss/search"
        params = {"q": query, "hl": "en", "gl": "US", "ceid": "US:en"}
        resp = self._session.get(url, params=params, timeout=15)
        articles = []
        items = re.findall(r"<item>(.*?)</item>", resp.text, re.DOTALL)
        for item in items[:5]:
            title = re.search(r"<title>(.*?)</title>", item)
            link = re.search(r"<link>(.*?)</link>", item)
            pub = re.search(r"<pubDate>(.*?)</pubDate>", item)
            source = re.search(r"<source.*?>(.*?)</source>", item)
            articles.append({
                "title": title.group(1) if title else "",
                "url": link.group(1) if link else "",
                "published": pub.group(1) if pub else "",
                "source": source.group(1) if source else "Google News",
            })
        return articles

    def _search_reddit(self, query: str) -> list[dict]:
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "sort": "new", "limit": 5, "t": "week"}
        headers = {"User-Agent": "GlobalEpidemicTracker/1.0"}
        resp = self._session.get(url, params=params, headers=headers, timeout=15)
        articles = []
        if resp.status_code == 200:
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                d = post.get("data", {})
                articles.append({
                    "title": d.get("title", ""),
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                    "source": f"r/{d.get('subreddit', 'unknown')}",
                    "score": d.get("score", 0),
                })
        return articles

    def _deduplicate(self, articles: list[dict]) -> list[dict]:
        seen_titles = set()
        unique = []
        for a in articles:
            title_key = re.sub(r"[^a-z0-9]", "", a.get("title", "").lower())[:50]
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(a)
        return unique

    def _summarize_findings(self, articles: list[dict], outbreak: OutbreakReport) -> str:
        sources = set()
        for a in articles:
            src = a.get("source", "Unknown")
            sources.add(src)

        case_mentions = []
        for a in articles:
            text = f"{a.get('title', '')} {a.get('description', '')}"
            m = re.search(r"(\d[\d,]*)\s*(?:cases?|infections?|people\s+infected)", text, re.I)
            if m:
                case_mentions.append(int(m.group(1).replace(",", "")))

        summary_parts = [
            f"Verified by {len(articles)} source(s): {', '.join(list(sources)[:3])}.",
        ]
        if case_mentions:
            avg_cases = sum(case_mentions) // len(case_mentions)
            summary_parts.append(f"News reports mention ~{avg_cases} cases.")
        if outbreak.cases > 0:
            summary_parts.append(f"WHO reports {outbreak.cases} cases, {outbreak.deaths} deaths.")

        return " ".join(summary_parts)

    def _extract_extra_data(self, articles: list[dict]) -> dict:
        total_cases = None
        total_deaths = None
        for a in articles:
            text = f"{a.get('title', '')} {a.get('description', '')}"
            m = re.search(r"(\d[\d,]*)\s*(?:confirmed\s*)?cases?", text, re.I)
            if m:
                total_cases = int(m.group(1).replace(",", ""))
            m = re.search(r"(\d[\d,]*)\s*death", text, re.I)
            if m:
                total_deaths = int(m.group(1).replace(",", ""))
        return {"cases": total_cases, "deaths": total_deaths}
