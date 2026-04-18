"""
Configuración centralizada del sistema de IA
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ModelConfig:
    """
    Configuración para todos los modelos de IA.
    
    Attributes:
        model_dir: Directorio donde se guardan los modelos entrenados
        data_file: Archivo CSV con datos de entrenamiento
        min_samples: Mínimo de muestras requeridas para entrenar
        retrain_interval: Segundos entre reentrenamientos automáticos
        cv_folds: Número de folds para validación cruzada
        n_estimators: Número de árboles en Random Forest
        max_depth: Profundidad máxima de árboles
        min_samples_leaf: Mínimo de muestras por hoja
        random_state: Semilla para reproducibilidad
    """
    
    # Paths
    model_dir: str = "models"
    data_file: str = "trades_dataset_train.csv"
    
    # Umbrales
    min_samples: int = 30
    min_samples_strategy: int = 80  # Estrategia necesita más datos
    retrain_interval: int = 300  # 5 minutos
    
    # ML
    cv_folds: int = 5
    n_estimators: int = 200
    max_depth: int = 8
    min_samples_leaf: int = 3
    random_state: int = 42
    
    # Features por modelo
    trade_predictor_features: List[str] = field(default_factory=lambda: [
        "rsi", "volume", "trend", "momentum", "hour",
        "day_of_week", "signal_confidence", "atr",
        "market_regime_num", "volatility_context_num",
        "liquidity_mode_num", "ai_context_risk_num"
    ])
    
    strategy_features: List[str] = field(default_factory=lambda: [
        "rsi", "volume", "trend", "momentum", "hour",
        "day_of_week", "signal_confidence", "atr",
        "market_regime_num", "volatility_context_num"
    ])
    
    # Targets
    target_trade: str = "result_net"
    target_strategy: str = "strategy_name"
    target_risk: str = "risk_mode"