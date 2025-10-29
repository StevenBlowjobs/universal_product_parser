#!/usr/bin/env python3
"""
Модуль валидации данных товаров
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class DataValidator:
    """Валидатор целостности и качества данных товаров"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("data_validator")
        
        # Критерии валидации
        self.validation_rules = {
            'min_name_length': 3,
            'max_name_length': 500,
            'min_price_value': 0,
            'max_price_value': 10000000,
            'required_fields': ['name', 'price', 'url'],
            'url_pattern': r'^https?://[^\s/$.?#].[^\s]*$',
            'allowed_image_formats': ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        }
    
    @retry_on_failure(max_retries=2)
    def validate_products(self, products: List[Dict]) -> Dict[str, Any]:
        """
        Валидация списка товаров
        
        Args:
            products: Список товаров для валидации
            
        Returns:
            Dict: Результаты валидации
        """
        self.logger.info(f"🔍 Валидация {len(products)} товаров")
        
        try:
            validation_results = {
                'total_products': len(products),
                'valid_products': [],
                'invalid_products': [],
                'validation_errors': {},
                'quality_metrics': {}
            }
            
            for i, product in enumerate(products):
                product_validation = self._validate_single_product(product)
                
                if product_validation['is_valid']:
                    validation_results['valid_products'].append({
                        'product': product,
                        'warnings': product_validation['warnings']
                    })
                else:
                    validation_results['invalid_products'].append({
                        'product': product,
                        'errors': product_validation['errors'],
                        'warnings': product_validation['warnings']
                    })
                    
                    # Статистика ошибок
                    for error in product_validation['errors']:
                        if error not in validation_results['validation_errors']:
                            validation_results['validation_errors'][error] = 0
                        validation_results['validation_errors'][error] += 1
            
            # Расчет метрик качества
            validation_results['quality_metrics'] = self._calculate_quality_metrics(validation_results)
            validation_results['success'] = True
            
            self.logger.info(f"✅ Валидация завершена: {len(validation_results['valid_products'])} валидных, "
                           f"{len(validation_results['invalid_products'])} невалидных")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации данных: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_products': len(products),
                'valid_products': [],
                'invalid_products': []
            }
    
    def _validate_single_product(self, product: Dict) -> Dict[str, Any]:
        """Валидация одного товара"""
        errors = []
        warnings = []
        
        # Проверка обязательных полей
        for field in self.validation_rules['required_fields']:
            if field not in product or not product[field]:
                errors.append(f"Отсутствует обязательное поле: {field}")
        
        # Валидация названия
        if 'name' in product:
            name_validation = self._validate_name(product['name'])
            errors.extend(name_validation['errors'])
            warnings.extend(name_validation['warnings'])
        
        # Валидация цены
        if 'price' in product:
            price_validation = self._validate_price(product['price'])
            errors.extend(price_validation['errors'])
            warnings.extend(price_validation['warnings'])
        
        # Валидация URL
        if 'url' in product:
            url_validation = self._validate_url(product['url'])
            errors.extend(url_validation['errors'])
            warnings.extend(url_validation['warnings'])
        
        # Валидация изображений
        if 'images' in product:
            images_validation = self._validate_images(product['images'])
            errors.extend(images_validation['errors'])
            warnings.extend(images_validation['warnings'])
        
        # Валидация характеристик
        if 'characteristics' in product:
            chars_validation = self._validate_characteristics(product['characteristics'])
            warnings.extend(chars_validation['warnings'])
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_name(self, name: str) -> Dict[str, List[str]]:
        """Валидация названия товара"""
        errors = []
        warnings = []
        
        if not isinstance(name, str):
            errors.append("Название должно быть строкой")
            return {'errors': errors, 'warnings': warnings}
        
        name = name.strip()
        
        # Проверка длины
        if len(name) < self.validation_rules['min_name_length']:
            errors.append(f"Название слишком короткое (мин. {self.validation_rules['min_name_length']} символов)")
        
        if len(name) > self.validation_rules['max_name_length']:
            warnings.append(f"Название очень длинное ({len(name)} символов)")
        
        # Проверка содержания
        if not any(char.isalnum() for char in name):
            errors.append("Название должно содержать буквы или цифры")
        
        # Проверка на мусорные символы
        if re.search(r'[^\w\s\-\.\,\!\?\(\)]', name):
            warnings.append("Название содержит специальные символы")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_price(self, price: Any) -> Dict[str, List[str]]:
        """Валидация цены"""
        errors = []
        warnings = []
        
        if price is None:
            errors.append("Цена не может быть None")
            return {'errors': errors, 'warnings': warnings}
        
        try:
            price_float = float(price)
        except (ValueError, TypeError):
            errors.append("Цена должна быть числом")
            return {'errors': errors, 'warnings': warnings}
        
        # Проверка диапазона
        if price_float < self.validation_rules['min_price_value']:
            errors.append(f"Цена не может быть отрицательной")
        
        if price_float > self.validation_rules['max_price_value']:
            warnings.append(f"Цена очень высокая: {price_float}")
        
        # Проверка на округление
        if price_float != round(price_float, 2):
            warnings.append("Цена имеет более 2 знаков после запятой")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_url(self, url: str) -> Dict[str, List[str]]:
        """Валидация URL"""
        errors = []
        warnings = []
        
        if not isinstance(url, str):
            errors.append("URL должен быть строкой")
            return {'errors': errors, 'warnings': warnings}
        
        url = url.strip()
        
        # Проверка формата URL
        if not re.match(self.validation_rules['url_pattern'], url):
            errors.append("Неверный формат URL")
        
        # Проверка длины URL
        if len(url) > 2000:
            warnings.append("URL очень длинный")
        
        # Проверка безопасных протоколов
        if not url.startswith(('http://', 'https://')):
            errors.append("URL должен использовать HTTP или HTTPS протокол")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_images(self, images: List[str]) -> Dict[str, List[str]]:
        """Валидация изображений"""
        errors = []
        warnings = []
        
        if not isinstance(images, list):
            errors.append("Изображения должны быть списком")
            return {'errors': errors, 'warnings': warnings}
        
        # Проверка количества изображений
        if len(images) == 0:
            warnings.append("Нет изображений товара")
        
        if len(images) > 20:
            warnings.append(f"Слишком много изображений: {len(images)}")
        
        # Валидация каждого URL изображения
        for i, img_url in enumerate(images):
            if not isinstance(img_url, str):
                errors.append(f"URL изображения {i} должен быть строкой")
                continue
            
            img_url = img_url.strip()
            
            # Проверка формата URL
            if not re.match(self.validation_rules['url_pattern'], img_url):
                errors.append(f"Неверный формат URL изображения {i}")
            
            # Проверка расширения файла
            img_lower = img_url.lower()
            has_valid_extension = any(img_lower.endswith(ext) for ext in self.validation_rules['allowed_image_formats'])
            
            if not has_valid_extension:
                warnings.append(f"Изображение {i} имеет нестандартное расширение: {img_url}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_characteristics(self, characteristics: Dict) -> Dict[str, List[str]]:
        """Валидация характеристик"""
        warnings = []
        
        if not isinstance(characteristics, dict):
            warnings.append("Характеристики должны быть словарем")
            return {'warnings': warnings}
        
        # Проверка на пустые характеристики
        if not characteristics:
            warnings.append("Нет характеристик товара")
        
        # Проверка длины ключей и значений
        for key, value in characteristics.items():
            if not isinstance(key, str):
                warnings.append(f"Ключ характеристики должен быть строкой: {key}")
                continue
            
            if len(key) > 100:
                warnings.append(f"Слишком длинный ключ характеристики: {key}")
            
            if isinstance(value, str) and len(value) > 500:
                warnings.append(f"Слишком длинное значение характеристики '{key}': {value}")
        
        return {'warnings': warnings}
    
    def _calculate_quality_metrics(self, validation_results: Dict[str, Any]) -> Dict[str, float]:
        """Расчет метрик качества данных"""
        total_products = validation_results['total_products']
        valid_products = len(validation_results['valid_products'])
        invalid_products = len(validation_results['invalid_products'])
        
        if total_products == 0:
            return {
                'completeness_score': 0,
                'validity_score': 0,
                'quality_score': 0
            }
        
        # Оценка полноты данных
        completeness_score = valid_products / total_products
        
        # Оценка валидности
        validity_score = valid_products / total_products
        
        # Общая оценка качества
        quality_score = (completeness_score + validity_score) / 2
        
        return {
            'completeness_score': completeness_score,
            'validity_score': validity_score,
            'quality_score': quality_score,
            'valid_products_count': valid_products,
            'invalid_products_count': invalid_products
        }
    
    def generate_validation_report(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация отчета о валидации"""
        metrics = validation_results['quality_metrics']
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_products': validation_results['total_products'],
                'valid_products': len(validation_results['valid_products']),
                'invalid_products': len(validation_results['invalid_products']),
                'data_quality_score': metrics['quality_score']
            },
            'common_errors': validation_results['validation_errors'],
            'recommendations': self._generate_recommendations(validation_results)
        }
        
        return report
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций по улучшению данных"""
        recommendations = []
        metrics = validation_results['quality_metrics']
        
        if metrics['quality_score'] < 0.8:
            recommendations.append("Улучшите качество данных: проверьте обязательные поля и форматы")
        
        if validation_results['validation_errors']:
            common_errors = list(validation_results['validation_errors'].keys())[:3]
            recommendations.append(f"Исправьте частые ошибки: {', '.join(common_errors)}")
        
        if metrics['completeness_score'] < 0.9:
            recommendations.append("Увеличьте полноту данных: добавьте недостающие поля")
        
        return recommendations
