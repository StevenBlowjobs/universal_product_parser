#!/usr/bin/env python3
"""
Модуль валидации переписанного контента
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class ContentValidator:
    """Валидатор качества переписанного контента"""
    
    def __init__(self):
        self.logger = setup_logger("content_validator")
        
        # Критерии валидации
        self.validation_criteria = {
            'min_similarity': 0.3,      # Минимальное сходство с оригиналом
            'max_similarity': 0.9,      # Максимальное сходство с оригиналом
            'min_length_ratio': 0.5,    # Минимальная длина относительно оригинала
            'max_length_ratio': 2.0,    # Максимальная длина относительно оригинала
            'max_repetition': 3,        # Максимум повторений одного слова
            'readability_threshold': 0.6 # Порог читабельности
        }
    
    def validate_rewriting(self, original: str, rewritten: str, 
                         min_meaning_preservation: float = 0.8) -> Dict[str, Any]:
        """
        Валидация переписанного текста
        
        Args:
            original: Исходный текст
            rewritten: Переписанный текст
            min_meaning_preservation: Минимальное сохранение смысла
            
        Returns:
            Dict: Результаты валидации
        """
        self.logger.info("🔍 Валидация переписанного текста")
        
        try:
            validation_results = {}
            
            # Базовые проверки
            validation_results['length_check'] = self._validate_length(original, rewritten)
            validation_results['similarity_check'] = self._validate_similarity(original, rewritten)
            validation_results['repetition_check'] = self._check_repetition(rewritten)
            validation_results['readability_check'] = self._check_readability(rewritten)
            validation_results['grammar_check'] = self._check_grammar(rewritten)
            
            # Комплексная оценка
            overall_score = self._calculate_overall_score(validation_results)
            validation_results['overall_score'] = overall_score
            
            # Финальное решение
            is_valid = (
                validation_results['length_check']['passed'] and
                validation_results['similarity_check']['passed'] and
                validation_results['repetition_check']['passed'] and
                overall_score >= min_meaning_preservation
            )
            
            validation_results['is_valid'] = is_valid
            validation_results['recommendation'] = self._generate_recommendation(validation_results)
            
            self.logger.info(f"📊 Результат валидации: {'✅ Успех' if is_valid else '❌ Требует доработки'}")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации: {e}")
            return {
                'is_valid': False,
                'error': str(e),
                'recommendation': 'Проверка не удалась'
            }
    
    def _validate_length(self, original: str, rewritten: str) -> Dict[str, Any]:
        """Проверка длины текста"""
        orig_len = len(original)
        rewrite_len = len(rewritten)
        
        if orig_len == 0:
            ratio = 1.0
        else:
            ratio = rewrite_len / orig_len
        
        passed = (
            ratio >= self.validation_criteria['min_length_ratio'] and 
            ratio <= self.validation_criteria['max_length_ratio']
        )
        
        return {
            'passed': passed,
            'original_length': orig_len,
            'rewritten_length': rewrite_len,
            'ratio': ratio,
            'message': f"Длина: {ratio:.2f} от оригинала" + (" ✅" if passed else " ❌")
        }
    
    def _validate_similarity(self, original: str, rewritten: str) -> Dict[str, Any]:
        """Проверка схожести с оригиналом"""
        similarity = SequenceMatcher(None, original, rewritten).ratio()
        
        passed = (
            similarity >= self.validation_criteria['min_similarity'] and 
            similarity <= self.validation_criteria['max_similarity']
        )
        
        return {
            'passed': passed,
            'similarity': similarity,
            'message': f"Схожесть: {similarity:.2f}" + (" ✅" if passed else " ❌")
        }
    
    def _check_repetition(self, text: str) -> Dict[str, Any]:
        """Проверка на повторения слов"""
        words = re.findall(r'\b\w+\b', text.lower())
        word_counts = {}
        
        for word in words:
            if len(word) > 2:  # Игнорируем короткие слова
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Находим максимальное количество повторений
        max_repetition = max(word_counts.values()) if word_counts else 0
        passed = max_repetition <= self.validation_criteria['max_repetition']
        
        problem_words = [
            word for word, count in word_counts.items() 
            if count > self.validation_criteria['max_repetition']
        ]
        
        return {
            'passed': passed,
            'max_repetition': max_repetition,
            'problem_words': problem_words,
            'message': f"Макс. повторений: {max_repetition}" + (" ✅" if passed else " ❌")
        }
    
    def _check_readability(self, text: str) -> Dict[str, Any]:
        """Проверка читабельности текста"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {
                'passed': False,
                'readability_score': 0,
                'message': "Нет предложений для анализа ❌"
            }
        
        # Простая метрика читабельности на основе длины предложений
        total_words = 0
        total_sentences = len(sentences)
        
        for sentence in sentences:
            words = sentence.split()
            total_words += len(words)
        
        avg_sentence_length = total_words / total_sentences if total_sentences > 0 else 0
        
        # Нормализованная оценка читабельности
        readability_score = max(0, 1 - (avg_sentence_length - 10) / 20)  # Оптимально 10-15 слов
        
        passed = readability_score >= self.validation_criteria['readability_threshold']
        
        return {
            'passed': passed,
            'readability_score': readability_score,
            'avg_sentence_length': avg_sentence_length,
            'message': f"Читабельность: {readability_score:.2f}" + (" ✅" if passed else " ❌")
        }
    
    def _check_grammar(self, text: str) -> Dict[str, Any]:
        """Базовая проверка грамматики"""
        issues = []
        
        # Проверка пунктуации в конце предложения
        sentences = re.split(r'[.!?]+', text)
        for i, sentence in enumerate(sentences[:-1]):  # Пропускаем последний элемент (может быть пустым)
            if sentence and not sentence[-1] in '.!?':
                issues.append(f"Отсутствует пунктуация в предложении {i+1}")
        
        # Проверка двойных пробелов
        if '  ' in text:
            issues.append("Обнаружены двойные пробелы")
        
        # Проверка регистра в начале предложения
        for sentence in sentences:
            if sentence and sentence[0].islower():
                issues.append("Начало предложения с маленькой буквы")
                break  # Достаточно одной ошибки
        
        passed = len(issues) == 0
        
        return {
            'passed': passed,
            'issues': issues,
            'issue_count': len(issues),
            'message': f"Грамматика: {len(issues)} проблем" + (" ✅" if passed else " ❌")
        }
    
    def _calculate_overall_score(self, validation_results: Dict[str, Any]) -> float:
        """Вычисление общей оценки качества"""
        weights = {
            'length_check': 0.2,
            'similarity_check': 0.3,
            'repetition_check': 0.2,
            'readability_check': 0.2,
            'grammar_check': 0.1
        }
        
        score = 0
        
        # Оценка длины
        length_ratio = validation_results['length_check']['ratio']
        if length_ratio < 1:
            length_score = length_ratio  # Штраф за укорочение
        else:
            length_score = 1 / length_ratio  # Штраф за удлинение
        score += length_score * weights['length_check']
        
        # Оценка схожести (оптимально средняя схожесть)
        similarity = validation_results['similarity_check']['similarity']
        optimal_similarity = 0.6  # Оптимальная схожесть
        similarity_score = 1 - abs(similarity - optimal_similarity)
        score += similarity_score * weights['similarity_check']
        
        # Оценка повторений
        max_repetition = validation_results['repetition_check']['max_repetition']
        repetition_score = max(0, 1 - (max_repetition - 1) / 5)  # Штраф за повторения
        score += repetition_score * weights['repetition_check']
        
        # Оценка читабельности
        readability_score = validation_results['readability_check']['readability_score']
        score += readability_score * weights['readability_check']
        
        # Оценка грамматики
        grammar_issues = validation_results['grammar_check']['issue_count']
        grammar_score = max(0, 1 - grammar_issues / 5)  # Штраф за грамматические ошибки
        score += grammar_score * weights['grammar_check']
        
        return min(1.0, max(0.0, score))
    
    def _generate_recommendation(self, validation_results: Dict[str, Any]) -> str:
        """Генерация рекомендаций по улучшению текста"""
        recommendations = []
        
        if not validation_results['length_check']['passed']:
            ratio = validation_results['length_check']['ratio']
            if ratio < self.validation_criteria['min_length_ratio']:
                recommendations.append("Увеличить длину текста")
            else:
                recommendations.append("Уменьшить длину текста")
        
        if not validation_results['similarity_check']['passed']:
            similarity = validation_results['similarity_check']['similarity']
            if similarity < self.validation_criteria['min_similarity']:
                recommendations.append("Увеличить схожесть с оригиналом")
            else:
                recommendations.append("Уменьшить схожесть с оригиналом")
        
        if not validation_results['repetition_check']['passed']:
            recommendations.append("Уменьшить повторения слов")
        
        if not validation_results['readability_check']['passed']:
            recommendations.append("Улучшить читабельность")
        
        if not validation_results['grammar_check']['passed']:
            recommendations.append("Исправить грамматические ошибки")
        
        if not recommendations:
            return "Текст соответствует всем критериям качества"
        
        return "Рекомендации: " + ", ".join(recommendations)
    
    def validate_technical_preservation(self, original: str, rewritten: str, 
                                     technical_terms: List[str]) -> Dict[str, Any]:
        """
        Специализированная проверка сохранения технических терминов
        
        Args:
            original: Исходный текст
            rewritten: Переписанный текст
            technical_terms: Список технических терминов для сохранения
            
        Returns:
            Dict: Результаты проверки
        """
        preserved_terms = []
        lost_terms = []
        
        original_lower = original.lower()
        rewritten_lower = rewritten.lower()
        
        for term in technical_terms:
            if term.lower() in original_lower:
                if term.lower() in rewritten_lower:
                    preserved_terms.append(term)
                else:
                    lost_terms.append(term)
        
        preservation_rate = len(preserved_terms) / max(1, len(technical_terms))
        
        return {
            'preserved_terms': preserved_terms,
            'lost_terms': lost_terms,
            'preservation_rate': preservation_rate,
            'passed': preservation_rate >= 0.9  # 90% терминов должны сохраниться
        }
