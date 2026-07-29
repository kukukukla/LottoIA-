
"""
motor_estatistico.py - Motor de Análise Estatística
"""
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass
import numpy as np
from scipy import stats
from models import Concurso, LoteriaTipo


@dataclass
class MetricaDezena:
    """Métricas individuais de uma dezena"""
    dezena: int
    frequencia_absoluta: int
    frequencia_relativa: float
    atraso_atual: int
    atraso_medio: float
    atraso_maximo: int
    ultima_ocorrencia: int  # número do concurso
    tendencia: str  # "subindo", "estavel", "descendo"


class MotorEstatistico:
    """
    Motor de análise estatística para loterias.
    Implementa análises de frequência, atraso, distribuição e correlação.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None
        self._cache = {}

    # ═══════════════════════════════════════════════════════════
    # ANÁLISES DE FREQUÊNCIA
    # ═══════════════════════════════════════════════════════════

    def frequencia_absoluta(self) -> Dict[int, int]:
        """Conta ocorrências totais de cada dezena no histórico completo."""
        todas = []
        for c in self.concursos:
            todas.extend(c.dezenas)
        return dict(Counter(todas))

    def frequencia_relativa(self) -> Dict[int, float]:
        """Frequência absoluta normalizada pelo total de sorteios."""
        freq_abs = self.frequencia_absoluta()
        total_sorteios = len(self.concursos)
        return {
            d: round(count / total_sorteios, 4)
            for d, count in freq_abs.items()
        }

    def frequencia_por_janela(self, janela: int) -> Dict[int, int]:
        """
        Frequência dos últimos N concursos.
        Janelas suportadas: 10, 25, 50, 100, 300
        """
        if janela > len(self.concursos):
            janela = len(self.concursos)

        ultimos = self.concursos[-janela:]
        todas = []
        for c in ultimos:
            todas.extend(c.dezenas)
        return dict(Counter(todas))

    def frequencia_por_janelas_multiplas(self, janelas: List[int] = None) -> Dict[int, Dict[int, int]]:
        """Frequência para múltiplas janelas simultaneamente."""
        if janelas is None:
            janelas = [10, 25, 50, 100, 300]
        return {j: self.frequencia_por_janela(j) for j in janelas}

    # ═══════════════════════════════════════════════════════════
    # ANÁLISES DE ATRASO
    # ═══════════════════════════════════════════════════════════

    def atraso_atual(self) -> Dict[int, int]:
        """
        Quantos concursos desde a última ocorrência de cada dezena.
        Atraso 0 = saiu no concurso mais recente.
        """
        if not self.concursos:
            return {}

        ultimo = self.concursos[-1].numero
        atrasos = {}

        for dezena in range(1, self.loteria.dezenas_totais + 1):
            encontrado = False
            for i, c in enumerate(reversed(self.concursos)):
                if dezena in c.dezenas:
                    atrasos[dezena] = i
                    encontrado = True
                    break
            if not encontrado:
                atrasos[dezena] = len(self.concursos)

        return atrasos

    def atraso_medio(self) -> Dict[int, float]:
        """Média de atraso entre ocorrências de cada dezena."""
        atrasos = defaultdict(list)

        for dezena in range(1, self.loteria.dezenas_totais + 1):
            ultima_pos = -1
            for i, c in enumerate(self.concursos):
                if dezena in c.dezenas:
                    if ultima_pos >= 0:
                        atrasos[dezena].append(i - ultima_pos - 1)
                    ultima_pos = i

        return {
            d: round(np.mean(atrasos[d]), 2) if atrasos[d] else 0.0
            for d in range(1, self.loteria.dezenas_totais + 1)
        }

    def atraso_maximo(self) -> Dict[int, int]:
        """Maior atraso já registrado para cada dezena."""
        atrasos = defaultdict(list)

        for dezena in range(1, self.loteria.dezenas_totais + 1):
            ultima_pos = -1
            for i, c in enumerate(self.concursos):
                if dezena in c.dezenas:
                    if ultima_pos >= 0:
                        atrasos[dezena].append(i - ultima_pos - 1)
                    ultima_pos = i

        return {
            d: max(atrasos[d]) if atrasos[d] else 0
            for d in range(1, self.loteria.dezenas_totais + 1)
        }

    def historico_atrasos(self, dezena: int) -> List[int]:
        """Lista completa de atrasos de uma dezena específica."""
        historico = []
        ultima_pos = -1
        for i, c in enumerate(self.concursos):
            if dezena in c.dezenas:
                if ultima_pos >= 0:
                    historico.append(i - ultima_pos - 1)
                ultima_pos = i
        return historico

    # ═══════════════════════════════════════════════════════════
    # ANÁLISES DE REPETIÇÃO
    # ═══════════════════════════════════════════════════════════

    def repeticoes_entre_concursos(self) -> Dict[int, int]:
        """
        Quantas dezenas se repetem entre concursos consecutivos.
        Retorna distribuição: {qtd_repeticoes: frequencia}
        """
        repeticoes = Counter()
        for i in range(1, len(self.concursos)):
            atual = set(self.concursos[i].dezenas)
            anterior = set(self.concursos[i-1].dezenas)
            comuns = len(atual & anterior)
            repeticoes[comuns] += 1
        return dict(repeticoes)

    def dezenas_mais_repetidas(self, top_n: int = 10) -> List[Tuple[int, int]]:
        """Dezenas que mais se repetem entre concursos consecutivos."""
        repeticoes = Counter()
        for i in range(1, len(self.concursos)):
            anterior = set(self.concursos[i-1].dezenas)
            for d in self.concursos[i].dezenas:
                if d in anterior:
                    repeticoes[d] += 1
        return repeticoes.most_common(top_n)

    # ═══════════════════════════════════════════════════════════
    # DISTRIBUIÇÃO ESPACIAL
    # ═══════════════════════════════════════════════════════════

    def distribuicao_faixas(self, n_faixas: int = 5) -> Dict[str, Dict]:
        """
        Distribuição das dezenas em faixas numéricas.
        Ex: 5 faixas para Lotofácil (1-5, 6-10, 11-15, 16-20, 21-25)
        """
        total = self.loteria.dezenas_totais
        tamanho_faixa = total // n_faixas
        faixas = {}

        for i in range(n_faixas):
            inicio = i * tamanho_faixa + 1
            fim = (i + 1) * tamanho_faixa
            nome = f"{inicio}-{fim}"
            faixas[nome] = {"inicio": inicio, "fim": fim, "frequencias": Counter()}

        for c in self.concursos:
            for d in c.dezenas:
                for nome, faixa in faixas.items():
                    if faixa["inicio"] <= d <= faixa["fim"]:
                        faixas[nome]["frequencias"][d] += 1
                        break

        # Normaliza
        resultado = {}
        for nome, faixa in faixas.items():
            resultado[nome] = dict(faixa["frequencias"])
        return resultado

    def distribuicao_pares_impares(self) -> Dict[str, List[int]]:
        """Distribuição da quantidade de pares/ímpares por concurso."""
        distrib = {"pares": [], "impares": []}
        for c in self.concursos:
            distrib["pares"].append(len(c.pares))
            distrib["impares"].append(len(c.impares))
        return distrib

    def distribuicao_baixos_altos(self) -> Dict[str, List[int]]:
        """Distribuição da quantidade de baixos/altos por concurso."""
        distrib = {"baixos": [], "altos": []}
        for c in self.concursos:
            distrib["baixos"].append(len(c.baixos))
            distrib["altos"].append(len(c.altos))
        return distrib

    def distribuicao_linhas(self) -> Dict[int, List[int]]:
        """Quantidade de dezenas por linha em cada concurso."""
        distrib = {i: [] for i in range(1, 6)}
        for c in self.concursos:
            linhas = c.linhas
            for i in range(1, 6):
                distrib[i].append(len(linhas.get(i, [])))
        return distrib

    def distribuicao_colunas(self) -> Dict[int, List[int]]:
        """Quantidade de dezenas por coluna em cada concurso."""
        distrib = {i: [] for i in range(1, 6)}
        for c in self.concursos:
            cols = c.colunas
            for i in range(1, 6):
                distrib[i].append(len(cols.get(i, [])))
        return distrib

    # ═══════════════════════════════════════════════════════════
    # ESTATÍSTICAS DESCRITIVAS
    # ═══════════════════════════════════════════════════════════

    def estatisticas_soma(self) -> Dict:
        """Estatísticas descritivas da soma das dezenas por concurso."""
        somas = [c.soma for c in self.concursos]
        return {
            "media": round(np.mean(somas), 2),
            "mediana": round(np.median(somas), 2),
            "moda": stats.mode(somas, keepdims=True)[0][0] if len(somas) > 0 else 0,
            "desvio_padrao": round(np.std(somas), 2),
            "variancia": round(np.var(somas), 2),
            "minimo": min(somas) if somas else 0,
            "maximo": max(somas) if somas else 0,
            "percentil_25": round(np.percentile(somas, 25), 2) if somas else 0,
            "percentil_50": round(np.percentile(somas, 50), 2) if somas else 0,
            "percentil_75": round(np.percentile(somas, 75), 2) if somas else 0,
            "percentil_90": round(np.percentile(somas, 90), 2) if somas else 0,
            "percentil_95": round(np.percentile(somas, 95), 2) if somas else 0,
        }

    def estatisticas_media(self) -> Dict:
        """Estatísticas descritivas da média das dezenas por concurso."""
        medias = [c.media for c in self.concursos]
        return {
            "media": round(np.mean(medias), 2),
            "mediana": round(np.median(medias), 2),
            "desvio_padrao": round(np.std(medias), 2),
            "minimo": round(min(medias), 2) if medias else 0,
            "maximo": round(max(medias), 2) if medias else 0,
        }

    # ═══════════════════════════════════════════════════════════
    # SEQUÊNCIAS E CICLOS
    # ═══════════════════════════════════════════════════════════

    def analise_sequencias_consecutivas(self) -> Dict:
        """Análise estatística de sequências consecutivas."""
        todas_sequencias = []
        qtd_sequencias = []
        tamanhos = []

        for c in self.concursos:
            seqs = c.sequencias_consecutivas
            qtd_sequencias.append(len(seqs))
            for seq in seqs:
                tamanhos.append(len(seq))
            todas_sequencias.extend(seqs)

        return {
            "total_sequencias": len(todas_sequencias),
            "media_sequencias_por_concurso": round(np.mean(qtd_sequencias), 2) if qtd_sequencias else 0,
            "max_sequencias_por_concurso": max(qtd_sequencias) if qtd_sequencias else 0,
            "tamanho_medio_sequencia": round(np.mean(tamanhos), 2) if tamanhos else 0,
            "tamanho_maximo_sequencia": max(tamanhos) if tamanhos else 0,
            "distribuicao_tamanhos": dict(Counter(tamanhos)),
            "frequencia_por_concurso": dict(Counter(qtd_sequencias))
        }

    def analise_ciclos(self, dezena: int, ciclo_max: int = 50) -> Dict:
        """
        Análise de ciclos de ocorrência de uma dezena.
        Identifica padrões periódicos na frequência de saída.
        """
        ocorrencias = [i for i, c in enumerate(self.concursos) if dezena in c.dezenas]
        if len(ocorrencias) < 2:
            return {"dezena": dezena, "ciclos": [], "media_ciclo": 0}

        ciclos = [ocorrencias[i] - ocorrencias[i-1] for i in range(1, len(ocorrencias))]

        return {
            "dezena": dezena,
            "ciclos": ciclos,
            "media_ciclo": round(np.mean(ciclos), 2),
            "desvio_ciclo": round(np.std(ciclos), 2),
            "min_ciclo": min(ciclos),
            "max_ciclo": max(ciclos),
            "frequencia_ciclos": dict(Counter(ciclos))
        }

    # ═══════════════════════════════════════════════════════════
    # CORRELAÇÃO E HEATMAP
    # ═══════════════════════════════════════════════════════════

    def matriz_correlacao(self) -> np.ndarray:
        """
        Matriz de correlação entre dezenas.
        Correlação de Pearson baseada em co-ocorrência.
        """
        n_dezenas = self.loteria.dezenas_totais
        matriz = np.zeros((n_dezenas, n_dezenas))

        # Matriz de co-ocorrência
        coocorrencia = np.zeros((n_dezenas, n_dezenas))
        for c in self.concursos:
            for i, d1 in enumerate(c.dezenas):
                for d2 in c.dezenas[i+1:]:
                    coocorrencia[d1-1][d2-1] += 1
                    coocorrencia[d2-1][d1-1] += 1

        # Normaliza para correlação
        for i in range(n_dezenas):
            for j in range(n_dezenas):
                if i == j:
                    matriz[i][j] = 1.0
                else:
                    freq_i = sum(1 for c in self.concursos if (i+1) in c.dezenas)
                    freq_j = sum(1 for c in self.concursos if (j+1) in c.dezenas)
                    if freq_i > 0 and freq_j > 0:
                        esperado = (freq_i * freq_j) / len(self.concursos)
                        if esperado > 0:
                            matriz[i][j] = round((coocorrencia[i][j] - esperado) / esperado, 4)

        return matriz

    def heatmap_data(self) -> Dict:
        """Dados para heatmap de frequência por posição no tempo."""
        n_dezenas = self.loteria.dezenas_totais
        # Agrupa concursos em blocos de 10
        bloco = 10
        n_blocos = len(self.concursos) // bloco

        heatmap = []
        for b in range(n_blocos):
            inicio = b * bloco
            fim = min((b + 1) * bloco, len(self.concursos))
            freq = Counter()
            for c in self.concursos[inicio:fim]:
                freq.update(c.dezenas)
            linha = [freq.get(d, 0) for d in range(1, n_dezenas + 1)]
            heatmap.append(linha)

        return {
            "data": heatmap,
            "blocos": [f"C{self.concursos[b*bloco].numero}-{self.concursos[min((b+1)*bloco-1, len(self.concursos)-1)].numero}" 
                      for b in range(n_blocos)],
            "dezenas": list(range(1, n_dezenas + 1))
        }

    # ═══════════════════════════════════════════════════════════
    # MÉTRICAS AGREGADAS POR DEZENA
    # ═══════════════════════════════════════════════════════════

    def metricas_completas_por_dezena(self) -> Dict[int, MetricaDezena]:
        """Retorna todas as métricas consolidadas para cada dezena."""
        freq_abs = self.frequencia_absoluta()
        freq_rel = self.frequencia_relativa()
        atraso_at = self.atraso_atual()
        atraso_med = self.atraso_medio()
        atraso_max = self.atraso_maximo()

        # Frequência por janelas para tendência
        freq_10 = self.frequencia_por_janela(10)
        freq_50 = self.frequencia_por_janela(50)

        metricas = {}
        for d in range(1, self.loteria.dezenas_totais + 1):
            f10 = freq_10.get(d, 0)
            f50 = freq_50.get(d, 0)
            if f10 > f50 / 5:
                tendencia = "subindo"
            elif f10 < f50 / 5:
                tendencia = "descendo"
            else:
                tendencia = "estavel"

            # Última ocorrência
            ultima = None
            for c in reversed(self.concursos):
                if d in c.dezenas:
                    ultima = c.numero
                    break

            metricas[d] = MetricaDezena(
                dezena=d,
                frequencia_absoluta=freq_abs.get(d, 0),
                frequencia_relativa=freq_rel.get(d, 0.0),
                atraso_atual=atraso_at.get(d, 0),
                atraso_medio=atraso_med.get(d, 0.0),
                atraso_maximo=atraso_max.get(d, 0),
                ultima_ocorrencia=ultima or 0,
                tendencia=tendencia
            )

        return metricas

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIO COMPLETO
    # ═══════════════════════════════════════════════════════════

    def relatorio_completo(self) -> Dict:
        """Gera relatório estatístico completo do histórico."""
        metricas = self.metricas_completas_por_dezena()

        return {
            "total_concursos": len(self.concursos),
            "loteria": self.loteria.value if self.loteria else None,
            "primeiro_concurso": self.concursos[0].numero if self.concursos else None,
            "ultimo_concurso": self.concursos[-1].numero if self.concursos else None,
            "metricas_dezenas": {d: {
                "frequencia_absoluta": m.frequencia_absoluta,
                "frequencia_relativa": m.frequencia_relativa,
                "atraso_atual": m.atraso_atual,
                "atraso_medio": m.atraso_medio,
                "atraso_maximo": m.atraso_maximo,
                "ultima_ocorrencia": m.ultima_ocorrencia,
                "tendencia": m.tendencia
            } for d, m in metricas.items()},
            "estatisticas_soma": self.estatisticas_soma(),
            "estatisticas_media": self.estatisticas_media(),
            "distribuicao_pares_impares": {
                "media_pares": round(np.mean(self.distribuicao_pares_impares()["pares"]), 2),
                "media_impares": round(np.mean(self.distribuicao_pares_impares()["impares"]), 2),
            },
            "distribuicao_baixos_altos": {
                "media_baixos": round(np.mean(self.distribuicao_baixos_altos()["baixos"]), 2),
                "media_altos": round(np.mean(self.distribuicao_baixos_altos()["altos"]), 2),
            },
            "repeticoes": self.repeticoes_entre_concursos(),
            "sequencias": self.analise_sequencias_consecutivas(),
            "heatmap": self.heatmap_data()
        }
