#!/usr/bin/env python3
"""
Интерактивный интерфейс для Universal Product Parser
С поддержкой артикулов и обработки изображений
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.markdown import Markdown
from rich.layout import Layout
from rich.prompt import Prompt, Confirm

from ..utils.logger import setup_logger
from ..utils.file_manager import FileManager
from ..core.adaptive_parser import AdaptiveProductParser


class InteractiveInterface:
    """Интерактивный текстовый интерфейс для парсера"""
    
    def __init__(self):
        self.console = Console()
        self.logger = setup_logger("interface")
        self.file_manager = FileManager()
        self.parser = None
        self.session_data = {}
        
    def show_banner(self):
        """Показать баннер приложения"""
        banner_text = """
╔════════════════════════════════════════════════════════════════╗
║                   UNIVERSAL PRODUCT PARSER                    ║
║                Универсальный парсер товаров                   ║
║        🆕 Генерация артикулов + Обработка изображений         ║
╚════════════════════════════════════════════════════════════════╝
        """
        
        self.console.print(Panel.fit(
            banner_text,
            style="bold blue",
            padding=(1, 2)
        ))
    
    async def main_menu(self):
        """Главное меню приложения"""
        self.show_banner()
        
        while True:
            choice = await questionary.select(
                "Выберите действие:",
                choices=[
                    {"name": "🚀 Запустить парсинг", "value": "parse"},
                    {"name": "🔧 Настройки парсера", "value": "config"},
                    {"name": "🧪 Тестирование соединения", "value": "test"},
                    {"name": "📊 Статистика и отчеты", "value": "stats"},
                    {"name": "❓ Помощь", "value": "help"},
                    {"name": "🚪 Выход", "value": "exit"}
                ],
                qmark="🎯",
                pointer="→"
            ).unsafe_ask_async()
            
            if choice == "parse":
                await self.parse_menu()
            elif choice == "config":
                await self.config_menu()
            elif choice == "test":
                await self.test_menu()
            elif choice == "stats":
                await self.stats_menu()
            elif choice == "help":
                self.show_help()
            elif choice == "exit":
                self.console.print("👋 До свидания!", style="bold green")
                break
    
    async def parse_menu(self):
        """Меню настройки и запуска парсинга"""
        self.console.print("\n🎯 [bold]Настройка парсинга[/bold]")
        
        # Выбор источника URL
        url_source = await questionary.select(
            "Источник URL:",
            choices=[
                {"name": "🌐 Ввести URL вручную", "value": "manual"},
                {"name": "📁 Выбрать файл с URL", "value": "file"},
                {"name": "📂 Использовать target_urls.txt", "value": "default"}
            ],
            qmark="🔗"
        ).unsafe_ask_async()
        
        target_url = await self._get_url_from_source(url_source)
        if not target_url:
            self.console.print("❌ URL не указан", style="bold red")
            return
        
        # Настройка фильтров
        filters = await self._configure_filters()
        
        # Подтверждение запуска
        self.console.print("\n📋 [bold]Параметры парсинга:[/bold]")
        self._display_parse_summary(target_url, filters)
        
        if not await Confirm.ask("Запустить парсинг с этими параметрами?"):
            return
        
        # Запуск парсинга с прогресс-баром
        await self._run_parsing_with_progress(target_url, filters)
    
    async def _get_url_from_source(self, source: str) -> Optional[str]:
        """Получение URL из выбранного источника"""
        if source == "manual":
            return await questionary.text(
                "Введите URL для парсинга:",
                validate=lambda text: len(text) > 0 or "URL не может быть пустым",
                qmark="🌐"
            ).unsafe_ask_async()
        
        elif source == "file":
            # Поиск текстовых файлов в директории input
            input_dir = Path("data/input")
            text_files = list(input_dir.glob("*.txt"))
            
            if not text_files:
                self.console.print("❌ В папке data/input нет текстовых файлов", style="yellow")
                return None
            
            file_choices = [{"name": f.name, "value": f} for f in text_files]
            selected_file = await questionary.select(
                "Выберите файл:",
                choices=file_choices,
                qmark="📁"
            ).unsafe_ask_async()
            
            try:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                return urls[0] if urls else None
            except Exception as e:
                self.console.print(f"❌ Ошибка чтения файла: {e}", style="red")
                return None
        
        elif source == "default":
            default_file = Path("data/input/target_urls.txt")
            if default_file.exists():
                try:
                    with open(default_file, 'r', encoding='utf-8') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    return urls[0] if urls else None
                except Exception as e:
                    self.console.print(f"❌ Ошибка чтения target_urls.txt: {e}", style="red")
                    return None
            else:
                self.console.print("❌ Файл data/input/target_urls.txt не найден", style="yellow")
                return None
        
        return None
    
    async def _configure_filters(self) -> Dict[str, Any]:
        """Интерактивная настройка фильтров"""
        filters = {}
        
        self.console.print("\n🔍 [bold]Настройка фильтров[/bold]")
        
        # Фильтр по цене
        if await Confirm.ask("Добавить фильтр по цене?"):
            min_price = await questionary.text(
                "Минимальная цена:",
                default="0",
                validate=lambda x: x.replace('.', '').isdigit() or "Введите число",
                qmark="💰"
            ).unsafe_ask_async()
            
            max_price = await questionary.text(
                "Максимальная цена:",
                default="1000000", 
                validate=lambda x: x.replace('.', '').isdigit() or "Введите число",
                qmark="💰"
            ).unsafe_ask_async()
            
            filters['price_range'] = {
                'min': float(min_price),
                'max': float(max_price)
            }
        
        # Фильтр по категориям
        if await Confirm.ask("Добавить фильтр по категориям?"):
            categories = await questionary.text(
                "Категории (через запятую):",
                qmark="📂"
            ).unsafe_ask_async()
            
            if categories.strip():
                filters['categories'] = [cat.strip() for cat in categories.split(',')]
        
        # Дополнительные фильтры
        if await Confirm.ask("Добавить фильтры по характеристикам?"):
            filters_text = await questionary.text(
                "Фильтры (формат: 'вес:0.1-10, длина:100-500'):",
                qmark="⚖️"
            ).unsafe_ask_async()
            
            if filters_text.strip():
                filters['characteristics'] = filters_text
        
        return filters
    
    def _display_parse_summary(self, url: str, filters: Dict[str, Any]):
        """Отображение сводки параметров парсинга"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="white")
        
        table.add_row("URL", url)
        
        if 'price_range' in filters:
            price_range = filters['price_range']
            table.add_row("Диапазон цен", f"{price_range['min']} - {price_range['max']}")
        
        if 'categories' in filters:
            table.add_row("Категории", ", ".join(filters['categories']))
        
        if 'characteristics' in filters:
            table.add_row("Фильтры характеристик", filters['characteristics'])
        
        # НОВАЯ ИНФОРМАЦИЯ: Функции системы
        table.add_row("Генерация артикулов", "✅ Включена")
        table.add_row("Обработка изображений", "✅ Включена")
        table.add_row("Структура Excel", "✅ Новая (с характеристиками)")
        
        self.console.print(table)
    
    async def _run_parsing_with_progress(self, target_url: str, filters: Dict[str, Any]):
        """Запуск парсинга с отображением прогресса"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:
                
                # Создаем задачи прогресса
                main_task = progress.add_task("[cyan]Инициализация парсера...", total=100)
                
                # Инициализация парсера
                self.parser = AdaptiveProductParser()
                await self.parser.initialize()
                progress.update(main_task, advance=20, description="[green]Поиск структуры сайта...")
                
                # Запуск парсинга
                products = await self.parser.parse_site(target_url, filters)
                progress.update(main_task, advance=60, description="[blue]Сохранение результатов...")
                
                # Сохранение результатов
                if products:
                    timestamp = asyncio.get_event_loop().time()
                    output_file = f"data/output/parsed_products_{int(timestamp)}.json"
                    
                    import json
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(products, f, indent=2, ensure_ascii=False)
                    
                    progress.update(main_task, advance=20, description="[bold green]Готово!")
                    
                    # Показ результатов с новой информацией
                    self._display_results(products, output_file)
                else:
                    progress.update(main_task, advance=20, description="[yellow]Товары не найдены")
                    self.console.print("❌ Товары не найдены по заданным критериям", style="yellow")
                
        except Exception as e:
            self.console.print(f"❌ Ошибка парсинга: {e}", style="bold red")
        finally:
            if self.parser:
                await self.parser.close()
    
    def _display_results(self, products: List[Dict], output_file: str):
        """Отображение результатов парсинга с информацией об артикулах и изображениях"""
        self.console.print(f"\n🎉 [bold green]Парсинг завершен![/bold green]")
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Метрика", style="cyan")
        table.add_column("Значение", style="white")
        
        table.add_row("Обработано товаров", str(len(products)))
        
        # НОВАЯ СТАТИСТИКА: Артикулы и изображения
        articles_count = sum(1 for p in products if p.get('article'))
        total_images = sum(
            len(p.get('processed_images', {}).get('processed_images', [])) 
            for p in products
        )
        approved_images = sum(
            p.get('processed_images', {}).get('moderation_results', {}).get('approved_count', 0)
            for p in products
        )
        
        table.add_row("Сгенерировано артикулов", f"{articles_count}/{len(products)}")
        table.add_row("Обработано изображений", f"{approved_images}/{total_images} одобрено")
        
        # Статистика по ценам
        prices = [p.get('price') for p in products if p.get('price')]
        if prices:
            table.add_row("Средняя цена", f"{sum(prices) / len(prices):.2f}")
            table.add_row("Минимальная цена", f"{min(prices):.2f}")
            table.add_row("Максимальная цена", f"{max(prices):.2f}")
        
        table.add_row("Файл результатов", output_file)
        
        self.console.print(table)
        
        # Показ первых нескольких товаров с новой информацией
        if products:
            self.console.print("\n📦 [bold]Первые товары:[/bold]")
            for i, product in enumerate(products[:3], 1):
                article = product.get('article', 'N/A')
                images_count = len(product.get('processed_images', {}).get('processed_images', []))
                images_info = f"[Изобр: {images_count}]" if images_count > 0 else "[Нет изобр]"
                
                self.console.print(f"{i}. {product.get('name', 'Без названия')}")
                self.console.print(f"   💰 Цена: {product.get('price', 'N/A')}")
                self.console.print(f"   📝 Артикул: {article} {images_info}")
                
                # Информация о главном изображении
                main_image = product.get('processed_images', {}).get('main_image')
                if main_image:
                    self.console.print(f"   🖼️  Главное: {main_image.get('file_name', 'N/A')}")
    
    async def config_menu(self):
        """Меню настройки парсера"""
        self.console.print("\n🔧 [bold]Настройки парсера[/bold]")
        
        config_options = await questionary.select(
            "Настройки:",
            choices=[
                {"name": "📄 Просмотр текущей конфигурации", "value": "view"},
                {"name": "🎯 Настройка генерации артикулов", "value": "articles"},
                {"name": "🖼️  Настройка обработки изображений", "value": "images"},
                {"name": "⚙️  Редактировать конфигурацию", "value": "edit"},
                {"name": "🔄 Сбросить настройки", "value": "reset"},
                {"name": "↩️  Назад", "value": "back"}
            ],
            qmark="⚙️"
        ).unsafe_ask_async()
        
        if config_options == "view":
            self._view_configuration()
        elif config_options == "articles":
            await self._configure_articles()
        elif config_options == "images":
            await self._configure_images()
        elif config_options == "edit":
            await self._edit_configuration()
        elif config_options == "reset":
            await self._reset_configuration()
    
    def _view_configuration(self):
        """Просмотр текущей конфигурации"""
        try:
            import yaml
            config_path = Path("config/parser_config.yaml")
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                self.console.print("\n📄 [bold]Текущая конфигурация:[/bold]")
                
                # Выводим только важные разделы
                important_sections = ['article_generation', 'product_images_processing', 'parser']
                for section in important_sections:
                    if section in config:
                        self.console.print(f"\n[bold]{section.upper()}:[/bold]")
                        self.console.print(yaml.dump(
                            {section: config[section]}, 
                            default_flow_style=False, 
                            allow_unicode=True
                        ))
            else:
                self.console.print("❌ Файл конфигурации не найден", style="yellow")
                
        except Exception as e:
            self.console.print(f"❌ Ошибка чтения конфигурации: {e}", style="red")
    
    async def _configure_articles(self):
        """Настройка генерации артикулов"""
        self.console.print("\n🎯 [bold]Настройка генерации артикулов[/bold]")
        
        try:
            import yaml
            config_path = Path("config/parser_config.yaml")
            
            if not config_path.exists():
                self.console.print("❌ Файл конфигурации не найден", style="yellow")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Настройка метода генерации
            method_choices = [
                {"name": "🔑 Хеш-генерация (рекомендуется)", "value": "hash_based"},
                {"name": "🧩 Композитная генерация", "value": "composite_based"},
                {"name": "🔢 Последовательная нумерация", "value": "sequential"}
            ]
            
            current_method = config.get('article_generation', {}).get('method', 'hash_based')
            new_method = await questionary.select(
                "Метод генерации артикулов:",
                choices=method_choices,
                default=next((c for c in method_choices if c['value'] == current_method), method_choices[0]),
                qmark="🔑"
            ).unsafe_ask_async()
            
            # Обновление конфигурации
            if 'article_generation' not in config:
                config['article_generation'] = {}
            
            config['article_generation']['method'] = new_method
            
            # Сохранение конфигурации
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self.console.print(f"✅ Метод генерации артикулов изменен на: {new_method}", style="green")
            
        except Exception as e:
            self.console.print(f"❌ Ошибка настройки генерации артикулов: {e}", style="red")
    
    async def _configure_images(self):
        """Настройка обработки изображений"""
        self.console.print("\n🖼️  [bold]Настройка обработки изображений[/bold]")
        
        try:
            import yaml
            config_path = Path("config/parser_config.yaml")
            
            if not config_path.exists():
                self.console.print("❌ Файл конфигурации не найден", style="yellow")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Настройки обработки изображений
            image_config = config.get('product_images_processing', {})
            
            # Максимальное количество изображений на товар
            max_images = await questionary.text(
                "Максимальное количество изображений на товар:",
                default=str(image_config.get('max_images_per_product', 10)),
                validate=lambda x: x.isdigit() and int(x) > 0,
                qmark="📷"
            ).unsafe_ask_async()
            
            # Порог модерации
            quality_threshold = await questionary.text(
                "Порог качества для модерации (0.1-1.0):",
                default=str(image_config.get('moderation', {}).get('quality_threshold', 0.7)),
                validate=lambda x: x.replace('.', '').isdigit() and 0.1 <= float(x) <= 1.0,
                qmark="🎯"
            ).unsafe_ask_async()
            
            # Обновление конфигурации
            if 'product_images_processing' not in config:
                config['product_images_processing'] = {}
            
            config['product_images_processing']['max_images_per_product'] = int(max_images)
            
            if 'moderation' not in config['product_images_processing']:
                config['product_images_processing']['moderation'] = {}
            
            config['product_images_processing']['moderation']['quality_threshold'] = float(quality_threshold)
            
            # Сохранение конфигурации
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self.console.print("✅ Настройки обработки изображений обновлены", style="green")
            self.console.print(f"   📷 Максимум изображений: {max_images}")
            self.console.print(f"   🎯 Порог качества: {quality_threshold}")
            
        except Exception as e:
            self.console.print(f"❌ Ошибка настройки обработки изображений: {e}", style="red")
    
    async def _edit_configuration(self):
        """Редактирование конфигурации"""
        self.console.print("\n📝 [bold]Редактирование конфигурации[/bold]")
        
        # TODO: Реализовать интерактивное редактирование конфига
        # Пока просто сообщение
        
        self.console.print("ℹ️  Функция редактирования конфигурации в разработке", style="yellow")
        self.console.print("📁 Вы можете редактировать файл config/parser_config.yaml вручную")
    
    async def _reset_configuration(self):
        """Сброс конфигурации к значениям по умолчанию"""
        if await Confirm.ask("Вы уверены, что хотите сбросить настройки к значениям по умолчанию?"):
            try:
                # Создание бекапа текущего конфига
                config_path = Path("config/parser_config.yaml")
                if config_path.exists():
                    backup_path = config_path.with_suffix('.yaml.backup')
                    import shutil
                    shutil.copy2(config_path, backup_path)
                    self.console.print(f"💾 Создан бэкап: {backup_path}", style="green")
                
                # Пересоздание конфига
                from ...scripts.setup_environment import setup_environment
                setup_environment()
                
                self.console.print("✅ Конфигурация сброшена к значениям по умолчанию", style="green")
                
            except Exception as e:
                self.console.print(f"❌ Ошибка сброса конфигурации: {e}", style="red")
    
    async def test_menu(self):
        """Меню тестирования соединения"""
        self.console.print("\n🧪 [bold]Тестирование соединения[/bold]")
        
        url = await questionary.text(
            "Введите URL для тестирования:",
            validate=lambda text: len(text) > 0 or "URL не может быть пустым",
            qmark="🌐"
        ).unsafe_ask_async()
        
        if not url:
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            
            task = progress.add_task("[cyan]Тестирование соединения...", total=None)
            
            from ..utils.network_utils import NetworkUtils
            network_utils = NetworkUtils()
            
            # Проверка интернета
            progress.update(task, description="[blue]Проверка интернет-соединения...")
            internet_ok = await network_utils.check_internet_connection()
            
            if not internet_ok:
                progress.update(task, description="[red]❌ Нет интернет-соединения")
                return
            
            # Проверка сайта
            progress.update(task, description="[green]Проверка доступности сайта...")
            site_check = await network_utils.check_site_availability(url)
            
            # Отображение результатов
            progress.update(task, description="[bold]Формирование отчета...")
            
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Параметр", style="cyan")
            table.add_column("Значение", style="white")
            
            table.add_row("URL", url)
            table.add_row("Доступен", "✅ Да" if site_check['available'] else "❌ Нет")
            table.add_row("Статус код", str(site_check.get('status_code', 'N/A')))
            table.add_row("Время ответа", f"{site_check.get('response_time', 0):.2f} сек")
            table.add_row("Сервер", site_check.get('server', 'N/A'))
            
            if not site_check['available']:
                table.add_row("Ошибка", site_check.get('error', 'Unknown'))
            
            self.console.print("\n" + table)
    
    async def stats_menu(self):
        """Меню статистики и отчетов"""
        self.console.print("\n📊 [bold]Статистика и отчеты[/bold]")
        
        from ..utils.error_handler import get_global_error_stats
        
        stats = get_global_error_stats()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Метрика", style="cyan")
        table.add_column("Значение", style="white")
        
        table.add_row("Всего ошибок", str(stats['total_errors']))
        table.add_row("Восстановлено ошибок", str(stats['recovered_errors']))
        
        if stats['total_errors'] > 0:
            recovery_rate = (stats['recovered_errors'] / stats['total_errors']) * 100
            table.add_row("Процент восстановления", f"{recovery_rate:.1f}%")
        
        # Ошибки по типам
        for error_type, count in stats['by_type'].items():
            table.add_row(f"Ошибки {error_type}", str(count))
        
        self.console.print(table)
        
        # Дополнительные опции
        choice = await questionary.select(
            "Дополнительные действия:",
            choices=[
                {"name": "📈 Подробная статистика", "value": "detailed"},
                {"name": "🧹 Очистить статистику", "value": "clear"},
                {"name": "📄 Экспорт отчета", "value": "export"},
                {"name": "↩️  Назад", "value": "back"}
            ],
            qmark="📊"
        ).unsafe_ask_async()
        
        if choice == "clear":
            from ..utils.error_handler import global_error_handler
            global_error_handler.reset_stats()
            self.console.print("✅ Статистика очищена", style="green")
        elif choice == "export":
            await self._export_stats_report(stats)
    
    async def _export_stats_report(self, stats: Dict[str, Any]):
        """Экспорт отчета статистики"""
        try:
            timestamp = asyncio.get_event_loop().time()
            report_file = f"data/output/stats_report_{int(timestamp)}.json"
            
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            self.console.print(f"✅ Отчет экспортирован: {report_file}", style="green")
            
        except Exception as e:
            self.console.print(f"❌ Ошибка экспорта: {e}", style="red")
    
    def show_help(self):
        """Показать справку по использованию"""
        help_text = """
