"""
demo.py - Demonstração completa do Motor Estatístico de Loterias v2.0
"""
import sys
sys.path.insert(0, 'core')

from datetime import date, timedelta
import random
import numpy as np

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


def main():
    print("=" * 70)
    print("  MOTOR ESTATÍSTICO DE LOTERIAS v2.0 - DEMONSTRAÇÃO")
    print("=" * 70)

    random.seed(42)
    np.random.seed(42)

    # ── Dados de teste ──
    print("\n📊 Gerando dados de teste (Lotofácil, 300 concursos)...")
    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    print(f"   ✓ {len(concursos)} concursos gerados")

    # ── Motor Estatístico ──
    print("\n📈 MOTOR ESTATÍSTICO")
    print("-" * 50)
    motor = MotorPrincipal(concursos)

    freq = motor.estatistico.frequencia_absoluta()
    top5 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"   Frequência Absoluta - Top 5:")
    for d, f in top5:
        print(f"      Dezena {d:2d}: {f} ocorrências")

    atraso = motor.estatistico.atraso_atual()
    mais_atrasadas = sorted(atraso.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"\n   Atraso Atual - 5 dezenas mais atrasadas:")
    for d, a in mais_atrasadas:
        print(f"      Dezena {d:2d}: {a} concursos de atraso")

    rep = motor.estatistico.repeticoes_entre_concursos()
    print(f"\n   Repetições entre concursos consecutivos:")
    for k, v in sorted(rep.items()):
        print(f"      {k} dezenas repetidas: {v} vezes")

    seq = motor.estatistico.analise_sequencias_consecutivas()
    print(f"\n   Sequências consecutivas:")
    print(f"      Média/concurso: {seq['media_sequencias_por_concurso']}")
    print(f"      Tamanho máximo: {seq['tamanho_maximo_sequencia']}")

    est_soma = motor.estatistico.estatisticas_soma()
    print(f"\n   Estatísticas da Soma:")
    print(f"      Média: {est_soma['media']} | Mediana: {est_soma['mediana']} | DP: {est_soma['desvio_padrao']}")
    print(f"      P25/P75: {est_soma['percentil_25']} / {est_soma['percentil_75']}")

    # ── Motor Matemático ──
    print("\n🔢 MOTOR MATEMÁTICO")
    print("-" * 50)
    print(f"   Combinações C(25,15): {motor.matematico.combinacoes_totais():,}")
    print(f"   Prob. 15/15: {motor.matematico.probabilidade_acerto(15, 15):.2e}")
    print(f"   Prob. 14/15: {motor.matematico.probabilidade_acerto(15, 14):.6f}")
    print(f"   Fibonacci: {motor.matematico.sequencia_fibonacci()}")

    # ── Motor de Score ──
    print("\n⭐ MOTOR DE SCORE")
    print("-" * 50)
    top10 = motor.score.top_dezenas(10)
    print("   Top 10 dezenas por score:")
    for s in top10:
        print(f"      #{s.ranking:2d} Dezena {s.dezena:2d}: Score={s.score_total:.4f}")

    # ── Motor de Estratégias ──
    print("\n🎯 MOTOR DE ESTRATÉGIAS")
    print("-" * 50)
    config = EstrategiaConfig(
        nome="Estratégia Frequência + Atraso",
        loteria=LoteriaTipo.LOTOFACIL,
        quantidade_dezenas=15,
        filtros={
            "frequencia_historica": {"max_rank": 20},
            "dezenas_atrasadas": {"min_atraso": 1, "max_atraso": 8},
            "equilibrio_par_impar": {"min_pares": 6, "max_pares": 9},
            "soma_dezenas": {"min_soma": 150, "max_soma": 230},
        },
        pesos={"frequencia_absoluta": 0.3, "atraso_atual": 0.3, "frequencia_recente": 0.2, "tendencia": 0.2}
    )
    id_estr = motor.criar_estrategia(config)
    print(f"   Estratégia criada: '{config.nome}' (ID: {id_estr})")

    jogos_estr = motor.gerar_por_estrategia(id_estr, 3)
    print(f"\n   Jogos gerados:")
    for i, j in enumerate(jogos_estr, 1):
        status = "✓ Válido" if j['valido'] else f"✗ {j['motivo']}"
        print(f"      Jogo {i}: {j['dezenas']} | {status}")

    # ── Gerador de Jogos ──
    print("\n🎲 GERADOR DE JOGOS")
    print("-" * 50)
    for nome, metodo, params in [("Aleatório", "aleatorio", {}), ("Score", "score", {"top_n": 20})]:
        jogo = motor.gerar_jogos(metodo, 15, 1, params)[0]
        print(f"   {nome}: {jogo['dezenas']}")

    # ── Simulações ──
    print("\n🎰 MOTOR DE SIMULAÇÕES")
    print("-" * 50)
    rel_mc = motor.simulacoes.monte_carlo_aleatorio(1000, 15, seed=42)
    print(f"   Simulações: {rel_mc.total_simulacoes}")
    print(f"   Média: {rel_mc.media_acertos} | Máx: {rel_mc.max_acertos} | DP: {rel_mc.desvio_padrao}")
    print(f"   Distribuição:")
    for k, v in sorted(rel_mc.acertos_percentual.items()):
        print(f"      {k:2d} acertos: {v:6.2f}%")

    # ── Testes Estatísticos ──
    print("\n📐 TESTES DE ALEATORIEDADE")
    print("-" * 50)
    chi = motor.comparativo.teste_chi_quadrado(concursos)
    print(f"   Qui-Quadrado: p={chi['p_value']:.4f} → {chi['interpretacao']}")
    ks = motor.comparativo.teste_ks(concursos)
    print(f"   KS: p={ks['p_value']:.4f} → {ks['interpretacao']}")

    # ── Final ──
    print("\n" + "=" * 70)
    print("  ✅ DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 70)
    print("\n⚠️  AVISO: Sistema para análise estatística. Não prevê resultados.")


if __name__ == "__main__":
    main()
