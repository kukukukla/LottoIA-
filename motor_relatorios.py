
"""
motor_relatorios.py - Motor de Relatórios e Exportação
"""
from typing import List, Dict
from datetime import datetime
import json
from models import Concurso, LoteriaTipo, EstrategiaConfig


class MotorRelatorios:
    """
    Motor de geração de relatórios e exportação de dados.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIOS JSON
    # ═══════════════════════════════════════════════════════════

    def relatorio_json(self, motor_estatistico) -> str:
        """Gera relatório completo em JSON."""
        relatorio = motor_estatistico.relatorio_completo()
        relatorio["gerado_em"] = datetime.now().isoformat()
        relatorio["versao"] = "2.0"
        return json.dumps(relatorio, indent=2, ensure_ascii=False)

    def exportar_concursos(self) -> List[Dict]:
        """Exporta todos os concursos."""
        return [c.to_dict() for c in self.concursos]

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIOS CSV (dados para exportação)
    # ═══════════════════════════════════════════════════════════

    def dados_csv_concursos(self) -> List[Dict]:
        """Dados formatados para CSV."""
        return [
            {
                "concurso": c.numero,
                "data": c.data.isoformat(),
                "dezenas": " ".join(map(str, c.dezenas)),
                "soma": c.soma,
                "media": c.media,
                "pares": len(c.pares),
                "impares": len(c.impares),
                "baixos": len(c.baixos),
                "altos": len(c.altos),
                "sequencias": len(c.sequencias_consecutivas)
            }
            for c in self.concursos
        ]

    def dados_csv_frequencia(self, motor_estatistico) -> List[Dict]:
        """Dados de frequência para CSV."""
        metricas = motor_estatistico.metricas_completas_por_dezena()
        return [
            {
                "dezena": d,
                "frequencia_absoluta": m.frequencia_absoluta,
                "frequencia_relativa": m.frequencia_relativa,
                "atraso_atual": m.atraso_atual,
                "atraso_medio": m.atraso_medio,
                "atraso_maximo": m.atraso_maximo,
                "tendencia": m.tendencia
            }
            for d, m in metricas.items()
        ]

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIO EXECUTIVO
    # ═══════════════════════════════════════════════════════════

    def relatorio_executivo(self, motor_estatistico) -> Dict:
        """Relatório executivo resumido."""
        est = motor_estatistico
        freq = est.frequencia_absoluta()
        top5 = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
        bottom5 = sorted(freq.items(), key=lambda x: x[1])[:5]
        atraso = est.atraso_atual()
        mais_atrasadas = sorted(atraso.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "titulo": f"Relatório Executivo - {self.loteria.value.upper()}",
            "periodo": {
                "primeiro_concurso": self.concursos[0].numero,
                "ultimo_concurso": self.concursos[-1].numero,
                "total_concursos": len(self.concursos)
            },
            "destaques": {
                "dezenas_mais_frequentes": [{"dezena": d, "freq": f} for d, f in top5],
                "dezenas_menos_frequentes": [{"dezena": d, "freq": f} for d, f in bottom5],
                "dezenas_mais_atrasadas": [{"dezena": d, "atraso": a} for d, a in mais_atrasadas]
            },
            "estatisticas_gerais": est.estatisticas_soma(),
            "recomendacao": "Este relatório é para fins de análise estatística. Não garante previsão de resultados."
        }

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIO DE ESTRATÉGIAS
    # ═══════════════════════════════════════════════════════════

    def relatorio_estrategias(self, estrategias: List[EstrategiaConfig]) -> Dict:
        """Relatório das estratégias salvas."""
        return {
            "total_estrategias": len(estrategias),
            "estrategias": [
                {
                    "id": e.id,
                    "nome": e.nome,
                    "loteria": e.loteria.value,
                    "dezenas": e.quantidade_dezenas,
                    "n_filtros": len(e.filtros),
                    "filtros": list(e.filtros.keys()),
                    "created_at": e.created_at.isoformat()
                }
                for e in estrategias
            ]
        }

    # ═══════════════════════════════════════════════════════════
    # RELATÓRIO DE SIMULAÇÃO
    # ═══════════════════════════════════════════════════════════

    def relatorio_simulacao(self, relatorio_sim) -> Dict:
        """Formata relatório de simulação."""
        return {
            "estrategia": relatorio_sim.estrategia_nome,
            "total_simulacoes": relatorio_sim.total_simulacoes,
            "resultados": {
                "media_acertos": relatorio_sim.media_acertos,
                "mediana_acertos": relatorio_sim.mediana_acertos,
                "desvio_padrao": relatorio_sim.desvio_padrao,
                "max_acertos": relatorio_sim.max_acertos,
                "min_acertos": relatorio_sim.min_acertos
            },
            "distribuicao_acertos": relatorio_sim.acertos_percentual,
            "interpretacao": "Resultados dentro do esperado para distribuição aleatória"
                            if abs(relatorio_sim.media_acertos - (self.loteria.dezenas_sorteadas * self.loteria.dezenas_sorteadas / self.loteria.dezenas_totais)) < 1
                            else "Verificar possível viés"
        }
