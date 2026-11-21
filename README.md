# Atlas de Barragens

Sistema acadêmico de mapeamento nacional de barragens de rejeitos e análise da proximidade com epicentros sísmicos. A aplicação apresenta contagens, procedência, recortes espaciais, série anual e relatório imprimível. As distâncias são epicentrais e os resultados têm finalidade acadêmica.

## Tecnologias e estrutura

Python 3.10+, Flask, PostgreSQL/PostGIS, Psycopg 3, python-dotenv, GeoPandas/Pandas, Pytest, HTML5, CSS3, JavaScript, Leaflet, OpenStreetMap e Chart.js.

| Diretório | Responsabilidade |
| --- | --- |
| `rotas/` | Blueprints HTML e API |
| `controle/` | Validação e regras de negócio |
| `modelo/` | Consultas parametrizadas, GeoJSON e proveniência |
| `db/` | Conexão, esquema, consulta espacial e guia para pgAdmin/DBeaver |
| `templates/` e `static/` | Interface web |
| `scripts/` | Importadores de dados públicos |
| `dados/brutos/`, `dados/processados/` | Arquivos locais ignorados pelo Git |
| `testes/` | Testes de API, validação e PostGIS |

## Instalação no Windows pelo terminal do VS Code

No PowerShell, abra a raiz do projeto. Instale o Python a partir de [python.org](https://www.python.org/downloads/windows/) se o comando `python` estiver indisponível. Os comandos usam o executável do ambiente diretamente e dispensam a ativação pelo PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.exemplo .env }
```

Instale [PostgreSQL para Windows](https://www.postgresql.org/download/windows/) e [PostGIS compatível com o PostgreSQL](https://postgis.net/documentation/getting_started/install_windows/). Use a senha escolhida na instalação em `DB_PASSWORD`. Ajuste host, porta, usuário e banco em `.env`. Mantenha esse arquivo local. `FLASK_DEBUG` controla a recarga no desenvolvimento e deve ficar desativado em execução regular. A aplicação não usa sessões.

Com `psql` disponível no PATH, execute:

```powershell
psql -h localhost -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE mapeamento_barragens"
psql -h localhost -p 5432 -U postgres -d mapeamento_barragens -v ON_ERROR_STOP=1 -f db/schema.sql
psql -h localhost -p 5432 -U postgres -d mapeamento_barragens -c "SELECT PostGIS_Full_Version()"
```

Para pgAdmin e DBeaver, consulte [db/db.txt](db/db.txt). A conta de setup precisa poder criar a extensão. Em uma instalação compartilhada, use contas separadas para administração, importação e leitura.

## Importar dados

### Barragens de rejeitos

Baixe o [CSV oficial da ANM](https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv) em `dados/brutos/Barragens.csv` e informe a data da edição disponível no [diretório SIGBM](https://dadosabertos.anm.gov.br/SIGBM/). O arquivo de 19/11/2026 foi inspecionado. Ele usa Windows-1252, separador vírgula, e coordenadas em graus, minutos e segundos. O script também aceita CSV UTF-8 e coordenadas decimais.

| Coluna da ANM | Campo/uso |
| --- | --- |
| ID | Identificador oficial e chave do upsert |
| Nome, Município, UF | Nome e localização administrativa |
| Latitude, Longitude | Conversão de DMS com sinal para ponto WGS 84 |
| Categoria de Risco - CRI, Dano Potencial Associado - DPA | Classificações do cadastro |
| Estrutura com o Objetivo de Contenção | Inclui `Rejeitos` e `Mista` por padrão |

```powershell
.\.venv\Scripts\python.exe -m scripts.importar_barragens dados/brutos/Barragens.csv --inspecionar
.\.venv\Scripts\python.exe -m scripts.importar_barragens dados/brutos/Barragens.csv --data-base 2026-11-19 --validar
.\.venv\Scripts\python.exe -m scripts.importar_barragens dados/brutos/Barragens.csv --data-base 2026-11-19
```

O caminho do arquivo é opcional para tentar o download pelo próprio importador. Se o servidor recusar a conexão, baixe pelo navegador e passe o caminho local. `--valor-rejeitos Rejeitos` restringe a importação à categoria exclusiva. Para uma revisão do layout, confira o cabeçalho com `--inspecionar`. Os campos de ID, UF e finalidade aceitam substituição explícita. `--coluna-atualizacao` permite ler uma data de atualização por linha quando a edição tiver esse campo. O importador preserva registros sem coordenadas no cadastro e os exclui do mapa e da análise. Cada lote guarda a data de coleta e o SHA-256. Registros ausentes em uma edição posterior continuam no banco.

### Sismos USGS e limite IBGE

Baixe a [Malha País 2024 do IBGE](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/Brasil/BR_Pais_2024.zip) em `dados/brutos/BR_Pais_2024.zip`. A [API USGS](https://earthquake.usgs.gov/fdsnws/event/1/) fornece GeoJSON paginado. GeoPandas lê a malha, reprojeta para WGS 84 e une os polígonos. PostGIS aplica o limite territorial e a distância à malha quando houver margem. A API consulta primeiro uma caixa de busca conservadora. Datas de início e fim são inclusivas em UTC.

```powershell
.\.venv\Scripts\python.exe -m scripts.importar_sismos --inicio 2020-01-01 --fim 2026-11-20 --magnitude-minima 3 --limite dados/brutos/BR_Pais_2024.zip --margem-km 250
```

Omita `--margem-km` para o recorte estrito. A margem inclui eventos externos próximos a fronteiras e ao litoral. Se a API estiver indisponível, exporte o catálogo USGS com `format=geojson` e passe `--arquivo dados/brutos/USGS_2020-2026.geojson`. Repetir a importação atualiza os eventos pelo identificador USGS. Importações com margem diferente preservam os eventos de lotes anteriores.

### Zonas sismogênicas

O [GeoSGB](https://geosgb.sgb.gov.br/) oferece contexto geológico. A publicação sobre [ameaça sísmica no Nordeste](https://pmc.ncbi.nlm.nih.gov/articles/PMC11098838/) e o [estudo da margem continental sudeste](https://www.iag.usp.br/~marcelo/pdfs/Assumpcao_SVicente_eq_GJInt2011.pdf) exemplificam como a delimitação depende de recorte, evidências e metodologia. A distribuição padrão deixa essa camada indisponível, pois nenhuma base vetorial nacional com zonas e metodologia verificadas foi incorporada. Falhas geológicas e classes normativas de aceleração exigem interpretação própria.

Use um GeoJSON ou GeoPackage com polígonos válidos, CRS conhecido e campos `nome`, `classificacao` e, opcionalmente, `descricao`. A URL, versão, metodologia e referência devem descrever o conjunto efetivamente importado. Os valores abaixo são parâmetros a preencher com a publicação consultada.

```powershell
.\.venv\Scripts\python.exe -m scripts.importar_zonas dados/brutos/zonas.gpkg --fonte "<instituição>" --url "<URL da base>" --versao "<edição>" --metodologia "<método publicado>" --referencia "<DOI ou referência bibliográfica>"
```

Use `--camada` se o GeoPackage tiver múltiplas camadas. A aplicação informa a indisponibilidade enquanto a tabela estiver vazia.

## Executar

```powershell
.\.venv\Scripts\python.exe main.py
```

Com o ambiente ativado, também funciona com `python main.py`. Abra [http://127.0.0.1:5000](http://127.0.0.1:5000/).

### Reusar a instância portátil desta entrega

Neste workspace, o banco de validação está em `.venv/postgres-portatil/dados`. Para reabri-lo, execute no primeiro terminal:

```powershell
.\.venv\postgres-portatil\pgsql\bin\postgres.exe -D .venv/postgres-portatil/dados -p 55432 -h 127.0.0.1
```

Em outro terminal, use a porta da instância de validação para iniciar o Flask:

```powershell
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "55432"
.\.venv\Scripts\python.exe main.py
```

O banco portátil usa autenticação local de teste e escuta apenas na interface de loopback. Reserve-o para validação na máquina local. A configuração padrão em `.env` usa o PostgreSQL da instalação normal.

### Páginas

| Página | Caminho |
| --- | --- |
| Resumo e fontes | `/` |
| Mapa com camadas e filtros | `/mapa` |
| Catálogo e detalhes | `/barragens` |
| Raio, distância, gráfico e relatório | `/analises` |
| Metodologia | `/sobre` |

O mapa requisita feições por área visível com teto por camada. Quando o teto é atingido, aproxime a região ou refine os filtros. O mapa-base segue a [política de tiles da OSM Foundation](https://operations.osmfoundation.org/policies/tiles/), com atribuição, acesso HTTPS, cache normal do navegador e carregamento sob demanda. A interface carrega Leaflet, Chart.js e tiles de provedores externos e precisa de acesso à internet para esses recursos.

## API pública de leitura

| GET | Parâmetros |
| --- | --- |
| `/api/barragens` | `uf`, `municipio` (igualdade ignorando maiúsculas), `nome` (trecho), `mapeada=1`, `bbox`, `pagina`, `limite` |
| `/api/barragens/<id>` | ID interno retornado pela coleção |
| `/api/sismos` | `magnitude_minima`, `inicio`, `fim`, `bbox`, `pagina`, `limite` |
| `/api/zonas` | `bbox`, `pagina`, `limite`, com sinalizador `disponivel` |
| `/api/estatisticas` | Totais e metadados de origem |
| `/api/analises/proximidade` | `barragem_id`, `raio_km`, `magnitude_minima`, `inicio`, `fim`, `pagina`, `limite` |
| `/api/analises/barragem/<id>` | Mesmos filtros de proximidade com ID na URL |

`bbox=oeste,sul,leste,norte` usa graus WGS 84. As coleções retornam GeoJSON com `paginacao.mais` e limite de 500 por página (padrão 100). Datas usam `AAAA-MM-DD`. O raio aceita 0,01 a 1.000 km, com padrão de 50 km. Falhas de validação retornam 400. IDs ausentes retornam 404. Erros internos retornam 500 com mensagem genérica. Exemplo:

```text
/api/analises/proximidade?barragem_id=1&raio_km=25&magnitude_minima=3&inicio=2020-01-01&fim=2026-11-20
```

## Testes e interpretação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
# Opcional: use uma conexão com o PostGIS habilitado.
$env:TESTE_POSTGIS_DSN = "host=localhost port=5432 dbname=mapeamento_barragens user=postgres"
.\.venv\Scripts\python.exe -m pytest -q
```

Configure autenticação de teste por `pgpass.conf` quando necessário. O teste de integração usa tabelas temporárias para conferir o raio, a distância, o corte de datas em UTC, a magnitude e a paginação.

O resumo de proximidade considera todos os eventos filtrados, enquanto o mapa de análise e o relatório imprimível mostram os epicentros da página selecionada. O PostGIS usa `geography` e distância elipsoidal. O círculo Leaflet é uma representação visual aproximada. A profundidade permanece um atributo do catálogo. Diferenças de cobertura e limiares de detecção influenciam as contagens. A aplicação tem finalidade acadêmica e não produz previsões sísmicas, avaliações de estabilidade ou certificações de segurança.

