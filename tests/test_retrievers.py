"""
Tests for the Retrieval Engine (Layer 3).
All external API calls are mocked — no real network requests.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from app.services.retrieval.wikipedia_retriever import WikipediaRetriever
from app.services.retrieval.serp_retriever import SerpAPIRetriever
from app.services.retrieval.source_router import SourceRouter
from app.services.retrieval.evidence_aggregator import EvidenceAggregator


# ── 3A: Wikipedia Retriever Tests ──────────────────────────────────

class TestWikipediaRetriever:
    """Tests for WikipediaRetriever with mocked wikipedia-api."""

    @patch("app.services.retrieval.wikipedia_retriever.wikipediaapi.Wikipedia")
    def test_successful_search(self, mock_wiki_cls):
        mock_page = MagicMock()
        mock_page.exists.return_value = True
        mock_page.title = "Paris"
        mock_page.summary = "Paris is the capital of France.\nIt is located along the Seine River."
        mock_page.fullurl = "https://en.wikipedia.org/wiki/Paris"

        mock_wiki = MagicMock()
        mock_wiki.page.return_value = mock_page
        mock_wiki_cls.return_value = mock_wiki

        retriever = WikipediaRetriever()
        result = retriever.search("Paris")

        assert result["found"] is True
        assert result["title"] == "Paris"
        assert "Paris" in result["content"]
        assert result["url"] == "https://en.wikipedia.org/wiki/Paris"
        assert result["relevance_score"] > 0

    @patch("app.services.retrieval.wikipedia_retriever.wikipediaapi.Wikipedia")
    def test_page_not_found(self, mock_wiki_cls):
        mock_page = MagicMock()
        mock_page.exists.return_value = False

        mock_wiki = MagicMock()
        mock_wiki.page.return_value = mock_page
        mock_wiki_cls.return_value = mock_wiki

        retriever = WikipediaRetriever()
        result = retriever.search("xyznonexistentpage123")

        assert result["found"] is False
        assert result["content"] is None

    @patch("app.services.retrieval.wikipedia_retriever.wikipediaapi.Wikipedia")
    def test_api_error_handled(self, mock_wiki_cls):
        mock_wiki = MagicMock()
        mock_wiki.page.side_effect = Exception("Network error")
        mock_wiki_cls.return_value = mock_wiki

        retriever = WikipediaRetriever()
        result = retriever.search("Paris")

        assert result["found"] is False

    @patch("app.services.retrieval.wikipedia_retriever.wikipediaapi.Wikipedia")
    def test_get_evidence_returns_content(self, mock_wiki_cls):
        mock_page = MagicMock()
        mock_page.exists.return_value = True
        mock_page.title = "Paris"
        mock_page.summary = "Paris is the capital of France."
        mock_page.fullurl = "https://en.wikipedia.org/wiki/Paris"

        mock_wiki = MagicMock()
        mock_wiki.page.return_value = mock_page
        mock_wiki_cls.return_value = mock_wiki

        retriever = WikipediaRetriever()
        evidence = retriever.get_evidence("Paris capital France")

        assert evidence is not None
        assert "Paris" in evidence

    @patch("app.services.retrieval.wikipedia_retriever.wikipediaapi.Wikipedia")
    def test_get_evidence_returns_none_when_not_found(self, mock_wiki_cls):
        mock_page = MagicMock()
        mock_page.exists.return_value = False

        mock_wiki = MagicMock()
        mock_wiki.page.return_value = mock_page
        mock_wiki_cls.return_value = mock_wiki

        retriever = WikipediaRetriever()
        evidence = retriever.get_evidence("nonexistent claim")

        assert evidence is None


# ── 3B: SerpAPI Retriever Tests ────────────────────────────────────

class TestSerpAPIRetriever:
    """Tests for SerpAPIRetriever with mocked serpapi."""

    @patch("app.services.retrieval.serp_retriever.get_settings")
    def test_no_api_key_skips(self, mock_settings):
        mock_settings.return_value = MagicMock(serpapi_key="")
        retriever = SerpAPIRetriever()
        result = retriever.search("test query")

        assert result["found"] is False
        assert result["results"] == []

    @patch("app.services.retrieval.serp_retriever.get_settings")
    def test_placeholder_api_key_skips(self, mock_settings):
        mock_settings.return_value = MagicMock(serpapi_key="your_serpapi_key_here")
        retriever = SerpAPIRetriever()
        result = retriever.search("test query")

        assert result["found"] is False

    @patch("app.services.retrieval.serp_retriever.get_settings")
    def test_get_evidence_no_key(self, mock_settings):
        mock_settings.return_value = MagicMock(serpapi_key="")
        retriever = SerpAPIRetriever()
        evidence = retriever.get_evidence("some claim")

        assert evidence is None


# ── 3C: Source Router Tests ────────────────────────────────────────

class TestSourceRouter:
    """Tests for SourceRouter routing logic."""

    def test_encyclopedic_routes_to_wikipedia(self):
        router = SourceRouter()
        sources = router.get_sources_for_query_type("encyclopedic")
        assert sources == ["wikipedia"]

    def test_recent_event_routes_to_both(self):
        router = SourceRouter()
        sources = router.get_sources_for_query_type("recent_event")
        assert "serpapi" in sources
        assert "wikipedia" in sources

    def test_numeric_routes_to_both(self):
        router = SourceRouter()
        sources = router.get_sources_for_query_type("numeric_statistical")
        assert "wikipedia" in sources
        assert "serpapi" in sources

    def test_opinion_skips_retrieval(self):
        router = SourceRouter()
        sources = router.get_sources_for_query_type("opinion_subjective")
        assert sources == []

    def test_retrieve_evidence_no_claims(self):
        router = SourceRouter()
        result = router.retrieve_evidence([], "encyclopedic")
        assert result == {}

    def test_retrieve_evidence_opinion_returns_empty(self):
        router = SourceRouter()
        result = router.retrieve_evidence(["some claim"], "opinion_subjective")
        assert result == {}

    @patch.object(WikipediaRetriever, "get_evidence", return_value="Paris is the capital of France.")
    def test_retrieve_evidence_wikipedia_success(self, mock_wiki):
        router = SourceRouter()
        result = router.retrieve_evidence(["Paris capital"], "encyclopedic")

        assert "Wikipedia" in result
        assert "Paris" in result["Wikipedia"]

    @patch.object(WikipediaRetriever, "get_evidence", side_effect=Exception("API down"))
    def test_retrieve_evidence_handles_failure(self, mock_wiki):
        """When a retriever fails, it should not crash the whole pipeline."""
        router = SourceRouter()
        result = router.retrieve_evidence(["some claim"], "encyclopedic")

        # Should return empty, not crash
        assert isinstance(result, dict)


# ── 3D: Evidence Aggregator Tests ──────────────────────────────────

class TestEvidenceAggregator:
    """Tests for EvidenceAggregator."""

    def test_deduplicate_exact(self):
        agg = EvidenceAggregator()
        evidence = ["Fact A", "Fact B", "Fact A", "Fact C"]
        result = agg.deduplicate(evidence)
        assert len(result) == 3
        assert "Fact A" in result

    def test_deduplicate_substring(self):
        agg = EvidenceAggregator()
        evidence = [
            "Paris is the capital of France and its largest city.",
            "Paris is the capital of France.",
        ]
        result = agg.deduplicate(evidence)
        # The shorter one is contained in the longer one, so drop the shorter
        assert len(result) == 1
        assert "largest city" in result[0]

    def test_deduplicate_empty(self):
        agg = EvidenceAggregator()
        assert agg.deduplicate([]) == []

    def test_rank_evidence_prefers_medium_length(self):
        agg = EvidenceAggregator()
        short = "Short."
        medium = "This is a medium-length evidence snippet with some factual content about 42 things."
        long = "x" * 1200
        result = agg.rank_evidence([short, long, medium])
        # Medium should come first
        assert result[0] == medium

    def test_rank_evidence_penalizes_boilerplate(self):
        agg = EvidenceAggregator()
        good = "Paris has a population of over 2 million people."
        bad = "Click here to read more about our privacy policy and subscribe."
        result = agg.rank_evidence([bad, good])
        assert result[0] == good

    def test_trim_within_budget(self):
        agg = EvidenceAggregator()
        short_text = "This is short evidence."
        result = agg.trim_to_budget(short_text)
        assert result == short_text

    def test_trim_exceeds_budget(self):
        agg = EvidenceAggregator()
        # 800 tokens * 4 chars = 3200 chars max
        long_text = "This is a sentence. " * 200  # ~4000 chars
        result = agg.trim_to_budget(long_text)
        assert len(result) <= 3200

    def test_aggregate_full_pipeline(self):
        agg = EvidenceAggregator()
        evidence = [
            "Paris is the capital of France.",
            "Paris is the capital of France.",  # duplicate
            "It has a population of over 2 million.",
        ]
        result = agg.aggregate(evidence)
        assert "Paris" in result
        assert len(result) > 0

    def test_aggregate_empty(self):
        agg = EvidenceAggregator()
        assert agg.aggregate([]) == ""
