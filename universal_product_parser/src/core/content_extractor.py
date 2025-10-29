#!/usr/bin/env python3
"""
Модуль извлечения и нормализации данных товаров
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from ..utils.normalizer import DataNormalizer
from ..utils.logger import setup_logger


class ContentExtractor:
    """Экстрактор и нормализатор данных товаров"""
    
    def __init__(self, detected_selectors: Dict[str, str]):
        self.selectors = detected_selectors
        self.normalizer = DataNormalizer()
        self.logger = setup_logger("content_extractor")
        
    def extract_product_data(self, html_content: str, url: str) -> Dict[str, Any]:
        """Извлекает все данные товара из HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        product_data = {
            'url': url,
            'name': self._extract_field(soup, 'product_name'),
            'price': self._extract_price(soup),
            'original_description': self._extract_field(soup, 'description'),
            'images': self._extract_images(soup, url),
            'characteristics': self._extract_characteristics(soup),
            'rating': self._extract_rating(soup),
            'availability': self._extract_availability(soup),
            'sku': self._extract_sku(soup),
            'category': self._extract_category(soup),
            'metadata': self._extract_metadata(soup)
        }
        
        # Очистка и нормализация данных
        return self._clean_product_data(product_data)
    
    def _extract_field(self, soup: BeautifulSoup, field_name: str) -> Optional[str]:
        """Извлечение поля по обнаруженному селектору"""
        if field_name not in self.selectors:
            return None
            
        selector = self.selectors[field_name]
        try:
            if selector.startswith('//'):
                # XPath (упрощенная реализация через CSS)
                css_selector = self._xpath_to_css(selector)
                elements = soup.select(css_selector)
            else:
                elements = soup.select(selector)
            
            if elements:
                element = elements[0]
                
                # Извлечение текста или атрибута
                if selector.startswith('meta['):
                    return element.get('content', '').strip()
                else:
                    text = element.get_text(strip=True)
                    return text if text else None
                    
        except Exception as e:
            self.logger.debug(f"Ошибка извлечения {field_name}: {e}")
            
        return None
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Специализированное извлечение цены"""
        price_text = self._extract_field(soup, 'price')
        if price_text:
            # Очистка текста цены
            price_clean = re.sub(r'[^\d,.]', '', price_text)
            price_clean = price_clean.replace(',', '.')
            
            try:
                # Поиск числового значения
                price_match = re.search(r'\d+\.?\d*', price_clean)
                if price_match:
                    return float(price_match.group())
            except (ValueError, TypeError):
                pass
                
        return None
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Извлечение ссылок на изображения"""
        images = []
        
        # Извлечение по обнаруженному селектору
        main_image = self._extract_field(soup, 'images')
        if main_image and main_image.startswith(('http', '//')):
            images.append(main_image)
        
        # Дополнительный поиск изображений
        img_elements = soup.find_all('img', {'src': True})
        for img in img_elements[:10]:  # Ограничим количество
            src = img.get('src', '')
            if src and any(keyword in src.lower() for keyword in ['product', 'item', 'goods']):
                full_url = urljoin(base_url, src)
                if full_url not in images:
                    images.append(full_url)
        
        return images[:5]  # Возвращаем первые 5 изображений
    
    def _extract_characteristics(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Извлечение характеристик товара"""
        characteristics = {}
        
        # Попытка извлечь по обнаруженному селектору
        if 'characteristics' in self.selectors:
            selector = self.selectors['characteristics']
            try:
                elements = soup.select(selector)
                for element in elements:
                    char_data = self._parse_characteristics_element(element)
                    characteristics.update(char_data)
            except Exception as e:
                self.logger.debug(f"Ошибка парсинга характеристик: {e}")
        
        # Дополнительный поиск по распространенным паттернам
        if not characteristics:
            characteristics = self._find_characteristics_fallback(soup)
        
        # Нормализация характеристик
        return self.normalizer.normalize_characteristics(characteristics)
    
    def _parse_characteristics_element(self, element) -> Dict[str, str]:
        """Парсинг элемента с характеристиками"""
        chars = {}
        
        # Попробуем разные форматы: таблица, список, dl
        if element.name == 'table':
            # Табличный формат
            rows = element.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        chars[key] = value
        
        elif element.name in ['ul', 'ol']:
            # Списковый формат
            items = element.find_all('li')
            for item in items:
                text = item.get_text(strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    chars[key.strip()] = value.strip()
        
        elif element.name == 'dl':
            # Definition list формат
            dts = element.find_all('dt')
            dds = element.find_all('dd')
            for dt, dd in zip(dts, dds):
                key = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                chars[key] = value
        
        return chars
    
    def _find_characteristics_fallback(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Резервный поиск характеристик"""
        chars = {}
        
        # Поиск по текстовым паттернам
        patterns = [
            r'(\w+[\w\s]*?):\s*([^\n]+)',
            r'(\w+[\w\s]*?)\s*-\s*([^\n]+)'
        ]
        
        text_elements = soup.find_all(text=True)
        full_text = ' '.join([elem for elem in text_elements if elem.parent.name not in ['script', 'style']])
        
        for pattern in patterns:
            matches = re.findall(pattern, full_text)
            for key, value in matches:
                if len(key) < 50 and len(value) < 100:  # Фильтр мусора
                    chars[key.strip()] = value.strip()
        
        return chars
    
    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Извлечение рейтинга"""
        rating_text = self._extract_field(soup, 'rating')
        if rating_text:
            # Поиск числового рейтинга
            rating_match = re.search(r'(\d+[.,]?\d*)', rating_text)
            if rating_match:
                try:
                    return float(rating_match.group(1).replace(',', '.'))
                except ValueError:
                    pass
            
            # Поиск звездочного рейтинга
            if '★' in rating_text:
                stars = rating_text.count('★')
                return float(stars)
        
        return None
    
    def _extract_availability(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение информации о наличии"""
        availability_text = self._extract_field(soup, 'availability') or ""
        availability_text = availability_text.lower()
        
        # Определение статуса наличия
        in_stock_keywords = ['в наличии', 'есть', 'available', 'in stock', 'есть в наличии']
        out_of_stock_keywords = ['нет в наличии', 'распродано', 'out of stock', 'sold out']
        
        in_stock = any(keyword in availability_text for keyword in in_stock_keywords)
        out_of_stock = any(keyword in availability_text for keyword in out_of_stock_keywords)
        
        # Поиск количества
        quantity = None
        quantity_match = re.search(r'(\d+)\s*(шт|штук|pieces?)', availability_text)
        if quantity_match:
            quantity = int(quantity_match.group(1))
        
        return {
            'status': 'in_stock' if in_stock else 'out_of_stock' if out_of_stock else 'unknown',
            'text': availability_text,
            'quantity': quantity
        }
    
    def _extract_sku(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение артикула"""
        sku_text = self._extract_field(soup, 'sku')
        if sku_text:
            # Очистка артикула
            sku_clean = re.sub(r'[^\w-]', '', sku_text)
            return sku_clean if sku_clean else None
        return None
    
    def _extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение категории товара"""
        # Поиск в хлебных крошках
        breadcrumbs = soup.select('.breadcrumbs, .breadcrumb, [class*="breadcrumb"]')
        if breadcrumbs:
            breadcrumb_text = ' > '.join([elem.get_text(strip=True) for elem in breadcrumbs[0].find_all(['a', 'span'])])
            return breadcrumb_text
        
        # Поиск в навигации
        nav_elements = soup.select('.category-path, .product-category')
        if nav_elements:
            return nav_elements[0].get_text(strip=True)
            
        return None
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Извлечение метаданных"""
        metadata = {}
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        return metadata
    
    def _clean_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Очистка и нормализация данных товара"""
        cleaned_data = {}
        
        for key, value in product_data.items():
            if value is None or value == "":
                continue
                
            if isinstance(value, str):
                # Очистка строк от лишних пробелов
                value = re.sub(r'\s+', ' ', value).strip()
                
            cleaned_data[key] = value
        
        return cleaned_data
    
    def _xpath_to_css(self, xpath: str) -> str:
        """Упрощенное преобразование XPath в CSS"""
        # Базовая конвертация
        css = xpath.replace('//', '').replace('[contains(@class, "', '[class*="')
        css = css.replace('[@class="', '[class="').replace('[@id="', '[id="')
        css = css.replace('/', ' > ')
        return css
