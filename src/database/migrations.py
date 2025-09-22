"""
Database migration utilities for Huntly
"""
from sqlalchemy import text
from .connection import engine
import logging

def create_search_indexes():
    """Create PostgreSQL full-text search indexes"""
    
    migrations = [
        # First, ensure the search_vector column exists
        """
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS search_vector tsvector;
        """,
        
        # Create basic performance indexes first
        """
        CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);
        """,
        
        # Create function to automatically update search_vector (simplified version)
        """
        CREATE OR REPLACE FUNCTION update_lead_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.company, '') || ' ' ||
                coalesce(NEW.description, '') || ' ' ||
                coalesce(NEW.industry, '')
            );
            NEW.updated_at := NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        # Drop existing trigger if it exists
        """
        DROP TRIGGER IF EXISTS update_lead_search_vector_trigger ON leads;
        """,
        
        # Create trigger to update search_vector automatically
        """
        CREATE TRIGGER update_lead_search_vector_trigger
            BEFORE INSERT OR UPDATE ON leads
            FOR EACH ROW EXECUTE FUNCTION update_lead_search_vector();
        """,
        
        # Update existing records with search_vector
        """
        UPDATE leads SET search_vector = to_tsvector('english', 
            coalesce(company, '') || ' ' || 
            coalesce(description, '') || ' ' || 
            coalesce(industry, '')
        ) WHERE search_vector IS NULL;
        """,
        
        # Create GIN index for full-text search
        """
        CREATE INDEX IF NOT EXISTS idx_leads_search_vector 
        ON leads USING gin(search_vector);
        """
    ]
    
    with engine.connect() as conn:
        for i, migration in enumerate(migrations):
            try:
                # Skip empty migrations
                if not migration.strip():
                    continue
                    
                conn.execute(text(migration))
                conn.commit()
                logging.info(f"Migration {i+1}/{len(migrations)} executed successfully")
            except Exception as e:
                logging.error(f"Migration {i+1}/{len(migrations)} failed: {e}")
                logging.error(f"Failed migration SQL: {migration[:200]}...")
                conn.rollback()
                
                # For some errors, we can continue (like if index already exists)
                if "already exists" in str(e).lower() or "does not exist" in str(e).lower():
                    logging.warning(f"Skipping migration {i+1} - object already exists or doesn't exist")
                    continue
                else:
                    raise

def create_analytics_tables():
    """Create analytics tables for search performance tracking"""
    
    migrations = [
        # Search Analytics Events Table
        """
        CREATE TABLE IF NOT EXISTS search_analytics_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            
            -- Search details
            query_text TEXT,
            filters_applied JSONB,
            results_count INTEGER DEFAULT 0,
            response_time_ms INTEGER,
            
            -- User interaction
            clicked_results INTEGER DEFAULT 0,
            contacted_leads INTEGER DEFAULT 0,
            converted_leads INTEGER DEFAULT 0,
            
            -- Cache performance
            cache_hit VARCHAR(10) DEFAULT 'miss',
            
            -- Metadata
            session_id VARCHAR(255),
            user_agent VARCHAR(500),
            ip_address VARCHAR(45),
            
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        
        # Lead Interaction Events Table
        """
        CREATE TABLE IF NOT EXISTS lead_interaction_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            lead_id INTEGER REFERENCES leads(id),
            
            -- Interaction type
            interaction_type VARCHAR(50), -- view, contact, email, call, convert
            interaction_data JSONB,
            
            -- Source of interaction
            source_search_query TEXT,
            source_campaign_id INTEGER REFERENCES campaigns(id),
            
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        
        # Create indexes for analytics performance
        """
        CREATE INDEX IF NOT EXISTS idx_search_analytics_user_created 
        ON search_analytics_events(user_id, created_at);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_search_analytics_query 
        ON search_analytics_events USING gin(to_tsvector('english', query_text));
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_lead_interactions_user_created 
        ON lead_interaction_events(user_id, created_at);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_lead_interactions_lead_type 
        ON lead_interaction_events(lead_id, interaction_type);
        """,
        
        # Add analytics-related columns to existing tables
        """
        ALTER TABLE leads 
        ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS contact_count INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS conversion_score FLOAT DEFAULT 0.0;
        """,
        
        # Create indexes for new lead analytics columns
        """
        CREATE INDEX IF NOT EXISTS idx_leads_view_count ON leads(view_count);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_leads_contact_count ON leads(contact_count);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_leads_conversion_score ON leads(conversion_score);
        """,
        
        # Add search tracking to campaigns
        """
        ALTER TABLE campaigns 
        ADD COLUMN IF NOT EXISTS total_searches INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS avg_response_time_ms INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS cache_hit_rate FLOAT DEFAULT 0.0;
        """
    ]
    
    with engine.connect() as conn:
        for i, migration in enumerate(migrations):
            try:
                # Skip empty migrations
                if not migration.strip():
                    continue
                    
                conn.execute(text(migration))
                conn.commit()
                logging.info(f"Analytics migration {i+1}/{len(migrations)} executed successfully")
            except Exception as e:
                logging.error(f"Analytics migration {i+1}/{len(migrations)} failed: {e}")
                logging.error(f"Failed migration SQL: {migration[:200]}...")
                conn.rollback()
                
                # For some errors, we can continue (like if table already exists)
                if "already exists" in str(e).lower() or "does not exist" in str(e).lower():
                    logging.warning(f"Skipping analytics migration {i+1} - object already exists or doesn't exist")
                    continue
                else:
                    raise

def run_migrations():
    """Run all database migrations"""
    try:
        create_search_indexes()
        create_analytics_tables()
        logging.info("All migrations completed successfully")
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        # Don't raise the error to prevent startup failure
        # The application can still work without full-text search
        logging.warning("Continuing startup without full-text search features")
        return False
    return True