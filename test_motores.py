"""
Testes automatizados do Motor Estatístico de Loterias
"""
import pytest
import random
import numpy as np
from datetime import date

from core.models import Concurso, LoteriaTipo, EstrategiaConfig
from core.main_engine import MotorPrincipal
from core.motor_estatistico import MotorEstatistico
from core.motor_matematico import MotorMatematico
from core.motor_score import MotorScore


def gerar_concursos(n=50):
    random.seed(42)
    concursos = []
    for i in range(1, n + 1):
        dezenas = sorted(random.sample(range(1, 26), 15))
        concursos.append(Concurso(
            numero=i,
            data=date(2000, 1, 1),
            dezenas=dezenas,
            loteria=LoteriaTipo.LOTOFACIL
        ))
    return concursos


class TestModels:
    def test_concurso_criacao(self):
        c = Concurso(numero=1, data=date(2000, 1, 1), dezenas=[1, 2, 3], loteria=LoteriaTipo.LOTOFACIL)
        assert c.numero == 1
        assert len(c.dezenas) == 3
        assert c.soma == 6

    def test_loteria_propriedades(self):
        assert LoteriaTipo.LOTOFACIL.dezenas_totais == 25
        assert LoteriaTipo.LOTOFACIL.dezenas_sorteadas == 15
        assert LoteriaTipo.MEGA_SENA.dezenas_totais == 60


class TestMotorEstatistico:
    def test_frequencia_absoluta(self):
        concursos = gerar_concursos(50)
        est = MotorEstatistico(concursos)
        freq = est.frequencia_absoluta()
        assert len(freq) > 0
        assert all(isinstance(v, int) for v in freq.values())

    def test_atraso_atual(self):
        concursos = gerar_concursos(50)
        est = MotorEstatistico(concursos)
        atraso = est.atraso_atual()
        assert len(atraso) == 25
        assert all(isinstance(v, int) for v in atraso.values())
        assert all(v >= 0 for v in atraso.values())

    def test_estatisticas_soma(self):
        concursos = gerar_concursos(50)
        est = MotorEstatistico(concursos)
        stats = est.estatisticas_soma()
        assert 'media' in stats
        assert 'desvio_padrao' in stats
        assert stats['media'] > 0


class TestMotorMatematico:
    def test_combinacoes(self):
        mat = MotorMatematico(LoteriaTipo.LOTOFACIL)
        assert mat.combinacoes_totais() == 3_268_760

    def test_probabilidade(self):
        mat = MotorMatematico(LoteriaTipo.LOTOFACIL)
        prob = mat.probabilidade_acerto(15, 15)
        assert 0 <= prob <= 1
        assert prob > 0

    def test_fibonacci(self):
        mat = MotorMatematico(LoteriaTipo.LOTOFACIL)
        fib = mat.sequencia_fibonacci()
        assert 1 in fib
        assert 2 in fib
        assert 21 in fib


class TestMotorScore:
    def test_calcular_scores(self):
        concursos = gerar_concursos(50)
        score = MotorScore(concursos)
        scores = score.calcular_scores()
        assert len(scores) == 25
        assert all(0 <= s.score_total <= 1 for s in scores.values())

    def test_top_dezenas(self):
        concursos = gerar_concursos(50)
        score = MotorScore(concursos)
        top = score.top_dezenas(5)
        assert len(top) == 5
        assert top[0].score_total >= top[-1].score_total

    def test_matriz_correlacao_calculada_uma_vez(self, monkeypatch):
        score = MotorScore(gerar_concursos(10))
        original = score.estatistico.matriz_correlacao
        chamadas = 0

        def contar_chamadas():
            nonlocal chamadas
            chamadas += 1
            return original()

        monkeypatch.setattr(score.estatistico, "matriz_correlacao", contar_chamadas)
        score.calcular_scores()
        assert chamadas == 1


class TestMotorPrincipal:
    def test_resumo(self):
        concursos = gerar_concursos(50)
        motor = MotorPrincipal(concursos)
        resumo = motor.resumo()
        assert resumo['loteria'] == 'lotofacil'
        assert resumo['total_concursos'] == 50

    def test_gerar_jogos(self):
        concursos = gerar_concursos(50)
        motor = MotorPrincipal(concursos)
        jogos = motor.gerar_jogos("aleatorio", 15, 3)
        assert len(jogos) == 3
        assert all(len(j['dezenas']) == 15 for j in jogos)

    def test_estrategia_crud(self):
        concursos = gerar_concursos(50)
        motor = MotorPrincipal(concursos)
        config = EstrategiaConfig(
            nome="Teste",
            loteria=LoteriaTipo.LOTOFACIL,
            quantidade_dezenas=15,
            filtros={"frequencia_historica": {"max_rank": 20}}
        )
        id_estr = motor.criar_estrategia(config)
        assert id_estr is not None
        assert motor.estrategias.obter_estrategia(id_estr) is not None


class TestMotorSimulacoes:
    def test_monte_carlo_respeita_quantidade_solicitada(self):
        motor = MotorPrincipal(gerar_concursos(5))
        relatorio = motor.simulacoes.monte_carlo_aleatorio(
            n_simulacoes=12,
            n_dezenas=15,
            seed=42,
        )
        assert relatorio.total_simulacoes == 12
        assert len(relatorio.detalhes) == 12

    def test_monte_carlo_rejeita_quantidade_invalida(self):
        motor = MotorPrincipal(gerar_concursos(5))
        with pytest.raises(ValueError, match="inteiro positivo"):
            motor.simulacoes.monte_carlo_aleatorio(n_simulacoes=0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
