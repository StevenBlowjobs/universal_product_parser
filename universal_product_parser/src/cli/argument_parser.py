#!/usr/bin/env python3
"""
Парсер аргументов командной строки
"""

import argparse


def create_parser():
    """Создание парсера аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Universal Product Parser - Парсер товаров с любого сайта",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py parse --url "https://example-shop.com"
  python main.py parse --url-file urls.txt --min-price 1000 --max-price 5000
  python main.py test --url "https://example-shop.com"
  python main.py stats

Новые функции:
  📝 Автоматическая генерация артикулов
  🖼️ Обработка и модерация изображений
  📊 Новая структура Excel отчетов
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    # Парсинг
    parse_parser = subparsers.add_parser('parse', help='Запуск парсинга с генерацией артикулов и обработкой изображений')
    parse_parser.add_argument('--url', type=str, help='URL целевого сайта')
    parse_parser.add_argument('--url-file', type=str, help='Файл со списком URL')
    parse_parser.add_argument('--config', type=str, default='config/parser_config.yaml', 
                            help='Путь к файлу конфигурации')
    parse_parser.add_argument('--output', type=str, help='Путь для сохранения результатов')
    parse_parser.add_argument('--min-price', type=float, help='Минимальная цена товара')
    parse_parser.add_argument('--max-price', type=float, help='Максимальная цена товара')
    parse_parser.add_argument('--categories', type=str, help='Список категорий через запятую')
    parse_parser.add_argument('--filters', type=str, help='Фильтры характеристик в формате "ключ:значение"')
    
    # Тестирование
    test_parser = subparsers.add_parser('test', help='Тестирование соединения')
    test_parser.add_argument('--url', type=str, required=True, help='URL для тестирования')
    
    # Статистика
    subparsers.add_parser('stats', help='Показать статистику ошибок')
    
    return parser
