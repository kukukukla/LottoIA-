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

import argparse
import json
import random
import numpy as np
from datetime import date, timedelta

from core.models import Concurso, LoteriaTipo, EstrategiaConfig
from core.main_engine import MotorPrincipal
from caixa_client import CAIXA_CLIENT, CaixaAPIError


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


def _carregar_dados_cli(args):
    loteria = LoteriaTipo(args.loteria)
    if args.fonte == "demo":
        concursos = gerar_dados_teste(loteria, max(args.ultimos, 300))
        metadata = {"fonte": "sintético/demo", "aviso": "Não são resultados oficiais."}
        return loteria, concursos, metadata
    try:
        concursos, metadata = CAIXA_CLIENT.obter_historico(
            loteria, args.ultimos, getattr(args, "atualizar", False)
        )
        return loteria, concursos, metadata
    except (CaixaAPIError, ValueError) as exc:
        raise SystemExit(f"Não foi possível carregar dados CAIXA: {exc}") from exc


def _add_data_options(parser, default_fonte="demo", ultimos=30):
    parser.add_argument(
        "--fonte", choices=["caixa", "demo"], default=default_fonte,
        help="Fonte dos concursos; 'demo' usa dados artificiais, 'caixa' consulta resultados oficiais.",
    )
    parser.add_argument(
        "--loteria", choices=[item.value for item in LoteriaTipo], default="lotofacil"
    )
    parser.add_argument("--ultimos", type=int, default=ultimos, help="Quantidade de concursos históricos (1–300).")
    parser.add_argument("--atualizar", action="store_true", help="Ignora cache recente e consulta a CAIXA.")


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
    print(f"   Qui-Quadrado: p={chi['p_value']:.4f} → {chi.get('interpretacao', chi.get('conclusao', ''))}")

    print("\n" + "=" * 70)
    print("  ✅ DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 70)


def cmd_gerar(args):
    """Gera jogos usando a fonte escolhida, demo por padrão ou CAIXA."""
    loteria, concursos, metadata = _carregar_dados_cli(args)
    dezenas = args.dezenas if args.dezenas is not None else loteria.minimo_aposta
    if not loteria.minimo_aposta <= dezenas <= loteria.maximo_aposta:
        raise SystemExit(
            f"Para {loteria.value}, dezenas deve ficar entre "
            f"{loteria.minimo_aposta} e {loteria.maximo_aposta}."
        )
    if not 1 <= args.jogos <= 50:
        raise SystemExit("--jogos deve ficar entre 1 e 50.")
    motor = MotorPrincipal(concursos)
    jogos = motor.gerar_jogos(args.metodo, n_dezenas=dezenas, n_jogos=args.jogos)
    print(f"Fonte: {metadata['fonte']} | Loteria: {loteria.value} | Histórico: {len(concursos)}")
    print(f"\n🎲 Jogos gerados pelo método '{args.metodo}':")
    for i, jogo in enumerate(jogos, 1):
        print(f"   Jogo {i}: {jogo['dezenas']}")


def cmd_simular(args):
    """Executa Monte Carlo sobre histórico CAIXA ou dados artificiais."""
    loteria, concursos, metadata = _carregar_dados_cli(args)
    if args.n < 1 or args.n > 1000000:
        raise SystemExit("--n deve ficar entre 1 e 1.000.000.")
    motor = MotorPrincipal(concursos)
    print(f"\n🎰 Monte Carlo ({args.n} simulações) | {metadata['fonte']} | {loteria.value}")
    rel = motor.simulacoes.monte_carlo_aleatorio(args.n, loteria.dezenas_sorteadas)
    print(f"\n   Total: {rel.total_simulacoes}")
    print(f"   Média: {rel.media_acertos}")
    print(f"   Máx/Mín: {rel.max_acertos}/{rel.min_acertos}")
    print(f"   Desvio: {rel.desvio_padrao}")
    print("\n   Distribuição:")
    for k, v in sorted(rel.acertos_percentual.items()):
        print(f"      {k:2d} acertos: {v:6.2f}%")


def cmd_testar(args):
    """Executa testes estatísticos sobre a fonte escolhida."""
    loteria, concursos, metadata = _carregar_dados_cli(args)
    motor = MotorPrincipal(concursos)
    print(f"\n📐 TESTES ESTATÍSTICOS | {metadata['fonte']} | {loteria.value} | {len(concursos)} concursos")
    print("-" * 60)
    chi = motor.comparativo.teste_chi_quadrado(concursos)
    ks = motor.comparativo.teste_ks(concursos)
    runs = motor.comparativo.teste_runs(concursos, 1)
    print(f"Qui-Quadrado: estatística={chi.get('chi2')}; p={chi.get('p_value')}; {chi.get('conclusao', chi.get('interpretacao', ''))}")
    print(f"Kolmogorov-Smirnov: estatística={ks.get('statistic')}; p={ks.get('p_value')}; {ks.get('interpretacao', '')}")
    print(f"Runs (dezena 1): z={runs.get('z_score')}; {runs.get('interpretacao', '')}")


def cmd_resultados(args):
    """Mostra concursos reais recentes consultados ou cacheados da CAIXA."""
    loteria = LoteriaTipo(args.loteria)
    try:
        concursos, metadata = CAIXA_CLIENT.obter_historico(
            loteria, args.ultimos, args.atualizar
        )
    except (CaixaAPIError, ValueError) as exc:
        raise SystemExit(f"Não foi possível consultar resultados oficiais: {exc}") from exc
    print(f"Fonte: {metadata['fonte']} | atualização: {metadata['atualizado_em']} | cache: {metadata['cache']}")
    if metadata.get("aviso"):
        print(f"Aviso: {metadata['aviso']}")
    for item in concursos[-args.ultimos:]:
        print(f"Concurso {item.numero} | {item.data.isoformat()} | {item.dezenas}")


def cmd_analisar(args):
    """Executa o fluxo integrado de estatística, tempo, padrões e aleatoriedade."""
    loteria, concursos, metadata = _carregar_dados_cli(args)
    motor = MotorPrincipal(concursos)
    resultado = motor.analise_completa()
    print(f"Fonte: {metadata['fonte']} | {loteria.value} | {len(concursos)} concursos | último #{concursos[-1].numero}")
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))


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
    gerar_parser.add_argument('--dezenas', type=int, default=None)
    gerar_parser.add_argument('--jogos', type=int, default=1)
    _add_data_options(gerar_parser)

    # simular
    sim_parser = subparsers.add_parser('simular', help='Simulação Monte Carlo')
    sim_parser.add_argument('--n', type=int, default=1000, help='Número de simulações')
    _add_data_options(sim_parser)

    # testar
    testar_parser = subparsers.add_parser('testar', help='Testes estatísticos')
    _add_data_options(testar_parser)

    # Importação/consulta e análise com resultados oficiais
    resultados_parser = subparsers.add_parser('resultados', help='Consultar últimos resultados CAIXA')
    resultados_parser.add_argument('--loteria', choices=[item.value for item in LoteriaTipo], default='lotofacil')
    resultados_parser.add_argument('--ultimos', type=int, default=5)
    resultados_parser.add_argument('--atualizar', action='store_true')

    analise_parser = subparsers.add_parser('analisar', help='Executar análise completa sobre histórico escolhido')
    _add_data_options(analise_parser)

    args = parser.parse_args()

    if not args.comando:
        parser.print_help()
        return

    comandos = {
        'demo': cmd_demo,
        'gerar': cmd_gerar,
        'simular': cmd_simular,
        'testar': cmd_testar,
        'resultados': cmd_resultados,
        'analisar': cmd_analisar,
    }

    if args.comando in comandos:
        comandos[args.comando](args)
    else:
        print(f"Comando desconhecido: {args.comando}")
        parser.print_help()


if __name__ == "__main__":
    main()
