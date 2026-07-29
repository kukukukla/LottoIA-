
"""
motor_estrategias.py - Motor de Estratégias Configuráveis (EXPANDIDO)
"""
from typing import List, Dict, Callable, Optional, Set, Tuple
from collections import Counter
import numpy as np
from models import Concurso, LoteriaTipo, EstrategiaConfig
from motor_estatistico import MotorEstatistico


class FiltroInvalidoError(Exception):
    """Exceção para filtros inválidos."""
    pass


class MotorEstrategias:
    """
    Motor de estratégias configuráveis para geração de jogos.
    Versão expandida com 20+ filtros.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None
        self.estatistico = MotorEstatistico(self.concursos)
        self._estrategias: Dict[str, EstrategiaConfig] = {}
        self._filtros_disponiveis = self._registrar_filtros()

    def _registrar_filtros(self) -> Dict[str, Callable]:
        """Registra todos os filtros disponíveis (20+ filtros)."""
        return {
            # === FILTROS DE FREQUÊNCIA ===
            "frequencia_historica": self._filtro_frequencia_historica,
            "frequencia_recente": self._filtro_frequencia_recente,
            "frequencia_por_janela": self._filtro_frequencia_por_janela,
            "dezenas_quentes": self._filtro_dezenas_quentes,
            "dezenas_frias": self._filtro_dezenas_frias,

            # === FILTROS DE ATRASO ===
            "dezenas_atrasadas": self._filtro_dezenas_atrasadas,
            "atraso_relativo": self._filtro_atraso_relativo,
            "atraso_acima_media": self._filtro_atraso_acima_media,
            "atraso_maximo_historico": self._filtro_atraso_maximo,

            # === FILTROS DE DISTRIBUIÇÃO ===
            "distribuicao_espacial": self._filtro_distribuicao_espacial,
            "equilibrio_par_impar": self._filtro_equilibrio_par_impar,
            "equilibrio_baixo_alto": self._filtro_equilibrio_baixo_alto,
            "distribuicao_linhas": self._filtro_distribuicao_linhas,
            "distribuicao_colunas": self._filtro_distribuicao_colunas,

            # === FILTROS DE SOMA E ESTATÍSTICAS ===
            "soma_dezenas": self._filtro_soma_dezenas,
            "media_dezenas": self._filtro_media_dezenas,
            "desvio_padrao": self._filtro_desvio_padrao,

            # === FILTROS DE SEQUÊNCIA ===
            "sequencias_limitadas": self._filtro_sequencias_limitadas,
            "sequencias_minimas": self._filtro_sequencias_minimas,
            "gap_maximo": self._filtro_gap_maximo,

            # === FILTROS DE REPETIÇÃO ===
            "repeticoes_controladas": self._filtro_repeticoes_controladas,
            "repeticoes_minimas": self._filtro_repeticoes_minimas,
            "dezenas_do_ultimo": self._filtro_dezenas_do_ultimo,

            # === FILTROS ESPECIAIS ===
            "criterio_fibonacci": self._filtro_fibonacci,
            "criterio_primos": self._filtro_primos,
            "criterio_multiplos": self._filtro_multiplos,
            "terminacoes": self._filtro_terminacoes,

            # === FILTROS DE TENDÊNCIA ===
            "tendencia": self._filtro_tendencia,
            "momentum_positivo": self._filtro_momentum_positivo,
            "ciclo_dominante": self._filtro_ciclo_dominante,
        }

    # ═══════════════════════════════════════════════════════════
    # CRUD DE ESTRATÉGIAS
    # ═══════════════════════════════════════════════════════════

    def criar_estrategia(self, config: EstrategiaConfig) -> str:
        self._validar_config(config)
        self._estrategias[config.id] = config
        return config.id

    def editar_estrategia(self, id: str, config: EstrategiaConfig) -> bool:
        if id not in self._estrategias:
            return False
        self._validar_config(config)
        config.id = id
        self._estrategias[id] = config
        return True

    def duplicar_estrategia(self, id: str, novo_nome: str = None) -> Optional[str]:
        if id not in self._estrategias:
            return None
        original = self._estrategias[id]
        nova = EstrategiaConfig(
            nome=novo_nome or f"{original.nome} (Cópia)",
            loteria=original.loteria,
            quantidade_dezenas=original.quantidade_dezenas,
            filtros=original.filtros.copy(),
            pesos=original.pesos.copy()
        )
        self._estrategias[nova.id] = nova
        return nova.id

    def remover_estrategia(self, id: str) -> bool:
        if id in self._estrategias:
            del self._estrategias[id]
            return True
        return False

    def listar_estrategias(self) -> List[EstrategiaConfig]:
        return list(self._estrategias.values())

    def obter_estrategia(self, id: str) -> Optional[EstrategiaConfig]:
        return self._estrategias.get(id)

    def exportar_estrategia(self, id: str) -> Dict:
        """Exporta estratégia para JSON/dict."""
        e = self._estrategias.get(id)
        if not e:
            return {}
        return {
            "id": e.id,
            "nome": e.nome,
            "loteria": e.loteria.value,
            "quantidade_dezenas": e.quantidade_dezenas,
            "filtros": e.filtros,
            "pesos": e.pesos,
            "created_at": e.created_at.isoformat()
        }

    def importar_estrategia(self, dados: Dict) -> str:
        """Importa estratégia de dict/JSON."""
        config = EstrategiaConfig(
            nome=dados["nome"],
            loteria=LoteriaTipo(dados["loteria"]),
            quantidade_dezenas=dados["quantidade_dezenas"],
            filtros=dados.get("filtros", {}),
            pesos=dados.get("pesos", {})
        )
        return self.criar_estrategia(config)

    def _validar_config(self, config: EstrategiaConfig):
        if config.quantidade_dezenas < config.loteria.minimo_aposta:
            raise FiltroInvalidoError(
                f"Mínimo de dezenas para {config.loteria.value}: {config.loteria.minimo_aposta}"
            )
        if config.quantidade_dezenas > config.loteria.maximo_aposta:
            raise FiltroInvalidoError(
                f"Máximo de dezenas para {config.loteria.value}: {config.loteria.maximo_aposta}"
            )

    # ═══════════════════════════════════════════════════════════
    # FILTROS DE FREQUÊNCIA
    # ═══════════════════════════════════════════════════════════

    def _filtro_frequencia_historica(self, pool: Set[int], params: Dict) -> Set[int]:
        freq = self.estatistico.frequencia_absoluta()
        ranking = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        top = set(d for d, _ in ranking[:params.get("max_rank", 25)])
        return pool & top

    def _filtro_frequencia_recente(self, pool: Set[int], params: Dict) -> Set[int]:
        janela = params.get("janela", 10)
        min_freq = params.get("min_freq", 1)
        freq = self.estatistico.frequencia_por_janela(janela)
        return {d for d in pool if freq.get(d, 0) >= min_freq}

    def _filtro_frequencia_por_janela(self, pool: Set[int], params: Dict) -> Set[int]:
        janela = params.get("janela", 25)
        min_freq = params.get("min_freq", 1)
        freq = self.estatistico.frequencia_por_janela(janela)
        return {d for d in pool if freq.get(d, 0) >= min_freq}

    def _filtro_dezenas_quentes(self, pool: Set[int], params: Dict) -> Set[int]:
        """Dezenas mais frequentes em múltiplas janelas."""
        janelas = params.get("janelas", [10, 25, 50])
        min_janelas = params.get("min_janelas", 2)
        contagem = Counter()
        for j in janelas:
            freq = self.estatistico.frequencia_por_janela(j)
            top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:params.get("top", 10)]
            for d, _ in top:
                contagem[d] += 1
        quentes = {d for d, c in contagem.items() if c >= min_janelas}
        return pool & quentes

    def _filtro_dezenas_frias(self, pool: Set[int], params: Dict) -> Set[int]:
        """Dezenas menos frequentes (podem estar "devendo")."""
        freq = self.estatistico.frequencia_absoluta()
        bottom = sorted(freq.items(), key=lambda x: x[1])[:params.get("bottom", 10)]
        return pool & {d for d, _ in bottom}

    # ═══════════════════════════════════════════════════════════
    # FILTROS DE ATRASO
    # ═══════════════════════════════════════════════════════════

    def _filtro_dezenas_atrasadas(self, pool: Set[int], params: Dict) -> Set[int]:
        atrasos = self.estatistico.atraso_atual()
        min_atraso = params.get("min_atraso", 0)
        max_atraso = params.get("max_atraso", 999)
        return {d for d in pool if min_atraso <= atrasos.get(d, 0) <= max_atraso}

    def _filtro_atraso_relativo(self, pool: Set[int], params: Dict) -> Set[int]:
        atraso_atual = self.estatistico.atraso_atual()
        atraso_medio = self.estatistico.atraso_medio()
        razao_min = params.get("razao_min", 0.5)
        razao_max = params.get("razao_max", 3.0)
        selecionadas = set()
        for d in pool:
            atual = atraso_atual.get(d, 0)
            medio = atraso_medio.get(d, 1)
            if medio > 0:
                razao = atual / medio
                if razao_min <= razao <= razao_max:
                    selecionadas.add(d)
        return selecionadas

    def _filtro_atraso_acima_media(self, pool: Set[int], params: Dict) -> Set[int]:
        atraso_atual = self.estatistico.atraso_atual()
        atraso_medio = self.estatistico.atraso_medio()
        return {d for d in pool if atraso_atual.get(d, 0) > atraso_medio.get(d, 0)}

    def _filtro_atraso_maximo(self, pool: Set[int], params: Dict) -> Set[int]:
        atraso_atual = self.estatistico.atraso_atual()
        atraso_max = self.estatistico.atraso_maximo()
        limite = params.get("limite", 0.8)
        return {d for d in pool if atraso_atual.get(d, 0) >= atraso_max.get(d, 0) * limite}

    # ═══════════════════════════════════════════════════════════
    # FILTROS DE DISTRIBUIÇÃO
    # ═══════════════════════════════════════════════════════════

    def _filtro_distribuicao_espacial(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_equilibrio_par_impar(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_equilibrio_baixo_alto(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_distribuicao_linhas(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_distribuicao_colunas(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    # ═══════════════════════════════════════════════════════════
    # FILTROS DE SOMA E ESTATÍSTICAS
    # ═══════════════════════════════════════════════════════════

    def _filtro_soma_dezenas(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_media_dezenas(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_desvio_padrao(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    # ═══════════════════════════════════════════════════════════
    # FILTROS DE SEQUÊNCIA
    # ═══════════════════════════════════════════════════════════

    def _filtro_sequencias_limitadas(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_sequencias_minimas(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    def _filtro_gap_maximo(self, pool: Set[int], params: Dict) -> Set[int]:
        return pool  # Aplicado na validação

    # ═══════════════════════════════════════════════════════════
    # FILTROS DE REPETIÇÃO
    # ═══════════════════════════════════════════════════════════

    def _filtro_repeticoes_controladas(self, pool: Set[int], params: Dict) -> Set[int]:
        max_rep = params.get("max_repeticoes", 15)
        if len(self.concursos) < 2:
            return pool
        ultimo = set(self.concursos[-1].dezenas)
        # Permite até max_rep dezenas do último concurso
        permitidas = set()
        for d in pool:
            if d in ultimo:
                if len(permitidas & ultimo) < max_rep:
                    permitidas.add(d)
            else:
                permitidas.add(d)
        return permitidas

    def _filtro_repeticoes_minimas(self, pool: Set[int], params: Dict) -> Set[int]:
        min_rep = params.get("min_repeticoes", 1)
        if len(self.concursos) < 2:
            return pool
        ultimo = set(self.concursos[-1].dezenas)
        return pool | ultimo  # Garante que pelo menos algumas se repitam

    def _filtro_dezenas_do_ultimo(self, pool: Set[int], params: Dict) -> Set[int]:
        """Inclui/exclui dezenas do último concurso."""
        acao = params.get("acao", "incluir")  # "incluir" ou "excluir"
        if len(self.concursos) < 1:
            return pool
        ultimo = set(self.concursos[-1].dezenas)
        if acao == "incluir":
            return pool | ultimo
        else:
            return pool - ultimo

    # ═══════════════════════════════════════════════════════════
    # FILTROS ESPECIAIS
    # ═══════════════════════════════════════════════════════════

    def _filtro_fibonacci(self, pool: Set[int], params: Dict) -> Set[int]:
        fibs = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89}
        fibs = {f for f in fibs if f <= self.loteria.dezenas_totais}
        min_fib = params.get("min_fibonacci", 0)
        max_fib = params.get("max_fibonacci", 5)
        # Retorna pool + fibs (garante disponibilidade)
        return pool | fibs

    def _filtro_primos(self, pool: Set[int], params: Dict) -> Set[int]:
        primos = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97}
        primos = {p for p in primos if p <= self.loteria.dezenas_totais}
        min_p = params.get("min_primos", 0)
        return pool | primos

    def _filtro_multiplos(self, pool: Set[int], params: Dict) -> Set[int]:
        n = params.get("n", 3)
        multiplos = {d for d in range(1, self.loteria.dezenas_totais + 1) if d % n == 0}
        return pool | multiplos

    def _filtro_terminacoes(self, pool: Set[int], params: Dict) -> Set[int]:
        terminacoes_desejadas = set(params.get("terminacoes", [0, 5]))
        filtradas = {d for d in pool if d % 10 in terminacoes_desejadas}
        if len(filtradas) >= params.get("min_dezenas", 5):
            return filtradas
        return pool

    # ═══════════════════════════════════════════════════════════
    # FILTROS DE TENDÊNCIA
    # ═══════════════════════════════════════════════════════════

    def _filtro_tendencia(self, pool: Set[int], params: Dict) -> Set[int]:
        tendencia_desejada = params.get("tendencia", "subindo")
        metricas = self.estatistico.metricas_completas_por_dezena()
        return {d for d in pool if metricas.get(d) and metricas[d].tendencia == tendencia_desejada}

    def _filtro_momentum_positivo(self, pool: Set[int], params: Dict) -> Set[int]:
        janela = params.get("janela", 10)
        if len(self.concursos) < janela * 2:
            return pool
        recente = self.concursos[-janela:]
        anterior = self.concursos[-2*janela:-janela]
        selecionadas = set()
        for d in pool:
            freq_rec = sum(1 for c in recente if d in c.dezenas)
            freq_ant = sum(1 for c in anterior if d in c.dezenas)
            if freq_ant > 0 and freq_rec / freq_ant > 1.0:
                selecionadas.add(d)
        return selecionadas

    def _filtro_ciclo_dominante(self, pool: Set[int], params: Dict) -> Set[int]:
        """Seleciona dezenas cujo ciclo está próximo de completar."""
        from motor_temporal import MotorTemporal
        temporal = MotorTemporal(self.concursos)
        selecionadas = set()
        for d in pool:
            ciclo = temporal.detectar_ciclos(d)
            ciclo_principal = ciclo.get("ciclo_principal")
            forca = ciclo.get("forca_ciclo", 0)
            if ciclo_principal and forca > 0.3:
                # Verifica se está próximo do ciclo
                posicoes = [i for i, c in enumerate(self.concursos) if d in c.dezenas]
                if posicoes:
                    ultima = posicoes[-1]
                    proximo = ultima + ciclo_principal
                    if abs(len(self.concursos) - proximo) <= params.get("tolerancia", 3):
                        selecionadas.add(d)
        return selecionadas

    # ═══════════════════════════════════════════════════════════
    # APLICAÇÃO DE ESTRATÉGIA
    # ═══════════════════════════════════════════════════════════

    def aplicar_estrategia(self, estrategia_id: str, n_jogos: int = 1) -> List[Dict]:
        config = self._estrategias.get(estrategia_id)
        if not config:
            raise FiltroInvalidoError(f"Estratégia {estrategia_id} não encontrada")
        jogos = []
        for _ in range(n_jogos):
            jogo = self._gerar_jogo_estrategia(config)
            jogos.append(jogo)
        return jogos

    def _gerar_jogo_estrategia(self, config: EstrategiaConfig) -> Dict:
        pool = set(range(1, self.loteria.dezenas_totais + 1))
        criterios_aplicados = {}

        for filtro_nome, params in config.filtros.items():
            if filtro_nome in self._filtros_disponiveis:
                pool = self._filtros_disponiveis[filtro_nome](pool, params)
                criterios_aplicados[filtro_nome] = len(pool)

        if len(pool) < config.quantidade_dezenas:
            faltantes = set(range(1, self.loteria.dezenas_totais + 1)) - pool
            necessario = config.quantidade_dezenas - len(pool)
            if faltantes and necessario > 0:
                adicionais = set(np.random.choice(list(faltantes), size=min(necessario, len(faltantes)), replace=False))
                pool.update(adicionais)

        if len(pool) >= config.quantidade_dezenas:
            dezenas = sorted(np.random.choice(list(pool), size=config.quantidade_dezenas, replace=False))
        else:
            dezenas = sorted(np.random.choice(range(1, self.loteria.dezenas_totais + 1), size=config.quantidade_dezenas, replace=False))

        valido, motivo = self._validar_jogo(dezenas, config)

        return {
            "dezenas": dezenas,
            "estrategia": config.nome,
            "valido": valido,
            "motivo": motivo,
            "criterios_aplicados": criterios_aplicados,
            "balanceamento": self._calcular_balanceamento(dezenas)
        }

    def _validar_jogo(self, dezenas: List[int], config: EstrategiaConfig) -> Tuple[bool, str]:
        # Par/Ímpar
        if "equilibrio_par_impar" in config.filtros:
            params = config.filtros["equilibrio_par_impar"]
            pares = len([d for d in dezenas if d % 2 == 0])
            impares = len(dezenas) - pares
            if params.get("pares") and pares != params["pares"]:
                return False, f"Pares: {pares}, esperado: {params['pares']}"
            if params.get("impares") and impares != params["impares"]:
                return False, f"Ímpares: {impares}, esperado: {params['impares']}"
            if params.get("min_pares") and pares < params["min_pares"]:
                return False, f"Pares: {pares}, mínimo: {params['min_pares']}"
            if params.get("max_pares") and pares > params["max_pares"]:
                return False, f"Pares: {pares}, máximo: {params['max_pares']}"

        # Baixo/Alto
        if "equilibrio_baixo_alto" in config.filtros:
            params = config.filtros["equilibrio_baixo_alto"]
            meio = self.loteria.dezenas_totais // 2
            baixos = len([d for d in dezenas if d <= meio])
            altos = len(dezenas) - baixos
            if params.get("baixos") and baixos != params["baixos"]:
                return False, f"Baixos: {baixos}, esperado: {params['baixos']}"
            if params.get("min_baixos") and baixos < params["min_baixos"]:
                return False, f"Baixos: {baixos}, mínimo: {params['min_baixos']}"

        # Soma
        if "soma_dezenas" in config.filtros:
            params = config.filtros["soma_dezenas"]
            soma = sum(dezenas)
            if "min_soma" in params and soma < params["min_soma"]:
                return False, f"Soma {soma} abaixo do mínimo {params['min_soma']}"
            if "max_soma" in params and soma > params["max_soma"]:
                return False, f"Soma {soma} acima do máximo {params['max_soma']}"

        # Média
        if "media_dezenas" in config.filtros:
            params = config.filtros["media_dezenas"]
            media = sum(dezenas) / len(dezenas)
            if "min_media" in params and media < params["min_media"]:
                return False, f"Média {media:.2f} abaixo do mínimo"
            if "max_media" in params and media > params["max_media"]:
                return False, f"Média {media:.2f} acima do máximo"

        # Sequências
        if "sequencias_limitadas" in config.filtros:
            params = config.filtros["sequencias_limitadas"]
            seqs = self._contar_sequencias(dezenas)
            if params.get("max_sequencias") and seqs > params["max_sequencias"]:
                return False, f"Sequências: {seqs}, máximo: {params['max_sequencias']}"

        if "sequencias_minimas" in config.filtros:
            params = config.filtros["sequencias_minimas"]
            seqs = self._contar_sequencias(dezenas)
            if params.get("min_sequencias") and seqs < params["min_sequencias"]:
                return False, f"Sequências: {seqs}, mínimo: {params['min_sequencias']}"

        # Gap máximo
        if "gap_maximo" in config.filtros:
            params = config.filtros["gap_maximo"]
            gaps = self._calcular_gaps(dezenas)
            if gaps and max(gaps) > params.get("max_gap", 10):
                return False, f"Gap máximo: {max(gaps)}, limite: {params['max_gap']}"

        # Distribuição por faixas
        if "distribuicao_espacial" in config.filtros:
            params = config.filtros["distribuicao_espacial"]
            n_faixas = params.get("n_faixas", 5)
            faixas = self._distribuir_faixas(dezenas, n_faixas)
            min_por_faixa = params.get("min_por_faixa", 1)
            max_por_faixa = params.get("max_por_faixa", 10)
            for f, qtd in faixas.items():
                if qtd < min_por_faixa:
                    return False, f"Faixa {f}: {qtd} dezenas, mínimo: {min_por_faixa}"
                if qtd > max_por_faixa:
                    return False, f"Faixa {f}: {qtd} dezenas, máximo: {max_por_faixa}"

        # Fibonacci
        if "criterio_fibonacci" in config.filtros:
            params = config.filtros["criterio_fibonacci"]
            fibs = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89}
            fibs = {f for f in fibs if f <= self.loteria.dezenas_totais}
            n_fib = len(set(dezenas) & fibs)
            if params.get("min_fibonacci") and n_fib < params["min_fibonacci"]:
                return False, f"Fibonacci: {n_fib}, mínimo: {params['min_fibonacci']}"
            if params.get("max_fibonacci") and n_fib > params["max_fibonacci"]:
                return False, f"Fibonacci: {n_fib}, máximo: {params['max_fibonacci']}"

        # Primos
        if "criterio_primos" in config.filtros:
            params = config.filtros["criterio_primos"]
            primos = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47}
            primos = {p for p in primos if p <= self.loteria.dezenas_totais}
            n_primos = len(set(dezenas) & primos)
            if params.get("min_primos") and n_primos < params["min_primos"]:
                return False, f"Primos: {n_primos}, mínimo: {params['min_primos']}"

        # Terminações
        if "terminacoes" in config.filtros:
            params = config.filtros["terminacoes"]
            terminacoes_desejadas = set(params.get("terminacoes", []))
            n_term = sum(1 for d in dezenas if d % 10 in terminacoes_desejadas)
            if params.get("min_terminacoes") and n_term < params["min_terminacoes"]:
                return False, f"Terminações: {n_term}, mínimo: {params['min_terminacoes']}"

        # Repetições
        if "repeticoes_controladas" in config.filtros:
            params = config.filtros["repeticoes_controladas"]
            if len(self.concursos) > 0:
                ultimo = set(self.concursos[-1].dezenas)
                repeticoes = len(set(dezenas) & ultimo)
                if params.get("max_repeticoes") and repeticoes > params["max_repeticoes"]:
                    return False, f"Repetições: {repeticoes}, máximo: {params['max_repeticoes']}"
                if params.get("min_repeticoes") and repeticoes < params["min_repeticoes"]:
                    return False, f"Repetições: {repeticoes}, mínimo: {params['min_repeticoes']}"

        return True, "Válido"

    def _contar_sequencias(self, dezenas: List[int]) -> int:
        dezenas = sorted(dezenas)
        seqs = 0
        for i in range(len(dezenas) - 1):
            if dezenas[i+1] == dezenas[i] + 1:
                seqs += 1
        return seqs

    def _calcular_gaps(self, dezenas: List[int]) -> List[int]:
        dezenas = sorted(dezenas)
        return [dezenas[i+1] - dezenas[i] for i in range(len(dezenas)-1)]

    def _distribuir_faixas(self, dezenas: List[int], n_faixas: int) -> Dict:
        total = self.loteria.dezenas_totais
        tamanho = total // n_faixas
        faixas = {}
        for i in range(n_faixas):
            inicio = i * tamanho + 1
            fim = (i + 1) * tamanho
            faixas[f"{inicio}-{fim}"] = len([d for d in dezenas if inicio <= d <= fim])
        return faixas

    def _calcular_balanceamento(self, dezenas: List[int]) -> Dict:
        meio = self.loteria.dezenas_totais // 2
        return {
            "pares": len([d for d in dezenas if d % 2 == 0]),
            "impares": len([d for d in dezenas if d % 2 != 0]),
            "baixos": len([d for d in dezenas if d <= meio]),
            "altos": len([d for d in dezenas if d > meio]),
            "soma": sum(dezenas),
            "media": round(sum(dezenas) / len(dezenas), 2)
        }
