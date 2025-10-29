#!/usr/bin/env python3
"""
Настройка логирования для всего проекта
"""

import logging
import logging.config
from pathlib import Path
import sys
from typing import Optional


def setup_logger(name: str = "root", config_path: str = "config/logging_config.conf") -> logging.Logger:
    """
    Настройка логгера с конфигурацией из файла
    
    Args:
        name: Имя логгера
        config_path: Путь к файлу конфигурации
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    try:
        config_file = Path(config_path)
        if config_file.exists():
            logging.config.fileConfig(config_path, disable_existing_loggers=False)
        else:
            # Fallback к базовой конфигурации
            _setup_basic_logging()
            
        logger = logging.getLogger(name)
        
        # Создание директорий для логов если нужно
        log_dir = Path("data/output/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return logger
        
    except Exception as e:
        print(f"❌ Ошибка настройки логирования: {e}")
        return _setup_basic_logging(name)


def _setup_basic_logging(name: str = "root") -> logging.Logger:
    """Базовая настройка логирования если конфиг недоступен"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный обработчик
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Файловый обработчик
        try:
            log_dir = Path("data/output/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_dir / "parser.log", encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"⚠️ Не удалось настроить файловое логирование: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Получение логгера по имени
    
    Args:
        name: Имя логгера
        
    Returns:
        logging.Logger: Логгер
    """
    return logging.getLogger(name)
