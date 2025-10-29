#!/usr/bin/env python3
"""
Анализатор трендов и паттернов цен
"""

import statistics
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json

from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class TrendAnalyzer:
    """Анализатор ценовых трендов и паттернов"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("trend_analyzer")
        
        self.analysis_settings = {
            'trend_period_days': 30,
            'seasonality_analysis': True,
            'volatility_threshold': 0.1,
            'min_data_points': 5
        }
        
        if 'trend_analysis' in self.config:
            self.analysis_settings.update(self.config['trend_analysis'])
    
    @retry_on_failure(max_retries=2)
    def analyze_price_trends(self, price_history: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Анализ ценовых трендов по всем товарам
        
        Args:
            price_history: История цен в формате {product_key: [{'date': ..., 'price': ...}]}
            
        Returns:
            Dict: Результаты анализа трендов
        """
        self.logger.info(f"📈 Анализ трендов для {len(price_history)} товаров")
        
        try:
            trends_analysis = {}
            
            for product_key, history in price_history.items():
                if len(history) >= self.analysis_settings['min_data_points']:
                    product_trend = self._analyze_product_trend(product_key, history)
                    trends_analysis[product_key] = product_trend
            
            # Агрегированная статистика
            summary = self._generate_trends_summary(trends_analysis)
            
            return {
                'success': True,
                'total_products_analyzed': len(trends_analysis),
                'trends_analysis': trends_analysis,
                'summary': summary,
                'market_insights': self._generate_market_insights(trends_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа трендов: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_product_trend(self, product_key: str, history: List[Dict]) -> Dict[str, Any]:
        """Анализ тренда для одного товара"""
        # Сортируем по дате
        sorted_history = sorted(history, key=lambda x: x['date'])
        
        prices = [point['price'] for point in sorted_history if point['price'] is not None]
        dates = [point['date'] for point in sorted_history]
        
        if len(prices) < 2:
            return {'trend': 'insufficient_data', 'reason': 'Недостаточно данных'}
        
        # Базовые метрики
        first_price = prices[0]
        last_price = prices[-1]
        min_price = min(prices)
        max_price = max(prices)
        
        # Процентное изменение
        if first_price > 0:
            total_change_percent = ((last_price - first_price) / first_price) * 100
        else:
            total_change_percent = 0
        
        # Определение тренда
        trend_direction = self._determine_trend_direction(prices)
        
        # Волатильность
        volatility = self._calculate_volatility(prices)
        
        # Сезонность (базовый анализ)
        seasonality = self._analyze_seasonality(prices, dates)
        
        return {
            'product_key': product_key,
            'trend_direction': trend_direction,
            'total_change_percent': total_change_percent,
            'total_change_amount': last_price - first_price,
            'volatility': volatility,
            'price_range': {
                'min': min_price,
                'max': max_price,
                'current': last_price
            },
            'seasonality': seasonality,
            'data_points': {
                'total': len(prices),
                'period_days': (datetime.fromisoformat(dates[-1]) - datetime.fromisoformat(dates[0])).days,
                'first_date': dates[0],
                'last_date': dates[-1]
            },
            'statistics': {
                'mean': statistics.mean(prices),
                'median': statistics.median(prices),
                'std_dev': statistics.stdev(prices) if len(prices) > 1 else 0
            }
        }
    
    def _determine_trend_direction(self, prices: List[float]) -> str:
        """Определение направления тренда"""
        if len(prices) < 3:
            return 'uncertain'
        
        # Простой анализ через линейную регрессию
        x = list(range(len(prices)))
        y = prices
        
        n = len(x)
        if n == 0:
            return 'uncertain'
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        except ZeroDivisionError:
            return 'uncertain'
        
        # Определяем тренд по углу наклона
        if slope > 0.01:
            return 'upward'
        elif slope < -0.01:
            return 'downward'
        else:
            return 'stable'
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Расчет волатильности цен"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return 0.0
        
        return statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    def _analyze_seasonality(self, prices: List[float], dates: List[str]) -> Dict[str, Any]:
        """Базовый анализ сезонности"""
        if len(prices) < 7:  # Минимум неделя данных
            return {'detected': False, 'confidence': 0}
        
        # Простая проверка: сравнение с предыдущим периодом
        # В реальной реализации здесь был бы более сложный анализ
        return {
            'detected': False,
            'confidence': 0,
            'pattern': 'none'
        }
    
    def _generate_trends_summary(self, trends_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация сводки по трендам"""
        if not trends_analysis:
            return {}
        
        directions = [analysis['trend_direction'] for analysis in trends_analysis.values()]
        changes = [analysis['total_change_percent'] for analysis in trends_analysis.values()]
        volatilities = [analysis['volatility'] for analysis in trends_analysis.values()]
        
        return {
            'trend_distribution': {
                'upward': directions.count('upward'),
                'downward': directions.count('downward'), 
                'stable': directions.count('stable'),
                'uncertain': directions.count('uncertain')
            },
            'price_changes': {
                'average_change': statistics.mean(changes) if changes else 0,
                'max_increase': max(changes) if changes else 0,
                'max_decrease': min(changes) if changes else 0,
                'positive_changes': sum(1 for c in changes if c > 0),
                'negative_changes': sum(1 for c in changes if c < 0)
            },
            'volatility_analysis': {
                'average_volatility': statistics.mean(volatilities) if volatilities else 0,
                'high_volatility_count': sum(1 for v in volatilities if v > self.analysis_settings['volatility_threshold']),
                'max_volatility': max(volatilities) if volatilities else 0
            }
        }
    
    def _generate_market_insights(self, trends_analysis: Dict[str, Any]) -> List[str]:
        """Генерация рыночных инсайтов"""
        insights = []
        summary = self._generate_trends_summary(trends_analysis)
        
        if not summary:
            return ["Недостаточно данных для анализа"]
        
        trend_dist = summary['trend_distribution']
        price_changes = summary['price_changes']
        
        # Анализ общего тренда
        total_products = sum(trend_dist.values())
        if trend_dist['upward'] > total_products * 0.6:
            insights.append("📈 Преобладает восходящий тренд цен")
        elif trend_dist['downward'] > total_products * 0.6:
            insights.append("📉 Преобладает нисходящий тренд цен")
        
        # Анализ волатильности
        if summary['volatility_analysis']['high_volatility_count'] > total_products * 0.3:
            insights.append("⚡ Высокая волатильность цен на рынке")
        
        # Анализ изменений
        if price_changes['positive_changes'] > price_changes['negative_changes'] * 1.5:
            insights.append("💹 Большинство товаров демонстрируют рост цен")
        elif price_changes['negative_changes'] > price_changes['positive_changes'] * 1.5:
            insights.append("🔻 Большинство товаров демонстрируют снижение цен")
        
        return insights
    
    def predict_future_prices(self, trends_analysis: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
        """
        Прогнозирование цен на основе трендов
        
        Args:
            trends_analysis: Результаты анализа трендов
            days: Количество дней для прогноза
            
        Returns:
            Dict: Прогнозы цен
        """
        self.logger.info(f"🔮 Прогнозирование цен на {days} дней")
        
        predictions = {}
        
        for product_key, analysis in trends_analysis.items():
            if analysis['trend_direction'] == 'insufficient_data':
                continue
                
            current_price = analysis['price_range']['current']
            trend = analysis['trend_direction']
            volatility = analysis['volatility']
            
            # Простой прогноз на основе тренда
            if trend == 'upward':
                predicted_change = analysis['total_change_percent'] / analysis['data_points']['period_days'] * days
            elif trend == 'downward':
                predicted_change = analysis['total_change_percent'] / analysis['data_points']['period_days'] * days
            else:
                predicted_change = 0
            
            predicted_price = current_price * (1 + predicted_change / 100)
            
            # Учет волатильности
            confidence = max(0.1, 1 - volatility * 10)  # Простая метрика уверенности
            
            predictions[product_key] = {
                'current_price': current_price,
                'predicted_price': predicted_price,
                'predicted_change_percent': predicted_change,
                'confidence': confidence,
                'trend': trend,
                'prediction_date': (datetime.now() + timedelta(days=days)).isoformat()
            }
        
        return {
            'success': True,
            'prediction_horizon_days': days,
            'predictions': predictions,
            'total_predictions': len(predictions)
        }
