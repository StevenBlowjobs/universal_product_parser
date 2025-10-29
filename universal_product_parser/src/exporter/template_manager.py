#!/usr/bin/env python3
"""
Менеджер шаблонов Excel
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..utils.logger import setup_logger


class TemplateManager:
    """Управление шаблонами Excel отчетов"""
    
    def __init__(self, templates_dir: str = "data/input/templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger("template_manager")
        
        # Стандартные шаблоны
        self.default_templates = {
            "basic": {
                "sheets": ["Товары", "Сводка"],
                "columns": {
                    "Товары": ["Название", "Цена", "Описание", "Категория", "URL"]
                },
                "formatting": {
                    "header_color": "366092",
                    "auto_adjust_columns": True
                }
            },
            "detailed": {
                "sheets": ["Товары", "Сравнение цен", "Анализ трендов", "Валидация", "Сводка"],
                "columns": {
                    "Товары": ["Название", "Цена", "Описание", "Категория", "URL", "Бренд", "Рейтинг"],
                    "Сравнение цен": ["Товар", "Старая цена", "Новая цена", "Изменение (%)", "Тип изменения"]
                },
                "formatting": {
                    "header_color": "4472C4", 
                    "auto_adjust_columns": True,
                    "apply_borders": True
                }
            }
        }
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение шаблона по имени
        
        Args:
            template_name: Имя шаблона
            
        Returns:
            Dict: Настройки шаблона
        """
        # Сначала проверяем пользовательские шаблоны
        custom_template = self._load_custom_template(template_name)
        if custom_template:
            return custom_template
        
        # Затем стандартные шаблоны
        if template_name in self.default_templates:
            return self.default_templates[template_name]
        
        self.logger.warning(f"⚠️ Шаблон '{template_name}' не найден, используется basic")
        return self.default_templates.get("basic")
    
    def _load_custom_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Загрузка пользовательского шаблона"""
        template_file = self.templates_dir / f"{template_name}.json"
        
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки шаблона {template_name}: {e}")
        
        return None
    
    def save_template(self, template_name: str, template_config: Dict[str, Any]) -> bool:
        """
        Сохранение пользовательского шаблона
        
        Args:
            template_name: Имя шаблона
            template_config: Конфигурация шаблона
            
        Returns:
            bool: Успешность сохранения
        """
        try:
            template_file = self.templates_dir / f"{template_name}.json"
            
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Шаблон '{template_name}' сохранен")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения шаблона: {e}")
            return False
    
    def list_templates(self) -> List[str]:
        """
        Список доступных шаблонов
        
        Returns:
            List[str]: Имена шаблонов
        """
        templates = list(self.default_templates.keys())
        
        # Добавляем пользовательские шаблоны
        for template_file in self.templates_dir.glob("*.json"):
            templates.append(template_file.stem)
        
        return templates
    
    def create_custom_template(self, 
                             template_name: str,
                             sheets: List[str],
                             columns: Dict[str, List[str]],
                             formatting: Dict[str, Any] = None) -> bool:
        """
        Создание пользовательского шаблона
        
        Args:
            template_name: Имя шаблона
            sheets: Список листов
            columns: Колонки для каждого листа
            formatting: Настройки форматирования
            
        Returns:
            bool: Успешность создания
        """
        template_config = {
            "sheets": sheets,
            "columns": columns,
            "formatting": formatting or {
                "header_color": "366092",
                "auto_adjust_columns": True
            }
        }
        
        return self.save_template(template_name, template_config)
    
    def validate_template(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидация конфигурации шаблона
        
        Args:
            template_config: Конфигурация шаблона
            
        Returns:
            Dict: Результаты валидации
        """
        errors = []
        warnings = []
        
        # Проверка обязательных полей
        if 'sheets' not in template_config:
            errors.append("Отсутствует поле 'sheets'")
        elif not isinstance(template_config['sheets'], list):
            errors.append("Поле 'sheets' должно быть списком")
        
        if 'columns' not in template_config:
            errors.append("Отсутствует поле 'columns'")
        elif not isinstance(template_config['columns'], dict):
            errors.append("Поле 'columns' должно быть словарем")
        
        # Проверка согласованности
        if 'sheets' in template_config and 'columns' in template_config:
            for sheet in template_config['sheets']:
                if sheet not in template_config['columns']:
                    warnings.append(f"Для листа '{sheet}' не указаны колонки")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
