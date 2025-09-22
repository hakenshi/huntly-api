"""
Search Analytics Tracker for Huntly MVP
Tracks search events and user interactions for analytics
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..database.models import SearchAnalyticsEvent, LeadInteractionEvent, Lead
from ..cache.manager import CacheManager

logger = logging.getLogger(__name__)

class SearchAnalyticsTracker:
    """Tracks search analytics events and user interactions"""
    
    def __init__(self, db_session: Session, cache_manager: CacheManager):
        """Initialize analytics tracker with database and cache"""
        self.db = db_session
        self.cache = cache_manager
        
    def track_search_event(
        self,
        user_id: Optional[int],
        query_text: Optional[str],
        filters_applied: Dict[str, Any],
        results_count: int,
        response_time_ms: int,
        cache_hit: str = "miss",
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[int]:
        """
        Track a search event
        
        Args:
            user_id: ID of the user performing the search
            query_text: The search query text
            filters_applied: Dictionary of applied filters
            results_count: Number of results returned
            response_time_ms: Response time in milliseconds
            cache_hit: Cache performance (hit, miss, partial)
            session_id: User session ID
            user_agent: User agent string
            ip_address: User IP address
            
        Returns:
            ID of the created search event or None if failed
        """
        try:
            # Create search analytics event
            search_event = SearchAnalyticsEvent(
                user_id=user_id,
                query_text=query_text,
                filters_applied=filters_applied,
                results_count=results_count,
                response_time_ms=response_time_ms,
                cache_hit=cache_hit,
                session_id=session_id or str(uuid.uuid4()),
                user_agent=user_agent,
                ip_address=ip_address
            )
            
            self.db.add(search_event)
            self.db.commit()
            
            # Update cache with search analytics
            self._update_search_analytics_cache(query_text, cache_hit, response_time_ms)
            
            logger.debug(f"Tracked search event: user={user_id}, query='{query_text}', results={results_count}")
            return search_event.id
            
        except SQLAlchemyError as e:
            logger.error(f"Database error tracking search event: {e}")
            self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Error tracking search event: {e}")
            return None
    
    def track_lead_interaction(
        self,
        user_id: int,
        lead_id: int,
        interaction_type: str,
        interaction_data: Optional[Dict[str, Any]] = None,
        source_search_query: Optional[str] = None,
        source_campaign_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Track a lead interaction event
        
        Args:
            user_id: ID of the user
            lead_id: ID of the lead
            interaction_type: Type of interaction (view, contact, email, call, convert)
            interaction_data: Additional data about the interaction
            source_search_query: Original search query that led to this lead
            source_campaign_id: Campaign that led to this interaction
            
        Returns:
            ID of the created interaction event or None if failed
        """
        try:
            # Create lead interaction event
            interaction_event = LeadInteractionEvent(
                user_id=user_id,
                lead_id=lead_id,
                interaction_type=interaction_type,
                interaction_data=interaction_data or {},
                source_search_query=source_search_query,
                source_campaign_id=source_campaign_id
            )
            
            self.db.add(interaction_event)
            
            # Update lead interaction counters
            self._update_lead_counters(lead_id, interaction_type)
            
            self.db.commit()
            
            # Update cache with interaction analytics
            self._update_interaction_analytics_cache(interaction_type, lead_id)
            
            logger.debug(f"Tracked lead interaction: user={user_id}, lead={lead_id}, type={interaction_type}")
            return interaction_event.id
            
        except SQLAlchemyError as e:
            logger.error(f"Database error tracking lead interaction: {e}")
            self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Error tracking lead interaction: {e}")
            return None
    
    def track_search_result_click(
        self,
        search_event_id: int,
        lead_id: int,
        position: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Track when a user clicks on a search result
        
        Args:
            search_event_id: ID of the original search event
            lead_id: ID of the clicked lead
            position: Position of the lead in search results
            user_id: ID of the user (optional)
            
        Returns:
            True if successfully tracked, False otherwise
        """
        try:
            # Update search event with click
            search_event = self.db.query(SearchAnalyticsEvent).filter(
                SearchAnalyticsEvent.id == search_event_id
            ).first()
            
            if search_event:
                search_event.clicked_results += 1
                
                # Track as lead interaction
                if user_id:
                    self.track_lead_interaction(
                        user_id=user_id,
                        lead_id=lead_id,
                        interaction_type="view",
                        interaction_data={
                            "search_event_id": search_event_id,
                            "position": position,
                            "click_timestamp": datetime.utcnow().isoformat()
                        },
                        source_search_query=search_event.query_text
                    )
                
                self.db.commit()
                logger.debug(f"Tracked search result click: search={search_event_id}, lead={lead_id}, pos={position}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error tracking search result click: {e}")
            self.db.rollback()
            return False
    
    def track_search_conversion(
        self,
        search_event_id: int,
        lead_id: int,
        conversion_type: str = "contact",
        user_id: Optional[int] = None
    ) -> bool:
        """
        Track when a search leads to a conversion
        
        Args:
            search_event_id: ID of the original search event
            lead_id: ID of the converted lead
            conversion_type: Type of conversion (contact, qualified, sale)
            user_id: ID of the user (optional)
            
        Returns:
            True if successfully tracked, False otherwise
        """
        try:
            # Update search event with conversion
            search_event = self.db.query(SearchAnalyticsEvent).filter(
                SearchAnalyticsEvent.id == search_event_id
            ).first()
            
            if search_event:
                if conversion_type == "contact":
                    search_event.contacted_leads += 1
                elif conversion_type in ["qualified", "sale"]:
                    search_event.converted_leads += 1
                
                # Track as lead interaction
                if user_id:
                    self.track_lead_interaction(
                        user_id=user_id,
                        lead_id=lead_id,
                        interaction_type="convert",
                        interaction_data={
                            "search_event_id": search_event_id,
                            "conversion_type": conversion_type,
                            "conversion_timestamp": datetime.utcnow().isoformat()
                        },
                        source_search_query=search_event.query_text
                    )
                
                self.db.commit()
                logger.debug(f"Tracked search conversion: search={search_event_id}, lead={lead_id}, type={conversion_type}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error tracking search conversion: {e}")
            self.db.rollback()
            return False
    
    def get_search_analytics_summary(
        self,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get search analytics summary for the last N days
        
        Args:
            user_id: Filter by user ID (optional)
            days: Number of days to include
            
        Returns:
            Dictionary with analytics summary
        """
        try:
            from datetime import timedelta
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Build query
            query = self.db.query(SearchAnalyticsEvent).filter(
                SearchAnalyticsEvent.created_at >= start_date
            )
            
            if user_id:
                query = query.filter(SearchAnalyticsEvent.user_id == user_id)
            
            events = query.all()
            
            if not events:
                return {
                    "total_searches": 0,
                    "avg_response_time_ms": 0,
                    "cache_hit_rate": 0.0,
                    "avg_results_per_search": 0.0,
                    "total_clicks": 0,
                    "total_conversions": 0,
                    "click_through_rate": 0.0,
                    "conversion_rate": 0.0
                }
            
            # Calculate metrics
            total_searches = len(events)
            total_response_time = sum(e.response_time_ms for e in events if e.response_time_ms)
            cache_hits = sum(1 for e in events if e.cache_hit == "hit")
            total_results = sum(e.results_count for e in events)
            total_clicks = sum(e.clicked_results for e in events)
            total_conversions = sum(e.converted_leads + e.contacted_leads for e in events)
            
            avg_response_time = total_response_time / total_searches if total_searches > 0 else 0
            cache_hit_rate = (cache_hits / total_searches * 100) if total_searches > 0 else 0.0
            avg_results_per_search = total_results / total_searches if total_searches > 0 else 0.0
            click_through_rate = (total_clicks / total_searches * 100) if total_searches > 0 else 0.0
            conversion_rate = (total_conversions / total_searches * 100) if total_searches > 0 else 0.0
            
            return {
                "total_searches": total_searches,
                "avg_response_time_ms": round(avg_response_time),
                "cache_hit_rate": round(cache_hit_rate, 1),
                "avg_results_per_search": round(avg_results_per_search, 1),
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "click_through_rate": round(click_through_rate, 1),
                "conversion_rate": round(conversion_rate, 1),
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting search analytics summary: {e}")
            return {}
    
    def get_popular_queries(
        self,
        user_id: Optional[int] = None,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most popular search queries
        
        Args:
            user_id: Filter by user ID (optional)
            days: Number of days to include
            limit: Maximum number of queries to return
            
        Returns:
            List of popular queries with counts
        """
        try:
            from datetime import timedelta
            from sqlalchemy import func, desc
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Build query
            query = self.db.query(
                SearchAnalyticsEvent.query_text,
                func.count(SearchAnalyticsEvent.id).label('count'),
                func.avg(SearchAnalyticsEvent.results_count).label('avg_results'),
                func.avg(SearchAnalyticsEvent.response_time_ms).label('avg_response_time')
            ).filter(
                SearchAnalyticsEvent.created_at >= start_date,
                SearchAnalyticsEvent.query_text.isnot(None),
                SearchAnalyticsEvent.query_text != ""
            )
            
            if user_id:
                query = query.filter(SearchAnalyticsEvent.user_id == user_id)
            
            results = query.group_by(SearchAnalyticsEvent.query_text).order_by(
                desc(func.count(SearchAnalyticsEvent.id))
            ).limit(limit).all()
            
            return [
                {
                    "query": result.query_text,
                    "count": int(result.count),
                    "avg_results": round(float(result.avg_results or 0), 1),
                    "avg_response_time_ms": round(float(result.avg_response_time or 0))
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting popular queries: {e}")
            return []
    
    def _update_lead_counters(self, lead_id: int, interaction_type: str) -> None:
        """Update lead interaction counters"""
        try:
            lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                if interaction_type == "view":
                    lead.view_count = (lead.view_count or 0) + 1
                elif interaction_type in ["contact", "email", "call"]:
                    lead.contact_count = (lead.contact_count or 0) + 1
                    lead.last_contact = datetime.utcnow()
                elif interaction_type == "convert":
                    lead.conversion_score = min((lead.conversion_score or 0) + 0.1, 1.0)
                
        except Exception as e:
            logger.error(f"Error updating lead counters: {e}")
    
    def _update_search_analytics_cache(
        self,
        query_text: Optional[str],
        cache_hit: str,
        response_time_ms: int
    ) -> None:
        """Update search analytics in cache"""
        try:
            # Add to popular searches if query exists
            if query_text and query_text.strip():
                self.cache.add_popular_search(query_text.strip())
            
            # Update performance metrics in cache
            cache_key = "search_performance_realtime"
            current_data = self.cache.get_cached_analytics_data(cache_key) or {
                "total_searches": 0,
                "total_response_time": 0,
                "cache_hits": 0
            }
            
            current_data["total_searches"] += 1
            current_data["total_response_time"] += response_time_ms
            if cache_hit == "hit":
                current_data["cache_hits"] += 1
            
            # Cache for 5 minutes
            self.cache.cache_analytics_data(cache_key, current_data, 300)
            
        except Exception as e:
            logger.error(f"Error updating search analytics cache: {e}")
    
    def _update_interaction_analytics_cache(
        self,
        interaction_type: str,
        lead_id: int
    ) -> None:
        """Update interaction analytics in cache"""
        try:
            cache_key = "interaction_analytics_realtime"
            current_data = self.cache.get_cached_analytics_data(cache_key) or {
                "total_interactions": 0,
                "views": 0,
                "contacts": 0,
                "conversions": 0
            }
            
            current_data["total_interactions"] += 1
            
            if interaction_type == "view":
                current_data["views"] += 1
            elif interaction_type in ["contact", "email", "call"]:
                current_data["contacts"] += 1
            elif interaction_type == "convert":
                current_data["conversions"] += 1
            
            # Cache for 5 minutes
            self.cache.cache_analytics_data(cache_key, current_data, 300)
            
        except Exception as e:
            logger.error(f"Error updating interaction analytics cache: {e}")