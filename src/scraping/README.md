# 🕷️ Sistema de Lead Scraping Automático

Sistema completo para coleta automática de leads da internet, integrado com o Huntly MVP.

## 📋 Visão Geral

O sistema de scraping permite coletar automaticamente informações de empresas e contatos de várias fontes na internet:

- **Google Maps**: Empresas locais com informações de contato
- **LinkedIn**: Empresas e profissionais (limitado)
- **Sites de Empresas**: Informações diretas dos websites

## 🚀 Funcionalidades

### ✅ Implementado

- **Scraping Multi-Fonte**: Coleta dados de múltiplas fontes simultaneamente
- **Gerenciamento de Jobs**: Sistema assíncrono para executar scraping em background
- **Rate Limiting**: Controle de velocidade para respeitar limites dos sites
- **Validação de Dados**: Verificação e limpeza automática dos dados coletados
- **Cache Inteligente**: Evita duplicatas e melhora performance
- **Indexação Automática**: Leads coletados são automaticamente indexados para busca
- **API REST Completa**: Endpoints para gerenciar scraping via API
- **Templates Pré-configurados**: Configurações prontas para diferentes indústrias

### 🔄 Fontes de Dados Suportadas

| Fonte | Dados Coletados | Qualidade | Velocidade | Limitações |
|-------|----------------|-----------|------------|------------|
| **Google Maps** | Empresa, telefone, endereço, website | Alta | Rápida | Rate limiting |
| **LinkedIn** | Empresa, indústria, funcionários, descrição | Muito Alta | Lenta | Requer autenticação |
| **Sites de Empresas** | Email, telefone, descrição detalhada | Variável | Média | Estrutura variável |

## 🛠️ Como Usar

### 1. Via API REST

```python
# Iniciar scraping
POST /scraping/start
{
    "search_query": "restaurante pizza",
    "location": "São Paulo, SP",
    "max_results": 100,
    "sources": ["google_maps"],
    "required_fields": ["company", "phone"]
}

# Acompanhar progresso
GET /scraping/jobs/{job_id}

# Listar jobs
GET /scraping/jobs
```

### 2. Via Python (Programático)

```python
from src.scraping.manager import ScrapingManager
from src.scraping.models import ScrapingConfig, ScrapingSource

# Configurar scraping
config = ScrapingConfig(
    search_query="empresa software",
    location="São Paulo",
    max_results=50,
    sources=[ScrapingSource.GOOGLE_MAPS]
)

# Executar
manager = ScrapingManager(db_session, cache_manager)
job = await manager.start_scraping_job(user_id=1, config=config)
```

### 3. Templates Prontos

```python
# Usar template pré-configurado
GET /scraping/templates

# Exemplo de resposta:
{
    "name": "Empresas de Tecnologia",
    "config": {
        "search_query": "empresa software desenvolvimento",
        "industry": "Tecnologia",
        "sources": ["google_maps", "linkedin"],
        "max_results": 100
    }
}
```

## ⚙️ Configuração

### Parâmetros Principais

```python
ScrapingConfig(
    # Busca
    search_query="termo de busca",      # Obrigatório
    location="cidade, estado",          # Opcional
    industry="indústria",               # Opcional
    
    # Limites
    max_results=100,                    # Máximo de leads
    max_pages=10,                       # Máximo de páginas
    
    # Performance
    delay_between_requests=1.0,         # Delay entre requests (segundos)
    
    # Filtros
    required_fields=["company", "email"], # Campos obrigatórios
    min_employees=10,                   # Mínimo de funcionários
    max_employees=500,                  # Máximo de funcionários
    
    # Fontes
    sources=[ScrapingSource.GOOGLE_MAPS], # Fontes a usar
    
    # Avançado
    use_proxy=False,                    # Usar proxy
    respect_robots_txt=True             # Respeitar robots.txt
)
```

### Variáveis de Ambiente

```bash
# Rate limiting
SCRAPING_DEFAULT_DELAY=1.0
SCRAPING_MAX_CONCURRENT=5

# Timeouts
SCRAPING_REQUEST_TIMEOUT=30
SCRAPING_SESSION_TIMEOUT=300

# Proxy (opcional)
SCRAPING_PROXY_URL=http://proxy:8080
SCRAPING_PROXY_ROTATION=true
```

## 📊 Monitoramento

### Status do Job

