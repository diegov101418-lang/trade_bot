"""
Clases base para todos los modelos de IA
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

import joblib
import numpy as np
import pandas as pd

from .config import ModelConfig

logger = logging.getLogger(__name__)


class BaseModel(ABC):
    """
    Clase base abstracta para todos los modelos de IA del sistema.
    Define la interfaz común y funcionalidad compartida.
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self.model: Optional[Any] = None
        self.last_train: float = 0.0
        self.metrics: Dict[str, Any] = {}

        os.makedirs(self.config.model_dir, exist_ok=True)

        # Cargar o entrenar al inicializar
        self.load_or_train()

    @property
    @abstractmethod
    def model_file(self) -> str:
        """Nombre del archivo donde se guarda el modelo."""
        raise NotImplementedError

    @property
    @abstractmethod
    def features(self) -> List[str]:
        """Lista de features que usa el modelo."""
        raise NotImplementedError

    @property
    @abstractmethod
    def target_column(self) -> str:
        """Nombre de la columna target."""
        raise NotImplementedError

    @property
    def min_samples_required(self) -> int:
        """
        Mínimo de muestras requeridas para entrenar este modelo.
        Las subclases pueden sobrescribir esto si necesitan otro umbral.
        """
        return self.config.min_samples

    def get_model_path(self) -> str:
        """Path completo al archivo del modelo."""
        return os.path.join(self.config.model_dir, self.model_file)

    def load_or_train(self) -> None:
        """
        Intenta cargar modelo existente. Si no existe o falla, entrena uno nuevo.
        """
        path = self.get_model_path()

        if os.path.exists(path):
            try:
                self.model = joblib.load(path)
                logger.info(f"✅ {self.__class__.__name__} cargado desde {path}")
                return
            except Exception as e:
                logger.warning(f"⚠ Error cargando modelo desde {path}: {e}. Reentrenando...")

        logger.info(f"📦 No existe modelo válido en {path}. Entrenando...")
        self.train()

    def validate_dataset(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Validación básica del dataset crudo antes de ingeniería de features.
        """
        if self.target_column not in df.columns:
            logger.warning(
                f"⚠ Falta target '{self.target_column}' en {self.__class__.__name__}"
            )
            return None

        df = df.copy()
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df[df[self.target_column].astype(str).str.strip() != ""]

        if df.empty:
            logger.warning(f"⚠ {self.__class__.__name__}: dataset vacío tras filtrar target")
            return None

        return df

    @abstractmethod
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Realiza ingeniería de features específica del modelo.
        """
        raise NotImplementedError

    @abstractmethod
    def prepare_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara la columna target (conversión de tipos, filtros, etc.).
        """
        raise NotImplementedError

    @abstractmethod
    def _fit_model(self, df: pd.DataFrame) -> bool:
        """
        Entrena el modelo específico.
        """
        raise NotImplementedError

    @abstractmethod
    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realiza predicción sobre nuevos datos.
        """
        raise NotImplementedError

    def train(self) -> bool:
        """
        Pipeline completo de entrenamiento.

        Returns:
            bool: True si el entrenamiento fue exitoso.
        """
        if not os.path.exists(self.config.data_file):
            logger.warning(f"⚠ No existe dataset: {self.config.data_file}")
            return False

        try:
            df = pd.read_csv(
                self.config.data_file,
                encoding="utf-8",
                on_bad_lines="skip",
                engine="python",
            )
            logger.info(f"📊 Dataset cargado para {self.__class__.__name__}: {len(df)} filas")
        except Exception as e:
            logger.error(f"🔥 Error leyendo dataset {self.config.data_file}: {e}")
            return False

        df = self.validate_dataset(df)
        if df is None:
            return False

        try:
            df = self.engineer_features(df)

            missing = [c for c in self.features if c not in df.columns]
            if missing:
                logger.warning(
                    f"⚠ Faltan features procesadas en {self.__class__.__name__}: {missing}"
                )
                return False

            df = self.prepare_target(df)
        except Exception as e:
            logger.error(f"🔥 Error preparando datos en {self.__class__.__name__}: {e}")
            return False

        df = df.dropna(subset=self.features + [self.target_column])

        min_samples = self.min_samples_required
        if len(df) < min_samples:
            logger.warning(f"⚠ Muestras insuficientes en {self.__class__.__name__}: {len(df)} < {min_samples}")
            return False

        success = self._fit_model(df)

        if success:
            self.last_train = time.time()

        return success

    def auto_train(self) -> None:
        """
        Reentrena el modelo si ha pasado el intervalo configurado.
        """
        now = time.time()

        # Si nunca entrenó en esta sesión, evitamos reentrenar inmediatamente
        if self.last_train == 0:
            self.last_train = now
            return

        if now - self.last_train > self.config.retrain_interval:
            logger.info(f"🧠 Reentrenando {self.__class__.__name__}...")
            self.train()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas del modelo actual.
        """
        return {
            "model_type": self.__class__.__name__,
            "metrics": self.metrics,
            "last_train": self.last_train,
            "model_loaded": self.model is not None,
            "model_path": self.get_model_path(),
            "features": self.features,
            "target_column": self.target_column,
            "min_samples_required": self.min_samples_required,
        }

    def delete_model(self) -> bool:
        """
        Elimina el archivo del modelo forzando reentrenamiento.
        """
        path = self.get_model_path()

        if not os.path.exists(path):
            return False

        try:
            os.remove(path)
            logger.info(f"🗑️ Modelo eliminado: {path}")
            self.model = None
            return True
        except Exception as e:
            logger.error(f"🔥 Error eliminando modelo: {e}")
            return False