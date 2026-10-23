# Revisão técnica do LottoIA

## Resumo executivo

A revisão foi feita sobre a branch `main` do repositório `kukukukla/LottoIA-`. As correções incluídas nesta atualização abrangem importação e API pública do pacote `core`, simulação Monte Carlo, autenticação/sessões, limites de requisição, dependências web e configuração do container. Foi também evitado um cálculo repetido da matriz de correlação no cálculo de scores.

A aplicação pode ser executada como CLI ou como serviço FastAPI. A CLI oferece uma demonstração sintética explícita e também consulta resultados oficiais da CAIXA para Lotofácil, Mega-Sena e Lotomania. A API e o dashboard usam a CAIXA por padrão, identificam o último concurso e mostram os resultados recentes. Dados sintéticos só são usados quando `fonte=demo`/`--fonte demo` é solicitado ou em `run.py demo`. Rankings e jogos continuam sendo critérios descritivos/heurísticos: não preveem sorteios nem aumentam a probabilidade matemática de acerto.

## Revisões e correções aplicadas

1. **Importações e API pública:** removida da suíte uma alteração de `sys.path` que fazia os shims em `core/` importarem a si mesmos. O pacote `core` agora exporta sob demanda os tipos e motores exemplificados no README (`MotorPrincipal`, `Concurso`, `LoteriaTipo`, `EstrategiaConfig`, `MotorEstatistico`, `MotorScore` e `MotorTemporal`). Os módulos-fonte continuam na raiz; `core/` é uma camada de compatibilidade.
2. **Monte Carlo:** `monte_carlo_aleatorio` agora executa exatamente `n_simulacoes`, inclusive quando esse valor supera a quantidade de concursos disponíveis, amostrando concursos históricos com reposição. Rejeita quantidade inválida, dados históricos ausentes e quantidade inválida de dezenas; usa um gerador NumPy local para não alterar o estado aleatório global.
3. **Score e correlação:** durante cada cálculo de score, a matriz de correlação é calculada uma vez e reutilizada para as dezenas. Antes, a matriz — cujo cálculo percorre os concursos e pares de dezenas — era reconstruída para cada dezena.
4. **Web e sessão:** a chave fixa de desenvolvimento foi removida. Sem `SESSION_SECRET`, uma chave aleatória temporária é criada e registrada como aviso; em produção, deve ser definida de forma estável. O login limpa a sessão antes de atribuí-la, a senha é comparada sem remover espaços e a sessão tem validade de 12 horas. `SESSION_HTTPS_ONLY=true` ativa o atributo Secure para uso atrás de HTTPS.
5. **Validação de requisições:** `/api/gerar` limita jogos a 1–50 e dezenas a 15–20 (Lotofácil); `/api/simular` aceita 1–10.000 simulações. Valores fora dos limites resultam em HTTP 422.
6. **Dependência do formulário:** incluído `python-multipart`, necessário para que o FastAPI registre e processe o formulário de login.
7. **Container:** Docker e Compose iniciam o servidor web em `0.0.0.0:5000`, não apenas a demonstração CLI. O Compose exige `SESSION_SECRET`, `ADMIN_USERNAME` e `ADMIN_PASSWORD` no ambiente.
8. **Testes:** adicionados testes de regressão para quantidade exata de simulações, rejeição de entrada inválida e cálculo único da matriz de correlação.
9. **Resultados CAIXA:** criado `caixa_client.py` para mapear modalidades internas aos slugs da CAIXA, validar número/data/dezenas e consultar o concurso mais recente. Como o índice da fonte pode ficar defasado, o cliente verifica concursos subsequentes; resultados de até 300 concursos são buscados com paralelismo limitado.
10. **Cache e indisponibilidade:** cache JSON local, escrita atômica e TTL de 10 minutos; em falha de rede, o uso do cache é explicitamente identificado como recente ou desatualizado. Sem cache válido, a API retorna HTTP 503. Credenciais e dados de cache não são adicionados ao Git.
11. **API/CLI/UI:** rotas de resultados, análise, geração, simulação e testes aceitam modalidade e fonte; CLI tem `resultados` e `analisar`. O dashboard exibe concursos oficiais, permite atualização forçada e seleciona as três modalidades suportadas, com limites de dezenas adequados. Modalidades não suportadas aparecem desabilitadas.

## Estrutura e responsabilidades

