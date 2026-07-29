
"""
main_engine.py - Orquestrador Principal do Sistema
"""
from typing import List, Dict, Optional, Callable
from datetime import datetime
from models import Concurso, LoteriaTipo, EstrategiaConfig
from motor_estatistico import MotorEstatistico
from motor_matematico import MotorMatematico
from motor_simulacoes import MotorSimulacoes
from motor_estrategias import MotorEstrategias
from motor_score import MotorScore
from motor_desdobramentos import MotorDesdobramentos
from motor_temporal import MotorTemporal
from motor_padroes import MotorPadroes
from motor_comparativo import MotorComparativo
from motor_genetico import MotorGenetico
from motor_relatorios import MotorRelatorios
from gerador_jogos import GeradorJogos


class MotorPrincipal:
    """
    Orquestrador principal que integra todos os motores do sistema.
    Interface única para acesso a todas as funcionalidades.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None

        # Inicializa todos os motores
        self.estatistico = MotorEstatistico(self.concursos)
        self.matematico = MotorMatematico(self.loteria) if self.loteria else None
        self.simulacoes = MotorSimulacoes(self.concursos)
        self.estrategias = MotorEstrategias(self.concursos)
        self.score = MotorScore(self.concursos)
        self.desdobramentos = MotorDesdobramentos(self.loteria) if self.loteria else None
        self.temporal = MotorTemporal(self.concursos)
        self.padroes = MotorPadroes(self.concursos)
        self.comparativo = MotorComparativo()
        self.genetico = None  # Inicializado sob demanda
        self.relatorios = MotorRelatorios(self.concursos)
        self.gerador = GeradorJogos(self.concursos)

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE CONVENIÊNCIA
    # ═══════════════════════════════════════════════════════════

    def resumo(self) -> Dict:
        """Resumo rápido do sistema."""
        return {
            "loteria": self.loteria.value if self.loteria else None,
            "total_concursos": len(self.concursos),
            "primeiro_concurso": self.concursos[0].numero if self.concursos else None,
            "ultimo_concurso": self.concursos[-1].numero if self.concursos else None,
            "motores_disponiveis": [
                "estatistico", "matematico", "simulacoes", "estrategias",
                "score", "desdobramentos", "temporal", "padroes",
                "comparativo", "genetico", "relatorios", "gerador"
            ]
        }

    def analise_completa(self) -> Dict:
        """Executa análise completa de todos os motores."""
        print("Executando análise estatística...")
        rel_est = self.estatistico.relatorio_completo()

        print("Executando análise temporal...")
        pred_temp = self.temporal.ranking_predicoes()[:10]

        print("Executando análise de padrões...")
        padroes_hist = self.padroes.padroes_mais_comuns(10)

        print("Executando teste de aleatoriedade...")
        teste_aleat = self.comparativo.teste_chi_quadrado(self.concursos)

        return {
            "estatistico": rel_est,
            "temporal": [{"dezena": p.dezena, "prob": p.probabilidade_saida} for p in pred_temp],
            "padroes": padroes_hist,
            "aleatoriedade": teste_aleat,
            "gerado_em": datetime.now().isoformat()
        }

    # ═══════════════════════════════════════════════════════════
    # GERAÇÃO DE JOGOS UNIFICADA
    # ═══════════════════════════════════════════════════════════

    def gerar_jogos(
        self,
        metodo: str,
        n_dezenas: int = 15,
        n_jogos: int = 1,
        params: Dict = None
    ) -> List[Dict]:
        """
        Gera jogos usando qualquer método disponível.
        """
        return self.gerador.gerar(metodo, n_dezenas, n_jogos, params or {})

    def gerar_jogos_geneticos(
        self,
        n_dezenas: int = 15,
        n_jogos: int = 10,
        n_geracoes: int = 50,
        fitness_pesos: Dict = None
    ) -> List[Dict]:
        """Gera jogos usando algoritmo genético."""
        if self.genetico is None:
            self.genetico = MotorGenetico(self.concursos)

        def fitness_custom(ind):
            return self.genetico.fitness_combinado(ind, fitness_pesos)

        self.genetico.evoluir(n_dezenas, n_geracoes, fitness_custom)
        return self.genetico.melhores_jogos(n_jogos)

    # ═══════════════════════════════════════════════════════════
    # ESTRATÉGIAS
    # ═══════════════════════════════════════════════════════════

    def criar_estrategia(self, config: EstrategiaConfig) -> str:
        return self.estrategias.criar_estrategia(config)

    def gerar_por_estrategia(self, estrategia_id: str, n_jogos: int = 1) -> List[Dict]:
        return self.estrategias.aplicar_estrategia(estrategia_id, n_jogos)

    # ═══════════════════════════════════════════════════════════
    # SIMULAÇÕES
    # ═══════════════════════════════════════════════════════════

    def simular_monte_carlo(self, n_simulacoes: int = 1000, n_dezenas: int = 15) -> Dict:
        rel = self.simulacoes.monte_carlo_aleatorio(n_simulacoes, n_dezenas)
        return self.relatorios.relatorio_simulacao(rel)

    def comparar_estrategias_simulacao(
        self,
        geradores: Dict[str, Callable],
        janela_treino: int = 50
    ) -> Dict:
        relatorios = self.simulacoes.comparar_estrategias(geradores, janela_treino)
        return self.simulacoes.estatisticas_agregadas(relatorios)

    # ═══════════════════════════════════════════════════════════
    # DESDOBRAMENTOS
    # ═══════════════════════════════════════════════════════════

    def desdobramento_completo(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        max_jogos: int = 100
    ) -> List[Dict]:
        jogos = self.desdobramentos.desdobramento_simples(dezenas_base, n_por_jogo, max_jogos)
        return [{"dezenas": sorted(j), "tipo": "desdobramento"} for j in jogos]

    def fechamento_reduzido(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        garantia: int,
        max_jogos: int = 500
    ) -> Dict:
        return self.desdobramentos.fechamento_reduzido_otimizado(
            dezenas_base, n_por_jogo, garantia, max_jogos
        )

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIOS
    # ═══════════════════════════════════════════════════════════

    def exportar_relatorio(self, formato: str = "json") -> str:
        if formato == "json":
            return self.relatorios.relatorio_json(self.estatistico)
        return "Formato não suportado"

    def relatorio_executivo(self) -> Dict:
        return self.relatorios.relatorio_executivo(self.estatistico)

    # ═══════════════════════════════════════════════════════════
    # TESTES ESTATÍSTICOS
    # ═══════════════════════════════════════════════════════════

    def testar_aleatoriedade(self) -> Dict:
        return {
            "chi_quadrado": self.comparativo.teste_chi_quadrado(self.concursos),
            "kolmogorov_smirnov": self.comparativo.teste_ks(self.concursos),
            "runs_test": self.comparativo.teste_runs(self.concursos, 1)
        }
