#!/bin/bash
# Обновление ML моделей

source venv/bin/activate

echo "🔄 Обновление ML моделей..."
echo "==========================="

# Создание директории для моделей
mkdir -p models

# Обновление модели для удаления фона
echo "📥 Загрузка U2-Net модели..."
python -c "
from rembg import new_session
try:
    session = new_session('u2net')
    print('✅ Модель U2-Net обновлена')
except Exception as e:
    print(f'❌ Ошибка загрузки модели: {e}')
"

# Обновление Spacy модели для русского языка
echo "📥 Обновление NLP модели..."
python -c "
import spacy
try:
    nlp = spacy.load('ru_core_news_lg')
    print('✅ NLP модель уже актуальна')
except OSError:
    print('📥 Установка NLP модели...')
    spacy.cli.download('ru_core_news_lg')
    print('✅ NLP модель установлена')
"

# Обновление словарей синонимов
echo "📥 Обновление словарей синонимов..."
python -c "
import nltk
nltk.download('wordnet')
nltk.download('omw-1.4')
print('✅ Словари NLTK обновлены')
"

echo "✅ Все модели обновлены!"
