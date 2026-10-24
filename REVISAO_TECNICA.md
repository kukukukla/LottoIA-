# Revisão técnica do LottoIA

## Resumo executivo

A revisão foi feita sobre a branch `main` do repositório `kukukukla/LottoIA-`. As correções incluídas nesta atualização abrangem importação e API pública do pacote `core`, simulação Monte Carlo, autenticação/sessões, limites de requisição, dependências web e configuração do container. Foi também evitado um cálculo repetido da matriz de correlação no cálculo de scores.

A aplicação pode ser executada como CLI ou como serviço FastAPI. A CLI oferece uma demonstração sintética explícita e também consulta resultados oficiais da CAIXA para Lotofácil, Mega-Sena e Lotomania. A API e o dashboard usam a CAIXA por padrão, identificam o último concurso e mostram os resultados recentes. Dados sintéticos só são usados quando `fonte=demo`/`--fonte demo` é solicitado ou em `run.py demo`. Rankings e jogos continuam sendo critérios descritivos/heurísticos: não preveem sorteios nem aumentam a probabilidade matemática de acerto.

## Revisões e correções aplicadas

1. **Importações e API pública:** removida da suíte uma alteração de `sys.path` que fazia os shims em `core/` importarem a si mesmos. O pacote `core` agora exporta sob demanda os tipos e motores exemplificados no README (`MotorPrincipal`, `Concurso`, `LoteriaTipo`, `EstrategiaConfig`, `MotorEstatistico`, `MotorScore` e `MotorTemporal`). Os módulos-fonte continuam na raiz; `core/` é uma camada de compatibilidade.
2. **Monte Carlo:** `monte_carlo_aleatorio` agora executa exatamente `n_simulacoes`, inclusive quando esse valor supera a quantidade de concursos disponíveis, amostrando concursos históricos com reposição. Rejeita quantidade inválida, dados históricos ausentes e quantidade inválida de dezenas; usa um gerador NumPy local para não alterar o estado aleatório global.
3. **Score e correlação:** durante cada cálculo de score, a matriz de correlação é calculada uma vez e reutilizada para as dezenas. Antes, a matriz — cujo cálculo percorre os concursos e pares de dezenas — era reconstruída para cada dezena.
4. **Web e sessão:** a chave fixa de desenvolvimento foi removida. Sem `SESSION_SECRET`, uma chave aleatória temporária é criada e registrada como aviso; em produção, deve ser definida de forma estável. O login limpa a sessão antes de atribuí-la, a senha é comparada sem remover espaços e a sessão tem validade de 12 horas. Cookies usam `HttpOnly`/`SameSite=Lax`; `SESSION_HTTPS_ONLY=true` ativa `Secure` em HTTPS. Gravações de jogos exigem token CSRF vinculado à sessão.
5. **Validação de requisições:** `/api/gerar` limita jogos a 1–50 e dezenas a 15–20 (Lotofácil); `/api/simular` aceita 1–10.000 simulações. Valores fora dos limites resultam em HTTP 422.
6. **Dependência do formulário:** incluído `python-multipart`, necessário para que o FastAPI registre e processe o formulário de login.
7. **Container:** a imagem usa `requirements-docker.txt` com as dependências web/motores necessários, inicia FastAPI em `0.0.0.0:5000` dentro do contêiner e o Compose local publica apenas em `127.0.0.1`. O processo roda sem privilégios administrativos. `.dockerignore` exclui `.env`, banco e cache do build context. O Compose exige segredos e monta volume persistente; a imagem inclui health check.
8. **Testes:** adicionados testes de regressão para quantidade exata de simulações, rejeição de entrada inválida e cálculo único da matriz de correlação.
9. **Resultados CAIXA:** criado `caixa_client.py` para mapear modalidades internas aos slugs da CAIXA, validar número/data/dezenas e consultar o concurso mais recente. Como o índice da fonte pode ficar defasado, o cliente verifica concursos subsequentes; resultados de até 300 concursos são buscados com paralelismo limitado.
10. **Cache e indisponibilidade:** cache JSON local, escrita atômica e TTL de 10 minutos; em falha de rede, o uso do cache é explicitamente identificado como recente ou desatualizado. Sem cache válido, a API retorna HTTP 503. Credenciais e dados de cache não são adicionados ao Git.
11. **API/CLI/UI:** rotas de resultados, análise, geração, simulação e testes aceitam modalidade e fonte; CLI tem `resultados` e `analisar`. O dashboard exibe concursos oficiais, permite atualização forçada e seleciona as três modalidades suportadas, com limites de dezenas adequados. Modalidades não suportadas aparecem desabilitadas.
12. **Histórico de jogos:** `games_store.py` persiste lotes nomeados no SQLite local. O lote registra método, modalidade, quantidade, combinações, fonte, concurso-base e horário. A API/área autenticada permite listar histórico, baixar `.txt` e comparar cada combinação com até 100 concursos oficiais, destacando o mais recente e as dezenas coincidentes.
13. **Isolamento e segurança do histórico:** rotas de leitura filtram pelo usuário da sessão; lote alheio não é revelado. Nomes são validados e escapados ao renderizar, exportações têm `Cache-Control: private, no-store`, e o banco/cache não são versionados.

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
| `games_store.py` | Persistência SQLite de lotes nomeados, com filtro por usuário. |
| `app.py`, `templates/`, `static/` | Aplicação FastAPI, sessão de login, páginas e assets do dashboard. |
| `run.py` | CLI de demonstração, consulta oficial, análise, geração, simulação e testes. |
| `test_motores.py`, `tests/` | Testes de domínio, cliente CAIXA, API, integração, cache e regressões. |
| `requirements.txt`, `requirements-docker.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.dockerignore` | Dependências completas/dev e mínimas/web, imagem não-root, exclusão de secrets, volume persistente e configuração local. |