O código de domínio está principalmente na raiz; os módulos em `core/` reexportam módulos-raiz como compatibilidade. Essa duplicidade é intencional na versão atual, mas é uma decisão arquitetural a acompanhar para evitar divergência no futuro.

| Caminho | Responsabilidade |
|---|---|
| `models.py` | Entidades e enumerações: `Concurso`, `LoteriaTipo`, `EstrategiaConfig` e `JogoGerado`. |
| `main_engine.py` | Fachada/orquestrador; instancia motores e encaminha análise, geração, simulação e relatórios. |
| `motor_estatistico.py` | Frequência, atrasos, métricas por dezena, ciclos, coocorrência e matriz de correlação. |
| `motor_matematico.py` | Combinatória, probabilidades teóricas e critérios numéricos, como Fibonacci. |
| `motor_estrategias.py` | Cadastro e aplicação de filtros configuráveis sobre jogos candidatos. |
| `motor_score.py` | Normaliza métricas e calcula score ponderado e ranking de dezenas. |
| `motor_simulacoes.py` | Monte Carlo, backtests walk-forward e agregação de resultados. |
| `gerador_jogos.py` | Combina métodos aleatório, score, frequência, atraso, balanceado, Fibonacci, estratégia e desdobramento. |
| `motor_desdobramentos.py` | Combinações e coberturas reduzidas sobre conjuntos-base. |
| `motor_temporal.py` | Intervalos, ciclos, momentum, sazonalidade, tendências e ranking heurístico. |
| `motor_padroes.py` | Padrões de distribuição, primos, simetria, distância e clusters. |
| `motor_comparativo.py` | Testes qui-quadrado, Kolmogorov–Smirnov e runs, além de comparações. |
| `motor_genetico.py` | Evolução de combinações por fitness; inicializado sob demanda pelo orquestrador. |
| `motor_ml.py` | Modelos de ML disponíveis no módulo; não é uma opção da lista de métodos da CLI/web nesta configuração. |
| `motor_relatorios.py` | Relatórios executivos, JSON e dados para CSV/simulações. |
| `caixa_client.py` | Cliente CAIXA, validação do payload oficial e cache local com fallback identificado. |
| `app.py`, `templates/`, `static/` | Aplicação FastAPI, sessão de login, páginas e assets do dashboard. |
| `run.py` | CLI de demonstração, consulta oficial, análise, geração, simulação e testes. |
| `test_motores.py`, `tests/` | Testes de domínio, cliente CAIXA, API, integração, cache e regressões. |
| `requirements.txt`, `Dockerfile`, `docker-compose.yml` | Dependências Python, imagem e execução web containerizada. |

## Fluxo da lógica

1. O cliente consulta o endpoint HTTPS da CAIXA, valida e ordena as dezenas, valida número/data/modalidade e converte cada concurso em objeto `Concurso`. A integração e suas limitações estão em [FONTES_DADOS_CAIXA.md](FONTES_DADOS_CAIXA.md).
2. Um cache local reduz chamadas. O cache é gravado atomicamente; falhas não são convertidas em dados sintéticos. A resposta informa idade/origem do cache; sem cache, o serviço falha de forma explícita.
3. `MotorPrincipal` ordena o histórico e compõe os motores de estatística, score, estratégia, tempo, padrões, testes, simulação, relatório e geração.
4. Os motores calculam métricas descritivas a partir do histórico. O score pondera frequência absoluta/recente, atraso, tendência, ciclos e correlação; o gerador seleciona combinações conforme o método escolhido.
5. A simulação cria jogos aleatórios e os compara com concursos históricos. Backtests separam janelas de treino/teste em ordem temporal.
6. A API web verifica sessão antes de expor resultados e análises; o login usa credenciais de ambiente e proteção de tentativas por endereço IP em memória.

A aleatoriedade dos sorteios significa que frequência histórica, atraso, score e modelos não devem ser tratados como vantagem preditiva. Os testes estatísticos descrevem uma amostra e não demonstram previsibilidade.

## Como executar

Requisitos: Python 3.10 ou superior e `pip`.

```bash
git clone https://github.com/kukukukla/LottoIA-.git
cd LottoIA-
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt

# Testes e demonstração
python -m pytest -q
python run.py demo
python run.py gerar --metodo score --dezenas 15 --jogos 5
python run.py simular --n 10000
```

