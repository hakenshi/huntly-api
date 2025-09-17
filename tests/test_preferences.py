import pytest
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.preferences import UserPreferencesCreate, UserPreferencesUpdate

class TestPreferencesValidation:
    """Test validation logic for preferences"""
    
    def test_scoring_weights_validation(self):
        """Test that scoring weights are properly validated"""
        # Valid weights (sum to 1.0)
        valid_preferences = UserPreferencesCreate(
            scoring_weights={
                "industry_match": 0.25,
                "location_proximity": 0.15,
                "company_size": 0.1,
                "text_relevance": 0.4,
                "data_quality": 0.1
            }
        )
        assert valid_preferences.scoring_weights is not None
        
        # Test that weights sum validation works
        with pytest.raises(ValueError, match="Scoring weights must sum to approximately 1.0"):
            UserPreferencesCreate(
                scoring_weights={
                    "industry_match": 0.5,
                    "location_proximity": 0.5,
                    "company_size": 0.5,  # This makes sum > 1.0
                    "text_relevance": 0.4,
                    "data_quality": 0.1
                }
            )
        
        # Test individual weight validation
        with pytest.raises(ValueError, match="Weight for .* must be between 0 and 1"):
            UserPreferencesCreate(
                scoring_weights={
                    "industry_match": 1.5,  # Invalid: > 1.0
                    "location_proximity": 0.0,
                    "company_size": 0.0,
                    "text_relevance": 0.0,
                    "data_quality": -0.5  # Invalid: < 0.0
                }
            )
    
    def test_preferences_create_defaults(self):
        """Test that default values are set correctly"""
        preferences = UserPreferencesCreate()
        
        assert preferences.preferred_industries == []
        assert preferences.preferred_locations == []
        assert preferences.company_size_range is None
        assert preferences.revenue_range is None
        assert preferences.scoring_weights is not None
        
        # Check default weights sum to 1.0
        total_weight = sum(preferences.scoring_weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point differences
    
    def test_preferences_update_validation(self):
        """Test update model validation"""
        # Valid update with partial data
        update = UserPreferencesUpdate(
            preferred_industries=["Tecnologia"],
            scoring_weights={
                "industry_match": 0.3,
                "location_proximity": 0.2,
                "company_size": 0.1,
                "text_relevance": 0.3,
                "data_quality": 0.1
            }
        )
        
        assert update.preferred_industries == ["Tecnologia"]
        assert update.preferred_locations is None  # Not set
        assert update.scoring_weights["industry_match"] == 0.3
    
    def test_empty_preferences_create(self):
        """Test creating preferences with minimal data"""
        preferences = UserPreferencesCreate(
            preferred_industries=["Saúde", "Educação"],
            preferred_locations=["São Paulo, SP"]
        )
        
        assert preferences.preferred_industries == ["Saúde", "Educação"]
        assert preferences.preferred_locations == ["São Paulo, SP"]
        assert preferences.company_size_range is None
        assert preferences.revenue_range is None
        # Should have default scoring weights
        assert preferences.scoring_weights is not None

class TestPreferencesModels:
    """Test preferences model behavior"""
    
    def test_preferences_model_serialization(self):
        """Test that preferences models serialize correctly"""
        preferences = UserPreferencesCreate(
            preferred_industries=["Tecnologia", "Fintech"],
            preferred_locations=["Rio de Janeiro, RJ", "São Paulo, SP"],
            company_size_range="50-200",
            revenue_range="R$ 5M - R$ 20M"
        )
        
        # Test model_dump
        data = preferences.model_dump()
        
        assert "preferred_industries" in data
        assert "preferred_locations" in data
        assert "company_size_range" in data
        assert "revenue_range" in data
        assert "scoring_weights" in data
        
        assert data["preferred_industries"] == ["Tecnologia", "Fintech"]
        assert data["company_size_range"] == "50-200"

# Remove the database-dependent tests for now since we don't have fixtures set up
# These can be added later when proper test database setup is implemented

if __name__ == "__main__":
    pytest.main([__file__])