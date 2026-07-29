
"""
motor_matematico.py - Motor de Análise Matemática
"""
from typing import List, Set, Tuple, Dict, Iterator
from itertools import combinations, permutations
import math
import numpy as np
from models import LoteriaTipo


class MotorMatematico:
    """
    Motor de análise matemática e combinatória para loterias.
    Implementa combinações, permutações, desdobramentos e fechamentos.
    """

    def __init__(self, loteria: LoteriaTipo):
        self.loteria = loteria
        self.total_dezenas = loteria.dezenas_totais
        self.dezenas_sorteadas = loteria.dezenas_sorteadas

    # ═══════════════════════════════════════════════════════════
    # ANÁLISE COMBINATÓRIA BÁSICA
    # ═══════════════════════════════════════════════════════════

    def combinacoes_totais(self, n: int = None, k: int = None) -> int:
        """C(n,k) = n! / (k!(n-k)!)"""
        n = n or self.total_dezenas
        k = k or self.dezenas_sorteadas
        return math.comb(n, k)

    def permutacoes_totais(self, n: int = None, k: int = None) -> int:
        """P(n,k) = n! / (n-k)!"""
        n = n or self.total_dezenas
        k = k or self.dezenas_sorteadas
        return math.perm(n, k)

    def probabilidade_acerto(self, dezenas_apostadas: int, acertos_desejados: int) -> float:
        """
        Probabilidade de acertar exatamente K dezenas
        apostando N dezenas em uma loteria que sorteia M.
        Fórmula: C(M,K) * C(N-M, N-K) / C(N, M)
        """
        m = self.dezenas_sorteadas
        n = dezenas_apostadas
        k = acertos_desejados

        if k > m or k > n:
            return 0.0

        # C(m, k) * C(total - m, n - k) / C(total, n)
        numerador = math.comb(m, k) * math.comb(self.total_dezenas - m, n - k)
        denominador = math.comb(self.total_dezenas, n)

        return numerador / denominador if denominador > 0 else 0.0

    def probabilidade_acerto_minimo(self, dezenas_apostadas: int, acertos_minimos: int) -> float:
        """Probabilidade de acertar pelo menos K dezenas."""
        prob = 0.0
        for k in range(acertos_minimos, min(dezenas_apostadas, self.dezenas_sorteadas) + 1):
            prob += self.probabilidade_acerto(dezenas_apostadas, k)
        return prob

    def tabela_probabilidades(self, dezenas_apostadas: int) -> Dict[int, float]:
        """Tabela completa de probabilidades para uma aposta."""
        return {
            k: round(self.probabilidade_acerto(dezenas_apostadas, k), 10)
            for k in range(min(dezenas_apostadas, self.dezenas_sorteadas) + 1)
        }

    # ═══════════════════════════════════════════════════════════
    # GERAÇÃO DE COMBINAÇÕES
    # ═══════════════════════════════════════════════════════════

    def gerar_combinacoes(self, dezenas: List[int], k: int) -> Iterator[Tuple[int, ...]]:
        """Gera todas as combinações de k elementos de uma lista."""
        return combinations(sorted(dezenas), k)

    def gerar_combinacoes_aleatorias(
        self,
        quantidade: int,
        n_dezenas: int = None,
        seed: int = None
    ) -> List[Set[int]]:
        """Gera combinações aleatórias uniformemente distribuídas."""
        if seed is not None:
            np.random.seed(seed)

        n = n_dezenas or self.dezenas_sorteadas
        jogos = []
        for _ in range(quantidade):
            jogo = set(np.random.choice(
                range(1, self.total_dezenas + 1),
                size=n,
                replace=False
            ))
            jogos.append(jogo)
        return jogos

    # ═══════════════════════════════════════════════════════════
    # DESDOBRAMENTOS
    # ═══════════════════════════════════════════════════════════

    def desdobramento_completo(self, dezenas_base: List[int], n_por_jogo: int) -> List[Set[int]]:
        """
        Desdobramento completo: todas as combinações possíveis.
        CUIDADO: Pode gerar milhões de combinações.
        """
        return [set(c) for c in combinations(sorted(dezenas_base), n_por_jogo)]

    def desdobramento_limitado(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        max_jogos: int = 1000,
        seed: int = None
    ) -> List[Set[int]]:
        """
        Desdobramento limitado: amostra aleatória do desdobramento completo.
        """
        if seed is not None:
            np.random.seed(seed)

        todas = list(combinations(sorted(dezenas_base), n_por_jogo))
        if len(todas) <= max_jogos:
            return [set(c) for c in todas]

        indices = np.random.choice(len(todas), size=max_jogos, replace=False)
        return [set(todas[i]) for i in indices]

    def desdobramento_garantia(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        garantia: int
    ) -> List[Set[int]]:
        """
        Desdobramento com garantia mínima de acertos.
        Garante que qualquer combinação de 'garantia' dezenas
        das dezenas_base apareça em pelo menos um jogo.
        """
        if garantia > n_por_jogo:
            raise ValueError("Garantia não pode ser maior que dezenas por jogo")

        # Algoritmo guloso de cobertura
        todas_garantias = list(combinations(sorted(dezenas_base), garantia))
        jogos = []
        cobertas = set()

        for g in todas_garantias:
            g_tuple = tuple(sorted(g))
            if g_tuple in cobertas:
                continue

            # Cria um jogo que cobre esta garantia
            jogo = set(g)
            # Completa o jogo com dezenas restantes
            restantes = [d for d in dezenas_base if d not in jogo]
            while len(jogo) < n_por_jogo and restantes:
                jogo.add(restantes.pop(0))

            jogos.append(jogo)

            # Marca todas as garantias cobertas por este jogo
            for sub in combinations(sorted(jogo), garantia):
                cobertas.add(tuple(sorted(sub)))

        return jogos

    # ═══════════════════════════════════════════════════════════
    # FECHAMENTOS MATEMÁTICOS
    # ═══════════════════════════════════════════════════════════

    def fechamento_completo(self, dezenas_aposta: int) -> int:
        """
        Número de jogos no fechamento completo.
        C(total_dezenas, dezenas_aposta)
        """
        return self.combinacoes_totais(self.total_dezenas, dezenas_aposta)

    def fechamento_reduzido(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        garantia: int,
        acerto_minimo: int = 1
    ) -> List[Set[int]]:
        """
        Fechamento reduzido: cobertura mínima com garantia.
        """
        # Usa algoritmo de cobertura por conjuntos
        todas_comb_garantia = list(combinations(sorted(dezenas_base), garantia))
        jogos_selecionados = []
        nao_cobertas = set(todas_comb_garantia)

        while nao_cobertas:
            # Encontra o jogo que cobre mais garantias não cobertas
            melhor_jogo = None
            melhor_cobertura = set()

            # Gera candidatos (amostra para performance)
            candidatos = list(combinations(sorted(dezenas_base), n_por_jogo))
            if len(candidatos) > 10000:
                import random
                candidatos = random.sample(candidatos, 10000)

            for candidato in candidatos:
                cobertura = set()
                for sub in combinations(candidato, garantia):
                    if sub in nao_cobertas:
                        cobertura.add(sub)
                if len(cobertura) > len(melhor_cobertura):
                    melhor_cobertura = cobertura
                    melhor_jogo = set(candidato)

            if melhor_jogo is None:
                break

            jogos_selecionados.append(melhor_jogo)
            nao_cobertas -= melhor_cobertura

        return jogos_selecionados

    # ═══════════════════════════════════════════════════════════
    # DISTRIBUIÇÃO UNIFORME E BALANCEAMENTO
    # ═══════════════════════════════════════════════════════════

    def distribuicao_uniforme(self, n_dezenas: int, n_jogos: int, seed: int = None) -> List[Set[int]]:
        """
        Gera jogos com distribuição uniforme das dezenas.
        Tenta balancear a frequência de cada dezena entre os jogos.
        """
        if seed is not None:
            np.random.seed(seed)

        jogos = []
        frequencias = {d: 0 for d in range(1, self.total_dezenas + 1)}

        for _ in range(n_jogos):
            # Pondera escolha por frequência (menos frequentes têm mais chance)
            pesos = [1.0 / (frequencias[d] + 1) for d in range(1, self.total_dezenas + 1)]
            pesos = np.array(pesos) / sum(pesos)

            jogo = set(np.random.choice(
                range(1, self.total_dezenas + 1),
                size=n_dezenas,
                replace=False,
                p=pesos
            ))

            for d in jogo:
                frequencias[d] += 1

            jogos.append(jogo)

        return jogos

    def balanceamento_jogo(self, dezenas: List[int]) -> Dict:
        """
        Avalia o balanceamento de um jogo em múltiplas dimensões.
        """
        dezenas = sorted(dezenas)
        meio = self.total_dezenas // 2

        pares = len([d for d in dezenas if d % 2 == 0])
        impares = len(dezenas) - pares

        baixos = len([d for d in dezenas if d <= meio])
        altos = len(dezenas) - baixos

        # Distribuição por faixas
        faixas = {i: 0 for i in range(1, 6)}
        for d in dezenas:
            faixa = ((d - 1) // (self.total_dezenas // 5)) + 1
            if faixa in faixas:
                faixas[faixa] += 1

        # Sequências
        seqs = []
        atual = [dezenas[0]]
        for i in range(1, len(dezenas)):
            if dezenas[i] == dezenas[i-1] + 1:
                atual.append(dezenas[i])
            else:
                if len(atual) >= 2:
                    seqs.append(atual[:])
                atual = [dezenas[i]]
        if len(atual) >= 2:
            seqs.append(atual)

        return {
            "pares": pares,
            "impares": impares,
            "baixos": baixos,
            "altos": altos,
            "faixas": faixas,
            "sequencias": len(seqs),
            "tamanho_sequencias": [len(s) for s in seqs],
            "soma": sum(dezenas),
            "media": round(sum(dezenas) / len(dezenas), 2)
        }

    # ═══════════════════════════════════════════════════════════
    # SEQUÊNCIAS DE FIBONACCI
    # ═══════════════════════════════════════════════════════════

    def sequencia_fibonacci(self, max_val: int = None) -> List[int]:
        """Gera sequência de Fibonacci até o limite da loteria."""
        max_val = max_val or self.total_dezenas
        fib = [1, 1]
        while True:
            prox = fib[-1] + fib[-2]
            if prox > max_val:
                break
            fib.append(prox)
        return fib

    def jogo_com_fibonacci(self, n_dezenas: int, n_fibonacci: int = 3) -> Set[int]:
        """
        Gera jogo incluindo dezenas da sequência de Fibonacci.
        n_fibonacci: quantas dezenas da sequência devem estar no jogo.
        """
        fibs = set(self.sequencia_fibonacci())
        fibs = {f for f in fibs if f <= self.total_dezenas}

        if len(fibs) < n_fibonacci:
            n_fibonacci = len(fibs)

        jogo = set(np.random.choice(list(fibs), size=n_fibonacci, replace=False))

        restantes = [d for d in range(1, self.total_dezenas + 1) if d not in jogo]
        complemento = set(np.random.choice(restantes, size=n_dezenas - n_fibonacci, replace=False))
        jogo.update(complemento)

        return jogo

    # ═══════════════════════════════════════════════════════════
    # PROGRESSÕES ARITMÉTICAS E GEOMÉTRICAS
    # ═══════════════════════════════════════════════════════════

    def progressao_aritmetica(self, a1: int, r: int, n: int) -> List[int]:
        """PA: a1, a1+r, a1+2r, ..."""
        return [a1 + i * r for i in range(n)]

    def progressao_geometrica(self, a1: int, r: float, n: int) -> List[int]:
        """PG: a1, a1*r, a1*r², ... (arredondado para inteiros)"""
        return [int(round(a1 * (r ** i))) for i in range(n)]

    def jogos_com_pa(self, n_dezenas: int, n_pa: int = 2) -> Set[int]:
        """Gera jogo contendo uma progressão aritmética."""
        # Escolhe uma PA aleatória
        r = np.random.randint(1, 5)
        a1 = np.random.randint(1, self.total_dezenas - n_pa * r)
        pa = self.progressao_aritmetica(a1, r, n_pa)
        pa = [p for p in pa if 1 <= p <= self.total_dezenas]

        jogo = set(pa)
        restantes = [d for d in range(1, self.total_dezenas + 1) if d not in jogo]
        if len(restantes) >= n_dezenas - len(jogo):
            complemento = set(np.random.choice(restantes, size=n_dezenas - len(jogo), replace=False))
            jogo.update(complemento)

        return jogo

    # ═══════════════════════════════════════════════════════════
    # COBERTURA MATEMÁTICA
    # ═══════════════════════════════════════════════════════════

    def taxa_cobertura(self, jogos: List[Set[int]], dezenas_alvo: List[int] = None) -> float:
        """
        Taxa de cobertura das dezenas alvo pelos jogos gerados.
        """
        if dezenas_alvo is None:
            dezenas_alvo = list(range(1, self.total_dezenas + 1))

        cobertas = set()
        for j in jogos:
            cobertas.update(j)

        return len(cobertas & set(dezenas_alvo)) / len(dezenas_alvo)

    def redundancia(self, jogos: List[Set[int]]) -> Dict[int, int]:
        """
        Quantas vezes cada dezena aparece nos jogos.
        """
        contagem = Counter()
        for j in jogos:
            contagem.update(j)
        return dict(contagem)
