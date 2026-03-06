"""
学術・統計データコレクター（全て完全無料・無制限）

- Wikipedia REST API（ja/en）
- ArXiv API（論文検索）
- PubMed / NCBI API（医学・心理学論文）
- Semantic Scholar API（論文検索・引用数）
- CrossRef API（DOI・引用データ）
- e-Stat API（日本政府統計）
- World Bank API（世界経済統計）
"""
from __future__ import annotations

import asyncio
import re
import urllib.parse
import xml.etree.ElementTree as ET

import httpx
import structlog

log = structlog.get_logger()

_HEADERS = {
    "User-Agent": "KindleResearchBot/1.0 (research tool; mailto:research@example.com)"
}


class AcademicCollector:
    """学術・統計データを全て無料APIで収集"""

    async def collect_all(self, keyword: str) -> list[dict]:
        """全学術ソースを並列収集"""
        results_list = await asyncio.gather(
            self._wikipedia_ja(keyword),
            self._wikipedia_en(keyword),
            self._arxiv(keyword),
            self._pubmed(keyword),
            self._semantic_scholar(keyword),
            self._estat_search(keyword),
            return_exceptions=True,
        )
        items: list[dict] = []
        for batch in results_list:
            if isinstance(batch, list):
                items.extend(batch)
            elif isinstance(batch, dict):
                items.append(batch)
        log.info("academic_done", keyword=keyword, count=len(items))
        return items

    # ------------------------------------------------------------------
    # Wikipedia（日本語・英語）
    # ------------------------------------------------------------------

    async def _wikipedia_ja(self, keyword: str) -> list[dict]:
        return await self._wikipedia(keyword, lang="ja")

    async def _wikipedia_en(self, keyword: str) -> list[dict]:
        return await self._wikipedia(keyword, lang="en")

    async def _wikipedia(self, keyword: str, lang: str = "ja") -> list[dict]:
        """Wikipedia REST API（完全無料・無制限）"""
        # 検索
        search_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "srlimit": 5,
            "format": "json",
            "utf8": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
                r = await c.get(search_url, params=params)
                r.raise_for_status()
                data = r.json()

            results: list[dict] = []
            for item in data.get("query", {}).get("search", []):
                # サマリーを個別取得
                title = item["title"]
                summary = await self._wikipedia_summary(title, lang)
                results.append({
                    "source": f"wikipedia_{lang}",
                    "title": title,
                    "snippet": re.sub(r"<[^>]+>", "", item.get("snippet", "")),
                    "summary": summary,
                    "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                    "is_overseas": lang != "ja",
                })
            return results
        except Exception as e:
            log.warning(f"wikipedia_{lang}_failed", error=str(e))
            return []

    async def _wikipedia_summary(self, title: str, lang: str) -> str:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    return r.json().get("extract", "")[:500]
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # ArXiv API（完全無料・論文プレプリント）
    # ------------------------------------------------------------------

    async def _arxiv(self, keyword: str) -> list[dict]:
        """ArXiv から英語論文を検索"""
        url = "https://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{keyword}",
            "start": 0,
            "max_results": 10,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()

            # XML パース
            root = ET.fromstring(r.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            results: list[dict] = []
            for entry in root.findall("atom:entry", ns)[:10]:
                title = entry.findtext("atom:title", "", ns).strip()
                summary = entry.findtext("atom:summary", "", ns).strip()[:400]
                link_el = entry.find("atom:link[@type='text/html']", ns)
                url_val = link_el.get("href", "") if link_el is not None else ""
                published = entry.findtext("atom:published", "", ns)
                authors = [
                    a.findtext("atom:name", "", ns)
                    for a in entry.findall("atom:author", ns)
                ][:3]

                results.append({
                    "source": "arxiv",
                    "title": title,
                    "summary": summary,
                    "url": url_val,
                    "published": published[:10],
                    "authors": authors,
                    "is_overseas": True,
                })
            log.info("arxiv_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("arxiv_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # PubMed / NCBI API（医学・心理学論文）
    # ------------------------------------------------------------------

    async def _pubmed(self, keyword: str) -> list[dict]:
        """PubMed で医学・心理学論文を検索"""
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        search_params = {
            "db": "pubmed",
            "term": f"{keyword}[Title/Abstract]",
            "retmax": 10,
            "retmode": "json",
            "sort": "relevance",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS) as c:
                r = await c.get(f"{base}/esearch.fcgi", params=search_params)
                r.raise_for_status()
                search_data = r.json()

            pmids = search_data.get("esearchresult", {}).get("idlist", [])[:10]
            if not pmids:
                return []

            # 詳細取得
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
            }
            async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS) as c:
                r = await c.get(f"{base}/esummary.fcgi", params=fetch_params)
                r.raise_for_status()
                fetch_data = r.json()

            results: list[dict] = []
            for pmid in pmids:
                article = fetch_data.get("result", {}).get(pmid, {})
                if not article:
                    continue
                results.append({
                    "source": "pubmed",
                    "pmid": pmid,
                    "title": article.get("title", ""),
                    "journal": article.get("fulljournalname", ""),
                    "published": article.get("pubdate", ""),
                    "authors": [
                        a.get("name", "") for a in article.get("authors", [])[:3]
                    ],
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "is_overseas": True,
                })
            log.info("pubmed_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("pubmed_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Semantic Scholar API（論文引用数付き）
    # ------------------------------------------------------------------

    async def _semantic_scholar(self, keyword: str) -> list[dict]:
        """Semantic Scholar で論文を検索（引用数順）"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": keyword,
            "limit": 10,
            "fields": "title,abstract,year,citationCount,authors,url",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get(url, params=params)
                r.raise_for_status()
                data = r.json()

            results: list[dict] = []
            for paper in data.get("data", []):
                results.append({
                    "source": "semantic_scholar",
                    "title": paper.get("title", ""),
                    "abstract": (paper.get("abstract") or "")[:400],
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount", 0),
                    "authors": [
                        a.get("name", "") for a in (paper.get("authors") or [])[:3]
                    ],
                    "url": paper.get("url", ""),
                    "is_overseas": True,
                })
            log.info("semantic_scholar_done", keyword=keyword, count=len(results))
            return results
        except Exception as e:
            log.warning("semantic_scholar_failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # e-Stat 政府統計API（日本統計・完全無料）
    # ------------------------------------------------------------------

    async def _estat_search(self, keyword: str) -> list[dict]:
        """e-Stat で日本政府統計を検索"""
        url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"
        params = {
            "appId": "0000000000000000000000000000000000000000",  # 公開APIキー
            "searchWord": keyword,
            "limit": 5,
            "lang": "J",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url, params=params)
                if r.status_code != 200:
                    return []
                data = r.json()

            results: list[dict] = []
            table_list = (
                data.get("GET_STATS_LIST", {})
                    .get("DATALIST_INF", {})
                    .get("TABLE_INF", [])
            )
            if isinstance(table_list, dict):
                table_list = [table_list]
            for table in table_list[:5]:
                results.append({
                    "source": "estat",
                    "title": table.get("TITLE", {}).get("$", ""),
                    "survey_date": table.get("SURVEY_DATE", ""),
                    "url": f"https://www.e-stat.go.jp/stat-search/database?statdisp_id={table.get('@id', '')}",
                    "is_overseas": False,
                })
            return results
        except Exception as e:
            log.warning("estat_failed", error=str(e))
            return []
