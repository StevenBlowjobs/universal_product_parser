#!/usr/bin/env python3
"""
Главный модуль переписывания текстов товаров
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from .nlp_engine import NlpEngine
from .synonym_manager import SynonymManager
from .content_validator import ContentValidator
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class TextRewriter:
    """Основной класс для переписывания текстов с сохранением смысла"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("text_rewriter")
        self.nlp_engine = NlpEngine()
        self.synonym_manager = SynonymManager()
        self.validator = ContentValidator()
        
        # Настройки переписывания
        self.rewrite_settings = {
            'synonym_replacement_rate': 0.7,
            'sentence_reorder_rate': 0.5,
            'structure_change_rate': 0.8,
            'preserve_technical_terms': True,
            'min_meaning_preservation': 0.8
        }
        
        # Обновление настроек из конфига
        if 'content_rewriting' in self.config:
            self.rewrite_settings.update(self.config['content_rewriting'])
    
    @retry_on_failure(max_retries=2)
    def rewrite_description(self, original_text: str, product_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Переписывание описания товара с сохранением смысла
        
        Args:
            original_text: Исходный текст описания
            product_context: Контекст товара (характеристики, категория и т.д.)
            
        Returns:
            Dict: Результаты переписывания
        """
        if not original_text or not isinstance(original_text, str):
            return {
                'original': original_text,
                'rewritten': original_text,
                'success': False,
                'error': 'Invalid input text'
            }
        
        self.logger.info(f"📝 Переписывание текста (длина: {len(original_text)})")
        
        try:
            # Предварительная обработка текста
            cleaned_text = self._preprocess_text(original_text)
            
            # Сохранение технических характеристик
            preserved_terms = self._extract_preserved_terms(cleaned_text, product_context)
            
            # Анализ текста с помощью NLP
            analyzed_text = self.nlp_engine.analyze_text(cleaned_text)
            
            # Переписывание текста
            rewritten_text = self._rewrite_with_nlp(analyzed_text, preserved_terms)
            
            # Пост-обработка
            final_text = self._postprocess_text(rewritten_text, preserved_terms)
            
            # Валидация результата
            validation_result = self.validator.validate_rewriting(
                original_text, final_text, self.rewrite_settings['min_meaning_preservation']
            )
            
            result = {
                'original': original_text,
                'rewritten': final_text,
                'success': validation_result['is_valid'],
                'preserved_terms': preserved_terms,
                'validation': validation_result,
                'changes_made': self._calculate_changes(original_text, final_text)
            }
            
            if validation_result['is_valid']:
                self.logger.info("✅ Текст успешно переписан")
            else:
                self.logger.warning("⚠️  Текст переписан, но валидация не пройдена")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка переписывания текста: {e}")
            return {
                'original': original_text,
                'rewritten': original_text,
                'success': False,
                'error': str(e)
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Предварительная обработка текста"""
        # Удаление лишних пробелов и переносов
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Нормализация пунктуации
        text = re.sub(r'\.{2,}', '...', text)
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)
        
        # Удаление специальных символов (кроме пунктуации)
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\(\)]', '', text)
        
        return text
    
    def _extract_preserved_terms(self, text: str, product_context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Извлечение терминов для сохранения"""
        preserved = {
            'technical_specs': [],
            'brands': [],
            'models': [],
            'measurements': [],
            'materials': []
        }
        
        # Извлечение технических характеристик из контекста
        if product_context and 'characteristics' in product_context:
            chars = product_context['characteristics']
            for key, value in chars.items():
                if isinstance(value, (int, float)):
                    preserved['technical_specs'].append(f"{key}: {value}")
                elif isinstance(value, str) and any(unit in value.lower() for unit in ['mm', 'cm', 'kg', 'g', 'l', 'ml']):
                    preserved['measurements'].append(f"{key} {value}")
        
        # Извлечение брендов и моделей из текста
        brands_models = self.nlp_engine.extract_brands_and_models(text)
        preserved['brands'].extend(brands_models.get('brands', []))
        preserved['models'].extend(brands_models.get('models', []))
        
        # Извлечение технических спецификаций из текста
        tech_terms = self.nlp_engine.extract_technical_terms(text)
        preserved['technical_specs'].extend(tech_terms)
        
        # Удаление дубликатов
        for key in preserved:
            preserved[key] = list(set(preserved[key]))
        
        return preserved
    
    def _rewrite_with_nlp(self, analyzed_text: Dict[str, Any], preserved_terms: Dict[str, List[str]]) -> str:
        """Переписывание текста с использованием NLP"""
        sentences = analyzed_text.get('sentences', [])
        
        if not sentences:
            return analyzed_text.get('original_text', '')
        
        rewritten_sentences = []
        
        for sentence in sentences:
            # Пропускаем предложения с важными техническими терминами
            if self._contains_preserved_terms(sentence['text'], preserved_terms):
                rewritten_sentences.append(sentence['text'])
                continue
            
            # Переписываем предложение
            rewritten_sentence = self._rewrite_sentence(sentence, preserved_terms)
            rewritten_sentences.append(rewritten_sentence)
        
        # Изменение порядка предложений (с определенной вероятностью)
        if len(rewritten_sentences) > 1 and self._should_reorder():
            rewritten_sentences = self._reorder_sentences(rewritten_sentences)
        
        return ' '.join(rewritten_sentences)
    
    def _rewrite_sentence(self, sentence: Dict[str, Any], preserved_terms: Dict[str, List[str]]) -> str:
        """Переписывание отдельного предложения"""
        original_sentence = sentence['text']
        
        # Различные методы переписывания
        methods = [
            self._replace_with_synonyms,
            self._change_sentence_structure,
            self._paraphrase_sentence
        ]
        
        # Выбор метода в зависимости от длины и сложности предложения
        if len(sentence['tokens']) < 5:
            # Короткие предложения - простая замена синонимов
            return self._replace_with_synonyms(original_sentence, preserved_terms)
        else:
            # Длинные предложения - комбинация методов
            method = self._choose_rewrite_method(sentence)
            return method(original_sentence, preserved_terms)
    
    def _replace_with_synonyms(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Замена слов синонимами"""
        words = sentence.split()
        rewritten_words = []
        
        for word in words:
            # Пропускаем сохраненные термины
            if self._is_preserved_term(word, preserved_terms):
                rewritten_words.append(word)
                continue
            
            # Замена с определенной вероятностью
            if self._should_replace_word():
                synonym = self.synonym_manager.get_synonym(word, context=sentence)
                rewritten_words.append(synonym if synonym else word)
            else:
                rewritten_words.append(word)
        
        return ' '.join(rewritten_words)
    
    def _change_sentence_structure(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Изменение структуры предложения"""
        # Используем NLP для анализа и изменения структуры
        return self.nlp_engine.restructure_sentence(sentence, preserved_terms)
    
    def _paraphrase_sentence(self, sentence: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Парафраз предложения"""
        # Используем продвинутые методы парафраза
        return self.nlp_engine.paraphrase_sentence(sentence, preserved_terms)
    
    def _contains_preserved_terms(self, text: str, preserved_terms: Dict[str, List[str]]) -> bool:
        """Проверка содержит ли текст сохраненные термины"""
        text_lower = text.lower()
        
        for category, terms in preserved_terms.items():
            for term in terms:
                if term.lower() in text_lower:
                    return True
        
        return False
    
    def _is_preserved_term(self, word: str, preserved_terms: Dict[str, List[str]]) -> bool:
        """Проверка является ли слово сохраненным термином"""
        word_clean = re.sub(r'[^\w]', '', word.lower())
        
        for category, terms in preserved_terms.items():
            for term in terms:
                term_clean = re.sub(r'[^\w]', '', term.lower())
                if word_clean == term_clean:
                    return True
        
        return False
    
    def _should_replace_word(self) -> bool:
        """Определить нужно ли заменять слово"""
        import random
        return random.random() < self.rewrite_settings['synonym_replacement_rate']
    
    def _should_reorder(self) -> bool:
        """Определить нужно ли изменять порядок предложений"""
        import random
        return random.random() < self.rewrite_settings['sentence_reorder_rate']
    
    def _choose_rewrite_method(self, sentence: Dict[str, Any]) -> callable:
        """Выбор метода переписывания для предложения"""
        methods = [
            (self._replace_with_synonyms, 0.4),
            (self._change_sentence_structure, 0.4),
            (self._paraphrase_sentence, 0.2)
        ]
        
        import random
        rand_val = random.random()
        cumulative = 0
        
        for method, probability in methods:
            cumulative += probability
            if rand_val <= cumulative:
                return method
        
        return self._replace_with_synonyms
    
    def _reorder_sentences(self, sentences: List[str]) -> List[str]:
        """Изменение порядка предложений"""
        if len(sentences) <= 1:
            return sentences
        
        # Простой реверс или случайное перемешивание
        import random
        if random.random() < 0.5:
            return list(reversed(sentences))
        else:
            shuffled = sentences.copy()
            random.shuffle(shuffled)
            return shuffled
    
    def _postprocess_text(self, text: str, preserved_terms: Dict[str, List[str]]) -> str:
        """Пост-обработка переписанного текста"""
        # Восстановление сохраненных терминов если они были повреждены
        for category, terms in preserved_terms.items():
            for term in terms:
                # Простая проверка и восстановление
                if term not in text:
                    # TODO: Более сложная логика восстановления
                    pass
        
        # Исправление грамматики и пунктуации
        text = self.nlp_engine.correct_grammar(text)
        
        # Убедимся, что текст заканчивается точкой
        text = text.strip()
        if text and not text[-1] in '.!?':
            text += '.'
        
        return text
    
    def _calculate_changes(self, original: str, rewritten: str) -> Dict[str, Any]:
        """Расчет статистики изменений"""
        from difflib import SequenceMatcher
        
        similarity = SequenceMatcher(None, original, rewritten).ratio()
        
        original_words = original.split()
        rewritten_words = rewritten.split()
        
        return {
            'similarity_score': similarity,
            'original_length': len(original),
            'rewritten_length': len(rewritten),
            'original_word_count': len(original_words),
            'rewritten_word_count': len(rewritten_words),
            'change_ratio': 1 - similarity
        }
    
    def batch_rewrite(self, texts: List[str], product_contexts: List[Dict] = None) -> List[Dict[str, Any]]:
        """
        Пакетное переписывание текстов
        
        Args:
            texts: Список текстов для переписывания
            product_contexts: Список контекстов товаров
            
        Returns:
            List: Результаты переписывания для каждого текста
        """
        results = []
        
        for i, text in enumerate(texts):
            context = product_contexts[i] if product_contexts and i < len(product_contexts) else None
            result = self.rewrite_description(text, context)
            results.append(result)
        
        return results
