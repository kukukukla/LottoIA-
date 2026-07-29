
"""
motor_padroes.py - Motor de Detecção de Padrões Avançados
"""
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict, Counter
import numpy as np
from models import Concurso, LoteriaTipo


class MotorPadroes:
    """
    Motor de detecção de padrões avançados em sorteios.
    Identifica padrões geométricos, numéricos e estruturais.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None

    # ═══════════════════════════════════════════════════════════
    # PADRÕES GEOMÉTRICOS (Cartela)
    # ═══════════════════════════════════════════════════════════

    def padrao_cruz(self, dezenas: List[int]) -> bool:
        """Detecta padrão em cruz na cartela."""
        # Centro da cartela (para Lotofácil: 13)
        if self.loteria == LoteriaTipo.LOTOFACIL:
            centro = 13
            cruz = {centro, 8, 18, 12, 14}  # centro + 4 vizinhos
            return len(set(dezenas) & cruz) >= 3
        return False

    def padrao_diagonal(self, dezenas: List[int]) -> bool:
        """Detecta padrão diagonal na cartela."""
        if self.loteria == LoteriaTipo.LOTOFACIL:
            diag1 = {1, 7, 13, 19, 25}  # diagonal principal
            diag2 = {5, 9, 13, 17, 21}  # diagonal secundária
            return len(set(dezenas) & diag1) >= 3 or len(set(dezenas) & diag2) >= 3
        return False

    def padrao_cantos(self, dezenas: List[int]) -> bool:
        """Detecta concentração nos cantos da cartela."""
        if self.loteria == LoteriaTipo.LOTOFACIL:
            cantos = {1, 5, 21, 25}
            return len(set(dezenas) & cantos) >= 3
        return False

    def padrao_bordas(self, dezenas: List[int]) -> bool:
        """Detecta concentração nas bordas da cartela."""
        if self.loteria == LoteriaTipo.LOTOFACIL:
            bordas = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
            return len(set(dezenas) & bordas) >= 10
        return False

    def padrao_centro(self, dezenas: List[int]) -> bool:
        """Detecta concentração no centro da cartela."""
        if self.loteria == LoteriaTipo.LOTOFACIL:
            centro = {7, 8, 9, 12, 13, 14, 17, 18, 19}
            return len(set(dezenas) & centro) >= 8
        return False

    # ═══════════════════════════════════════════════════════════
    # PADRÕES NUMÉRICOS
    # ═══════════════════════════════════════════════════════════

    def padrao_numeros_primos(self, dezenas: List[int]) -> Dict:
        """Análise de números primos no jogo."""
        primos = {2, 3, 5, 7, 11, 13, 17, 19, 23}
        primos_no_jogo = set(dezenas) & primos
        return {
            "quantidade": len(primos_no_jogo),
            "dezenas": sorted(primos_no_jogo),
            "proporcao": round(len(primos_no_jogo) / len(dezenas), 2)
        }

    def padrao_multiplos(self, dezenas: List[int], n: int = 3) -> Dict:
        """Análise de múltiplos de N."""
        multiplos = {d for d in dezenas if d % n == 0}
        return {
            "de": n,
            "quantidade": len(multiplos),
            "dezenas": sorted(multiplos),
            "proporcao": round(len(multiplos) / len(dezenas), 2)
        }

    def padrao_digitos(self, dezenas: List[int]) -> Dict:
        """Análise dos dígitos das dezenas."""
        digitos = Counter()
        for d in dezenas:
            for digito in str(d):
                digitos[int(digito)] += 1
        return dict(digitos)

    def padrao_dezenas_terminadas(self, dezenas: List[int]) -> Dict[int, int]:
        """Conta dezenas terminadas em cada dígito (0-9)."""
        terminacoes = Counter()
        for d in dezenas:
            terminacoes[d % 10] += 1
        return dict(terminacoes)

    def padrao_soma_digitos(self, dezenas: List[int]) -> Dict:
        """Soma dos dígitos de cada dezena."""
        somas = [sum(int(d) for d in str(dez)) for dez in dezenas]
        return {
            "somas": somas,
            "media": round(np.mean(somas), 2),
            "mediana": round(np.median(somas), 2)
        }

    # ═══════════════════════════════════════════════════════════
    # PADRÕES DE DISTÂNCIA
    # ═══════════════════════════════════════════════════════════

    def distancias_entre_dezenas(self, dezenas: List[int]) -> List[int]:
        """Distâncias entre dezenas consecutivas."""
        ordenadas = sorted(dezenas)
        return [ordenadas[i+1] - ordenadas[i] for i in range(len(ordenadas)-1)]

    def padrao_distancias(self, dezenas: List[int]) -> Dict:
        """Análise estatística das distâncias."""
        dists = self.distancias_entre_dezenas(dezenas)
        return {
            "distancias": dists,
            "media_distancia": round(np.mean(dists), 2) if dists else 0,
            "max_distancia": max(dists) if dists else 0,
            "min_distancia": min(dists) if dists else 0,
            "distancias_iguais": len([d for d in Counter(dists).values() if d > 1])
        }

    def padrao_simetria(self, dezenas: List[int]) -> Dict:
        """Verifica simetria em relação ao centro da cartela."""
        total = self.loteria.dezenas_totais
        pares_sim = []
        for d in dezenas:
            simetrico = total + 1 - d
            if simetrico in dezenas and simetrico != d:
                par = tuple(sorted([d, simetrico]))
                if par not in pares_sim:
                    pares_sim.append(par)

        return {
            "pares_simetricos": pares_sim,
            "quantidade_pares": len(pares_sim),
            "grau_simetria": round(len(pares_sim) * 2 / len(dezenas), 2) if dezenas else 0
        }

    # ═══════════════════════════════════════════════════════════
    # PADRÕES HISTÓRICOS
    # ═══════════════════════════════════════════════════════════

    def padroes_mais_comuns(self, n_padroes: int = 10) -> List[Dict]:
        """Identifica os padrões mais comuns no histórico."""
        padroes = Counter()

        for c in self.concursos:
            dezenas = c.dezenas
            # Verifica cada padrão
            if self.padrao_cruz(dezenas):
                padroes["cruz"] += 1
            if self.padrao_diagonal(dezenas):
                padroes["diagonal"] += 1
            if self.padrao_cantos(dezenas):
                padroes["cantos"] += 1
            if self.padrao_bordas(dezenas):
                padroes["bordas"] += 1
            if self.padrao_centro(dezenas):
                padroes["centro"] += 1

            primos = self.padrao_numeros_primos(dezenas)
            padroes[f"primos_{primos['quantidade']}"] += 1

        return [{"padrao": p, "frequencia": f, "percentual": round(f/len(self.concursos)*100, 2)}
                for p, f in padroes.most_common(n_padroes)]

    def frequencia_padroes_por_concurso(self) -> List[Dict]:
        """Retorna padrões detectados em cada concurso."""
        resultado = []
        for c in self.concursos:
            padroes = []
            if self.padrao_cruz(c.dezenas):
                padroes.append("cruz")
            if self.padrao_diagonal(c.dezenas):
                padroes.append("diagonal")
            if self.padrao_cantos(c.dezenas):
                padroes.append("cantos")
            if self.padrao_bordas(c.dezenas):
                padroes.append("bordas")
            if self.padrao_centro(c.dezenas):
                padroes.append("centro")

            resultado.append({
                "concurso": c.numero,
                "padroes": padroes,
                "quantidade": len(padroes)
            })
        return resultado

    # ═══════════════════════════════════════════════════════════
    # ANÁLISE DE CLUSTER
    # ═══════════════════════════════════════════════════════════

    def clusters_dezenas(self, dezenas: List[int], max_distancia: int = 3) -> List[List[int]]:
        """Identifica clusters de dezenas próximas."""
        ordenadas = sorted(dezenas)
        clusters = []
        atual = [ordenadas[0]]

        for i in range(1, len(ordenadas)):
            if ordenadas[i] - ordenadas[i-1] <= max_distancia:
                atual.append(ordenadas[i])
            else:
                if len(atual) >= 2:
                    clusters.append(atual[:])
                atual = [ordenadas[i]]

        if len(atual) >= 2:
            clusters.append(atual)

        return clusters

    def analise_clusters_historico(self) -> Dict:
        """Análise estatística de clusters no histórico."""
        todos_clusters = []
        tamanhos = []

        for c in self.concursos:
            clusters = self.clusters_dezenas(c.dezenas)
            todos_clusters.extend(clusters)
            tamanhos.extend([len(cl) for cl in clusters])

        return {
            "total_clusters": len(todos_clusters),
            "media_clusters_por_concurso": round(len(todos_clusters) / len(self.concursos), 2),
            "tamanho_medio_cluster": round(np.mean(tamanhos), 2) if tamanhos else 0,
            "tamanho_maximo": max(tamanhos) if tamanhos else 0,
            "distribuicao_tamanhos": dict(Counter(tamanhos))
        }
