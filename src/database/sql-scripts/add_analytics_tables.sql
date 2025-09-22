-- Add analytics tables for search performance tracking
-- This migration adds tables to track search analytics and lead interactions

-- Search Analytics Events Table
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

-- Lead Interaction Events Table
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

-- Create indexes for analytics performance
CREATE INDEX IF NOT EXISTS idx_search_analytics_user_created 
ON search_analytics_events(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_search_analytics_query 
ON search_analytics_events USING gin(to_tsvector('english', query_text));

CREATE INDEX IF NOT EXISTS idx_lead_interactions_user_created 
ON lead_interaction_events(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_lead_interactions_lead_type 
ON lead_interaction_events(lead_id, interaction_type);

-- Add analytics-related columns to existing tables if they don't exist
ALTER TABLE leads 
ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS contact_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS conversion_score FLOAT DEFAULT 0.0;

-- Create indexes for new lead analytics columns
CREATE INDEX IF NOT EXISTS idx_leads_view_count ON leads(view_count);
CREATE INDEX IF NOT EXISTS idx_leads_contact_count ON leads(contact_count);
CREATE INDEX IF NOT EXISTS idx_leads_conversion_score ON leads(conversion_score);

-- Add search tracking to campaigns
ALTER TABLE campaigns 
ADD COLUMN IF NOT EXISTS total_searches INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS avg_response_time_ms INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS cache_hit_rate FLOAT DEFAULT 0.0;

COMMIT;