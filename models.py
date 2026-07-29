
"""
models.py - Entidades do domínio
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json

class LoteriaTipo(Enum):
    LOTOFACIL = "lotofacil"
    MEGA_SENA = "mega_sena"
    LOTOMANIA = "lotomania"

    @property
    def dezenas_totais(self) -> int:
        return {
            LoteriaTipo.LOTOFACIL: 25,
            LoteriaTipo.MEGA_SENA: 60,
            LoteriaTipo.LOTOMANIA: 100
        }[self]

    @property
    def dezenas_sorteadas(self) -> int:
        return {
            LoteriaTipo.LOTOFACIL: 15,
            LoteriaTipo.MEGA_SENA: 6,
            LoteriaTipo.LOTOMANIA: 20
        }[self]

    @property
    def minimo_aposta(self) -> int:
        return {
            LoteriaTipo.LOTOFACIL: 15,
            LoteriaTipo.MEGA_SENA: 6,
            LoteriaTipo.LOTOMANIA: 50
        }[self]

    @property
    def maximo_aposta(self) -> int:
        return {
            LoteriaTipo.LOTOFACIL: 20,
            LoteriaTipo.MEGA_SENA: 15,
            LoteriaTipo.LOTOMANIA: 50
        }[self]


@dataclass
class Concurso:
    numero: int
    data: date
    dezenas: List[int]
    loteria: LoteriaTipo
    estatisticas: Dict = field(default_factory=dict)
    indices: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.dezenas = sorted(self.dezenas)

    @property
    def soma(self) -> int:
        return sum(self.dezenas)

    @property
    def media(self) -> float:
        return self.soma / len(self.dezenas)

    @property
    def pares(self) -> List[int]:
        return [d for d in self.dezenas if d % 2 == 0]

    @property
    def impares(self) -> List[int]:
        return [d for d in self.dezenas if d % 2 != 0]

    @property
    def baixos(self) -> List[int]:
        meio = self.loteria.dezenas_totais // 2
        return [d for d in self.dezenas if d <= meio]

    @property
    def altos(self) -> List[int]:
        meio = self.loteria.dezenas_totais // 2
        return [d for d in self.dezenas if d > meio]

    @property
    def linhas(self) -> Dict[int, List[int]]:
        """Distribuição por linhas (5 dezenas por linha)"""
        linhas = {i: [] for i in range(1, 6)}
        for d in self.dezenas:
            linha = ((d - 1) // 5) + 1
            if linha in linhas:
                linhas[linha].append(d)
        return linhas

    @property
    def colunas(self) -> Dict[int, List[int]]:
        """Distribuição por colunas (5 dezenas por coluna)"""
        cols = {i: [] for i in range(1, 6)}
        for d in self.dezenas:
            col = ((d - 1) % 5) + 1
            if col in cols:
                cols[col].append(d)
        return cols

    @property
    def sequencias_consecutivas(self) -> List[List[int]]:
        """Identifica sequências consecutivas de dezenas"""
        if not self.dezenas:
            return []
        sequencias = []
        atual = [self.dezenas[0]]
        for i in range(1, len(self.dezenas)):
            if self.dezenas[i] == self.dezenas[i-1] + 1:
                atual.append(self.dezenas[i])
            else:
                if len(atual) >= 2:
                    sequencias.append(atual[:])
                atual = [self.dezenas[i]]
        if len(atual) >= 2:
            sequencias.append(atual)
        return sequencias

    def to_dict(self) -> Dict:
        return {
            "numero": self.numero,
            "data": self.data.isoformat(),
            "dezenas": self.dezenas,
            "loteria": self.loteria.value,
            "estatisticas": self.estatisticas,
            "indices": self.indices,
            "soma": self.soma,
            "media": self.media,
            "pares": len(self.pares),
            "impares": len(self.impares),
            "baixos": len(self.baixos),
            "altos": len(self.altos),
            "sequencias": self.sequencias_consecutivas
        }


@dataclass
class EstrategiaConfig:
    nome: str
    loteria: LoteriaTipo
    quantidade_dezenas: int
    filtros: Dict = field(default_factory=dict)
    pesos: Dict[str, float] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.id:
            self.id = f"est_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@dataclass
class JogoGerado:
    dezenas: List[int]
    estrategia_id: str
    score: float
    criterios_aplicados: Dict
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.dezenas = sorted(self.dezenas)
