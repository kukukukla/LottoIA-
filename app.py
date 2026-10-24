#!/usr/bin/env python3
"""
Motor Estatístico de Loterias v2.0 — Web Application
FastAPI + Jinja2 + Session Auth
"""

import asyncio
import os
import logging as _logging
import secrets as _secrets
import random
import sqlite3
from datetime import date, timedelta, datetime
from typing import Literal, Optional
from collections import defaultdict

from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from core.models import Concurso, LoteriaTipo
from core.main_engine import MotorPrincipal
from caixa_client import CAIXA_CLIENT, CaixaAPIError
from games_store import GAME_STORE

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────
app = FastAPI(title="Motor Estatístico de Loterias v2.0")


class GenerateBatchRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    loteria: str = "lotofacil"
    metodo: Literal["aleatorio", "score", "frequencia", "atraso", "balanceado", "fibonacci"] = "score"
    dezenas: Optional[int] = Field(default=None, ge=1, le=100)
    jogos: int = Field(default=5, ge=1, le=50)
    fonte: Literal["caixa", "demo"] = "caixa"
    historico: int = Field(default=30, ge=1, le=300)

SECRET_KEY = os.environ.get("SESSION_SECRET") or _secrets.token_urlsafe(32)
if not os.environ.get("SESSION_SECRET"):
    _logging.getLogger("lottoia.auth").warning(
        "SESSION_SECRET ausente; usando chave temporária. Defina um segredo estável em produção."
    )
_https_only = os.environ.get("SESSION_HTTPS_ONLY", "").lower() in {"1", "true", "yes"}
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=_https_only,
    max_age=60 * 60 * 12,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ──────────────────────────────────────────────
# Credentials — loaded from environment Secrets
# ──────────────────────────────────────────────
_ADMIN_USER = os.environ.get("ADMIN_USERNAME", "").strip()
_ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "")

_log = _logging.getLogger("lottoia.auth")
if not _ADMIN_USER or not _ADMIN_PASS:
    _log.error("ADMIN_USERNAME ou ADMIN_PASSWORD ausentes nos Secrets — nenhum login será aceito.")
else:
    _log.info("Credenciais carregadas: ADMIN_USERNAME=%d chars, ADMIN_PASSWORD=%d chars",
              len(_ADMIN_USER), len(_ADMIN_PASS))

# Brute-force protection: track failed attempts per IP
_FAILED: dict = defaultdict(lambda: {"count": 0, "lockout_until": None})
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300  # 5 minutes


def _check_credentials(username: str, password: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    if not _ADMIN_USER or not _ADMIN_PASS:
        return False
    user_ok = _secrets.compare_digest(username.strip(), _ADMIN_USER)
    pass_ok = _secrets.compare_digest(password, _ADMIN_PASS)
    return user_ok and pass_ok

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def get_current_user(request: Request) -> Optional[str]:
    return request.session.get("user")

def require_login(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/"})
    return user

def gerar_dados_teste(loteria: LoteriaTipo, n: int = 300) -> list:
    concursos = []
    data_base = date(2000, 1, 1)
    for i in range(1, n + 1):
        dezenas = sorted(random.sample(
            range(1, loteria.dezenas_totais + 1),
            loteria.dezenas_sorteadas
        ))
        concursos.append(Concurso(
            numero=i,
            data=data_base + timedelta(days=i * 3),
            dezenas=dezenas,
            loteria=loteria
        ))
    return concursos


async def carregar_concursos_api(
    loteria_slug: str = "lotofacil",
    fonte: str = "caixa",
    quantidade: int = 30,
    atualizar: bool = False,
):
    """Obtém histórico oficial em threadpool ou dados sintéticos explicitamente."""
    try:
        loteria = LoteriaTipo(loteria_slug)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Modalidade inválida.") from exc
    if fonte == "demo":
        concursos = gerar_dados_teste(loteria, max(300, quantidade))
        return loteria, concursos, {
            "fonte": "sintético/demo",
            "atualizado_em": None,
            "cache": False,
            "cache_desatualizado": False,
            "aviso": "Dados artificiais de demonstração; não são resultados oficiais.",
        }
    if fonte != "caixa":
        raise HTTPException(status_code=422, detail="fonte deve ser 'caixa' ou 'demo'.")
    try:
        concursos, metadata = await asyncio.to_thread(
            CAIXA_CLIENT.obter_historico, loteria, quantidade, atualizar
        )
    except CaixaAPIError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Resultados oficiais da CAIXA indisponíveis: {exc}",
        ) from exc
    return loteria, concursos, metadata

# ──────────────────────────────────────────────
# Auth routes
# ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    ip = request.client.host if request.client else "unknown"
    state = _FAILED[ip]

    # Check lockout
    if state["lockout_until"] and datetime.utcnow() < state["lockout_until"]:
        remaining = int((state["lockout_until"] - datetime.utcnow()).total_seconds())
        return templates.TemplateResponse(request, "login.html", {
            "error": f"Muitas tentativas. Tente novamente em {remaining}s."
        })

    if _check_credentials(username, password):
        # Reset failed counter on success
        _FAILED[ip] = {"count": 0, "lockout_until": None}
        request.session.clear()
        request.session["user"] = _ADMIN_USER
        request.session["csrf_token"] = _secrets.token_urlsafe(32)
        return RedirectResponse("/dashboard", status_code=302)

    # Increment failure counter
    state["count"] += 1
    if state["count"] >= _MAX_ATTEMPTS:
        state["lockout_until"] = datetime.utcnow() + timedelta(seconds=_LOCKOUT_SECONDS)
        state["count"] = 0
        return templates.TemplateResponse(request, "login.html", {
            "error": f"Conta bloqueada por {_LOCKOUT_SECONDS // 60} minutos após várias tentativas."
        })

    attempts_left = _MAX_ATTEMPTS - state["count"]
    return templates.TemplateResponse(request, "login.html", {
        "error": f"Usuário ou senha incorretos. ({attempts_left} tentativa(s) restante(s))"
    })

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/images/logo_brand.png", media_type="image/png")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"user": user, "csrf_token": request.session.get("csrf_token", "")},
    )