Para executar a aplicação web localmente, defina credenciais próprias antes de iniciar. Use uma chave aleatória estável por instalação; não reutilize a chave de demonstração abaixo em produção:

```bash
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="substitua-por-uma-senha-forte"
python app.py
```

A aplicação escuta a porta 5000. Os endpoints de geração/simulação e o dashboard exigem login. Sem usuário e senha de administrador, nenhum login é aceito.

### Docker Compose

Crie um arquivo `.env` local (não o versione) com os três valores abaixo, usando credenciais próprias:

```dotenv
SESSION_SECRET=gere-um-segredo-aleatorio-longo
ADMIN_USERNAME=admin
ADMIN_PASSWORD=senha-forte
```

Em seguida, execute:

```bash
docker compose up --build -d
```

O serviço web fica na porta 5000. Se o tráfego for servido por HTTPS atrás de um proxy TLS, configure `SESSION_HTTPS_ONLY=true` no ambiente do container para cookies `Secure`. O Compose atual não provisiona PostgreSQL, Redis nem frontend React; as definições de banco/cache no YAML estão comentadas.

## Testes e desempenho observado

Validação executada no sandbox, Python 3.12.3:

- `python -m compileall -q .`: passou.
- `python -m pytest -q`: **45 testes passaram** na rodada final, incluindo parsing e rejeição de payloads CAIXA inválidos, descoberta do concurso mais recente, cache/fallback offline e integração autenticada das rotas/modalidades.
- `python -m compileall -q .`, `node --check static/js/dashboard.js` e `git diff --check`: passaram.
- Teste HTTP com `TestClient`: login, dashboard, autorização, limites, resultados, análise, geração, simulação e testes estatísticos passaram usando cliente CAIXA controlado por mocks (sem tráfego externo na suíte).
- `python run.py demo`: conclusão normal.
- Consultas oficiais ao vivo confirmaram Lotofácil #3811, Mega-Sena #3073 e Lotomania #2990 em 23/10/2026; geração `score` da Lotofácil executada com histórico real de 5 concursos.
- Docker não estava instalado no ambiente, portanto não foi possível executar `docker build` ou validar o container em runtime.

Tempos de parede observados em execuções locais pontuais (incluem inicialização do interpretador; não são SLA nem benchmark de produção):

| Operação | Tempo observado |
|---|---:|
| `python run.py demo` | ~0,86 s |
| `python run.py simular --n 10000` | ~0,77 s |
| `python run.py gerar --metodo score --dezenas 15 --jogos 5` | ~0,94 s |
| GET autenticado `/api/simular?n=10000` com `TestClient` | ~0,15 s |
| Núcleo Monte Carlo, 10.000 trials, 300 concursos já carregados | ~0,084 s |

Os valores variam por CPU, versões NumPy/SciPy e carga do host. O custo do Monte Carlo cresce aproximadamente de forma linear com o número de trials; a pontuação por dezena depende do tamanho do universo, do histórico e da matriz de coocorrência. O cálculo da correlação por score foi reduzido de uma construção por dezena para uma por chamada. A implementação da matriz estatística ainda contém loops Python sobre concursos/dezenas e pode ser otimizada para universos maiores ou históricos extensos.

## Limitações e próximos passos técnicos

- O endpoint público da CAIXA não fornece contrato de API versionado. A busca de concurso próximo infere a ausência de concurso futuro em respostas HTTP 404/500, comportamento que pode mudar; consulte `FONTES_DADOS_CAIXA.md`. O botão Atualizar força nova consulta, mas não substitui monitoramento de disponibilidade do provedor.
- Para buscar até 300 resultados históricos, o serviço faz várias chamadas por concurso (paralelismo limitado a 4 por padrão); a latência e os limites de requisição dependem da CAIXA. O cache local é por instalação/contêiner e não é compartilhado entre réplicas.
- A proteção contra força bruta é um contador em memória: reinicia com o processo e não coordena múltiplas réplicas. Para implantação distribuída, mova o rate limit para um armazenamento compartilhado e configure proxy/IP confiável.
- Os testes de cliente e API são offline e usam respostas simuladas. Foi feita consulta real à CAIXA durante o desenvolvimento, mas os testes não garantem disponibilidade futura nem substituem monitoramento, testes de carga ou revisão independente de segurança.
- O score e os métodos de geração são heurísticas e critérios descritivos; não oferecem previsão de sorteios.
