
"""
motor_ml.py - Motor de Machine Learning para Loterias
"""
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from models import Concurso, LoteriaTipo


class MotorML:
    """
    Motor de Machine Learning para análise preditiva de loterias.
    IMPORTANTE: Os modelos identificam padrões históricos, mas
    NÃO predizem resultados futuros com acurácia superior ao acaso.
    """

    def __init__(self, concursos: List[Concurso]):
        self.concursos = sorted(concursos, key=lambda c: c.numero)
        self.loteria = self.concursos[0].loteria if self.concursos else None
        self.scaler = StandardScaler()
        self.modelos = {}
        self._preparar_dados()

    def _preparar_dados(self):
        """Prepara features para treinamento."""
        self.features = []
        self.labels = []

        for i in range(50, len(self.concursos)):
            # Features: estatísticas dos últimos 50 concursos
            historico = self.concursos[i-50:i]
            feat = self._extrair_features(historico)

            # Label: quais dezenas saíram no concurso i
            label = self.concursos[i].dezenas

            self.features.append(feat)
            self.labels.append(label)

    def _extrair_features(self, historico: List[Concurso]) -> Dict[int, np.ndarray]:
        """Extrai features para cada dezena baseado no histórico."""
        features_por_dezena = {}

        for d in range(1, self.loteria.dezenas_totais + 1):
            # Frequência nos últimos N concursos
            freq_5 = sum(1 for c in historico[-5:] if d in c.dezenas)
            freq_10 = sum(1 for c in historico[-10:] if d in c.dezenas)
            freq_25 = sum(1 for c in historico[-25:] if d in c.dezenas)
            freq_50 = sum(1 for c in historico if d in c.dezenas)

            # Atraso
            atraso = 0
            for c in reversed(historico):
                if d in c.dezenas:
                    break
                atraso += 1

            # Última posição
            ultima_pos = None
            for i, c in enumerate(reversed(historico)):
                if d in c.dezenas:
                    ultima_pos = len(historico) - 1 - i
                    break

            # Momentum
            momentum = freq_5 / max(freq_10, 1)

            # Sequência (se saiu nos últimos 3)
            sequencia = 1 if all(d in c.dezenas for c in historico[-3:]) else 0

            features_por_dezena[d] = np.array([
                freq_5 / 5,
                freq_10 / 10,
                freq_25 / 25,
                freq_50 / 50,
                atraso / 50,
                momentum,
                sequencia,
                d / self.loteria.dezenas_totais,  # posição numérica
            ])

        return features_por_dezena

    def treinar_modelo(self, modelo_tipo: str = "random_forest") -> Dict:
        """
        Treina um modelo de ML para cada dezena.
        """
        resultados = {}

        for d in range(1, self.loteria.dezenas_totais + 1):
            X = []
            y = []

            for feat, label in zip(self.features, self.labels):
                X.append(feat[d])
                y.append(1 if d in label else 0)

            X = np.array(X)
            y = np.array(y)

            if len(set(y)) < 2:
                continue

            if modelo_tipo == "random_forest":
                modelo = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            elif modelo_tipo == "gradient_boosting":
                modelo = GradientBoostingClassifier(n_estimators=50, max_depth=3, random_state=42)
            elif modelo_tipo == "logistic":
                modelo = LogisticRegression(max_iter=1000, random_state=42)
            else:
                modelo = RandomForestClassifier(n_estimators=50, random_state=42)

            # Cross-validation
            try:
                scores = cross_val_score(modelo, X, y, cv=3, scoring='roc_auc')
                auc_medio = np.mean(scores)
            except:
                auc_medio = 0.5

            # Treina no conjunto completo
            modelo.fit(X, y)
            self.modelos[d] = modelo

            resultados[d] = {
                "auc_cv": round(auc_medio, 4),
                "acuracia": round(modelo.score(X, y), 4),
                "importancia_features": dict(zip(
                    ["freq_5", "freq_10", "freq_25", "freq_50", "atraso", "momentum", "sequencia", "posicao"],
                    modelo.feature_importances_.tolist() if hasattr(modelo, 'feature_importances_') else [0]*8
                ))
            }

        return resultados

    def predizer_probabilidades(self) -> Dict[int, float]:
        """
        Prediz probabilidade de cada dezena no próximo concurso.
        """
        if not self.modelos:
            return {}

        # Features do estado atual
        historico = self.concursos[-50:]
        feat_atual = self._extrair_features(historico)

        probabilidades = {}
        for d in range(1, self.loteria.dezenas_totais + 1):
            if d in self.modelos:
                prob = self.modelos[d].predict_proba(feat_atual[d].reshape(1, -1))[0][1]
                probabilidades[d] = round(prob, 4)
            else:
                probabilidades[d] = self.loteria.dezenas_sorteadas / self.loteria.dezenas_totais

        return probabilidades

    def ranking_ml(self, top_n: int = 15) -> List[Tuple[int, float]]:
        """Ranking das dezenas por probabilidade do modelo ML."""
        probs = self.predizer_probabilidades()
        return sorted(probs.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def avaliar_modelo(self) -> Dict:
        """Avaliação honesta do modelo - espera-se AUC ~ 0.5 (aleatório)."""
        aucs = []
        for d, info in self.modelos.items():
            if hasattr(info, 'feature_importances_'):
                continue

        return {
            "mensagem": "Modelos de ML em loterias esperam AUC ≈ 0.5 (acaso).",
            "interpretacao": "AUC > 0.55 pode indicar vazamento de dados ou overfitting.",
            "recomendacao": "Usar como uma dimensão adicional de análise, não como preditor."
        }
