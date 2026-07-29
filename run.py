#!/usr/bin/env python3
"""
Lotérias Inteligência - Script Principal de Execução
Uso: python run.py [comando] [opcoes]

Comandos:
    demo        → Executa demonstração completa
    analise     → Análise estatística rápida
    gerar       → Gera jogos (requer --metodo e --dezenas)
    simular     → Simulação Monte Carlo
    testar      → Testes estatísticos de aleatoriedade
    estrategia  → Cria e aplica estratégia

Exemplos:
    python run.py demo
    python run.py gerar --metodo score --dezenas 15 --jogos 5
    python run.py simular --n 1000
    python run.py testar
"""

import sys
import argparse
import random
import numpy as np
from datetime import date, timedelta

sys.path.insert(0, 'core')

from core.models import Concurso, LoteriaTipo, EstrategiaConfig
from core.main_engine import MotorPrincipal


def gerar_dados_teste(loteria: LoteriaTipo, n_concursos: int = 300) -> list:
    """Gera dados históricos simulados para demonstração."""
    concursos = []
    data_base = date(2000, 1, 1)
    for i in range(1, n_concursos + 1):
        dezenas = sorted(random.sample(
            range(1, loteria.dezenas_totais + 1),
            loteria.dezenas_sorteadas
        ))
        concursos.append(Concurso(
            numero=i,
            data=data_base + timedelta(days=i * 3),
            dezenas=dezenas,
            loteria=loteria
        ))
    return concursos


def cmd_demo(args):
    """Executa demonstração completa."""
    print("=" * 70)
    print("  MOTOR ESTATÍSTICO DE LOTERIAS v2.0 - DEMONSTRAÇÃO")
    print("=" * 70)

    random.seed(42)
    np.random.seed(42)

    print("\n📊 Gerando dados de teste (Lotofácil, 300 concursos)...")
    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    motor = MotorPrincipal(concursos)
    print(f"   ✓ {len(concursos)} concursos | 12 motores ativos")

    # Resumo estatístico
    print("\n📈 ESTATÍSTICAS RÁPIDAS")
    print("-" * 50)
    freq = motor.estatistico.frequencia_absoluta()
    top5 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
    print("   Top 5 mais frequentes:")
    for d, f in top5:
        print(f"      Dezena {d:2d}: {f} ocorrências")

    atraso = motor.estatistico.atraso_atual()
    atrasadas = sorted(atraso.items(), key=lambda x: x[1], reverse=True)[:5]
    print("\n   Top 5 mais atrasadas:")
    for d, a in atrasadas:
        print(f"      Dezena {d:2d}: {a} concursos")

    # Score
    print("\n⭐ TOP 10 SCORE")
    top10 = motor.score.top_dezenas(10)
    for s in top10:
        print(f"      #{s.ranking:2d} Dezena {s.dezena:2d}: Score={s.score_total:.4f}")

    # Jogos
    print("\n🎲 JOGOS GERADOS")
    metodos = [("Aleatório", "aleatorio", {}), ("Score", "score", {"top_n": 20})]
    for nome, met, params in metodos:
        jogo = motor.gerar_jogos(met, 15, 1, params)[0]
        print(f"   {nome}: {jogo['dezenas']}")

    # Simulação
    print("\n🎰 MONTE CARLO (1.000 simulações)")
    rel = motor.simulacoes.monte_carlo_aleatorio(1000, 15, seed=42)
    print(f"   Média acertos: {rel.media_acertos}")
    print(f"   Máximo: {rel.max_acertos} | Desvio: {rel.desvio_padrao}")

    # Testes
    print("\n📐 TESTES DE ALEATORIEDADE")
    chi = motor.comparativo.teste_chi_quadrado(concursos)
    print(f"   Qui-Quadrado: p={chi['p_value']:.4f} → {chi['interpretacao']}")

    print("\n" + "=" * 70)
    print("  ✅ DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 70)


def cmd_gerar(args):
    """Gera jogos pelo método especificado."""
    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    motor = MotorPrincipal(concursos)

    jogos = motor.gerar_jogos(
        args.metodo,
        n_dezenas=args.dezenas,
        n_jogos=args.jogos
    )

    print(f"\n🎲 Jogos gerados pelo método '{args.metodo}':")
    for i, j in enumerate(jogos, 1):
        print(f"   Jogo {i}: {j['dezenas']}")


def cmd_simular(args):
    """Executa simulação Monte Carlo."""
    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    motor = MotorPrincipal(concursos)

    print(f"\n🎰 Executando Monte Carlo ({args.n} simulações)...")
    rel = motor.simulacoes.monte_carlo_aleatorio(args.n, 15)

    print(f"\n   Total: {rel.total_simulacoes}")
    print(f"   Média: {rel.media_acertos}")
    print(f"   Máx/Mín: {rel.max_acertos}/{rel.min_acertos}")
    print(f"   Desvio: {rel.desvio_padrao}")
    print("\n   Distribuição:")
    for k, v in sorted(rel.acertos_percentual.items()):
        print(f"      {k:2d} acertos: {v:6.2f}%")


def cmd_testar(args):
    """Executa testes estatísticos."""
    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    motor = MotorPrincipal(concursos)

    print("\n📐 TESTES ESTATÍSTICOS DE ALEATORIEDADE")
    print("-" * 50)

    chi = motor.comparativo.teste_chi_quadrado(concursos)
    print(f"\n1. Qui-Quadrado:")
    print(f"   χ² = {chi['chi2']}")
    print(f"   p-value = {chi['p_value']}")
    print(f"   → {chi['conclusao']}")

    ks = motor.comparativo.teste_ks(concursos)
    print(f"\n2. Kolmogorov-Smirnov:")
    print(f"   Estatística = {ks['statistic']}")
    print(f"   p-value = {ks['p_value']}")
    print(f"   → {ks['interpretacao']}")

    runs = motor.comparativo.teste_runs(concursos, 1)
    print(f"\n3. Teste de Runs (Dezena 1):")
    print(f"   z-score = {runs['z_score']}")
    print(f"   → {runs['interpretacao']}")


def main():
    parser = argparse.ArgumentParser(
        description="Motor Estatístico de Inteligência para Loterias",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python run.py demo
  python run.py gerar --metodo score --dezenas 15 --jogos 5
  python run.py simular --n 1000
  python run.py testar
        """
    )

    subparsers = parser.add_subparsers(dest='comando', help='Comando a executar')

    # demo
    subparsers.add_parser('demo', help='Demonstração completa')

    # gerar
    gerar_parser = subparsers.add_parser('gerar', help='Gerar jogos')
    gerar_parser.add_argument('--metodo', required=True, choices=['aleatorio', 'score', 'frequencia', 'atraso', 'balanceado', 'fibonacci'])
    gerar_parser.add_argument('--dezenas', type=int, default=15)
    gerar_parser.add_argument('--jogos', type=int, default=1)

    # simular
    sim_parser = subparsers.add_parser('simular', help='Simulação Monte Carlo')
    sim_parser.add_argument('--n', type=int, default=1000, help='Número de simulações')

    # testar
    subparsers.add_parser('testar', help='Testes estatísticos')

    args = parser.parse_args()

    if not args.comando:
        parser.print_help()
        return

    comandos = {
        'demo': cmd_demo,
        'gerar': cmd_gerar,
        'simular': cmd_simular,
        'testar': cmd_testar,
    }

    if args.comando in comandos:
        comandos[args.comando](args)
    else:
        print(f"Comando desconhecido: {args.comando}")
        parser.print_help()


if __name__ == "__main__":
    main()
