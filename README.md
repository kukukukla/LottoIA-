# 🎲 Motor Estatístico de Inteligência para Loterias v2.0

Plataforma profissional de análise quantitativa para loterias brasileiras (Lotofácil, Mega-Sena, Lotomania), baseada exclusivamente em matemática, estatística, simulações e análise histórica.

> ⚠️ **AVISO IMPORTANTE**: Este sistema é uma ferramenta de **análise estatística** e **NÃO** prevê resultados de sorteios nem aumenta as probabilidades reais de acerto. Sorteios são eventos aleatórios independentes.

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Instalação](#-instalação)
- [Uso Rápido](#-uso-rápido)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Motores Especializados](#-motores-especializados)
- [Estratégias Configuráveis](#-estratégias-configuráveis)
- [Testes Estatísticos](#-testes-estatísticos)
- [Deploy](#-deploy)
- [Revisão técnica](REVISAO_TECNICA.md)
- [Licença](#-licença)

---

## ✨ Funcionalidades

- ✅ **Motores estatísticos e matemáticos** — Análise de frequência, atraso, combinatória, padrões e séries temporais
- ✅ **Filtros de estratégia** — Composição de jogos configurável
- ✅ **Geração de jogos** — Aleatório, Score, Frequência, Atraso, Balanceado, Fibonacci, estratégias e desdobramentos
- ✅ **Simulações Monte Carlo** — Backtests e comparação de estratégias
- ✅ **Módulo de Machine Learning** — Implementação disponível em `motor_ml.py`
- ✅ **Algoritmo Genético** — Evolução de jogos com fitness configurável
- ✅ **Testes Estatísticos** — Qui-quadrado, Kolmogorov-Smirnov, Runs
- ✅ **Análise Temporal** — Ciclos, momentum, sazonalidade, regressão
- ✅ **Padrões Avançados** — Geométricos, numéricos, clusters
- ✅ **Exportação** — Relatórios JSON, CSV, executivo

---

## 🏗️ Arquitetura

```
LottoIA/
├── app.py                    # Aplicação web FastAPI e autenticação por sessão
├── run.py                    # CLI: demo, geração, simulação e testes estatísticos
├── models.py                 # Entidades do domínio e tipos de loteria
├── main_engine.py            # Orquestrador dos motores
├── gerador_jogos.py          # Geração unificada de combinações
├── motor_*.py                # Motores estatístico, matemático, temporal, ML etc.
├── core/                     # Shims de compatibilidade e exports públicos
├── templates/ + static/      # HTML, CSS, JavaScript e imagens do dashboard
├── test_motores.py            # Testes pytest (inclui regressões)
├── requirements.txt           # Dependências Python
├── Dockerfile                 # Imagem que serve a aplicação web
├── docker-compose.yml         # Serviço web; requer secrets no ambiente
└── REVISAO_TECNICA.md         # Revisão, limitações, execução e desempenho
```

Os módulos de implementação ficam na raiz; os módulos em `core/` reexportam os módulos legados. A aplicação e o CLI usam dados sintéticos na demonstração; não há carregamento automático de resultados oficiais.

---

## 🚀 Instalação

### Requisitos

- Python 3.10+
- pip

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/kukukukla/LottoIA-.git
cd LottoIA-

# 2. Crie um ambiente virtual (recomendado)
python3 -m venv .venv

# Ative o ambiente:
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instale as dependências
python -m pip install -r requirements.txt

# 4. Execute testes e demonstração
python -m pytest -q
python run.py demo
```

---

## ⚡ Uso Rápido

### Via Orquestrador Principal (recomendado)

```python
from core import MotorPrincipal, Concurso, LoteriaTipo, EstrategiaConfig

# Carregar concursos históricos
concursos = [...]  # lista de objetos Concurso

# Inicializar sistema
motor = MotorPrincipal(concursos)

# Análise completa
analise = motor.analise_completa()

# Gerar jogos por score
jogos = motor.gerar_jogos("score", n_dezenas=15, n_jogos=5)

# Criar estratégia personalizada
config = EstrategiaConfig(
    nome="Estratégia Híbrida",
    loteria=LoteriaTipo.LOTOFACIL,
    quantidade_dezenas=15,
    filtros={
        "frequencia_historica": {"max_rank": 15},
        "dezenas_atrasadas": {"min_atraso": 2, "max_atraso": 10},
        "equilibrio_par_impar": {"pares": 7, "impares": 8},
        "soma_dezenas": {"min_soma": 170, "max_soma": 220}
    }
)
id_estr = motor.criar_estrategia(config)
jogos = motor.gerar_por_estrategia(id_estr, n_jogos=3)

# Simulação Monte Carlo
relatorio = motor.simular_monte_carlo(n_simulacoes=1000)

# Testar aleatoriedade
testes = motor.testar_aleatoriedade()

# Relatório executivo
rel_exec = motor.relatorio_executivo()
```

### Via Motores Individuais

```python
from core import MotorEstatistico, MotorScore, MotorTemporal

# Análise estatística
est = MotorEstatistico(concursos)
freq = est.frequencia_absoluta()
atraso = est.atraso_atual()
relatorio = est.relatorio_completo()

# Score de dezenas
score = MotorScore(concursos)
top10 = score.top_dezenas(10)
explicacao = score.explicar_score(10)

# Análise temporal
temporal = MotorTemporal(concursos)
predicoes = temporal.ranking_predicoes()
ciclos = temporal.detectar_ciclos(10)
```

---

## 🔧 Motores Especializados

| Motor | Descrição | Métodos |
|-------|-----------|---------|
| **Estatístico** | Frequência, atraso, distribuição, correlação | 14 |
| **Matemático** | Combinatória, probabilidades, Fibonacci | 12 |
| **Simulações** | Monte Carlo, backtests walk-forward | 8 |
| **Estratégias** | 25+ filtros configuráveis com CRUD | 25+ |
| **Score** | Pontuação ponderada com explicação | 6 |
| **Desdobramentos** | Fechamentos com garantia (guloso) | 8 |
| **Temporal** | Ciclos, momentum, sazonalidade, regressão | 8 |
| **ML** | Random Forest, Gradient Boosting, Logistic | 5 |
| **Padrões** | Geométricos, primos, clusters, simetria | 10 |
| **Comparativo** | Testes χ², KS, runs, convergência | 8 |
| **Genético** | Evolução com fitness configurável | 7 |
| **Relatórios** | Exportação JSON, CSV, executivo | 4 |

---

## 🎯 Estratégias Configuráveis

### Categorias de Filtros

| Categoria | Filtros |
|-----------|---------|
| **Frequência** | `frequencia_historica`, `frequencia_recente`, `dezenas_quentes`, `dezenas_frias` |
| **Atraso** | `dezenas_atrasadas`, `atraso_relativo`, `atraso_acima_media` |
| **Distribuição** | `equilibrio_par_impar`, `equilibrio_baixo_alto`, `distribuicao_linhas` |
| **Soma** | `soma_dezenas`, `media_dezenas`, `desvio_padrao` |
| **Sequência** | `sequencias_limitadas`, `gap_maximo` |
| **Repetição** | `repeticoes_controladas`, `dezenas_do_ultimo` |
| **Especiais** | `criterio_fibonacci`, `criterio_primos`, `terminacoes` |
| **Tendência** | `tendencia`, `momentum_positivo`, `ciclo_dominante` |

### Exemplo de Estratégia

```python
config = EstrategiaConfig(
    nome="Estratégia Avançada",
    loteria=LoteriaTipo.LOTOFACIL,
    quantidade_dezenas=15,
    filtros={
        "frequencia_historica": {"max_rank": 18},
        "dezenas_atrasadas": {"min_atraso": 1, "max_atraso": 8},
        "equilibrio_par_impar": {"pares": 7, "impares": 8},
        "equilibrio_baixo_alto": {"baixos": 7, "altos": 8},
        "soma_dezenas": {"min_soma": 170, "max_soma": 220},
        "sequencias_limitadas": {"max_sequencias": 4},
        "criterio_fibonacci": {"min_fibonacci": 2, "max_fibonacci": 5},
        "repeticoes_controladas": {"max_repeticoes": 8}
    },
    pesos={"frequencia": 0.3, "atraso": 0.3, "diversidade": 0.2, "balanceamento": 0.2}
)
```

---

## 📊 Testes Estatísticos

O sistema inclui testes rigorosos para verificar a aleatoriedade dos dados:

- **Qui-Quadrado (χ²)**: Verifica uniformidade da distribuição
- **Kolmogorov-Smirnov**: Compara com distribuição uniforme teórica
- **Teste de Runs**: Detecta padrões não aleatórios em sequências

Resultados esperados para sorteios verdadeiramente aleatórios:
- p-value > 0.05 (não rejeita hipótese de uniformidade)
- z-score próximo de 0 (sequência aleatória)

---

## 🐳 Deploy

O container inicia a aplicação FastAPI na porta 5000. Configure as credenciais em um `.env` local (não versionado) antes de subir:

```dotenv
SESSION_SECRET=gere-um-segredo-aleatorio-longo
ADMIN_USERNAME=admin
ADMIN_PASSWORD=senha-forte
```

```bash
docker compose up --build -d
```

O Compose atual contém somente o serviço web. As configurações de PostgreSQL e Redis no YAML estão comentadas; não há frontend React configurado neste repositório. Em produção atrás de TLS, configure `SESSION_HTTPS_ONLY=true` no ambiente do serviço.

---

## 🧪 Testes

```bash
# Executar todos os testes
python -m pytest -q
```

---

## 📚 Documentação

- [Revisão técnica](REVISAO_TECNICA.md) — arquitetura, lógica, validações, limitações, desempenho medido e instruções
- `RESUMO_SISTEMA.txt` — Resumo do sistema
- `exemplo_completo.ipynb` — Notebook de exemplo
- `dashboard_demo_2.png` — Imagem demonstrativa do dashboard

---

## ⚠️ Aviso Legal

Este software é fornecido **"como está"** para fins de **estudo estatístico** e **entretenimento**.

**O sistema NÃO:**
- Prever resultados futuros de sorteios
- Aumentar probabilidades reais de acerto
- Garantir retorno financeiro

**Recomendações:**
- Use como ferramenta de análise, não como única base de decisão
- Lembre-se que cada sorteio é um evento independente
- Jogue com responsabilidade e dentro de sua capacidade financeira
- Considere os jogos como entretenimento, não investimento

---

## 📄 Licença

MIT License — Livre para uso, modificação e distribuição.

---

## 👥 Contribuição

Contribuições são bem-vindas! Por favor, abra uma issue ou pull request.

---

**Desenvolvido com Python, Matemática e Estatística.**
