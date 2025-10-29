"""
Ядро системы - парсинг и обработка данных
"""

from .adaptive_parser import AdaptiveProductParser
from .structure_detector import WebsiteStructureDetector
from .content_extractor import ContentExtractor
from .navigation_manager import NavigationManager

__all__ = [
    'AdaptiveProductParser',
    'WebsiteStructureDetector',
    'ContentExtractor', 
    'NavigationManager'
]
