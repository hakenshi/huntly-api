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

def run_migrations():
    """Run all database migrations"""
    try:
        create_search_indexes()
        logging.info("All migrations completed successfully")
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        # Don't raise the error to prevent startup failure
        # The application can still work without full-text search
        logging.warning("Continuing startup without full-text search features")
        return False
    return True