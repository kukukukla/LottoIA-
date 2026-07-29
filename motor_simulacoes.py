
"""
motor_simulacoes.py - Motor de Simulações e Backtests
"""
from typing import List, Dict, Callable, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
import numpy as np
from models import Concurso, LoteriaTipo, EstrategiaConfig
from motor_estatistico import MotorEstatistico


@dataclass
class ResultadoSimulacao:
    """Resultado de uma simulação individual"""
    concurso_numero: int
    dezenas_sorteadas: List[int]
    dezenas_apostadas: List[int]
    acertos: int
    premio_estimado: float = 0.0


@dataclass
class RelatorioSimulacao:
    """Relatório agregado de simulações"""
    estrategia_nome: str
    total_simulacoes: int
    acertos_distribuicao: Dict[int, int]
    acertos_percentual: Dict[int, float]
    media_acertos: float
    mediana_acertos: float
    desvio_padrao: float
    max_acertos: int
    min_acertos: int
    roi_estimado: float
    detalhes: List[ResultadoSimulacao] = field(default_factory=list)


class MotorSimulacoes:
    """
    Motor de simulações Monte Carlo e backtests.
    Permite testar estratégias sobre dados históricos.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None

    # ═══════════════════════════════════════════════════════════
    # BACKTEST
    # ═══════════════════════════════════════════════════════════

    def backtest_estrategia(
        self,
        gerador_jogos: Callable[[List[Concurso]], List[int]],
        janela_treino: int = 50,
        janela_teste: int = 1,
        passo: int = 1
    ) -> List[ResultadoSimulacao]:
        """
        Executa backtest walk-forward da estratégia.
        Treina com N concursos anteriores, testa no próximo.
        """
        resultados = []
        total = len(self.concursos)

        for i in range(janela_treino, total, passo):
            treino = self.concursos[i - janela_treino:i]
            teste = self.concursos[i:i + janela_teste]

            for concurso_teste in teste:
                jogo = gerador_jogos(treino)
                acertos = len(set(jogo) & set(concurso_teste.dezenas))

                resultados.append(ResultadoSimulacao(
                    concurso_numero=concurso_teste.numero,
                    dezenas_sorteadas=concurso_teste.dezenas,
                    dezenas_apostadas=sorted(jogo),
                    acertos=acertos
                ))

        return resultados

    def backtest_multiplo(
        self,
        geradores: Dict[str, Callable[[List[Concurso]], List[int]]],
        janela_treino: int = 50,
        passo: int = 1
    ) -> Dict[str, List[ResultadoSimulacao]]:
        """Executa backtest para múltiplas estratégias simultaneamente."""
        return {
            nome: self.backtest_estrategia(gerador, janela_treino, 1, passo)
            for nome, gerador in geradores.items()
        }

    # ═══════════════════════════════════════════════════════════
    # SIMULAÇÃO MONTE CARLO
    # ═══════════════════════════════════════════════════════════

    def monte_carlo_aleatorio(
        self,
        n_simulacoes: int = 10000,
        n_dezenas: int = None,
        seed: int = None
    ) -> RelatorioSimulacao:
        """
        Simulação Monte Carlo com jogos completamente aleatórios.
        Compara com o histórico real.
        """
        if seed is not None:
            np.random.seed(seed)

        n_dezenas = n_dezenas or self.loteria.dezenas_sorteadas
        resultados = []

        for c in self.concursos:
            jogo = set(np.random.choice(
                range(1, self.loteria.dezenas_totais + 1),
                size=n_dezenas,
                replace=False
            ))
            acertos = len(jogo & set(c.dezenas))
            resultados.append(ResultadoSimulacao(
                concurso_numero=c.numero,
                dezenas_sorteadas=c.dezenas,
                dezenas_apostadas=sorted(jogo),
                acertos=acertos
            ))

        return self._gerar_relatorio("Monte Carlo Aleatório", resultados)

    def monte_carlo_estrategia(
        self,
        gerador_jogos: Callable[[], List[int]],
        n_simulacoes: int = 1000,
        nome: str = "Estratégia"
    ) -> RelatorioSimulacao:
        """
        Simulação Monte Carlo usando uma estratégia específica.
        """
        resultados = []

        for c in self.concursos[:n_simulacoes]:
            jogo = set(gerador_jogos())
            acertos = len(jogo & set(c.dezenas))
            resultados.append(ResultadoSimulacao(
                concurso_numero=c.numero,
                dezenas_sorteadas=c.dezenas,
                dezenas_apostadas=sorted(jogo),
                acertos=acertos
            ))

        return self._gerar_relatorio(nome, resultados)

    # ═══════════════════════════════════════════════════════════
    # COMPARAÇÃO ENTRE ESTRATÉGIAS
    # ═══════════════════════════════════════════════════════════

    def comparar_estrategias(
        self,
        estrategias: Dict[str, Callable[[List[Concurso]], List[int]]],
        janela_treino: int = 50
    ) -> Dict[str, RelatorioSimulacao]:
        """Compara múltiplas estratégias via backtest."""
        resultados = self.backtest_multiplo(estrategias, janela_treino)
        return {
            nome: self._gerar_relatorio(nome, res)
            for nome, res in resultados.items()
        }

    def ranking_estrategias(
        self,
        relatorios: Dict[str, RelatorioSimulacao],
        metrica: str = "media_acertos"
    ) -> List[Tuple[str, float]]:
        """Ordena estratégias por uma métrica específica."""
        return sorted(
            [(nome, getattr(rep, metrica)) for nome, rep in relatorios.items()],
            key=lambda x: x[1],
            reverse=True
        )

    # ═══════════════════════════════════════════════════════════
    # ESTATÍSTICAS AGREGADAS
    # ═══════════════════════════════════════════════════════════

    def _gerar_relatorio(self, nome: str, resultados: List[ResultadoSimulacao]) -> RelatorioSimulacao:
        """Gera relatório agregado a partir de resultados individuais."""
        if not resultados:
            return RelatorioSimulacao(
                estrategia_nome=nome,
                total_simulacoes=0,
                acertos_distribuicao={},
                acertos_percentual={},
                media_acertos=0.0,
                mediana_acertos=0.0,
                desvio_padrao=0.0,
                max_acertos=0,
                min_acertos=0,
                roi_estimado=0.0
            )

        acertos = [r.acertos for r in resultados]
        distrib = dict(Counter(acertos))
        total = len(acertos)

        percentual = {k: round(v / total * 100, 2) for k, v in distrib.items()}

        return RelatorioSimulacao(
            estrategia_nome=nome,
            total_simulacoes=total,
            acertos_distribuicao=distrib,
            acertos_percentual=percentual,
            media_acertos=round(np.mean(acertos), 2),
            mediana_acertos=round(np.median(acertos), 2),
            desvio_padrao=round(np.std(acertos), 2),
            max_acertos=max(acertos),
            min_acertos=min(acertos),
            roi_estimado=0.0,  # Calculado externamente com tabela de prêmios
            detalhes=resultados
        )

    def estatisticas_agregadas(self, relatorios: Dict[str, RelatorioSimulacao]) -> Dict:
        """Estatísticas agregadas de múltiplas simulações."""
        return {
            "total_estrategias": len(relatorios),
            "melhor_media": max((r.media_acertos for r in relatorios.values()), default=0),
            "pior_media": min((r.media_acertos for r in relatorios.values()), default=0),
            "melhor_max_acertos": max((r.max_acertos for r in relatorios.values()), default=0),
            "estrategias": {
                nome: {
                    "media_acertos": r.media_acertos,
                    "max_acertos": r.max_acertos,
                    "desvio_padrao": r.desvio_padrao,
                    "distribuicao": r.acertos_percentual
                }
                for nome, r in relatorios.items()
            }
        }

    # ═══════════════════════════════════════════════════════════
    # GRÁFICOS E VISUALIZAÇÕES (dados para gráficos)
    # ═══════════════════════════════════════════════════════════

    def dados_grafico_distribuicao(self, relatorio: RelatorioSimulacao) -> Dict:
        """Dados para gráfico de distribuição de acertos."""
        return {
            "labels": list(relatorio.acertos_distribuicao.keys()),
            "frequencias": list(relatorio.acertos_distribuicao.values()),
            "percentuais": list(relatorio.acertos_percentual.values()),
            "media": relatorio.media_acertos,
            "desvio": relatorio.desvio_padrao
        }

    def dados_grafico_comparativo(self, relatorios: Dict[str, RelatorioSimulacao]) -> Dict:
        """Dados para gráfico comparativo entre estratégias."""
        return {
            "estrategias": list(relatorios.keys()),
            "medias": [r.media_acertos for r in relatorios.values()],
            "maximos": [r.max_acertos for r in relatorios.values()],
            "desvios": [r.desvio_padrao for r in relatorios.values()],
            "distribuicoes": {
                nome: r.acertos_percentual
                for nome, r in relatorios.items()
            }
        }
