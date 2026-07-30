#!/usr/bin/env python3
"""
Motor Estatístico de Loterias v2.0 — Web Application
FastAPI + Jinja2 + Session Auth
"""

import os
import secrets as _secrets
import random
import numpy as np
from datetime import date, timedelta, datetime
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from core.models import Concurso, LoteriaTipo
from core.main_engine import MotorPrincipal

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────
app = FastAPI(title="Motor Estatístico de Loterias v2.0")

SECRET_KEY = os.environ.get("SESSION_SECRET", "loteria-dev-secret-2024")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ──────────────────────────────────────────────
# Credentials — loaded from environment Secrets
# ──────────────────────────────────────────────
_ADMIN_USER = os.environ.get("ADMIN_USERNAME", "").strip()
_ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "").strip()

import logging as _logging
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
    pass_ok = _secrets.compare_digest(password.strip(), _ADMIN_PASS)
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
# API — Análise Rápida
# ──────────────────────────────────────────────
@app.get("/api/analise")
async def api_analise(request: Request):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    random.seed(None)
    np.random.seed(None)
    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
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
    }

# ──────────────────────────────────────────────
# API — Gerar Jogos
# ──────────────────────────────────────────────
@app.get("/api/gerar")
async def api_gerar(
    request: Request,
    metodo: str = "aleatorio",
    dezenas: int = 15,
    jogos: int = 5,
):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    metodos_validos = ["aleatorio", "score", "frequencia", "atraso", "balanceado", "fibonacci"]
    if metodo not in metodos_validos:
        return JSONResponse({"error": f"Método inválido. Use: {metodos_validos}"}, status_code=400)

    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    motor = MotorPrincipal(concursos)
    resultado = motor.gerar_jogos(metodo, n_dezenas=dezenas, n_jogos=jogos)

    return {
        "metodo": metodo,
        "dezenas": dezenas,
        "jogos": [j["dezenas"] for j in resultado],
    }

# ──────────────────────────────────────────────
# API — Monte Carlo
# ──────────────────────────────────────────────
@app.get("/api/simular")
async def api_simular(request: Request, n: int = 1000):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    if n > 10000:
        return JSONResponse({"error": "Máximo 10.000 simulações por requisição."}, status_code=400)

    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
    motor = MotorPrincipal(concursos)
    rel = motor.simulacoes.monte_carlo_aleatorio(n, 15)

    return {
        "total":   rel.total_simulacoes,
        "media":   rel.media_acertos,
        "maximo":  rel.max_acertos,
        "minimo":  rel.min_acertos,
        "desvio":  rel.desvio_padrao,
        "distribuicao": {str(k): v for k, v in sorted(rel.acertos_percentual.items())},
    }

# ──────────────────────────────────────────────
# API — Testes Estatísticos
# ──────────────────────────────────────────────
@app.get("/api/testes")
async def api_testes(request: Request):
    if not get_current_user(request):
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    concursos = gerar_dados_teste(LoteriaTipo.LOTOFACIL, 300)
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
    }

# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=False)
