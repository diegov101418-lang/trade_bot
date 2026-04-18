"""
Sistema de IA para trading
==========================

Módulos principales:
- TradePredictor: Predice si un trade será rentable neto (0/1)
- StrategyRecommender: Sugiere estrategia y modo de riesgo
- FeatureEncoder: Codificación compartida de features
- ModelConfig: Configuración centralizada

Uso rápido:
    from ai import TradePredictor, StrategyRecommender

    predictor = TradePredictor()
    result = predictor.predict(market_data)
"""
from .historical import HistoricalTradePredictor
from .manager import TradePredictionManager
from .config import ModelConfig
from .encoders import FeatureEncoder
from .predictors import TradePredictor
from .strategy import StrategyRecommender
from .historical import HistoricalTradePredictor
from .manager import TradePredictionManager

__version__ = "2.0.0"

__all__ = [
    "TradePredictor",
    "StrategyRecommender",
    "FeatureEncoder",
    "ModelConfig",
    "predict_trade",
    "train_model",
    "auto_train",
    "load_model",
    "get_model_metrics",
    "suggest_context_decision",
    "train_strategy_models",
    "HistoricalTradePredictor",
    "TradePredictionManager",
    "HistoricalTradePredictor",
]

# Cache simple de instancias para evitar recargar/reentrenar en cada llamada
_trade_predictor = None
_strategy_recommender = None
_risk_recommender = None


def _get_trade_predictor() -> TradePredictor:
    global _trade_predictor
    if _trade_predictor is None:
        _trade_predictor = TradePredictor()
    return _trade_predictor


def _get_strategy_recommender() -> StrategyRecommender:
    global _strategy_recommender
    if _strategy_recommender is None:
        _strategy_recommender = StrategyRecommender(mode="strategy")
    return _strategy_recommender


def _get_risk_recommender() -> StrategyRecommender:
    global _risk_recommender
    if _risk_recommender is None:
        _risk_recommender = StrategyRecommender(mode="risk")
    return _risk_recommender


# Compatibilidad hacia atrás (ai_model.py original)
_prediction_manager = None

def _get_prediction_manager():
    global _prediction_manager
    if _prediction_manager is None:
        _prediction_manager = TradePredictionManager()
    return _prediction_manager

def predict_trade(data: dict) -> int:
    return _get_prediction_manager().predict(data)["prediction"]

def train_model() -> bool:
    """
    Entrena el modelo principal.
    """
    return _get_trade_predictor().train()


def auto_train() -> None:
    """
    Reentrena el modelo principal si es necesario.
    """
    _get_trade_predictor().auto_train()


def load_model():
    """
    Retorna el modelo principal cargado.
    """
    return _get_trade_predictor().model


def get_model_metrics() -> dict:
    """
    Obtiene métricas del modelo principal.
    """
    return _get_trade_predictor().get_metrics()


# Compatibilidad con ai_strategy_learning.py
def suggest_context_decision(data: dict) -> dict:
    """
    Sugiere estrategia y modo de riesgo.
    """
    strategy_result = _get_strategy_recommender().predict(data)
    risk_result = _get_risk_recommender().predict(data)

    return {
        "strategy_suggestion": strategy_result.get("suggestion"),
        "risk_suggestion": risk_result.get("suggestion"),
    }


def train_strategy_models() -> tuple:
    """
    Entrena modelos de estrategia y riesgo.
    """
    strategy_rec = _get_strategy_recommender()
    risk_rec = _get_risk_recommender()

    strategy_success = strategy_rec.train()
    risk_success = risk_rec.train()

    return (
        strategy_rec.model if strategy_success else None,
        risk_rec.model if risk_success else None,
    )