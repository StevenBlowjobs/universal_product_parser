#!/bin/bash
# Очистка временных файлов и кэша

echo "🧹 Очистка временных файлов..."

# Удаление кэша Python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name ".DS_Store" -delete

# Очистка временных данных
rm -rf data/temp/*
rm -rf .pytest_cache
rm -rf .cache

# Очистка логов (сохраняем только последние 7 дней)
find data/output/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true

echo "✅ Очистка завершена!"
