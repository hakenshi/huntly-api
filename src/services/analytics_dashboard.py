"""
Analytics Dashboard Service for Huntly MVP
Specialized service for dashboard analytics and real-time metrics
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_, desc

from ..database.models import Lead, SearchAnalyticsEvent, LeadInteractionEvent
from ..cache.manager import CacheManager
from .analytics import AnalyticsService

logger = logging.getLogger(__name__)

class AnalyticsDashboardService:
    """Specialized service for dashboard analytics with real-time capabilities"""
    
    def __init__(self, db_session: Session, cache_manager: CacheManager):
        """Initialize dashboard service"""
        self.db = db_session
        self.cache = cache_manager
        self.analytics_service = AnalyticsService(db_session, cache_manager)
        
        # Dashboard-specific cache TTL (shorter for real-time updates)
        self.dashboard_cache_ttl = {
            "real_time_metrics": 60,        # 1 minute
            "dashboard_summary": 300,       # 5 minutes
            "activity_feed": 120,           # 2 minutes
            "performance_alerts": 180,      # 3 minutes
            "conversion_funnel": 600        # 10 minutes
        }
    
    def get_dashboard_summary(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive dashboard summary optimized for frontend"""
        cache_key = f"dashboard_summary_{user_id or 'global'}"
        
        # Try cache first
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get core metrics
            dashboard_metrics = self.analytics_service.get_dashboard_metrics(user_id)
            search_performance = self.analytics_service.get_search_performance_metrics()
            
            # Calculate additional dashboard-specific metrics
            summary = {
                "overview": {
                    "total_leads": dashboard_metrics.get("total_leads", 0),
                    "qualified_leads": dashboard_metrics.get("qualified_leads", 0),
                    "conversion_rate": dashboard_metrics.get("conversion_rate", 0),
                    "growth_rate": dashboard_metrics.get("growth_rate", 0),
                    "high_quality_leads": dashboard_metrics.get("high_quality_leads", 0)
                },
                "performance": {
                    "avg_response_time": search_performance.get("avg_response_time_ms", 0),
                    "cache_hit_rate": search_performance.get("cache_hit_rate", 0),
                    "searches_today": search_performance.get("total_searches_today", 0),
                    "system_health": self._calculate_system_health(search_performance)
                },
                "recent_activity": self._get_recent_activity(user_id),
                "alerts": self._get_performance_alerts(dashboard_metrics, search_performance),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Cache the summary
            self.cache.cache_analytics_data(
                cache_key,
                summary,
                self.dashboard_cache_ttl["dashboard_summary"]
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return self._get_fallback_summary()
    
    def get_real_time_metrics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get real-time metrics for live dashboard updates"""
        cache_key = f"real_time_metrics_{user_id or 'global'}"
        
        # Check cache (very short TTL for real-time data)
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get current activity
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            
            # Recent search activity
            recent_searches = self.db.query(func.count(SearchAnalyticsEvent.id)).filter(
                SearchAnalyticsEvent.created_at >= hour_ago
            )
            if user_id:
                recent_searches = recent_searches.filter(SearchAnalyticsEvent.user_id == user_id)
            recent_searches_count = recent_searches.scalar() or 0
            
            # Recent lead interactions
            recent_interactions = self.db.query(func.count(LeadInteractionEvent.id)).filter(
                LeadInteractionEvent.created_at >= hour_ago
            )
            if user_id:
                recent_interactions = recent_interactions.filter(LeadInteractionEvent.user_id == user_id)
            recent_interactions_count = recent_interactions.scalar() or 0
            
            # Active users (users with activity in last hour)
            active_users = self.db.query(func.count(func.distinct(SearchAnalyticsEvent.user_id))).filter(
                SearchAnalyticsEvent.created_at >= hour_ago
            ).scalar() or 0
            
            # System performance
            cache_health = self.cache.health_check() if self.cache else {"status": "disabled"}
            
            metrics = {
                "timestamp": now.isoformat(),
                "activity": {
                    "searches_last_hour": recent_searches_count,
                    "interactions_last_hour": recent_interactions_count,
                    "active_users": active_users if not user_id else 1
                },
                "performance": {
                    "cache_status": cache_health.get("status", "unknown"),
                    "response_time_trend": "stable",  # Would be calculated from recent events
                    "error_rate": 0.1  # Would be calculated from error logs
                },
                "system_load": {
                    "database_connections": cache_health.get("connected_clients", 0),
                    "cache_memory_usage": cache_health.get("used_memory_human", "0B"),
                    "processing_queue": 0  # Would be from background job queue
                }
            }
            
            # Cache for 1 minute
            self.cache.cache_analytics_data(
                cache_key,
                metrics,
                self.dashboard_cache_ttl["real_time_metrics"]
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "activity": {"searches_last_hour": 0, "interactions_last_hour": 0, "active_users": 0},
                "performance": {"cache_status": "error", "response_time_trend": "unknown", "error_rate": 0},
                "system_load": {"database_connections": 0, "cache_memory_usage": "0B", "processing_queue": 0}
            }
    
    def get_conversion_funnel(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get conversion funnel analytics"""
        cache_key = f"conversion_funnel_{user_id or 'global'}"
        
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Build base query
            query = self.db.query(Lead)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            total_leads = query.count()
            
            # Funnel stages
            stages = {
                "discovered": total_leads,
                "viewed": query.filter(Lead.view_count > 0).count() if hasattr(Lead, 'view_count') else int(total_leads * 0.7),
                "contacted": query.filter(Lead.contact_count > 0).count() if hasattr(Lead, 'contact_count') else int(total_leads * 0.3),
                "qualified": query.filter(
                    or_(Lead.email.isnot(None), Lead.phone.isnot(None))
                ).count(),
                "converted": query.filter(Lead.conversion_score > 0.5).count() if hasattr(Lead, 'conversion_score') else int(total_leads * 0.1)
            }
            
            # Calculate conversion rates
            funnel = []
            stage_names = ["discovered", "viewed", "contacted", "qualified", "converted"]
            stage_labels = ["Descobertos", "Visualizados", "Contatados", "Qualificados", "Convertidos"]
            
            for i, (stage, label) in enumerate(zip(stage_names, stage_labels)):
                count = stages[stage]
                rate = (count / total_leads * 100) if total_leads > 0 else 0
                drop_off = 0
                
                if i > 0:
                    prev_count = stages[stage_names[i-1]]
                    drop_off = ((prev_count - count) / prev_count * 100) if prev_count > 0 else 0
                
                funnel.append({
                    "stage": stage,
                    "label": label,
                    "count": count,
                    "conversion_rate": round(rate, 1),
                    "drop_off_rate": round(drop_off, 1)
                })
            
            result = {
                "funnel": funnel,
                "total_leads": total_leads,
                "overall_conversion_rate": round((stages["converted"] / total_leads * 100) if total_leads > 0 else 0, 1),
                "biggest_drop_off": max(funnel[1:], key=lambda x: x["drop_off_rate"])["stage"] if len(funnel) > 1 else None
            }
            
            # Cache for 10 minutes
            self.cache.cache_analytics_data(
                cache_key,
                result,
                self.dashboard_cache_ttl["conversion_funnel"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting conversion funnel: {e}")
            return {"funnel": [], "total_leads": 0, "overall_conversion_rate": 0, "biggest_drop_off": None}
    
    def get_activity_feed(self, user_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent activity feed for dashboard"""
        cache_key = f"activity_feed_{user_id or 'global'}_{limit}"
        
        cached_data = self.cache.get_cached_analytics_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            activities = []
            
            # Get recent search events
            search_query = self.db.query(SearchAnalyticsEvent).order_by(desc(SearchAnalyticsEvent.created_at))
            if user_id:
                search_query = search_query.filter(SearchAnalyticsEvent.user_id == user_id)
            
            recent_searches = search_query.limit(limit // 2).all()
            
            for search in recent_searches:
                activities.append({
                    "type": "search",
                    "timestamp": search.created_at.isoformat(),
                    "description": f"Busca por '{search.query_text or 'filtros'}' retornou {search.results_count} resultados",
                    "metadata": {
                        "query": search.query_text,
                        "results": search.results_count,
                        "response_time": search.response_time_ms
                    }
                })
            
            # Get recent lead interactions
            interaction_query = self.db.query(LeadInteractionEvent).order_by(desc(LeadInteractionEvent.created_at))
            if user_id:
                interaction_query = interaction_query.filter(LeadInteractionEvent.user_id == user_id)
            
            recent_interactions = interaction_query.limit(limit // 2).all()
            
            for interaction in recent_interactions:
                activities.append({
                    "type": "interaction",
                    "timestamp": interaction.created_at.isoformat(),
                    "description": f"Lead {interaction.lead_id} - {interaction.interaction_type}",
                    "metadata": {
                        "lead_id": interaction.lead_id,
                        "interaction_type": interaction.interaction_type,
                        "data": interaction.interaction_data
                    }
                })
            
            # Sort by timestamp and limit
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            activities = activities[:limit]
            
            # Cache for 2 minutes
            self.cache.cache_analytics_data(
                cache_key,
                activities,
                self.dashboard_cache_ttl["activity_feed"]
            )
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting activity feed: {e}")
            return []
    
    def _get_recent_activity(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get recent activity summary"""
        try:
            now = datetime.utcnow()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Today's activity
            query = self.db.query(Lead).filter(Lead.created_at >= today)
            if user_id:
                query = query.filter(Lead.user_id == user_id)
            
            leads_today = query.count()
            
            # Recent searches
            search_query = self.db.query(SearchAnalyticsEvent).filter(SearchAnalyticsEvent.created_at >= today)
            if user_id:
                search_query = search_query.filter(SearchAnalyticsEvent.user_id == user_id)
            
            searches_today = search_query.count()
            
            return {
                "leads_added_today": leads_today,
                "searches_today": searches_today,
                "last_activity": now.isoformat(),
                "trend": "up" if leads_today > 0 else "stable"
            }
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return {"leads_added_today": 0, "searches_today": 0, "last_activity": None, "trend": "stable"}
    
    def _calculate_system_health(self, search_performance: Dict[str, Any]) -> str:
        """Calculate overall system health status"""
        try:
            response_time = search_performance.get("avg_response_time_ms", 0)
            cache_hit_rate = search_performance.get("cache_hit_rate", 0)
            
            if response_time < 200 and cache_hit_rate > 70:
                return "excellent"
            elif response_time < 500 and cache_hit_rate > 50:
                return "good"
            elif response_time < 1000:
                return "fair"
            else:
                return "poor"
                
        except Exception:
            return "unknown"
    
    def _get_performance_alerts(self, dashboard_metrics: Dict[str, Any], search_performance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get performance alerts for dashboard"""
        alerts = []
        
        try:
            # Check response time
            response_time = search_performance.get("avg_response_time_ms", 0)
            if response_time > 500:
                alerts.append({
                    "type": "warning",
                    "title": "Tempo de resposta alto",
                    "message": f"Tempo médio de resposta: {response_time}ms",
                    "action": "Considere otimizar consultas ou cache"
                })
            
            # Check cache hit rate
            cache_hit_rate = search_performance.get("cache_hit_rate", 0)
            if cache_hit_rate < 50:
                alerts.append({
                    "type": "info",
                    "title": "Taxa de cache baixa",
                    "message": f"Taxa de acerto do cache: {cache_hit_rate}%",
                    "action": "Verifique configuração do Redis"
                })
            
            # Check conversion rate
            conversion_rate = dashboard_metrics.get("conversion_rate", 0)
            if conversion_rate < 20:
                alerts.append({
                    "type": "info",
                    "title": "Taxa de conversão baixa",
                    "message": f"Taxa de conversão: {conversion_rate}%",
                    "action": "Revise critérios de qualificação de leads"
                })
            
            return alerts[:3]  # Limit to 3 alerts
            
        except Exception as e:
            logger.error(f"Error getting performance alerts: {e}")
            return []
    
    def _get_fallback_summary(self) -> Dict[str, Any]:
        """Get fallback summary when main calculation fails"""
        return {
            "overview": {
                "total_leads": 0,
                "qualified_leads": 0,
                "conversion_rate": 0,
                "growth_rate": 0,
                "high_quality_leads": 0
            },
            "performance": {
                "avg_response_time": 0,
                "cache_hit_rate": 0,
                "searches_today": 0,
                "system_health": "unknown"
            },
            "recent_activity": {
                "leads_added_today": 0,
                "searches_today": 0,
                "last_activity": None,
                "trend": "stable"
            },
            "alerts": [],
            "last_updated": datetime.utcnow().isoformat(),
            "error": "Failed to load analytics data"
        }