## Fluxo da lógica

1. O cliente consulta o endpoint HTTPS da CAIXA, valida e ordena as dezenas, valida número/data/modalidade e converte cada concurso em objeto `Concurso`. A integração e suas limitações estão em [FONTES_DADOS_CAIXA.md](FONTES_DADOS_CAIXA.md).
2. Um cache local reduz chamadas. O cache é gravado atomicamente; falhas não são convertidas em dados sintéticos. A resposta informa idade/origem do cache; sem cache, o serviço falha de forma explícita.
3. `MotorPrincipal` ordena o histórico e compõe os motores de estatística, score, estratégia, tempo, padrões, testes, simulação, relatório e geração.
4. Os motores calculam métricas descritivas a partir do histórico. O score pondera frequência absoluta/recente, atraso, tendência, ciclos e correlação; o gerador seleciona combinações conforme o método escolhido.
5. A simulação cria jogos aleatórios e os compara com concursos históricos. Backtests separam janelas de treino/teste em ordem temporal.
6. A rota autenticada de criação verifica CSRF, gera o lote com a modalidade/método/quantidade recebidos e grava seus metadados e combinações em SQLite.
7. Histórico, exportação TXT e comparação confirmam proprietário pela sessão. A comparação cruza combinações com resultados CAIXA, apresenta coincidências por concurso e assinala o resultado publicado mais recente.
8. As demais rotas web verificam sessão; login usa credenciais do ambiente e proteção de tentativas por IP em memória.

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

### Docker local

O sandbox de desenvolvimento atual não tem Docker instalado; não foi possível executar o build real desta imagem. Para setup Windows/macOS/Linux, secrets, verificação da instalação, `docker compose up`, volume, backup e publicação web/mobile, consulte [OPERACAO_DOCKER_E_JOGOS.md](OPERACAO_DOCKER_E_JOGOS.md). O `.env.example` é apenas um modelo vazio: preencha os três secrets antes de iniciar. O serviço local vincula em `127.0.0.1:5000`; dados persistem no volume nomeado `lottoia_data`.

## Testes e desempenho observado

Validação executada no sandbox, Python 3.12.3:

- `python -m compileall -q .`: passou.
- `python -m pytest -q`: **53 testes passaram** após a implementação de persistência/CSRF/comparação, incluindo a nova suíte de histórico SQLite e geração nas três modalidades suportadas.
- `python -m compileall -q .`, `node --check static/js/dashboard.js` e `git diff --check`: passaram.
- Teste HTTP com `TestClient`: login, dashboard, autorização, limites, resultados, análise, geração, simulação e testes estatísticos passaram usando cliente CAIXA controlado por mocks (sem tráfego externo na suíte).
- `python run.py demo`: conclusão normal.
- Consulta direta à CAIXA em 24/10/2026 retornou Lotofácil #3812 (apurada em 23/10), após #3811; os snapshots anteriores registraram Mega-Sena #3073 e Lotomania #2990 em 23/10. Geração `score` da Lotofácil também foi executada com histórico real de 5 concursos.
- O `docker-compose.yml` passou parsing YAML e inspeção de mapeamento local/volume. Docker CLI não está instalado neste ambiente, portanto `docker compose config`, build e health check em runtime ainda precisam ser executados no computador local.

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
