#!/usr/bin/env python3
"""
Менеджер резервного копирования данных
"""

import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class BackupManager:
    """Управление резервным копированием данных"""
    
    def __init__(self, backup_dir: str = "data/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger("backup_manager")
        
        self.backup_settings = {
            'max_backups': 30,  # Максимум 30 бэкапов
            'backup_interval_hours': 24,  # Раз в сутки
            'compress_backups': True,
            'include_logs': True,
            'include_configs': True
        }
    
    @retry_on_failure(max_retries=2)
    def create_backup(self, 
                     data_files: List[str] = None,
                     backup_name: str = None,
                     description: str = "") -> str:
        """
        Создание резервной копии
        
        Args:
            data_files: Список файлов для бэкапа
            backup_name: Имя бэкапа (опционально)
            description: Описание бэкапа
            
        Returns:
            str: Путь к созданному бэкапу
        """
        self.logger.info("💾 Создание резервной копии")
        
        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"
            
            backup_path = self.backup_dir / backup_name
            
            if self.backup_settings['compress_backups']:
                backup_path = backup_path.with_suffix('.zip')
                self._create_compressed_backup(backup_path, data_files, description)
            else:
                backup_path.mkdir(parents=True, exist_ok=True)
                self._create_directory_backup(backup_path, data_files, description)
            
            # Очистка старых бэкапов
            self._cleanup_old_backups()
            
            self.logger.info(f"✅ Резервная копия создана: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания бэкапа: {e}")
            raise
    
    def _create_compressed_backup(self, backup_path: Path, data_files: List[str], description: str):
        """Создание сжатого бэкапа"""
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавление файлов данных
            if data_files:
                for file_pattern in data_files:
                    for file_path in Path('data').rglob(file_pattern):
                        if file_path.is_file():
                            arcname = file_path.relative_to('data')
                            zipf.write(file_path, arcname)
            
            # Добавление логов
            if self.backup_settings['include_logs']:
                for log_file in Path('data/output/logs').rglob('*.log'):
                    if log_file.is_file():
                        arcname = log_file.relative_to('data')
                        zipf.write(log_file, arcname)
            
            # Добавление конфигов
            if self.backup_settings['include_configs']:
                for config_file in Path('config').rglob('*'):
                    if config_file.is_file():
                        arcname = config_file.relative_to('.')
                        zipf.write(config_file, arcname)
            
            # Добавление метаданных
            metadata = {
                'backup_date': datetime.now().isoformat(),
                'description': description,
                'files_included': len(zipf.filelist),
                'backup_size': backup_path.stat().st_size if backup_path.exists() else 0
            }
            
            zipf.writestr('backup_metadata.json', 
                         json.dumps(metadata, ensure_ascii=False, indent=2))
    
    def _create_directory_backup(self, backup_path: Path, data_files: List[str], description: str):
        """Создание бэкапа в директории"""
        # Копирование файлов данных
        if data_files:
            for file_pattern in data_files:
                for file_path in Path('data').rglob(file_pattern):
                    if file_path.is_file():
                        relative_path = file_path.relative_to('data')
                        target_path = backup_path / relative_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, target_path)
        
        # Сохранение метаданных
        metadata = {
            'backup_date': datetime.now().isoformat(),
            'description': description,
            'backup_type': 'directory'
        }
        
        with open(backup_path / 'backup_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _cleanup_old_backups(self):
        """Очистка старых бэкапов"""
        try:
            backups = []
            
            # Сбор всех бэкапов
            for backup_file in self.backup_dir.iterdir():
                if backup_file.is_file() and backup_file.suffix in ['.zip', '']:
                    creation_time = datetime.fromtimestamp(backup_file.stat().st_ctime)
                    backups.append((backup_file, creation_time))
            
            # Сортировка по дате создания (новые сначала)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Удаление старых бэкапов
            if len(backups) > self.backup_settings['max_backups']:
                for backup_file, _ in backups[self.backup_settings['max_backups']:]:
                    try:
                        if backup_file.is_file():
                            backup_file.unlink()
                        else:
                            shutil.rmtree(backup_file)
                        self.logger.info(f"🗑️ Удален старый бэкап: {backup_file}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Не удалось удалить бэкап {backup_file}: {e}")
                        
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка очистки бэкапов: {e}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Список доступных бэкапов
        
        Returns:
            List[Dict]: Информация о бэкапах
        """
        backups_info = []
        
        for backup_file in self.backup_dir.iterdir():
            if backup_file.is_file() and backup_file.suffix == '.zip':
                try:
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        metadata_str = zipf.read('backup_metadata.json').decode('utf-8')
                        metadata = json.loads(metadata_str)
                        
                        backups_info.append({
                            'name': backup_file.stem,
                            'path': str(backup_file),
                            'date': metadata.get('backup_date'),
                            'description': metadata.get('description', ''),
                            'size': backup_file.stat().st_size,
                            'file_count': metadata.get('files_included', 0)
                        })
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось прочитать метаданные бэкапа {backup_file}: {e}")
        
        # Сортировка по дате (новые сначала)
        backups_info.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return backups_info
    
    def restore_backup(self, backup_name: str, target_dir: str = "data") -> bool:
        """
        Восстановление из бэкапа
        
        Args:
            backup_name: Имя бэкапа
            target_dir: Целевая директория
            
        Returns:
            bool: Успешность восстановления
        """
        self.logger.info(f"🔄 Восстановление из бэкапа: {backup_name}")
        
        try:
            backup_path = self.backup_dir / f"{backup_name}.zip"
            
            if not backup_path.exists():
                self.logger.error(f"❌ Бэкап не найден: {backup_path}")
                return False
            
            # Создание временной директории для восстановления
            temp_dir = Path('data/temp/restore')
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Распаковка бэкапа
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Копирование файлов в целевую директорию
            target_path = Path(target_dir)
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(temp_dir)
                    final_path = target_path / relative_path
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, final_path)
            
            # Очистка временной директории
            shutil.rmtree(temp_dir)
            
            self.logger.info(f"✅ Восстановление завершено: {backup_name} -> {target_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка восстановления бэкапа: {e}")
            return False
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Получение статистики бэкапов
        
        Returns:
            Dict: Статистика бэкапов
        """
        backups = self.list_backups()
        
        total_size = sum(backup['size'] for backup in backups)
        total_files = sum(backup['file_count'] for backup in backups)
        
        return {
            'total_backups': len(backups),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'total_files': total_files,
            'oldest_backup': backups[-1]['date'] if backups else None,
            'newest_backup': backups[0]['date'] if backups else None
        }


# Для JSON сериализации в методах бэкапа
import json
