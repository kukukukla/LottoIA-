# Motor Estatístico de Inteligência para Loterias v2.0

Plataforma profissional de análise quantitativa para loterias brasileiras (Lotofácil, Mega-Sena, Lotomania).

> ⚠️ Ferramenta de análise estatística — não prevê resultados nem aumenta probabilidades reais de acerto.

## Stack

- **Language**: Python 3.12
- **Key dependencies**: numpy, scipy, scikit-learn, pyyaml

## How to run

```bash
# Demonstração completa (padrão)
python run.py demo

# Gerar jogos
python run.py gerar --metodo score --dezenas 15 --jogos 5

# Simulação Monte Carlo
python run.py simular --n 1000

# Testes estatísticos
python run.py testar
```

The Replit workflow runs `python run.py demo` by default.

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
