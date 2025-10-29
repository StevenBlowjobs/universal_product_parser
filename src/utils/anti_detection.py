#!/usr/bin/env python3
"""
Система обхода анти-бот защиты и детекта
"""

import random
import asyncio
import time
from typing import Dict, List, Optional, Any
from playwright.async_api import Page, BrowserContext
from urllib.parse import urlparse
from .logger import setup_logger


class AntiDetectionSystem:
    """Комплексная система обхода обнаружения ботов"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('anti_detection', {})
        self.logger = setup_logger("anti_detection")
        self.user_agents = self._load_user_agents()
        self.proxies = self._load_proxies()
        
    def _load_user_agents(self) -> List[str]:
        """Загрузка списка User-Agent"""
        default_agents = [
            # Современные десктопные браузеры
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            
            # Мобильные User-Agent
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        ]
        
        return self.config.get('user_agents', default_agents)
    
    def _load_proxies(self) -> List[str]:
        """Загрузка списка прокси"""
        return self.config.get('proxies', [])
    
    def get_random_user_agent(self) -> str:
        """Получение случайного User-Agent"""
        return random.choice(self.user_agents)
    
    def get_random_delay(self) -> float:
        """Получение случайной задержки между запросами"""
        delay_config = self.config.get('request_delay', {'min': 2, 'max': 5})
        return random.uniform(delay_config['min'], delay_config['max'])
    
    def get_browser_launch_options(self) -> Dict[str, Any]:
        """Получение опций для запуска браузера"""
        options = {
            'headless': True,
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-ipc-flooding-protection',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--disable-translate',
                '--disable-extensions',
                '--disable-component-extensions-with-background-pages',
            ]
        }
        
        # Добавляем прокси если есть
        if self.proxies and self.config.get('use_proxies', False):
            proxy = random.choice(self.proxies)
            options['args'].append(f'--proxy-server={proxy}')
        
        return options
    
    def get_context_options(self) -> Dict[str, Any]:
        """Получение опций для контекста браузера"""
        user_agent = self.get_random_user_agent()
        
        return {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': user_agent,
            'locale': 'ru-RU',
            'timezone_id': 'Europe/Moscow',
            'geolocation': {'latitude': 55.7558, 'longitude': 37.6173},  # Москва
            'permissions': ['geolocation'],
            'extra_http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'DNT': '1',
                'Upgrade-Insecure-Requests': '1',
            },
            'bypass_csp': True,
        }
    
    async def bypass_cloudflare(self, page: Page) -> bool:
        """Обход Cloudflare защиты"""
        self.logger.info("☁️  Обход Cloudflare защиты...")
        
        try:
            # Ожидание появления Cloudflare challenge
            try:
                await page.wait_for_selector('div#cf-content, .challenge-form', timeout=10000)
            except:
                # Cloudflare не обнаружен
                return True
            
            # Дополнительные действия для обхода
            await page.wait_for_timeout(5000)
            
            # Попытка решить challenge автоматически
            await self._solve_cloudflare_challenge(page)
            
            self.logger.info("✅ Cloudflare успешно обойден")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обхода Cloudflare: {e}")
            return False
    
    async def _solve_cloudflare_challenge(self, page: Page):
        """Решение Cloudflare challenge"""
        # Эмулируем человеческое поведение
        await page.mouse.move(100, 100)
        await page.wait_for_timeout(1000)
        await page.mouse.move(200, 200)
        await page.wait_for_timeout(1000)
        
        # Клик по кнопке проверки если есть
        verify_selectors = [
            'input[type="submit"]',
            'button[type="submit"]',
            '.btn-primary',
            'input[value*="Verify"]',
            'button:has-text("Verify")'
        ]
        
        for selector in verify_selectors:
            try:
                button = await page.query_selector(selector)
                if button:
                    await button.click()
                    await page.wait_for_timeout(3000)
                    break
            except:
                continue
    
    async def bypass_akamai(self, page: Page) -> bool:
        """Обход Akamai защиты"""
        self.logger.info("🛡️  Обход Akamai защиты...")
        
        try:
            # Эмуляция человеческого поведения
            await page.evaluate("""
                () => {
                    // Удаление свойств, которые выдают автоматизацию
                    delete navigator.__proto__.webdriver;
                    delete window.__proto__.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.__proto__.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.__proto__.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    
                    // Переопределение permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                }
            """)
            
            # Добавляем случайные движения мыши
            viewport = page.viewport_size
            if viewport:
                for _ in range(3):
                    x = random.randint(0, viewport['width'])
                    y = random.randint(0, viewport['height'])
                    await page.mouse.move(x, y)
                    await page.wait_for_timeout(500)
            
            self.logger.info("✅ Akamai успешно обойден")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обхода Akamai: {e}")
            return False
    
    async def bypass_protection(self, page: Page) -> bool:
        """Универсальный обход защиты"""
        self.logger.info("🛡️  Проверка систем защиты...")
        
        # Проверка текущего URL
        current_url = page.url
        domain = urlparse(current_url).netloc.lower()
        
        # Обход в зависимости от домена
        if 'cloudflare' in domain:
            return await self.bypass_cloudflare(page)
        elif 'akamai' in domain:
            return await self.bypass_akamai(page)
        
        # Универсальные методы для любых сайтов
        success = True
        
        # Эмуляция человеческого поведения
        await self._emulate_human_behavior(page)
        
        # Проверка на наличие блокировки
        if await self._is_blocked(page):
            self.logger.warning("⚠️  Обнаружена блокировка, применяем дополнительные методы...")
            success = await self._apply_advanced_bypass(page)
        
        return success
    
    async def _emulate_human_behavior(self, page: Page):
        """Эмуляция человеческого поведения"""
        # Случайные задержки
        await page.wait_for_timeout(random.randint(1000, 3000))
        
        # Случайные скроллы
        await page.evaluate("""
            window.scrollTo({
                top: Math.random() * document.body.scrollHeight,
                behavior: 'smooth'
            });
        """)
        
        await page.wait_for_timeout(1000)
        
        # Случайные движения мыши
        viewport = page.viewport_size
        if viewport:
            for _ in range(2):
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await page.mouse.move(x, y)
                await page.wait_for_timeout(800)
    
    async def _is_blocked(self, page: Page) -> bool:
        """Проверка на блокировку доступа"""
        try:
            content = await page.content()
            block_indicators = [
                'access denied', 'доступ запрещен', 'bot detected',
                'cloudflare', 'captcha', 'recaptcha', '403',
                '404', '500', 'error', 'blocked'
            ]
            
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in block_indicators)
        except:
            return False
    
    async def _apply_advanced_bypass(self, page: Page) -> bool:
        """Применение продвинутых методов обхода"""
        self.logger.info("🔧 Применение продвинутых методов обхода...")
        
        try:
            # Смена User-Agent
            new_user_agent = self.get_random_user_agent()
            await page.set_extra_HTTP_headers({'User-Agent': new_user_agent})
            
            # Очистка cookies и localStorage
            await page.context.clear_cookies()
            await page.evaluate("localStorage.clear();")
            
            # Перезагрузка страницы
            await page.reload(wait_until='networkidle')
            
            # Дополнительная эмуляция поведения
            await self._emulate_human_behavior(page)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка продвинутого обхода: {e}")
            return False
    
    async def random_delay(self):
        """Случайная задержка между действиями"""
        delay = self.get_random_delay()
        self.logger.debug(f"⏳ Задержка: {delay:.2f} сек")
        await asyncio.sleep(delay)
