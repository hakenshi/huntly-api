"""
Database migration utilities for Huntly
"""
from sqlalchemy import text
from database.connection import engine
import logging

def create_search_indexes():
    """Create PostgreSQL full-text search indexes"""
    
    migrations = [
        # Create tsvector index for company names
        """
        UPDATE leads SET search_vector = to_tsvector('english', 
            coalesce(company, '') || ' ' || 
            coalesce(description, '') || ' ' || 
            coalesce(industry, '') || ' ' ||
            array_to_string(coalesce(keywords, ARRAY[]::text[]), ' ')
        ) WHERE search_vector IS NULL;
        """,
        
        # Create function to automatically update search_vector
        """
        CREATE OR REPLACE FUNCTION update_lead_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.company, '') || ' ' ||
                coalesce(NEW.description, '') || ' ' ||
                coalesce(NEW.industry, '') || ' ' ||
                array_to_string(coalesce(NEW.keywords, ARRAY[]::text[]), ' ')
            );
            NEW.updated_at := NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        # Create trigger to update search_vector automatically
        """
        DROP TRIGGER IF EXISTS update_lead_search_vector_trigger ON leads;
        CREATE TRIGGER update_lead_search_vector_trigger
            BEFORE INSERT OR UPDATE ON leads
            FOR EACH ROW EXECUTE FUNCTION update_lead_search_vector();
        """,
        
        # Create GIN index for full-text search
        """
        CREATE INDEX IF NOT EXISTS idx_leads_search_vector 
        ON leads USING gin(search_vector);
        """,
        
        # Create additional performance indexes
        """
        CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
        CREATE INDEX IF NOT EXISTS idx_campaigns_next_execution ON campaigns(next_execution);
        """
    ]
    
    with engine.connect() as conn:
        for migration in migrations:
            try:
                conn.execute(text(migration))
                conn.commit()
                logging.info(f"Migration executed successfully")
            except Exception as e:
                logging.error(f"Migration failed: {e}")
                conn.rollback()
                raise

def run_migrations():
    """Run all database migrations"""
    try:
        create_search_indexes()
        logging.info("All migrations completed successfully")
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        raise