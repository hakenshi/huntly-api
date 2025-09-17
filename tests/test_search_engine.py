"""
Unit tests for SearchEngine core functionality
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.search.engine import SearchEngine, QueryProcessor, RankingAlgorithm
from src.models.search import SearchQuery, SearchFilters, SearchUserPreferences
from src.search.models import SearchResult, IndexedLead
from src.database.models import Lead as LeadModel
from src.cache.manager import CacheManager


class TestQueryProcessor:
    """Test QueryProcessor functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.processor = QueryProcessor()
    
    def test_parse_simple_query(self):
        """Test parsing simple text query"""
        result = self.processor.parse_query("technology startup")
        
        assert "technology" in result["terms"]
        assert "startup" in result["terms"]
        assert result["phrases"] == []
        assert result["original_query"] == "technology startup"
    
    def test_parse_quoted_phrases(self):
        """Test parsing queries with quoted phrases"""
        result = self.processor.parse_query('software "machine learning" company')
        
        assert "software" in result["terms"]
        assert "company" in result["terms"]
        assert "machine learning" in result["phrases"]
    
    def test_parse_implicit_filters(self):
        """Test extraction of implicit filters"""
        result = self.processor.parse_query("tech startup in São Paulo")
        
        assert result["filters"].get("industry") == "Tecnologia"
        assert result["filters"].get("location") == "São Paulo"
    
    def test_parse_empty_query(self):
        """Test parsing empty or None query"""
        result = self.processor.parse_query("")
        assert result["terms"] == []
        assert result["phrases"] == []
        
        result = self.processor.parse_query(None)
        assert result["terms"] == []
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        cleaned = self.processor._clean_text("Tech-Company! @#$")
        assert cleaned == "tech-company"
        
        cleaned = self.processor._clean_text("  Multiple   Spaces  ")
        assert cleaned == "multiple spaces"
    
    def test_extract_terms(self):
        """Test term extraction with stop words filtering"""
        terms = self.processor._extract_terms("the technology company and software")
        
        assert "technology" in terms
        assert "company" in terms
        assert "software" in terms
        assert "the" not in terms  # Stop word
        assert "and" not in terms  # Stop word