def validar_csrf(request: Request) -> None:
    esperado = request.session.get("csrf_token")
    recebido = request.headers.get("x-csrf-token", "")
    if not esperado or not recebido or not _secrets.compare_digest(esperado, recebido):
        raise HTTPException(status_code=403, detail="Token CSRF ausente ou inválido.")

# ──────────────────────────────────────────────
# API — Resultados oficiais recentes
# ──────────────────────────────────────────────
@app.get("/api/resultados")
async def api_resultados(
    request: Request,
    loteria: str = Query(default="lotofacil"),
    fonte: str = Query(default="caixa"),
    quantidade: int = Query(default=5, ge=1, le=100),
    atualizar: bool = Query(default=False),
):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)
    modalidade, concursos, metadata = await carregar_concursos_api(
        loteria, fonte, quantidade, atualizar
    )
    return {
        "loteria": modalidade.value,
        "total_concursos": len(concursos),
        "ultimo_concurso": concursos[-1].numero if concursos else None,
        "fonte_dados": metadata,
        "resultados": [
            {
                "concurso": item.numero,
                "data": item.data.isoformat(),
                "dezenas": item.dezenas,
            }
            for item in concursos[-quantidade:]
        ],
    }

# ──────────────────────────────────────────────
# API — Análise Rápida
# ──────────────────────────────────────────────
@app.get("/api/analise")
async def api_analise(
    request: Request,
    loteria: str = Query(default="lotofacil"),
    fonte: str = Query(default="caixa"),
    quantidade: int = Query(default=30, ge=1, le=300),
):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    modalidade, concursos, metadata = await carregar_concursos_api(loteria, fonte, quantidade)
    motor = MotorPrincipal(concursos)

    freq = motor.estatistico.frequencia_absoluta()
    top10_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]

    atraso = motor.estatistico.atraso_atual()
    top10_atraso = sorted(atraso.items(), key=lambda x: x[1], reverse=True)[:10]

    est_soma = motor.estatistico.estatisticas_soma()

    top10_score = motor.score.top_dezenas(10)

    return {
        "frequencia": [{"dezena": d, "ocorrencias": f} for d, f in top10_freq],
        "atraso":     [{"dezena": d, "concursos": a} for d, a in top10_atraso],
        "soma": {
            "media":      est_soma["media"],
            "mediana":    est_soma["mediana"],
            "desvio":     est_soma["desvio_padrao"],
            "p25":        est_soma["percentil_25"],
            "p75":        est_soma["percentil_75"],
        },
        "score": [
            {"ranking": s.ranking, "dezena": s.dezena, "score": round(s.score_total, 4)}
            for s in top10_score
        ],
        "total_concursos": len(concursos),
        "loteria": modalidade.value,
        "ultimo_concurso": concursos[-1].numero if concursos else None,
        "fonte_dados": metadata,
    }

