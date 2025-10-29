#!/usr/bin/env python3
"""
Главный класс адаптивного парсера товаров
"""

import asyncio
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page
from .structure_detector import WebsiteStructureDetector
from .content_extractor import ContentExtractor
from .navigation_manager import NavigationManager
from ..utils.anti_detection import AntiDetectionSystem
from ..utils.logger import setup_logger
from ..utils.error_handler import ParserError, retry_on_failure
from ..utils.article_generator import ArticleGenerator
from ..image_processor.product_images_manager import ProductImagesManager


class AdaptiveProductParser:
    """Адаптивный парсер товаров с автодетектом структуры сайта"""
    
    def __init__(self, config_path: str = "config/parser_config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = setup_logger("parser")
        
        # ИСПРАВЛЕНИЕ: Передаем правильные разделы конфига
        parser_config = self.config.get('parser', {})
        self.anti_detection = AntiDetectionSystem(parser_config.get('anti_detection', {}))
        
        self.structure_detector = WebsiteStructureDetector()
        self.content_extractor = None
        self.navigation_manager = None
        
        # НОВЫЕ КОМПОНЕНТЫ - ИСПРАВЛЕНИЕ: используем правильные разделы конфига
        self.article_generator = ArticleGenerator(
            self.config.get('article_generation', {})
        )
        self.images_manager = ProductImagesManager(
            self.config.get('product_images_processing', {})  # ИСПРАВЛЕНО: product_images_processing вместо image_processing
        )
        
        # Состояние парсера
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.detected_selectors: Dict[str, str] = {}
        self.playwright = None
        self.context = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации из YAML файла"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise ParserError(f"Конфигурационный файл не найден: {config_path}")
                
            with open(config_file, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                self.logger.info(f"✅ Конфигурация загружена из: {config_path}")
                return config
        except Exception as e:
            raise ParserError(f"Ошибка загрузки конфигурации: {e}")
    
    async def initialize(self):
        """Инициализация парсера и браузера"""
        self.logger.info("🔄 Инициализация парсера...")
        
        try:
            # Запуск Playwright
            self.playwright = await async_playwright().start()
            
            # Настройка браузера с анти-детект функциями
            browser_config = self.config.get('parser', {}).get('browser', {})
            launch_options = self.anti_detection.get_browser_launch_options()
            launch_options.update({
                'headless': browser_config.get('headless', True),
                'slow_mo': browser_config.get('slow_mo', 100),
            })
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # Создание контекста с настройками
            context_options = self.anti_detection.get_context_options()
            self.context = await self.browser.new_context(**context_options)
            
            # Установка размера viewport
            viewport_config = self.config.get('parser', {}).get('browser', {})
            await self.context.set_viewport_size({
                'width': viewport_config.get('viewport_width', 1920),
                'height': viewport_config.get('viewport_height', 1080)
            })
            
            # Создание страницы
            self.page = await self.context.new_page()
            
            # Настройка обработчиков страницы
            await self._setup_page_handlers()
            
            # Инициализация менеджера изображений
            if hasattr(self.images_manager, 'initialize'):
                await self.images_manager.initialize()
            else:
                self.logger.warning("⚠️ ProductImagesManager не имеет метода initialize")
            
            self.logger.info("✅ Парсер успешно инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации парсера: {e}")
            await self.close()
            raise ParserError(f"Ошибка инициализации парсера: {e}")
    
    async def _setup_page_handlers(self):
        """Настройка обработчиков событий страницы"""
        if not self.page:
            return
            
        # ИСПРАВЛЕНИЕ: Более умная блокировка ресурсов
        # Разрешаем загрузку изображений товаров, но блокируем остальные ресурсы для ускорения
        async def route_handler(route):
            request = route.request
            resource_type = request.resource_type
            
            # Разрешаем загрузку изображений и основных документов
            if resource_type in ["image", "document"]:
                await route.continue_()
            else:
                await route.abort()
                
        await self.page.route("**/*", route_handler)
        
        # Дополнительные настройки для улучшения производительности
        await self.page.set_extra_http_headers({
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })
    
    @retry_on_failure(max_retries=3)
    async def parse_site(self, target_url: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Основной метод парсинга сайта
        
        Args:
            target_url: URL целевого сайта
            filters: Фильтры для товаров (цена, категории и т.д.)
        
        Returns:
            List[Dict]: Список товаров с данными
        """
        self.logger.info(f"🎯 Начало парсинга: {target_url}")
        
        try:
            # Переход на целевую страницу
            navigation_config = self.config.get('parser', {}).get('navigation', {})
            timeout = navigation_config.get('pagination_timeout', 30) * 1000  # Convert to ms
            
            await self.page.goto(target_url, wait_until="domcontentloaded", timeout=timeout)
            
            # Обход защиты (Cloudflare и т.д.)
            await self.anti_detection.bypass_protection(self.page)
            
            # Ждем полной загрузки
            await self.page.wait_for_load_state('networkidle')
            
            # Автодетект структуры сайта
            self.logger.info("🔍 Автодетект структуры сайта...")
            html_content = await self.page.content()
            self.detected_selectors = self.structure_detector.auto_detect_selectors(html_content)
            
            # Инициализация экстрактора с найденными селекторами
            self.content_extractor = ContentExtractor(self.detected_selectors)
            self.navigation_manager = NavigationManager(self.page, self.detected_selectors)
            
            self.logger.info(f"✅ Структура определена: {len(self.detected_selectors)} селекторов")
            
            # Навигация по категориям
            categories = await self.navigation_manager.get_categories()
            self.logger.info(f"📂 Найдено категорий: {len(categories)}")
            
            # Парсинг товаров
            all_products = []
            max_categories = navigation_config.get('max_categories', 10)
            max_products = navigation_config.get('max_products_per_category', 50)
            
            for category in categories[:max_categories]:
                self.logger.info(f"📦 Парсинг категории: {category.get('name', 'Unknown')}")
                
                try:
                    products = await self.navigation_manager.parse_category(
                        category['url'], 
                        filters
                    )
                    
                    # ОБРАБОТКА КАЖДОГО ТОВАРА С ГЕНЕРАЦИЕЙ АРТИКУЛОВ И ИЗОБРАЖЕНИЙ
                    processed_products = []
                    for product in products[:max_products]:
                        try:
                            processed_product = await self._enrich_product_data(product)
                            processed_products.append(processed_product)
                        except Exception as e:
                            self.logger.error(f"❌ Ошибка обработки товара: {e}")
                            # Продолжаем обработку остальных товаров
                            continue
                    
                    all_products.extend(processed_products)
                    
                    self.logger.info(f"✅ Категория '{category.get('name', 'Unknown')}': {len(processed_products)} товаров")
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка парсинга категории {category.get('name', 'Unknown')}: {e}")
                    # Продолжаем с следующей категорией
                    continue
            
            self.logger.info(f"🎉 Парсинг завершен! Всего товаров: {len(all_products)}")
            return all_products
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга: {e}")
            raise ParserError(f"Ошибка парсинга сайта: {e}")
    
    async def parse_single_product(self, product_url: str) -> Optional[Dict]:
        """Парсинг одиночного товара по URL"""
        try:
            navigation_config = self.config.get('parser', {}).get('navigation', {})
            timeout = navigation_config.get('pagination_timeout', 30) * 1000
            
            await self.page.goto(product_url, wait_until="domcontentloaded", timeout=timeout)
            await self.page.wait_for_load_state('networkidle')
            
            html_content = await self.page.content()
            
            if not self.content_extractor:
                # Детект структуры если еще не сделан
                self.detected_selectors = self.structure_detector.auto_detect_selectors(html_content)
                self.content_extractor = ContentExtractor(self.detected_selectors)
            
            product_data = self.content_extractor.extract_product_data(html_content, product_url)
            
            # ОБОГАЩЕНИЕ ДАННЫХ ТОВАРА
            enriched_data = await self._enrich_product_data(product_data)
            
            return enriched_data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга товара {product_url}: {e}")
            return None
    
    async def _enrich_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обогащение данных товара: генерация артикула и обработка изображений
        
        Args:
            product_data: Исходные данные товара
            
        Returns:
            Dict[str, Any]: Обогащенные данные товара
        """
        try:
            # ГЕНЕРАЦИЯ АРТИКУЛА
            if 'article' not in product_data or not product_data['article']:
                product_data['article'] = self.article_generator.generate_article(product_data)
                self.logger.debug(f"📝 Сгенерирован артикул: {product_data['article']}")
            
            # ОБРАБОТКА ИЗОБРАЖЕНИЙ
            image_urls = product_data.get('image_urls', [])
            if not image_urls:
                # Попробуем найти изображения в других полях
                image_url = product_data.get('image_url')
                if image_url:
                    image_urls = [image_url]
            
            if image_urls:
                self.logger.info(f"🖼️ Обработка {len(image_urls)} изображений для товара {product_data['article']}")
                
                try:
                    processed_images = await self.images_manager.process_product_images(
                        image_urls, 
                        product_data['article']
                    )
                    product_data['processed_images'] = processed_images
                    
                    approved_count = processed_images.get('moderation_results', {}).get('approved_count', 0)
                    self.logger.info(f"✅ Обработано изображений: {approved_count} одобрено")
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки изображений: {e}")
                    product_data['processed_images'] = {
                        'original_count': len(image_urls),
                        'processed_images': [],
                        'moderation_results': {'total_processed': 0, 'approved_count': 0},
                        'main_image': None,
                        'gallery_images': [],
                        'error': str(e)
                    }
            else:
                product_data['processed_images'] = {
                    'original_count': 0,
                    'processed_images': [],
                    'moderation_results': {'total_processed': 0, 'approved_count': 0},
                    'main_image': None,
                    'gallery_images': []
                }
                self.logger.warning(f"⚠️ Нет изображений для товара {product_data['article']}")
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обогащения данных товара: {e}")
            # Возвращаем оригинальные данные в случае ошибки, но добавляем информацию об ошибке
            product_data['processing_error'] = str(e)
            return product_data
    
    async def close(self):
        """Корректное закрытие парсера"""
        self.logger.info("🔚 Завершение работы парсера...")
        
        try:
            # Закрытие менеджера изображений
            if hasattr(self.images_manager, 'close'):
                await self.images_manager.close()
            elif hasattr(self.images_manager, 'close') and callable(getattr(self.images_manager, 'close')):
                self.images_manager.close()
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка при закрытии менеджера изображений: {e}")
        
        if self.browser:
            await self.browser.close()
            self.browser = None
            
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        self.logger.info("✅ Парсер завершил работу")
    
    async def __aenter__(self):
        """Поддержка async context manager"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Поддержка async context manager"""
        await self.close()
