#!/usr/bin/env python3
"""
Модуль управления файлами, кэшированием и данными
"""

import json
import pickle
import csv
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from .logger import setup_logger


class FileManager:
    """Управление файлами, кэшем и структурами данных"""
    
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.logger = setup_logger("file_manager")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        directories = [
            'input',
            'output/excel_exports',
            'output/processed_images/original',
            'output/processed_images/no_watermark', 
            'output/processed_images/no_background',
            'output/processed_images/final',
            'output/logs',
            'temp/cache',
            'temp/session_data'
        ]
        
        for directory in directories:
            path = self.base_path / directory
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"✅ Создана директория: {path}")
    
    def save_json(self, data: Any, filename: str, subfolder: str = "") -> str:
        """
        Сохранение данных в JSON файл
        
        Args:
            data: Данные для сохранения
            filename: Имя файла
            subfolder: Подпапка для сохранения
            
        Returns:
            str: Путь к сохраненному файлу
        """
        filepath = self._build_path(filename, subfolder, 'json')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.debug(f"💾 JSON сохранен: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения JSON {filepath}: {e}")
            raise
    
    def load_json(self, filename: str, subfolder: str = "") -> Any:
        """Загрузка данных из JSON файла"""
        filepath = self._build_path(filename, subfolder, 'json')
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.debug(f"📂 JSON загружен: {filepath}")
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки JSON {filepath}: {e}")
            return None
    
    def save_cache(self, key: str, data: Any, expire_hours: int = 24) -> str:
        """
        Сохранение данных в кэш с TTL
        
        Args:
            key: Ключ кэша
            data: Данные для кэширования
            expire_hours: Время жизни в часах
            
        Returns:
            str: Путь к файлу кэша
        """
        cache_data = {
            'data': data,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=expire_hours)).isoformat()
        }
        
        # Создание безопасного имени файла из ключа
        safe_key = self._safe_filename(key)
        filepath = self.base_path / 'temp' / 'cache' / f"{safe_key}.pkl"
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(cache_data, f)
            
            self.logger.debug(f"💾 Кэш сохранен: {key} -> {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения кэша {key}: {e}")
            raise
    
    def load_cache(self, key: str) -> Any:
        """Загрузка данных из кэша с проверкой TTL"""
        safe_key = self._safe_filename(key)
        filepath = self.base_path / 'temp' / 'cache' / f"{safe_key}.pkl"
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Проверка срока годности
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.now() > expires_at:
                self.logger.debug(f"🗑️ Кэш просрочен: {key}")
                filepath.unlink()  # Удаляем просроченный кэш
                return None
            
            self.logger.debug(f"📂 Кэш загружен: {key}")
            return cache_data['data']
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки кэша {key}: {e}")
            return None
    
    def save_image(self, image_data: bytes, filename: str, category: str = "original") -> str:
        """
        Сохранение изображения с категоризацией
        
        Args:
            image_data: Байты изображения
            filename: Имя файла
            category: Категория (original, no_watermark, no_background, final)
            
        Returns:
            str: Путь к сохраненному изображению
        """
        valid_categories = ['original', 'no_watermark', 'no_background', 'final']
        if category not in valid_categories:
            raise ValueError(f"Неверная категория. Допустимо: {valid_categories}")
        
        filepath = self.base_path / 'output' / 'processed_images' / category / filename
        
        try:
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            self.logger.debug(f"🖼️ Изображение сохранено: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения изображения {filepath}: {e}")
            raise
    
    def load_image(self, filename: str, category: str = "original") -> Optional[bytes]:
        """Загрузка изображения по категории"""
        filepath = self.base_path / 'output' / 'processed_images' / category / filename
        
        try:
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            self.logger.debug(f"📂 Изображение загружено: {filepath}")
            return image_data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки изображения {filepath}: {e}")
            return None
    
    def save_excel_backup(self, data: List[Dict], prefix: str = "products") -> str:
        """
        Создание резервной копии данных в JSON перед экспортом в Excel
        
        Args:
            data: Данные для резервного копирования
            prefix: Префикс имени файла
            
        Returns:
            str: Путь к резервной копии
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_backup_{timestamp}.json"
        
        backup_data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_items': len(data),
                'prefix': prefix
            },
            'products': data
        }
        
        return self.save_json(backup_data, filename, 'temp/session_data')
    
    def list_files(self, pattern: str = "*", subfolder: str = "") -> List[Path]:
        """Список файлов по шаблону"""
        directory = self.base_path / subfolder if subfolder else self.base_path
        return list(directory.rglob(pattern))
    
    def cleanup_old_files(self, days: int = 7, pattern: str = "*"):
        """
        Очистка старых файлов
        
        Args:
            days: Удалять файлы старше этого количества дней
            pattern: Шаблон для поиска файлов
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for filepath in self.list_files(pattern):
            if filepath.is_file():
                file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        filepath.unlink()
                        self.logger.debug(f"🗑️ Удален старый файл: {filepath}")
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка удаления {filepath}: {e}")
    
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """Получение информации о файле"""
        path = Path(filepath)
        
        if not path.exists():
            return {}
        
        stat = path.stat()
        return {
            'path': str(path),
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified_at': datetime.fromtimestamp(stat.st_mtime),
            'created_at': datetime.fromtimestamp(stat.st_ctime),
            'extension': path.suffix.lower(),
            'is_file': path.is_file(),
            'is_dir': path.is_dir()
        }
    
    def _build_path(self, filename: str, subfolder: str, extension: str) -> Path:
        """Построение полного пути к файлу"""
        if subfolder:
            path = self.base_path / subfolder / f"{filename}.{extension}"
        else:
            path = self.base_path / f"{filename}.{extension}"
        
        # Создание директорий если нужно
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    def _safe_filename(self, filename: str) -> str:
        """Создание безопасного имени файла"""
        # Замена небезопасных символов
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Удаление лишних подчеркиваний
        safe_name = re.sub(r'_+', '_', safe_name)
        # Ограничение длины
        return safe_name[:100]