# ──────────────────────────────────────────────
# API — Gerar Jogos
# ──────────────────────────────────────────────
@app.get("/api/gerar")
async def api_gerar(
    request: Request,
    metodo: str = "aleatorio",
    dezenas: Optional[int] = Query(default=None, ge=1, le=100),
    jogos: int = Query(default=5, ge=1, le=50),
    loteria: str = Query(default="lotofacil"),
    fonte: str = Query(default="caixa"),
    quantidade: int = Query(default=30, ge=1, le=300),
):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    metodos_validos = ["aleatorio", "score", "frequencia", "atraso", "balanceado", "fibonacci"]
    if metodo not in metodos_validos:
        return JSONResponse({"error": f"Método inválido. Use: {metodos_validos}"}, status_code=400)

    modalidade, concursos, metadata = await carregar_concursos_api(loteria, fonte, quantidade)
    n_dezenas = modalidade.minimo_aposta if dezenas is None else dezenas
    if not modalidade.minimo_aposta <= n_dezenas <= modalidade.maximo_aposta:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Para {modalidade.value}, dezenas deve ficar entre "
                f"{modalidade.minimo_aposta} e {modalidade.maximo_aposta}."
            ),
        )
    motor = MotorPrincipal(concursos)
    resultado = motor.gerar_jogos(metodo, n_dezenas=n_dezenas, n_jogos=jogos)

    return {
        "metodo": metodo,
        "dezenas": n_dezenas,
        "jogos": [j["dezenas"] for j in resultado],
        "loteria": modalidade.value,
        "ultimo_concurso": concursos[-1].numero if concursos else None,
        "fonte_dados": metadata,
    }


def _public_batch(batch: dict) -> dict:
    return {key: value for key, value in batch.items() if key != "owner"}


def _get_owned_batch(batch_id: str, owner: str) -> dict:
    batch = GAME_STORE.get_batch(batch_id, owner)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lote de jogos não encontrado.")
    return batch


@app.post("/api/jogos", status_code=201)
async def api_criar_lote_jogos(payload: GenerateBatchRequest, request: Request):
    """Gera e persiste um lote de jogos no histórico do usuário autenticado."""
    owner = get_current_user(request)
    if not owner:
        return JSONResponse({"error": "Não autenticado"}, status_code=401)
    validar_csrf(request)
    nome = payload.nome.strip()
    if not nome or any(ord(character) < 32 or ord(character) == 127 for character in nome):
        raise HTTPException(status_code=422, detail="Informe um nome de lote válido, sem caracteres de controle.")
    try:
        loteria = LoteriaTipo(payload.loteria)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Modalidade inválida.") from exc

    loteria, concursos, metadata = await carregar_concursos_api(
        loteria.value, payload.fonte, payload.historico
    )
    quantidade_dezenas = loteria.minimo_aposta if payload.dezenas is None else payload.dezenas
    if not loteria.minimo_aposta <= quantidade_dezenas <= loteria.maximo_aposta:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Para {loteria.value}, dezenas deve ficar entre "
                f"{loteria.minimo_aposta} e {loteria.maximo_aposta}."
            ),
        )
    engine = MotorPrincipal(concursos)
    generated = engine.gerar_jogos(
        payload.metodo, n_dezenas=quantidade_dezenas, n_jogos=payload.jogos
    )
    try:
        batch = GAME_STORE.create_batch(
            owner=owner,
            name=nome,
            lottery=loteria.value,
            method=payload.metodo,
            number_count=quantidade_dezenas,
            source=metadata["fonte"],
            reference_draw=concursos[-1].numero if concursos else None,
            games=[item["dezenas"] for item in generated],
        )
    except (OSError, sqlite3.Error) as exc:
        _log.exception("Falha ao persistir lote de jogos")
        raise HTTPException(status_code=503, detail="Não foi possível salvar o histórico de jogos.") from exc
    return {**_public_batch(batch), "fonte_dados": metadata}


@app.get("/api/jogos")
async def api_historico_jogos(request: Request, limite: int = Query(default=50, ge=1, le=100)):
    owner = get_current_user(request)
    if not owner:
        return JSONResponse({"error": "Não autenticado"}, status_code=401)
    return {"lotes": [_public_batch(item) for item in GAME_STORE.list_batches(owner, limite)]}


@app.get("/api/jogos/{batch_id}/texto")
async def api_exportar_lote_txt(batch_id: str, request: Request):
    owner = get_current_user(request)
    if not owner:
        return JSONResponse({"error": "Não autenticado"}, status_code=401)
    batch = _get_owned_batch(batch_id, owner)
    lines = [
        "LOTTOIA — JOGOS GERADOS",
        f"Nome: {batch['name']}",
        f"Modalidade: {batch['lottery']}",
        f"Método: {batch['method']}",
        f"Dezenas por jogo: {batch['number_count']}",
        f"Quantidade de jogos: {batch['game_count']}",
        f"Fonte: {batch['source']}",
        f"Concurso de referência: {batch['reference_draw'] or 'não informado'}",
        f"Gerado em (UTC): {batch['created_at']}",
        "",
    ]
    lines.extend(
        f"Jogo {index}: " + " ".join(f"{number:02d}" for number in numbers)
        for index, numbers in enumerate(batch["games"], start=1)
    )
    lines.extend(["", "Nota: combinação não representa previsão nem aumenta a probabilidade de acerto."])
    return PlainTextResponse(
        "\n".join(lines) + "\n",
        headers={
            "Content-Disposition": f'attachment; filename="lottoia_{batch_id[:12]}.txt"',
            "Cache-Control": "private, no-store",
        },
    )


