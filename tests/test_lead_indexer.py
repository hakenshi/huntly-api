"""
Tests for Lead Indexer functionality
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from src.search.indexer import LeadIndexer
from src.database.models import Lead as LeadModel
from src.cache.manager import CacheManager

class TestLeadIndexer:
    """Test cases for LeadIndexer class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_cache.enabled = True
        self.indexer = LeadIndexer(self.mock_db, self.mock_cache)
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        # Test basic cleaning
        result = self.indexer._clean_text("Hello World!")
        assert result == "hello world"
        
        # Test special characters removal
        result = self.indexer._clean_text("Tech@Company (2024)")
        assert result == "tech company 2024"
        
        # Test multiple spaces
        result = self.indexer._clean_text("Multiple   Spaces    Here")
        assert result == "multiple spaces here"
        
        # Test empty string
        result = self.indexer._clean_text("")
        assert result == ""
        
        # Test None input
        result = self.indexer._clean_text(None)
        assert result == ""
    
    def test_tokenize_text(self):
        """Test text tokenization"""
        # Test basic tokenization
        result = self.indexer._tokenize_text("hello world technology")
        assert "hello" in result
        assert "world" in result
        assert "technology" in result
        
        # Test stop words removal
        result = self.indexer._tokenize_text("the quick brown fox")
        assert "the" not in result  # Stop word should be removed
        assert "quick" in result
        assert "brown" in result
        
        # Test short words removal
        result = self.indexer._tokenize_text("a big company")
        assert "a" not in result  # Too short
        assert "big" in result
        assert "company" in result
        
        # Test duplicates removal
        result = self.indexer._tokenize_text("tech tech technology")
        assert len([t for t in result if t == "tech"]) == 1
    
    def test_extract_keywords_from_text(self):
        """Test keyword extraction from text"""
        text = "We are a SaaS company using Python and React for web development"
        
        result = self.indexer._extract_keywords_from_text(text)
        
        # Should extract capitalized words and technical terms
        # Convert all to lowercase for comparison
        result_lower = [kw.lower() for kw in result]
        
        # Check that at least some keywords were extracted
        assert len(result) > 0
        
        # Should find Python and React (capitalized words)
        assert any("python" in kw for kw in result_lower)
        assert any("react" in kw for kw in result_lower)
    
    def test_extract_searchable_metadata(self):
        """Test metadata extraction from lead"""
        # Create mock lead
        mock_lead = Mock(spec=LeadModel)
        mock_lead.id = 1
        mock_lead.company = "TechCorp Solutions"
        mock_lead.description = "Leading SaaS provider using Python"
        mock_lead.industry = "Technology"
        mock_lead.location = "São Paulo"
        mock_lead.keywords = ["saas", "python"]
        mock_lead.contact = "John Doe"
        mock_lead.email = "john@techcorp.com"
        mock_lead.website = "techcorp.com"
        
        result = self.indexer.extract_searchable_metadata(mock_lead)
        
        # Check that all fields are included
        assert "searchable_text" in result
        assert "company_tokens" in result
        assert "industry_tokens" in result
        assert "location_tokens" in result
        assert "keywords" in result
        assert "all_tokens" in result
        
        # Check content
        assert "techcorp" in result["searchable_text"].lower()
        assert "technology" in result["searchable_text"].lower()
        assert "saas" in result["keywords"]
        assert "python" in result["keywords"]
    
    def test_index_lead_success(self):
        """Test successful lead indexing"""
        # Create mock lead
        mock_lead = Mock(spec=LeadModel)
        mock_lead.id = 1
        mock_lead.company = "Test Company"
        mock_lead.description = "Test description"
        mock_lead.industry = "Technology"
        mock_lead.location = "São Paulo"
        mock_lead.keywords = ["test"]
        mock_lead.contact = "Test Contact"
        mock_lead.email = "test@test.com"
        mock_lead.website = "test.com"
        mock_lead.phone = "123456789"
        mock_lead.revenue = "1M-5M"
        mock_lead.employees = "10-50"
        
        # Mock database commit
        self.mock_db.commit = Mock()
        
        # Mock cache methods
        self.mock_cache.add_to_inverted_index = Mock(return_value=True)
        self.mock_cache.cache_lead_data = Mock(return_value=True)
        
        # Test indexing
        result = self.indexer.index_lead(mock_lead)
        
        # Verify success
        assert result is True
        
        # Verify database was updated
        assert mock_lead.indexed_at is not None
        self.mock_db.commit.assert_called_once()
        
        # Verify cache was updated
        self.mock_cache.add_to_inverted_index.assert_called()
        self.mock_cache.cache_lead_data.assert_called()
    
    def test_index_lead_with_cache_disabled(self):
        """Test lead indexing when cache is disabled"""
        # Disable cache
        self.mock_cache.enabled = False
        
        # Create mock lead
        mock_lead = Mock(spec=LeadModel)
        mock_lead.id = 1
        mock_lead.company = "Test Company"
        mock_lead.description = "Test description"
        mock_lead.industry = "Technology"
        mock_lead.location = "São Paulo"
        mock_lead.keywords = ["test"]
        mock_lead.contact = "Test Contact"
        mock_lead.email = "test@test.com"
        mock_lead.website = "test.com"
        mock_lead.phone = "123456789"
        mock_lead.revenue = "1M-5M"
        mock_lead.employees = "10-50"
        
        # Mock database commit
        self.mock_db.commit = Mock()
        
        # Test indexing
        result = self.indexer.index_lead(mock_lead)
        
        # Should still succeed even without cache
        assert result is True
        assert mock_lead.indexed_at is not None
        self.mock_db.commit.assert_called_once()
    
    def test_remove_lead_from_index(self):
        """Test removing lead from index"""
        lead_id = 1
        
        # Mock cached data
        cached_data = {
            "company_tokens": ["techcorp"],
            "industry_tokens": ["technology"],
            "location_tokens": ["saopaulo"],
            "keywords": ["saas", "python"],
            "searchable_text": "techcorp technology saas python"
        }
        
        self.mock_cache.get_cached_lead_data = Mock(return_value=cached_data)
        self.mock_cache.remove_from_inverted_index = Mock(return_value=True)
        self.mock_cache.invalidate_lead_cache = Mock(return_value=True)
        
        # Test removal
        result = self.indexer.remove_lead_from_index(lead_id)
        
        # Verify success
        assert result is True
        
        # Verify cache methods were called
        self.mock_cache.get_cached_lead_data.assert_called_with(lead_id)
        self.mock_cache.remove_from_inverted_index.assert_called()
        self.mock_cache.invalidate_lead_cache.assert_called_with(lead_id)
    
    def test_search_leads_by_tokens(self):
        """Test searching leads using Redis inverted index"""
        tokens = ["technology", "saas"]
        expected_lead_ids = [1, 2, 3]
        
        self.mock_cache.get_index_intersection = Mock(return_value=expected_lead_ids)
        
        result = self.indexer.search_leads_by_tokens(tokens, limit=10)
        
        assert result == expected_lead_ids
        self.mock_cache.get_index_intersection.assert_called_once()
    
    def test_search_leads_by_tokens_cache_disabled(self):
        """Test searching when cache is disabled"""
        self.mock_cache.enabled = False
        
        result = self.indexer.search_leads_by_tokens(["technology"], limit=10)
        
        assert result == []
    
    def test_bulk_index_leads(self):
        """Test bulk indexing functionality"""
        # Create mock leads
        mock_leads = []
        for i in range(3):
            mock_lead = Mock(spec=LeadModel)
            mock_lead.id = i + 1
            mock_lead.company = f"Company {i+1}"
            mock_lead.description = f"Description {i+1}"
            mock_lead.industry = "Technology"
            mock_lead.location = "São Paulo"
            mock_lead.keywords = [f"keyword{i+1}"]
            mock_lead.contact = f"Contact {i+1}"
            mock_lead.email = f"test{i+1}@test.com"
            mock_lead.website = f"test{i+1}.com"
            mock_lead.phone = "123456789"
            mock_lead.revenue = "1M-5M"
            mock_lead.employees = "10-50"
            mock_leads.append(mock_lead)
        
        # Mock database query with proper pagination simulation
        mock_query = Mock()
        
        # Simulate pagination: first batch (2 leads), second batch (1 lead), third batch (empty)
        mock_offset_limit = Mock()
        mock_offset_limit.all.side_effect = [
            mock_leads[:2],  # First batch: leads 0-1
            mock_leads[2:],  # Second batch: lead 2
            []               # Third batch: empty (stops the loop)
        ]
        mock_query.offset.return_value.limit.return_value = mock_offset_limit
        mock_query.count.return_value = len(mock_leads)
        self.mock_db.query.return_value = mock_query
        self.mock_db.commit = Mock()
        
        # Mock cache methods
        self.mock_cache.add_to_inverted_index = Mock(return_value=True)
        self.mock_cache.cache_lead_data = Mock(return_value=True)
        
        # Test bulk indexing
        stats = self.indexer.bulk_index_leads(batch_size=2)
        
        # Verify results
        assert stats.total_leads == 3
        assert stats.indexed_leads == 3
        assert stats.failed_leads == 0
        assert stats.processing_time > 0
    
    def test_get_indexing_status(self):
        """Test getting indexing status"""
        # Mock database queries
        self.mock_db.query.return_value.scalar.return_value = 100  # total leads
        
        # Mock filter query for indexed leads
        mock_filter_query = Mock()
        mock_filter_query.scalar.return_value = 80  # indexed leads
        self.mock_db.query.return_value.filter.return_value = mock_filter_query
        
        # Mock cache health check
        self.mock_cache.health_check = Mock(return_value={"status": "healthy"})
        
        result = self.indexer.get_indexing_status()
        
        assert result["total_leads"] == 100
        assert result["indexed_leads"] == 80
        assert result["unindexed_leads"] == 20
        assert result["indexing_coverage"] == 80.0
        assert result["cache_status"]["status"] == "healthy"

if __name__ == "__main__":
    pytest.main([__file__])