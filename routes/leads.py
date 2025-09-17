from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from models.lead import Lead, LeadCreate
from models.search import SearchFilters
from datetime import datetime

router = APIRouter(prefix="/leads", tags=["leads"])

# Mock data para desenvolvimento
mock_leads = [
    {
        "id": 1,
        "company": "TechInova Solutions",
        "contact": "Carlos Silva",
        "email": "carlos@techinova.com.br",
        "phone": "(11) 99999-9999",
        "industry": "Tecnologia",
        "location": "São Paulo, SP",
        "score": 92,
        "status": "Novo",
        "priority": "Alta",
        "revenue": "R$ 2-5M",
        "employees": "50-100",
        "last_contact": None,
        "created_at": datetime.now()
    },
    {
        "id": 2,
        "company": "EcoCommerce Brasil",
        "contact": "Ana Santos",
        "email": "ana@ecocommerce.com.br",
        "phone": "(21) 88888-8888",
        "industry": "E-commerce",
        "location": "Rio de Janeiro, RJ",
        "score": 78,
        "status": "Contatado",
        "priority": "Média",
        "revenue": "R$ 1-2M",
        "employees": "20-50",
        "last_contact": datetime.now(),
        "created_at": datetime.now()
    }
]

@router.get("/", response_model=List[Lead])
async def get_leads(
    skip: int = 0,
    limit: int = 100,
    industry: Optional[str] = None,
    status: Optional[str] = None
):
    """Buscar leads com filtros opcionais"""
    leads = mock_leads[skip:skip + limit]
    
    if industry:
        leads = [lead for lead in leads if lead["industry"].lower() == industry.lower()]
    
    if status:
        leads = [lead for lead in leads if lead["status"] == status]
    
    return leads

@router.post("/", response_model=Lead)
async def create_lead(lead: LeadCreate):
    """Criar novo lead"""
    new_lead = {
        "id": len(mock_leads) + 1,
        **lead.dict(),
        "score": 75,  # Score padrão
        "status": "Novo",
        "priority": "Média",
        "created_at": datetime.now()
    }
    mock_leads.append(new_lead)
    return new_lead

@router.get("/{lead_id}", response_model=Lead)
async def get_lead(lead_id: int):
    """Buscar lead por ID"""
    lead = next((lead for lead in mock_leads if lead["id"] == lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead

@router.put("/{lead_id}", response_model=Lead)
async def update_lead(lead_id: int, lead_update: dict):
    """Atualizar lead"""
    lead = next((lead for lead in mock_leads if lead["id"] == lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    lead.update(lead_update)
    return lead

@router.post("/search", response_model=List[Lead])
async def search_leads(filters: SearchFilters):
    """Buscar leads com filtros avançados"""
    # Simular busca inteligente
    results = []
    
    if filters.industry:
        # Simular encontrar leads baseado na indústria
        for i in range(5):
            results.append({
                "id": len(mock_leads) + i + 1,
                "company": f"Empresa {filters.industry} {i+1}",
                "contact": f"Contato {i+1}",
                "email": f"contato{i+1}@empresa.com",
                "industry": filters.industry,
                "location": filters.location or "São Paulo, SP",
                "score": 80 + i,
                "status": "Novo",
                "priority": "Alta" if i < 2 else "Média",
                "revenue": filters.revenue_range or "R$ 1-5M",
                "employees": filters.company_size or "10-50",
                "created_at": datetime.now()
            })
    
    return results
