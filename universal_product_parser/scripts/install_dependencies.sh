#!/bin/bash

# Universal Product Parser - Installation Script for Kali Linux
set -e

echo "🚀 Начало установки Universal Product Parser..."
echo "================================================"

# Проверка ОС
if ! grep -q "Kali GNU/Linux" /etc/os-release; then
    echo "⚠️  Внимание: Скрипт оптимизирован для Kali Linux"
fi

# Обновление системы
echo "📦 Обновление пакетов системы..."
sudo apt update && sudo apt upgrade -y

# Установка системных зависимостей
echo "🔧 Установка системных зависимостей..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libopencv-dev \
    chromium \
    chromium-driver \
    tor \
    proxychains4 \
    git \
    wget \
    curl

# Создание виртуального окружения
echo "🐍 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Обновление pip
echo "⬆️  Обновление pip..."
pip install --upgrade pip

# Установка Python зависимостей
echo "📚 Установка Python зависимостей..."
pip install -r requirements.txt

# Установка браузеров для Playwright
echo "🌐 Установка браузеров для Playwright..."
python -m playwright install chromium
python -m playwright install-deps

# Настройка прав на скрипты
echo "🔒 Настройка прав доступа..."
chmod +x scripts/*.sh
chmod +x scripts/setup_environment.sh

# Создание необходимых директорий
echo "📁 Создание структуры директорий..."
mkdir -p data/input data/output/excel_exports data/output/processed_images data/output/logs data/temp
mkdir -p config models logs

echo "✅ Установка завершена!"
echo ""
echo "Для активации окружения выполните:"
echo "source venv/bin/activate"
echo ""
echo "Для проверки установки выполните:"
echo "python scripts/verify_installation.py"
