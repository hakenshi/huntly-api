-- Test data for Huntly Database
-- Sample data for development and testing

-- Insert test user
INSERT INTO users (email, hashed_password, is_active) VALUES 
('test@huntly.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6hsxq5/Qe2', true)
ON CONFLICT (email) DO NOTHING;

-- Get the test user ID
DO $$
DECLARE
    test_user_id INTEGER;
BEGIN
    SELECT id INTO test_user_id FROM users WHERE email = 'test@huntly.com';
    
    -- Insert sample leads
    INSERT INTO leads (user_id, company, contact, email, phone, website, industry, location, revenue, employees, description, keywords, score, status, priority) VALUES 
    (test_user_id, 'TechCorp Solutions', 'João Silva', 'joao@techcorp.com', '+55 11 99999-1234', 'https://techcorp.com', 'Tecnologia', 'São Paulo, SP', 'R$ 5M - R$ 20M', '51-200', 'Empresa de desenvolvimento de software especializada em soluções empresariais', ARRAY['software', 'desenvolvimento', 'tecnologia'], 85, 'Novo', 'Alta'),
    (test_user_id, 'E-commerce Plus', 'Maria Santos', 'maria@ecommerceplus.com', '+55 21 88888-5678', 'https://ecommerceplus.com', 'E-commerce', 'Rio de Janeiro, RJ', 'R$ 1M - R$ 5M', '11-50', 'Plataforma de e-commerce para pequenas e médias empresas', ARRAY['ecommerce', 'vendas', 'digital'], 78, 'Contatado', 'Média'),
    (test_user_id, 'HealthTech Innovations', 'Dr. Carlos Oliveira', 'carlos@healthtech.com', '+55 11 77777-9012', 'https://healthtech.com', 'Saúde', 'São Paulo, SP', 'R$ 10M - R$ 50M', '101-500', 'Startup de tecnologia aplicada à saúde, desenvolvendo soluções de telemedicina', ARRAY['saúde', 'telemedicina', 'inovação'], 92, 'Qualificado', 'Alta'),
    (test_user_id, 'EduLearn Platform', 'Ana Costa', 'ana@edulearn.com', '+55 31 66666-3456', 'https://edulearn.com', 'Educação', 'Belo Horizonte, MG', 'R$ 2M - R$ 10M', '21-100', 'Plataforma de educação online com foco em cursos profissionalizantes', ARRAY['educação', 'online', 'cursos'], 73, 'Em Negociação', 'Média'),
    (test_user_id, 'FinTech Brasil', 'Roberto Lima', 'roberto@fintechbr.com', '+55 11 55555-7890', 'https://fintechbr.com', 'Financeiro', 'São Paulo, SP', 'R$ 20M - R$ 100M', '201-500', 'Fintech especializada em soluções de pagamento digital para empresas', ARRAY['fintech', 'pagamentos', 'digital'], 88, 'Proposta Enviada', 'Alta'),
    (test_user_id, 'GreenEnergy Solutions', 'Fernanda Alves', 'fernanda@greenenergy.com', '+55 48 44444-2345', 'https://greenenergy.com', 'Energia', 'Florianópolis, SC', 'R$ 15M - R$ 75M', '151-300', 'Empresa de energia renovável focada em soluções solares para empresas', ARRAY['energia', 'sustentabilidade', 'solar'], 81, 'Convertido', 'Alta'),
    (test_user_id, 'LogiTrans Cargo', 'Pedro Souza', 'pedro@logitrans.com', '+55 19 33333-6789', 'https://logitrans.com', 'Logística', 'Campinas, SP', 'R$ 8M - R$ 30M', '76-150', 'Empresa de logística e transporte com tecnologia de rastreamento avançada', ARRAY['logística', 'transporte', 'rastreamento'], 69, 'Perdido', 'Baixa'),
    (test_user_id, 'FoodTech Delivery', 'Juliana Ferreira', 'juliana@foodtech.com', '+55 85 22222-4567', 'https://foodtech.com', 'Alimentação', 'Fortaleza, CE', 'R$ 3M - R$ 15M', '31-75', 'Plataforma de delivery de comida com foco em restaurantes locais', ARRAY['food', 'delivery', 'restaurantes'], 76, 'Novo', 'Média'),
    (test_user_id, 'TravelTech Adventures', 'Marcos Pereira', 'marcos@traveltech.com', '+55 71 11111-8901', 'https://traveltech.com', 'Turismo', 'Salvador, BA', 'R$ 4M - R$ 18M', '41-80', 'Agência de viagens online especializada em turismo de aventura', ARRAY['turismo', 'viagens', 'aventura'], 72, 'Contatado', 'Média'),
    (test_user_id, 'PropTech Imóveis', 'Carla Rodrigues', 'carla@proptech.com', '+55 61 99999-0123', 'https://proptech.com', 'Imobiliário', 'Brasília, DF', 'R$ 12M - R$ 40M', '91-200', 'Plataforma digital para compra e venda de imóveis com realidade virtual', ARRAY['imóveis', 'proptech', 'realidade virtual'], 84, 'Qualificado', 'Alta')
    ON CONFLICT DO NOTHING;
    
    -- Insert sample user preferences
    INSERT INTO user_preferences (user_id, preferred_industries, preferred_locations, company_size_range, revenue_range) VALUES 
    (test_user_id, ARRAY['Tecnologia', 'Saúde', 'Financeiro'], ARRAY['São Paulo, SP', 'Rio de Janeiro, RJ'], '51-200', 'R$ 5M - R$ 50M')
    ON CONFLICT (user_id) DO UPDATE SET
        preferred_industries = EXCLUDED.preferred_industries,
        preferred_locations = EXCLUDED.preferred_locations,
        company_size_range = EXCLUDED.company_size_range,
        revenue_range = EXCLUDED.revenue_range;
    
    -- Insert sample campaign
    INSERT INTO campaigns (user_id, name, description, status) VALUES 
    (test_user_id, 'Campanha Q4 2024', 'Campanha focada em empresas de tecnologia para o último trimestre', 'Ativa')
    ON CONFLICT DO NOTHING;
    
END $$;