```python
job_status = {
    "id": "uuid",
    "status": "running",           # pending, running, completed, failed
    "leads_found": 45,            # Total encontrado
    "leads_saved": 42,            # Total salvo no banco
    "progress": 75,               # Progresso %
    "estimated_completion": "2024-01-15T10:30:00Z",
    "errors": [],                 # Lista de erros
    "warnings": []                # Lista de avisos
}
```

### Estatísticas Gerais

```python
GET /scraping/stats
{
    "active_jobs": 3,
    "total_leads_found": 1250,
    "total_leads_saved": 1180,
    "average_success_rate": 94.4,
    "sources_usage": {
        "google_maps": 15,
        "linkedin": 8,
        "company_website": 5
    }
}
```

## 🔧 Exemplos de Uso

### Restaurantes Locais

```python
config = ScrapingConfig(
    search_query="restaurante pizza delivery",
    location="Rio de Janeiro, RJ",
    sources=[ScrapingSource.GOOGLE_MAPS],
    max_results=200,
    required_fields=["company", "phone"]
)
```

### Startups de Tecnologia

```python
config = ScrapingConfig(
    search_query="startup software saas",
    industry="Tecnologia",
    sources=[ScrapingSource.LINKEDIN, ScrapingSource.COMPANY_WEBSITE],
    max_results=100,
    min_employees=5,
    max_employees=50,
    required_fields=["company", "website"]
)
```

### Serviços Profissionais

```python
config = ScrapingConfig(
    search_query="advogado contador consultor",
    location="São Paulo",
    sources=[ScrapingSource.GOOGLE_MAPS],
    max_results=150,
    required_fields=["company", "phone"]
)
```

## 🚨 Considerações Éticas e Legais

### ✅ Boas Práticas

- **Respeite robots.txt**: Sempre verificar e respeitar as diretrizes
- **Rate Limiting**: Não sobrecarregar os servidores
- **Dados Públicos**: Coletar apenas informações publicamente disponíveis
- **Uso Responsável**: Usar dados coletados de forma ética

### ⚠️ Limitações

- **LinkedIn**: Requer autenticação, considere usar API oficial
- **Google Maps**: Sujeito a rate limiting e possível bloqueio
- **Sites Empresariais**: Estrutura variável, dados podem ser incompletos

### 📋 Recomendações

1. **Para LinkedIn**: Use a API oficial do Sales Navigator
2. **Para Google**: Considere a Google Places API
3. **Para dados específicos**: APIs especializadas como Clearbit, ZoomInfo
4. **Para compliance**: Implemente LGPD/GDPR se necessário

## 🔄 Integração com o Sistema

### Fluxo Completo

1. **Configuração**: Usuário define parâmetros de busca
2. **Execução**: Sistema executa scraping em background
3. **Validação**: Dados são validados e limpos
4. **Armazenamento**: Leads salvos no banco PostgreSQL
5. **Indexação**: Leads indexados para busca (Redis + PostgreSQL)
6. **Disponibilização**: Leads disponíveis via API de busca

### Integração com Search Engine

```python
# Leads coletados são automaticamente indexados
scraping_manager = ScrapingManager(db, cache)
job = await scraping_manager.start_scraping_job(user_id, config)

# Após conclusão, leads estão disponíveis para busca
search_engine = SearchEngine(db, cache)
results = search_engine.search_leads(SearchQuery(text="pizza delivery"))
```

## 🚀 Próximos Passos

### Melhorias Planejadas

- [ ] **Scraping de Redes Sociais**: Instagram, Facebook Business
- [ ] **APIs Especializadas**: Integração com Clearbit, ZoomInfo
- [ ] **Machine Learning**: Classificação automática de indústrias
- [ ] **Enriquecimento de Dados**: Validação de emails, telefones
- [ ] **Scraping Agendado**: Jobs recorrentes automáticos
- [ ] **Dashboard Visual**: Interface para monitoramento
- [ ] **Exportação**: CSV, Excel, integração com CRMs

### Otimizações

- [ ] **Proxy Rotation**: Rotação automática de proxies
- [ ] **CAPTCHA Solving**: Integração com serviços de CAPTCHA
- [ ] **Selenium Integration**: Para sites com JavaScript pesado
- [ ] **Distributed Scraping**: Scraping distribuído para escala

## 📚 Documentação Adicional

- [API Reference](../routes/scraping.py) - Documentação completa da API
- [Examples](example_usage.py) - Exemplos práticos de uso
- [Models](models.py) - Modelos de dados detalhados
- [Scrapers](scrapers/) - Implementação dos scrapers individuais

---

**⚡ Dica**: Para começar rapidamente, use os templates pré-configurados disponíveis em `/scraping/templates`!