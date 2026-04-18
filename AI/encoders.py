"""
Codificadores de features categóricas
"""

from typing import Any, Dict, Optional


class FeatureEncoder:
    """
    Codificador centralizado para features categóricas.
    Todos los mappings en un solo lugar para consistencia.
    """
    
    MAPPINGS: Dict[str, Dict[str, int]] = {
        'market_regime': {
            'bull': 1, 
            'bear': -1, 
            'sideways': 0,
            'alcista': 1,
            'bajista': -1,
            'lateral': 0
        },
        'volatility': {
            'low': 0, 
            'medium': 1, 
            'high': 2,
            'baja': 0,
            'media': 1,
            'alta': 2
        },
        'liquidity': {
            'low': 0, 
            'medium': 1, 
            'normal': 2,
            'baja': 0,
            'media': 1,
            'normal': 2
        },
        'risk': {
            'conservative': 0, 
            'normal': 1, 
            'aggressive': 2,
            'conservador': 0,
            'normal': 1,
            'agresivo': 2
        }
    }
    
    DEFAULTS = {
        'market_regime': 0,
        'volatility': 1,
        'liquidity': 1,
        'risk': 1
    }
    
    @classmethod
    def encode(cls, feature_type: str, value: Any, default: Optional[int] = None) -> int:
        """
        Codifica un valor categórico a numérico.
        
        Args:
            feature_type: Tipo de feature ('market_regime', 'volatility', etc.)
            value: Valor a codificar
            default: Valor por defecto si no se encuentra mapping
            
        Returns:
            int: Valor numérico codificado
        """
        if value is None:
            return default if default is not None else cls.DEFAULTS.get(feature_type, 0)
        
        mapping = cls.MAPPINGS.get(feature_type, {})
        default_val = default if default is not None else cls.DEFAULTS.get(feature_type, 0)
        
        # Normalizar: minúsculas, sin espacios
        if value is None:
            return default_val

        normalized = str(value).lower().strip()

        if normalized == "":
            return default_val
        
        return mapping.get(normalized, default_val)
    
    @classmethod
    def market_regime(cls, value: Any) -> int:
        """Codifica régimen de mercado: bull/bear/sideways → 1/-1/0"""
        return cls.encode('market_regime', value, 0)
    
    @classmethod
    def volatility(cls, value: Any) -> int:
        """Codifica volatilidad: low/medium/high → 0/1/2"""
        return cls.encode('volatility', value, 1)
    
    @classmethod
    def liquidity(cls, value: Any) -> int:
        """Codifica liquidez: low/medium/normal → 0/1/2"""
        return cls.encode('liquidity', value, 1)
    
    @classmethod
    def risk(cls, value: Any) -> int:
        """Codifica riesgo: conservative/normal/aggressive → 0/1/2"""
        return cls.encode('risk', value, 1)
    
    @classmethod
    def decode(cls, feature_type: str, value: int) -> str:
        """
        Decodifica un valor numérico a categórico (útil para debugging).
        """
        mapping = cls.MAPPINGS.get(feature_type, {})
        reverse_mapping = {v: k for k, v in mapping.items()}
        return reverse_mapping.get(value, "unknown")