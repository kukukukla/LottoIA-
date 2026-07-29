
"""
motor_comparativo.py - Motor de Análise Comparativa entre Loterias
"""
from typing import List, Dict, Tuple
from collections import Counter
import numpy as np
from models import Concurso, LoteriaTipo
from motor_estatistico import MotorEstatistico


class MotorComparativo:
    """
    Motor de análise comparativa entre diferentes loterias
    e entre períodos do mesmo histórico.
    """

    def __init__(self):
        self.historicos = {}

    def carregar_historico(self, nome: str, concursos: List[Concurso]):
        """Carrega um histórico para comparação."""
        self.historicos[nome] = sorted(concursos, key=lambda c: c.numero)

    # ═══════════════════════════════════════════════════════════
    # COMPARAÇÃO ENTRE LOTERIAS
    # ═══════════════════════════════════════════════════════════

    def comparar_loterias(self, nome1: str, nome2: str) -> Dict:
        """Compara estatísticas entre duas loterias."""
        h1 = self.historicos.get(nome1, [])
        h2 = self.historicos.get(nome2, [])

        if not h1 or not h2:
            return {"erro": "Histórico não encontrado"}

        est1 = MotorEstatistico(h1)
        est2 = MotorEstatistico(h2)

        soma1 = est1.estatisticas_soma()
        soma2 = est2.estatisticas_soma()

        return {
            "loteria_1": {
                "nome": nome1,
                "total_concursos": len(h1),
                "tipo": h1[0].loteria.value,
                "media_soma": soma1["media"],
                "dp_soma": soma1["desvio_padrao"],
                "media_pares": round(np.mean(est1.distribuicao_pares_impares()["pares"]), 2)
            },
            "loteria_2": {
                "nome": nome2,
                "total_concursos": len(h2),
                "tipo": h2[0].loteria.value,
                "media_soma": soma2["media"],
                "dp_soma": soma2["desvio_padrao"],
                "media_pares": round(np.mean(est2.distribuicao_pares_impares()["pares"]), 2)
            },
            "comparativo": {
                "diferenca_media_soma": round(soma1["media"] - soma2["media"], 2),
                "ratio_media_soma": round(soma1["media"] / max(soma2["media"], 1), 4)
            }
        }

    # ═══════════════════════════════════════════════════════════
    # COMPARAÇÃO ENTRE PERÍODOS
    # ═══════════════════════════════════════════════════════════

    def comparar_periodos(
        self,
        concursos: List[Concurso],
        ponto_corte: int
    ) -> Dict:
        """
        Compara estatísticas antes e depois de um ponto de corte.
        """
        concursos = sorted(concursos, key=lambda c: c.numero)
        antes = concursos[:ponto_corte]
        depois = concursos[ponto_corte:]

        if not antes or not depois:
            return {"erro": "Períodos insuficientes"}

        est_antes = MotorEstatistico(antes)
        est_depois = MotorEstatistico(depois)

        freq_antes = est_antes.frequencia_absoluta()
        freq_depois = est_depois.frequencia_absoluta()

        # Dezenas que mudaram de comportamento
        mudancas = []
        for d in range(1, concursos[0].loteria.dezenas_totais + 1):
            f1 = freq_antes.get(d, 0) / max(len(antes), 1)
            f2 = freq_depois.get(d, 0) / max(len(depois), 1)
            if f1 > 0 and abs(f2 - f1) / f1 > 0.3:
                mudancas.append({
                    "dezena": d,
                    "freq_antes": round(f1, 4),
                    "freq_depois": round(f2, 4),
                    "mudanca_percentual": round((f2 - f1) / f1 * 100, 2)
                })

        return {
            "periodo_1": {"concursos": len(antes), "inicio": antes[0].numero, "fim": antes[-1].numero},
            "periodo_2": {"concursos": len(depois), "inicio": depois[0].numero, "fim": depois[-1].numero},
            "mudancas_significativas": sorted(mudancas, key=lambda x: abs(x["mudanca_percentual"]), reverse=True)[:10],
            "estatisticas_antes": est_antes.estatisticas_soma(),
            "estatisticas_depois": est_depois.estatisticas_soma()
        }

    # ═══════════════════════════════════════════════════════════
    # TESTE DE ALEATORIEDADE
    # ═══════════════════════════════════════════════════════════

    def teste_chi_quadrado(self, concursos: List[Concurso]) -> Dict:
        """
        Teste qui-quadrado para verificar uniformidade das dezenas.
        """
        from scipy.stats import chisquare

        est = MotorEstatistico(concursos)
        freq = est.frequencia_absoluta()

        n_dezenas = concursos[0].loteria.dezenas_totais
        n_sorteios = len(concursos)
        n_por_sorteio = concursos[0].loteria.dezenas_sorteadas

        # Frequência esperada uniforme
        esperado = (n_sorteios * n_por_sorteio) / n_dezenas
        observado = [freq.get(d, 0) for d in range(1, n_dezenas + 1)]

        chi2, p_value = chisquare(observado, [esperado] * n_dezenas)

        return {
            "chi2": round(chi2, 4),
            "p_value": round(p_value, 6),
            "graus_liberdade": n_dezenas - 1,
            "frequencia_esperada": round(esperado, 2),
            "frequencia_media_observada": round(np.mean(observado), 2),
            "frequencia_dp_observada": round(np.std(observado), 2),
            "interpretacao": "uniforme" if p_value > 0.05 else "nao_uniforme",
            "conclusao": "As dezenas seguem distribuição uniforme (não há viés detectável)"
                        if p_value > 0.05 else "Possível desvio da uniformidade detectado"
        }

    def teste_runs(self, concursos: List[Concurso], dezena: int) -> Dict:
        """
        Teste de runs (sequências) para verificar aleatoriedade.
        """
        serie = [1 if dezena in c.dezenas else 0 for c in concursos]
        n = len(serie)
        n1 = sum(serie)
        n0 = n - n1

        # Conta runs
        runs = 1
        for i in range(1, n):
            if serie[i] != serie[i-1]:
                runs += 1

        # Valor esperado e variância
        if n1 == 0 or n0 == 0:
            return {"erro": "Série constante"}

        esperado = (2 * n1 * n0) / n + 1
        variancia = (2 * n1 * n0 * (2 * n1 * n0 - n)) / (n**2 * (n - 1))

        z = (runs - esperado) / np.sqrt(variancia) if variancia > 0 else 0

        return {
            "dezena": dezena,
            "runs_observados": runs,
            "runs_esperados": round(esperado, 2),
            "z_score": round(z, 4),
            "aleatorio": "sim" if abs(z) < 1.96 else "nao",
            "interpretacao": "Sequência aleatória" if abs(z) < 1.96 else "Possível padrão não aleatório"
        }

    def teste_ks(self, concursos: List[Concurso]) -> Dict:
        """
        Teste Kolmogorov-Smirnov para uniformidade.
        """
        from scipy.stats import kstest, uniform

        # Coleta todas as dezenas sorteadas
        todas = []
        for c in concursos:
            todas.extend(c.dezenas)

        n_dezenas = concursos[0].loteria.dezenas_totais
        # Normaliza para [0, 1]
        normalizadas = [(d - 1) / n_dezenas for d in todas]

        statistic, p_value = kstest(normalizadas, uniform.cdf)

        return {
            "statistic": round(statistic, 6),
            "p_value": round(p_value, 6),
            "uniforme": p_value > 0.05,
            "interpretacao": "Distribuição uniforme confirmada" if p_value > 0.05 else "Desvio de uniformidade"
        }

    # ═══════════════════════════════════════════════════════════
    # ANÁLISE DE CONVERGÊNCIA
    # ═══════════════════════════════════════════════════════════

    def convergencia_frequencia(self, concursos: List[Concurso], dezena: int) -> List[Dict]:
        """
        Analisa como a frequência relativa converge para a esperada.
        """
        esperada = concursos[0].loteria.dezenas_sorteadas / concursos[0].loteria.dezenas_totais
        convergencia = []
        acumulado = 0

        for i, c in enumerate(concursos):
            if dezena in c.dezenas:
                acumulado += 1
            freq_rel = acumulado / (i + 1)
            convergencia.append({
                "concurso": c.numero,
                "frequencia_relativa": round(freq_rel, 6),
                "diferenca_esperada": round(freq_rel - esperada, 6),
                "acumulado": acumulado
            })

        return convergencia
