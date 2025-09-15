-- Usuários
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) DEFAULT 'starter',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leads
CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    website VARCHAR(255),
    industry VARCHAR(100),
    company_size VARCHAR(50),
    revenue VARCHAR(50),
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'new',
    score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Campanhas de busca
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    filters JSONB,
    status VARCHAR(50) DEFAULT 'active',
    leads_found INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analytics
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value INTEGER NOT NULL,
    date DATE DEFAULT CURRENT_DATE
);
