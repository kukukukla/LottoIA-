import os
from datetime import date

os.environ.setdefault("SESSION_SECRET", "test-secret-for-suite")
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password"

import pytest
from fastapi.testclient import TestClient

import app as app_module
from caixa_client import CaixaAPIError
from core.models import Concurso, LoteriaTipo


class FakeCaixaClient:
    def obter_historico(self, loteria, quantidade=30, atualizar=False):
        if quantidade < 1:
            raise ValueError("quantidade inválida")
        concursos = []
        for numero in range(100, 100 + quantidade):
            dezenas = list(range(1, loteria.dezenas_sorteadas + 1))
            concursos.append(
                Concurso(
                    numero=numero,
                    data=date(2026, 10, 1),
                    dezenas=dezenas,
                    loteria=loteria,
                )
            )
        return concursos, {
            "fonte": "CAIXA",
            "url_fonte": "https://servicebus2.caixa.gov.br/portaldeloterias/api",
            "atualizado_em": "2026-10-19T00:00:00+00:00",
            "cache": False,
            "cache_desatualizado": False,
            "aviso": None,
        }


def authenticated_client(monkeypatch, caixaclient=None):
    app_module._FAILED.clear()
    monkeypatch.setattr(app_module, "CAIXA_CLIENT", caixaclient or FakeCaixaClient())
    client = TestClient(app_module.app)
    response = client.post(
        "/login",
        data={"username": "admin", "password": "test-password"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return client


def test_api_resultados_lista_resultados_oficiais_e_metadados(monkeypatch):
    client = authenticated_client(monkeypatch)
    response = client.get("/api/resultados?loteria=lotofacil&quantidade=3")
    assert response.status_code == 200
    body = response.json()
    assert body["loteria"] == "lotofacil"
    assert body["total_concursos"] == 3
    assert body["ultimo_concurso"] == 102
    assert body["fonte_dados"]["fonte"] == "CAIXA"
    assert [r["concurso"] for r in body["resultados"]] == [100, 101, 102]


def test_api_analise_usa_historico_real_e_informa_concurso(monkeypatch):
    client = authenticated_client(monkeypatch)
    response = client.get("/api/analise?loteria=mega_sena&quantidade=20")
    assert response.status_code == 200
    body = response.json()
    assert body["loteria"] == "mega_sena"
    assert body["total_concursos"] == 20
    assert body["ultimo_concurso"] == 119
    assert len(body["frequencia"]) > 0
    assert len(body["score"]) == 10
    assert body["fonte_dados"]["fonte"] == "CAIXA"


def test_geracao_usa_modalidade_e_dezenas_corretas(monkeypatch):
    client = authenticated_client(monkeypatch)
    response = client.get(
        "/api/gerar?metodo=aleatorio&loteria=mega_sena&dezenas=6&jogos=3&quantidade=5"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["loteria"] == "mega_sena"
    assert body["dezenas"] == 6
    assert len(body["jogos"]) == 3
    assert all(len(jogo) == 6 and len(set(jogo)) == 6 for jogo in body["jogos"])
    assert all(1 <= dezena <= 60 for jogo in body["jogos"] for dezena in jogo)


def test_geracao_por_score_invoca_motor_com_historico_carregado(monkeypatch):
    client = authenticated_client(monkeypatch)
    response = client.get(
        "/api/gerar?metodo=score&loteria=lotofacil&dezenas=15&jogos=2&quantidade=30"
    )
    assert response.status_code == 200
    assert len(response.json()["jogos"]) == 2
    assert all(len(jogo) == 15 for jogo in response.json()["jogos"])


@pytest.mark.parametrize(
    "loteria,dezenas,total,sorteadas",
    [
        ("lotofacil", 15, 25, 15),
        ("mega_sena", 6, 60, 6),
        ("lotomania", 50, 100, 20),
    ],
)
def test_geracao_respeita_regras_por_modalidade(monkeypatch, loteria, dezenas, total, sorteadas):
    client = authenticated_client(monkeypatch)
    response = client.get(
        f"/api/gerar?metodo=aleatorio&loteria={loteria}&dezenas={dezenas}&jogos=2&quantidade=5"
    )
    assert response.status_code == 200
    jogos = response.json()["jogos"]
    assert len(jogos) == 2
    assert all(len(jogo) == dezenas for jogo in jogos)
    assert all(len(set(jogo)) == dezenas for jogo in jogos)
    assert all(1 <= n <= total for jogo in jogos for n in jogo)
    assert response.json()["loteria"] == loteria
    assert sorteadas == LoteriaTipo(loteria).dezenas_sorteadas


def test_geracao_rejeita_dezenas_incompatíveis_com_modalidade(monkeypatch):
    client = authenticated_client(monkeypatch)
    response = client.get("/api/gerar?loteria=mega_sena&dezenas=5")
    assert response.status_code == 422


def test_simulacao_e_testes_estatisticos_aceitam_dados_reais(monkeypatch):
    client = authenticated_client(monkeypatch)
    sim = client.get("/api/simular?n=7&loteria=mega_sena&quantidade=10")
    assert sim.status_code == 200
    assert sim.json()["total"] == 7
    assert sim.json()["loteria"] == "mega_sena"
    stats = client.get("/api/testes?loteria=lotofacil&quantidade=30")
    assert stats.status_code == 200
    assert stats.json()["total_concursos"] == 30
    assert "chi_quadrado" in stats.json()
    assert stats.json()["fonte_dados"]["fonte"] == "CAIXA"


def test_demo_e_explicito_e_nao_chama_fonte_caixa(monkeypatch):
    class MustNotCall:
        def obter_historico(self, *args, **kwargs):
            raise AssertionError("fonte CAIXA não deve ser chamada em fonte=demo")
    client = authenticated_client(monkeypatch, MustNotCall())
    response = client.get("/api/resultados?fonte=demo&quantidade=2")
    assert response.status_code == 200
    assert response.json()["fonte_dados"]["fonte"] == "sintético/demo"
    assert "artificiais" in response.json()["fonte_dados"]["aviso"]


def test_falha_da_caixa_e_exposta_com_503_sem_substituir_por_demo(monkeypatch):
    class Offline:
        def obter_historico(self, *args, **kwargs):
            raise CaixaAPIError("sem conexão")
    client = authenticated_client(monkeypatch, Offline())
    response = client.get("/api/analise")
    assert response.status_code == 503
    assert "indisponíveis" in response.json()["detail"]


def test_rota_de_resultados_exige_autenticacao(monkeypatch):
    monkeypatch.setattr(app_module, "CAIXA_CLIENT", FakeCaixaClient())
    app_module._FAILED.clear()
    response = TestClient(app_module.app).get("/api/resultados")
    assert response.status_code == 401


def test_dashboard_apresenta_resultados_oficiais_e_modalidades_habilitadas(monkeypatch):
    client = authenticated_client(monkeypatch)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Resultados oficiais recentes" in response.text
    assert 'value="mega_sena"' in response.text
    assert 'value="lotofacil"' in response.text
    assert 'value="lotomania"' in response.text
    script = client.get("/static/js/dashboard.js")
    assert script.status_code == 200
    assert "atualizar=true" in script.text
