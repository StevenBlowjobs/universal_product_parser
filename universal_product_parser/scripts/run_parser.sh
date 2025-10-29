#!/bin/bash
# Основной скрипт запуска парсера

source venv/bin/activate

echo "🚀 Запуск Universal Product Parser..."
echo "====================================="

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            TARGET_URL="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -f|--filters)
            FILTERS="$2"
            shift 2
            ;;
        *)
            echo "❌ Неизвестный параметр: $1"
            echo "Использование: $0 [-u URL] [-c CONFIG] [-f FILTERS]"
            exit 1
            ;;
    esac
done

# Установка значений по умолчанию
CONFIG_FILE=${CONFIG_FILE:-"config/parser_config.yaml"}

echo "🎯 Целевой URL: ${TARGET_URL:-'Из config файла'}"
echo "⚙️  Конфиг: $CONFIG_FILE"
echo "🔍 Фильтры: ${FILTERS:-'Нет'}"

# Запуск парсера
python -m src.cli.main \
    --url "${TARGET_URL}" \
    --config "${CONFIG_FILE}" \
    --filters "${FILTERS}" \
    "$@"

echo "✅ Парсинг завершен!"
