#!/usr/bin/env python3
"""
Модуль сравнения цен и анализа изменений
"""

import json
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure
from ..utils.file_manager import FileManager


class PriceComparator:
    """Анализатор изменений цен и наличия товаров"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("price_comparator")
        self.file_manager = FileManager()
        
        # Настройки сравнения
        self.comparison_settings = {
            'price_change_threshold': 0.05,  # 5% изменение
            'significant_change_threshold': 0.15,  # 15% значительное изменение
            'max_price_difference': 10.0,  # Максимальная абсолютная разница
            'tracking_period_days': 30,
            'min_comparison_samples': 2
        }
        
        if 'analysis' in self.config:
            self.comparison_settings.update(self.config['analysis'])
    
    @retry_on_failure(max_retries=2)
    def compare_prices(self, current_data: List[Dict], previous_data: List[Dict] = None, 
                     previous_file_path: str = None) -> Dict[str, Any]:
        """
        Сравнение текущих данных с предыдущими
        
        Args:
            current_data: Текущие данные товаров
            previous_data: Предыдущие данные товаров (опционально)
            previous_file_path: Путь к файлу с предыдущими данными (опционально)
            
        Returns:
            Dict: Результаты сравнения
        """
        self.logger.info("📊 Сравнение цен и наличия товаров")
        
        try:
            # Загрузка предыдущих данных если нужно
            if previous_data is None and previous_file_path:
                previous_data = self._load_previous_data(previous_file_path)
            
            if previous_data is None:
                return self._create_initial_comparison(current_data)
            
            # Сравнение данных
            comparison_results = self._perform_comparison(current_data, previous_data)
            
            # Сохранение результатов сравнения
            self._save_comparison_results(comparison_results)
            
            self.logger.info(f"✅ Сравнение завершено: {len(comparison_results['changed_products'])} изменений")
            
            return comparison_results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сравнения цен: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_products': len(current_data),
                'changed_products': []
            }
    
    def _load_previous_data(self, file_path: str) -> Optional[List[Dict]]:
        """Загрузка предыдущих данных из файла"""
        try:
            if file_path.endswith('.json'):
                return self.file_manager.load_json(Path(file_path).stem, 'output')
            elif file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
                return df.to_dict('records')
            else:
                self.logger.warning(f"⚠️  Неподдерживаемый формат файла: {file_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки предыдущих данных: {e}")
            return None
    
    def _create_initial_comparison(self, current_data: List[Dict]) -> Dict[str, Any]:
        """Создание начального сравнения (первый запуск)"""
        self.logger.info("🆕 Первый запуск - создание базовой линии")
        
        return {
            'success': True,
            'is_initial': True,
            'total_products': len(current_data),
            'changed_products': [],
            'new_products': current_data,
            'discontinued_products': [],
            'price_changes': {
                'increased': 0,
                'decreased': 0,
                'unchanged': len(current_data)
            },
            'summary': {
                'total_changes': 0,
                'price_changes_count': 0,
                'availability_changes_count': 0,
                'new_products_count': len(current_data),
                'discontinued_count': 0
            }
        }
    
    def _perform_comparison(self, current_data: List[Dict], previous_data: List[Dict]) -> Dict[str, Any]:
        """Выполнение сравнения данных"""
        # Создание словарей для быстрого поиска
        current_dict = {self._get_product_key(product): product for product in current_data}
        previous_dict = {self._get_product_key(product): product for product in previous_data}
        
        changed_products = []
        new_products = []
        discontinued_products = []
        
        price_increases = 0
        price_decreases = 0
        price_unchanged = 0
        
        # Поиск изменений в существующих товарах
        for product_key, current_product in current_dict.items():
            if product_key in previous_dict:
                previous_product = previous_dict[product_key]
                
                changes = self._compare_single_product(current_product, previous_product)
                if changes['has_changes']:
                    changed_products.append(changes)
                    
                    # Статистика по ценам
                    if changes['price_change']['changed']:
                        if changes['price_change']['change_percent'] > 0:
                            price_increases += 1
                        else:
                            price_decreases += 1
                    else:
                        price_unchanged += 1
                else:
                    price_unchanged += 1
            else:
                # Новый товар
                new_products.append(current_product)
        
        # Поиск отсутствующих товаров
        for product_key, previous_product in previous_dict.items():
            if product_key not in current_dict:
                discontinued_products.append(previous_product)
        
        return {
            'success': True,
            'is_initial': False,
            'total_products': len(current_data),
            'changed_products': changed_products,
            'new_products': new_products,
            'discontinued_products': discontinued_products,
            'price_changes': {
                'increased': price_increases,
                'decreased': price_decreases,
                'unchanged': price_unchanged
            },
            'summary': {
                'total_changes': len(changed_products) + len(new_products) + len(discontinued_products),
                'price_changes_count': price_increases + price_decreases,
                'availability_changes_count': len(new_products) + len(discontinued_products),
                'new_products_count': len(new_products),
                'discontinued_count': len(discontinued_products),
                'comparison_timestamp': datetime.now().isoformat()
            }
        }
    
    def _get_product_key(self, product: Dict) -> str:
        """Создание уникального ключа товара"""
        # Комбинация названия, артикула и характеристик для уникальности
        name = product.get('name', '')
        sku = product.get('sku', '')
        url = product.get('url', '')
        
        return f"{name}_{sku}_{hash(url) % 10000:04d}"
    
    def _compare_single_product(self, current: Dict, previous: Dict) -> Dict[str, Any]:
        """Сравнение одного товара"""
        changes = {
            'product_key': self._get_product_key(current),
            'name': current.get('name', ''),
            'url': current.get('url', ''),
            'has_changes': False,
            'changes': [],
            'price_change': self._compare_price(current, previous),
            'availability_change': self._compare_availability(current, previous),
            'characteristics_changes': self._compare_characteristics(current, previous),
            'images_changes': self._compare_images(current, previous)
        }
        
        # Проверка наличия изменений
        changes['has_changes'] = (
            changes['price_change']['changed'] or
            changes['availability_change']['changed'] or
            changes['characteristics_changes']['has_changes'] or
            changes['images_changes']['has_changes']
        )
        
        # Сбор всех изменений в один список
        if changes['price_change']['changed']:
            changes['changes'].append({
                'field': 'price',
                'old_value': changes['price_change']['old_price'],
                'new_value': changes['price_change']['new_price'],
                'change_percent': changes['price_change']['change_percent']
            })
        
        if changes['availability_change']['changed']:
            changes['changes'].append({
                'field': 'availability',
                'old_value': changes['availability_change']['old_status'],
                'new_value': changes['availability_change']['new_status']
            })
        
        if changes['characteristics_changes']['has_changes']:
            for char_change in changes['characteristics_changes']['changes']:
                changes['changes'].append({
                    'field': f"characteristic_{char_change['key']}",
                    'old_value': char_change['old_value'],
                    'new_value': char_change['new_value']
                })
        
        return changes
    
    def _compare_price(self, current: Dict, previous: Dict) -> Dict[str, Any]:
        """Сравнение цен"""
        current_price = current.get('price')
        previous_price = previous.get('price')
        
        if current_price is None or previous_price is None:
            return {
                'changed': False,
                'old_price': previous_price,
                'new_price': current_price,
                'change_amount': 0,
                'change_percent': 0
            }
        
        change_amount = current_price - previous_price
        
        if previous_price != 0:
            change_percent = (change_amount / abs(previous_price)) * 100
        else:
            change_percent = 100 if current_price != 0 else 0
        
        # Определение значительности изменения
        is_significant = abs(change_percent) >= self.comparison_settings['significant_change_threshold'] * 100
        is_changed = abs(change_percent) >= self.comparison_settings['price_change_threshold'] * 100
        
        return {
            'changed': is_changed,
            'significant': is_significant,
            'old_price': previous_price,
            'new_price': current_price,
            'change_amount': change_amount,
            'change_percent': change_percent,
            'change_direction': 'increase' if change_amount > 0 else 'decrease' if change_amount < 0 else 'unchanged'
        }
    
    def _compare_availability(self, current: Dict, previous: Dict) -> Dict[str, Any]:
        """Сравнение наличия товара"""
        current_avail = current.get('availability', {})
        previous_avail = previous.get('availability', {})
        
        if isinstance(current_avail, dict):
            current_status = current_avail.get('status', 'unknown')
        else:
            current_status = str(current_avail)
        
        if isinstance(previous_avail, dict):
            previous_status = previous_avail.get('status', 'unknown')
        else:
            previous_status = str(previous_avail)
        
        changed = current_status != previous_status
        
        return {
            'changed': changed,
            'old_status': previous_status,
            'new_status': current_status
        }
    
    def _compare_characteristics(self, current: Dict, previous: Dict) -> Dict[str, Any]:
        """Сравнение характеристик"""
        current_chars = current.get('characteristics', {})
        previous_chars = previous.get('characteristics', {})
        
        changes = []
        all_keys = set(current_chars.keys()) | set(previous_chars.keys())
        
        for key in all_keys:
            current_val = current_chars.get(key)
            previous_val = previous_chars.get(key)
            
            if current_val != previous_val:
                changes.append({
                    'key': key,
                    'old_value': previous_val,
                    'new_value': current_val
                })
        
        return {
            'has_changes': len(changes) > 0,
            'changes': changes,
            'total_changes': len(changes)
        }
    
    def _compare_images(self, current: Dict, previous: Dict) -> Dict[str, Any]:
        """Сравнение изображений"""
        current_images = current.get('images', [])
        previous_images = previous.get('images', [])
        
        # Простая проверка по количеству изображений
        changed = len(current_images) != len(previous_images)
        
        return {
            'has_changes': changed,
            'old_count': len(previous_images),
            'new_count': len(current_images)
        }
    
    def _save_comparison_results(self, results: Dict[str, Any]):
        """Сохранение результатов сравнения"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"price_comparison_{timestamp}"
            
            self.file_manager.save_json(results, filename, 'output/analysis')
            self.logger.info(f"💾 Результаты сравнения сохранены: {filename}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения результатов сравнения: {e}")
    
    def get_price_trends(self, product_data: List[Dict], period_days: int = 30) -> Dict[str, Any]:
        """
        Анализ ценовых трендов
        
        Args:
            product_data: Данные товаров за период
            period_days: Период анализа в днях
            
        Returns:
            Dict: Анализ трендов
        """
        self.logger.info(f"📈 Анализ ценовых трендов за {period_days} дней")
        
        try:
            # Группировка данных по товарам
            products_trends = {}
            
            for product in product_data:
                product_key = self._get_product_key(product)
                if product_key not in products_trends:
                    products_trends[product_key] = []
                
                products_trends[product_key].append({
                    'timestamp': product.get('timestamp', datetime.now()),
                    'price': product.get('price'),
                    'availability': product.get('availability')
                })
            
            # Анализ трендов для каждого товара
            trends_analysis = {}
            for product_key, history in products_trends.items():
                if len(history) >= 2:
                    trends_analysis[product_key] = self._analyze_product_trend(history)
            
            return {
                'success': True,
                'total_products_analyzed': len(trends_analysis),
                'trends_analysis': trends_analysis,
                'summary': self._summarize_trends(trends_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа трендов: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_product_trend(self, history: List[Dict]) -> Dict[str, Any]:
        """Анализ тренда для одного товара"""
        # Сортировка по времени
        history.sort(key=lambda x: x['timestamp'])
        
        prices = [point['price'] for point in history if point['price'] is not None]
        
        if len(prices) < 2:
            return {'trend': 'insufficient_data'}
        
        # Простой анализ тренда
        first_price = prices[0]
        last_price = prices[-1]
        price_change = last_price - first_price
        
        if first_price != 0:
            change_percent = (price_change / first_price) * 100
        else:
            change_percent = 0
        
        # Определение тренда
        if abs(change_percent) < 2:
            trend = 'stable'
        elif change_percent > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        # Волатильность
        price_std = np.std(prices) if len(prices) > 1 else 0
        
        return {
            'trend': trend,
            'price_change_percent': change_percent,
            'price_change_amount': price_change,
            'volatility': price_std,
            'first_price': first_price,
            'last_price': last_price,
            'data_points': len(prices),
            'analysis_period': (history[-1]['timestamp'] - history[0]['timestamp']).days
        }
    
    def _summarize_trends(self, trends_analysis: Dict[str, Any]) -> Dict[str, int]:
        """Сводка по трендам"""
        trend_counts = {
            'increasing': 0,
            'decreasing': 0,
            'stable': 0,
            'insufficient_data': 0
        }
        
        for product_analysis in trends_analysis.values():
            trend = product_analysis.get('trend', 'insufficient_data')
            trend_counts[trend] += 1
        
        return trend_counts
