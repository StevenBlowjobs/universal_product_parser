#!/bin/bash

# Environment Setup Script
set -e

echo "⚙️  Настройка окружения Universal Product Parser..."
echo "==================================================="

# Активация виртуального окружения
if [ -d "venv" ]; then
    echo "🐍 Активация виртуального окружения..."
    source venv/bin/activate
else
    echo "❌ Виртуальное окружение не найдено. Сначала запустите install_dependencies.sh"
    exit 1
fi

# Создание конфигурационных файлов
echo "📄 Создание конфигурационных файлов..."

# Основной конфиг парсера
cat > config/parser_config.yaml << EOF
parsing:
  max_pages: 1000
  request_delay:
    min: 2
    max: 5
  retry_attempts: 3
  timeout: 30
  user_agents:
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    - "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

anti_detection:
  use_tor: false
  use_proxies: false
  rotate_user_agents: true
  random_delays: true

logging:
  level: "INFO"
  file: "data/output/logs/parser.log"
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
  rotation: "10 MB"

filters:
  price_range:
    min: 0
    max: 1000000
  categories: []
EOF

# Конфиг логирования
cat > config/logging_config.conf << EOF
[loggers]
keys=root,parser,image_processor

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_parser]
level=DEBUG
handlers=fileHandler
qualname=parser
propagate=0

[logger_image_processor]
level=DEBUG
handlers=fileHandler
qualname=image_processor
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=handlers.RotatingFileHandler
level=DEBUG
formatter=simpleFormatter
args=('data/output/logs/application.log', 'a', 10485760, 5)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
EOF

# Файл с примером URL
cat > data/input/target_urls.txt << EOF
# Добавьте целевые URL для парсинга, каждый с новой строки
# Пример:
# https://example-shop.com/category/electronics
# https://another-shop.com/products
EOF

echo "✅ Настройка окружения завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Добавьте целевые URL в data/input/target_urls.txt"
echo "2. Настройте параметры в config/parser_config.yaml"
echo "3. Запустите проверку: python scripts/verify_installation.py"
