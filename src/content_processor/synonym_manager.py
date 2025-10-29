#!/usr/bin/env python3
"""
Модуль управления словарями синонимов и замены слов
"""

import json
import re
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class SynonymManager:
    """Менеджер синонимов для контекстно-зависимой замены слов"""
    
    def __init__(self, dictionaries_path: str = "data/input/synonym_dictionaries"):
        self.dictionaries_path = Path(dictionaries_path)
        self.logger = setup_logger("synonym_manager")
        self.synonym_dict = {}
        self.technical_terms = set()
        self._load_dictionaries()
    
    def _load_dictionaries(self):
        """Загрузка словарей синонимов и технических терминов"""
        try:
            # Загрузка общего словаря синонимов
            general_path = self.dictionaries_path / "general_synonyms.json"
            if general_path.exists():
                with open(general_path, 'r', encoding='utf-8') as f:
                    self.synonym_dict = json.load(f)
                self.logger.info(f"✅ Загружен общий словарь синонимов: {len(self.synonym_dict)} записей")
            else:
                self.logger.warning("⚠️  Файл general_synonyms.json не найден")
                self._create_default_synonym_dict()
            
            # Загрузка технических терминов
            technical_path = self.dictionaries_path / "technical_terms.json"
            if technical_path.exists():
                with open(technical_path, 'r', encoding='utf-8') as f:
                    technical_data = json.load(f)
                    self.technical_terms = set(technical_data.get('preserved_terms', []))
                self.logger.info(f"✅ Загружены технические термины: {len(self.technical_terms)} терминов")
            else:
                self.logger.warning("⚠️  Файл technical_terms.json не найден")
                self._create_default_technical_terms()
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки словарей: {e}")
            self._create_default_synonym_dict()
            self._create_default_technical_terms()
    
    def _create_default_synonym_dict(self):
        """Создание словаря синонимов по умолчанию"""
        self.synonym_dict = {
            "хороший": ["отличный", "превосходный", "замечательный", "качественный"],
            "плохой": ["неудовлетворительный", "низкокачественный", "слабый"],
            "красивый": ["привлекательный", "эстетичный", "изящный"],
            "большой": ["крупный", "масштабный", "обширный"],
            "маленький": ["небольшой", "компактный", "миниатюрный"],
            "дорогой": ["ценный", "стоимостный", "премиальный"],
            "дешевый": ["экономичный", "бюджетный", "недорогой"],
            "новый": ["современный", "актуальный", "свежий"],
            "старый": ["устаревший", "архаичный", "ветхий"],
            "быстрый": ["скоростной", "оперативный", "шустрый"],
            "медленный": ["неторопливый", "замедленный", "размеренный"],
            "легкий": ["простой", "нетрудный", "элементарный"],
            "тяжелый": ["сложный", "затруднительный", "напряженный"],
            "важный": ["значительный", "критический", "приоритетный"],
            "полезный": ["ценный", "практичный", "функциональный"],
            "интересный": ["увлекательный", "захватывающий", "любопытный"],
            "популярный": ["востребованный", "распространенный", "известный"],
            "уникальный": ["эксклюзивный", "неповторимый", "особенный"],
            "надежный": ["доверительный", "стабильный", "прочный"],
            "удобный": ["комфортный", "эргономичный", "практичный"]
        }
        self.logger.info("✅ Создан словарь синонимов по умолчанию")
    
    def _create_default_technical_terms(self):
        """Создание списка технических терминов по умолчанию"""
        self.technical_terms = {
            # Единицы измерения
            "мм", "см", "м", "км", "г", "кг", "л", "мл", "Вт", "кВт", 
            "Гц", "кГц", "МГц", "В", "А", "Ом", "°C", "°F",
            
            # Технические характеристики
            "диаметр", "длина", "ширина", "высота", "глубина", "толщина",
            "объем", "вес", "мощность", "напряжение", "ток", "сопротивление",
            "частота", "скорость", "давление", "температура",
            
            # Материалы
            "сталь", "алюминий", "пластик", "дерево", "стекло", "керамика",
            "резина", "силикон", "текстиль", "кожа", "металл",
            
            # Производственные термины
            "гарантия", "производитель", "модель", "артикул", "серия",
            "партия", "сборка", "качество", "стандарт", "сертификат"
        }
        self.logger.info("✅ Создан список технических терминов по умолчанию")
    
    def get_synonym(self, word: str, context: str = "", pos: str = "") -> Optional[str]:
        """
        Получение синонима для слова с учетом контекста
        
        Args:
            word: Слово для замены
            context: Контекст предложения
            pos: Часть речи слова
            
        Returns:
            str: Синоним или None если замена не нужна
        """
        # Приведение к нижнему регистру для поиска
        word_lower = word.lower()
        
        # Проверка технических терминов
        if self._is_technical_term(word_lower, context):
            return None
        
        # Поиск в словаре синонимов
        if word_lower in self.synonym_dict:
            synonyms = self.synonym_dict[word_lower]
            
            # Фильтрация по контексту если нужно
            filtered_synonyms = self._filter_by_context(synonyms, context, pos)
            
            if filtered_synonyms:
                import random
                return random.choice(filtered_synonyms)
            elif synonyms:
                import random
                return random.choice(synonyms)
        
        return None
    
    def _is_technical_term(self, word: str, context: str) -> bool:
        """Проверка является ли слово техническим термином"""
        # Прямое совпадение
        if word in self.technical_terms:
            return True
        
        # Проверка по паттернам (числа с единицами измерения)
        technical_patterns = [
            r'\d+[.,]?\d*\s*(мм|см|м|кг|г|л|мл|Вт|кВт|В|А|Гц)',
            r'\b(диаметр|длина|ширина|высота|вес|мощность)\b',
            r'\b(модель|артикул|серия|гарантия)\b'
        ]
        
        for pattern in technical_patterns:
            if re.search(pattern, f"{word} {context}", re.IGNORECASE):
                return True
        
        return False
    
    def _filter_by_context(self, synonyms: List[str], context: str, pos: str) -> List[str]:
        """Фильтрация синонимов по контексту и части речи"""
        # TODO: Реализовать более сложную логику фильтрации по контексту
        # Пока возвращаем все синонимы
        return synonyms
    
    def add_synonym(self, word: str, synonym: str):
        """Добавление синонима в словарь"""
        word_lower = word.lower()
        
        if word_lower not in self.synonym_dict:
            self.synonym_dict[word_lower] = []
        
        if synonym not in self.synonym_dict[word_lower]:
            self.synonym_dict[word_lower].append(synonym)
            self.logger.debug(f"✅ Добавлен синоним: {word} -> {synonym}")
    
    def add_technical_term(self, term: str):
        """Добавление технического термина"""
        self.technical_terms.add(term.lower())
        self.logger.debug(f"✅ Добавлен технический термин: {term}")
    
    def save_dictionaries(self):
        """Сохранение словарей в файлы"""
        try:
            # Создание директории если нужно
            self.dictionaries_path.mkdir(parents=True, exist_ok=True)
            
            # Сохранение синонимов
            general_path = self.dictionaries_path / "general_synonyms.json"
            with open(general_path, 'w', encoding='utf-8') as f:
                json.dump(self.synonym_dict, f, indent=2, ensure_ascii=False)
            
            # Сохранение технических терминов
            technical_path = self.dictionaries_path / "technical_terms.json"
            technical_data = {
                "preserved_terms": list(self.technical_terms),
                "metadata": {
                    "total_terms": len(self.technical_terms),
                    "updated_at": "auto_generated"
                }
            }
            with open(technical_path, 'w', encoding='utf-8') as f:
                json.dump(technical_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("💾 Словари успешно сохранены")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения словарей: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики словарей"""
        return {
            "synonym_entries": len(self.synonym_dict),
            "total_synonyms": sum(len(synonyms) for synonyms in self.synonym_dict.values()),
            "technical_terms": len(self.technical_terms),
            "average_synonyms_per_word": sum(len(synonyms) for synonyms in self.synonym_dict.values()) / max(1, len(self.synonym_dict))
        }
