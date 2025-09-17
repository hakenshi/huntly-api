# Lead Indexing System

Sistema de indexação de leads para o Huntly MVP que combina PostgreSQL full-text search com Redis inverted index para busca rápida e eficiente.

## Visão Geral

O sistema de indexação extrai metadados pesquisáveis dos leads e cria índices otimizados para:

- **PostgreSQL tsvector**: Full-text search nativo do PostgreSQL
- **Redis inverted index**: Índice invertido para buscas rápidas por tokens
- **Cache inteligente**: Cache de dados de leads e resultados de busca

## Componentes Principais

### LeadIndexer

Classe principal responsável pela indexação de leads:

```python
from src.search.indexer import LeadIndexer
from src.database.connection import SessionLocal, get_redis
from src.cache.manager import CacheManager

# Inicializar
db = SessionLocal()
cache_manager = CacheManager(get_redis())
indexer = LeadIndexer(db, cache_manager)

# Indexar um lead
success = indexer.index_lead(lead)

# Indexação em lote
stats = indexer.bulk_index_leads(batch_size=100)

# Buscar por tokens
lead_ids = indexer.search_leads_by_tokens(["tecnologia", "saas"])
```

### Funcionalidades

#### 1. Extração de Metadados

O sistema extrai e processa:

- **Texto pesquisável**: Combinação de todos os campos relevantes
- **Tokens de empresa**: Palavras-chave da empresa
- **Tokens de indústria**: Categorização por setor
- **Tokens de localização**: Informações geográficas
- **Keywords automáticas**: Extração de termos técnicos e relevantes

#### 2. Indexação PostgreSQL

- Utiliza `tsvector` para full-text search
- Trigger automático para atualizar search_vector
- Índices GIN para performance otimizada
- Suporte a busca em português e inglês

#### 3. Índice Invertido Redis

- Mapeamento token → lead_ids para busca rápida
- Operações de interseção para múltiplos termos
- Cache com TTL configurável
- Fallback gracioso quando Redis não disponível

## Uso Básico

### Indexar Lead Individual

```python
# Criar ou obter lead
lead = LeadModel(
    company="TechCorp Solutions",
    industry="Tecnologia",
    description="Empresa de SaaS especializada em e-commerce",
    keywords=["saas", "ecommerce", "python"]
)

# Indexar
success = indexer.index_lead(lead)
if success:
    print("Lead indexado com sucesso!")
```

### Indexação em Lote

```python
# Indexar todos os leads não indexados
stats = indexer.bulk_index_leads()

print(f"Processados: {stats.total_leads}")
print(f"Indexados: {stats.indexed_leads}")
print(f"Falhas: {stats.failed_leads}")
print(f"Tempo: {stats.processing_time:.2f}s")
```

### Busca por Tokens

```python
# Buscar leads que contenham os termos
lead_ids = indexer.search_leads_by_tokens(
    tokens=["tecnologia", "saas"],
    limit=50
)

# Obter dados completos dos leads
leads = db.query(LeadModel).filter(LeadModel.id.in_(lead_ids)).all()
```

### Status da Indexação

```python
status = indexer.get_indexing_status()

print(f"Total de leads: {status['total_leads']}")
print(f"Leads indexados: {status['indexed_leads']}")
print(f"Cobertura: {status['indexing_coverage']:.1f}%")
```

## Configuração

### Variáveis de Ambiente

```bash
# Cache TTL (segundos)
SEARCH_CACHE_TTL=3600
LEAD_CACHE_TTL=7200

# Performance
MAX_SEARCH_RESULTS=1000
INDEXING_BATCH_SIZE=100

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=20
```

### Dependências

```bash
# Instalar dependências
pip install redis sqlalchemy psycopg2-binary

# Para desenvolvimento
pip install pytest pytest-asyncio
```

## Estrutura de Dados

### Metadados Extraídos

```python
{
    "searchable_text": "techcorp solutions tecnologia saas ecommerce python",
    "company_tokens": ["techcorp", "solutions"],
    "industry_tokens": ["tecnologia"],
    "location_tokens": ["sao", "paulo"],
    "keywords": ["saas", "ecommerce", "python"],
    "all_tokens": ["techcorp", "solutions", "tecnologia", "saas", ...]
}
```

### Cache Redis

```
# Índice invertido
index:tecnologia -> {1, 2, 5, 8}
index:saas -> {1, 3, 7}
index:python -> {1, 4, 6}

# Cache de leads
lead:1 -> {lead_data_json}
lead:2 -> {lead_data_json}

# Cache de buscas
search:hash123 -> {query, results, cached_at}
```

## Performance

### Benchmarks Esperados

- **Indexação**: ~100 leads/segundo
- **Busca Redis**: <10ms para 100k leads
- **Busca PostgreSQL**: <500ms para datasets grandes
- **Cache hit rate**: >80% para buscas frequentes

### Otimizações

1. **Batch processing**: Processa leads em lotes
2. **Cache inteligente**: TTL diferenciado por tipo de dados
3. **Índices otimizados**: GIN indexes no PostgreSQL
4. **Fallback gracioso**: Funciona sem Redis se necessário

## Testes

```bash
# Executar testes
cd backend
python -m pytest tests/test_lead_indexer.py -v

# Executar exemplo
python -m src.search.example_usage
```

### Casos de Teste

- ✅ Limpeza e tokenização de texto
- ✅ Extração de metadados
- ✅ Indexação individual e em lote
- ✅ Busca por tokens
- ✅ Operações de cache
- ✅ Fallback sem Redis
- ✅ Tratamento de erros

## Monitoramento

### Health Check

```python
status = indexer.get_indexing_status()
cache_health = cache_manager.health_check()

# Verificar se sistema está saudável
if status['indexing_coverage'] > 90 and cache_health['status'] == 'healthy':
    print("Sistema funcionando normalmente")
```

### Métricas Importantes

- **Cobertura de indexação**: % de leads indexados
- **Performance de busca**: Tempo médio de resposta
- **Cache hit rate**: Taxa de acerto do cache
- **Erros de indexação**: Leads que falharam na indexação

## Troubleshooting

### Problemas Comuns

1. **Redis indisponível**
   - Sistema continua funcionando com PostgreSQL apenas
   - Performance reduzida mas funcional

2. **Leads não indexados**
   - Verificar logs de erro
   - Executar reindexação: `indexer.reindex_all_leads()`

3. **Performance lenta**
   - Verificar índices PostgreSQL
   - Monitorar uso de memória Redis
   - Ajustar batch_size para indexação

4. **Cache inconsistente**
   - Limpar cache: `cache_manager.clear_all_cache()`
   - Reindexar leads afetados

### Logs Úteis

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs detalhados de indexação
logger = logging.getLogger('src.search.indexer')
```

## Roadmap

### Próximas Funcionalidades

- [ ] Busca fuzzy para typos
- [ ] Ranking por relevância
- [ ] Sugestões de autocomplete
- [ ] Análise de sentimento
- [ ] Indexação de documentos anexos
- [ ] Busca geográfica avançada

### Melhorias de Performance

- [ ] Sharding Redis para datasets grandes
- [ ] Compressão de índices
- [ ] Cache warming automático
- [ ] Indexação incremental otimizada