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
- [Licença](#-licença)

---

## ✨ Funcionalidades

- ✅ **12 Motores Especializados** — Análise multidimensional completa
- ✅ **25+ Filtros de Estratégia** — Composição de jogos altamente configurável
- ✅ **10 Métodos de Geração** — Aleatório, Score, Frequência, Atraso, Balanceado, Fibonacci, Genético, ML, etc.
- ✅ **Simulações Monte Carlo** — Backtests e comparação de estratégias
- ✅ **Machine Learning** — Random Forest, Gradient Boosting, Logistic Regression
- ✅ **Algoritmo Genético** — Evolução de jogos com fitness configurável
- ✅ **Testes Estatísticos** — Qui-quadrado, Kolmogorov-Smirnov, Runs
- ✅ **Análise Temporal** — Ciclos, momentum, sazonalidade, regressão
- ✅ **Padrões Avançados** — Geométricos, numéricos, clusters
- ✅ **Exportação** — Relatórios JSON, CSV, executivo

---

## 🏗️ Arquitetura

```
loterias_inteligencia/
├── core/           # 16 módulos Python (4.410 linhas)
│   ├── models.py              # Entidades do domínio
│   ├── main_engine.py         # Orquestrador principal
│   ├── motor_estatistico.py   # Análise estatística
│   ├── motor_matematico.py    # Combinatória e probabilidade
│   ├── motor_simulacoes.py    # Monte Carlo e backtests
│   ├── motor_estrategias.py   # 25+ filtros configuráveis
│   ├── motor_score.py         # Pontuação de dezenas
│   ├── motor_desdobramentos.py # Fechamentos matemáticos
│   ├── motor_temporal.py      # Séries temporais
│   ├── motor_ml.py            # Machine Learning
│   ├── motor_padroes.py       # Padrões geométricos/numéricos
│   ├── motor_comparativo.py   # Testes estatísticos
│   ├── motor_genetico.py      # Algoritmo genético
│   ├── motor_relatorios.py    # Exportação de dados
│   └── gerador_jogos.py       # Gerador unificado
├── scripts/        # Scripts de execução
├── tests/          # Testes automatizados
├── data/           # Dados históricos
├── docs/           # Documentação e imagens
├── config/         # Configurações
└── notebooks/      # Jupyter notebooks
```

---

## 🚀 Instalação

### Requisitos

- Python 3.10+
- pip

### Passo a passo

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd loterias_inteligencia

# 2. Crie um ambiente virtual (recomendado)
python -m venv venv

# Ative o ambiente:
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute a demonstração
python scripts/demo.py
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

### Docker (recomendado)

```bash
# Construir imagem
docker build -t loterias-inteligencia .

# Executar
docker run -p 8000:8000 loterias-inteligencia
```

### Docker Compose

```bash
docker-compose up -d
```

Serviços incluídos:
- **API** (FastAPI) na porta 8000
- **PostgreSQL** na porta 5432
- **Redis** na porta 6379
- **Frontend** (React) na porta 3000

---

## 🧪 Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=core --cov-report=html
```

---

## 📚 Documentação

- `docs/RESUMO_SISTEMA.txt` — Documentação técnica completa
- `docs/dashboard_demo.png` — Screenshots do dashboard
- `notebooks/` — Jupyter notebooks com exemplos

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
