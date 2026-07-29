
"""
motor_desdobramentos.py - Motor de Desdobramentos e Fechamentos
"""
from typing import List, Set, Dict, Tuple, Optional
from itertools import combinations
import numpy as np
from models import LoteriaTipo
from motor_matematico import MotorMatematico


class MotorDesdobramentos:
    """
    Motor especializado em desdobramentos e fechamentos matemáticos.
    Implementa algoritmos de cobertura otimizada.
    """

    def __init__(self, loteria: LoteriaTipo):
        self.loteria = loteria
        self.matematico = MotorMatematico(loteria)

    # ═══════════════════════════════════════════════════════════
    # DESDOBRAMENTOS
    # ═══════════════════════════════════════════════════════════

    def desdobramento_simples(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        max_jogos: Optional[int] = None
    ) -> List[Set[int]]:
        """
        Desdobramento simples: todas as combinações ou amostra.
        """
        todas = list(combinations(sorted(dezenas_base), n_por_jogo))

        if max_jogos and len(todas) > max_jogos:
            # Amostra sistemática para cobertura uniforme
            step = len(todas) // max_jogos
            indices = [i * step for i in range(max_jogos)]
            selecionadas = [todas[i] for i in indices]
        else:
            selecionadas = todas

        return [set(j) for j in selecionadas]

    def desdobramento_aleatorio(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        n_jogos: int,
        seed: int = None
    ) -> List[Set[int]]:
        """Desdobramento com amostragem aleatória."""
        if seed is not None:
            np.random.seed(seed)

        todas = list(combinations(sorted(dezenas_base), n_por_jogo))
        if len(todas) <= n_jogos:
            return [set(j) for j in todas]

        indices = np.random.choice(len(todas), size=n_jogos, replace=False)
        return [set(todas[i]) for i in indices]

    def desdobramento_por_garantia(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        garantia: int,
        max_jogos: int = 1000
    ) -> List[Set[int]]:
        """
        Desdobramento com garantia mínima usando algoritmo guloso.
        Garante que toda combinação de 'garantia' dezenas das 'dezenas_base'
        apareça em pelo menos um jogo.
        """
        if garantia > n_por_jogo:
            raise ValueError("Garantia não pode exceder dezenas por jogo")

        # Gera todas as combinações de garantia
        todas_garantias = list(combinations(sorted(dezenas_base), garantia))
        nao_cobertas = set(todas_garantias)
        jogos = []

        while nao_cobertas and len(jogos) < max_jogos:
            melhor_jogo = None
            melhor_cobertura = set()

            # Heurística: escolhe dezenas que cobrem mais garantias
            # Amostra candidatos para performance
            candidatos = self._gerar_candidatos(dezenas_base, n_por_jogo, 500)

            for candidato in candidatos:
                cobertura = set()
                for sub in combinations(sorted(candidato), garantia):
                    sub_t = tuple(sorted(sub))
                    if sub_t in nao_cobertas:
                        cobertura.add(sub_t)

                if len(cobertura) > len(melhor_cobertura):
                    melhor_cobertura = cobertura
                    melhor_jogo = candidato

            if melhor_jogo is None or not melhor_cobertura:
                break

            jogos.append(melhor_jogo)
            nao_cobertas -= melhor_cobertura

        return jogos

    def _gerar_candidatos(self, dezenas_base: List[int], n_por_jogo: int, n_candidatos: int) -> List[Set[int]]:
        """Gera candidatos para o algoritmo guloso."""
        todas = list(combinations(sorted(dezenas_base), n_por_jogo))
        if len(todas) <= n_candidatos:
            return [set(c) for c in todas]

        indices = np.random.choice(len(todas), size=n_candidatos, replace=False)
        return [set(todas[i]) for i in indices]

    # ═══════════════════════════════════════════════════════════
    # FECHAMENTOS
    # ═══════════════════════════════════════════════════════════

    def fechamento_completo(self, dezenas_aposta: int) -> Dict:
        """
        Informações sobre o fechamento completo.
        """
        total = self.matematico.fechamento_completo(dezenas_aposta)
        return {
            "dezenas_aposta": dezenas_aposta,
            "total_jogos": total,
            "custo_estimado": total * 2.50,  # R$ 2,50 por jogo
            "viavel": total <= 100000
        }

    def fechamento_reduzido_otimizado(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        garantia: int,
        max_jogos: int = 500
    ) -> Dict:
        """
        Fechamento reduzido otimizado.
        Retorna jogos + estatísticas de cobertura.
        """
        jogos = self.desdobramento_por_garantia(
            dezenas_base, n_por_jogo, garantia, max_jogos
        )

        # Calcula cobertura
        todas_garantias = list(combinations(sorted(dezenas_base), garantia))
        cobertas = set()
        for jogo in jogos:
            for sub in combinations(sorted(jogo), garantia):
                cobertas.add(tuple(sorted(sub)))

        taxa_cobertura = len(cobertas) / len(todas_garantias) if todas_garantias else 0

        return {
            "jogos": [sorted(j) for j in jogos],
            "total_jogos": len(jogos),
            "garantia": garantia,
            "taxa_cobertura": round(taxa_cobertura, 4),
            "total_garantias": len(todas_garantias),
            "garantias_cobertas": len(cobertas),
            "economia": round((1 - len(jogos) / self.matematico.combinacoes_totais(len(dezenas_base), n_por_jogo)) * 100, 2) if len(dezenas_base) >= n_por_jogo else 0
        }

    def fechamento_por_faixas(
        self,
        faixas: Dict[str, List[int]],
        n_por_jogo: int,
        distribuicao: Dict[str, int]
    ) -> List[Set[int]]:
        """
        Fechamento por faixas: define quantas dezenas de cada faixa.
        """
        # Seleciona dezenas de cada faixa conforme distribuição
        selecionadas = []
        for faixa, dezenas in faixas.items():
            qtd = distribuicao.get(faixa, 0)
            if qtd > 0 and len(dezenas) >= qtd:
                escolhidas = np.random.choice(dezenas, size=qtd, replace=False)
                selecionadas.extend(escolhidas.tolist())

        if len(selecionadas) < n_por_jogo:
            # Completa com aleatórias
            todas = []
            for d in faixas.values():
                todas.extend(d)
            faltantes = [d for d in todas if d not in selecionadas]
            necessario = n_por_jogo - len(selecionadas)
            if faltantes and necessario > 0:
                extras = np.random.choice(faltantes, size=min(necessario, len(faltantes)), replace=False)
                selecionadas.extend(extras.tolist())

        # Gera combinações das selecionadas
        if len(selecionadas) >= n_por_jogo:
            jogo = set(np.random.choice(selecionadas, size=n_por_jogo, replace=False))
            return [jogo]

        return []

    # ═══════════════════════════════════════════════════════════
    # COBERTURA E OTIMIZAÇÃO
    # ═══════════════════════════════════════════════════════════

    def avaliar_cobertura(
        self,
        jogos: List[Set[int]],
        dezenas_base: List[int],
        garantia: int
    ) -> Dict:
        """Avalia a qualidade da cobertura de um conjunto de jogos."""
        todas_garantias = list(combinations(sorted(dezenas_base), garantia))
        cobertas = set()
        redundancia = {}

        for jogo in jogos:
            for sub in combinations(sorted(jogo), garantia):
                sub_t = tuple(sorted(sub))
                cobertas.add(sub_t)
                redundancia[sub_t] = redundancia.get(sub_t, 0) + 1

        # Dezenas mais redundantes
        dezenas_contagem = {}
        for j in jogos:
            for d in j:
                dezenas_contagem[d] = dezenas_contagem.get(d, 0) + 1

        return {
            "taxa_cobertura": round(len(cobertas) / len(todas_garantias), 4) if todas_garantias else 0,
            "total_garantias": len(todas_garantias),
            "garantias_cobertas": len(cobertas),
            "redundancia_media": round(np.mean(list(redundancia.values())), 2) if redundancia else 0,
            "redundancia_maxima": max(redundancia.values()) if redundancia else 0,
            "dezenas_mais_frequentes": sorted(dezenas_contagem.items(), key=lambda x: x[1], reverse=True)[:10]
        }

    def otimizar_jogos(
        self,
        jogos: List[Set[int]],
        dezenas_base: List[int],
        garantia: int,
        max_iteracoes: int = 100
    ) -> List[Set[int]]:
        """
        Tenta reduzir o número de jogos mantendo a cobertura.
        Algoritmo de remoção gulosa.
        """
        todas_garantias = set(combinations(sorted(dezenas_base), garantia))
        jogos_atual = jogos[:]

        for _ in range(max_iteracoes):
            if len(jogos_atual) <= 1:
                break

            # Tenta remover cada jogo e verifica cobertura
            melhor_remover = None
            melhor_cobertura = 0

            for i, jogo in enumerate(jogos_atual):
                restantes = jogos_atual[:i] + jogos_atual[i+1:]
                cobertas = set()
                for j in restantes:
                    for sub in combinations(sorted(j), garantia):
                        cobertas.add(tuple(sorted(sub)))

                if len(cobertas) >= melhor_cobertura:
                    melhor_cobertura = len(cobertas)
                    melhor_remover = i

            # Se ainda cobre tudo, remove
            jogos_teste = jogos_atual[:melhor_remover] + jogos_atual[melhor_remover+1:]
            cobertas_teste = set()
            for j in jogos_teste:
                for sub in combinations(sorted(j), garantia):
                    cobertas_teste.add(tuple(sorted(sub)))

            if cobertas_teste == todas_garantias:
                jogos_atual = jogos_teste
            else:
                break

        return jogos_atual
