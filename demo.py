#!/usr/bin/env python3
"""
demo.py - Demonstração completa do Motor Estatístico de Loterias v2.0
"""
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

    print("\n📊 Gerando dados de teste (Lotofácil, 300 concursos)...")
    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    print(f"   ✓ {len(concursos)} concursos gerados")

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

    print("\n  ✅ DEMONSTRAÇÃO CONCLUÍDA")
    print("\n⚠️  AVISO: Sistema para análise estatística. Não prevê resultados.")


if __name__ == "__main__":
    main()
