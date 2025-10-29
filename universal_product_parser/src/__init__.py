"""
Universal Product Parser
Универсальный парсер товаров с автоматической обработкой контента
"""

__version__ = "1.0.0"
__author__ = "Universal Parser Team"
__description__ = "Автоматический парсер товаров с NLP и обработкой изображений"

# Основные импорты для удобства
from .core import AdaptiveProductParser
from .cli.main import main

__all__ = ['AdaptiveProductParser', 'main']
