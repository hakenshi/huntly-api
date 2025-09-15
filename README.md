# Huntly API

API para geração e qualificação de leads com IA.

## Deploy no Railway

### 1. Conectar Repositório
- Acesse [Railway](https://railway.app)
- Conecte seu repositório GitHub
- Selecione a pasta `api/`

### 2. Configurar Variáveis de Ambiente
```
DATABASE_URL=postgresql://...
SECRET_KEY=sua-chave-secreta
FRONTEND_URL=https://seu-frontend.vercel.app
ENVIRONMENT=production
```

### 3. Deploy Automático
- Railway detectará o `Dockerfile`
- Build e deploy automáticos
- URL gerada automaticamente

## Endpoints Principais

- `GET /` - Status da API
- `GET /health` - Health check
- `GET /leads` - Listar leads
- `POST /leads/search` - Buscar leads
- `GET /campaigns` - Listar campanhas
- `GET /analytics/dashboard` - Métricas

## Desenvolvimento Local

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

API disponível em: http://localhost:8000
