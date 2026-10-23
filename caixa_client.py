"""Integração de leitura com o endpoint oficial de resultados da CAIXA.

O serviço de resultados não publica contrato de API versionado. Por isso, este
cliente valida campos, datas, dezenas e número do concurso antes de devolver
qualquer objeto ao motor; falhas nunca viram silenciosamente dados sintéticos.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.models import Concurso, LoteriaTipo


class CaixaAPIError(RuntimeError):
    """Falha de transporte ou resposta inválida do serviço CAIXA."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CaixaLoteriasClient:
    BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api"
    API_SLUGS = {
        LoteriaTipo.LOTOFACIL: "lotofacil",
        LoteriaTipo.MEGA_SENA: "megasena",
        LoteriaTipo.LOTOMANIA: "lotomania",
    }
    MAX_HISTORICO = 300
    MAX_FUTURE_PROBES = 5

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        timeout: float = 15.0,
        cache_ttl_seconds: int = 600,
        max_workers: int = 4,
    ):
        default_dir = Path(__file__).resolve().parent / "data" / "loterias"
        self.cache_dir = Path(cache_dir or os.getenv("LOTTO_DATA_DIR", default_dir))
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_workers = max(1, min(int(max_workers), 6))
        self._cache_lock = threading.RLock()

    def _slug(self, loteria: LoteriaTipo) -> str:
        try:
            return self.API_SLUGS[loteria]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Modalidade não suportada pela integração CAIXA: {loteria!r}") from exc

    def _fetch_json(self, url: str) -> Dict[str, Any]:
        request = Request(
            url,
            headers={
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "LottoIA/2.1 (+https://github.com/kukukukla/LottoIA-)",
                "Origin": "https://loterias.caixa.gov.br",
                "Referer": "https://loterias.caixa.gov.br/",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise CaixaAPIError(
                f"A CAIXA respondeu HTTP {exc.code} ao consultar resultados.",
                status_code=exc.code,
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise CaixaAPIError(f"Não foi possível conectar ao serviço da CAIXA: {exc}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CaixaAPIError("A CAIXA retornou uma resposta que não é JSON UTF-8 válido.") from exc
        if not isinstance(payload, dict):
            raise CaixaAPIError("A resposta da CAIXA não é um objeto JSON.")
        return payload

    @staticmethod
    def _parse_date(value: Any) -> date:
        if not isinstance(value, str) or not value.strip():
            raise CaixaAPIError("Campo dataApuracao ausente ou inválido na resposta da CAIXA.")
        value = value.strip()
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
        for pattern in ("%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, pattern).date()
            except ValueError:
                continue
        raise CaixaAPIError(f"Data de apuração não reconhecida: {value!r}.")

    def _parse_concurso(
        self,
        payload: Dict[str, Any],
        loteria: LoteriaTipo,
        esperado: Optional[int] = None,
    ) -> Concurso:
        numero_raw = payload.get("numero", payload.get("numeroDoConcurso"))
        try:
            numero = int(numero_raw)
        except (TypeError, ValueError) as exc:
            raise CaixaAPIError("Número de concurso ausente ou inválido na resposta da CAIXA.") from exc
        if numero < 1 or (esperado is not None and numero != esperado):
            raise CaixaAPIError(
                f"A CAIXA retornou concurso {numero}; era esperado {esperado or 'um número positivo'}."
            )

        data = self._parse_date(payload.get("dataApuracao", payload.get("data")))
        dezenas_raw = payload.get("listaDezenas")
        if dezenas_raw is None:
            dezenas_raw = payload.get("dezenasSorteadasOrdemSorteio")
        if not isinstance(dezenas_raw, list):
            raise CaixaAPIError("Lista de dezenas ausente ou inválida na resposta da CAIXA.")
        try:
            dezenas = [int(str(item).strip()) for item in dezenas_raw]
        except (TypeError, ValueError) as exc:
            raise CaixaAPIError("A resposta da CAIXA contém dezenas que não são números inteiros.") from exc

        if len(dezenas) != loteria.dezenas_sorteadas:
            raise CaixaAPIError(
                f"Concurso {numero}: esperadas {loteria.dezenas_sorteadas} dezenas para "
                f"{loteria.value}; recebidas {len(dezenas)}."
            )
        if len(set(dezenas)) != len(dezenas):
            raise CaixaAPIError(f"Concurso {numero}: a resposta contém dezenas duplicadas.")
        if any(dezena < 1 or dezena > loteria.dezenas_totais for dezena in dezenas):
            raise CaixaAPIError(
                f"Concurso {numero}: há dezena fora do intervalo 1–{loteria.dezenas_totais}."
            )

        return Concurso(numero=numero, data=data, dezenas=sorted(dezenas), loteria=loteria)

    def buscar_concurso(self, loteria: LoteriaTipo, numero: int) -> Concurso:
        """Busca e valida um concurso específico."""
        if isinstance(numero, bool) or not isinstance(numero, int) or numero < 1:
            raise ValueError("numero deve ser um inteiro positivo")
        url = f"{self.BASE_URL}/{self._slug(loteria)}/{numero}"
        return self._parse_concurso(self._fetch_json(url), loteria, esperado=numero)

    def buscar_ultimo(self, loteria: LoteriaTipo) -> Concurso:
        """Consulta o índice mais recente e confirma concursos imediatamente seguintes."""
        url = f"{self.BASE_URL}/{self._slug(loteria)}"
        ultimo = self._parse_concurso(self._fetch_json(url), loteria)
        # O índice /<modalidade> pode ficar atrás do resultado já publicado.
        # Confirma até cinco números seguintes; a CAIXA responde 404/500 para
        # concurso futuro ainda não publicado, situação tratada como fim da série.
        for _ in range(self.MAX_FUTURE_PROBES):
            proximo_numero = ultimo.numero + 1
            try:
                proximo = self.buscar_concurso(loteria, proximo_numero)
            except CaixaAPIError as exc:
                if exc.status_code in (404, 500):
                    break
                raise
            ultimo = proximo
        return ultimo

    def buscar_historico(self, loteria: LoteriaTipo, quantidade: int = 30) -> List[Concurso]:
        """Busca os últimos N concursos; paralelismo limitado para reduzir latência."""
        if isinstance(quantidade, bool) or not isinstance(quantidade, int):
            raise ValueError("quantidade deve ser um inteiro entre 1 e 300")
        if not 1 <= quantidade <= self.MAX_HISTORICO:
            raise ValueError("quantidade deve ser um inteiro entre 1 e 300")

        ultimo = self.buscar_ultimo(loteria)
        primeiro_numero = max(1, ultimo.numero - quantidade + 1)
        numeros = list(range(primeiro_numero, ultimo.numero))
        if not numeros:
            return [ultimo]
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            anteriores = list(executor.map(lambda n: self.buscar_concurso(loteria, n), numeros))
        concursos = sorted(anteriores + [ultimo], key=lambda item: item.numero)
        if len(concursos) != ultimo.numero - primeiro_numero + 1:
            raise CaixaAPIError("O histórico oficial retornado está incompleto.")
        return concursos

    def _cache_path(self, loteria: LoteriaTipo) -> Path:
        return self.cache_dir / f"{self._slug(loteria)}.json"

    def _ler_cache(self, loteria: LoteriaTipo) -> Optional[Tuple[List[Concurso], datetime]]:
        path = self._cache_path(loteria)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("loteria") != loteria.value or not isinstance(raw.get("concursos"), list):
                return None
            atualizado_em = datetime.fromisoformat(raw["atualizado_em"])
            if atualizado_em.tzinfo is None:
                atualizado_em = atualizado_em.replace(tzinfo=timezone.utc)
            concursos = [self._parse_concurso(item, loteria) for item in raw["concursos"]]
            concursos.sort(key=lambda item: item.numero)
            if not concursos or len({c.numero for c in concursos}) != len(concursos):
                return None
            return concursos, atualizado_em
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, CaixaAPIError):
            return None

    def _gravar_cache(self, loteria: LoteriaTipo, concursos: List[Concurso]) -> datetime:
        now = datetime.now(timezone.utc)
        path = self._cache_path(loteria)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._cache_lock:
            existing = self._ler_cache(loteria)
            merged = {c.numero: c for c in (existing[0] if existing else [])}
            merged.update({c.numero: c for c in concursos})
            keep = sorted(merged.values(), key=lambda item: item.numero)[-self.MAX_HISTORICO :]
            payload = {
                "loteria": loteria.value,
                "fonte": self.BASE_URL,
                "atualizado_em": now.isoformat(),
                "concursos": [
                    {
                        "numero": c.numero,
                        "dataApuracao": c.data.strftime("%d/%m/%Y"),
                        "listaDezenas": [f"{d:02d}" for d in c.dezenas],
                    }
                    for c in keep
                ],
            }
            temp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, path)
        return now

    def obter_historico(
        self,
        loteria: LoteriaTipo,
        quantidade: int = 30,
        atualizar: bool = False,
    ) -> Tuple[List[Concurso], Dict[str, Any]]:
        """Lê cache recente ou atualiza na fonte oficial, com fallback cacheado explícito."""
        if (
            isinstance(quantidade, bool)
            or not isinstance(quantidade, int)
            or not 1 <= quantidade <= self.MAX_HISTORICO
        ):
            raise ValueError("quantidade deve estar entre 1 e 300")
        with self._cache_lock:
            cached = self._ler_cache(loteria)
        now = datetime.now(timezone.utc)
        if cached:
            cached_items, cache_time = cached
            age = max(0, int((now - cache_time).total_seconds()))
            fresh = age <= self.cache_ttl_seconds
            if fresh and len(cached_items) >= quantidade and not atualizar:
                return cached_items[-quantidade:], {
                    "fonte": "CAIXA",
                    "url_fonte": self.BASE_URL,
                    "atualizado_em": cache_time.isoformat(),
                    "cache": True,
                    "cache_desatualizado": False,
                    "idade_cache_segundos": age,
                    "aviso": None,
                }
        try:
            concursos = self.buscar_historico(loteria, quantidade)
            updated = self._gravar_cache(loteria, concursos)
            return concursos, {
                "fonte": "CAIXA",
                "url_fonte": self.BASE_URL,
                "atualizado_em": updated.isoformat(),
                "cache": False,
                "cache_desatualizado": False,
                "idade_cache_segundos": 0,
                "aviso": None,
            }
        except CaixaAPIError as exc:
            if not cached:
                raise
            cached_items, cache_time = cached
            age = max(0, int((now - cache_time).total_seconds()))
            return cached_items[-quantidade:], {
                "fonte": "CAIXA",
                "url_fonte": self.BASE_URL,
                "atualizado_em": cache_time.isoformat(),
                "cache": True,
                "cache_desatualizado": True,
                "idade_cache_segundos": age,
                "aviso": f"Fonte CAIXA indisponível; exibido cache anterior: {exc}",
            }


CAIXA_CLIENT = CaixaLoteriasClient()
