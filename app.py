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
from datetime import date, timedelta, datetime
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from core.models import Concurso, LoteriaTipo
from core.main_engine import MotorPrincipal
from caixa_client import CAIXA_CLIENT, CaixaAPIError

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────
app = FastAPI(title="Motor Estatístico de Loterias v2.0")

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
        request.session["user"] = username
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
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})

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
