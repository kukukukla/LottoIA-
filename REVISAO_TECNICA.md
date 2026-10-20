# Revisão técnica do LottoIA

## Resumo executivo

A revisão foi feita sobre a branch `main` do repositório `kukukukla/LottoIA-`. As correções incluídas nesta atualização abrangem importação e API pública do pacote `core`, simulação Monte Carlo, autenticação/sessões, limites de requisição, dependências web e configuração do container. Foi também evitado um cálculo repetido da matriz de correlação no cálculo de scores.

A aplicação pode ser executada como CLI ou como serviço FastAPI. A demonstração e a aplicação web usam **concursos sintéticos aleatórios**, não uma integração com resultados oficiais da Caixa. Portanto, os rankings e jogos gerados são demonstrações estatísticas, não previsões, e não aumentam a probabilidade matemática de acerto.

## Revisões e correções aplicadas

1. **Importações e API pública:** removida da suíte uma alteração de `sys.path` que fazia os shims em `core/` importarem a si mesmos. O pacote `core` agora exporta sob demanda os tipos e motores exemplificados no README (`MotorPrincipal`, `Concurso`, `LoteriaTipo`, `EstrategiaConfig`, `MotorEstatistico`, `MotorScore` e `MotorTemporal`). Os módulos-fonte continuam na raiz; `core/` é uma camada de compatibilidade.
2. **Monte Carlo:** `monte_carlo_aleatorio` agora executa exatamente `n_simulacoes`, inclusive quando esse valor supera a quantidade de concursos disponíveis, amostrando concursos históricos com reposição. Rejeita quantidade inválida, dados históricos ausentes e quantidade inválida de dezenas; usa um gerador NumPy local para não alterar o estado aleatório global.
3. **Score e correlação:** durante cada cálculo de score, a matriz de correlação é calculada uma vez e reutilizada para as dezenas. Antes, a matriz — cujo cálculo percorre os concursos e pares de dezenas — era reconstruída para cada dezena.
4. **Web e sessão:** a chave fixa de desenvolvimento foi removida. Sem `SESSION_SECRET`, uma chave aleatória temporária é criada e registrada como aviso; em produção, deve ser definida de forma estável. O login limpa a sessão antes de atribuí-la, a senha é comparada sem remover espaços e a sessão tem validade de 12 horas. `SESSION_HTTPS_ONLY=true` ativa o atributo Secure para uso atrás de HTTPS.
5. **Validação de requisições:** `/api/gerar` limita jogos a 1–50 e dezenas a 15–20 (Lotofácil); `/api/simular` aceita 1–10.000 simulações. Valores fora dos limites resultam em HTTP 422.
6. **Dependência do formulário:** incluído `python-multipart`, necessário para que o FastAPI registre e processe o formulário de login.
7. **Container:** Docker e Compose iniciam o servidor web em `0.0.0.0:5000`, não apenas a demonstração CLI. O Compose exige `SESSION_SECRET`, `ADMIN_USERNAME` e `ADMIN_PASSWORD` no ambiente.
8. **Testes:** adicionados testes de regressão para quantidade exata de simulações, rejeição de entrada inválida e cálculo único da matriz de correlação.

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
| `app.py`, `templates/`, `static/` | Aplicação FastAPI, sessão de login, páginas e assets do dashboard. |
| `run.py` | CLI de demonstração, geração, simulação e testes estatísticos. |
| `test_motores.py` | Suíte de testes automatizados de domínio e regressão. |
| `requirements.txt`, `Dockerfile`, `docker-compose.yml` | Dependências Python, imagem e execução web containerizada. |

## Fluxo da lógica

1. Os concursos são representados como objetos `Concurso`, associados a uma `LoteriaTipo`.
2. `MotorPrincipal` ordena o histórico e compõe os motores de estatística, score, estratégia, tempo, padrões, testes, simulação, relatório e geração.
3. Os motores calculam métricas descritivas a partir do histórico. O score pondera frequência absoluta/recente, atraso, tendência, ciclos e correlação; o gerador seleciona combinações conforme o método escolhido.
4. A simulação cria um jogo aleatório e o compara com uma amostra de concursos históricos. Backtests separam janelas de treino/teste em ordem temporal.
5. A API web verifica sessão antes de expor análises, geração e simulação; o login usa credenciais de ambiente e proteção de tentativas por endereço IP em memória.

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
- `python -m pytest -q`: **16 testes passaram** após adicionar a regressão de correlação.
- Teste HTTP com `TestClient`: login, dashboard, autorização, limites, geração e simulação passaram.
- `python run.py demo`: conclusão normal.
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

- A API e o CLI geram dados sintéticos para demonstração; não há, nesta versão, carregador que atualize automaticamente resultados oficiais. O CSV de exemplo não é usado automaticamente.
- A proteção contra força bruta é um contador em memória: reinicia com o processo e não coordena múltiplas réplicas. Para implantação distribuída, mova o rate limit para um armazenamento compartilhado e configure proxy/IP confiável.
- Os testes atuais validam motores principais e regressões específicas; não substituem testes de integração de produção, testes de carga, revisão de segurança independente ou validação de dados reais.
- O score e os métodos de geração são heurísticas e critérios descritivos; não oferecem previsão de sorteios.
