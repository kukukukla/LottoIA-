
"""
motor_genetico.py - Motor de Otimização Genética para Jogos
"""
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass
import numpy as np
import random
from models import Concurso, LoteriaTipo
from motor_estatistico import MotorEstatistico


@dataclass
class Individuo:
    """Representa um jogo no algoritmo genético."""
    dezenas: List[int]
    fitness: float = 0.0


class MotorGenetico:
    """
    Motor de otimização genética para geração de jogos.
    Evolui populações de jogos segundo funções de fitness configuráveis.
    """

    def __init__(
        self,
        concursos: List[Concurso],
        tamanho_populacao: int = 100,
        taxa_mutacao: float = 0.1,
        taxa_crossover: float = 0.8,
        elitismo: int = 5
    ):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None
        self.estatistico = MotorEstatistico(self.concursos)
        self.tamanho_pop = tamanho_populacao
        self.taxa_mut = taxa_mutacao
        self.taxa_cross = taxa_crossover
        self.elitismo = elitismo
        self.populacao = []

    # ═══════════════════════════════════════════════════════════
    # FUNÇÕES DE FITNESS
    # ═══════════════════════════════════════════════════════════

    def fitness_frequencia(self, individuo: Individuo) -> float:
        """Fitness baseado na frequência histórica das dezenas."""
        freq = self.estatistico.frequencia_absoluta()
        max_freq = max(freq.values()) if freq else 1
        score = sum(freq.get(d, 0) / max_freq for d in individuo.dezenas)
        return score / len(individuo.dezenas)

    def fitness_atraso(self, individuo: Individuo) -> float:
        """Fitness baseado no atraso (favorece dezenas atrasadas)."""
        atraso = self.estatistico.atraso_atual()
        atraso_medio = self.estatistico.atraso_medio()
        score = 0
        for d in individuo.dezenas:
            atual = atraso.get(d, 0)
            medio = atraso_medio.get(d, 1)
            if medio > 0:
                score += min(atual / medio, 2.0) / 2.0
        return score / len(individuo.dezenas)

    def fitness_diversidade(self, individuo: Individuo) -> float:
        """Fitness baseado na diversidade espacial das dezenas."""
        dezenas = sorted(individuo.dezenas)
        distancias = [dezenas[i+1] - dezenas[i] for i in range(len(dezenas)-1)]
        if not distancias:
            return 0
        media_dist = np.mean(distancias)
        dp_dist = np.std(distancias)
        # Premia distâncias uniformes
        return media_dist / (dp_dist + 1)

    def fitness_balanceamento(self, individuo: Individuo) -> float:
        """Fitness baseado no balanceamento par/ímpar e baixo/alto."""
        dezenas = individuo.dezenas
        meio = self.loteria.dezenas_totais // 2
        n = len(dezenas)

        pares = len([d for d in dezenas if d % 2 == 0])
        impares = n - pares
        bal_par = 1 - abs(pares - n/2) / (n/2) if n > 0 else 0

        baixos = len([d for d in dezenas if d <= meio])
        altos = n - baixos
        bal_baixo = 1 - abs(baixos - n/2) / (n/2) if n > 0 else 0

        return (bal_par + bal_baixo) / 2

    def fitness_combinado(
        self,
        individuo: Individuo,
        pesos: Dict[str, float] = None
    ) -> float:
        """Fitness combinado com pesos configuráveis."""
        pesos = pesos or {
            "frequencia": 0.25,
            "atraso": 0.25,
            "diversidade": 0.25,
            "balanceamento": 0.25
        }

        f_freq = self.fitness_frequencia(individuo)
        f_atraso = self.fitness_atraso(individuo)
        f_div = self.fitness_diversidade(individuo)
        f_bal = self.fitness_balanceamento(individuo)

        return (
            pesos.get("frequencia", 0.25) * f_freq +
            pesos.get("atraso", 0.25) * f_atraso +
            pesos.get("diversidade", 0.25) * f_div +
            pesos.get("balanceamento", 0.25) * f_bal
        )

    # ═══════════════════════════════════════════════════════════
    # OPERAÇÕES GENÉTICAS
    # ═══════════════════════════════════════════════════════════

    def _criar_individuo_aleatorio(self, n_dezenas: int) -> Individuo:
        """Cria um indivíduo aleatório."""
        dezenas = sorted(random.sample(
            range(1, self.loteria.dezenas_totais + 1),
            n_dezenas
        ))
        return Individuo(dezenas=dezenas)

    def _crossover(self, pai1: Individuo, pai2: Individuo, n_dezenas: int) -> Individuo:
        """Crossover de dois pais."""
        if random.random() > self.taxa_cross:
            return random.choice([pai1, pai2])

        # Combina dezenas dos dois pais
        pool = set(pai1.dezenas) | set(pai2.dezenas)
        if len(pool) >= n_dezenas:
            dezenas = sorted(random.sample(list(pool), n_dezenas))
        else:
            # Completa com aleatórias
            restantes = [d for d in range(1, self.loteria.dezenas_totais + 1) if d not in pool]
            extras = random.sample(restantes, n_dezenas - len(pool))
            dezenas = sorted(list(pool) + extras)

        return Individuo(dezenas=dezenas)

    def _mutacao(self, individuo: Individuo, n_dezenas: int) -> Individuo:
        """Aplica mutação em um indivíduo."""
        if random.random() > self.taxa_mut:
            return individuo

        dezenas = individuo.dezenas[:]
        # Substitui uma dezena aleatória
        idx = random.randint(0, len(dezenas) - 1)
        nova = random.randint(1, self.loteria.dezenas_totais)
        while nova in dezenas:
            nova = random.randint(1, self.loteria.dezenas_totais)
        dezenas[idx] = nova

        return Individuo(dezenas=sorted(dezenas))

    # ═══════════════════════════════════════════════════════════
    # ALGORITMO EVOLUTIVO
    # ═══════════════════════════════════════════════════════════

    def evoluir(
        self,
        n_dezenas: int,
        n_geracoes: int = 50,
        funcao_fitness: Callable = None,
        verbose: bool = False
    ) -> List[Individuo]:
        """
        Executa o algoritmo genético.
        """
        if funcao_fitness is None:
            funcao_fitness = self.fitness_combinado

        # População inicial
        self.populacao = [
            self._criar_individuo_aleatorio(n_dezenas)
            for _ in range(self.tamanho_pop)
        ]

        melhor_historico = []

        for geracao in range(n_geracoes):
            # Avalia fitness
            for ind in self.populacao:
                ind.fitness = funcao_fitness(ind)

            # Ordena por fitness
            self.populacao.sort(key=lambda x: x.fitness, reverse=True)
            melhor = self.populacao[0]
            melhor_historico.append(melhor.fitness)

            if verbose and geracao % 10 == 0:
                print(f"  Geração {geracao}: Melhor fitness = {melhor.fitness:.4f}")

            # Elitismo: mantém os melhores
            nova_populacao = self.populacao[:self.elitismo]

            # Gera nova população
            while len(nova_populacao) < self.tamanho_pop:
                # Seleção por torneio
                torneio = random.sample(self.populacao[:self.tamanho_pop//2], 3)
                pai1 = max(torneio, key=lambda x: x.fitness)
                torneio = random.sample(self.populacao[:self.tamanho_pop//2], 3)
                pai2 = max(torneio, key=lambda x: x.fitness)

                filho = self._crossover(pai1, pai2, n_dezenas)
                filho = self._mutacao(filho, n_dezenas)
                nova_populacao.append(filho)

            self.populacao = nova_populacao

        # Fitness final
        for ind in self.populacao:
            ind.fitness = funcao_fitness(ind)
        self.populacao.sort(key=lambda x: x.fitness, reverse=True)

        return self.populacao

    def melhores_jogos(self, n: int = 10) -> List[Dict]:
        """Retorna os N melhores jogos da população."""
        return [
            {
                "dezenas": ind.dezenas,
                "fitness": round(ind.fitness, 6),
                "ranking": i + 1
            }
            for i, ind in enumerate(self.populacao[:n])
        ]
