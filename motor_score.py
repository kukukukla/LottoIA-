
"""
motor_score.py - Motor de Pontuação de Dezenas
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np
from models import Concurso, LoteriaTipo
from motor_estatistico import MotorEstatistico


@dataclass
class ScoreDezena:
    """Score detalhado de uma dezena"""
    dezena: int
    score_total: float
    contribuicoes: Dict[str, float]
    ranking: int


class MotorScore:
    """
    Motor de pontuação de dezenas.
    Cada dezena recebe um score baseado em múltiplas métricas com pesos configuráveis.
    """

    # Pesos padrão
    PESOS_PADRAO = {
        "frequencia_absoluta": 0.15,
        "frequencia_recente": 0.20,
        "atraso_atual": 0.20,
        "atraso_relativo": 0.15,
        "tendencia": 0.10,
        "correlacao": 0.10,
        "ciclos": 0.10,
    }

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None
        self.estatistico = MotorEstatistico(self.concursos)
        self._cache = {}

    def calcular_scores(self, pesos: Dict[str, float] = None) -> Dict[int, ScoreDezena]:
        """
        Calcula score para todas as dezenas.
        pesos: dicionário com pesos para cada métrica.
        """
        pesos = pesos or self.PESOS_PADRAO
        total_peso = sum(pesos.values())

        # Normaliza pesos
        pesos_normalizados = {k: v / total_peso for k, v in pesos.items()}

        # Coleta métricas
        metricas = self.estatistico.metricas_completas_por_dezena()
        freq_abs = self.estatistico.frequencia_absoluta()
        freq_recente = self.estatistico.frequencia_por_janela(25)
        atraso_at = self.estatistico.atraso_atual()
        atraso_med = self.estatistico.atraso_medio()
        matriz_correlacao = (
            self.estatistico.matriz_correlacao()
            if "correlacao" in pesos_normalizados
            else None
        )

        # Normaliza métricas para escala 0-1
        max_freq = max(freq_abs.values()) if freq_abs else 1
        max_freq_rec = max(freq_recente.values()) if freq_recente else 1
        max_atraso = max(atraso_at.values()) if atraso_at else 1
        max_atraso_med = max(atraso_med.values()) if atraso_med else 1

        scores = {}
        for d in range(1, self.loteria.dezenas_totais + 1):
            m = metricas.get(d)
            if not m:
                continue

            contribuicoes = {}

            # Frequência absoluta (normalizada)
            if "frequencia_absoluta" in pesos_normalizados:
                contribuicoes["frequencia_absoluta"] = round(
                    (freq_abs.get(d, 0) / max_freq) * pesos_normalizados["frequencia_absoluta"], 4
                )

            # Frequência recente (normalizada)
            if "frequencia_recente" in pesos_normalizados:
                contribuicoes["frequencia_recente"] = round(
                    (freq_recente.get(d, 0) / max_freq_rec) * pesos_normalizados["frequencia_recente"], 4
                )

            # Atraso atual (inverso: menor atraso = maior score)
            if "atraso_atual" in pesos_normalizados:
                atraso = atraso_at.get(d, 0)
                score_atraso = (1 - (atraso / max_atraso)) if max_atraso > 0 else 1
                contribuicoes["atraso_atual"] = round(
                    score_atraso * pesos_normalizados["atraso_atual"], 4
                )

            # Atraso relativo (atraso atual / média)
            if "atraso_relativo" in pesos_normalizados:
                atual = atraso_at.get(d, 0)
                medio = atraso_med.get(d, 1)
                if medio > 0:
                    razao = atual / medio
                    # Score maior quando atraso está próximo da média ou acima
                    score_rel = min(razao / 2, 1.0) if razao > 0 else 0
                else:
                    score_rel = 0
                contribuicoes["atraso_relativo"] = round(
                    score_rel * pesos_normalizados["atraso_relativo"], 4
                )

            # Tendência
            if "tendencia" in pesos_normalizados:
                tendencia_score = {
                    "subindo": 1.0,
                    "estavel": 0.5,
                    "descendo": 0.0
                }.get(m.tendencia, 0.5)
                contribuicoes["tendencia"] = round(
                    tendencia_score * pesos_normalizados["tendencia"], 4
                )

            # Ciclos (regularidade)
            if "ciclos" in pesos_normalizados:
                ciclo = self.estatistico.analise_ciclos(d)
                desvio = ciclo.get("desvio_ciclo", 999)
                # Menor desvio = ciclos mais regulares = maior score
                score_ciclo = max(0, 1 - (desvio / 10)) if desvio < 999 else 0
                contribuicoes["ciclos"] = round(
                    score_ciclo * pesos_normalizados["ciclos"], 4
                )

            # Correlação (co-ocorrência com dezenas quentes)
            if "correlacao" in pesos_normalizados:
                corr = self._score_correlacao(d, freq_abs, matriz_correlacao)
                contribuicoes["correlacao"] = round(
                    corr * pesos_normalizados["correlacao"], 4
                )

            score_total = round(sum(contribuicoes.values()), 4)

            scores[d] = ScoreDezena(
                dezena=d,
                score_total=score_total,
                contribuicoes=contribuicoes,
                ranking=0  # Preenchido depois
            )

        # Ordena e atribui ranking
        ordenados = sorted(scores.values(), key=lambda s: s.score_total, reverse=True)
        for i, s in enumerate(ordenados):
            scores[s.dezena].ranking = i + 1

        return scores

    def _score_correlacao(
        self,
        dezena: int,
        freq_abs: Dict[int, int],
        matriz=None,
    ) -> float:
        """Score de correlação com dezenas mais frequentes."""
        top_dezenas = sorted(freq_abs.items(), key=lambda x: x[1], reverse=True)[:10]
        top_set = {d for d, _ in top_dezenas}

        if matriz is None:
            matriz = self.estatistico.matriz_correlacao()
        score = 0
        for td in top_set:
            if td != dezena:
                score += abs(matriz[dezena-1][td-1])

        return min(score / len(top_set), 1.0) if top_set else 0

    def explicar_score(self, dezena: int, pesos: Dict[str, float] = None) -> Dict:
        """
        Explica detalhadamente o score de uma dezena.
        Retorna contribuição de cada critério.
        """
        scores = self.calcular_scores(pesos)
        s = scores.get(dezena)
        if not s:
            return {"erro": f"Dezena {dezena} não encontrada"}

        metricas = self.estatistico.metricas_completas_por_dezena()
        m = metricas.get(dezena)

        explicacao = {
            "dezena": dezena,
            "score_total": s.score_total,
            "ranking": s.ranking,
            "metricas_base": {
                "frequencia_absoluta": m.frequencia_absoluta if m else 0,
                "frequencia_relativa": m.frequencia_relativa if m else 0,
                "atraso_atual": m.atraso_atual if m else 0,
                "atraso_medio": m.atraso_medio if m else 0,
                "tendencia": m.tendencia if m else "desconhecida",
            },
            "contribuicoes": s.contribuicoes,
            "interpretacao": self._interpretar_score(s)
        }

        return explicacao

    def _interpretar_score(self, score: ScoreDezena) -> str:
        """Gera interpretação textual do score."""
        if score.score_total >= 0.7:
            return "Dezena com forte sinal estatístico. Múltiplos critérios favoráveis."
        elif score.score_total >= 0.4:
            return "Dezena com sinal moderado. Alguns critérios favoráveis."
        else:
            return "Dezena com sinal fraco. Poucos critérios favoráveis."

    def top_dezenas(self, n: int = 10, pesos: Dict[str, float] = None) -> List[ScoreDezena]:
        """Retorna as N dezenas com maior score."""
        scores = self.calcular_scores(pesos)
        ordenados = sorted(scores.values(), key=lambda s: s.score_total, reverse=True)
        return ordenados[:n]

    def gerar_jogo_por_score(
        self,
        n_dezenas: int,
        pesos: Dict[str, float] = None,
        top_n: int = 25
    ) -> List[int]:
        """
        Gera um jogo selecionando as dezenas com maior score.
        """
        scores = self.calcular_scores(pesos)
        ordenados = sorted(scores.values(), key=lambda s: s.score_total, reverse=True)

        # Seleciona do topo com pequena aleatoriedade para variedade
        candidatas = [s.dezena for s in ordenados[:top_n]]

        # Probabilidade proporcional ao score
        pesos_sel = [scores[d].score_total for d in candidatas]
        pesos_sel = np.array(pesos_sel) / sum(pesos_sel)

        selecionadas = np.random.choice(
            candidatas,
            size=min(n_dezenas, len(candidatas)),
            replace=False,
            p=pesos_sel
        )

        return sorted(selecionadas.tolist())
