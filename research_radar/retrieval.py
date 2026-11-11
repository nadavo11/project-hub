"""Bounded public scholarly retrieval with content-addressed provenance."""

import hashlib
import html
import json
import re
import time
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .core import now, paper_key
from .archive import Archive


class BudgetExceeded(RuntimeError):
    pass


class Retriever:
    def __init__(self, store, job, checkpoint=lambda: None):
        self.store, self.job, self.checkpoint = store, job, checkpoint
        self.campaign = store.campaign(job["campaign_id"])
        self.config = self.campaign["config"]
        self.cache = store.home / "sources"
        self.cache.mkdir(exist_ok=True)

    def fetch(self, url):
        self.checkpoint()
        costs = self.store.costs(self.job["campaign_id"])
        if costs["http_requests"] >= self.config["max_requests"]:
            raise BudgetExceeded("HTTP request budget exhausted; increase it explicitly before retrying")
        if costs["elapsed_seconds"] >= self.config["time_budget_seconds"]:
            raise BudgetExceeded("Campaign work-time budget exhausted")
        start = time.monotonic()
        data, failure = b"", None
        try:
            request = Request(url, headers={"User-Agent": "ResearchRadar/0.1 (bounded academic research)", "Accept": "application/json, application/atom+xml"})
            with urlopen(request, timeout=20) as response:
                data = response.read(4_000_001)
                media_type = response.headers.get("Content-Type", "application/octet-stream")
            if len(data) > 4_000_000:
                raise ValueError("Source exceeds the four MB metadata limit")
            digest = hashlib.sha256(data).hexdigest()
            accessed_at = now()
            archived = Archive(self.store.home / "archive").store_bytes(
                data, url=url, media_type=media_type, retrieved_at=accessed_at)
            path = self.cache / (digest + ".source")
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Existing retrieval cache was modified; archived original retained")
            if not path.exists():
                path.write_bytes(data)
            return data, {"url": url, "sha256": digest, "accessed_at": accessed_at,
                          "cache": path.name, "archive": archived.to_dict()}
        except Exception as error:
            failure = str(error)
            raise
        finally:
            self.store.event(self.job["campaign_id"], "retrieval",
                             "Public source fetched." if failure is None else "Public source unavailable; no evidence inferred.",
                             {"url": url, "http_requests": 1, "download_bytes": len(data),
                              "elapsed_seconds": time.monotonic() - start, "error": failure}, self.job["id"])
            self.checkpoint()

    @staticmethod
    def clean(value):
        return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()

    @staticmethod
    def keywords(query):
        stop = {
            "a", "an", "the", "of", "for", "to", "and", "or", "in", "on", "with", "by",
            "is", "are", "does", "do", "can", "how", "what", "whether", "than", "from",
            "it", "its", "this", "that", "under", "using", "use", "based", "vs",
            "find", "paper", "papers", "research", "study", "existing", "prior", "art",
        }
        return list(dict.fromkeys(word for word in re.findall(r"[a-z0-9]+", query.lower())
                                  if word not in stop and len(word) > 2))

    @classmethod
    def relevant(cls, paper, query):
        words = cls.keywords(query)
        document = set(cls.keywords(paper.get("title", "") + " " + paper.get("abstract", "")))
        return len(set(words) & document) >= min(2, len(words)) if words else False

    def in_date_range(self, paper):
        lower, upper = self.config.get("date_from"), self.config.get("date_to")
        if not lower and not upper:
            return True
        try:
            published = date.fromisoformat(str(paper.get("date", ""))[:10])
        except ValueError:
            return False
        return (not lower or published >= date.fromisoformat(lower)) and (not upper or published <= date.fromisoformat(upper))

    def openalex(self, query, limit, reference_ids=None):
        parameters = {"search": query, "per-page": limit}
        if reference_ids:
            parameters = {"filter": "openalex:" + "|".join(reference_ids), "per-page": limit}
        url = "https://api.openalex.org/works?" + urlencode(parameters)
        raw, provenance = self.fetch(url)
        results = json.loads(raw)["results"]
        papers = []
        for item in results:
            abstract_index = item.get("abstract_inverted_index") or {}
            words = {pos: word for word, positions in abstract_index.items() for pos in positions}
            abstract = " ".join(words[k] for k in sorted(words))
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            papers.append({
                "id": "p-" + hashlib.sha256(item["id"].encode()).hexdigest()[:12],
                "title": item["title"], "authors": [a["author"]["display_name"] for a in item.get("authorships", [])],
                "year": item.get("publication_year"), "date": item.get("publication_date"),
                "venue": source.get("display_name", ""), "doi": item.get("doi"),
                "url": location.get("landing_page_url") or item.get("doi") or item["id"],
                "abstract": abstract, "verification": "abstract" if abstract else "metadata",
                "family": "unclassified", "task": "unclassified", "query_context": self.campaign["field"], "datasets": [],
                "contribution": "Awaiting paper examination", "mechanism": "Unverified",
                "limitations": "Metadata retrieval does not validate scientific claims",
                "evaluation": "Unverified", "evidence": [], "provenance": [provenance],
                "references": item.get("referenced_works", [])[:5], "relevance": "retrieved, not screened",
            })
        return papers

    def arxiv(self, query, limit):
        expression = " AND ".join(f'all:"{word}"' for word in self.keywords(query)[:8])
        url = "https://export.arxiv.org/api/query?" + urlencode({"search_query": expression, "start": 0, "max_results": limit})
        raw, provenance = self.fetch(url)
        root = ET.fromstring(raw)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("a:entry", ns):
            source = entry.findtext("a:id", "", ns).replace("http://", "https://")
            arxiv_id = source.rsplit("/", 1)[-1]
            date = entry.findtext("a:published", "", ns)
            papers.append({
                "id": "p-" + re.sub(r"\W", "-", arxiv_id), "arxiv_id": arxiv_id,
                "title": " ".join(entry.findtext("a:title", "", ns).split()),
                "authors": [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)],
                "year": int(date[:4]) if date else None, "date": date, "venue": "arXiv",
                "url": source, "abstract": " ".join(entry.findtext("a:summary", "", ns).split()),
                "verification": "abstract", "family": "unclassified", "datasets": [],
                "task": "unclassified", "query_context": self.campaign["field"], "evidence": [], "provenance": [provenance],
                "contribution": "Awaiting paper examination", "mechanism": "Unverified",
                "evaluation": "Unverified", "limitations": "Abstract only; full paper not examined",
                "relevance": "retrieved, not screened",
            })
        return papers

    def crossref(self, query, limit):
        url = "https://api.crossref.org/works?" + urlencode({"query.bibliographic": query, "rows": limit})
        raw, provenance = self.fetch(url)
        papers = []
        for item in json.loads(raw)["message"]["items"]:
            title = (item.get("title") or [""])[0]
            if not title:
                continue
            date = (item.get("published") or {}).get("date-parts", [[]])[0]
            doi = item.get("DOI")
            papers.append({
                "id": "p-" + hashlib.sha256(str(doi or title).encode()).hexdigest()[:12],
                "title": title, "doi": doi, "url": item.get("URL") or "https://doi.org/" + doi,
                "authors": [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in item.get("author", [])],
                "year": date[0] if date else None, "date": "-".join(map(str, date)),
                "venue": (item.get("container-title") or [""])[0],
                "abstract": self.clean(item.get("abstract")), "verification": "abstract" if item.get("abstract") else "metadata",
                "family": "unclassified", "task": "unclassified", "query_context": self.campaign["field"], "datasets": [],
                "contribution": "Awaiting paper examination", "mechanism": "Unverified",
                "evaluation": "Unverified", "limitations": "Metadata only unless an abstract is supplied",
                "evidence": [], "provenance": [provenance], "references": item.get("reference", [])[:5],
                "relevance": "retrieved, not screened",
            })
        return papers

    def search(self, query):
        existing = self.store.records(self.job["campaign_id"], "papers")
        limit = min(10, max(1, self.config["max_papers"] - len(existing)))
        if self.job["role"] == "cartographer":
            reserved = min(6, max(1, self.config["max_papers"] // 3))
            query_count = max(1, len(self.config["queries"]))
            limit = min(limit, max(1, (self.config["max_papers"] - reserved) // query_count))
        elif self.job["role"] == "novelty":
            limit = min(limit, 2)
        failures = []
        excluded = []
        for name, provider in (("openalex", self.openalex), ("arxiv", self.arxiv), ("crossref", self.crossref)):
            try:
                papers = provider(query, limit)
                self.checkpoint()
                irrelevant = [p for p in papers if not self.relevant(p, query) or not self.in_date_range(p)]
                excluded.extend({"title": p["title"], "url": p["url"], "provider": name} for p in irrelevant)
                papers = [p for p in papers if self.relevant(p, query) and self.in_date_range(p)]
                if irrelevant:
                    self.store.event(self.job["campaign_id"], "relevance_screen",
                                     "Discarded keyword-unmatched search results; source existence is not topical relevance.",
                                     {"query": query, "excluded": excluded, "rule": "Query-token overlap plus configured publication-date boundaries; unknown dates excluded when bounded. Not semantic verification or a version-level historical cutoff."},
                                     self.job["id"])
                if not papers:
                    failures.append(name + ": empty results")
                    continue
                if self.config["search_depth"] > 1 and name == "openalex":
                    refs = list(dict.fromkeys(
                        ref.rsplit("/", 1)[-1] for paper in papers for ref in paper.get("references", [])
                        if isinstance(ref, str) and re.fullmatch(r"https://openalex.org/W\d+", ref)
                    ))[:3]
                    if refs:
                        try:
                            papers += [p for p in self.openalex("", min(3, limit), refs) if self.in_date_range(p)]
                        except BudgetExceeded:
                            raise
                        except (OSError, ValueError, KeyError) as error:
                            failures.append(f"reference expansion: {error}")
                stored = []
                skipped = []
                existing_keys = {paper_key(p) for p in existing}
                for paper in papers:
                    if len(existing_keys) >= self.config["max_papers"] and paper_key(paper) not in existing_keys:
                        skipped.append({"title": paper["title"], "url": paper["url"]})
                        continue
                    saved = self.store.put(self.job["campaign_id"], "papers", paper)
                    existing_keys.add(paper_key(saved))
                    stored.append(saved["id"])
                if not stored:
                    raise BudgetExceeded("Paper limit reached; increase max_papers (pilot maximum 25) before adding new literature")
                return {"query": query, "paper_ids": stored, "provider": name, "failures": failures,
                        "excluded_by_paper_budget": skipped,
                        "excluded_by_relevance_screen": excluded,
                        "coverage": "Bounded retrieval, not exhaustive; ranking is provider-defined"}
            except BudgetExceeded:
                raise
            except (OSError, ValueError, KeyError, ET.ParseError) as error:
                failures.append(f"{name}: {error}")
        raise RuntimeError("All public retrieval providers failed or returned no results: " + "; ".join(failures))
