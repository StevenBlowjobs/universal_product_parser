# 🚀 Руководство по установке

╔═════════════════════════════════════════════════════════════════════════╗
║                  УСТАНОВКА И НАСТРОЙКА ПАРСЕРА                         ║
╚═════════════════════════════════════════════════════════════════════════╝

## 📦 Быстрый старт

1. Клонирование репозитория

git clone https://github.com/your-username/universal-product-parser.git
cd universal-product-parser

2. Автоматическая установка

chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh

3. Проверка установки

python scripts/verify_installation.py


🔧 Подробная установка
Системные требования

┌──────────────────────┬─────────────────────────────────────────────┐
│     Компонент        │             Требования                     │
├──────────────────────┼─────────────────────────────────────────────┤
│ 🖥️  ОС              │ Kali Linux, Ubuntu 20.04+, Windows 10+     │
│ 💾  Память          │ 8 GB RAM (рекомендуется 16 GB)             │
│ 🎮  Процессор       │ 4+ ядер                                     │
│ 💽  Диск            │ 10 GB свободного места                      │
│ 🌐  Сеть            │ Стабильное интернет-соединение              │
└──────────────────────┴─────────────────────────────────────────────┘

Установка зависимостей
Python 3.8+

sudo apt update
sudo apt install python3.8 python3.8-venv python3-pip

Создание виртуального окружения

python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

Установка Python пакетов

pip install -r requirements.txt

Установка системных зависимостей

# Для Kali Linux
sudo apt install chromium chromium-driver
sudo apt install libopencv-dev python3-opencv

# Установка Playwright браузеров
playwright install chromium

Настройка конфигурации

1. Базовый конфиг
Создайте файл config/parser_config.yaml:

parser:
  request_timeout: 30
  user_agent: "Mozilla/5.0..."

browser:
  headless: true
  viewport_width: 1920

2. Настройка путей

mkdir -p data/{input,output,temp}
mkdir -p data/input/{custom_backgrounds,synonym_dictionaries}
mkdir -p data/output/{excel_exports,processed_images,logs}

3. Добавление целевых URL
Создайте data/input/target_urls.txt:

https://example-shop.com/category1
https://example-shop.com/category2


🧪 Проверка установки
Запуск диагностики

python scripts/verify_installation.py

Ожидаемый вывод:

🔍 ДИАГНОСТИКА СИСТЕМЫ
══════════════════════════════════════
✅ Python 3.8.10
✅ Виртуальное окружение активировано
✅ Все зависимости установлены
✅ Playwright браузеры готовы
✅ Директории созданы
✅ Конфигурация загружена

🎉 Система готова к работе!


Тестовый запуск

python src/cli/main.py test --url "https://httpbin.org/html"


⚙️ Расширенная настройка
Настройка NLP моделей

# Загрузка spaCy модели для русского
python -m spacy download ru_core_news_lg

# Создание словарей синонимов
cp data/input/synonym_dictionaries/general_synonyms.json.example \
   data/input/synonym_dictionaries/general_synonyms.json


Настройка обработки изображений

# Скачивание ML моделей
chmod +x scripts/update_models.sh
./scripts/update_models.sh


Настройка прокси (опционально)
Создайте data/input/proxies.txt:

http://user:pass@proxy1.example.com:8080
http://user:pass@proxy2.example.com:8080

