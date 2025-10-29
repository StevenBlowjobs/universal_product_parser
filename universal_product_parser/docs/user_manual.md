❌ Устранение неполадок
┌─────────────────────┬───────────────────────────┬─────────────────────┐
│     Проблема        │         Решение           │       Команда       │
├─────────────────────┼───────────────────────────┼─────────────────────┤
│ Отсутствует Chrome  │ Установить браузер        │ playwright install  │
│ Ошибка памяти       │ Увеличить swap            │ sudo fallocate -l   │
│ Блокировка Cloudflare│ Настроить прокси         │ --proxy-server      │
│ SSL ошибки          │ Игнорировать SSL          │ ignore_https_errors │
└─────────────────────┴───────────────────────────┴─────────────────────┘

📋 Доступные команды
┌──────────────────┬─────────────────────────────────────────────────────┐
│     Команда      │                 Описание                           │
├──────────────────┼─────────────────────────────────────────────────────┤
│ parse            │ Основной парсинг сайта                             │
│ test             │ Тестирование соединения с сайтом                   │
│ stats            │ Просмотр статистики ошибок                         │
│ help             │ Показать справку по командам                       │
└──────────────────┴─────────────────────────────────────────────────────┘

⚙️ Параметры командной строки
Команда parse
┌──────────────────┬──────────────────┬──────────────────────────────────┐
│     Параметр     │     Короткий     │         Описание                │
├──────────────────┼──────────────────┼──────────────────────────────────┤
│ --url            │ -u               │ URL целевого сайта              │
│ --url-file       │ -f               │ Файл со списком URL             │
│ --config         │ -c               │ Путь к конфигурации             │
│ --output         │ -o               │ Путь для сохранения результатов │
│ --min-price      │                  │ Минимальная цена товара         │
│ --max-price      │                  │ Максимальная цена товара        │
│ --categories     │                  │ Список категорий через запятую  │
│ --filters        │                  │ Фильтры характеристик           │
└──────────────────┴──────────────────┴──────────────────────────────────┘

📊 Формат результатов
Структура Excel отчета
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXCEL ОТЧЕТ                                  │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────┤
│   Товары     │ Сравнение цен│ Анализ трендов│  Валидация   │   Сводка   │
│              │              │              │              │             │
│ • Название   │ • Изменения  │ • Тренды     │ • Ошибки     │ • Статистика│
│ • Цена       │ • Новые      │ • Прогнозы   │ • Предупрежд.│ • Метрики   │
│ • Описание   │ • Пропавшие  │ • Волатильн. │ • Качество   │ • Графики   │


📄Структура проекта:

universal_product_parser/
├── 📁 config/          # Конфигурационные файлы
├── 📁 src/            # Исходный код
├── 📁 data/           # Данные и ресурсы  
├── 📁 models/         # ML модели
├── 📁 scripts/        # Вспомогательные скрипты
├── 📁 tests/          # Тесты
└── 📁 docs/           # Документация


🎪 Примеры использования

Пример 1: Базовый парсинг

python src/cli/main.py parse \
  --url "https://electronics-store.com/laptops" \
  --output "results/laptops.xlsx"


Пример 2: Парсинг с фильтрами

python src/cli/main.py parse \
  --url "https://example.com/phones" \
  --min-price 500 \
  --max-price 2000 \
  --categories "smartphones,accessories" \
  --filters "brand:apple,samsung; memory:128-512"


Пример 3: Пакетный парсинг

# Создайте файл urls.txt
echo "https://site1.com/category1" > urls.txt
echo "https://site1.com/category2" >> urls.txt

python src/cli/main.py parse --url-file urls.txt


Пример 4: Тестирование соединения

python src/cli/main.py test --url "https://target-site.com"


Пример выходных данных

{
  "name": "Ноутбук Gaming Pro",
  "price": 129999,
  "description": "Мощный игровой ноутбук...",
  "original_description": "Игровой ноутбук для геймеров...",
  "category": "Ноутбуки",
  "characteristics": {
    "Процессор": "Intel i7",
    "Память": "16GB RAM",
    "SSD": "1TB"
  },
  "images": ["https://.../image1.jpg"]
}

🎨 Кастомизация
Пользовательские селекторы

Создайте config/custom_selectors.yaml:
yaml

"example.com":
  product: ".product-card"
  name: ".product-title"
  price: ".price-tag"
  image: ".product-image img"

Пользовательские словари синонимов

Добавьте в data/input/synonym_dictionaries/custom_terms.json:
json

{
  "специфичный_термин": ["синоним1", "синоним2"],
  "бренд": ["аналог", "альтернатива"]
}

Пользовательские фоны
Поместите фоны в data/input/custom_backgrounds/:

cp my_background.jpg data/input/custom_backgrounds/

🚀 Продвинутые возможности
Мониторинг в реальном времени

# Просмотр логов во время выполнения
tail -f data/output/logs/parser.log
# Мониторинг производительности
watch -n 1 "ps aux | grep python"

Автоматизация через cron
# Ежедневный парсинг в 6:00
0 6 * * * cd /path/to/parser && python src/cli/main.py parse --url "https://..."

Интеграция с внешними системами

from src.core.adaptive_parser import AdaptiveProductParser
async def custom_integration():
    parser = AdaptiveProductParser()
    await parser.initialize()
    products = await parser.parse_site("https://...")
    
