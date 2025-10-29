#!/usr/bin/env python3
"""
Модуль автоматического определения структуры сайта
"""

import re
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import json
from ..utils.logger import setup_logger


class WebsiteStructureDetector:
    """Интеллектуальный детектор структуры сайта"""
    
    def __init__(self):
        self.logger = setup_logger("structure_detector")
        self.common_patterns = self._load_common_patterns()
        
    def _load_common_patterns(self) -> Dict[str, List[str]]:
        """Загрузка общих паттернов для разных платформ"""
        return {
            'product_name': [
                # XPath паттерны
                '//h1[contains(@class, "title")]',
                '//h1[contains(@class, "product")]',
                '//div[contains(@class, "product-name")]//h1',
                '//h1[@itemprop="name"]',
                # CSS паттерны
                'h1.product-title',
                '.product-name h1',
                '[data-product-name]',
                # Meta tags
                'meta[property="og:title"]'
            ],
            'price': [
                '//span[contains(@class, "price")]',
                '//meta[@property="product:price"]',
                '//div[contains(@class, "price")]',
                '.price-current',
                '[data-price]',
                '.product-price',
                'span.price'
            ],
            'images': [
                '//img[contains(@class, "product-image")]',
                '//div[contains(@class, "gallery")]//img',
                '.product-image img',
                '.gallery-slider img',
                'meta[property="og:image"]'
            ],
            'description': [
                '//div[contains(@class, "description")]',
                '//div[@itemprop="description"]',
                '.product-description',
                '.product-info__description',
                'meta[name="description"]'
            ],
            'characteristics': [
                '//table[contains(@class, "specs")]',
                '//div[contains(@class, "attributes")]',
                '//dl[contains(@class, "features")]',
                '.product-specifications',
                '.technical-data table'
            ],
            'rating': [
                '//div[contains(@class, "rating")]',
                '//span[contains(@class, "stars")]',
                'meta[property="og:rating"]',
                '.product-rating',
                '[data-rating]'
            ],
            'availability': [
                '//span[contains(@class, "stock")]',
                '//link[@itemprop="availability"]',
                '.product-availability',
                '.stock-status',
                '[data-in-stock]'
            ],
            'sku': [
                '//span[contains(@class, "sku")]',
                'meta[itemprop="sku"]',
                '.product-sku',
                '[data-product-id]'
            ]
        }
    
    def auto_detect_selectors(self, html_content: str) -> Dict[str, str]:
        """
        Автоматическое определение селекторов на странице
        
        Args:
            html_content: HTML содержимое страницы
            
        Returns:
            Dict[str, str]: Словарь с найденными селекторами
        """
        self.logger.info("🕵️ Автодетект селекторов...")
        soup = BeautifulSoup(html_content, 'html.parser')
        detected_selectors = {}
        
        for field, patterns in self.common_patterns.items():
            selector = self._find_best_selector(soup, patterns, field)
            if selector:
                detected_selectors[field] = selector
                self.logger.debug(f"✅ {field}: {selector}")
            else:
                self.logger.warning(f"⚠️  {field}: селектор не найден")
        
        # Дополнительный поиск по семантическим признакам
        self._enhance_with_semantic_detection(soup, detected_selectors)
        
        self.logger.info(f"🎯 Найдено селекторов: {len(detected_selectors)}")
        return detected_selectors
    
    def _find_best_selector(self, soup: BeautifulSoup, patterns: List[str], field_type: str) -> Optional[str]:
        """Находит лучший селектор для поля"""
        for pattern in patterns:
            try:
                if pattern.startswith('//'):
                    # XPath поиск (упрощенный через CSS)
                    css_equivalent = self._xpath_to_css(pattern)
                    elements = soup.select(css_equivalent)
                else:
                    # CSS поиск
                    elements = soup.select(pattern)
                
                if elements and self._validate_elements(elements, field_type):
                    return pattern
                    
            except Exception as e:
                self.logger.debug(f"Паттерн {pattern} не сработал: {e}")
                continue
        
        return None
    
    def _xpath_to_css(self, xpath: str) -> str:
        """Упрощенное преобразование XPath в CSS селектор"""
        # Базовая конвертация распространенных паттернов
        conversions = {
            '//': '',  # Убираем начало XPath
            '[contains(@class, "']: '[class*="',
            '[@class="']: '[class="',
            '[@id="']: '[id="',
            '/': ' > ',
        }
        
        css = xpath
        for xpath_pattern, css_pattern in conversions.items():
            css = css.replace(xpath_pattern, css_pattern)
            
        return css.strip()
    
    def _validate_elements(self, elements: List, field_type: str) -> bool:
        """Валидация найденных элементов"""
        if not elements:
            return False
            
        element = elements[0]
        text_content = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
        
        # Валидация по типу поля
        validators = {
            'price': lambda x: bool(re.search(r'\d+[\s.,]*\d*', x)),
            'rating': lambda x: bool(re.search(r'[0-9.,]+', x)) or '★' in x,
            'sku': lambda x: bool(re.search(r'[A-Za-z0-9-]+', x)),
            'availability': lambda x: any(word in x.lower() for word in ['в наличии', 'есть', 'available', 'stock']),
        }
        
        validator = validators.get(field_type)
        return validator(text_content) if validator else bool(text_content.strip())
    
    def _enhance_with_semantic_detection(self, soup: BeautifulSoup, selectors: Dict[str, str]):
        """Улучшение детекции через семантический анализ"""
        # Поиск по текстовым паттернам
        if 'price' not in selectors:
            price_elements = soup.find_all(text=re.compile(r'[\d\s.,]+₽|руб|€|\$'))
            if price_elements:
                # Находим родительский элемент с ценой
                for element in price_elements[:3]:
                    parent = element.parent
                    if parent and hasattr(parent, 'name'):
                        selectors['price'] = f"{parent.name}[class*='price']"
                        break
    
    def save_detected_structure(self, filepath: str, selectors: Dict[str, str]):
        """Сохранение обнаруженной структуры в файл"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(selectors, f, indent=2, ensure_ascii=False)
            self.logger.info(f"💾 Структура сохранена: {filepath}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения структуры: {e}")
