#!/usr/bin/env python3
"""
Модуль нормализации и стандартизации данных
"""

import re
from typing import Dict, List, Optional, Any, Union
from .logger import setup_logger


class DataNormalizer:
    """Нормализатор данных товаров"""
    
    def __init__(self):
        self.logger = setup_logger("normalizer")
        self.unit_conversions = self._load_unit_conversions()
        
    def _load_unit_conversions(self) -> Dict[str, Dict[str, float]]:
        """Загрузка коэффициентов конвертации единиц"""
        return {
            'length': {
                'mm': 1.0,
                'cm': 10.0,
                'm': 1000.0,
                'in': 25.4,
                'ft': 304.8
            },
            'weight': {
                'g': 1.0,
                'kg': 1000.0,
                'lb': 453.592,
                'oz': 28.3495
            },
            'volume': {
                'l': 1.0,
                'ml': 0.001,
                'gal': 3.78541,
                'm3': 1000.0
            }
        }
    
    def normalize_characteristics(self, characteristics: Dict[str, str]) -> Dict[str, Any]:
        """
        Нормализация характеристик товара
        
        Args:
            characteristics: Словарь характеристик
            
        Returns:
            Dict[str, Any]: Нормализованные характеристики
        """
        normalized = {}
        
        for key, value in characteristics.items():
            try:
                normalized_key = self._normalize_key(key)
                normalized_value = self._normalize_value(normalized_key, value)
                
                if normalized_value is not None:
                    normalized[normalized_key] = normalized_value
                    
            except Exception as e:
                self.logger.debug(f"Ошибка нормализации {key}: {e}")
                # Сохраняем оригинальное значение в случае ошибки
                normalized[key] = value
        
        return normalized
    
    def _normalize_key(self, key: str) -> str:
        """Нормализация ключа характеристики"""
        key_lower = key.lower().strip()
        
        # Словарь синонимов для стандартизации ключей
        key_mappings = {
            # Вес
            'вес': 'weight',
            'масса': 'weight',
            'weight': 'weight',
            'mass': 'weight',
            
            # Размеры
            'размер': 'dimensions',
            'габариты': 'dimensions',
            'dimensions': 'dimensions',
            'размеры': 'dimensions',
            
            # Длина
            'длина': 'length',
            'length': 'length',
            
            # Ширина
            'ширина': 'width', 
            'width': 'width',
            
            # Высота
            'высота': 'height',
            'height': 'height',
            
            # Объем
            'объем': 'volume',
            'ёмкость': 'volume',
            'volume': 'volume',
            'capacity': 'volume',
            
            # Цвет
            'цвет': 'color',
            'colour': 'color',
            'color': 'color',
            
            # Материал
            'материал': 'material',
            'material': 'material',
            
            # Производитель
            'производитель': 'manufacturer',
            'бренд': 'manufacturer',
            'manufacturer': 'manufacturer',
            'brand': 'manufacturer',
            
            # Страна
            'страна': 'country',
            'country': 'country',
            'страна происхождения': 'country',
            
            # Артикул
            'артикул': 'sku',
            'код товара': 'sku',
            'sku': 'sku',
            'article': 'sku',
            
            # Модель
            'модель': 'model',
            'model': 'model',
        }
        
        return key_mappings.get(key_lower, key_lower)
    
    def _normalize_value(self, key: str, value: str) -> Any:
        """Нормализация значения характеристики"""
        if not value or not isinstance(value, str):
            return value
        
        value = value.strip()
        
        # Обработка в зависимости от типа характеристики
        if key in ['weight', 'mass']:
            return self._normalize_weight(value)
        elif key in ['length', 'width', 'height', 'dimensions']:
            return self._normalize_dimensions(value)
        elif key == 'volume':
            return self._normalize_volume(value)
        elif key == 'color':
            return self._normalize_color(value)
        elif key in ['price', 'cost']:
            return self._normalize_price(value)
        elif key == 'availability':
            return self._normalize_availability(value)
        else:
            # Общая нормализация текста
            return self._normalize_text(value)
    
    def _normalize_weight(self, value: str) -> Optional[float]:
        """Нормализация веса в граммы"""
        try:
            # Поиск числового значения и единицы измерения
            pattern = r'(\d+[.,]?\d*)\s*([a-zA-Zа-яА-Я]*)'
            match = re.search(pattern, value)
            
            if not match:
                return None
            
            number = float(match.group(1).replace(',', '.'))
            unit = match.group(2).lower()
            
            # Определение коэффициента конвертации
            if unit in ['g', 'г', 'гр', 'gram', 'gramm']:
                factor = 1.0
            elif unit in ['kg', 'кг', 'kilogram', 'килограмм']:
                factor = 1000.0
            elif unit in ['lb', 'фунт', 'pound']:
                factor = 453.592
            elif unit in ['oz', 'унция', 'ounce']:
                factor = 28.3495
            else:
                # Если единица не указана, предполагаем граммы
                factor = 1.0
            
            return round(number * factor, 2)
            
        except (ValueError, TypeError):
            return None
    
    def _normalize_dimensions(self, value: str) -> Optional[Dict[str, float]]:
        """Нормализация размеров в миллиметры"""
        try:
            # Различные форматы размеров: 100x200x300, 100*200*300, 100×200×300
            patterns = [
                r'(\d+[.,]?\d*)\s*[x×*]\s*(\d+[.,]?\d*)\s*[x×*]\s*(\d+[.,]?\d*)\s*([a-zA-Zа-яА-Я]*)',
                r'(\d+[.,]?\d*)\s*[x×*]\s*(\d+[.,]?\d*)\s*([a-zA-Zа-яА-Я]*)',
                r'(\d+[.,]?\d*)\s*([a-zA-Zа-яА-Я]*)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, value)
                if match:
                    groups = match.groups()
                    numbers = [float(g.replace(',', '.')) for g in groups if g and g.replace(',', '').replace('.', '').isdigit()]
                    unit = next((g for g in groups if g and not g.replace(',', '').replace('.', '').isdigit()), '').lower()
                    
                    if numbers:
                        # Конвертация в мм
                        factor = self._get_length_factor(unit)
                        dimensions_mm = [round(n * factor, 2) for n in numbers]
                        
                        if len(dimensions_mm) == 3:
                            return {'length': dimensions_mm[0], 'width': dimensions_mm[1], 'height': dimensions_mm[2]}
                        elif len(dimensions_mm) == 2:
                            return {'length': dimensions_mm[0], 'width': dimensions_mm[1]}
                        else:
                            return dimensions_mm[0]
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    def _normalize_volume(self, value: str) -> Optional[float]:
        """Нормализация объема в литры"""
        try:
            pattern = r'(\d+[.,]?\d*)\s*([a-zA-Zа-яА-Я]*)'
            match = re.search(pattern, value)
            
            if not match:
                return None
            
            number = float(match.group(1).replace(',', '.'))
            unit = match.group(2).lower()
            
            # Определение коэффициента конвертации
            if unit in ['l', 'л', 'литр', 'liter', 'litre']:
                factor = 1.0
            elif unit in ['ml', 'мл', 'миллилитр', 'milliliter']:
                factor = 0.001
            elif unit in ['gal', 'галлон', 'gallon']:
                factor = 3.78541
            elif unit in ['m3', 'м3', 'кубометр']:
                factor = 1000.0
            else:
                factor = 1.0  # Предполагаем литры
            
            return round(number * factor, 3)
            
        except (ValueError, TypeError):
            return None
    
    def _normalize_color(self, value: str) -> str:
        """Нормализация цвета"""
        color_mappings = {
            'черный': 'black',
            'белый': 'white', 
            'красный': 'red',
            'синий': 'blue',
            'зеленый': 'green',
            'желтый': 'yellow',
            'оранжевый': 'orange',
            'фиолетовый': 'purple',
            'розовый': 'pink',
            'серый': 'gray',
            'коричневый': 'brown',
            'голубой': 'lightblue',
            'серебристый': 'silver',
            'золотой': 'gold'
        }
        
        value_lower = value.lower()
        return color_mappings.get(value_lower, value)
    
    def _normalize_price(self, value: str) -> Optional[float]:
        """Нормализация цены"""
        try:
            # Удаление всех нецифровых символов кроме точки и запятой
            clean_value = re.sub(r'[^\d,.]', '', value)
            clean_value = clean_value.replace(',', '.')
            
            # Поиск числового значения
            match = re.search(r'\d+\.?\d*', clean_value)
            if match:
                return float(match.group())
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    def _normalize_availability(self, value: str) -> str:
        """Нормализация статуса наличия"""
        value_lower = value.lower()
        
        in_stock_indicators = ['в наличии', 'есть', 'available', 'in stock', 'на складе']
        out_of_stock_indicators = ['нет в наличии', 'распродано', 'out of stock', 'sold out']
        
        if any(indicator in value_lower for indicator in in_stock_indicators):
            return 'in_stock'
        elif any(indicator in value_lower for indicator in out_of_stock_indicators):
            return 'out_of_stock'
        else:
            return 'unknown'
    
    def _normalize_text(self, value: str) -> str:
        """Общая нормализация текста"""
        # Удаление лишних пробелов и переносов строк
        value = re.sub(r'\s+', ' ', value).strip()
        
        # Стандартизация регистра для определенных полей
        if value.isupper():
            value = value.title()
        
        return value
    
    def _get_length_factor(self, unit: str) -> float:
        """Получение коэффициента конвертации для длины"""
        unit_mappings = {
            'mm': 1.0, 'мм': 1.0, 'millimeter': 1.0, 'миллиметр': 1.0,
            'cm': 10.0, 'см': 10.0, 'centimeter': 10.0, 'сантиметр': 10.0,
            'm': 1000.0, 'м': 1000.0, 'meter': 1000.0, 'метр': 1000.0,
            'in': 25.4, 'дюйм': 25.4, 'inch': 25.4,
            'ft': 304.8, 'фут': 304.8, 'foot': 304.8
        }
        
        return unit_mappings.get(unit.lower(), 1.0)  # По умолчанию мм
    
    def normalize_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Полная нормализация данных товара"""
        normalized = product_data.copy()
        
        # Нормализация характеристик
        if 'characteristics' in normalized:
            normalized['characteristics'] = self.normalize_characteristics(
                normalized['characteristics']
            )
        
        # Нормализация цены
        if 'price' in normalized and isinstance(normalized['price'], str):
            normalized['price'] = self._normalize_price(normalized['price'])
        
        # Нормализация наличия
        if 'availability' in normalized and isinstance(normalized['availability'], str):
            if isinstance(normalized['availability'], dict):
                # Если availability уже словарь, нормализуем текстовое поле
                if 'text' in normalized['availability']:
                    normalized['availability']['status'] = self._normalize_availability(
                        normalized['availability']['text']
                    )
            else:
                normalized['availability'] = {
                    'status': self._normalize_availability(normalized['availability']),
                    'text': normalized['availability']
                }
        
        return normalized