class TestRankingAlgorithm:
    """Test RankingAlgorithm functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.user_prefs = SearchUserPreferences(
            preferred_industries=["Tecnologia"],
            preferred_locations=["São Paulo"],
            scoring_weights={
                "text_relevance": 0.4,
                "industry_match": 0.3,
                "location_proximity": 0.2,
                "company_size": 0.05,
                "data_quality": 0.03,
                "freshness": 0.02
            }
        )
        self.ranker = RankingAlgorithm(self.user_prefs)
    
    def create_mock_lead(self, **kwargs):
        """Create a mock lead for testing"""
        defaults = {
            "id": 1,
            "company": "Test Company",
            "contact": "Test Contact",
            "email": "test@example.com",
            "phone": "123456789",
            "industry": "Tecnologia",
            "location": "São Paulo",
            "description": "Test description",
            "created_at": datetime.now(timezone.utc)
        }
        defaults.update(kwargs)
        
        mock_lead = Mock(spec=LeadModel)
        for key, value in defaults.items():
            setattr(mock_lead, key, value)
        
        return mock_lead
    
    def test_calculate_text_score(self):
        """Test text relevance scoring"""
        lead = self.create_mock_lead(
            company="TechInova Solutions",
            description="Software development company"
        )
        
        parsed_query = {
            "terms": ["software", "tech"],
            "phrases": ["software development"]
        }
        
        score, reasons = self.ranker._calculate_text_score(lead, parsed_query)
        
        assert score > 0
        assert any("software" in reason.lower() for reason in reasons)
        assert any("tech" in reason.lower() for reason in reasons)
    
    def test_calculate_industry_score(self):
        """Test industry match scoring"""
        lead = self.create_mock_lead(industry="Tecnologia")
        filters = SearchFilters(industry="Tecnologia")
        
        score, reasons = self.ranker._calculate_industry_score(lead, filters)
        
        assert score == 1.0  # Exact match
        assert len(reasons) > 0
        assert "exact industry match" in reasons[0].lower()
    
    def test_calculate_location_score(self):
        """Test location proximity scoring"""
        lead = self.create_mock_lead(location="São Paulo, SP")
        filters = SearchFilters(location="São Paulo")
        
        score, reasons = self.ranker._calculate_location_score(lead, filters)
        
        assert score > 0
        assert len(reasons) > 0
    
    def test_calculate_quality_score(self):
        """Test data quality scoring"""
        # High quality lead (all fields filled)
        high_quality_lead = self.create_mock_lead(
            company="Test Company",
            contact="John Doe",
            email="john@test.com",
            phone="123456789",
            industry="Tech",
            location="São Paulo",
            description="Complete description"
        )
        
        score, reasons = self.ranker._calculate_quality_score(high_quality_lead)
        assert score > 0.8
        
        # Low quality lead (few fields filled)
        low_quality_lead = self.create_mock_lead(
            company="Test",
            contact=None,
            email=None,
            phone=None,
            industry=None,
            location=None,
            description=None
        )
        
        score, reasons = self.ranker._calculate_quality_score(low_quality_lead)
        assert score < 0.5
    
    def test_calculate_freshness_score(self):
        """Test freshness scoring"""
        # Recent lead
        recent_lead = self.create_mock_lead(created_at=datetime.now(timezone.utc))
        score, reasons = self.ranker._calculate_freshness_score(recent_lead)
        assert score == 1.0
        
        # Old lead
        from datetime import timedelta
        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        old_lead = self.create_mock_lead(created_at=old_date)
        score, reasons = self.ranker._calculate_freshness_score(old_lead)
        assert score < 1.0
    
    def test_full_relevance_calculation(self):
        """Test complete relevance score calculation"""
        lead = self.create_mock_lead(
            company="TechInova Solutions",
            industry="Tecnologia",
            location="São Paulo",
            description="Software development company"
        )
        
        parsed_query = {
            "terms": ["software", "tech"],
            "phrases": []
        }
        
        filters = SearchFilters(industry="Tecnologia")
        
        score, reasons = self.ranker.calculate_relevance_score(lead, parsed_query, filters)
        
        assert 0 <= score <= 1.0
        assert len(reasons) > 0
        assert isinstance(reasons, list)


class TestSearchEngine:
    """Test SearchEngine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock(spec=Session)
        self.mock_cache = Mock(spec=CacheManager)
        self.search_engine = SearchEngine(self.mock_db, self.mock_cache)
    
    def create_mock_lead(self, **kwargs):
        """Create a mock lead for testing"""
        defaults = {
            "id": 1,
            "company": "Test Company",
            "contact": "Test Contact",
            "email": "test@example.com",
            "phone": "123456789",
            "website": None,
            "industry": "Tecnologia",
            "location": "São Paulo",
            "revenue": None,
            "employees": None,
            "description": "Test description",
            "keywords": None,
            "created_at": datetime.now(timezone.utc),
            "indexed_at": datetime.now(timezone.utc)
        }
        defaults.update(kwargs)
        
        mock_lead = Mock(spec=LeadModel)
        for key, value in defaults.items():
            setattr(mock_lead, key, value)
        
        return mock_lead
    
    def test_merge_filters(self):
        """Test filter merging functionality"""
        explicit_filters = SearchFilters(industry="Tecnologia")
        implicit_filters = {"location": "São Paulo", "industry": "E-commerce"}
        
        merged = self.search_engine._merge_filters(explicit_filters, implicit_filters)
        
        # Explicit should take precedence
        assert merged.industry == "Tecnologia"
        # Implicit should be added if not explicit
        assert merged.location == "São Paulo"
    
    def test_convert_to_indexed_lead(self):
        """Test conversion from LeadModel to IndexedLead"""
        mock_lead = self.create_mock_lead()
        
        # Mock cache data
        self.mock_cache.get_cached_lead_data.return_value = {
            "keywords": ["tech", "software"],
            "searchable_text": "test searchable text",
            "company_tokens": ["test", "company"],
            "industry_tokens": ["tecnologia"],
            "location_tokens": ["são", "paulo"]
        }
        
        indexed_lead = self.search_engine._convert_to_indexed_lead(mock_lead)
        
        assert isinstance(indexed_lead, IndexedLead)
        assert indexed_lead.id == mock_lead.id
        assert indexed_lead.company == mock_lead.company
        assert indexed_lead.keywords == ["tech", "software"]
    
    def test_generate_highlights(self):
        """Test search result highlighting"""
        mock_lead = self.create_mock_lead(
            company="TechInova Solutions",
            description="Software development company"
        )
        
        parsed_query = {
            "terms": ["tech", "software"],
            "phrases": []
        }
        
        highlights = self.search_engine._generate_highlights(mock_lead, parsed_query)
        
        assert "company" in highlights or "description" in highlights
        if "company" in highlights:
            assert "<mark>" in highlights["company"]
    
    @patch('src.search.engine.time.time')
    def test_search_leads_cache_hit(self, mock_time):
        """Test search with cache hit"""
        mock_time.return_value = 1000.0
        
        # Mock cache hit
        cached_results = {
            "results": [
                {
                    "lead": {
                        "id": 1,
                        "company": "Test Company",
                        "contact": "Test Contact",
                        "email": "test@example.com",
                        "phone": None,
                        "website": None,
                        "industry": "Tech",
                        "location": "São Paulo",
                        "revenue": None,
                        "employees": None,
                        "description": "Test",
                        "keywords": [],
                        "searchable_text": "",
                        "indexed_at": None,
                        "industry_tokens": [],
                        "location_tokens": [],
                        "company_tokens": []
                    },
                    "relevance_score": 0.8,
                    "match_reasons": ["test reason"],
                    "highlighted_fields": {}
                }
            ]
        }
        
        self.mock_cache.get_cached_search_results.return_value = cached_results
        
        query = SearchQuery(text="test query")
        results = self.search_engine.search_leads(query)
        
        assert len(results) == 1
        assert results[0].relevance_score == 0.8
        self.mock_cache.get_cached_search_results.assert_called_once()
    
    def test_search_leads_cache_miss(self):
        """Test search with cache miss"""
        # Mock cache miss
        self.mock_cache.get_cached_search_results.return_value = None
        
        # Mock database query
        mock_lead = self.create_mock_lead()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_lead]
        self.mock_db.query.return_value = mock_query
        
        # Mock indexer search (no Redis results)
        self.search_engine.indexer.search_leads_by_tokens = Mock(return_value=[])
        
        # Mock cache operations
        self.mock_cache.get_cached_lead_data.return_value = None
        self.mock_cache.cache_search_results.return_value = True
        self.mock_cache.add_popular_search.return_value = True
        
        query = SearchQuery(text="test query", limit=10)
        results = self.search_engine.search_leads(query)
        
        # Should have processed the query and returned results
        assert isinstance(results, list)
        self.mock_cache.cache_search_results.assert_called_once()
    
    def test_get_search_suggestions(self):
        """Test search suggestions functionality"""
        # Mock cache miss for suggestions
        self.mock_cache.get_cached_suggestions.return_value = None
        
        # Mock popular searches
        self.mock_cache.get_popular_searches.return_value = ["technology", "tech startup"]
        
        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [("TechCorp",), ("TechInova",)]
        self.mock_db.query.return_value = mock_query
        
        # Mock cache operations
        self.mock_cache.cache_suggestions.return_value = True
        
        suggestions = self.search_engine.get_search_suggestions("tech", limit=5)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
        self.mock_cache.cache_suggestions.assert_called_once()
    
    def test_get_search_stats(self):
        """Test search statistics functionality"""
        # Mock indexer status
        self.search_engine.indexer.get_indexing_status = Mock(return_value={
            "total_leads": 100,
            "indexed_leads": 95,
            "indexing_coverage": 95.0
        })
        
        # Mock cache operations
        self.mock_cache.get_popular_searches.return_value = ["tech", "startup"]
        self.mock_cache.health_check.return_value = {"status": "healthy"}
        
        stats = self.search_engine.get_search_stats()
        
        assert "indexing_status" in stats
        assert "popular_searches" in stats
        assert "cache_health" in stats
        assert "last_updated" in stats
    
    def test_invalidate_search_cache(self):
        """Test cache invalidation"""
        self.mock_cache.invalidate_search_cache.return_value = 10  # 10 keys invalidated
        
        result = self.search_engine.invalidate_search_cache()
        
        assert result is True
        self.mock_cache.invalidate_search_cache.assert_called_once()


