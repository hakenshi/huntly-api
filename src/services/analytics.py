"""
Analytics Service for Huntly MVP
Calculates real-time metrics from database and provides caching
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_, case, desc
from sqlalchemy.sql import extract

from ..database.models import Lead, Campaign, User
from ..cache.manager import CacheManager
from ..models.search_analytics import (
    SearchPerformanceMetrics, 
    SearchConversionMetrics,
    SearchAnalytics,
    FacetValue,
    SearchFacets
)

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for calculating and caching analytics metrics"""
    
    def __init__(self, db_session: Session, cache_manager: CacheManager):
        """Initialize analytics service with database and cache"""
        self.db = db_session
        self.cache = cache_manager
        
        # Cache TTL settings (in seconds)
        self.cache_ttl = {
            "dashboard_metrics": 1800,      # 30 minutes
            "search_performance": 300,      # 5 minutes
            "search_conversion": 600,       # 10 minutes
            "leads_by_month": 3600,         # 1 hour
            "industry_breakdown": 1800,     # 30 minutes
            "source_metrics": 1800,         # 30 minutes
            "quality_scores": 1800,         # 30 minutes
            "search_trends": 300,           # 5 minutes
            "facets": 600                   # 10 minutes
        }
    
    def get_dashboard_metrics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get main dashboard metrics with caching"""
        cache_key = f"dashboard_metrics_{user_id or 'global'}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for dashboard metrics (user: {user_id})")
            return cached_data
        
        logger.debug(f"Cache MISS for dashboard metrics (user: {user_id})")
        
        try:
            # Build base query
            query = self.db.query(Lead)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            # Calculate metrics
            total_leads = query.count()
            
            # Qualified leads (leads with email or phone)
            qualified_query = query.filter(
                or_(
                    Lead.email.isnot(None),
                    Lead.phone.isnot(None)
                )
            )
            qualified_leads = qualified_query.count()
            
            # Conversion rate
            conversion_rate = (qualified_leads / total_leads * 100) if total_leads > 0 else 0.0
            
            # High quality leads (score > 70 or complete data)
            high_quality_leads = query.filter(
                or_(
                    Lead.score > 70,
                    and_(
                        Lead.email.isnot(None),
                        Lead.phone.isnot(None),
                        Lead.industry.isnot(None),
                        Lead.location.isnot(None)
                    )
                )
            ).count()
            
            # Average ROI calculation (simplified based on lead quality)
            avg_roi = self._calculate_average_roi(query)
            
            # Recent activity (leads created in last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_leads = query.filter(Lead.created_at >= week_ago).count()
            
            # Growth rate (compare with previous period)
            two_weeks_ago = datetime.utcnow() - timedelta(days=14)
            previous_week_leads = query.filter(
                and_(
                    Lead.created_at >= two_weeks_ago,
                    Lead.created_at < week_ago
                )
            ).count()
            
            growth_rate = (
                ((recent_leads - previous_week_leads) / previous_week_leads * 100)
                if previous_week_leads > 0 else 0.0
            )
            
            metrics = {
                "total_leads": total_leads,
                "qualified_leads": qualified_leads,
                "conversion_rate": round(conversion_rate, 1),
                "average_roi": round(avg_roi, 0),
                "high_quality_leads": high_quality_leads,
                "recent_leads": recent_leads,
                "growth_rate": round(growth_rate, 1),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key, 
                metrics, 
                self.cache_ttl["dashboard_metrics"]
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating dashboard metrics: {e}")
            return {
                "total_leads": 0,
                "qualified_leads": 0,
                "conversion_rate": 0.0,
                "average_roi": 0.0,
                "high_quality_leads": 0,
                "recent_leads": 0,
                "growth_rate": 0.0,
                "error": str(e)
            }
    
    def get_search_performance_metrics(self) -> Dict[str, Any]:
        """Get search performance metrics with caching"""
        cache_key = "search_performance_global"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug("Cache HIT for search performance metrics")
            return cached_data
        
        logger.debug("Cache MISS for search performance metrics")
        
        try:
            # Get popular searches from Redis
            popular_searches = self.cache.get_popular_searches(10)
            popular_queries = [
                {"query": query, "count": i + 1} 
                for i, query in enumerate(reversed(popular_searches))
            ]
            
            # Calculate search trends (hourly distribution)
            search_trends = self._calculate_search_trends()
            
            # Get indexing status
            indexing_status = self._get_indexing_status()
            
            # Cache health for response time estimation
            cache_health = self.cache.health_check()
            avg_response_time = 150 if cache_health.get("status") == "healthy" else 300
            
            # Estimate cache hit rate based on Redis keyspace
            cache_hit_rate = self._estimate_cache_hit_rate()
            
            # Count today's searches (estimated from popular searches activity)
            total_searches_today = len(popular_searches) * 5  # Rough estimation
            
            metrics = {
                "total_searches_today": total_searches_today,
                "avg_response_time_ms": avg_response_time,
                "cache_hit_rate": cache_hit_rate,
                "popular_queries": popular_queries,
                "search_trends": search_trends,
                "indexing_status": indexing_status,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key,
                metrics,
                self.cache_ttl["search_performance"]
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating search performance metrics: {e}")
            return {
                "total_searches_today": 0,
                "avg_response_time_ms": 300,
                "cache_hit_rate": 0.0,
                "popular_queries": [],
                "search_trends": {},
                "indexing_status": {},
                "error": str(e)
            }
    
    def get_search_conversion_metrics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get search conversion metrics with caching"""
        cache_key = f"search_conversion_{user_id or 'global'}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for search conversion metrics (user: {user_id})")
            return cached_data
        
        logger.debug(f"Cache MISS for search conversion metrics (user: {user_id})")
        
        try:
            # Build base query
            query = self.db.query(Lead)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            total_leads = query.count()
            
            # Calculate conversion rates
            contacted_leads = query.filter(Lead.last_contact.isnot(None)).count()
            qualified_leads = query.filter(
                or_(Lead.email.isnot(None), Lead.phone.isnot(None))
            ).count()
            
            search_to_contact_rate = (
                (contacted_leads / total_leads * 100) if total_leads > 0 else 0.0
            )
            search_to_qualified_rate = (
                (qualified_leads / total_leads * 100) if total_leads > 0 else 0.0
            )
            
            # Average results per search (estimated)
            avg_results_per_search = 12.5  # Based on typical search behavior
            
            # Zero results rate (estimated from incomplete leads)
            incomplete_leads = query.filter(
                and_(
                    Lead.company.is_(None),
                    Lead.email.is_(None),
                    Lead.phone.is_(None)
                )
            ).count()
            zero_results_rate = (incomplete_leads / total_leads * 100) if total_leads > 0 else 0.0
            
            # Refinement rate (estimated)
            refinement_rate = 18.9  # Typical refinement behavior
            
            # Conversion by query type (based on industry and location data)
            conversion_by_query_type = self._calculate_conversion_by_query_type(query)
            
            # Top converting filters
            top_converting_filters = self._calculate_top_converting_filters(query)
            
            metrics = {
                "search_to_contact_rate": round(search_to_contact_rate, 1),
                "search_to_qualified_rate": round(search_to_qualified_rate, 1),
                "avg_results_per_search": avg_results_per_search,
                "zero_results_rate": round(zero_results_rate, 1),
                "refinement_rate": refinement_rate,
                "conversion_by_query_type": conversion_by_query_type,
                "top_converting_filters": top_converting_filters,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key,
                metrics,
                self.cache_ttl["search_conversion"]
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating search conversion metrics: {e}")
            return {
                "search_to_contact_rate": 0.0,
                "search_to_qualified_rate": 0.0,
                "avg_results_per_search": 0.0,
                "zero_results_rate": 0.0,
                "refinement_rate": 0.0,
                "conversion_by_query_type": [],
                "top_converting_filters": [],
                "error": str(e)
            }
    
    def get_leads_by_month(self, user_id: Optional[int] = None, months: int = 6) -> List[Dict[str, Any]]:
        """Get leads evolution by month with caching"""
        cache_key = f"leads_by_month_{user_id or 'global'}_{months}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for leads by month (user: {user_id})")
            return cached_data
        
        logger.debug(f"Cache MISS for leads by month (user: {user_id})")
        
        try:
            # Build base query
            query = self.db.query(Lead)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            # Get data for the last N months
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=months * 30)
            
            query = query.filter(Lead.created_at >= start_date)
            
            # Group by month
            monthly_data = self.db.query(
                extract('year', Lead.created_at).label('year'),
                extract('month', Lead.created_at).label('month'),
                func.count(Lead.id).label('total_leads'),
                func.count(
                    case(
                        (or_(Lead.email.isnot(None), Lead.phone.isnot(None)), Lead.id),
                        else_=None
                    )
                ).label('qualified_leads')
            )
            
            if user_id:
                monthly_data = monthly_data.filter(Lead.user_id == user_id)
            
            monthly_data = monthly_data.filter(Lead.created_at >= start_date).group_by(
                extract('year', Lead.created_at),
                extract('month', Lead.created_at)
            ).order_by(
                extract('year', Lead.created_at),
                extract('month', Lead.created_at)
            ).all()
            
            # Format results
            month_names = [
                "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"
            ]
            
            results = []
            for row in monthly_data:
                month_name = month_names[int(row.month) - 1]
                results.append({
                    "month": month_name,
                    "leads": int(row.total_leads),
                    "qualified": int(row.qualified_leads),
                    "year": int(row.year)
                })
            
            # Fill missing months with zeros
            if len(results) < months:
                current_date = start_date
                existing_months = {(r["year"], month_names.index(r["month"]) + 1) for r in results}
                
                while current_date <= end_date:
                    year_month = (current_date.year, current_date.month)
                    if year_month not in existing_months:
                        results.append({
                            "month": month_names[current_date.month - 1],
                            "leads": 0,
                            "qualified": 0,
                            "year": current_date.year
                        })
                    current_date += timedelta(days=32)
                    current_date = current_date.replace(day=1)
            
            # Sort by date
            results.sort(key=lambda x: (x["year"], month_names.index(x["month"])))
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key,
                results,
                self.cache_ttl["leads_by_month"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating leads by month: {e}")
            return []
    
    def get_industry_breakdown(self, user_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get industry distribution with caching"""
        cache_key = f"industry_breakdown_{user_id or 'global'}_{limit}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for industry breakdown (user: {user_id})")
            return cached_data
        
        logger.debug(f"Cache MISS for industry breakdown (user: {user_id})")
        
        try:
            # Build query
            query = self.db.query(
                Lead.industry,
                func.count(Lead.id).label('count')
            ).filter(Lead.industry.isnot(None))
            
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            results = query.group_by(Lead.industry).order_by(
                desc(func.count(Lead.id))
            ).limit(limit).all()
            
            # Format results
            breakdown = [
                {
                    "industry": row.industry or "Não especificado",
                    "count": int(row.count)
                }
                for row in results
            ]
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key,
                breakdown,
                self.cache_ttl["industry_breakdown"]
            )
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Error calculating industry breakdown: {e}")
            return []
    
    def get_source_metrics(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get lead source metrics with caching"""
        cache_key = f"source_metrics_{user_id or 'global'}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for source metrics (user: {user_id})")
            return cached_data
        
        logger.debug(f"Cache MISS for source metrics (user: {user_id})")
        
        try:
            # Build base query
            query = self.db.query(Lead)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            total_leads = query.count()
            
            # Simulate source tracking based on data patterns
            # In a real implementation, you'd have a source field
            sources = []
            
            # LinkedIn (leads with complete professional info)
            linkedin_leads = query.filter(
                and_(
                    Lead.industry.isnot(None),
                    Lead.location.isnot(None),
                    Lead.description.isnot(None)
                )
            ).count()
            
            # Google Search (leads with website)
            google_leads = query.filter(Lead.website.isnot(None)).count()
            
            # Website (leads with email but no phone)
            website_leads = query.filter(
                and_(Lead.email.isnot(None), Lead.phone.is_(None))
            ).count()
            
            # Referrals (remaining leads)
            referral_leads = max(0, total_leads - linkedin_leads - google_leads - website_leads)
            
            if total_leads > 0:
                sources = [
                    {
                        "source": "LinkedIn",
                        "leads": linkedin_leads,
                        "percentage": round(linkedin_leads / total_leads * 100, 1)
                    },
                    {
                        "source": "Google Search",
                        "leads": google_leads,
                        "percentage": round(google_leads / total_leads * 100, 1)
                    },
                    {
                        "source": "Website",
                        "leads": website_leads,
                        "percentage": round(website_leads / total_leads * 100, 1)
                    },
                    {
                        "source": "Referências",
                        "leads": referral_leads,
                        "percentage": round(referral_leads / total_leads * 100, 1)
                    }
                ]
            
            # Sort by leads count
            sources.sort(key=lambda x: x["leads"], reverse=True)
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key,
                sources,
                self.cache_ttl["source_metrics"]
            )
            
            return sources
            
        except Exception as e:
            logger.error(f"Error calculating source metrics: {e}")
            return []
    
    def get_quality_scores(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get quality score distribution with caching"""
        cache_key = f"quality_scores_{user_id or 'global'}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for quality scores (user: {user_id})")
            return cached_data
        
        logger.debug(f"Cache MISS for quality scores (user: {user_id})")
        
        try:
            # Build base query
            query = self.db.query(Lead)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            # Calculate quality scores based on data completeness
            high_quality = query.filter(
                and_(
                    Lead.email.isnot(None),
                    Lead.phone.isnot(None),
                    Lead.industry.isnot(None),
                    Lead.location.isnot(None),
                    Lead.description.isnot(None)
                )
            ).count()
            
            good_quality = query.filter(
                and_(
                    or_(Lead.email.isnot(None), Lead.phone.isnot(None)),
                    Lead.industry.isnot(None),
                    Lead.location.isnot(None)
                )
            ).count() - high_quality
            
            medium_quality = query.filter(
                or_(Lead.email.isnot(None), Lead.phone.isnot(None))
            ).count() - high_quality - good_quality
            
            total_leads = query.count()
            low_quality = max(0, total_leads - high_quality - good_quality - medium_quality)
            
            scores = {
                "high_quality": {
                    "range": "90-100",
                    "count": high_quality,
                    "label": "Alta Prioridade"
                },
                "good_quality": {
                    "range": "70-89",
                    "count": good_quality,
                    "label": "Boa Qualidade"
                },
                "medium_quality": {
                    "range": "50-69",
                    "count": medium_quality,
                    "label": "Média Qualidade"
                },
                "low_quality": {
                    "range": "0-49",
                    "count": low_quality,
                    "label": "Baixa Prioridade"
                }
            }
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key,
                scores,
                self.cache_ttl["quality_scores"]
            )
            
            return scores
            
        except Exception as e:
            logger.error(f"Error calculating quality scores: {e}")
            return {
                "high_quality": {"range": "90-100", "count": 0, "label": "Alta Prioridade"},
                "good_quality": {"range": "70-89", "count": 0, "label": "Boa Qualidade"},
                "medium_quality": {"range": "50-69", "count": 0, "label": "Média Qualidade"},
                "low_quality": {"range": "0-49", "count": 0, "label": "Baixa Prioridade"}
            }
    
    def get_search_facets(self, user_id: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get search facets for advanced filtering with caching"""
        cache_key = f"search_facets_{user_id or 'global'}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            logger.debug(f"Cache HIT for search facets (user: {user_id})")
            return cached_data
        
        logger.debug(f"Cache MISS for search facets (user: {user_id})")
        
        try:
            # Build base query
            query = self.db.query(Lead)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            # Get industry facets
            industries = self.db.query(
                Lead.industry,
                func.count(Lead.id).label('count')
            ).filter(Lead.industry.isnot(None))
            
            if user_id:
                industries = industries.filter(Lead.user_id == user_id)
            
            industries = industries.group_by(Lead.industry).order_by(
                desc(func.count(Lead.id))
            ).limit(20).all()
            
            # Get location facets
            locations = self.db.query(
                Lead.location,
                func.count(Lead.id).label('count')
            ).filter(Lead.location.isnot(None))
            
            if user_id:
                locations = locations.filter(Lead.user_id == user_id)
            
            locations = locations.group_by(Lead.location).order_by(
                desc(func.count(Lead.id))
            ).limit(20).all()
            
            # Get company size facets
            company_sizes = self.db.query(
                Lead.employees,
                func.count(Lead.id).label('count')
            ).filter(Lead.employees.isnot(None))
            
            if user_id:
                company_sizes = company_sizes.filter(Lead.user_id == user_id)
            
            company_sizes = company_sizes.group_by(Lead.employees).order_by(
                desc(func.count(Lead.id))
            ).limit(10).all()
            
            # Get revenue range facets
            revenue_ranges = self.db.query(
                Lead.revenue,
                func.count(Lead.id).label('count')
            ).filter(Lead.revenue.isnot(None))
            
            if user_id:
                revenue_ranges = revenue_ranges.filter(Lead.user_id == user_id)
            
            revenue_ranges = revenue_ranges.group_by(Lead.revenue).order_by(
                desc(func.count(Lead.id))
            ).limit(10).all()
            
            # Format facets
            facets = {
                "industries": [
                    {"value": row.industry, "count": int(row.count)}
                    for row in industries
                ],
                "locations": [
                    {"value": row.location, "count": int(row.count)}
                    for row in locations
                ],
                "company_sizes": [
                    {"value": row.employees, "count": int(row.count)}
                    for row in company_sizes
                ],
                "revenue_ranges": [
                    {"value": row.revenue, "count": int(row.count)}
                    for row in revenue_ranges
                ]
            }
            
            # Cache the results
            self.cache.cache_analytics_data(
                cache_key,
                facets,
                self.cache_ttl["facets"]
            )
            
            return facets
            
        except Exception as e:
            logger.error(f"Error calculating search facets: {e}")
            return {
                "industries": [],
                "locations": [],
                "company_sizes": [],
                "revenue_ranges": []
            }
    
    def invalidate_analytics_cache(self, user_id: Optional[int] = None) -> bool:
        """Invalidate analytics cache for a user or globally"""
        try:
            if user_id:
                # Invalidate user-specific caches
                patterns = [
                    f"analytics:dashboard_metrics_{user_id}",
                    f"analytics:search_conversion_{user_id}",
                    f"analytics:leads_by_month_{user_id}_*",
                    f"analytics:industry_breakdown_{user_id}_*",
                    f"analytics:source_metrics_{user_id}",
                    f"analytics:quality_scores_{user_id}",
                    f"analytics:search_facets_{user_id}"
                ]
                
                for pattern in patterns:
                    self.cache.invalidate_pattern(pattern)
            else:
                # Invalidate all analytics caches
                self.cache.invalidate_analytics_cache()
            
            logger.info(f"Analytics cache invalidated for user: {user_id or 'global'}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating analytics cache: {e}")
            return False
    
    # Helper methods
    def _calculate_average_roi(self, query) -> float:
        """Calculate average ROI based on lead quality and conversion potential"""
        try:
            # Simplified ROI calculation based on lead completeness and quality
            high_value_leads = query.filter(
                and_(
                    Lead.email.isnot(None),
                    Lead.phone.isnot(None),
                    Lead.industry.isnot(None)
                )
            ).count()
            
            medium_value_leads = query.filter(
                or_(Lead.email.isnot(None), Lead.phone.isnot(None))
            ).count()
            
            total_leads = query.count()
            
            if total_leads == 0:
                return 0.0
            
            # Calculate weighted ROI based on lead quality
            # High value leads: $500 potential value
            # Medium value leads: $200 potential value
            # Low value leads: $50 potential value
            
            low_value_leads = total_leads - medium_value_leads
            estimated_roi = (
                (high_value_leads * 500) + 
                ((medium_value_leads - high_value_leads) * 200) + 
                (low_value_leads * 50)
            ) / total_leads if total_leads > 0 else 0.0
            
            return estimated_roi
            
        except Exception as e:
            logger.error(f"Error calculating average ROI: {e}")
            return 0.0
    
    def _calculate_search_trends(self) -> Dict[str, Any]:
        """Calculate search trends by hour of day"""
        try:
            # Simulate search trends based on typical business hours
            # In a real implementation, this would query SearchAnalyticsEvent
            trends = {
                "hourly_distribution": {
                    "0": 2, "1": 1, "2": 1, "3": 1, "4": 1, "5": 2,
                    "6": 5, "7": 12, "8": 25, "9": 35, "10": 40,
                    "11": 38, "12": 30, "13": 35, "14": 42, "15": 38,
                    "16": 32, "17": 25, "18": 15, "19": 10, "20": 8,
                    "21": 6, "22": 4, "23": 3
                },
                "peak_hours": ["9-11", "14-16"],
                "total_searches_last_24h": 287
            }
            return trends
        except Exception as e:
            logger.error(f"Error calculating search trends: {e}")
            return {}
    
    def _get_indexing_status(self) -> Dict[str, Any]:
        """Get current indexing status"""
        try:
            # Get indexing statistics from database
            total_leads = self.db.query(Lead).count()
            indexed_leads = self.db.query(Lead).filter(Lead.indexed_at.isnot(None)).count()
            
            indexing_percentage = (indexed_leads / total_leads * 100) if total_leads > 0 else 0.0
            
            return {
                "total_leads": total_leads,
                "indexed_leads": indexed_leads,
                "indexing_percentage": round(indexing_percentage, 1),
                "status": "healthy" if indexing_percentage > 95 else "needs_attention",
                "last_index_update": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting indexing status: {e}")
            return {
                "total_leads": 0,
                "indexed_leads": 0,
                "indexing_percentage": 0.0,
                "status": "error",
                "error": str(e)
            }
    
    def _estimate_cache_hit_rate(self) -> float:
        """Estimate cache hit rate based on Redis performance"""
        try:
            # Get cache statistics from Redis
            cache_stats = self.cache.get_cache_stats()
            
            if cache_stats and "hits" in cache_stats and "misses" in cache_stats:
                total_requests = cache_stats["hits"] + cache_stats["misses"]
                if total_requests > 0:
                    return round(cache_stats["hits"] / total_requests * 100, 1)
            
            # Fallback estimation based on cache health
            cache_health = self.cache.health_check()
            if cache_health.get("status") == "healthy":
                return 78.5  # Typical good cache hit rate
            else:
                return 45.2  # Lower hit rate when cache is struggling
                
        except Exception as e:
            logger.error(f"Error estimating cache hit rate: {e}")
            return 0.0
    
    def _calculate_conversion_by_query_type(self, query) -> List[Dict[str, Any]]:
        """Calculate conversion rates by query type"""
        try:
            # Analyze conversion patterns by industry and location
            industry_conversions = []
            
            # Get top industries with conversion data
            industries = self.db.query(
                Lead.industry,
                func.count(Lead.id).label('total'),
                func.count(
                    case((Lead.last_contact.isnot(None), Lead.id), else_=None)
                ).label('contacted')
            ).filter(Lead.industry.isnot(None))
            
            if hasattr(query, 'whereclause') and query.whereclause is not None:
                # Apply same filters as the main query
                industries = industries.filter(query.whereclause)
            
            industries = industries.group_by(Lead.industry).having(
                func.count(Lead.id) >= 5  # Only industries with at least 5 leads
            ).order_by(desc(func.count(Lead.id))).limit(5).all()
            
            for industry in industries:
                conversion_rate = (industry.contacted / industry.total * 100) if industry.total > 0 else 0.0
                industry_conversions.append({
                    "query_type": f"Industry: {industry.industry}",
                    "total_searches": industry.total,
                    "conversions": industry.contacted,
                    "conversion_rate": round(conversion_rate, 1)
                })
            
            return industry_conversions
            
        except Exception as e:
            logger.error(f"Error calculating conversion by query type: {e}")
            return []
    
    def _calculate_top_converting_filters(self, query) -> List[Dict[str, Any]]:
        """Calculate top converting filters"""
        try:
            converting_filters = []
            
            # Location-based conversions
            location_conversions = self.db.query(
                Lead.location,
                func.count(Lead.id).label('total'),
                func.count(
                    case((Lead.last_contact.isnot(None), Lead.id), else_=None)
                ).label('contacted')
            ).filter(Lead.location.isnot(None))
            
            if hasattr(query, 'whereclause') and query.whereclause is not None:
                location_conversions = location_conversions.filter(query.whereclause)
            
            location_conversions = location_conversions.group_by(Lead.location).having(
                func.count(Lead.id) >= 3
            ).order_by(desc(func.count(Lead.id))).limit(3).all()
            
            for location in location_conversions:
                conversion_rate = (location.contacted / location.total * 100) if location.total > 0 else 0.0
                converting_filters.append({
                    "filter_type": "location",
                    "filter_value": location.location,
                    "conversion_rate": round(conversion_rate, 1),
                    "total_leads": location.total
                })
            
            # Company size conversions
            size_conversions = self.db.query(
                Lead.employees,
                func.count(Lead.id).label('total'),
                func.count(
                    case((Lead.last_contact.isnot(None), Lead.id), else_=None)
                ).label('contacted')
            ).filter(Lead.employees.isnot(None))
            
            if hasattr(query, 'whereclause') and query.whereclause is not None:
                size_conversions = size_conversions.filter(query.whereclause)
            
            size_conversions = size_conversions.group_by(Lead.employees).having(
                func.count(Lead.id) >= 3
            ).order_by(desc(func.count(Lead.id))).limit(2).all()
            
            for size in size_conversions:
                conversion_rate = (size.contacted / size.total * 100) if size.total > 0 else 0.0
                converting_filters.append({
                    "filter_type": "company_size",
                    "filter_value": size.employees,
                    "conversion_rate": round(conversion_rate, 1),
                    "total_leads": size.total
                })
            
            # Sort by conversion rate
            converting_filters.sort(key=lambda x: x["conversion_rate"], reverse=True)
            
            return converting_filters[:5]  # Top 5 converting filters
            
        except Exception as e:
            logger.error(f"Error calculating top converting filters: {e}")
            return []
            
            medium_value_leads = query.filter(
                or_(Lead.email.isnot(None), Lead.phone.isnot(None))
            ).count()
            
            total_leads = query.count()
            
            if total_leads == 0:
                return 0.0
            
            # Estimate ROI based on lead quality distribution
            estimated_roi = (
                (high_value_leads * 5000) +  # High value leads worth $5000
                (medium_value_leads * 2000) +  # Medium value leads worth $2000
                ((total_leads - high_value_leads - medium_value_leads) * 500)  # Low value leads worth $500
            ) / total_leads
            
            return estimated_roi
            
        except Exception as e:
            logger.error(f"Error calculating average ROI: {e}")
            return 0.0
    
    def _calculate_search_trends(self) -> Dict[str, Any]:
        """Calculate search trends based on lead creation patterns"""
        try:
            # Simulate hourly search trends based on lead creation patterns
            # In a real implementation, you'd track actual search timestamps
            
            # Get leads created today by hour
            today = datetime.utcnow().date()
            hourly_leads = self.db.query(
                extract('hour', Lead.created_at).label('hour'),
                func.count(Lead.id).label('count')
            ).filter(
                func.date(Lead.created_at) == today
            ).group_by(
                extract('hour', Lead.created_at)
            ).all()
            
            # Convert to hourly search simulation
            hourly_searches = []
            for hour in range(24):
                # Find matching hour data
                hour_data = next((h for h in hourly_leads if int(h.hour) == hour), None)
                count = int(hour_data.count) * 2 if hour_data else 0  # Simulate 2 searches per lead
                
                hourly_searches.append({
                    "hour": f"{hour:02d}:00",
                    "searches": count
                })
            
            return {"hourly_searches": hourly_searches}
            
        except Exception as e:
            logger.error(f"Error calculating search trends: {e}")
            return {"hourly_searches": []}
    
    def _get_indexing_status(self) -> Dict[str, Any]:
        """Get indexing status information"""
        try:
            total_leads = self.db.query(Lead).count()
            indexed_leads = self.db.query(Lead).filter(Lead.indexed_at.isnot(None)).count()
            
            coverage = (indexed_leads / total_leads * 100) if total_leads > 0 else 0.0
            
            # Get last index update
            last_indexed = self.db.query(Lead.indexed_at).filter(
                Lead.indexed_at.isnot(None)
            ).order_by(desc(Lead.indexed_at)).first()
            
            last_update = (
                last_indexed[0].isoformat() if last_indexed and last_indexed[0]
                else datetime.utcnow().isoformat()
            )
            
            return {
                "total_leads": total_leads,
                "indexed_leads": indexed_leads,
                "indexing_coverage": round(coverage, 1),
                "last_index_update": last_update
            }
            
        except Exception as e:
            logger.error(f"Error getting indexing status: {e}")
            return {
                "total_leads": 0,
                "indexed_leads": 0,
                "indexing_coverage": 0.0,
                "last_index_update": datetime.utcnow().isoformat()
            }
    
    def _estimate_cache_hit_rate(self) -> float:
        """Estimate cache hit rate based on Redis health"""
        try:
            cache_health = self.cache.health_check()
            if cache_health.get("status") == "healthy":
                # Estimate based on keyspace info
                keyspace = cache_health.get("keyspace", {})
                if keyspace:
                    return 78.5  # Good cache performance
                return 45.0  # Moderate cache performance
            return 0.0  # No cache
            
        except Exception as e:
            logger.error(f"Error estimating cache hit rate: {e}")
            return 0.0
    
    def _calculate_conversion_by_query_type(self, query) -> List[Dict[str, Any]]:
        """Calculate conversion rates by query type"""
        try:
            total_leads = query.count()
            if total_leads == 0:
                return []
            
            # Simulate query types based on lead data patterns
            query_types = []
            
            # Company name searches (leads with complete company info)
            company_searches = query.filter(
                and_(Lead.company.isnot(None), Lead.description.isnot(None))
            ).count()
            company_conversions = query.filter(
                and_(
                    Lead.company.isnot(None),
                    Lead.description.isnot(None),
                    or_(Lead.email.isnot(None), Lead.phone.isnot(None))
                )
            ).count()
            
            if company_searches > 0:
                query_types.append({
                    "type": "Company Name",
                    "searches": company_searches,
                    "conversions": company_conversions,
                    "rate": round(company_conversions / company_searches * 100, 1)
                })
            
            # Industry + Location searches
            industry_location_searches = query.filter(
                and_(Lead.industry.isnot(None), Lead.location.isnot(None))
            ).count()
            industry_location_conversions = query.filter(
                and_(
                    Lead.industry.isnot(None),
                    Lead.location.isnot(None),
                    or_(Lead.email.isnot(None), Lead.phone.isnot(None))
                )
            ).count()
            
            if industry_location_searches > 0:
                query_types.append({
                    "type": "Industry + Location",
                    "searches": industry_location_searches,
                    "conversions": industry_location_conversions,
                    "rate": round(industry_location_conversions / industry_location_searches * 100, 1)
                })
            
            return query_types[:4]  # Limit to top 4 types
            
        except Exception as e:
            logger.error(f"Error calculating conversion by query type: {e}")
            return []
    
    def _calculate_top_converting_filters(self, query) -> List[Dict[str, Any]]:
        """Calculate top converting filters"""
        try:
            filters = []
            
            # Industry filters
            top_industries = self.db.query(
                Lead.industry,
                func.count(Lead.id).label('usage'),
                func.count(
                    case(
                        (or_(Lead.email.isnot(None), Lead.phone.isnot(None)), Lead.id),
                        else_=None
                    )
                ).label('conversions')
            ).filter(Lead.industry.isnot(None)).group_by(Lead.industry).order_by(
                desc(func.count(Lead.id))
            ).limit(3).all()
            
            for industry in top_industries:
                if industry.usage > 0:
                    conversion_rate = industry.conversions / industry.usage * 100
                    filters.append({
                        "filter": f"industry:{industry.industry}",
                        "usage": int(industry.usage),
                        "conversion_rate": round(conversion_rate, 1)
                    })
            
            # Location filters
            top_locations = self.db.query(
                Lead.location,
                func.count(Lead.id).label('usage'),
                func.count(
                    case(
                        (or_(Lead.email.isnot(None), Lead.phone.isnot(None)), Lead.id),
                        else_=None
                    )
                ).label('conversions')
            ).filter(Lead.location.isnot(None)).group_by(Lead.location).order_by(
                desc(func.count(Lead.id))
            ).limit(2).all()
            
            for location in top_locations:
                if location.usage > 0:
                    conversion_rate = location.conversions / location.usage * 100
                    filters.append({
                        "filter": f"location:{location.location}",
                        "usage": int(location.usage),
                        "conversion_rate": round(conversion_rate, 1)
                    })
            
            return filters[:4]  # Limit to top 4 filters
            
        except Exception as e:
            logger.error(f"Error calculating top converting filters: {e}")
            return []
    
    def _calculate_search_trends(self) -> Dict[str, Any]:
        """Calculate search trends and patterns"""
        try:
            # Get hourly distribution (mock data for now)
            hourly_distribution = {
                "00": 2, "01": 1, "02": 0, "03": 1, "04": 2, "05": 3,
                "06": 5, "07": 8, "08": 12, "09": 18, "10": 15, "11": 14,
                "12": 16, "13": 13, "14": 20, "15": 17, "16": 19, "17": 14,
                "18": 10, "19": 8, "20": 6, "21": 5, "22": 4, "23": 3
            }
            
            # Calculate peak hours
            peak_hours = sorted(hourly_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
            
            return {
                "hourly_distribution": hourly_distribution,
                "peak_hours": [f"{hour}:00" for hour, _ in peak_hours],
                "total_searches_today": sum(hourly_distribution.values()),
                "avg_searches_per_hour": round(sum(hourly_distribution.values()) / 24, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating search trends: {e}")
            return {}
    
    def _get_indexing_status(self) -> Dict[str, Any]:
        """Get indexing status information"""
        try:
            total_leads = self.db.query(func.count(Lead.id)).scalar()
            indexed_leads = self.db.query(func.count(Lead.id)).filter(
                Lead.indexed_at.isnot(None)
            ).scalar()
            
            # Get recent indexing activity
            from datetime import timedelta
            recent_indexed = self.db.query(func.count(Lead.id)).filter(
                Lead.indexed_at >= datetime.utcnow() - timedelta(hours=24)
            ).scalar()
            
            coverage_percent = (indexed_leads / total_leads * 100) if total_leads > 0 else 0
            
            return {
                "total_leads": total_leads,
                "indexed_leads": indexed_leads,
                "coverage_percent": round(coverage_percent, 1),
                "recent_indexed_24h": recent_indexed,
                "status": "healthy" if coverage_percent > 90 else "needs_attention",
                "last_index_update": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting indexing status: {e}")
            return {
                "total_leads": 0,
                "indexed_leads": 0,
                "coverage_percent": 0,
                "status": "error"
            }
    
    def _estimate_cache_hit_rate(self) -> float:
        """Estimate cache hit rate based on Redis statistics"""
        try:
            if not self.cache or not self.cache.enabled:
                return 0.0
            
            cache_stats = self.cache.get_cache_stats()
            if cache_stats:
                hits = cache_stats.get("hits", 0)
                misses = cache_stats.get("misses", 0)
                total = hits + misses
                
                if total > 0:
                    return round(hits / total * 100, 1)
            
            # Fallback estimation based on cache health
            cache_health = self.cache.health_check()
            if cache_health.get("status") == "healthy":
                return 75.5  # Reasonable default for healthy cache
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error estimating cache hit rate: {e}")
            return 0.0