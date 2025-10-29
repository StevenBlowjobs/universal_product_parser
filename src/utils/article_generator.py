#!/usr/bin/env python3
"""
Система генерации артикулов для товаров
"""

import hashlib
import uuid
from typing import Dict, Any

class ArticleGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.article_cache = {}
    
    def generate_article(self, product_data: Dict[str, Any]) -> str:
        """Генерация уникального артикула на основе данных товара"""
        
        # Стратегия 1: на основе хеша ключевых характеристик
        if self.config.get('hash_based', True):
            return self._generate_hash_article(product_data)
        
        # Стратегия 2: комбинированная (категория + характеристики)
        elif self.config.get('composite_based', False):
            return self._generate_composite_article(product_data)
        
        # Стратегия 3: последовательная нумерация
        else:
            return self._generate_sequential_article(product_data)
    
    def _generate_hash_article(self, product_data: Dict[str, Any]) -> str:
        """Генерация артикула на основе хеша данных"""
        key_string = f"{product_data.get('name', '')}{product_data.get('category', '')}{str(product_data.get('characteristics', {}))}"
        
        # Создаем хеш
        hash_object = hashlib.md5(key_string.encode())
        hash_hex = hash_object.hexdigest()[:8].upper()
        
        # Добавляем префикс категории
        category_prefix = self._get_category_prefix(product_data.get('category', 'GEN'))
        return f"{category_prefix}-{hash_hex}"
    
    def _generate_composite_article(self, product_data: Dict[str, Any]) -> str:
        """Комбинированный артикул (категория + бренд + характеристики)"""
        category = product_data.get('category', 'GEN')
        brand = self._extract_brand(product_data.get('name', '') + product_data.get('description', ''))
        
        # Нормализуем значения
        category_code = self._normalize_category(category)
        brand_code = self._normalize_brand(brand)
        
        # Генерируем уникальную часть
        unique_part = hashlib.md5(
            f"{product_data.get('name', '')}{product_data.get('price', 0)}".encode()
        ).hexdigest()[:4].upper()
        
        return f"{category_code}-{brand_code}-{unique_part}"
    
    def _generate_sequential_article(self, product_data: Dict[str, Any]) -> str:
        """Последовательная нумерация с кешированием"""
        category = product_data.get('category', 'GEN')
        product_key = self._create_product_key(product_data)
        
        if product_key not in self.article_cache:
            next_number = len(self.article_cache) + 1
            self.article_cache[product_key] = f"ART-{next_number:06d}"
        
        return self.article_cache[product_key]
    
    def _get_category_prefix(self, category: str) -> str:
        """Получение префикса категории"""
        category_map = {
            'ноутбук': 'NB', 'телефон': 'PH', 'телевизор': 'TV',
            'холодильник': 'FR', 'стиральная': 'WM', 'мебель': 'FRN'
        }
        
        category_lower = category.lower()
        for key, prefix in category_map.items():
            if key in category_lower:
                return prefix
        return 'GEN'
    
    def _extract_brand(self, text: str) -> str:
        """Извлечение бренда из текста"""
        common_brands = ['samsung', 'apple', 'xiaomi', 'lenovo', 'lg', 'sony', 'huawei']
        text_lower = text.lower()
        
        for brand in common_brands:
            if brand in text_lower:
                return brand
        return 'UNK'
    
    def _normalize_category(self, category: str) -> str:
        """Нормализация категории для кода"""
        return category[:3].upper() if len(category) >= 3 else category.upper()
    
    def _normalize_brand(self, brand: str) -> str:
        """Нормализация бренда для кода"""
        return brand[:3].upper() if len(brand) >= 3 else brand.upper()
    
    def _create_product_key(self, product_data: Dict[str, Any]) -> str:
        """Создание ключа товара для кеширования"""
        return f"{product_data.get('name', '')}_{product_data.get('category', '')}"