# Integration test fixtures
@pytest.fixture
def sample_leads():
    """Sample leads for testing"""
    return [
        {
            "id": 1,
            "company": "TechInova Solutions",
            "contact": "Carlos Silva",
            "email": "carlos@techinova.com.br",
            "industry": "Tecnologia",
            "location": "São Paulo, SP",
            "description": "Software development and SaaS solutions"
        },
        {
            "id": 2,
            "company": "EcoCommerce Brasil",
            "contact": "Ana Santos", 
            "email": "ana@ecocommerce.com.br",
            "industry": "E-commerce",
            "location": "Rio de Janeiro, RJ",
            "description": "Sustainable e-commerce platform"
        }
    ]


class TestSearchEngineIntegration:
    """Integration tests for SearchEngine"""
    
    def test_end_to_end_search_flow(self, sample_leads):
        """Test complete search flow from query to results"""
        # This would require actual database and Redis setup
        # For now, we'll test the flow with mocks
        
        mock_db = Mock(spec=Session)
        mock_cache = Mock(spec=CacheManager)
        search_engine = SearchEngine(mock_db, mock_cache)
        
        # Mock the entire flow
        mock_cache.get_cached_search_results.return_value = None
        search_engine.indexer.search_leads_by_tokens = Mock(return_value=[])
        
        # Mock database query results
        mock_leads = []
        for lead_data in sample_leads:
            mock_lead = Mock(spec=LeadModel)
            for key, value in lead_data.items():
                setattr(mock_lead, key, value)
            setattr(mock_lead, "created_at", datetime.now(timezone.utc))
            setattr(mock_lead, "indexed_at", datetime.now(timezone.utc))
            mock_leads.append(mock_lead)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_leads
        mock_db.query.return_value = mock_query
        
        # Mock cache operations
        mock_cache.get_cached_lead_data.return_value = None
        mock_cache.cache_search_results.return_value = True
        mock_cache.add_popular_search.return_value = True
        
        # Execute search
        query = SearchQuery(text="technology software", limit=10)
        results = search_engine.search_leads(query)
        
        # Verify results
        assert isinstance(results, list)
        # Results should be ranked by relevance
        if len(results) > 1:
            assert results[0].relevance_score >= results[1].relevance_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])