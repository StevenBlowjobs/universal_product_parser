#!/usr/bin/env python3
"""
Сетевые утилиты для проверки соединения, прокси и загрузки
"""

import aiohttp
import asyncio
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import time
from pathlib import Path
from .logger import setup_logger


class NetworkUtils:
    """Утилиты для сетевых операций и проверки соединения"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("network_utils")
        self.session = None
    
    async def check_internet_connection(self, timeout: int = 10) -> bool:
        """
        Проверка интернет-соединения
        
        Args:
            timeout: Таймаут в секундах
            
        Returns:
            bool: Есть ли соединение
        """
        test_urls = [
            "https://www.google.com",
            "https://www.cloudflare.com",
            "https://www.yandex.ru"
        ]
        
        for url in test_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            self.logger.info("✅ Интернет-соединение активно")
                            return True
            except Exception as e:
                self.logger.debug(f"❌ Не удалось подключиться к {url}: {e}")
                continue
        
        self.logger.error("❌ Отсутствует интернет-соединение")
        return False
    
    async def check_site_availability(self, url: str, timeout: int = 15) -> Dict[str, Any]:
        """
        Проверка доступности сайта
        
        Args:
            url: URL для проверки
            timeout: Таймаут в секундах
            
        Returns:
            Dict: Результаты проверки
        """
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        'url': url,
                        'available': True,
                        'status_code': response.status,
                        'response_time': round(response_time, 2),
                        'content_type': response.headers.get('content-type', ''),
                        'server': response.headers.get('server', ''),
                        'size_bytes': int(response.headers.get('content-length', 0))
                    }
                    
                    self.logger.info(f"✅ Сайт доступен: {url} ({response.status})")
                    return result
                    
        except asyncio.TimeoutError:
            self.logger.error(f"⏰ Таймаут при проверке {url}")
            return {
                'url': url,
                'available': False,
                'error': 'timeout',
                'response_time': timeout
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки {url}: {e}")
            return {
                'url': url,
                'available': False,
                'error': str(e),
                'response_time': round(time.time() - start_time, 2)
            }
    
    async def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
        """
        Асинхронная загрузка файла
        
        Args:
            url: URL файла
            save_path: Путь для сохранения
            timeout: Таймаут в секундах
            
        Returns:
            bool: Успешность загрузки
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Создание директории если нужно
                        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        
                        self.logger.info(f"✅ Файл загружен: {url} -> {save_path}")
                        return True
                    else:
                        self.logger.error(f"❌ Ошибка HTTP {response.status} при загрузке {url}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки {url}: {e}")
            return False
    
    async def test_proxy(self, proxy_url: str, test_url: str = "https://httpbin.org/ip") -> Dict[str, Any]:
        """
        Тестирование прокси-сервера
        
        Args:
            proxy_url: URL прокси (http://ip:port или socks5://ip:port)
            test_url: URL для тестирования
            
        Returns:
            Dict: Результаты теста
        """
        start_time = time.time()
        
        try:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(test_url, proxy=proxy_url) as response:
                    response_time = time.time() - start_time
                    data = await response.json()
                    
                    return {
                        'proxy': proxy_url,
                        'working': True,
                        'response_time': round(response_time, 2),
                        'your_ip': data.get('origin', ''),
                        'status_code': response.status
                    }
                    
        except Exception as e:
            return {
                'proxy': proxy_url,
                'working': False,
                'error': str(e),
                'response_time': round(time.time() - start_time, 2)
            }
    
    async def batch_test_proxies(self, proxies: List[str], max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """
        Массовое тестирование прокси-серверов
        
        Args:
            proxies: Список прокси
            max_concurrent: Максимальное количество одновременных тестов
            
        Returns:
            List: Результаты тестирования
        """
        self.logger.info(f"🔍 Тестирование {len(proxies)} прокси...")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def test_with_semaphore(proxy):
            async with semaphore:
                return await self.test_proxy(proxy)
        
        tasks = [test_with_semaphore(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтрация рабочих прокси
        working_proxies = [r for r in results if isinstance(r, dict) and r.get('working')]
        
        self.logger.info(f"✅ Найдено рабочих прокси: {len(working_proxies)}/{len(proxies)}")
        return working_proxies
    
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Валидация URL
        
        Args:
            url: URL для валидации
            
        Returns:
            Tuple: (Валиден ли, Сообщение об ошибке)
        """
        try:
            result = urlparse(url)
            
            if not all([result.scheme, result.netloc]):
                return False, "Неверный формат URL"
            
            if result.scheme not in ['http', 'https']:
                return False, "Поддерживаются только HTTP и HTTPS"
            
            return True, "URL валиден"
            
        except Exception as e:
            return False, f"Ошибка валидации: {e}"
    
    async def get_redirect_history(self, url: str, max_redirects: int = 10) -> List[Dict[str, str]]:
        """
        Получение истории редиректов
        
        Args:
            url: Исходный URL
            max_redirects: Максимальное количество редиректов
            
        Returns:
            List: История редиректов
        """
        redirects = []
        current_url = url
        
        for i in range(max_redirects):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(current_url, allow_redirects=False) as response:
                        
                        redirect_info = {
                            'url': current_url,
                            'status_code': response.status,
                            'location': response.headers.get('location', '')
                        }
                        redirects.append(redirect_info)
                        
                        if response.status in [301, 302, 303, 307, 308]:
                            current_url = urljoin(current_url, response.headers.get('location'))
                        else:
                            break
                            
            except Exception as e:
                self.logger.error(f"❌ Ошибка при отслеживании редиректа: {e}")
                break
        
        return redirects
    
    def get_domain_info(self, url: str) -> Dict[str, str]:
        """
        Получение информации о домене
        
        Args:
            url: URL для анализа
            
        Returns:
            Dict: Информация о домене
        """
        try:
            parsed = urlparse(url)
            
            return {
                'domain': parsed.netloc,
                'subdomain': '.'.join(parsed.netloc.split('.')[:-2]),
                'tld': '.'.join(parsed.netloc.split('.')[-2:]),
                'scheme': parsed.scheme,
                'path': parsed.path,
                'full_domain': parsed.netloc
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа домена {url}: {e}")
            return {}
    
    async def close(self):
        """Закрытие сетевых сессий"""
        if self.session:
            await self.session.close()
