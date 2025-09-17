"""
Script para popular o banco de dados com leads de exemplo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.database.connection import SessionLocal
from src.database.models import Lead, User
from src.cache.manager import CacheManager
from src.cache.config import get_redis_client
from src.search.indexer import LeadIndexer
from datetime import datetime, timedelta
import random

# Dados de exemplo realistas para empresas brasileiras
SAMPLE_LEADS = [
    {
        "company": "TechInova Solutions",
        "contact": "Carlos Silva",
        "email": "carlos@techinova.com.br",
        "phone": "(11) 99999-9999",
        "website": "https://techinova.com.br",
        "industry": "Tecnologia",
        "location": "São Paulo, SP",
        "revenue": "R$ 2-5M",
        "employees": "50-100",
        "description": "Empresa de tecnologia especializada em soluções SaaS para e-commerce. Desenvolve plataformas de gestão empresarial com foco em automação de processos.",
        "keywords": ["saas", "ecommerce", "automação", "gestão", "tecnologia"]
    },
    {
        "company": "EcoCommerce Brasil",
        "contact": "Ana Santos",
        "email": "ana@ecocommerce.com.br",
        "phone": "(21) 88888-8888",
        "website": "https://ecocommerce.com.br",
        "industry": "E-commerce",
        "location": "Rio de Janeiro, RJ",
        "revenue": "R$ 1-2M",
        "employees": "20-50",
        "description": "Plataforma de e-commerce sustentável focada em produtos ecológicos. Conecta consumidores conscientes com marcas sustentáveis.",
        "keywords": ["ecommerce", "sustentabilidade", "marketplace", "produtos ecológicos"]
    },
    {
        "company": "FinTech Inovadora",
        "contact": "Roberto Lima",
        "email": "roberto@fintechinova.com.br",
        "phone": "(11) 77777-7777",
        "website": "https://fintechinova.com.br",
        "industry": "Financeiro",
        "location": "São Paulo, SP",
        "revenue": "R$ 5-10M",
        "employees": "100-200",
        "description": "Startup fintech que oferece soluções de pagamento digital e crédito para pequenas e médias empresas. Foco em inclusão financeira.",
        "keywords": ["fintech", "pagamentos", "crédito", "pme", "inclusão financeira"]
    },
    {
        "company": "HealthTech Medicina",
        "contact": "Dra. Maria Oliveira",
        "email": "maria@healthtech.com.br",
        "phone": "(11) 66666-6666",
        "website": "https://healthtech.com.br",
        "industry": "Saúde",
        "location": "São Paulo, SP",
        "revenue": "R$ 3-5M",
        "employees": "30-50",
        "description": "Plataforma de telemedicina e gestão hospitalar. Oferece consultas online e sistemas de prontuário eletrônico.",
        "keywords": ["telemedicina", "saúde digital", "prontuário eletrônico", "consultas online"]
    },
    {
        "company": "EduTech Learning",
        "contact": "Prof. João Costa",
        "email": "joao@edutech.com.br",
        "phone": "(11) 55555-5555",
        "website": "https://edutech.com.br",
        "industry": "Educação",
        "location": "São Paulo, SP",
        "revenue": "R$ 1-3M",
        "employees": "15-30",
        "description": "Plataforma de ensino online com foco em cursos técnicos e profissionalizantes. Utiliza IA para personalização do aprendizado.",
        "keywords": ["educação", "ensino online", "cursos técnicos", "inteligência artificial"]
    },
    {
        "company": "AgriTech Sustentável",
        "contact": "Fernando Campos",
        "email": "fernando@agritech.com.br",
        "phone": "(16) 44444-4444",
        "website": "https://agritech.com.br",
        "industry": "Agronegócio",
        "location": "Ribeirão Preto, SP",
        "revenue": "R$ 10-20M",
        "employees": "200-500",
        "description": "Tecnologia para agricultura de precisão. Desenvolve sensores IoT e software para otimização de cultivos e sustentabilidade.",
        "keywords": ["agritech", "agricultura de precisão", "iot", "sustentabilidade", "sensores"]
    },
    {
        "company": "LogisTech Transportes",
        "contact": "Ricardo Alves",
        "email": "ricardo@logistech.com.br",
        "phone": "(11) 33333-3333",
        "website": "https://logistech.com.br",
        "industry": "Logística",
        "location": "São Paulo, SP",
        "revenue": "R$ 5-10M",
        "employees": "80-150",
        "description": "Plataforma de gestão logística com otimização de rotas e rastreamento em tempo real. Atende e-commerces e transportadoras.",
        "keywords": ["logística", "otimização de rotas", "rastreamento", "transportes", "ecommerce"]
    },
    {
        "company": "RetailTech Varejo",
        "contact": "Luciana Mendes",
        "email": "luciana@retailtech.com.br",
        "phone": "(21) 22222-2222",
        "website": "https://retailtech.com.br",
        "industry": "Varejo",
        "location": "Rio de Janeiro, RJ",
        "revenue": "R$ 2-5M",
        "employees": "40-80",
        "description": "Soluções tecnológicas para varejo físico e digital. Oferece sistemas de PDV, gestão de estoque e análise de dados de vendas.",
        "keywords": ["varejo", "pdv", "gestão de estoque", "análise de dados", "omnichannel"]
    },
    {
        "company": "PropTech Imóveis",
        "contact": "André Souza",
        "email": "andre@proptech.com.br",
        "phone": "(11) 11111-1111",
        "website": "https://proptech.com.br",
        "industry": "Imobiliário",
        "location": "São Paulo, SP",
        "revenue": "R$ 3-8M",
        "employees": "60-120",
        "description": "Plataforma digital para mercado imobiliário. Conecta compradores, vendedores e corretores com ferramentas de IA para avaliação de imóveis.",
        "keywords": ["proptech", "imóveis", "inteligência artificial", "avaliação", "marketplace"]
    },
    {
        "company": "CleanTech Energia",
        "contact": "Patrícia Verde",
        "email": "patricia@cleantech.com.br",
        "phone": "(11) 99999-0000",
        "website": "https://cleantech.com.br",
        "industry": "Energia",
        "location": "São Paulo, SP",
        "revenue": "R$ 15-30M",
        "employees": "300-500",
        "description": "Soluções em energia renovável e eficiência energética. Desenvolve sistemas de energia solar e eólica para empresas.",
        "keywords": ["energia renovável", "energia solar", "energia eólica", "eficiência energética", "sustentabilidade"]
    }
]

def create_sample_user(db: Session) -> User:
    """Criar usuário de exemplo se não existir"""
    user = db.query(User).filter(User.email == "admin@huntly.com").first()
    
    if not user:
        user = User(
            email="admin@huntly.com",
            name="Admin Huntly",
            password_hash="hashed_password_here",  # Em produção, usar hash real
            plan_type="enterprise"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ Usuário criado: {user.email}")
    
    return user

def populate_leads(db: Session, user_id: int, num_leads: int = None):
    """Popular banco com leads de exemplo"""
    
    if num_leads is None:
        num_leads = len(SAMPLE_LEADS)
    
    # Verificar se já existem leads
    existing_count = db.query(Lead).count()
    if existing_count > 0:
        print(f"⚠️  Já existem {existing_count} leads no banco. Continuando...")
    
    created_count = 0
    
    for i, lead_data in enumerate(SAMPLE_LEADS[:num_leads]):
        # Verificar se lead já existe
        existing_lead = db.query(Lead).filter(
            Lead.company == lead_data["company"]
        ).first()
        
        if existing_lead:
            print(f"⏭️  Lead já existe: {lead_data['company']}")
            continue
        
        # Criar lead com variações nos dados
        created_days_ago = random.randint(1, 90)
        created_at = datetime.now() - timedelta(days=created_days_ago)
        
        lead = Lead(
            user_id=user_id,
            company=lead_data["company"],
            contact=lead_data["contact"],
            email=lead_data["email"],
            phone=lead_data["phone"],
            website=lead_data.get("website"),
            industry=lead_data["industry"],
            location=lead_data["location"],
            revenue=lead_data["revenue"],
            employees=lead_data["employees"],
            description=lead_data["description"],
            keywords=lead_data["keywords"],
            score=random.randint(60, 95),
            status=random.choice(["Novo", "Contatado", "Qualificado", "Proposta", "Negociação"]),
            priority=random.choice(["Alta", "Média", "Baixa"]),
            created_at=created_at
        )
        
        db.add(lead)
        created_count += 1
        print(f"➕ Criando lead: {lead_data['company']}")
    
    try:
        db.commit()
        print(f"✅ {created_count} leads criados com sucesso!")
        return created_count
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar leads: {e}")
        return 0

def index_leads(db: Session, created_count: int):
    """Indexar leads para busca"""
    if created_count == 0:
        print("⏭️  Nenhum lead novo para indexar")
        return
    
    try:
        # Inicializar indexer
        redis_client = get_redis_client()
        cache_manager = CacheManager(redis_client)
        indexer = LeadIndexer(db, cache_manager)
        
        print("🔍 Iniciando indexação dos leads...")
        
        # Indexar todos os leads
        stats = indexer.bulk_index_leads()
        
        print(f"✅ Indexação concluída:")
        print(f"   - Total processado: {stats.total_leads}")
        print(f"   - Indexados com sucesso: {stats.indexed_leads}")
        print(f"   - Falhas: {stats.failed_leads}")
        print(f"   - Tempo: {stats.processing_time:.2f}s")
        
        if stats.errors:
            print(f"⚠️  Erros encontrados:")
            for error in stats.errors[:5]:  # Mostrar apenas os primeiros 5
                print(f"   - {error}")
        
    except Exception as e:
        print(f"❌ Erro na indexação: {e}")

def main():
    """Função principal"""
    print("🚀 Iniciando população do banco de dados com leads...")
    
    # Conectar ao banco
    db = SessionLocal()
    
    try:
        # Criar usuário de exemplo
        user = create_sample_user(db)
        
        # Popular leads
        created_count = populate_leads(db, user.id)
        
        # Indexar leads para busca
        index_leads(db, created_count)
        
        # Mostrar estatísticas finais
        total_leads = db.query(Lead).count()
        print(f"\n📊 Estatísticas finais:")
        print(f"   - Total de leads no banco: {total_leads}")
        print(f"   - Leads criados nesta execução: {created_count}")
        
        print("\n✅ População do banco concluída com sucesso!")
        print("\n💡 Agora você pode:")
        print("   - Usar GET /leads/ para listar leads")
        print("   - Usar GET /leads/search?q=tecnologia para buscar")
        print("   - Usar GET /leads/suggestions?q=tech para autocomplete")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()