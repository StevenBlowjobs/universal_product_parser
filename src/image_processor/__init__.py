"""
Модуль обработки изображений для Universal Product Parser
"""

from .watermark_remover import WatermarkRemover
from .background_handler import BackgroundHandler
from .image_editor import ImageEditor
from .pixel_manipulator import PixelManipulator

__all__ = [
    'WatermarkRemover',
    'BackgroundHandler',
    'ImageEditor',
    'PixelManipulator'
]
