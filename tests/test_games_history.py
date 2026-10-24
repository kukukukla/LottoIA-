import re
from datetime import date

from fastapi.testclient import TestClient
import pytest

import app as app_module
from caixa_client import CaixaAPIError
from core.models import Concurso, LoteriaTipo
from games_store import GameStore


class FakeCaixaClient:
    def obter_historico(self, loteria, quantidade=30, atualizar=False):
        concursos = [
            Concurso(
                numero=500 + offset,
                data=date(2026, 10, 1 + offset),
                dezenas=list(range(1, loteria.dezenas_sorteadas + 1)),
                loteria=loteria,
            )
            for offset in range(quantidade)
        ]
        return concursos, {
            "fonte": "CAIXA",
            "url_fonte": "https://servicebus2.caixa.gov.br/portaldeloterias/api",
            "atualizado_em": "2026-10-24T00:00:00+00:00",
            "cache": False,
            "cache_desatualizado": False,
            "aviso": None,
        }


def client_with_store(monkeypatch, tmp_path):
    app_module._FAILED.clear()
    monkeypatch.setattr(app_module, "GAME_STORE", GameStore(tmp_path / "games.sqlite3"))
    monkeypatch.setattr(app_module, "CAIXA_CLIENT", FakeCaixaClient())
    client = TestClient(app_module.app)
    response = client.post(
        "/login",
        data={"username": "admin", "password": "test-password"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    html = client.get("/dashboard").text
    token = re.search(r'<meta name="csrf-token" content="([^"]+)"', html).group(1)
    return client, token


def test_cria_lote_nomeado_persiste_jogos_e_gera_arquivo_txt(monkeypatch, tmp_path):
    client, token = client_with_store(monkeypatch, tmp_path)
    response = client.post(
        "/api/jogos",
        headers={"X-CSRF-Token": token},
        json={
            "nome": "Lote outubro",
            "loteria": "mega_sena",
            "metodo": "aleatorio",
            "dezenas": 6,
            "jogos": 3,
            "fonte": "caixa",
            "historico": 4,
        },
    )
    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["name"] == "Lote outubro"
    assert batch["lottery"] == "mega_sena"
    assert batch["game_count"] == 3
    assert len(batch["games"]) == 3
    assert all(len(game) == 6 for game in batch["games"])
    assert batch["reference_draw"] == 503

    history = client.get("/api/jogos?limite=10")
    assert history.status_code == 200
    assert [item["id"] for item in history.json()["lotes"]] == [batch["id"]]

    text = client.get(f"/api/jogos/{batch['id']}/texto")
    assert text.status_code == 200
    assert "attachment; filename=" in text.headers["content-disposition"]
    assert "Nome: Lote outubro" in text.text
    assert "Quantidade de jogos: 3" in text.text
    assert "Jogo 1:" in text.text
    assert "não representa previsão" in text.text


def test_csrf_obrigatorio_para_gerar_e_salvar(monkeypatch, tmp_path):
    client, _ = client_with_store(monkeypatch, tmp_path)
    response = client.post(
        "/api/jogos",
        json={"nome": "sem csrf", "loteria": "mega_sena", "fonte": "demo"},
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.parametrize(
    ("lottery", "number_count"),
    [("lotofacil", 15), ("mega_sena", 6), ("lotomania", 50)],
)
def test_geracao_persistida_respeita_modalidades_e_quantidade_de_dezenas(
    monkeypatch, tmp_path, lottery, number_count
):
    client, token = client_with_store(monkeypatch, tmp_path)
    response = client.post(
        "/api/jogos",
        headers={"X-CSRF-Token": token},
        json={
            "nome": f"Teste {lottery}",
            "loteria": lottery,
            "metodo": "aleatorio",
            "dezenas": number_count,
            "jogos": 2,
            "fonte": "caixa",
            "historico": 2,
        },
    )
    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["game_count"] == 2
    assert all(len(game) == number_count for game in batch["games"])
    assert all(len(set(game)) == number_count for game in batch["games"])


def test_comparacao_marca_ultimo_concurso_e_acertos_por_jogo(monkeypatch, tmp_path):
    client, token = client_with_store(monkeypatch, tmp_path)
    response = client.post(
        "/api/jogos",
        headers={"X-CSRF-Token": token},
        json={
            "nome": "Espelho teste",
            "loteria": "lotofacil",
            "metodo": "aleatorio",
            "dezenas": 15,
            "jogos": 2,
            "fonte": "demo",
            "historico": 3,
        },
    )
    assert response.status_code == 201, response.text
    batch = response.json()

    comparison = client.get(f"/api/jogos/{batch['id']}/comparar?quantidade=3")
    assert comparison.status_code == 200, comparison.text
    body = comparison.json()
    assert body["concurso_mais_recente"] == 502
    assert body["fonte_dados"]["fonte"] == "CAIXA"
    assert len(body["resultados_comparados"]) == 3
    assert [item["concurso"] for item in body["resultados_comparados"]] == [500, 501, 502]
    assert [item["atual"] for item in body["resultados_comparados"]] == [False, False, True]
    assert all(0 <= game["acertos"] <= 15 for draw in body["resultados_comparados"] for game in draw["jogos"])
    assert "retrospectiva" in body["aviso"]


def test_lote_de_outro_proprietario_nao_pode_ser_lido(monkeypatch, tmp_path):
    client, token = client_with_store(monkeypatch, tmp_path)
    store = app_module.GAME_STORE
    other = store.create_batch(
        owner="outro-usuario",
        name="Privado",
        lottery="mega_sena",
        method="aleatorio",
        number_count=6,
        source="CAIXA",
        reference_draw=99,
        games=[[1, 2, 3, 4, 5, 6]],
    )
    assert token
    assert client.get(f"/api/jogos/{other['id']}/texto").status_code == 404
    assert client.get(f"/api/jogos/{other['id']}/comparar").status_code == 404


def test_historico_sqlite_sobrevive_reinstanciacao_e_isola_owner(tmp_path):
    path = tmp_path / "persistente.sqlite3"
    store = GameStore(path)
    created = store.create_batch(
        owner="admin",
        name="Persistente",
        lottery="lotofacil",
        method="score",
        number_count=15,
        source="CAIXA",
        reference_draw=3811,
        games=[[1, 2, 3]],
    )
    reopened = GameStore(path)
    assert reopened.get_batch(created["id"], "admin")["games"] == [[1, 2, 3]]
    assert reopened.get_batch(created["id"], "outro") is None
