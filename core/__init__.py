"""
core/__init__.py - package shim
"""
_MODULES = [
    "models", "main_engine", "motor_estatistico", "motor_matematico",
    "motor_simulacoes", "motor_estrategias", "motor_score",
    "motor_desdobramentos", "motor_temporal", "motor_padroes",
    "motor_comparativo", "motor_genetico", "motor_relatorios",
    "gerador_jogos"
]

_EXPORTS = {
    "Concurso": (".models", "Concurso"),
    "LoteriaTipo": (".models", "LoteriaTipo"),
    "EstrategiaConfig": (".models", "EstrategiaConfig"),
    "JogoGerado": (".models", "JogoGerado"),
    "MotorPrincipal": (".main_engine", "MotorPrincipal"),
    "MotorEstatistico": (".motor_estatistico", "MotorEstatistico"),
    "MotorScore": (".motor_score", "MotorScore"),
    "MotorTemporal": (".motor_temporal", "MotorTemporal"),
}

__all__ = _MODULES + list(_EXPORTS)


def __getattr__(name):
    """Load documented public classes on demand, keeping imports lightweight."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    module_name, attribute = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value

__version__ = "2.0.0"
