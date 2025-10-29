#!/usr/bin/env python3
"""
Главный CLI интерфейс Universal Product Parser
Полная интеграция всех модулей
"""

import asyncio
import sys
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Добавляем путь к корню проекта для импортов
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.adaptive_parser import AdaptiveProductParser
from src.content_processor.text_rewriter import TextRewriter
from src.data_analyzer.data_validator import DataValidator
from src.data_analyzer.price_comparator import PriceComparator
from src.data_analyzer.trend_analyzer import TrendAnalyzer
from src.data_analyzer.alert_system import AlertSystem
from src.exporter.excel_generator import ExcelGenerator
from src.exporter.backup_manager import BackupManager
from src.utils.logger import setup_logger
from src.utils.file_manager import FileManager
from src.utils.error_handler import ParserError, handle_global_error
from .argument_parser import create_parser


class ParserCLI:
    """Командный интерфейс для управления парсером с полной интеграцией модулей"""
    
    def __init__(self):
        self.logger = setup_logger("cli")
        self.file_manager = FileManager()
        self.parser = None
        self.target_url = ""
        
        # Инициализация модулей (ленивая загрузка)
        self._modules_initialized = False
        self.text_rewriter = None
        self.data_validator = None
        self.price_comparator = None
        self.trend_analyzer = None
        self.alert_system = None
        self.excel_generator = None
        self.backup_manager = None
    
    def _initialize_modules(self, config: Dict[str, Any] = None):
        """Ленивая инициализация всех модулей"""
        if self._modules_initialized:
            return
            
        config = config or {}
        
        # Инициализация модулей обработки контента
        self.text_rewriter = TextRewriter(config)
        
        # Инициализация модулей анализа данных
        self.data_validator = DataValidator(config)
        self.price_comparator = PriceComparator(config)
        self.trend_analyzer = TrendAnalyzer(config)
        self.alert_system = AlertSystem(config)
        
        # Инициализация модулей экспорта
        self.excel_generator = ExcelGenerator(config)
        self.backup_manager = BackupManager()
        
        self._modules_initialized = True
        self.logger.info("✅ Все модули инициализированы")
    
    async def run(self, args):
        """Запуск парсера с полной интеграцией всех модулей"""
        try:
            self.logger.info("🚀 Запуск Universal Product Parser с полной интеграцией")
            self.logger.info("=" * 60)
            
            # Инициализация парсера
            self.parser = AdaptiveProductParser(args.config)
            await self.parser.initialize()
            
            # Определение источника URL
            self.target_url = await self._get_target_url(args)
            if not self.target_url:
                self.logger.error("❌ Не указан целевой URL для парсинга")
                return 1
            
            # Инициализация всех модулей
            self._initialize_modules(self.parser.config)
            
            # Подготовка фильтров
            filters = self._prepare_filters(args)
            
            # Запуск парсинга
            self.logger.info(f"🎯 Начинаем парсинг: {self.target_url}")
            products = await self.parser.parse_site(self.target_url, filters)
            
            if not products:
                self.logger.warning("⚠️ Товары не найдены")
                return 0
            
            self.logger.info(f"✅ Парсинг завершен: {len(products)} товаров")
            
            # Полная обработка данных
            processed_data = await self._process_data_pipeline(products, args)
            
            # Сохранение результатов
            await self._save_comprehensive_results(processed_data, args.output)
            
            self.logger.info("🎉 Все этапы обработки завершены успешно!")
            return 0
            
        except ParserError as e:
            handle_global_error(e, {'phase': 'parsing'})
            return 1
        except KeyboardInterrupt:
            self.logger.info("⏹️ Парсинг прерван пользователем")
            return 130
        except Exception as e:
            handle_global_error(e, {'phase': 'unknown'})
            return 1
        finally:
            if self.parser:
                await self.parser.close()
    
    async def _process_data_pipeline(self, raw_products: List[Dict], args) -> Dict[str, Any]:
        """
        Полный конвейер обработки данных через все модули
        
        Args:
            raw_products: Сырые данные товаров
            args: Аргументы командной строки
            
        Returns:
            Dict: Результаты всех этапов обработки
        """
        self.logger.info("🔄 Запуск полного конвейера обработки данных")
        
        pipeline_results = {
            'timestamp': datetime.now().isoformat(),
            'target_url': self.target_url,
            'original_products_count': len(raw_products)
        }
        
        try:
            # 1. Валидация данных
            self.logger.info("🔍 Этап 1: Валидация данных...")
            validation_results = self.data_validator.validate_products(raw_products)
            pipeline_results['validation'] = validation_results
            
            # Используем только валидные товары для дальнейшей обработки
            valid_products = [item['product'] for item in validation_results.get('valid_products', [])]
            self.logger.info(f"✅ Валидных товаров: {len(valid_products)}")
            
            if not valid_products:
                self.logger.warning("⚠️ Нет валидных товаров для дальнейшей обработки")
                return pipeline_results
            
            # 2. Переписывание текстов
            self.logger.info("📝 Этап 2: Переписывание описаний...")
            rewritten_products = []
            
            for product in valid_products:
                try:
                    rewrite_result = self.text_rewriter.rewrite_description(
                        product.get('description', ''),
                        product
                    )
                    
                    if rewrite_result['success']:
                        product['original_description'] = product.get('description', '')
                        product['description'] = rewrite_result['rewritten']
                        product['rewrite_metadata'] = {
                            'success': True,
                            'changes_made': rewrite_result.get('changes_made', {})
                        }
                    else:
                        product['rewrite_metadata'] = {
                            'success': False,
                            'error': rewrite_result.get('error', 'Unknown error')
                        }
                    
                    rewritten_products.append(product)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка переписывания товара {product.get('name')}: {e}")
                    product['rewrite_metadata'] = {'success': False, 'error': str(e)}
                    rewritten_products.append(product)
            
            pipeline_results['rewriting'] = {
                'total_processed': len(rewritten_products),
                'successful_rewrites': sum(1 for p in rewritten_products 
                                         if p.get('rewrite_metadata', {}).get('success', False))
            }
            
            # 3. Сравнение цен
            self.logger.info("📊 Этап 3: Сравнение цен...")
            price_comparison = self.price_comparator.compare_prices(
                current_data=rewritten_products,
                previous_file_path="data/output/previous_products.json"
            )
            pipeline_results['price_comparison'] = price_comparison
            
            # 4. Анализ трендов (если есть исторические данные)
            self.logger.info("📈 Этап 4: Анализ трендов...")
            trend_analysis = await self._analyze_trends(rewritten_products)
            pipeline_results['trend_analysis'] = trend_analysis
            
            # 5. Проверка уведомлений
            self.logger.info("🚨 Этап 5: Проверка уведомлений...")
            alerts = self.alert_system.check_for_alerts(
                price_comparison=price_comparison,
                trend_analysis=trend_analysis,
                validation_results=validation_results
            )
            pipeline_results['alerts'] = alerts
            
            # Отправка уведомлений в консоль
            self.alert_system.send_alerts(alerts, method='console')
            
            # Сохраняем текущие данные для следующего сравнения
            self._save_current_data(rewritten_products)
            
            pipeline_results['processed_products'] = rewritten_products
            pipeline_results['success'] = True
            
            self.logger.info("✅ Конвейер обработки данных завершен")
            return pipeline_results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка в конвейере обработки: {e}")
            pipeline_results['success'] = False
            pipeline_results['error'] = str(e)
            return pipeline_results
    
    async def _analyze_trends(self, products: List[Dict]) -> Dict[str, Any]:
        """Анализ трендов на основе исторических данных"""
        try:
            # Загрузка исторических данных
            history_file = Path("data/output/price_history.json")
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    price_history = json.load(f)
                
                # Анализ трендов
                return self.trend_analyzer.analyze_price_trends(price_history)
            else:
                return {
                    'success': False,
                    'reason': 'Недостаточно исторических данных для анализа трендов'
                }
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка анализа трендов: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_current_data(self, products: List[Dict]):
        """Сохранение текущих данных для будущего сравнения"""
        try:
            output_dir = Path("data/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохранение для сравнения цен
            with open(output_dir / "previous_products.json", 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            # Обновление истории цен
            self._update_price_history(products)
            
            self.logger.info("💾 Текущие данные сохранены для будущего сравнения")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения текущих данных: {e}")
    
    def _update_price_history(self, products: List[Dict]):
        """Обновление истории цен"""
        try:
            history_file = Path("data/output/price_history.json")
            history = {}
            
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            timestamp = datetime.now().isoformat()
            site_key = self._get_site_key(self.target_url)
            
            if site_key not in history:
                history[site_key] = {}
            
            # Добавление текущих цен в историю
            for product in products:
                product_key = self.price_comparator._get_product_key(product)
                if product_key not in history[site_key]:
                    history[site_key][product_key] = []
                
                history[site_key][product_key].append({
                    'timestamp': timestamp,
                    'price': product.get('price'),
                    'name': product.get('name', '')
                })
                
                # Ограничение истории (последние 100 записей на товар)
                if len(history[site_key][product_key]) > 100:
                    history[site_key][product_key] = history[site_key][product_key][-100:]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка обновления истории цен: {e}")
    
    async def _save_comprehensive_results(self, processed_data: Dict[str, Any], output_path: Optional[str]):
        """Комплексное сохранение результатов через все модули экспорта"""
        try:
            self.logger.info("💾 Комплексное сохранение результатов...")
            
            products = processed_data.get('processed_products', [])
            
            if not products:
                self.logger.warning("⚠️ Нет данных для сохранения")
                return
            
            # 1. Генерация Excel отчета
            self.logger.info("📊 Генерация комплексного Excel отчета...")
            excel_file = self.excel_generator.generate_comprehensive_report(
                products=products,
                price_comparison=processed_data.get('price_comparison'),
                trend_analysis=processed_data.get('trend_analysis'),
                validation_results=processed_data.get('validation'),
                alerts=processed_data.get('alerts'),
                site_url=self.target_url
            )
            
            # 2. Создание резервной копии
            self.logger.info("💾 Создание резервной копии...")
            backup_path = self.backup_manager.create_backup(
                data_files=['output/previous_products.json', 'output/price_history.json', 'output/excel_exports/*'],
                description=f"Автоматический бэкап после парсинга {self.target_url}"
            )
            
            # 3. Сохранение сырых данных для отладки
            debug_file = Path("data/output/debug_processing.json")
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
            # 4. Вывод итоговой статистики
            self._print_comprehensive_summary(processed_data, excel_file, backup_path)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения результатов: {e}")
            # Fallback: простой экспорт
            await self._save_fallback(products, output_path)
    
    def _print_comprehensive_summary(self, processed_data: Dict, excel_file: str, backup_path: str):
        """Вывод комплексной сводки результатов"""
        products = processed_data.get('processed_products', [])
        validation = processed_data.get('validation', {})
        price_comparison = processed_data.get('price_comparison', {})
        alerts = processed_data.get('alerts', {})
        
        print("\n" + "="*70)
        print("🎉 КОМПЛЕКСНЫЙ ОТЧЕТ ЗАВЕРШЕН!")
        print("="*70)
        
        # Основная статистика
        print(f"📊 Обработано товаров: {len(products)}")
        print(f"✅ Валидных товаров: {validation.get('quality_metrics', {}).get('valid_products_count', 0)}")
        print(f"💾 Excel отчет: {excel_file}")
        print(f"💾 Резервная копия: {backup_path}")
        
        # Статистика переписывания
        rewriting = processed_data.get('rewriting', {})
        print(f"📝 Переписано описаний: {rewriting.get('successful_rewrites', 0)}/{rewriting.get('total_processed', 0)}")
        
        # Статистика цен
        if price_comparison.get('success'):
            price_changes = price_comparison.get('price_changes', {})
            new_products = len(price_comparison.get('new_products', []))
            print(f"💰 Изменения цен: +{price_changes.get('increased', 0)}/-{price_changes.get('decreased', 0)}")
            print(f"🆕 Новых товаров: {new_products}")
        
        # Уведомления
        alert_summary = alerts.get('summary', {})
        if alert_summary.get('total_alerts', 0) > 0:
            print(f"🚨 Уведомлений: {alert_summary['total_alerts']} "
                  f"(критических: {alert_summary.get('critical_alerts', 0)})")
        
        # Качество данных
        quality_metrics = validation.get('quality_metrics', {})
        print(f"📈 Оценка качества данных: {quality_metrics.get('quality_score', 0):.1%}")
        
        print("="*70)
    
    async def _get_target_url(self, args) -> Optional[str]:
        """Получение целевого URL из аргументов или файла"""
        if args.url:
            return args.url
        elif args.url_file:
            try:
                with open(args.url_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                return urls[0] if urls else None
            except Exception as e:
                self.logger.error(f"❌ Ошибка чтения файла URL: {e}")
                return None
        else:
            # Попытка прочитать из стандартного файла
            default_url_file = Path("data/input/target_urls.txt")
            if default_url_file.exists():
                try:
                    with open(default_url_file, 'r', encoding='utf-8') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    return urls[0] if urls else None
                except Exception as e:
                    self.logger.error(f"❌ Ошибка чтения файла target_urls.txt: {e}")
        
        return None
    
    def _prepare_filters(self, args) -> dict:
        """Подготовка фильтров из аргументов командной строки"""
        filters = {}
        
        # Фильтр по цене
        if args.min_price or args.max_price:
            filters['price_range'] = {}
            if args.min_price:
                filters['price_range']['min'] = args.min_price
            if args.max_price:
                filters['price_range']['max'] = args.max_price
        
        # Фильтр по категориям
        if args.categories:
            filters['categories'] = [cat.strip() for cat in args.categories.split(',')]
        
        # Фильтр по характеристикам
        if args.filters:
            try:
                # Ожидаем формат: "вес:0.1-10,длина:100-500"
                char_filters = {}
                for filter_pair in args.filters.split(','):
                    if ':' in filter_pair:
                        key, value = filter_pair.split(':', 1)
                        char_filters[key.strip()] = value.strip()
                if char_filters:
                    filters['characteristics'] = char_filters
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка парсинга фильтров: {e}")
        
        return filters
    
    def _get_site_key(self, url: str) -> str:
        """Создание ключа для сайта"""
        return url.replace('https://', '').replace('http://', '').split('/')[0]
    
    async def _save_fallback(self, products: List[dict], output_path: Optional[str]):
        """Резервное сохранение в JSON"""
        try:
            output_file = output_path or "data/output/parsed_products.json"
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Резервная копия сохранена: {output_file}")
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка сохранения: {e}")
    
    async def test_connection(self, url: str):
        """Тестирование соединения с сайтом"""
        try:
            self.logger.info(f"🔍 Тестирование соединения с {url}")
            
            from src.utils.network_utils import NetworkUtils
            network_utils = NetworkUtils()
            
            # Проверка интернета
            if not await network_utils.check_internet_connection():
                self.logger.error("❌ Отсутствует интернет-соединение")
                return False
            
            # Проверка доступности сайта
            site_check = await network_utils.check_site_availability(url)
            
            if site_check['available']:
                self.logger.info(f"✅ Сайт доступен, ответ: {site_check['status_code']}")
                self.logger.info(f"⏱️ Время ответа: {site_check['response_time']} сек")
                return True
            else:
                self.logger.error(f"❌ Сайт недоступен: {site_check.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка тестирования: {e}")
            return False
    
    def show_stats(self):
        """Показать статистику ошибок"""
        from src.utils.error_handler import get_global_error_stats
        stats = get_global_error_stats()
        
        print("\n📊 СТАТИСТИКА ОШИБОК:")
        print("=" * 30)
        print(f"Всего ошибок: {stats['total_errors']}")
        print(f"Восстановлено: {stats['recovered_errors']}")
        print(f"По типам: {stats['by_type']}")


async def main():#!/usr/bin/env python3
"""
Главный CLI интерфейс Universal Product Parser
Полная интеграция всех модулей с поддержкой артикулов и изображений
"""

import asyncio
import sys
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Добавляем путь к корню проекта для импортов
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.adaptive_parser import AdaptiveProductParser
from src.content_processor.text_rewriter import TextRewriter
from src.data_analyzer.data_validator import DataValidator
from src.data_analyzer.price_comparator import PriceComparator
from src.data_analyzer.trend_analyzer import TrendAnalyzer
from src.data_analyzer.alert_system import AlertSystem
from src.exporter.excel_generator import ExcelGenerator
from src.exporter.backup_manager import BackupManager
from src.utils.logger import setup_logger
from src.utils.file_manager import FileManager
from src.utils.error_handler import ParserError, handle_global_error
from .argument_parser import create_parser


class ParserCLI:
    """Командный интерфейс для управления парсером с полной интеграцией модулей"""
    
    def __init__(self):
        self.logger = setup_logger("cli")
        self.file_manager = FileManager()
        self.parser = None
        self.target_url = ""
        
        # Инициализация модулей (ленивая загрузка)
        self._modules_initialized = False
        self.text_rewriter = None
        self.data_validator = None
        self.price_comparator = None
        self.trend_analyzer = None
        self.alert_system = None
        self.excel_generator = None
        self.backup_manager = None
    
    def _initialize_modules(self, config: Dict[str, Any] = None):
        """Ленивая инициализация всех модулей"""
        if self._modules_initialized:
            return
            
        config = config or {}
        
        # Инициализация модулей обработки контента
        self.text_rewriter = TextRewriter(config)
        
        # Инициализация модулей анализа данных
        self.data_validator = DataValidator(config)
        self.price_comparator = PriceComparator(config)
        self.trend_analyzer = TrendAnalyzer(config)
        self.alert_system = AlertSystem(config)
        
        # Инициализация модулей экспорта
        self.excel_generator = ExcelGenerator(config)
        self.backup_manager = BackupManager()
        
        self._modules_initialized = True
        self.logger.info("✅ Все модули инициализированы")
    
    async def run(self, args):
        """Запуск парсера с полной интеграцией всех модулей"""
        try:
            self.logger.info("🚀 Запуск Universal Product Parser с полной интеграцией")
            self.logger.info("=" * 60)
            
            # Инициализация парсера
            self.parser = AdaptiveProductParser(args.config)
            await self.parser.initialize()
            
            # Определение источника URL
            self.target_url = await self._get_target_url(args)
            if not self.target_url:
                self.logger.error("❌ Не указан целевой URL для парсинга")
                return 1
            
            # Инициализация всех модулей
            self._initialize_modules(self.parser.config)
            
            # Подготовка фильтров
            filters = self._prepare_filters(args)
            
            # Запуск парсинга
            self.logger.info(f"🎯 Начинаем парсинг: {self.target_url}")
            products = await self.parser.parse_site(self.target_url, filters)
            
            if not products:
                self.logger.warning("⚠️ Товары не найдены")
                return 0
            
            self.logger.info(f"✅ Парсинг завершен: {len(products)} товаров")
            
            # Полная обработка данных
            processed_data = await self._process_data_pipeline(products, args)
            
            # Сохранение результатов
            await self._save_comprehensive_results(processed_data, args.output)
            
            self.logger.info("🎉 Все этапы обработки завершены успешно!")
            return 0
            
        except ParserError as e:
            handle_global_error(e, {'phase': 'parsing'})
            return 1
        except KeyboardInterrupt:
            self.logger.info("⏹️ Парсинг прерван пользователем")
            return 130
        except Exception as e:
            handle_global_error(e, {'phase': 'unknown'})
            return 1
        finally:
            if self.parser:
                await self.parser.close()
    
    async def _process_data_pipeline(self, raw_products: List[Dict], args) -> Dict[str, Any]:
        """
        Полный конвейер обработки данных через все модулы
        
        Args:
            raw_products: Сырые данные товаров (уже с артикулами и изображениями)
            args: Аргументы командной строки
            
        Returns:
            Dict: Результаты всех этапов обработки
        """
        self.logger.info("🔄 Запуск полного конвейера обработки данных")
        
        pipeline_results = {
            'timestamp': datetime.now().isoformat(),
            'target_url': self.target_url,
            'original_products_count': len(raw_products)
        }
        
        try:
            # СТАТИСТИКА ПО НОВЫМ ФУНКЦИЯМ
            articles_generated = sum(1 for p in raw_products if p.get('article'))
            total_images = sum(
                len(p.get('processed_images', {}).get('processed_images', [])) 
                for p in raw_products
            )
            approved_images = sum(
                p.get('processed_images', {}).get('moderation_results', {}).get('approved_count', 0)
                for p in raw_products
            )
            
            self.logger.info(f"📝 Сгенерировано артикулов: {articles_generated}/{len(raw_products)}")
            self.logger.info(f"🖼️ Обработано изображений: {approved_images}/{total_images} одобрено")
            
            # 1. Валидация данных
            self.logger.info("🔍 Этап 1: Валидация данных...")
            validation_results = self.data_validator.validate_products(raw_products)
            pipeline_results['validation'] = validation_results
            
            # Используем только валидные товары для дальнейшей обработки
            valid_products = [item['product'] for item in validation_results.get('valid_products', [])]
            self.logger.info(f"✅ Валидных товаров: {len(valid_products)}")
            
            if not valid_products:
                self.logger.warning("⚠️ Нет валидных товаров для дальнейшей обработки")
                return pipeline_results
            
            # 2. Переписывание текстов
            self.logger.info("📝 Этап 2: Переписывание описаний...")
            rewritten_products = []
            
            for product in valid_products:
                try:
                    rewrite_result = self.text_rewriter.rewrite_description(
                        product.get('description', ''),
                        product
                    )
                    
                    if rewrite_result['success']:
                        product['original_description'] = product.get('description', '')
                        product['description'] = rewrite_result['rewritten']
                        product['rewrite_metadata'] = {
                            'success': True,
                            'changes_made': rewrite_result.get('changes_made', {})
                        }
                    else:
                        product['rewrite_metadata'] = {
                            'success': False,
                            'error': rewrite_result.get('error', 'Unknown error')
                        }
                    
                    rewritten_products.append(product)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка переписывания товара {product.get('name')}: {e}")
                    product['rewrite_metadata'] = {'success': False, 'error': str(e)}
                    rewritten_products.append(product)
            
            pipeline_results['rewriting'] = {
                'total_processed': len(rewritten_products),
                'successful_rewrites': sum(1 for p in rewritten_products 
                                         if p.get('rewrite_metadata', {}).get('success', False)),
                'articles_generated': articles_generated,
                'images_processed': total_images,
                'images_approved': approved_images
            }
            
            # 3. Сравнение цен
            self.logger.info("📊 Этап 3: Сравнение цен...")
            price_comparison = self.price_comparator.compare_prices(
                current_data=rewritten_products,
                previous_file_path="data/output/previous_products.json"
            )
            pipeline_results['price_comparison'] = price_comparison
            
            # 4. Анализ трендов (если есть исторические данные)
            self.logger.info("📈 Этап 4: Анализ трендов...")
            trend_analysis = await self._analyze_trends(rewritten_products)
            pipeline_results['trend_analysis'] = trend_analysis
            
            # 5. Проверка уведомлений
            self.logger.info("🚨 Этап 5: Проверка уведомлений...")
            alerts = self.alert_system.check_for_alerts(
                price_comparison=price_comparison,
                trend_analysis=trend_analysis,
                validation_results=validation_results
            )
            pipeline_results['alerts'] = alerts
            
            # Отправка уведомлений в консоль
            self.alert_system.send_alerts(alerts, method='console')
            
            # Сохраняем текущие данные для следующего сравнения
            self._save_current_data(rewritten_products)
            
            pipeline_results['processed_products'] = rewritten_products
            pipeline_results['success'] = True
            
            self.logger.info("✅ Конвейер обработки данных завершен")
            return pipeline_results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка в конвейере обработки: {e}")
            pipeline_results['success'] = False
            pipeline_results['error'] = str(e)
            return pipeline_results
    
    async def _analyze_trends(self, products: List[Dict]) -> Dict[str, Any]:
        """Анализ трендов на основе исторических данных"""
        try:
            # Загрузка исторических данных
            history_file = Path("data/output/price_history.json")
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    price_history = json.load(f)
                
                # Анализ трендов
                return self.trend_analyzer.analyze_price_trends(price_history)
            else:
                return {
                    'success': False,
                    'reason': 'Недостаточно исторических данных для анализа трендов'
                }
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка анализа трендов: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_current_data(self, products: List[Dict]):
        """Сохранение текущих данных для будущего сравнения"""
        try:
            output_dir = Path("data/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохранение для сравнения цен
            with open(output_dir / "previous_products.json", 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            # Обновление истории цен
            self._update_price_history(products)
            
            self.logger.info("💾 Текущие данные сохранены для будущего сравнения")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения текущих данных: {e}")
    
    def _update_price_history(self, products: List[Dict]):
        """Обновление истории цен"""
        try:
            history_file = Path("data/output/price_history.json")
            history = {}
            
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            timestamp = datetime.now().isoformat()
            site_key = self._get_site_key(self.target_url)
            
            if site_key not in history:
                history[site_key] = {}
            
            # Добавление текущих цен в историю
            for product in products:
                product_key = self.price_comparator._get_product_key(product)
                if product_key not in history[site_key]:
                    history[site_key][product_key] = []
                
                history[site_key][product_key].append({
                    'timestamp': timestamp,
                    'price': product.get('price'),
                    'name': product.get('name', ''),
                    'article': product.get('article', '')  # ДОБАВЛЕНО: артикул в историю
                })
                
                # Ограничение истории (последние 100 записей на товар)
                if len(history[site_key][product_key]) > 100:
                    history[site_key][product_key] = history[site_key][product_key][-100:]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка обновления истории цен: {e}")
    
    async def _save_comprehensive_results(self, processed_data: Dict[str, Any], output_path: Optional[str]):
        """Комплексное сохранение результатов через все модули экспорта"""
        try:
            self.logger.info("💾 Комплексное сохранение результатов...")
            
            products = processed_data.get('processed_products', [])
            
            if not products:
                self.logger.warning("⚠️ Нет данных для сохранения")
                return
            
            # 1. Генерация Excel отчета с новой структурой
            self.logger.info("📊 Генерация комплексного Excel отчета...")
            excel_file = self.excel_generator.generate_comprehensive_report(
                products=products,
                price_comparison=processed_data.get('price_comparison'),
                trend_analysis=processed_data.get('trend_analysis'),
                validation_results=processed_data.get('validation'),
                alerts=processed_data.get('alerts'),
                site_url=self.target_url
            )
            
            # 2. Создание резервной копии
            self.logger.info("💾 Создание резервной копии...")
            backup_path = self.backup_manager.create_backup(
                data_files=['output/previous_products.json', 'output/price_history.json', 'output/excel_exports/*'],
                description=f"Автоматический бэкап после парсинга {self.target_url}"
            )
            
            # 3. Сохранение сырых данных для отладки
            debug_file = Path("data/output/debug_processing.json")
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
            # 4. Вывод итоговой статистики
            self._print_comprehensive_summary(processed_data, excel_file, backup_path)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения результатов: {e}")
            # Fallback: простой экспорт
            await self._save_fallback(products, output_path)
    
    def _print_comprehensive_summary(self, processed_data: Dict, excel_file: str, backup_path: str):
        """Вывод комплексной сводки результатов"""
        products = processed_data.get('processed_products', [])
        validation = processed_data.get('validation', {})
        price_comparison = processed_data.get('price_comparison', {})
        alerts = processed_data.get('alerts', {})
        rewriting = processed_data.get('rewriting', {})
        
        print("\n" + "="*70)
        print("🎉 КОМПЛЕКСНЫЙ ОТЧЕТ ЗАВЕРШЕН!")
        print("="*70)
        
        # Основная статистика
        print(f"📊 Обработано товаров: {len(products)}")
        print(f"✅ Валидных товаров: {validation.get('quality_metrics', {}).get('valid_products_count', 0)}")
        print(f"💾 Excel отчет: {excel_file}")
        print(f"💾 Резервная копия: {backup_path}")
        
        # НОВАЯ СТАТИСТИКА: Артикулы и изображения
        print(f"📝 Сгенерировано артикулов: {rewriting.get('articles_generated', 0)}")
        print(f"🖼️ Обработано изображений: {rewriting.get('images_approved', 0)}/{rewriting.get('images_processed', 0)} одобрено")
        
        # Статистика переписывания
        print(f"📝 Переписано описаний: {rewriting.get('successful_rewrites', 0)}/{rewriting.get('total_processed', 0)}")
        
        # Статистика цен
        if price_comparison.get('success'):
            price_changes = price_comparison.get('price_changes', {})
            new_products = len(price_comparison.get('new_products', []))
            print(f"💰 Изменения цен: +{price_changes.get('increased', 0)}/-{price_changes.get('decreased', 0)}")
            print(f"🆕 Новых товаров: {new_products}")
        
        # Уведомления
        alert_summary = alerts.get('summary', {})
        if alert_summary.get('total_alerts', 0) > 0:
            print(f"🚨 Уведомлений: {alert_summary['total_alerts']} "
                  f"(критических: {alert_summary.get('critical_alerts', 0)})")
        
        # Качество данных
        quality_metrics = validation.get('quality_metrics', {})
        print(f"📈 Оценка качества данных: {quality_metrics.get('quality_score', 0):.1%}")
        
        print("="*70)
    
    async def _get_target_url(self, args) -> Optional[str]:
        """Получение целевого URL из аргументов или файла"""
        if args.url:
            return args.url
        elif args.url_file:
            try:
                with open(args.url_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                return urls[0] if urls else None
            except Exception as e:
                self.logger.error(f"❌ Ошибка чтения файла URL: {e}")
                return None
        else:
            # Попытка прочитать из стандартного файла
            default_url_file = Path("data/input/target_urls.txt")
            if default_url_file.exists():
                try:
                    with open(default_url_file, 'r', encoding='utf-8') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    return urls[0] if urls else None
                except Exception as e:
                    self.logger.error(f"❌ Ошибка чтения файла target_urls.txt: {e}")
        
        return None
    
    def _prepare_filters(self, args) -> dict:
        """Подготовка фильтров из аргументов командной строки"""
        filters = {}
        
        # Фильтр по цене
        if args.min_price or args.max_price:
            filters['price_range'] = {}
            if args.min_price:
                filters['price_range']['min'] = args.min_price
            if args.max_price:
                filters['price_range']['max'] = args.max_price
        
        # Фильтр по категориям
        if args.categories:
            filters['categories'] = [cat.strip() for cat in args.categories.split(',')]
        
        # Фильтр по характеристикам
        if args.filters:
            try:
                # Ожидаем формат: "вес:0.1-10,длина:100-500"
                char_filters = {}
                for filter_pair in args.filters.split(','):
                    if ':' in filter_pair:
                        key, value = filter_pair.split(':', 1)
                        char_filters[key.strip()] = value.strip()
                if char_filters:
                    filters['characteristics'] = char_filters
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка парсинга фильтров: {e}")
        
        return filters
    
    def _get_site_key(self, url: str) -> str:
        """Создание ключа для сайта"""
        return url.replace('https://', '').replace('http://', '').split('/')[0]
    
    async def _save_fallback(self, products: List[dict], output_path: Optional[str]):
        """Резервное сохранение в JSON"""
        try:
            output_file = output_path or "data/output/parsed_products.json"
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Резервная копия сохранена: {output_file}")
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка сохранения: {e}")
    
    async def test_connection(self, url: str):
        """Тестирование соединения с сайтом"""
        try:
            self.logger.info(f"🔍 Тестирование соединения с {url}")
            
            from src.utils.network_utils import NetworkUtils
            network_utils = NetworkUtils()
            
            # Проверка интернета
            if not await network_utils.check_internet_connection():
                self.logger.error("❌ Отсутствует интернет-соединение")
                return False
            
            # Проверка доступности сайта
            site_check = await network_utils.check_site_availability(url)
            
            if site_check['available']:
                self.logger.info(f"✅ Сайт доступен, ответ: {site_check['status_code']}")
                self.logger.info(f"⏱️ Время ответа: {site_check['response_time']} сек")
                return True
            else:
                self.logger.error(f"❌ Сайт недоступен: {site_check.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка тестирования: {e}")
            return False
    
    def show_stats(self):
        """Показать статистику ошибок"""
        from src.utils.error_handler import get_global_error_stats
        stats = get_global_error_stats()
        
        print("\n📊 СТАТИСТИКА ОШИБОК:")
        print("=" * 30)
        print(f"Всего ошибок: {stats['total_errors']}")
        print(f"Восстановлено: {stats['recovered_errors']}")
        print(f"По типам: {stats['by_type']}")


async def main():
    """Главная функция CLI"""
    parser = create_parser()
    args = parser.parse_args()
    
    cli = ParserCLI()
    
    # Обработка специальных команд
    if args.command == 'test':
        if not args.url:
            print("❌ Для тестирования укажите URL с помощью --url")
            return 1
        success = await cli.test_connection(args.url)
        return 0 if success else 1
    
    elif args.command == 'stats':
        cli.show_stats()
        return 0
    
    elif args.command == 'parse':
        return await cli.run(args)
    
    else:
        # Если команда не указана, показываем help
        parser.print_help()
        return 0


if __name__ == "__main__":
    # Запуск асинхронной главной функции
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
    """Главная функция CLI"""
    parser = create_parser()
    args = parser.parse_args()
    
    cli = ParserCLI()
    
    # Обработка специальных команд
    if args.command == 'test':
        if not args.url:
            print("❌ Для тестирования укажите URL с помощью --url")
            return 1
        success = await cli.test_connection(args.url)
        return 0 if success else 1
    
    elif args.command == 'stats':
        cli.show_stats()
        return 0
    
    elif args.command == 'parse':
        return await cli.run(args)
    
    else:
        # Если команда не указана, показываем help
        parser.print_help()
        return 0


if __name__ == "__main__":
    # Запуск асинхронной главной функции
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
