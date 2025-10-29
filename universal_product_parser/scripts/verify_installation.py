#!/usr/bin/env python3
"""
Скрипт проверки установки зависимостей
"""

import importlib
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Проверка версии Python"""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 9:
        print("✅ Версия Python соответствует требованиям")
        return True
    else:
        print("❌ Требуется Python 3.9 или выше")
        return False

def check_package(package_name, import_name=None):
    """Проверка установки пакета"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name}: {version}")
        return True
    except ImportError as e:
        print(f"❌ {package_name}: не установлен - {e}")
        return False

def check_playwright_browsers():
    """Проверка установки браузеров Playwright"""
    try:
        from playwright import sync_api
        with sync_api.sync_playwright() as p:
            browsers = [
                ('chromium', p.chromium),
                ('firefox', p.firefox),
                ('webkit', p.webkit)
            ]
            
            for name, browser_type in browsers:
                try:
                    browser = browser_type.launch(headless=True)
                    browser.close()
                    print(f"✅ Браузер {name}: установлен")
                except Exception as e:
                    print(f"❌ Браузер {name}: ошибка - {e}")
                    
        return True
    except Exception as e:
        print(f"❌ Playwright: ошибка - {e}")
        return False

def check_directories():
    """Проверка структуры директорий"""
    required_dirs = [
        'config',
        'data/input',
        'data/output/excel_exports',
        'data/output/processed_images',
        'data/output/logs',
        'data/temp',
        'scripts'
    ]
    
    all_exists = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✅ Директория {dir_path}: существует")
        else:
            print(f"❌ Директория {dir_path}: отсутствует")
            all_exists = False
    
    return all_exists

def check_config_files():
    """Проверка конфигурационных файлов"""
    required_files = [
        'config/parser_config.yaml',
        'config/logging_config.conf',
        'data/input/target_urls.txt',
        'requirements.txt'
    ]
    
    all_exists = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ Файл {file_path}: существует")
        else:
            print(f"❌ Файл {file_path}: отсутствует")
            all_exists = False
    
    return all_exists

def main():
    print("🔍 Проверка установки Universal Product Parser")
    print("=" * 50)
    
    results = []
    
    # Проверка версии Python
    results.append(("Python Version", check_python_version()))
    print()
    
    # Проверка основных пакетов
    print("📦 Проверка основных пакетов:")
    packages = [
        ('beautifulsoup4', 'bs4'),
        ('selenium', 'selenium'),
        ('playwright', 'playwright'),
        ('requests', 'requests'),
        ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'),
        ('pyyaml', 'yaml'),
        ('loguru', 'loguru'),
        ('tqdm', 'tqdm'),
        ('colorama', 'colorama')
    ]
    
    for package_name, import_name in packages:
        results.append((package_name, check_package(package_name, import_name)))
    print()
    
    # Проверка браузеров
    print("🌐 Проверка браузеров Playwright:")
    results.append(("Playwright Browsers", check_playwright_browsers()))
    print()
    
    # Проверка директорий
    print("📁 Проверка структуры директорий:")
    results.append(("Directories", check_directories()))
    print()
    
    # Проверка конфигурационных файлов
    print("⚙️  Проверка конфигурационных файлов:")
    results.append(("Config Files", check_config_files()))
    print()
    
    # Итоговый результат
    print("=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
    print("=" * 50)
    
    successful_checks = sum(1 for _, success in results if success)
    total_checks = len(results)
    
    for check_name, success in results:
        status = "✅ УСПЕХ" if success else "❌ ОШИБКА"
        print(f"{status}: {check_name}")
    
    print("=" * 50)
    print(f"Итого: {successful_checks}/{total_checks} проверок пройдено")
    
    if successful_checks == total_checks:
        print("🎉 Все проверки пройдены! Система готова к работе.")
        return 0
    else:
        print("⚠️  Некоторые проверки не пройдены. Проверьте установку.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
