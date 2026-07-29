
"""
motor_temporal.py - Motor de Análise Temporal e Séries Temporais
"""
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass
import numpy as np
from scipy import stats
from models import Concurso, LoteriaTipo


@dataclass
class PredicaoTemporal:
    """Resultado de uma predição temporal para uma dezena"""
    dezena: int
    probabilidade_saida: float
    intervalo_esperado: float
    confianca: float
    tendencia: str
    ciclo_detectado: Optional[int]


class MotorTemporal:
    """
    Motor de análise temporal avançada.
    Detecta padrões temporais, sazonalidades e ciclos.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None

    # ═══════════════════════════════════════════════════════════
    # ANÁLISE DE INTERVALOS
    # ═══════════════════════════════════════════════════════════

    def intervalos_ocorrencia(self, dezena: int) -> List[int]:
        """Lista de intervalos (em concursos) entre ocorrências de uma dezena."""
        posicoes = [i for i, c in enumerate(self.concursos) if dezena in c.dezenas]
        if len(posicoes) < 2:
            return []
        return [posicoes[i] - posicoes[i-1] for i in range(1, len(posicoes))]

    def estatisticas_intervalo(self, dezena: int) -> Dict:
        """Estatísticas descritivas dos intervalos de uma dezena."""
        intervalos = self.intervalos_ocorrencia(dezena)
        if not intervalos:
            return {"dezena": dezena, "media": 0, "mediana": 0, "moda": 0, "dp": 0}

        return {
            "dezena": dezena,
            "media": round(np.mean(intervalos), 2),
            "mediana": round(np.median(intervalos), 2),
            "moda": stats.mode(intervalos, keepdims=True)[0][0],
            "dp": round(np.std(intervalos), 2),
            "min": min(intervalos),
            "max": max(intervalos),
            "q1": round(np.percentile(intervalos, 25), 2),
            "q3": round(np.percentile(intervalos, 75), 2),
            "intervalos": intervalos
        }

    # ═══════════════════════════════════════════════════════════
    # DETECÇÃO DE CICLOS
    # ═══════════════════════════════════════════════════════════

    def detectar_ciclos(self, dezena: int, min_ciclo: int = 2, max_ciclo: int = 50) -> Dict:
        """
        Detecta ciclos dominantes usando autocorrelação.
        """
        # Série binária: 1 se a dezena saiu, 0 se não
        serie = [1 if dezena in c.dezenas else 0 for c in self.concursos]
        n = len(serie)

        if n < max_ciclo * 2:
            return {"dezena": dezena, "ciclos": [], "ciclo_principal": None}

        # Autocorrelação
        autocorr = []
        for lag in range(min_ciclo, min(max_ciclo, n // 2)):
            corr = np.corrcoef(serie[:-lag], serie[lag:])[0, 1]
            if not np.isnan(corr):
                autocorr.append((lag, corr))

        # Ordena por correlação
        autocorr.sort(key=lambda x: abs(x[1]), reverse=True)
        top_ciclos = autocorr[:5]

        ciclo_principal = top_ciclos[0][0] if top_ciclos else None

        return {
            "dezena": dezena,
            "ciclos": [{"periodo": p, "correlacao": round(c, 4)} for p, c in top_ciclos],
            "ciclo_principal": ciclo_principal,
            "forca_ciclo": round(top_ciclos[0][1], 4) if top_ciclos else 0
        }

    # ═══════════════════════════════════════════════════════════
    # SAZONALIDADE
    # ═══════════════════════════════════════════════════════════

    def sazonalidade_mensal(self) -> Dict[int, Dict]:
        """Frequência de cada dezena por mês do ano."""
        mensal = defaultdict(lambda: defaultdict(int))
        for c in self.concursos:
            mes = c.data.month
            for d in c.dezenas:
                mensal[d][mes] += 1

        resultado = {}
        for d in range(1, self.loteria.dezenas_totais + 1):
            freq_por_mes = dict(mensal[d])
            total = sum(freq_por_mes.values())
            if total > 0:
                media = total / 12
                desvio = np.std(list(freq_por_mes.values())) if freq_por_mes else 0
                resultado[d] = {
                    "frequencias": freq_por_mes,
                    "media_mensal": round(media, 2),
                    "desvio": round(desvio, 2),
                    "mes_mais_frequente": max(freq_por_mes.items(), key=lambda x: x[1])[0] if freq_por_mes else None
                }
        return resultado

    def sazonalidade_dia_semana(self) -> Dict[int, Dict]:
        """Frequência de cada dezena por dia da semana."""
        semanal = defaultdict(lambda: defaultdict(int))
        for c in self.concursos:
            dia = c.data.weekday()
            for d in c.dezenas:
                semanal[d][dia] += 1

        resultado = {}
        for d in range(1, self.loteria.dezenas_totais + 1):
            freq = dict(semanal[d])
            total = sum(freq.values())
            if total > 0:
                resultado[d] = {
                    "frequencias": freq,
                    "dia_mais_frequente": max(freq.items(), key=lambda x: x[1])[0] if freq else None
                }
        return resultado

    # ═══════════════════════════════════════════════════════════
    # MOMENTUM E TENDÊNCIA
    # ═══════════════════════════════════════════════════════════

    def momentum(self, dezena: int, janelas: List[int] = None) -> Dict:
        """
        Calcula momentum (força da tendência) em múltiplas janelas.
        """
        if janelas is None:
            janelas = [5, 10, 20, 50]

        momentums = {}
        for j in janelas:
            if j > len(self.concursos):
                continue
            recente = sum(1 for c in self.concursos[-j:] if dezena in c.dezenas)
            anterior = sum(1 for c in self.concursos[-2*j:-j] if dezena in c.dezenas)

            if anterior > 0:
                ratio = recente / anterior
            else:
                ratio = recente * 2  # Penaliza ausência anterior

            momentums[j] = {
                "frequencia_recente": recente,
                "frequencia_anterior": anterior,
                "ratio": round(ratio, 4),
                "momentum": "positivo" if ratio > 1.2 else "negativo" if ratio < 0.8 else "neutro"
            }

        return {"dezena": dezena, "momentums": momentums}

    def tendencia_linear(self, dezena: int, janela: int = 50) -> Dict:
        """
        Regressão linear da frequência acumulada para detectar tendência.
        """
        serie = [1 if dezena in c.dezenas else 0 for c in self.concursos[-janela:]]
        x = np.arange(len(serie))
        y = np.cumsum(serie)

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        return {
            "dezena": dezena,
            "inclinacao": round(slope, 6),
            "r_quadrado": round(r_value**2, 4),
            "p_value": round(p_value, 6),
            "tendencia": "crescente" if slope > 0.001 else "decrescente" if slope < -0.001 else "estavel",
            "significancia": "significativa" if p_value < 0.05 else "nao_significativa"
        }

    # ═══════════════════════════════════════════════════════════
    # PREDIÇÃO COMBINADA
    # ═══════════════════════════════════════════════════════════

    def predicao_combinada(self, dezena: int) -> PredicaoTemporal:
        """
        Combina múltiplas análises temporais em uma predição.
        """
        # Ciclo
        ciclo_info = self.detectar_ciclos(dezena)
        ciclo = ciclo_info.get("ciclo_principal")
        forca_ciclo = ciclo_info.get("forca_ciclo", 0)

        # Intervalo
        stats_int = self.estatisticas_intervalo(dezena)
        media_intervalo = stats_int.get("media", 10)

        # Última ocorrência
        ultima_pos = None
        for i, c in enumerate(reversed(self.concursos)):
            if dezena in c.dezenas:
                ultima_pos = len(self.concursos) - 1 - i
                break

        atraso_atual = len(self.concursos) - 1 - ultima_pos if ultima_pos is not None else len(self.concursos)

        # Probabilidade baseada no atraso vs média
        if media_intervalo > 0:
            prob_base = min(atraso_atual / media_intervalo, 2.0) / 2.0
        else:
            prob_base = 0.5

        # Ajusta pelo ciclo
        if ciclo and forca_ciclo > 0.3:
            proximo_ciclo = ultima_pos + ciclo if ultima_pos else 0
            distancia_ciclo = abs(len(self.concursos) - proximo_ciclo)
            if distancia_ciclo <= 3:
                prob_base *= 1.3

        # Ajusta pelo momentum
        mom = self.momentum(dezena, [10])
        if mom["momentums"]:
            m10 = list(mom["momentums"].values())[0]
            if m10["momentum"] == "positivo":
                prob_base *= 1.2
            elif m10["momentum"] == "negativo":
                prob_base *= 0.8

        prob = min(max(prob_base, 0.0), 1.0)

        # Confiança
        confianca = 0.3 + (forca_ciclo * 0.3) + (0.2 if stats_int.get("dp", 10) < 5 else 0)
        confianca = min(confianca, 0.95)

        return PredicaoTemporal(
            dezena=dezena,
            probabilidade_saida=round(prob, 4),
            intervalo_esperado=round(media_intervalo, 2),
            confianca=round(confianca, 4),
            tendencia=m10["momentum"] if mom["momentums"] else "neutro",
            ciclo_detectado=ciclo
        )

    def ranking_predicoes(self) -> List[PredicaoTemporal]:
        """Ranking de todas as dezenas por probabilidade de saída."""
        predicoes = []
        for d in range(1, self.loteria.dezenas_totais + 1):
            p = self.predicao_combinada(d)
            predicoes.append(p)
        return sorted(predicoes, key=lambda x: x.probabilidade_saida, reverse=True)
