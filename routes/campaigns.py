from fastapi import APIRouter, HTTPException
from typing import List
from models.campaign import Campaign, CampaignCreate
from datetime import datetime

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

mock_campaigns = [
    {
        "id": 1,
        "name": "Startups de Tecnologia - SP",
        "status": "Ativa",
        "leads_found": 127,
        "emails_sent": 89,
        "responses": 12,
        "conversions": 3,
        "created_at": datetime.now(),
        "next_execution": "Em 2 horas"
    },
    {
        "id": 2,
        "name": "E-commerce - Brasil",
        "status": "Pausada",
        "leads_found": 89,
        "emails_sent": 45,
        "responses": 8,
        "conversions": 2,
        "created_at": datetime.now(),
        "next_execution": "Pausada"
    }
]

@router.get("/", response_model=List[Campaign])
async def get_campaigns():
    """Listar todas as campanhas"""
    return mock_campaigns

@router.post("/", response_model=Campaign)
async def create_campaign(campaign: CampaignCreate):
    """Criar nova campanha"""
    new_campaign = {
        "id": len(mock_campaigns) + 1,
        **campaign.dict(),
        "status": "Ativa",
        "leads_found": 0,
        "emails_sent": 0,
        "responses": 0,
        "conversions": 0,
        "created_at": datetime.now(),
        "next_execution": "Em processamento"
    }
    mock_campaigns.append(new_campaign)
    return new_campaign

@router.get("/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: int):
    """Buscar campanha por ID"""
    campaign = next((c for c in mock_campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campaign

@router.put("/{campaign_id}/status")
async def update_campaign_status(campaign_id: int, status: str):
    """Atualizar status da campanha (pausar/retomar)"""
    campaign = next((c for c in mock_campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    
    campaign["status"] = status
    campaign["next_execution"] = "Pausada" if status == "Pausada" else "Em 1 hora"
    
    return {"message": f"Campanha {status.lower()} com sucesso"}
