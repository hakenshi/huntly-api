"""
Lead Indexer for Huntly MVP
Handles lead indexing with PostgreSQL tsvector and Redis inverted index
"""

import re
import logging
import time
from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from ..database.models import Lead as LeadModel
from ..cache.manager import CacheManager
from .models import IndexedLead, IndexingStats

logger = logging.getLogger(__name__)

class LeadIndexer:
    """
    Lead indexer that extracts searchable metadata and creates indexes
    for fast lead discovery using PostgreSQL full-text search and Redis
    """
    
    def __init__(self, db_session: Session, cache_manager: CacheManager):
        """Initialize indexer with database session and cache manager"""
        self.db = db_session
        self.cache = cache_manager
        
        # Stop words to exclude from indexing
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'
        }
    
    def extract_searchable_metadata(self, lead: LeadModel) -> Dict[str, Any]:
        """
        Extract and process searchable metadata from a lead
        
        Args:
            lead: SQLAlchemy Lead model instance
            
        Returns:
            Dictionary with extracted metadata for indexing
        """
        try:
            # Basic text fields
            company_text = self._clean_text(lead.company or "")
            description_text = self._clean_text(lead.description or "")
            industry_text = self._clean_text(lead.industry or "")
            location_text = self._clean_text(lead.location or "")
            
            # Extract keywords from various fields
            keywords = []
            if lead.keywords and isinstance(lead.keywords, (list, tuple)):
                keywords.extend([self._clean_text(kw) for kw in lead.keywords if kw])
            
            # Auto-extract keywords from description
            if description_text:
                auto_keywords = self._extract_keywords_from_text(description_text)
                keywords.extend(auto_keywords)
            
            # Tokenize important fields
            company_tokens = self._tokenize_text(company_text)
            industry_tokens = self._tokenize_text(industry_text)
            location_tokens = self._tokenize_text(location_text)
            
            # Create searchable text combining all relevant fields
            searchable_parts = [
                company_text,
                description_text,
                industry_text,
                location_text,
                " ".join(keywords),
                lead.contact or "",
                lead.email or "",
                lead.website or ""
            ]
            
            searchable_text = " ".join(filter(None, searchable_parts))
            
            return {
                "searchable_text": searchable_text,
                "company_tokens": company_tokens,
                "industry_tokens": industry_tokens,
                "location_tokens": location_tokens,
                "keywords": list(set(keywords)),  # Remove duplicates
                "all_tokens": self._tokenize_text(searchable_text)
            }
            
        except Exception as e:
            logger.error(f"Error extracting metadata for lead {lead.id}: {e}")
            return {
                "searchable_text": "",
                "company_tokens": [],
                "industry_tokens": [],
                "location_tokens": [],
                "keywords": [],
                "all_tokens": []
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for indexing"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces and alphanumeric
        text = re.sub(r'[^\w\s-]', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into searchable terms"""
        if not text:
            return []
        
        # Split by whitespace and filter out stop words and short terms
        tokens = [
            token for token in text.split()
            if len(token) >= 2 and token not in self.stop_words
        ]
        
        return list(set(tokens))  # Remove duplicates
    
    def _extract_keywords_from_text(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract potential keywords from text using simple heuristics"""
        if not text:
            return []
        
        # Look for capitalized words (potential company names, technologies)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        # Look for technical terms (words with numbers or specific patterns)
        technical_terms = re.findall(r'\b\w*[0-9]\w*\b|\b[A-Z]{2,}\b', text)
        
        # Combine and clean
        keywords = []
        for word in capitalized_words + technical_terms:
            clean_word = self._clean_text(word)
            if len(clean_word) >= 3 and clean_word not in self.stop_words:
                keywords.append(clean_word)
        
        # Return unique keywords, limited by max_keywords
        return list(set(keywords))[:max_keywords]
    
    def index_lead(self, lead: LeadModel) -> bool:
        """
        Index a single lead in both PostgreSQL and Redis
        
        Args:
            lead: SQLAlchemy Lead model instance
            
        Returns:
            True if indexing successful, False otherwise
        """
        try:
            # Extract metadata
            metadata = self.extract_searchable_metadata(lead)
            
            # Update PostgreSQL search vector (handled by trigger)
            # We just need to update the lead to trigger the search vector update
            lead.indexed_at = datetime.utcnow()
            self.db.commit()
            
            # Update Redis inverted index
            self._update_redis_index(lead.id, metadata)
            
            # Cache the indexed lead data
            indexed_lead_data = {
                "id": lead.id,
                "company": lead.company,
                "contact": lead.contact,
                "email": lead.email,
                "phone": lead.phone,
                "website": lead.website,
                "industry": lead.industry,
                "location": lead.location,
                "revenue": lead.revenue,
                "employees": lead.employees,
                "description": lead.description,
                "keywords": metadata["keywords"],
                "searchable_text": metadata["searchable_text"],
                "indexed_at": lead.indexed_at.isoformat() if lead.indexed_at else None,
                "company_tokens": metadata["company_tokens"],
                "industry_tokens": metadata["industry_tokens"],
                "location_tokens": metadata["location_tokens"]
            }
            
            self.cache.cache_lead_data(lead.id, indexed_lead_data)
            
            logger.debug(f"Successfully indexed lead {lead.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing lead {lead.id}: {e}")
            return False
    
    def _update_redis_index(self, lead_id: int, metadata: Dict[str, Any]) -> None:
        """Update Redis inverted index with lead tokens"""
        if not self.cache.enabled:
            return
        
        try:
            # Index all tokens from the lead
            all_tokens = set()
            all_tokens.update(metadata.get("all_tokens", []))
            all_tokens.update(metadata.get("company_tokens", []))
            all_tokens.update(metadata.get("industry_tokens", []))
            all_tokens.update(metadata.get("location_tokens", []))
            all_tokens.update(metadata.get("keywords", []))
            
            # Add lead ID to inverted index for each token
            for token in all_tokens:
                if len(token) >= 2:  # Only index meaningful tokens
                    self.cache.add_to_inverted_index(token, lead_id)
            
            # Also index industry and location as exact matches
            if metadata.get("industry_tokens"):
                industry_key = f"industry:{metadata['industry_tokens'][0]}" if metadata['industry_tokens'] else None
                if industry_key:
                    self.cache.add_to_inverted_index(industry_key, lead_id)
            
            if metadata.get("location_tokens"):
                location_key = f"location:{metadata['location_tokens'][0]}" if metadata['location_tokens'] else None
                if location_key:
                    self.cache.add_to_inverted_index(location_key, lead_id)
                    
        except Exception as e:
            logger.error(f"Error updating Redis index for lead {lead_id}: {e}")
    
    def remove_lead_from_index(self, lead_id: int) -> bool:
        """
        Remove a lead from both PostgreSQL and Redis indexes
        
        Args:
            lead_id: ID of the lead to remove
            
        Returns:
            True if removal successful, False otherwise
        """
        try:
            # Get cached lead data to know what to remove from Redis
            cached_data = self.cache.get_cached_lead_data(lead_id)
            
            if cached_data:
                # Remove from Redis inverted index
                all_tokens = set()
                all_tokens.update(cached_data.get("company_tokens", []))
                all_tokens.update(cached_data.get("industry_tokens", []))
                all_tokens.update(cached_data.get("location_tokens", []))
                all_tokens.update(cached_data.get("keywords", []))
                
                # Also get tokens from searchable text
                if cached_data.get("searchable_text"):
                    text_tokens = self._tokenize_text(cached_data["searchable_text"])
                    all_tokens.update(text_tokens)
                
                # Remove from inverted index
                for token in all_tokens:
                    if len(token) >= 2:
                        self.cache.remove_from_inverted_index(token, lead_id)
            
            # Remove cached lead data
            self.cache.invalidate_lead_cache(lead_id)
            
            # PostgreSQL search vector will be updated automatically when lead is deleted
            
            logger.debug(f"Successfully removed lead {lead_id} from indexes")
            return True
            
        except Exception as e:
            logger.error(f"Error removing lead {lead_id} from indexes: {e}")
            return False
    
    def bulk_index_leads(self, lead_ids: Optional[List[int]] = None, batch_size: int = 100) -> IndexingStats:
        """
        Index multiple leads in batches for better performance
        
        Args:
            lead_ids: Optional list of specific lead IDs to index. If None, indexes all leads.
            batch_size: Number of leads to process in each batch
            
        Returns:
            IndexingStats with processing results
        """
        start_time = time.time()
        stats = IndexingStats(
            total_leads=0,
            indexed_leads=0,
            failed_leads=0,
            processing_time=0.0,
            errors=[]
        )
        
        try:
            # Build query for leads to index
            query = self.db.query(LeadModel)
            
            if lead_ids:
                query = query.filter(LeadModel.id.in_(lead_ids))
                stats.total_leads = len(lead_ids)
            else:
                # Index all leads that haven't been indexed or need re-indexing
                stats.total_leads = query.count()
            
            logger.info(f"Starting bulk indexing of {stats.total_leads} leads")
            
            # Process in batches
            offset = 0
            while True:
                batch_leads = query.offset(offset).limit(batch_size).all()
                
                if not batch_leads:
                    break
                
                # Index each lead in the batch
                for lead in batch_leads:
                    try:
                        if self.index_lead(lead):
                            stats.indexed_leads += 1
                        else:
                            stats.failed_leads += 1
                            stats.errors.append(f"Failed to index lead {lead.id}")
                    except Exception as e:
                        stats.failed_leads += 1
                        error_msg = f"Error indexing lead {lead.id}: {str(e)}"
                        stats.errors.append(error_msg)
                        logger.error(error_msg)
                
                offset += batch_size
                
                # Log progress
                if offset % (batch_size * 10) == 0:
                    logger.info(f"Indexed {stats.indexed_leads} of {stats.total_leads} leads")
            
            # Commit any remaining database changes
            self.db.commit()
            
        except Exception as e:
            error_msg = f"Error in bulk indexing: {str(e)}"
            stats.errors.append(error_msg)
            logger.error(error_msg)
            self.db.rollback()
        
        finally:
            stats.processing_time = time.time() - start_time
            
        logger.info(
            f"Bulk indexing completed: {stats.indexed_leads} indexed, "
            f"{stats.failed_leads} failed, {stats.processing_time:.2f}s"
        )
        
        return stats
    
    def reindex_all_leads(self) -> IndexingStats:
        """
        Reindex all leads in the database
        Useful for updating indexes after schema changes
        
        Returns:
            IndexingStats with processing results
        """
        logger.info("Starting full reindex of all leads")
        
        # Clear existing Redis indexes
        if self.cache.enabled:
            try:
                # Clear all index keys
                pattern = f"{self.cache.config.get_key_prefix('index')}*"
                self.cache.invalidate_pattern(pattern)
                logger.info("Cleared existing Redis indexes")
            except Exception as e:
                logger.warning(f"Error clearing Redis indexes: {e}")
        
        # Perform bulk indexing of all leads
        return self.bulk_index_leads()
    
    def get_indexing_status(self) -> Dict[str, Any]:
        """
        Get current indexing status and statistics
        
        Returns:
            Dictionary with indexing status information
        """
        try:
            # Count total leads
            total_leads = self.db.query(func.count(LeadModel.id)).scalar()
            
            # Count indexed leads (those with indexed_at timestamp)
            indexed_leads = self.db.query(func.count(LeadModel.id)).filter(
                LeadModel.indexed_at.isnot(None)
            ).scalar()
            
            # Get cache status
            cache_status = self.cache.health_check() if self.cache.enabled else {"status": "disabled"}
            
            return {
                "total_leads": total_leads,
                "indexed_leads": indexed_leads,
                "unindexed_leads": total_leads - indexed_leads,
                "indexing_coverage": (indexed_leads / total_leads * 100) if total_leads > 0 else 0,
                "cache_status": cache_status,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting indexing status: {e}")
            return {
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat()
            }
    
    def search_leads_by_tokens(self, tokens: List[str], limit: int = 100) -> List[int]:
        """
        Search for lead IDs using Redis inverted index
        
        Args:
            tokens: List of search tokens
            limit: Maximum number of results to return
            
        Returns:
            List of lead IDs matching the search tokens
        """
        if not self.cache.enabled or not tokens:
            return []
        
        try:
            # Clean and filter tokens
            clean_tokens = [
                self._clean_text(token) for token in tokens
                if len(self._clean_text(token)) >= 2
            ]
            
            if not clean_tokens:
                return []
            
            # Get intersection of lead IDs for all tokens
            lead_ids = self.cache.get_index_intersection(clean_tokens)
            
            # Limit results
            return lead_ids[:limit]
            
        except Exception as e:
            logger.error(f"Error searching leads by tokens {tokens}: {e}")
            return []