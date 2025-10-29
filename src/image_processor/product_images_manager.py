#!/usr/bin/env python3

import asyncio
import aiohttp
import aiofiles
from typing import List, Dict, Any
from pathlib import Path
import os
from urllib.parse import urlparse
from PIL import Image
import io

# Импорты из нашего проекта
from .watermark_remover import WatermarkRemover
from .background_handler import BackgroundHandler
from .image_editor import ImageEditor
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class ProductImagesManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logger("image_manager")
        
        # Инициализация компонентов обработки изображений
        self.watermark_remover = WatermarkRemover(config)
        self.background_handler = BackgroundHandler(config)
        self.image_editor = ImageEditor(config)
        
        # Настройки из конфига
        self.output_directory = Path(config.get('output', {}).get('output_directory', 'data/output/processed_images/'))
        self.max_images = config.get('max_images_per_product', 10)
        self.quality_threshold = config.get('moderation', {}).get('quality_threshold', 0.7)
        
        # Создаем необходимые директории
        self._create_directories()
        
        # HTTP сессия для загрузки изображений
        self.session = None
        
    async def initialize(self):
        """Инициализация менеджера изображений"""
        self.logger.info("🖼️ Инициализация менеджера изображений...")
        self.session = aiohttp.ClientSession()
        
    async def close(self):
        """Закрытие ресурсов"""
        if self.session:
            await self.session.close()
        self.logger.info("✅ Менеджер изображений завершил работу")
    
    def _create_directories(self):
        """Создание необходимых директорий для хранения изображений"""
        directories = self.config.get('directory_structure', {})
        for dir_name in directories.values():
            dir_path = self.output_directory / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Основные директории
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"📁 Созданы директории для изображений: {self.output_directory}")
    
    async def process_product_images(self, image_urls: List[str], product_article: str) -> Dict[str, Any]:
        """Обработка всех изображений товара"""
        
        # Ограничиваем количество обрабатываемых изображений
        image_urls = image_urls[:self.max_images]
        
        results = {
            'original_count': len(image_urls),
            'processed_images': [],
            'moderation_results': {},
            'main_image': None,
            'gallery_images': [],
            'product_article': product_article
        }
        
        if not image_urls:
            self.logger.warning(f"⚠️ Нет URL изображений для товара {product_article}")
            return results
        
        self.logger.info(f"🔄 Начало обработки {len(image_urls)} изображений для товара {product_article}")
        
        tasks = []
        for i, image_url in enumerate(image_urls):
            task = self._process_single_image(image_url, product_article, i)
            tasks.append(task)
        
        # Параллельная обработка изображений
        try:
            processed_images = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Фильтруем успешно обработанные изображения
            successful_images = []
            for img in processed_images:
                if isinstance(img, dict) and img is not None:
                    successful_images.append(img)
                elif isinstance(img, Exception):
                    self.logger.error(f"❌ Ошибка при обработке изображения: {img}")
            
            if successful_images:
                # Модерация и выбор главного изображения
                moderated_images = self._moderate_images(successful_images)
                results['processed_images'] = moderated_images
                results['main_image'] = self._select_main_image(moderated_images)
                results['gallery_images'] = [img for img in moderated_images if img != results['main_image']]
                results['moderation_results'] = self._get_moderation_summary(moderated_images)
                
                self.logger.info(f"✅ Обработано изображений: {len(moderated_images)} из {len(image_urls)}")
            else:
                self.logger.warning(f"⚠️ Не удалось обработать ни одного изображения для товара {product_article}")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка при параллельной обработке изображений: {e}")
        
        return results
    
    @retry_on_failure(max_retries=3)
    async def _process_single_image(self, image_url: str, product_article: str, index: int) -> Dict[str, Any]:
        """Обработка одного изображения"""
        try:
            self.logger.debug(f"📥 Загрузка изображения {index}: {image_url}")
            
            # Скачивание изображения
            image_path = await self._download_image(image_url, product_article, index)
            if not image_path:
                return None
            
            # Получаем информацию об изображении
            image_info = await self._get_image_info(image_path)
            if not image_info:
                return None
            
            # Удаление водяных знаков
            cleaned_image = await self.watermark_remover.remove_watermark(image_path)
            if not cleaned_image:
                self.logger.warning(f"⚠️ Не удалось удалить водяные знаки с изображения {image_url}")
                cleaned_image = image_path
            
            # Обработка фона (если нужно)
            if self.config.get('background_removal', {}).get('enabled', True):
                final_image = await self.background_handler.remove_background(cleaned_image)
                if not final_image:
                    self.logger.warning(f"⚠️ Не удалось удалить фон с изображения {image_url}")
                    final_image = cleaned_image
            else:
                final_image = cleaned_image
            
            # Оптимизация изображения
            optimized_image = await self.image_editor.optimize_image(final_image)
            if not optimized_image:
                self.logger.warning(f"⚠️ Не удалось оптимизировать изображение {image_url}")
                optimized_image = final_image
            
            # Получаем информацию о финальном изображении
            final_info = await self._get_image_info(optimized_image)
            
            return {
                'original_url': image_url,
                'processed_path': str(optimized_image),
                'file_name': f"{product_article}_{index:02d}.jpg",
                'size': final_info['size'],
                'dimensions': final_info['dimensions'],
                'format': final_info['format'],
                'moderation_score': 0.0,  # Будет заполнено при модерации
                'is_approved': True,
                'processing_steps': {
                    'downloaded': bool(image_path),
                    'watermark_removed': bool(cleaned_image and cleaned_image != image_path),
                    'background_removed': bool(final_image and final_image != cleaned_image),
                    'optimized': bool(optimized_image and optimized_image != final_image)
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки изображения {image_url}: {e}")
            return None
    
    async def _download_image(self, image_url: str, product_article: str, index: int) -> Path:
        """Скачивание изображения по URL"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Парсим URL для получения расширения файла
            parsed_url = urlparse(image_url)
            file_extension = Path(parsed_url.path).suffix
            if not file_extension:
                file_extension = '.jpg'
            
            # Создаем имя файла
            filename = f"{product_article}_{index:02d}_original{file_extension}"
            original_dir = self.output_directory / self.config.get('directory_structure', {}).get('original', 'original/')
            original_dir.mkdir(parents=True, exist_ok=True)
            file_path = original_dir / filename
            
            # Загружаем изображение
            async with self.session.get(image_url) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Сохраняем файл
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(content)
                    
                    self.logger.debug(f"✅ Изображение сохранено: {file_path}")
                    return file_path
                else:
                    self.logger.error(f"❌ Ошибка загрузки изображения {image_url}: статус {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка при скачивании изображения {image_url}: {e}")
            return None
    
    async def _get_image_info(self, image_path: Path) -> Dict[str, Any]:
        """Получение информации об изображении"""
        try:
            if not image_path.exists():
                return None
            
            # Используем PIL для получения информации об изображении
            with Image.open(image_path) as img:
                dimensions = img.size  # (width, height)
                format = img.format
            
            size = image_path.stat().st_size
            
            return {
                'dimensions': dimensions,
                'size': size,
                'format': format
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения информации об изображении {image_path}: {e}")
            return None
    
    def _moderate_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Модерация изображений"""
        moderated_images = []
        
        for image in images:
            if image:
                # Проверка качества
                quality_score = self._assess_image_quality(image)
                image['moderation_score'] = quality_score
                image['is_approved'] = quality_score >= self.quality_threshold
                
                if image['is_approved']:
                    moderated_images.append(image)
                else:
                    self.logger.debug(f"🚫 Изображение отклонено модерацией: {image['file_name']} (оценка: {quality_score:.2f})")
        
        return sorted(moderated_images, key=lambda x: x['moderation_score'], reverse=True)
    
    def _assess_image_quality(self, image: Dict[str, Any]) -> float:
        """Оценка качества изображения"""
        score = 1.0
        
        # Проверка размера файла
        min_file_size = self.config.get('moderation', {}).get('min_file_size', 50000)
        if image['size'] < min_file_size:
            score -= 0.3
            self.logger.debug(f"📉 Маленький размер файла: {image['file_name']}")
        
        # Проверка разрешения
        min_width = self.config.get('moderation', {}).get('min_width', 400)
        min_height = self.config.get('moderation', {}).get('min_height', 400)
        width, height = image.get('dimensions', (0, 0))
        
        if width < min_width or height < min_height:
            score -= 0.2
            self.logger.debug(f"📉 Низкое разрешение: {image['file_name']} ({width}x{height})")
        
        # Бонус за высокое разрешение
        if width >= 1200 and height >= 1200:
            score += 0.1
        
        # Штраф за проблемы с обработкой
        processing_steps = image.get('processing_steps', {})
        if not processing_steps.get('watermark_removed', True):
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _select_main_image(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Выбор главного изображения товара"""
        if not images:
            return None
        
        # Выбираем изображение с наивысшим рейтингом
        main_image = images[0]
        self.logger.debug(f"🏆 Выбрано главное изображение: {main_image['file_name']} (оценка: {main_image['moderation_score']:.2f})")
        return main_image
    
    def _get_moderation_summary(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Сводка по модерации"""
        approved = [img for img in images if img['is_approved']]
        rejected = [img for img in images if not img['is_approved']]
        
        summary = {
            'total_processed': len(images),
            'approved_count': len(approved),
            'rejected_count': len(rejected),
            'approval_rate': len(approved) / len(images) if images else 0,
            'average_score': sum(img['moderation_score'] for img in images) / len(images) if images else 0,
            'main_image_selected': bool(approved)
        }
        
        # Добавляем информацию о лучшем и худшем изображении
        if approved:
            summary['best_score'] = max(img['moderation_score'] for img in approved)
            summary['worst_approved_score'] = min(img['moderation_score'] for img in approved)
        
        if rejected:
            summary['best_rejected_score'] = max(img['moderation_score'] for img in rejected) if rejected else 0
        
        self.logger.info(f"📊 Модерация: {summary['approved_count']}/{summary['total_processed']} одобрено ({summary['approval_rate']:.1%})")
        
        return summary

    async def cleanup_failed_images(self, product_article: str):
        """Очистка неудачно обработанных изображений"""
        try:
            original_dir = self.output_directory / self.config.get('directory_structure', {}).get('original', 'original/')
            
            # Удаляем все файлы, связанные с этим товаром
            pattern = f"{product_article}_*"
            for file_path in original_dir.glob(pattern):
                file_path.unlink()
                self.logger.debug(f"🧹 Удален файл: {file_path}")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка при очистке изображений для {product_article}: {e}")
