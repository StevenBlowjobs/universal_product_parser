#!/usr/bin/env python3
"""
Система обработки ошибок и повторных попыток
"""

import asyncio
import time
from functools import wraps
from typing import Dict, Any, Callable, Optional
from .logger import setup_logger


class ParserError(Exception):
    """Базовое исключение для ошибок парсера"""
    
    def __init__(self, message: str, original_error: Exception = None, context: Dict[str, Any] = None):
        self.message = message
        self.original_error = original_error
        self.context = context or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.original_error:
            return f"{self.message} (Original: {self.original_error})"
        return self.message


class NetworkError(ParserError):
    """Ошибка сетевого взаимодействия"""
    pass


class ParseError(ParserError):
    """Ошибка разбора контента"""
    pass


class ConfigurationError(ParserError):
    """Ошибка конфигурации"""
    pass


class AntiDetectionError(ParserError):
    """Ошибка обхода анти-бот защиты"""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0,
                    exceptions: tuple = (Exception,), logger_name: str = "error_handler"):
    """
    Декоратор для повторных попыток при ошибках
    
    Args:
        max_retries: Максимальное количество попыток
        delay: Начальная задержка между попытками
        backoff: Множитель для увеличения задержки
        exceptions: Типы исключений для перехвата
        logger_name: Имя логгера
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = setup_logger(logger_name)
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.warning(f"🔄 Повторная попытка {attempt}/{max_retries} для {func.__name__}")
                    
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"❌ Все попытки завершились ошибкой для {func.__name__}: {e}")
                        raise
                    
                    # Вычисляем задержку с backoff
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"⏳ Ошибка в {func.__name__}, повтор через {wait_time:.1f} сек: {e}")
                    
                    await asyncio.sleep(wait_time)
            
            # Эта строка не должна быть достигнута, но для подстраховки
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = setup_logger(logger_name)
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.warning(f"🔄 Повторная попытка {attempt}/{max_retries} для {func.__name__}")
                    
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"❌ Все попытки завершились ошибкой для {func.__name__}: {e}")
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"⏳ Ошибка в {func.__name__}, повтор через {wait_time:.1f} сек: {e}")
                    
                    time.sleep(wait_time)
            
            raise last_exception
        
        # Возвращаем асинхронный или синхронный wrapper в зависимости от функции
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ErrorHandler:
    """Централизованный обработчик ошибок"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("error_handler")
        self.error_stats = {
            'total_errors': 0,
            'by_type': {},
            'recovered_errors': 0
        }
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Обработка ошибки с логированием и статистикой
        
        Args:
            error: Исключение
            context: Контекст ошибки
            
        Returns:
            Dict: Информация об обработке ошибки
        """
        self.error_stats['total_errors'] += 1
        
        error_type = type(error).__name__
        self.error_stats['by_type'][error_type] = self.error_stats['by_type'].get(error_type, 0) + 1
        
        context = context or {}
        
        # Логирование в зависимости от типа ошибки
        if isinstance(error, NetworkError):
            self.logger.warning(f"🌐 Сетевая ошибка: {error}", extra=context)
        elif isinstance(error, ParseError):
            self.logger.error(f"📄 Ошибка разбора: {error}", extra=context)
        elif isinstance(error, AntiDetectionError):
            self.logger.error(f"🛡️ Ошибка обхода защиты: {error}", extra=context)
        else:
            self.logger.error(f"❌ Неизвестная ошибка: {error}", extra=context)
        
        # Решение о восстановлении в зависимости от типа ошибки
        recovery_action = self._get_recovery_action(error, context)
        
        if recovery_action['can_recover']:
            self.error_stats['recovered_errors'] += 1
            self.logger.info(f"🔄 Восстановление после ошибки: {recovery_action['action']}")
        
        return {
            'error_type': error_type,
            'message': str(error),
            'context': context,
            'recovery_action': recovery_action,
            'timestamp': time.time()
        }
    
    def _get_recovery_action(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Определение действия для восстановления после ошибки"""
        
        if isinstance(error, NetworkError):
            return {
                'can_recover': True,
                'action': 'retry_with_delay',
                'delay': 5,
                'max_retries': 3
            }
        
        elif isinstance(error, AntiDetectionError):
            return {
                'can_recover': True,
                'action': 'change_user_agent_and_retry',
                'delay': 10,
                'max_retries': 2
            }
        
        elif isinstance(error, ParseError):
            # Для ошибок разбора можно попробовать альтернативные селекторы
            return {
                'can_recover': True,
                'action': 'use_fallback_selectors',
                'delay': 1,
                'max_retries': 1
            }
        
        else:
            return {
                'can_recover': False,
                'action': 'abort',
                'reason': 'Unknown error type'
            }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Получение статистики ошибок"""
        return self.error_stats.copy()
    
    def reset_stats(self):
        """Сброс статистики ошибок"""
        self.error_stats = {
            'total_errors': 0,
            'by_type': {},
            'recovered_errors': 0
        }
    
    def create_error_report(self) -> Dict[str, Any]:
        """Создание отчета об ошибках"""
        stats = self.get_error_stats()
        
        return {
            'summary': {
                'total_errors': stats['total_errors'],
                'recovered_errors': stats['recovered_errors'],
                'success_rate': (1 - stats['total_errors'] / max(stats['total_errors'], 1)) * 100,
                'recovery_rate': (stats['recovered_errors'] / max(stats['total_errors'], 1)) * 100
            },
            'details': {
                'errors_by_type': stats['by_type'],
                'timestamp': time.time()
            }
        }


# Глобальный экземпляр обработчика ошибок
global_error_handler = ErrorHandler()

def handle_global_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Глобальная функция обработки ошибок
    
    Args:
        error: Исключение
        context: Контекст ошибки
        
    Returns:
        Dict: Результат обработки
    """
    return global_error_handler.handle_error(error, context)

def get_global_error_stats() -> Dict[str, Any]:
    """Получение глобальной статистики ошибок"""
    return global_error_handler.get_error_stats()
