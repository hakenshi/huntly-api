"""
Search Engine Core for Huntly MVP
Implements query processing, ranking algorithm, and cache-first search strategy
"""

import re
import logging
import time
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_, and_

from ..database.models import Lead as LeadModel
from ..cache.manager import CacheManager
from ..models.search import SearchQuery, SearchFilters, SearchUserPreferences
from .models import SearchResult, IndexedLead
from .indexer import LeadIndexer

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Processes and parses search queries"""
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'
        }
    
    def parse_query(self, query_text: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured search terms
        
        Args:
            query_text: Raw search query string
            
        Returns:
            Dictionary with parsed query components
        """
        if not query_text:
            return {"terms": [], "phrases": [], "filters": {}}
        
        # Clean and normalize query
        clean_query = self._clean_text(query_text)
        
        # Extract quoted phrases
        phrases = re.findall(r'"([^"]*)"', clean_query)
        
        # Remove quoted phrases from query for term extraction
        query_without_phrases = re.sub(r'"[^"]*"', '', clean_query)
        
        # Extract individual terms
        terms = self._extract_terms(query_without_phrases)
        
        # Extract implicit filters from query
        implicit_filters = self._extract_implicit_filters(clean_query)
        
        return {
            "terms": terms,
            "phrases": phrases,
            "filters": implicit_filters,
            "original_query": query_text
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep quotes, spaces, and alphanumeric
        text = re.sub(r'[^\w\s"-]', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_terms(self, text: str) -> List[str]:
        """Extract search terms from text"""
        if not text:
            return []
        
        # Split by whitespace and filter
        terms = [
            term for term in text.split()
            if len(term) >= 2 and term not in self.stop_words
        ]
        
        return list(set(terms))  # Remove duplicates
    
    def _extract_implicit_filters(self, query: str) -> Dict[str, Any]:
        """Extract implicit filters from natural language query"""
        filters = {}
        
        # Industry patterns
        industry_patterns = {
            r'\b(tech|technology|software|it)\b': 'Tecnologia',
            r'\b(ecommerce|e-commerce|retail|commerce)\b': 'E-commerce',
            r'\b(finance|financial|bank|banking)\b': 'Financeiro',
            r'\b(health|healthcare|medical)\b': 'Saúde',
            r'\b(education|educational|school)\b': 'Educação',
            r'\b(manufacturing|industrial)\b': 'Industrial'
        }
        
        for pattern, industry in industry_patterns.items():
            if re.search(pattern, query):
                filters['industry'] = industry
                break
        
        # Location patterns
        location_patterns = {
            r'\b(são paulo|sp|sao paulo)\b': 'São Paulo',
            r'\b(rio de janeiro|rj|rio)\b': 'Rio de Janeiro',
            r'\b(belo horizonte|bh|minas)\b': 'Belo Horizonte',
            r'\b(brasília|brasilia|df)\b': 'Brasília',
            r'\b(salvador|bahia|ba)\b': 'Salvador'
        }
        
        for pattern, location in location_patterns.items():
            if re.search(pattern, query):
                filters['location'] = location
                break
        
        # Company size patterns
        size_patterns = {
            r'\b(startup|small|pequena)\b': '1-10',
            r'\b(medium|média|mid-size)\b': '11-50',
            r'\b(large|grande|big)\b': '51-200',
            r'\b(enterprise|corporation|multinational)\b': '200+'
        }
        
        for pattern, size in size_patterns.items():
            if re.search(pattern, query):
                filters['company_size'] = size
                break
        
        return filters


class RankingAlgorithm:
    """Implements search result ranking with configurable weights"""
    
    def __init__(self, user_preferences: Optional[SearchUserPreferences] = None):
        """Initialize ranking algorithm with user preferences"""
        self.user_preferences = user_preferences or SearchUserPreferences()
        
        # Default scoring weights
        self.default_weights = {
            "text_relevance": 0.4,
            "industry_match": 0.25,
            "location_proximity": 0.15,
            "company_size": 0.1,
            "data_quality": 0.05,
            "freshness": 0.05
        }
        
        # Use user preferences if available
        self.weights = (
            self.user_preferences.scoring_weights 
            if self.user_preferences.scoring_weights 
            else self.default_weights
        )
    
    def calculate_relevance_score(
        self, 
        lead: LeadModel, 
        parsed_query: Dict[str, Any],
        filters: SearchFilters
    ) -> Tuple[float, List[str]]:
        """
        Calculate relevance score for a lead
        
        Args:
            lead: Lead model instance
            parsed_query: Parsed query components
            filters: Search filters
            
        Returns:
            Tuple of (score, match_reasons)
        """
        score = 0.0
        match_reasons = []
        
        # Text relevance score
        text_score, text_reasons = self._calculate_text_score(lead, parsed_query)
        score += text_score * self.weights.get("text_relevance", 0.4)
        match_reasons.extend(text_reasons)
        
        # Industry match score
        industry_score, industry_reasons = self._calculate_industry_score(lead, filters)
        score += industry_score * self.weights.get("industry_match", 0.25)
        match_reasons.extend(industry_reasons)
        
        # Location proximity score
        location_score, location_reasons = self._calculate_location_score(lead, filters)
        score += location_score * self.weights.get("location_proximity", 0.15)
        match_reasons.extend(location_reasons)
        
        # Company size match score
        size_score, size_reasons = self._calculate_size_score(lead, filters)
        score += size_score * self.weights.get("company_size", 0.1)
        match_reasons.extend(size_reasons)
        
        # Data quality score
        quality_score, quality_reasons = self._calculate_quality_score(lead)
        score += quality_score * self.weights.get("data_quality", 0.05)
        match_reasons.extend(quality_reasons)
        
        # Freshness score
        freshness_score, freshness_reasons = self._calculate_freshness_score(lead)
        score += freshness_score * self.weights.get("freshness", 0.05)
        match_reasons.extend(freshness_reasons)
        
        return min(score, 1.0), match_reasons  # Cap at 1.0
    
    def _calculate_text_score(self, lead: LeadModel, parsed_query: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculate text relevance score"""
        if not parsed_query.get("terms") and not parsed_query.get("phrases"):
            return 0.0, []
        
        score = 0.0
        reasons = []
        
        # Combine all searchable text from lead
        searchable_fields = {
            "company": lead.company or "",
            "description": lead.description or "",
            "industry": lead.industry or "",
            "contact": lead.contact or ""
        }
        
        # Check term matches with field weights
        field_weights = {
            "company": 0.4,
            "description": 0.3,
            "industry": 0.2,
            "contact": 0.1
        }
        
        terms = parsed_query.get("terms", [])
        phrases = parsed_query.get("phrases", [])
        
        for field, text in searchable_fields.items():
            if not text:
                continue
                
            text_lower = text.lower()
            field_weight = field_weights.get(field, 0.1)
            
            # Check term matches
            for term in terms:
                if term in text_lower:
                    term_score = field_weight * (0.8 if text_lower.startswith(term) else 0.5)
                    score += term_score
                    reasons.append(f"Term '{term}' found in {field}")
            
            # Check phrase matches (higher weight)
            for phrase in phrases:
                if phrase in text_lower:
                    phrase_score = field_weight * 1.0
                    score += phrase_score
                    reasons.append(f"Phrase '{phrase}' found in {field}")
        
        return min(score, 1.0), reasons
    
    def _calculate_industry_score(self, lead: LeadModel, filters: SearchFilters) -> Tuple[float, List[str]]:
        """Calculate industry match score"""
        if not lead.industry:
            return 0.0, []
        
        # Check explicit filter first
        if filters.industry:
            # Exact match
            if lead.industry.lower() == filters.industry.lower():
                return 1.0, [f"Exact industry match: {lead.industry}"]
            
            # Partial match
            if filters.industry.lower() in lead.industry.lower():
                return 0.7, [f"Partial industry match: {lead.industry}"]
        
        # User preference match (even without explicit filter)
        if (self.user_preferences.preferred_industries and 
            lead.industry in self.user_preferences.preferred_industries):
            return 0.6, [f"User preferred industry: {lead.industry}"]
        
        return 0.0, []
    
    def _calculate_location_score(self, lead: LeadModel, filters: SearchFilters) -> Tuple[float, List[str]]:
        """Calculate location proximity score"""
        if not lead.location:
            return 0.0, []
        
        # Check explicit filter first
        if filters.location:
            lead_location = lead.location.lower()
            filter_location = filters.location.lower()
            
            # Exact match
            if lead_location == filter_location:
                return 1.0, [f"Exact location match: {lead.location}"]
            
            # Same city/state
            if any(part in lead_location for part in filter_location.split()):
                return 0.8, [f"Location proximity: {lead.location}"]
        
        # User preference match (even without explicit filter)
        if (self.user_preferences.preferred_locations and 
            lead.location in self.user_preferences.preferred_locations):
            return 0.6, [f"User preferred location: {lead.location}"]
        
        return 0.0, []
    
    def _calculate_size_score(self, lead: LeadModel, filters: SearchFilters) -> Tuple[float, List[str]]:
        """Calculate company size match score"""
        if not filters.company_size or not lead.employees:
            return 0.0, []
        
        # Exact match
        if lead.employees == filters.company_size:
            return 1.0, [f"Exact size match: {lead.employees}"]
        
        # Range overlap (simplified)
        if filters.company_size in lead.employees or lead.employees in filters.company_size:
            return 0.7, [f"Size range match: {lead.employees}"]
        
        return 0.0, []
    
    def _calculate_quality_score(self, lead: LeadModel) -> Tuple[float, List[str]]:
        """Calculate data quality score based on completeness"""
        score = 0.0
        reasons = []
        
        # Check field completeness
        fields_to_check = [
            ("company", lead.company),
            ("contact", lead.contact),
            ("email", lead.email),
            ("phone", lead.phone),
            ("industry", lead.industry),
            ("location", lead.location),
            ("description", lead.description)
        ]
        
        filled_fields = sum(1 for _, value in fields_to_check if value and value.strip())
        total_fields = len(fields_to_check)
        
        score = filled_fields / total_fields
        
        if score > 0.8:
            reasons.append("High data completeness")
        elif score > 0.5:
            reasons.append("Good data completeness")
        
        return score, reasons
    
    def _calculate_freshness_score(self, lead: LeadModel) -> Tuple[float, List[str]]:
        """Calculate freshness score based on creation/update time"""
        if not lead.created_at:
            return 0.0, []
        
        # Calculate days since creation
        now = datetime.now(timezone.utc)
        created_at = lead.created_at
        
        # Handle timezone-naive datetime
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        days_old = (now - created_at).days
        
        if days_old <= 7:
            return 1.0, ["Very recent lead"]
        elif days_old <= 30:
            return 0.8, ["Recent lead"]
        elif days_old <= 90:
            return 0.5, ["Moderately recent lead"]
        else:
            return 0.2, []


class SearchEngine:
    """
    Core search engine with query processing, ranking, and caching
    """
    
    def __init__(self, db_session: Session, cache_manager: CacheManager):
        """Initialize search engine with database and cache"""
        self.db = db_session
        self.cache = cache_manager
        self.indexer = LeadIndexer(db_session, cache_manager)
        self.query_processor = QueryProcessor()
        
        # Search configuration
        self.max_results = 1000
        self.cache_ttl = 3600  # 1 hour
        
    def search_leads(
        self, 
        query: SearchQuery, 
        user_preferences: Optional[SearchUserPreferences] = None
    ) -> List[SearchResult]:
        """
        Main search method with cache-first strategy
        
        Args:
            query: Search query with text and filters
            user_preferences: Optional user preferences for ranking
            
        Returns:
            List of ranked search results
        """
        start_time = time.time()
        
        try:
            # Create cache key from query
            cache_key_data = {
                "text": query.text,
                "filters": query.filters.model_dump() if query.filters else {},
                "sort_by": query.sort_by,
                "limit": query.limit,
                "offset": query.offset,
                "user_prefs": user_preferences.model_dump() if user_preferences else None
            }
            
            # Try cache first
            cached_results = self.cache.get_cached_search_results(cache_key_data)
            if cached_results:
                logger.info(f"Cache HIT for search query: {query.text}")
                results = [SearchResult(**result) for result in cached_results["results"]]
                return results[query.offset:query.offset + query.limit]
            
            logger.info(f"Cache MISS for search query: {query.text}")
            
            # Parse query
            parsed_query = self.query_processor.parse_query(query.text or "")
            
            # Merge implicit filters with explicit filters
            merged_filters = self._merge_filters(query.filters, parsed_query.get("filters", {}))
            
            # Get candidate leads
            candidate_leads = self._get_candidate_leads(parsed_query, merged_filters)
            
            # Rank results
            ranking_algorithm = RankingAlgorithm(user_preferences)
            ranked_results = []
            
            for lead in candidate_leads:
                score, reasons = ranking_algorithm.calculate_relevance_score(
                    lead, parsed_query, merged_filters
                )
                
                if score > 0:  # Only include leads with positive relevance
                    indexed_lead = self._convert_to_indexed_lead(lead)
                    result = SearchResult(
                        lead=indexed_lead,
                        relevance_score=score,
                        match_reasons=reasons,
                        highlighted_fields=self._generate_highlights(lead, parsed_query)
                    )
                    ranked_results.append(result)
            
            # Sort by relevance score
            if query.sort_by == "relevance":
                ranked_results.sort(key=lambda x: x.relevance_score, reverse=True)
            elif query.sort_by == "created_at":
                ranked_results.sort(key=lambda x: x.lead.indexed_at or datetime.min, reverse=True)
            
            # Limit results for caching
            limited_results = ranked_results[:self.max_results]
            
            # Cache results
            cache_data = [result.model_dump() for result in limited_results]
            self.cache.cache_search_results(cache_key_data, cache_data, self.cache_ttl)
            
            # Track popular search
            if query.text:
                self.cache.add_popular_search(query.text)
            
            # Apply pagination
            paginated_results = limited_results[query.offset:query.offset + query.limit]
            
            search_time = time.time() - start_time
            logger.info(
                f"Search completed: {len(paginated_results)} results in {search_time:.3f}s "
                f"(query: '{query.text}', total_found: {len(limited_results)})"
            )
            
            return paginated_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _merge_filters(self, explicit_filters: SearchFilters, implicit_filters: Dict[str, Any]) -> SearchFilters:
        """Merge explicit and implicit filters, with explicit taking precedence"""
        merged = explicit_filters.model_dump() if explicit_filters else {}
        
        # Add implicit filters only if not explicitly set
        for key, value in implicit_filters.items():
            if not merged.get(key):
                merged[key] = value
        
        return SearchFilters(**merged)
    
    def _get_candidate_leads(self, parsed_query: Dict[str, Any], filters: SearchFilters) -> List[LeadModel]:
        """Get candidate leads using cache-first strategy"""
        
        # Try Redis inverted index first for text queries
        if parsed_query.get("terms"):
            redis_candidates = self.indexer.search_leads_by_tokens(
                parsed_query["terms"], 
                limit=self.max_results
            )
            
            if redis_candidates:
                # Get leads from database by IDs
                db_query = self.db.query(LeadModel).filter(LeadModel.id.in_(redis_candidates))
                candidates = self._apply_filters_to_query(db_query, filters).all()
                
                if candidates:
                    logger.debug(f"Found {len(candidates)} candidates via Redis index")
                    return candidates
        
        # Fallback to PostgreSQL full-text search
        return self._search_postgresql(parsed_query, filters)
    
    def _search_postgresql(self, parsed_query: Dict[str, Any], filters: SearchFilters) -> List[LeadModel]:
        """Search using PostgreSQL full-text search"""
        
        query = self.db.query(LeadModel)
        
        # Apply text search if terms exist
        if parsed_query.get("terms") or parsed_query.get("phrases"):
            search_terms = []
            search_terms.extend(parsed_query.get("terms", []))
            search_terms.extend(parsed_query.get("phrases", []))
            
            if search_terms:
                # Use PostgreSQL full-text search
                search_query = " | ".join(search_terms)  # OR search
                query = query.filter(
                    or_(
                        func.to_tsvector('english', LeadModel.company).match(search_query),
                        func.to_tsvector('english', LeadModel.description).match(search_query),
                        LeadModel.company.ilike(f"%{search_terms[0]}%"),
                        LeadModel.industry.ilike(f"%{search_terms[0]}%")
                    )
                )
        
        # Apply filters
        query = self._apply_filters_to_query(query, filters)
        
        # Limit results
        candidates = query.limit(self.max_results).all()
        
        logger.debug(f"Found {len(candidates)} candidates via PostgreSQL")
        return candidates
    
    def _apply_filters_to_query(self, query, filters: SearchFilters):
        """Apply search filters to database query"""
        
        if filters.industry:
            query = query.filter(LeadModel.industry.ilike(f"%{filters.industry}%"))
        
        if filters.location:
            query = query.filter(LeadModel.location.ilike(f"%{filters.location}%"))
        
        if filters.company_size:
            query = query.filter(LeadModel.employees.ilike(f"%{filters.company_size}%"))
        
        if filters.revenue_range:
            query = query.filter(LeadModel.revenue.ilike(f"%{filters.revenue_range}%"))
        
        if filters.keywords:
            for keyword in filters.keywords:
                query = query.filter(
                    or_(
                        LeadModel.company.ilike(f"%{keyword}%"),
                        LeadModel.description.ilike(f"%{keyword}%"),
                        LeadModel.industry.ilike(f"%{keyword}%")
                    )
                )
        
        return query
    
    def _convert_to_indexed_lead(self, lead: LeadModel) -> IndexedLead:
        """Convert SQLAlchemy Lead to IndexedLead model"""
        
        # Get cached metadata if available
        cached_data = self.cache.get_cached_lead_data(lead.id)
        
        if cached_data:
            return IndexedLead(
                id=lead.id,
                company=lead.company or "",
                contact=lead.contact or "",
                email=lead.email or "",
                phone=lead.phone or "",
                website=lead.website or "",
                industry=lead.industry or "",
                location=lead.location or "",
                revenue=lead.revenue or "",
                employees=lead.employees or "",
                description=lead.description or "",
                keywords=cached_data.get("keywords", []),
                searchable_text=cached_data.get("searchable_text", ""),
                indexed_at=lead.indexed_at,
                industry_tokens=cached_data.get("industry_tokens", []),
                location_tokens=cached_data.get("location_tokens", []),
                company_tokens=cached_data.get("company_tokens", [])
            )
        
        # Generate on-the-fly if not cached
        metadata = self.indexer.extract_searchable_metadata(lead)
        
        return IndexedLead(
            id=lead.id,
            company=lead.company or "",
            contact=lead.contact or "",
            email=lead.email or "",
            phone=lead.phone or "",
            website=lead.website or "",
            industry=lead.industry or "",
            location=lead.location or "",
            revenue=lead.revenue or "",
            employees=lead.employees or "",
            description=lead.description or "",
            keywords=metadata.get("keywords", []),
            searchable_text=metadata.get("searchable_text", ""),
            indexed_at=lead.indexed_at,
            industry_tokens=metadata.get("industry_tokens", []),
            location_tokens=metadata.get("location_tokens", []),
            company_tokens=metadata.get("company_tokens", [])
        )
    
    def _generate_highlights(self, lead: LeadModel, parsed_query: Dict[str, Any]) -> Dict[str, str]:
        """Generate highlighted text snippets for search results"""
        highlights = {}
        
        terms = parsed_query.get("terms", []) + parsed_query.get("phrases", [])
        if not terms:
            return highlights
        
        # Highlight matches in key fields
        fields_to_highlight = {
            "company": lead.company,
            "description": lead.description,
            "industry": lead.industry
        }
        
        for field_name, field_value in fields_to_highlight.items():
            if not field_value:
                continue
            
            highlighted_text = field_value
            
            # Highlight each term
            for term in terms:
                if term.lower() in field_value.lower():
                    # Simple highlighting with <mark> tags
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    highlighted_text = pattern.sub(f"<mark>{term}</mark>", highlighted_text)
            
            if "<mark>" in highlighted_text:
                highlights[field_name] = highlighted_text
        
        return highlights
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get autocomplete suggestions for partial queries"""
        
        if not partial_query or len(partial_query) < 2:
            return []
        
        # Check cache first
        cached_suggestions = self.cache.get_cached_suggestions(partial_query.lower())
        if cached_suggestions:
            return cached_suggestions[:limit]
        
        suggestions = []
        
        try:
            # Get popular searches that start with the partial query
            popular_searches = self.cache.get_popular_searches(50)
            for search in popular_searches:
                if search.lower().startswith(partial_query.lower()):
                    suggestions.append(search)
            
            # Get company names that match
            company_matches = self.db.query(LeadModel.company).filter(
                LeadModel.company.ilike(f"{partial_query}%")
            ).distinct().limit(limit - len(suggestions)).all()
            
            for match in company_matches:
                if match[0] and match[0] not in suggestions:
                    suggestions.append(match[0])
            
            # Get industry matches
            if len(suggestions) < limit:
                industry_matches = self.db.query(LeadModel.industry).filter(
                    LeadModel.industry.ilike(f"{partial_query}%")
                ).distinct().limit(limit - len(suggestions)).all()
                
                for match in industry_matches:
                    if match[0] and match[0] not in suggestions:
                        suggestions.append(match[0])
            
            # Cache suggestions
            self.cache.cache_suggestions(partial_query.lower(), suggestions, ttl=1800)  # 30 min
            
        except Exception as e:
            logger.error(f"Error generating suggestions for '{partial_query}': {e}")
        
        return suggestions[:limit]
    
    def invalidate_search_cache(self) -> bool:
        """Invalidate all search caches"""
        try:
            self.cache.invalidate_search_cache()
            logger.info("Search cache invalidated")
            return True
        except Exception as e:
            logger.error(f"Error invalidating search cache: {e}")
            return False
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        try:
            # Get indexing status
            indexing_status = self.indexer.get_indexing_status()
            
            # Get popular searches
            popular_searches = self.cache.get_popular_searches(10)
            
            # Get cache health
            cache_health = self.cache.health_check()
            
            return {
                "indexing_status": indexing_status,
                "popular_searches": popular_searches,
                "cache_health": cache_health,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {"error": str(e)}