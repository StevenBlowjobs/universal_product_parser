"""
ML модели для обработки изображений
"""

from .u2net_model import U2NetModel
from .watermark_detector import WatermarkDetector

__all__ = [
    'U2NetModel',
    'WatermarkDetector'
]
