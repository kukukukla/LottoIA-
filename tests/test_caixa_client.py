import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest

from caixa_client import CaixaAPIError, CaixaLoteriasClient
from core.models import LoteriaTipo


def payload(loteria=LoteriaTipo.LOTOFACIL, numero=1, data="19/10/2026"):
    return {
        "numero": numero,
        "dataApuracao": data,
        "listaDezenas": [f"{i:02d}" for i in range(1, loteria.dezenas_sorteadas + 1)],
    }


@pytest.mark.parametrize("loteria", list(LoteriaTipo))
def test_parseia_concurso_oficial_para_todas_modalidades(loteria):
    concurso = CaixaLoteriasClient()._parse_concurso(payload(loteria, 42), loteria)
    assert concurso.numero == 42
    assert concurso.data == date(2026, 10, 19)
    assert len(concurso.dezenas) == loteria.dezenas_sorteadas
    assert concurso.dezenas == sorted(set(concurso.dezenas))
    assert concurso.loteria is loteria


def test_parseia_campo_alternativo_dezenas_em_ordem_de_sorteio():
    client = CaixaLoteriasClient()
    source = payload()
    source["dezenasSorteadasOrdemSorteio"] = source.pop("listaDezenas")
    concurso = client._parse_concurso(source, LoteriaTipo.LOTOFACIL)
    assert len(concurso.dezenas) == 15


@pytest.mark.parametrize(
    "mutate,expected_error",
    [
        (lambda p: p.update(numero="abc"), "Número de concurso"),
        (lambda p: p.update(dataApuracao="ontem"), "Data de apuração"),
        (lambda p: p.update(listaDezenas=["01"]), "esperadas 15 dezenas"),
        (lambda p: p.update(listaDezenas=["01"] * 15), "duplicadas"),
        (lambda p: p.update(listaDezenas=["00"] + [f"{i:02d}" for i in range(2, 16)]), "fora do intervalo"),
    ],
)
def test_rejeita_payload_oficial_invalido(mutate, expected_error):
    source = payload()
    mutate(source)
    with pytest.raises(CaixaAPIError, match=expected_error):
        CaixaLoteriasClient()._parse_concurso(source, LoteriaTipo.LOTOFACIL)


def test_rejeita_resposta_de_numero_diferente_do_solicitado():
    with pytest.raises(CaixaAPIError, match="era esperado 9"):
        CaixaLoteriasClient()._parse_concurso(payload(numero=8), LoteriaTipo.LOTOFACIL, esperado=9)


def test_buscar_ultimo_confirma_concurso_novo_quando_indice_principal_atrasou(monkeypatch):
    client = CaixaLoteriasClient()
    def fake_fetch(url):
        if url.endswith("/lotofacil"):
            return payload(numero=3807)
        if url.endswith("/lotofacil/3808"):
            return payload(numero=3808)
        if url.endswith("/lotofacil/3809"):
            raise CaixaAPIError("concurso futuro indisponível", status_code=500)
        raise AssertionError(f"URL inesperada: {url}")
    monkeypatch.setattr(client, "_fetch_json", fake_fetch)
    assert client.buscar_ultimo(LoteriaTipo.LOTOFACIL).numero == 3808


def test_historico_busca_n_ordenado_com_ultimo_confirmado(monkeypatch):
    client = CaixaLoteriasClient(max_workers=2)
    def fake_fetch(url):
        if url.endswith("/lotofacil"):
            return payload(numero=10)
        if url.endswith("/lotofacil/11"):
            return payload(numero=11)
        if url.endswith("/lotofacil/12"):
            raise CaixaAPIError("ainda não publicado", status_code=500)
        numero = int(url.rsplit("/", 1)[1])
        return payload(numero=numero)
    monkeypatch.setattr(client, "_fetch_json", fake_fetch)
    assert [c.numero for c in client.buscar_historico(LoteriaTipo.LOTOFACIL, 5)] == [7, 8, 9, 10, 11]


def test_historico_rejeita_quantidade_invalida():
    client = CaixaLoteriasClient()
    for quantidade in [0, -1, 301, True, 1.5]:
        with pytest.raises(ValueError):
            client.buscar_historico(LoteriaTipo.LOTOFACIL, quantidade)
        with pytest.raises(ValueError):
            client.obter_historico(LoteriaTipo.LOTOFACIL, quantidade)


def test_cache_persistente_reutilizado_e_fallback_offline(tmp_path, monkeypatch):
    client = CaixaLoteriasClient(cache_dir=tmp_path, cache_ttl_seconds=600)
    concursos = [
        client._parse_concurso(payload(numero=n), LoteriaTipo.LOTOFACIL)
        for n in range(1, 4)
    ]
    monkeypatch.setattr(client, "buscar_historico", lambda loteria, quantidade: concursos[-quantidade:])
    first, metadata = client.obter_historico(LoteriaTipo.LOTOFACIL, 3, atualizar=True)
    assert [c.numero for c in first] == [1, 2, 3]
    assert metadata["cache"] is False
    assert (tmp_path / "lotofacil.json").is_file()

    def unavailable(*args, **kwargs):
        raise CaixaAPIError("offline")
    monkeypatch.setattr(client, "buscar_historico", unavailable)
    cached, cache_meta = client.obter_historico(LoteriaTipo.LOTOFACIL, 2)
    assert [c.numero for c in cached] == [2, 3]
    assert cache_meta["cache"] is True
    assert cache_meta["cache_desatualizado"] is False

    stale_client = CaixaLoteriasClient(cache_dir=tmp_path, cache_ttl_seconds=-1)
    monkeypatch.setattr(stale_client, "buscar_historico", unavailable)
    stale, stale_meta = stale_client.obter_historico(LoteriaTipo.LOTOFACIL, 2, atualizar=True)
    assert [c.numero for c in stale] == [2, 3]
    assert stale_meta["cache_desatualizado"] is True
    assert "offline" in stale_meta["aviso"]


def test_sem_cache_e_sem_rede_propaga_erro(tmp_path, monkeypatch):
    client = CaixaLoteriasClient(cache_dir=tmp_path)
    monkeypatch.setattr(client, "buscar_historico", lambda *args: (_ for _ in ()).throw(CaixaAPIError("offline")))
    with pytest.raises(CaixaAPIError, match="offline"):
        client.obter_historico(LoteriaTipo.LOTOFACIL, 3)


def test_cache_corrompido_e_ignorado(tmp_path):
    path = tmp_path / "lotofacil.json"
    path.write_text("{não-json", encoding="utf-8")
    assert CaixaLoteriasClient(cache_dir=tmp_path)._ler_cache(LoteriaTipo.LOTOFACIL) is None
