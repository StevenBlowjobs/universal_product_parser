#!/usr/bin/env python3
"""
Модуль управления навигацией по сайту и категориям
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.async_api import Page
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class NavigationManager:
    """Менеджер навигации по категориям и пагинации"""
    
    def __init__(self, page: Page, detected_selectors: Dict[str, str]):
        self.page = page
        self.selectors = detected_selectors
        self.logger = setup_logger("navigation_manager")
        self.base_url = None
        
    async def get_categories(self) -> List[Dict[str, str]]:
        """Получение списка категорий товаров"""
        self.logger.info("📂 Поиск категорий товаров...")
        
        categories = []
        
        try:
            # Получение базового URL
            self.base_url = await self._get_base_url()
            
            # Поиск категорий в навигации
            nav_categories = await self._find_navigation_categories()
            categories.extend(nav_categories)
            
            # Поиск категорий в карте сайта
            sitemap_categories = await self._find_sitemap_categories()
            categories.extend(sitemap_categories)
            
            # Удаление дубликатов
            unique_categories = self._remove_duplicate_categories(categories)
            
            self.logger.info(f"✅ Найдено категорий: {len(unique_categories)}")
            return unique_categories
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска категорий: {e}")
            return []
    
    async def _get_base_url(self) -> str:
        """Получение базового URL сайта"""
        current_url = self.page.url
        parsed = urlparse(current_url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    async def _find_navigation_categories(self) -> List[Dict[str, str]]:
        """Поиск категорий в навигационных меню"""
        categories = []
        
        # Распространенные селекторы навигационных меню
        nav_selectors = [
            'nav ul li a',
            '.navigation a',
            '.menu a',
            '.categories a',
            '.nav-menu a',
            '[class*="nav"] a',
            '[class*="menu"] a',
            '[class*="category"] a'
        ]
        
        for selector in nav_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    category = await self._extract_category_from_element(element)
                    if category and self._is_valid_category(category):
                        categories.append(category)
            except Exception as e:
                self.logger.debug(f"Селектор {selector} не сработал: {e}")
                continue
        
        return categories
    
    async def _extract_category_from_element(self, element) -> Optional[Dict[str, str]]:
        """Извлечение категории из элемента"""
        try:
            name = await element.text_content()
            href = await element.get_attribute('href')
            
            if not name or not href:
                return None
            
            name = name.strip()
            if len(name) > 100:  # Слишком длинное название - вероятно не категория
                return None
            
            # Формирование полного URL
            full_url = urljoin(self.base_url, href)
            
            # Проверка, что это действительно категория товаров
            if await self._is_product_category(full_url):
                return {
                    'name': name,
                    'url': full_url,
                    'type': 'navigation'
                }
                
        except Exception as e:
            self.logger.debug(f"Ошибка извлечения категории: {e}")
            
        return None
    
    async def _is_product_category(self, url: str) -> bool:
        """Проверка, что URL ведет на категорию товаров"""
        try:
            # Проверка по паттернам в URL
            category_patterns = [
                r'/categor', r'/category', r'/kategor', r'/kategoria',
                r'/shop', r'/products', r'/tovary', r'/catalog',
                r'/collection', r'/brand', r'/type'
            ]
            
            if any(re.search(pattern, url, re.IGNORECASE) for pattern in category_patterns):
                return True
            
            # Дополнительная проверка по содержимому страницы
            await self.page.goto(url, wait_until='domcontentloaded')
            content = await self.page.content()
            
            # Поиск индикаторов товарной категории
            indicators = [
                'product', 'товар', 'price', 'цена', 'buy', 'купить',
                'add to cart', 'в корзину', 'товаров', 'products'
            ]
            
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text().lower()
            
            # Если есть несколько индикаторов - вероятно это категория товаров
            indicator_count = sum(1 for indicator in indicators if indicator in text_content)
            return indicator_count >= 2
            
        except Exception as e:
            self.logger.debug(f"Ошибка проверки категории {url}: {e}")
            return False
    
    async def _find_sitemap_categories(self) -> List[Dict[str, str]]:
        """Поиск категорий через sitemap.xml"""
        categories = []
        
        sitemap_urls = [
            f"{self.base_url}/sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
            f"{self.base_url}/sitemap/categories.xml",
            f"{self.base_url}/sitemap-products.xml"
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                await self.page.goto(sitemap_url, wait_until='networkidle')
                content = await self.page.content()
                
                if '<?xml' in content:
                    # Парсинг XML sitemap
                    soup = BeautifulSoup(content, 'xml')
                    urls = soup.find_all('loc')
                    
                    for url in urls[:50]:  # Ограничим для производительности
                        url_text = url.get_text()
                        if self._is_category_url(url_text):
                            categories.append({
                                'name': self._extract_category_name_from_url(url_text),
                                'url': url_text,
                                'type': 'sitemap'
                            })
                            
            except Exception as e:
                self.logger.debug(f"Sitemap {sitemap_url} недоступен: {e}")
                continue
        
        return categories
    
    def _is_category_url(self, url: str) -> bool:
        """Проверка, что URL является категорией"""
        category_indicators = [
            '/category/', '/categor/', '/kategor/', '/shop/',
            '/products/', '/catalog/', '/collection/'
        ]
        return any(indicator in url.lower() for indicator in category_indicators)
    
    def _extract_category_name_from_url(self, url: str) -> str:
        """Извлечение названия категории из URL"""
        # Извлечение последней части URL как названия
        name = url.rstrip('/').split('/')[-1]
        # Замена дефисов и подчеркиваний на пробелы
        name = re.sub(r'[-_]', ' ', name)
        # Capitalize
        return name.title()
    
    def _is_valid_category(self, category: Dict[str, str]) -> bool:
        """Валидация категории"""
        name = category.get('name', '')
        url = category.get('url', '')
        
        # Проверка длины названия
        if len(name) < 2 or len(name) > 100:
            return False
        
        # Исключение общих страниц
        exclude_keywords = ['home', 'main', 'index', 'contact', 'about', 'login', 'register']
        if any(keyword in name.lower() for keyword in exclude_keywords):
            return False
        
        # Проверка URL
        if not url.startswith(('http://', 'https://')):
            return False
        
        return True
    
    def _remove_duplicate_categories(self, categories: List[Dict]) -> List[Dict]:
        """Удаление дубликатов категорий"""
        seen_urls = set()
        unique_categories = []
        
        for category in categories:
            url = category['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_categories.append(category)
        
        return unique_categories
    
    @retry_on_failure(max_retries=2)
    async def parse_category(self, category_url: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Парсинг товаров в категории с учетом фильтров
        
        Args:
            category_url: URL категории
            filters: Фильтры товаров (цена, характеристики и т.д.)
            
        Returns:
            List[Dict]: Список товаров в категории
        """
        self.logger.info(f"📦 Парсинг категории: {category_url}")
        
        try:
            await self.page.goto(category_url, wait_until='networkidle')
            
            products = []
            page_number = 1
            
            while True:
                self.logger.info(f"📄 Страница {page_number}")
                
                # Парсинг товаров на текущей странице
                page_products = await self._parse_products_on_page(filters)
                products.extend(page_products)
                
                self.logger.info(f"✅ Страница {page_number}: {len(page_products)} товаров")
                
                # Проверка возможности перехода на следующую страницу
                next_page_url = await self._get_next_page_url()
                if not next_page_url:
                    break
                
                # Переход на следующую страницу
                await self.page.goto(next_page_url, wait_until='networkidle')
                page_number += 1
                
                # Ограничение количества страниц для тестирования
                if page_number > 10:  # Максимум 10 страниц
                    self.logger.warning("⚠️  Достигнут лимит страниц (10)")
                    break
            
            self.logger.info(f"🎉 Категория обработана: {len(products)} товаров")
            return products
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга категории: {e}")
            return []
    
    async def _parse_products_on_page(self, filters: Optional[Dict]) -> List[Dict]:
        """Парсинг товаров на текущей странице"""
        products = []
        
        # Поиск элементов товаров
        product_selectors = [
            '.product', '.item', '.goods', '.product-item',
            '[class*="product"]', '[class*="item"]', '.card'
        ]
        
        for selector in product_selectors:
            try:
                product_elements = await self.page.query_selector_all(selector)
                if product_elements:
                    self.logger.debug(f"Найдены товары по селектору: {selector}")
                    break
            except Exception:
                continue
        
        if not product_elements:
            self.logger.warning("⚠️  Не найдены элементы товаров")
            return []
        
        # Парсинг каждого товара
        for element in product_elements:
            try:
                product_data = await self._extract_product_from_element(element)
                if product_data and self._apply_filters(product_data, filters):
                    products.append(product_data)
            except Exception as e:
                self.logger.debug(f"Ошибка парсинга товара: {e}")
                continue
        
        return products
    
    async def _extract_product_from_element(self, element) -> Optional[Dict]:
        """Извлечение данных товара из элемента"""
        try:
            # Извлечение базовой информации
            name_element = await element.query_selector('h3, h4, .title, .name, [class*="title"]')
            name = await name_element.text_content() if name_element else None
            
            price_element = await element.query_selector('.price, .cost, [class*="price"]')
            price_text = await price_element.text_content() if price_element else None
            
            link_element = await element.query_selector('a')
            product_url = await link_element.get_attribute('href') if link_element else None
            
            if not name or not product_url:
                return None
            
            # Формирование полного URL товара
            full_url = urljoin(self.base_url, product_url)
            
            product_data = {
                'name': name.strip(),
                'url': full_url,
                'price': self._extract_price_from_text(price_text) if price_text else None,
                'image_url': await self._extract_image_url(element),
                'category_page_data': True  # Флаг, что данные с страницы категории
            }
            
            return product_data
            
        except Exception as e:
            self.logger.debug(f"Ошибка извлечения товара: {e}")
            return None
    
    def _extract_price_from_text(self, price_text: str) -> Optional[float]:
        """Извлечение цены из текста"""
        try:
            # Очистка и нормализация цены
            price_clean = re.sub(r'[^\d,.]', '', price_text)
            price_clean = price_clean.replace(',', '.')
            price_match = re.search(r'\d+\.?\d*', price_clean)
            return float(price_match.group()) if price_match else None
        except (ValueError, TypeError):
            return None
    
    async def _extract_image_url(self, element) -> Optional[str]:
        """Извлечение URL изображения товара"""
        try:
            img_element = await element.query_selector('img')
            if img_element:
                src = await img_element.get_attribute('src')
                return urljoin(self.base_url, src) if src else None
        except Exception:
            pass
        return None
    
    def _apply_filters(self, product_data: Dict, filters: Optional[Dict]) -> bool:
        """Применение фильтров к товару"""
        if not filters:
            return True
        
        # Фильтр по цене
        if 'price_range' in filters:
            price_range = filters['price_range']
            product_price = product_data.get('price')
            
            if product_price is not None:
                min_price = price_range.get('min', 0)
                max_price = price_range.get('max', float('inf'))
                
                if not (min_price <= product_price <= max_price):
                    return False
        
        # Фильтр по категориям
        if 'categories' in filters and filters['categories']:
            category = product_data.get('category', '')
            if not any(cat.lower() in category.lower() for cat in filters['categories']):
                return False
        
        return True
    
    async def _get_next_page_url(self) -> Optional[str]:
        """Получение URL следующей страницы пагинации"""
        try:
            # Поиск кнопки "Следующая страница"
            next_selectors = [
                '.pagination .next a',
                '.pagination a[rel="next"]',
                '.next-page',
                '.load-more',
                'a:has-text("Далее")',
                'a:has-text("Next")',
                'button:has-text("Еще товары")'
            ]
            
            for selector in next_selectors:
                next_element = await self.page.query_selector(selector)
                if next_element:
                    href = await next_element.get_attribute('href')
                    if href:
                        return urljoin(self.base_url, href)
            
            # Проверка номеров страниц
            page_links = await self.page.query_selector_all('.pagination a, .page-numbers a')
            current_url = self.page.url
            
            for link in page_links:
                href = await link.get_attribute('href')
                link_text = await link.text_content()
                
                if href and href != current_url and link_text.strip().isdigit():
                    page_num = int(link_text.strip())
                    if page_num > self._get_current_page_number(current_url):
                        return urljoin(self.base_url, href)
                        
        except Exception as e:
            self.logger.debug(f"Ошибка поиска следующей страницы: {e}")
        
        return None
    
    def _get_current_page_number(self, url: str) -> int:
        """Получение номера текущей страницы из URL"""
        page_match = re.search(r'page[=/]?(\d+)', url, re.IGNORECASE)
        return int(page_match.group(1)) if page_match else 1