@app.get("/api/jogos/{batch_id}/comparar")
async def api_comparar_lote(
    batch_id: str,
    request: Request,
    quantidade: int = Query(default=30, ge=1, le=100),
    atualizar: bool = Query(default=False),
):
    owner = get_current_user(request)
    if not owner:
        return JSONResponse({"error": "Não autenticado"}, status_code=401)
    batch = _get_owned_batch(batch_id, owner)
    _, concursos, metadata = await carregar_concursos_api(
        batch["lottery"], "caixa", quantidade, atualizar
    )
    latest = concursos[-1].numero if concursos else None
    espelho = []
    resumo = {
        index: {"maximo_acertos": 0, "concurso_maximo": None}
        for index in range(1, batch["game_count"] + 1)
    }
    for concurso in concursos:
        sorteadas = set(concurso.dezenas)
        resultados_jogos = []
        for index, jogo in enumerate(batch["games"], start=1):
            correspondencias = sorted(set(jogo) & sorteadas)
            acertos = len(correspondencias)
            if acertos > resumo[index]["maximo_acertos"]:
                resumo[index] = {"maximo_acertos": acertos, "concurso_maximo": concurso.numero}
            resultados_jogos.append(
                {"jogo": index, "acertos": acertos, "dezenas_correspondentes": correspondencias}
            )
        espelho.append(
            {
                "concurso": concurso.numero,
                "data": concurso.data.isoformat(),
                "atual": concurso.numero == latest,
                "dezenas_sorteadas": concurso.dezenas,
                "jogos": resultados_jogos,
            }
        )
    return {
        "lote_id": batch_id,
        "nome": batch["name"],
        "loteria": batch["lottery"],
        "concurso_mais_recente": latest,
        "resumo_por_jogo": [
            {"jogo": index, **resumo[index]} for index in range(1, batch["game_count"] + 1)
        ],
        "resultados_comparados": espelho,
        "fonte_dados": metadata,
        "aviso": "Comparação retrospectiva de coincidências; não estima nem prevê sorteios futuros.",
    }

# ──────────────────────────────────────────────
# API — Monte Carlo
# ──────────────────────────────────────────────
@app.get("/api/simular")
async def api_simular(
    request: Request,
    n: int = Query(default=1000, ge=1, le=10000),
    loteria: str = Query(default="lotofacil"),
    fonte: str = Query(default="caixa"),
    quantidade: int = Query(default=30, ge=1, le=300),
):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    modalidade, concursos, metadata = await carregar_concursos_api(loteria, fonte, quantidade)
    motor = MotorPrincipal(concursos)
    rel = motor.simulacoes.monte_carlo_aleatorio(n, modalidade.dezenas_sorteadas)

    return {
        "total":   rel.total_simulacoes,
        "media":   rel.media_acertos,
        "maximo":  rel.max_acertos,
        "minimo":  rel.min_acertos,
        "desvio":  rel.desvio_padrao,
        "distribuicao": {str(k): v for k, v in sorted(rel.acertos_percentual.items())},
        "loteria": modalidade.value,
        "ultimo_concurso": concursos[-1].numero if concursos else None,
        "fonte_dados": metadata,
    }

# ──────────────────────────────────────────────
# API — Testes Estatísticos
# ──────────────────────────────────────────────
@app.get("/api/testes")
async def api_testes(
    request: Request,
    loteria: str = Query(default="lotofacil"),
    fonte: str = Query(default="caixa"),
    quantidade: int = Query(default=30, ge=1, le=300),
):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    modalidade, concursos, metadata = await carregar_concursos_api(loteria, fonte, quantidade)
    motor = MotorPrincipal(concursos)

    chi  = motor.comparativo.teste_chi_quadrado(concursos)
    ks   = motor.comparativo.teste_ks(concursos)
    runs = motor.comparativo.teste_runs(concursos, 1)

    return {
        "chi_quadrado": {
            "chi2":         chi.get("chi2"),
            "p_value":      chi.get("p_value"),
            "conclusao":    chi.get("conclusao", chi.get("interpretacao", "")),
        },
        "kolmogorov_smirnov": {
            "statistic":    ks.get("statistic"),
            "p_value":      ks.get("p_value"),
            "interpretacao": ks.get("interpretacao", ""),
        },
        "runs": {
            "z_score":      runs.get("z_score"),
            "interpretacao": runs.get("interpretacao", ""),
        },
        "loteria": modalidade.value,
        "ultimo_concurso": concursos[-1].numero if concursos else None,
        "total_concursos": len(concursos),
        "fonte_dados": metadata,
    }

# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=False)
