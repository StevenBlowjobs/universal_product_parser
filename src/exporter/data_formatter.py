#!/usr/bin/env python3
"""
Форматирование данных для экспорта
"""

import re
from typing import Dict, List, Any, Union
from datetime import datetime

from ..utils.logger import setup_logger


class DataFormatter:
    """Форматировщик данных для различных форматов экспорта"""
    
    def __init__(self):
        self.logger = setup_logger("data_formatter")
    
    def format_products_for_export(self, products: List[Dict]) -> List[Dict]:
        """
        Форматирование товаров для экспорта
        
        Args:
            products: Сырые данные товаров
            
        Returns:
            List[Dict]: Отформатированные данные
        """
        formatted_products = []
        
        for product in products:
            formatted_product = {
                'Название': self._format_name(product.get('name', '')),
                'Цена': self._format_price(product.get('price')),
                'Описание': self._format_description(product.get('description', '')),
                'Категория': product.get('category', ''),
                'URL товара': product.get('url', ''),
                'URL изображения': product.get('image_url', ''),
                'Артикул': product.get('sku', ''),
                'Наличие': self._format_availability(product.get('availability')),
                'Рейтинг': product.get('rating', ''),
                'Количество отзывов': product.get('review_count', ''),
                'Бренд': product.get('brand', ''),
                'Производитель': product.get('manufacturer', '')
            }
            
            # Характеристики
            characteristics = product.get('characteristics', {})
            for key, value in characteristics.items():
                formatted_key = self._format_characteristic_key(key)
                formatted_product[formatted_key] = self._format_characteristic_value(value)
            
            formatted_products.append(formatted_product)
        
        return formatted_products
    
    def _format_name(self, name: str) -> str:
        """Форматирование названия"""
        if not name:
            return "Без названия"
        
        # Удаление лишних пробелов и переносов
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Обрезка слишком длинных названий
        if len(name) > 200:
            name = name[:197] + "..."
        
        return name
    
    def _format_price(self, price: Any) -> Union[float, str]:
        """Форматирование цены"""
        if price is None:
            return "Нет данных"
        
        try:
            # Попытка преобразовать в число
            if isinstance(price, (int, float)):
                return float(price)
            elif isinstance(price, str):
                # Извлечение числа из строки
                price_clean = re.sub(r'[^\d,.]', '', price.replace(',', '.'))
                if price_clean:
                    return float(price_clean)
        except (ValueError, TypeError):
            pass
        
        return "Неверный формат"
    
    def _format_description(self, description: str) -> str:
        """Форматирование описания"""
        if not description:
            return ""
        
        # Очистка описания
        description = re.sub(r'\s+', ' ', description.strip())
        
        # Обрезка слишком длинных описаний
        if len(description) > 500:
            description = description[:497] + "..."
        
        return description
    
    def _format_availability(self, availability: Any) -> str:
        """Форматирование наличия"""
        if availability is None:
            return "Неизвестно"
        
        if isinstance(availability, dict):
            status = availability.get('status', '')
            if status:
                status_map = {
                    'in_stock': 'В наличии',
                    'out_of_stock': 'Нет в наличии',
                    'preorder': 'Предзаказ',
                    'available': 'В наличии',
                    'unavailable': 'Нет в наличии'
                }
                return status_map.get(status.lower(), status)
        
        if isinstance(availability, str):
            availability_lower = availability.lower()
            if 'есть' in availability_lower or 'в наличии' in availability_lower or 'available' in availability_lower:
                return 'В наличии'
            elif 'нет' in availability_lower or 'распродано' in availability_lower or 'out of stock' in availability_lower:
                return 'Нет в наличии'
        
        return str(availability)
    
    def _format_characteristic_key(self, key: str) -> str:
        """Форматирование ключа характеристики"""
        if not key:
            return "Характеристика"
        
        # Приведение к читаемому виду
        key = str(key).strip()
        key = key[0].upper() + key[1:] if key else key
        
        # Замена подчеркиваний на пробелы
        key = key.replace('_', ' ')
        
        return key
    
    def _format_characteristic_value(self, value: Any) -> str:
        """Форматирование значения характеристики"""
        if value is None:
            return ""
        
        if isinstance(value, (list, dict)):
            return str(value)
        
        return str(value).strip()
    
    def format_for_comparison(self, comparison_data: Dict[str, Any]) -> List[Dict]:
        """
        Форматирование данных сравнения для экспорта
        
        Args:
            comparison_data: Данные сравнения цен
            
        Returns:
            List[Dict]: Отформатированные данные сравнения
        """
        formatted_data = []
        
        for changed_product in comparison_data.get('changed_products', []):
            price_change = changed_product.get('price_change', {})
            
            formatted_data.append({
                'Товар': changed_product.get('name', ''),
                'Статус': 'Изменение цены',
                'Старая цена': price_change.get('old_price'),
                'Новая цена': price_change.get('new_price'),
                'Разница': price_change.get('change_amount'),
                'Изменение %': f"{price_change.get('change_percent', 0):.2f}%",
                'Направление': 'Увеличение' if price_change.get('change_direction') == 'increase' else 'Снижение',
                'Значимость': 'Высокая' if price_change.get('significant') else 'Низкая'
            })
        
        return formatted_data
