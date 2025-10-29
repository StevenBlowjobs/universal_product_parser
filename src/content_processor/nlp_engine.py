#!/usr/bin/env python3
"""
NLP движок для анализа и обработки текста
"""

import spacy
import pymorphy3
import nltk
from typing import Dict, List, Optional, Any, Tuple
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class NlpEngine:
    """NLP движок для русского языка"""
    
    def __init__(self):
        self.logger = setup_logger("nlp_engine")
        self._load_models()
    
    def _load_models(self):
        """Загрузка NLP моделей и ресурсов"""
        try:
            # Загрузка spaCy модели для русского языка
            self.logger.info("📥 Загрузка spaCy модели...")
            self.nlp = spacy.load("ru_core_news_lg")
            
            # Инициализация pymorphy3 для морфологического анализа
            self.logger.info("📥 Загрузка pymorphy3...")
            self.morph_analyzer = pymorphy3.MorphAnalyzer()
            
            # Загрузка необходимых ресурсов NLTK
            self.logger.info("📥 Загрузка NLTK ресурсов...")
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
            
            self.logger.info("✅ NLP модели успешно загружены")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки NLP моделей: {e}")
            raise
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Полный анализ текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Dict: Результаты анализа
        """
        if not text:
            return {}
        
        doc = self.nlp(text)
        
        sentences = []
        for sent in doc.sents:
            sentence_analysis = {
                'text': sent.text,
                'tokens': [],
                'entities': [],
                'pos_tags': []
            }
            
            for token in sent:
                token_info = {
                    'text': token.text,
                    'lemma': token.lemma_,
                    'pos': token.pos_,
                    'tag': token.tag_,
                    'dep': token.dep_,
                    'is_alpha': token.is_alpha,
                    'is_stop': token.is_stop
                }
                sentence_analysis['tokens'].append(token_info)
                sentence_analysis['pos_tags'].append(token.pos_)
            
            # Извлечение именованных сущностей
            for ent in sent.ents:
                sentence_analysis['entities'].append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char - sent.start_char,
                    'end': ent.end_char - sent.start_char
                })
            
            sentences.append(sentence_analysis)
        
        return {
            'original_text': text,
            'sentences': sentences,
            'word_count': len([token for token in doc if token.is_alpha]),
            'sentence_count': len(list(doc.sents)),
            'language': 'ru'
        }
    
    def extract_brands_and_models(self, text: str) -> Dict[str, List[str]]:
        """
        Извлечение брендов и моделей из текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Dict: Списки брендов и моделей
        """
        result = {
            'brands': [],
            'models': []
        }
        
        if not text:
            return result
        
        doc = self.nlp(text)
        
        # Паттерны для брендов и моделей
        brand_indicators = ['бренд', 'марка', 'производитель', 'brand', 'make']
        model_indicators = ['модель', 'version', 'тип', 'model']
        
        for sent in doc.sents:
            for token in sent:
                # Поиск брендов (обычно имена собственные в определенном контексте)
                if token.ent_type_ == 'ORG' or token.is_title:
                    # Проверка контекста для брендов
                    for child in token.children:
                        if child.lemma_ in brand_indicators:
                            result['brands'].append(token.text)
                
                # Поиск моделей (обычно комбинации букв и цифр)
                if any(char.isdigit() for char in token.text) and any(char.isalpha() for char in token.text):
                    # Проверка контекста для моделей
                    for child in token.children:
                        if child.lemma_ in model_indicators:
                            result['models'].append(token.text)
        
        # Удаление дубликатов
        result['brands'] = list(set(result['brands']))
        result['models'] = list(set(result['models']))
        
        return result
    
    def extract_technical_terms(self, text: str) -> List[str]:
        """
        Извлечение технических терминов
        
        Args:
            text: Текст для анализа
            
        Returns:
            List: Список технических терминов
        """
        technical_terms = []
        
        if not text:
            return technical_terms
        
        doc = self.nlp(text)
        
        # Паттерны для технических характеристик
        tech_patterns = [
            r'\d+[.,]?\d*\s*(мм|см|м|кг|г|л|мл|Гц|кГц|МГц|Вт|кВт|В|А|ч|°C)',
            r'\b(диаметр|длина|ширина|высота|глубина|вес|объем|мощность|напряжение|ток|частота)\b',
            r'\b(материал|цвет|размер|габариты|технические?|характеристики?|параметры?)\b'
        ]
        
        import re
        for pattern in tech_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                technical_terms.append(match.group())
        
        return list(set(technical_terms))
    
    def restructure_sentence(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """
        Изменение структуры предложения
        
        Args:
            sentence: Исходное предложение
            preserved_terms: Термины для сохранения
            
        Returns:
            str: Перестроенное предложение
        """
        doc = self.nlp(sentence)
        
        # Простое изменение структуры - изменение порядка слов
        words = [token.text for token in doc if not token.is_punct]
        
        if len(words) <= 3:
            return sentence  # Слишком короткое для изменений
        
        # Различные стратегии перестройки
        import random
        strategies = [
            self._reverse_clauses,
            self._change_voice,
            self._reorder_phrases
        ]
        
        strategy = random.choice(strategies)
        return strategy(sentence, preserved_terms)
    
    def _reverse_clauses(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Изменение порядка частей предложения"""
        doc = self.nlp(sentence)
        
        # Поиск союзов для разделения на части
        clauses = []
        current_clause = []
        
        for token in doc:
            current_clause.append(token.text)
            if token.dep_ == 'cc' or token.text in [',', ';']:
                clauses.append(' '.join(current_clause))
                current_clause = []
        
        if current_clause:
            clauses.append(' '.join(current_clause))
        
        if len(clauses) > 1:
            # Меняем порядок частей
            import random
            random.shuffle(clauses)
            return ' '.join(clauses)
        else:
            return sentence
    
    def _change_voice(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Изменение залога предложения (активный/пассивный)"""
        # Упрощенная реализация для русского языка
        # В реальной системе это требовало бы сложного анализа
        return sentence  # Заглушка
    
    def _reorder_phrases(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Изменение порядка фраз в предложении"""
        words = sentence.split()
        
        if len(words) > 4:
            # Меняем местами первые и последние слова
            words[0], words[-1] = words[-1], words[0]
            return ' '.join(words)
        else:
            return sentence
    
    def paraphrase_sentence(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """
        Парафраз предложения
        
        Args:
            sentence: Исходное предложение
            preserved_terms: Термины для сохранения
            
        Returns:
            str: Парафразированное предложение
        """
        # Используем комбинацию методов для парафраза
        methods = [
            self._replace_with_synonyms_simple,
            self._simplify_sentence,
            self._expand_sentence
        ]
        
        import random
        method = random.choice(methods)
        return method(sentence, preserved_terms)
    
    def _replace_with_synonyms_simple(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Простая замена слов синонимами"""
        # Эта функция будет дополнена в synonym_manager
        return sentence
    
    def _simplify_sentence(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Упрощение предложения"""
        doc = self.nlp(sentence)
        
        # Удаление некоторых прилагательных и наречий
        simplified_words = []
        for token in doc:
            if token.pos_ in ['ADJ', 'ADV']:
                # Пропускаем некоторые прилагательные/наречия с вероятностью
                import random
                if random.random() < 0.3:
                    continue
            
            simplified_words.append(token.text)
        
        return ' '.join(simplified_words)
    
    def _expand_sentence(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Расширение предложения дополнительными словами"""
        expanders = [
            'качественный', 'надежный', 'популярный', 'современный',
            'практичный', 'функциональный', 'стильный'
        ]
        
        import random
        if random.random() < 0.5:
            expanded = f"{random.choice(expanders)} {sentence}"
            return expanded
        else:
            return sentence
    
    def correct_grammar(self, text: str) -> str:
        """
        Коррекция грамматики текста
        
        Args:
            text: Текст для коррекции
            
        Returns:
            str: Исправленный текст
        """
        # Базовая коррекция пунктуации
        import re
        
        # Добавление пробелов после знаков препинания
        text = re.sub(r'([.!?])([А-Яа-я])', r'\1 \2', text)
        
        # Удаление лишних пробелов
        text = re.sub(r' +', ' ', text)
        
        # Коррекция регистра в начале предложения
        sentences = re.split(r'([.!?] )', text)
        corrected_sentences = []
        
        for i, sentence in enumerate(sentences):
            if i % 2 == 0 and sentence:  # Основная часть предложения
                if sentence and sentence[0].islower():
                    sentence = sentence[0].upper() + sentence[1:]
                corrected_sentences.append(sentence)
            else:  # Разделитель
                corrected_sentences.append(sentence)
        
        return ''.join(corrected_sentences)
    
    def get_word_lemma(self, word: str) -> str:
        """
        Получение леммы слова
        
        Args:
            word: Слово для лемматизации
            
        Returns:
            str: Лемма слова
        """
        try:
            parsed = self.morph_analyzer.parse(word)[0]
            return parsed.normal_form
        except Exception:
            return word
    
    def get_word_morphology(self, word: str) -> Dict[str, Any]:
        """
        Получение морфологической информации о слове
        
        Args:
            word: Слово для анализа
            
        Returns:
            Dict: Морфологическая информация
        """
        try:
            parsed = self.morph_analyzer.parse(word)[0]
            return {
                'normal_form': parsed.normal_form,
                'tag': str(parsed.tag),
                'score': parsed.score,
                'methods': parsed.methods_stack
            }
        except Exception as e:
            return {
                'normal_form': word,
                'tag': 'UNKN',
                'error': str(e)
            }