# 🆘 Помощь по Universal Product Parser

## 🆕 Новые функции:

### 📝 Генерация артикулов
- Автоматическая генерация уникальных артикулов для каждого товара
- Поддержка разных методов генерации (хеш, композитный, последовательный)
- Настраиваемые префиксы категорий

### 🖼️ Обработка изображений
- Загрузка и обработка всех изображений товара
- Удаление водяных знаков и фона
- Модерация качества изображений
- Выбор главного изображения

### 📊 Новая структура отчетов
- Excel отчеты с динамическими колонками характеристик
- Информация об артикулах и изображениях
- Улучшенное форматирование

## Основные функции:

### 🚀 Парсинг товаров
- Автоматическое определение структуры сайта
- Поддержка статических и динамических сайтов
- Фильтрация по цене, категориям, характеристикам
- Обход анти-бот защиты

### 🔧 Настройки
- Гибкая конфигурация через YAML файлы
- Настройка задержек между запросами
- Управление User-Agent и прокси

### 🧪 Тестирование
- Проверка доступности сайтов
- Тестирование соединения
- Валидация URL

### 📊 Отчеты
- Статистика ошибок
- Метрики производительности
- Экспорт результатов

## Использование:

### Командная строка:

python -m src.cli.main parse --url https://example.com
python -m src.cli.main test --url https://example.com
python -m src.cli.main stats
