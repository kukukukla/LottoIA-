# Motor Estatístico de Inteligência para Loterias v2.0

Plataforma profissional de análise quantitativa para loterias brasileiras (Lotofácil, Mega-Sena, Lotomania).

> ⚠️ Ferramenta de análise estatística — não prevê resultados nem aumenta probabilidades reais de acerto.

## Stack

- **Language**: Python 3.12
- **Key dependencies**: numpy, scipy, scikit-learn, pyyaml

## How to run

The Replit workflow runs `python app.py` — the FastAPI web server on port 5000.

```
http://localhost:5000/          → Login
http://localhost:5000/dashboard → Dashboard (requires login)
```

**Credentials (test):** `admin / loterias2024` · `demo / demo123`

### CLI (optional)
```bash
python run.py demo
python run.py gerar --metodo score --dezenas 15 --jogos 5
python run.py simular --n 1000
python run.py testar
```

### API endpoints
| Endpoint | Descrição |
|---|---|
| `GET /api/analise` | Frequência, atraso e score |
| `GET /api/gerar?metodo=score&dezenas=15&jogos=5` | Gerar jogos |
| `GET /api/simular?n=1000` | Monte Carlo |
| `GET /api/testes` | Qui-quadrado, KS, Runs |

## Project structure

All engine modules live at the root level. A `core/` package provides shim re-exports so that `from core.X import *` works as expected by `run.py` and `demo.py`.

| File | Purpose |
|------|---------|
| `run.py` | CLI entry point |
| `demo.py` | Standalone demo script |
| `main_engine.py` | Main orchestrator (12 engines) |
| `models.py` | Domain entities (Concurso, LoteriaTipo, …) |
| `motor_estatistico.py` | Frequency, delay, sequences, sums |
| `motor_matematico.py` | Combinatorics & probability |
| `motor_simulacoes.py` | Monte Carlo & backtests |
| `motor_estrategias.py` | 25+ configurable filters |
| `motor_score.py` | Dezena scoring |
| `motor_desdobramentos.py` | Mathematical closures |
| `motor_temporal.py` | Cycles, momentum, seasonality |
| `motor_padroes.py` | Geometric/numeric/cluster patterns |
| `motor_comparativo.py` | Chi-square, KS, runs tests |
| `motor_genetico.py` | Genetic algorithm |
| `motor_relatorios.py` | JSON/CSV/executive reports |
| `gerador_jogos.py` | Standalone game generator |
| `core/` | Shim re-exports for the above modules |

## User preferences

- Keep the existing flat module structure; use `core/` shims to satisfy package imports.
