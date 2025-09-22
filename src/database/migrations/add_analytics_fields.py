"""
Migration: Add analytics tracking fields to leads table
"""

from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade(connection):
    """Add analytics tracking fields to leads table"""
    try:
        # Add analytics fields to leads table
        connection.execute(text("""
            ALTER TABLE leads 
            ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS contact_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS conversion_score FLOAT DEFAULT 0.0
        """))
        
        # Create indexes for analytics queries
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leads_view_count ON leads(view_count);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leads_contact_count ON leads(contact_count);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_leads_conversion_score ON leads(conversion_score);
        """))
        
        logger.info("Successfully added analytics fields to leads table")
        return True
        
    except Exception as e:
        logger.error(f"Error adding analytics fields: {e}")
        return False

def downgrade(connection):
    """Remove analytics tracking fields from leads table"""
    try:
        # Remove indexes
        connection.execute(text("DROP INDEX IF EXISTS idx_leads_view_count"))
        connection.execute(text("DROP INDEX IF EXISTS idx_leads_contact_count"))
        connection.execute(text("DROP INDEX IF EXISTS idx_leads_conversion_score"))
        
        # Remove columns
        connection.execute(text("""
            ALTER TABLE leads 
            DROP COLUMN IF EXISTS view_count,
            DROP COLUMN IF EXISTS contact_count,
            DROP COLUMN IF EXISTS conversion_score
        """))
        
        logger.info("Successfully removed analytics fields from leads table")
        return True
        
    except Exception as e:
        logger.error(f"Error removing analytics fields: {e}")
        return False