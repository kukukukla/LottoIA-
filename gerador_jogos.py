
"""
gerador_jogos.py - Gerador de Jogos Completo
"""
from typing import List, Dict, Optional, Set
import numpy as np
from models import Concurso, LoteriaTipo, EstrategiaConfig, JogoGerado
from motor_estatistico import MotorEstatistico
from motor_matematico import MotorMatematico
from motor_estrategias import MotorEstrategias
from motor_score import MotorScore
from motor_desdobramentos import MotorDesdobramentos


class GeradorJogos:
    """
    Gerador de jogos unificado.
    Integra todos os motores para gerar combinações conforme critérios.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None
        self.estatistico = MotorEstatistico(self.concursos)
        self.matematico = MotorMatematico(self.loteria) if self.loteria else None
        self.estrategias = MotorEstrategias(self.concursos)
        self.score = MotorScore(self.concursos)
        self.desdobramentos = MotorDesdobramentos(self.loteria) if self.loteria else None

    # ═══════════════════════════════════════════════════════════
    # GERAÇÃO POR TIPO
    # ═══════════════════════════════════════════════════════════

    def gerar_aleatorio(self, n_dezenas: int, n_jogos: int = 1, seed: int = None) -> List[Dict]:
        """Gera jogos completamente aleatórios."""
        if seed is not None:
            np.random.seed(seed)

        jogos = []
        for _ in range(n_jogos):
            dezenas = sorted(np.random.choice(
                range(1, self.loteria.dezenas_totais + 1),
                size=n_dezenas,
                replace=False
            ).tolist())
            jogos.append({
                "dezenas": dezenas,
                "tipo": "aleatorio",
                "score_medio": None,
                "criterios": {"metodo": "aleatorio_uniforme"}
            })
        return jogos

    def gerar_por_score(
        self,
        n_dezenas: int,
        n_jogos: int = 1,
        pesos: Dict[str, float] = None,
        top_n: int = 25
    ) -> List[Dict]:
        """Gera jogos baseados nos scores das dezenas."""
        jogos = []
        scores = self.score.calcular_scores(pesos)

        for _ in range(n_jogos):
            dezenas = self.score.gerar_jogo_por_score(n_dezenas, pesos, top_n)
            score_medio = np.mean([scores[d].score_total for d in dezenas if d in scores])

            jogos.append({
                "dezenas": dezenas,
                "tipo": "score",
                "score_medio": round(score_medio, 4),
                "criterios": {
                    "metodo": "pontuacao_ponderada",
                    "pesos": pesos or MotorScore.PESOS_PADRAO,
                    "top_candidatas": top_n
                }
            })
        return jogos

    def gerar_por_estrategia(self, estrategia_id: str, n_jogos: int = 1) -> List[Dict]:
        """Gera jogos usando uma estratégia salva."""
        return self.estrategias.aplicar_estrategia(estrategia_id, n_jogos)

    def gerar_por_frequencia(
        self,
        n_dezenas: int,
        n_jogos: int = 1,
        tipo: str = "mais_frequentes",
        janela: int = None
    ) -> List[Dict]:
        """
        Gera jogos baseados em frequência.
        tipo: "mais_frequentes", "menos_frequentes", "misturado"
        """
        if janela:
            freq = self.estatistico.frequencia_por_janela(janela)
        else:
            freq = self.estatistico.frequencia_absoluta()

        ranking = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        jogos = []

        for _ in range(n_jogos):
            if tipo == "mais_frequentes":
                dezenas = [d for d, _ in ranking[:n_dezenas]]
            elif tipo == "menos_frequentes":
                dezenas = [d for d, _ in ranking[-n_dezenas:]]
            elif tipo == "misturado":
                metade = n_dezenas // 2
                top = [d for d, _ in ranking[:metade]]
                bottom = [d for d, _ in ranking[-(n_dezenas - metade):]]
                dezenas = sorted(top + bottom)
            else:
                dezenas = [d for d, _ in ranking[:n_dezenas]]

            jogos.append({
                "dezenas": dezenas,
                "tipo": f"frequencia_{tipo}",
                "criterios": {
                    "metodo": f"frequencia_{tipo}",
                    "janela": janela or "total"
                }
            })

        return jogos

    def gerar_por_atraso(
        self,
        n_dezenas: int,
        n_jogos: int = 1,
        criterio: str = "acima_media"
    ) -> List[Dict]:
        """
        Gera jogos baseados em atraso.
        criterio: "acima_media", "maximo", "proporcional"
        """
        atraso_atual = self.estatistico.atraso_atual()
        atraso_medio = self.estatistico.atraso_medio()

        if criterio == "acima_media":
            candidatas = [
                d for d in range(1, self.loteria.dezenas_totais + 1)
                if atraso_atual.get(d, 0) > atraso_medio.get(d, 0)
            ]
        elif criterio == "maximo":
            max_atraso = max(atraso_atual.values()) if atraso_atual else 0
            candidatas = [
                d for d, a in atraso_atual.items()
                if a >= max_atraso * 0.8
            ]
        else:
            candidatas = list(range(1, self.loteria.dezenas_totais + 1))

        jogos = []
        for _ in range(n_jogos):
            if len(candidatas) >= n_dezenas:
                dezenas = sorted(np.random.choice(candidatas, size=n_dezenas, replace=False).tolist())
            else:
                dezenas = sorted(candidatas + list(np.random.choice(
                    [d for d in range(1, self.loteria.dezenas_totais + 1) if d not in candidatas],
                    size=n_dezenas - len(candidatas),
                    replace=False
                )))

            jogos.append({
                "dezenas": dezenas,
                "tipo": f"atraso_{criterio}",
                "criterios": {
                    "metodo": f"atraso_{criterio}",
                    "candidatas": len(candidatas)
                }
            })

        return jogos

    def gerar_balanceado(
        self,
        n_dezenas: int,
        n_jogos: int = 1,
        equilibrio: Dict = None
    ) -> List[Dict]:
        """
        Gera jogos com balanceamento controlado.
        equilibrio: {"pares": int, "impares": int, "baixos": int, "altos": int}
        """
        meio = self.loteria.dezenas_totais // 2
        pares = list(range(2, self.loteria.dezenas_totais + 1, 2))
        impares = list(range(1, self.loteria.dezenas_totais + 1, 2))
        baixos = list(range(1, meio + 1))
        altos = list(range(meio + 1, self.loteria.dezenas_totais + 1))

        jogos = []
        for _ in range(n_jogos):
            # Determina proporções
            n_pares = equilibrio.get("pares", n_dezenas // 2) if equilibrio else n_dezenas // 2
            n_impares = n_dezenas - n_pares
            n_baixos = equilibrio.get("baixos", n_dezenas // 2) if equilibrio else n_dezenas // 2
            n_altos = n_dezenas - n_baixos

            # Seleciona pares/ímpares
            sel_pares = set(np.random.choice(pares, size=min(n_pares, len(pares)), replace=False))
            sel_impares = set(np.random.choice(impares, size=min(n_impares, len(impares)), replace=False))

            dezenas = sorted(sel_pares | sel_impares)

            # Ajusta se necessário
            while len(dezenas) < n_dezenas:
                restantes = [d for d in range(1, self.loteria.dezenas_totais + 1) if d not in dezenas]
                if restantes:
                    dezenas.append(np.random.choice(restantes))
                    dezenas = sorted(dezenas)
                else:
                    break

            while len(dezenas) > n_dezenas:
                dezenas.pop(np.random.randint(0, len(dezenas)))
                dezenas = sorted(dezenas)

            jogos.append({
                "dezenas": dezenas,
                "tipo": "balanceado",
                "criterios": {
                    "metodo": "balanceamento_controlado",
                    "pares": len([d for d in dezenas if d % 2 == 0]),
                    "impares": len([d for d in dezenas if d % 2 != 0]),
                    "baixos": len([d for d in dezenas if d <= meio]),
                    "altos": len([d for d in dezenas if d > meio])
                }
            })

        return jogos

    def gerar_com_fibonacci(self, n_dezenas: int, n_jogos: int = 1, n_fib: int = 3) -> List[Dict]:
        """Gera jogos incluindo dezenas de Fibonacci."""
        jogos = []
        for _ in range(n_jogos):
            jogo = self.matematico.jogo_com_fibonacci(n_dezenas, n_fib)
            jogos.append({
                "dezenas": sorted(jogo),
                "tipo": "fibonacci",
                "criterios": {
                    "metodo": "criterio_fibonacci",
                    "dezenas_fibonacci": n_fib,
                    "sequencia_fib": self.matematico.sequencia_fibonacci()
                }
            })
        return jogos

    # ═══════════════════════════════════════════════════════════
    # DESDOBRAMENTOS
    # ═══════════════════════════════════════════════════════════

    def gerar_desdobramento(
        self,
        dezenas_base: List[int],
        n_por_jogo: int,
        tipo: str = "simples",
        max_jogos: int = 100
    ) -> List[Dict]:
        """
        Gera desdobramento de dezenas base.
        tipo: "simples", "aleatorio", "garantia"
        """
        if tipo == "simples":
            jogos = self.desdobramentos.desdobramento_simples(dezenas_base, n_por_jogo, max_jogos)
        elif tipo == "aleatorio":
            jogos = self.desdobramentos.desdobramento_aleatorio(dezenas_base, n_por_jogo, max_jogos)
        elif tipo == "garantia":
            jogos = self.desdobramentos.desdobramento_por_garantia(dezenas_base, n_por_jogo, 3, max_jogos)
        else:
            jogos = []

        return [{
            "dezenas": sorted(j),
            "tipo": f"desdobramento_{tipo}",
            "criterios": {
                "metodo": f"desdobramento_{tipo}",
                "dezenas_base": dezenas_base,
                "n_por_jogo": n_por_jogo
            }
        } for j in jogos]

    # ═══════════════════════════════════════════════════════════
    # MÉTODO UNIFICADO
    # ═══════════════════════════════════════════════════════════

    def gerar(
        self,
        metodo: str,
        n_dezenas: int,
        n_jogos: int = 1,
        params: Dict = None
    ) -> List[Dict]:
        """
        Método unificado de geração de jogos.
        metodo: "aleatorio", "score", "frequencia", "atraso", "balanceado",
                "fibonacci", "estrategia", "desdobramento"
        """
        params = params or {}

        geradores = {
            "aleatorio": lambda: self.gerar_aleatorio(n_dezenas, n_jogos, params.get("seed")),
            "score": lambda: self.gerar_por_score(n_dezenas, n_jogos, params.get("pesos"), params.get("top_n", 25)),
            "frequencia": lambda: self.gerar_por_frequencia(n_dezenas, n_jogos, params.get("tipo", "mais_frequentes"), params.get("janela")),
            "atraso": lambda: self.gerar_por_atraso(n_dezenas, n_jogos, params.get("criterio", "acima_media")),
            "balanceado": lambda: self.gerar_balanceado(n_dezenas, n_jogos, params.get("equilibrio")),
            "fibonacci": lambda: self.gerar_com_fibonacci(n_dezenas, n_jogos, params.get("n_fib", 3)),
            "estrategia": lambda: self.gerar_por_estrategia(params.get("estrategia_id"), n_jogos),
            "desdobramento": lambda: self.gerar_desdobramento(
                params.get("dezenas_base", list(range(1, self.loteria.dezenas_totais + 1))),
                n_dezenas,
                params.get("tipo_desdobramento", "simples"),
                params.get("max_jogos", 100)
            ),
        }

        if metodo not in geradores:
            raise ValueError(f"Método '{metodo}' não reconhecido. Use: {list(geradores.keys())}")

        return geradores[metodo]()
