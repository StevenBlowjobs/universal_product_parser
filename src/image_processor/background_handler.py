#!/usr/bin/env python3
"""
Модуль для удаления и замены фона товаров
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from .models.u2net_model import U2NetModel
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class BackgroundHandler:
    """Обработчик фона товаров с поддержкой кастомных фонов"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("background_handler")
        self.u2net = U2NetModel()
        
        # Настройки обработки
        self.processing_settings = {
            'background_removal_confidence': 0.8,
            'edge_smoothing': True,
            'hair_processing': True,
            'default_background': 'white',
            'custom_background_path': None
        }
        
        if 'image_processing' in self.config:
            self.processing_settings.update(self.config['image_processing'])
    
    @retry_on_failure(max_retries=2)
    def remove_background(self, image_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Удаление фона с изображения товара
        
        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения результата
            
        Returns:
            Dict: Результаты обработки
        """
        self.logger.info(f"🖼️  Удаление фона: {image_path}")
        
        try:
            # Загрузка изображения
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }
            
            # Генерация маски с помощью U2-Net
            mask = self.u2net.predict_mask(image)
            
            # Пост-обработка маски
            refined_mask = self._refine_mask(mask, image)
            
            # Создание изображения с прозрачным фоном
            result_image = self._apply_mask(image, refined_mask)
            
            # Сохранение результата
            if output_path:
                save_success = self._save_transparent_image(result_image, output_path)
            else:
                original_path = Path(image_path)
                output_path = str(original_path.parent / f"{original_path.stem}_no_bg.png")
                save_success = self._save_transparent_image(result_image, output_path)
            
            result = {
                'success': save_success,
                'original_path': image_path,
                'output_path': output_path if save_success else None,
                'mask_quality': self._assess_mask_quality(refined_mask),
                'processing_time': None,  # TODO: Добавить тайминг
                'image_dimensions': image.shape
            }
            
            if save_success:
                self.logger.info(f"✅ Фон успешно удален: {output_path}")
            else:
                self.logger.error(f"❌ Ошибка сохранения: {output_path}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка удаления фона: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': image_path
            }
    
    @retry_on_failure(max_retries=2)
    def replace_background(self, image_path: str, background_path: str = None, 
                         output_path: str = None) -> Dict[str, Any]:
        """
        Замена фона товара
        
        Args:
            image_path: Путь к изображению товара
            background_path: Путь к фоновому изображению
            output_path: Путь для сохранения результата
            
        Returns:
            Dict: Результаты обработки
        """
        self.logger.info(f"🔄 Замена фона: {image_path}")
        
        try:
            # Загрузка основного изображения
            foreground = self._load_image(image_path)
            if foreground is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение товара',
                    'original_path': image_path
                }
            
            # Загрузка или создание фона
            if background_path and Path(background_path).exists():
                background = self._load_image(background_path)
                if background is None:
                    return {
                        'success': False,
                        'error': 'Не удалось загрузить фоновое изображение',
                        'background_path': background_path
                    }
                
                # Ресайз фона под размер основного изображения
                background = self._resize_background(background, foreground.shape)
            else:
                # Создание стандартного фона
                background = self._create_default_background(foreground.shape)
            
            # Удаление фона с основного изображения
            removal_result = self.remove_background(image_path)
            if not removal_result['success']:
                return removal_result
            
            # Загрузка изображения без фона
            foreground_no_bg = self._load_image(removal_result['output_path'])
            
            # Наложение на новый фон
            composite_image = self._blend_images(background, foreground_no_bg)
            
            # Сохранение результата
            if output_path:
                save_success = self._save_image(composite_image, output_path)
            else:
                original_path = Path(image_path)
                output_path = str(original_path.parent / f"{original_path.stem}_new_bg{original_path.suffix}")
                save_success = self._save_image(composite_image, output_path)
            
            result = {
                'success': save_success,
                'original_path': image_path,
                'background_path': background_path,
                'output_path': output_path if save_success else None,
                'composite_quality': self._assess_composite_quality(composite_image)
            }
            
            if save_success:
                self.logger.info(f"✅ Фон успешно заменен: {output_path}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка замены фона: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': image_path
            }
    
    def _load_image(self, image_path: str) -> Optional[np.ndarray]:
        """Загрузка изображения"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки {image_path}: {e}")
            return None
    
    def _refine_mask(self, mask: np.ndarray, original_image: np.ndarray) -> np.ndarray:
        """Уточнение маски для лучшего качества"""
        # Бинаризация маски
        _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        
        # Морфологические операции для сглаживания краев
        kernel = np.ones((5, 5), np.uint8)
        refined_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
        refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, kernel)
        
        # Сглаживание границ
        if self.processing_settings['edge_smoothing']:
            refined_mask = self._smooth_mask_edges(refined_mask, original_image)
        
        # Обработка волос/меха если нужно
        if self.processing_settings['hair_processing']:
            refined_mask = self._process_hair_areas(refined_mask, original_image)
        
        return refined_mask
    
    def _smooth_mask_edges(self, mask: np.ndarray, image: np.ndarray) -> np.ndarray:
        """Сглаживание границ маски"""
        # Gaussian blur для границ
        blurred_mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        # Создание градиентной маски для плавного перехода
        gradient = cv2.Laplacian(mask, cv2.CV_64F)
        gradient = np.absolute(gradient)
        gradient = np.uint8(255 * gradient / np.max(gradient))
        
        # Комбинирование масок
        smooth_mask = cv2.addWeighted(mask, 0.7, blurred_mask, 0.3, 0)
        
        return smooth_mask
    
    def _process_hair_areas(self, mask: np.ndarray, image: np.ndarray) -> np.ndarray:
        """Обработка областей с волосами/мехом"""
        # Детекция текстур, похожих на волосы
        gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Вычисление градиентов для обнаружения тонких структур
        sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        # Нормализация и пороговая обработка
        gradient_magnitude = np.uint8(255 * gradient_magnitude / np.max(gradient_magnitude))
        _, hair_mask = cv2.threshold(gradient_magnitude, 50, 255, cv2.THRESH_BINARY)
        
        # Комбинирование с основной маской
        combined_mask = cv2.bitwise_or(mask, hair_mask)
        
        return combined_mask
    
    def _apply_mask(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Применение маски для создания изображения с прозрачным фоном"""
        # Создание 4-канального изображения (RGBA)
        if len(image.shape) == 3:
            b_channel, g_channel, r_channel = cv2.split(image)
        else:
            b_channel = g_channel = r_channel = image
        
        alpha_channel = mask
        
        # Инвертирование маски для прозрачного фона
        alpha_channel = cv2.bitwise_not(alpha_channel)
        
        # Создание RGBA изображения
        rgba_image = cv2.merge([b_channel, g_channel, r_channel, alpha_channel])
        
        return rgba_image
    
    def _resize_background(self, background: np.ndarray, target_shape: Tuple[int, int, int]) -> np.ndarray:
        """Изменение размера фона под целевое изображение"""
        target_height, target_width = target_shape[:2]
        
        # Сохранение пропорций фона
        bg_height, bg_width = background.shape[:2]
        
        # Вычисление коэффициента масштабирования
        scale = max(target_width / bg_width, target_height / bg_height)
        
        new_width = int(bg_width * scale)
        new_height = int(bg_height * scale)
        
        # Ресайз
        resized_bg = cv2.resize(background, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Обрезка до нужного размера
        start_x = (new_width - target_width) // 2
        start_y = (new_height - target_height) // 2
        
        cropped_bg = resized_bg[start_y:start_y+target_height, start_x:start_x+target_width]
        
        return cropped_bg
    
    def _create_default_background(self, shape: Tuple[int, int, int]) -> np.ndarray:
        """Создание стандартного фона"""
        height, width, channels = shape
        
        if self.processing_settings['default_background'] == 'white':
            background = np.ones((height, width, channels), dtype=np.uint8) * 255
        elif self.processing_settings['default_background'] == 'black':
            background = np.zeros((height, width, channels), dtype=np.uint8)
        else:
            # Градиентный фон
            background = self._create_gradient_background((height, width, channels))
        
        return background
    
    def _create_gradient_background(self, shape: Tuple[int, int, int]) -> np.ndarray:
        """Создание градиентного фона"""
        height, width, channels = shape
        background = np.zeros((height, width, channels), dtype=np.uint8)
        
        # Вертикальный градиент от светлого к темному
        for i in range(height):
            intensity = int(255 * (1 - i / height))
            background[i, :, :] = intensity
        
        return background
    
    def _blend_images(self, background: np.ndarray, foreground: np.ndarray) -> np.ndarray:
        """Наложение изображений с учетом прозрачности"""
        # Если foreground имеет альфа-канал
        if foreground.shape[2] == 4:
            # Разделение на RGB и альфа-канал
            foreground_rgb = foreground[:, :, :3]
            alpha = foreground[:, :, 3] / 255.0
            
            # Наложение с учетом прозрачности
            result = np.zeros_like(background, dtype=np.float32)
            
            for c in range(3):
                result[:, :, c] = alpha * foreground_rgb[:, :, c] + (1 - alpha) * background[:, :, c]
            
            return result.astype(np.uint8)
        else:
            # Простое наложение
            return foreground
    
    def _assess_mask_quality(self, mask: np.ndarray) -> Dict[str, float]:
        """Оценка качества маски"""
        # Анализ четкости границ
        edges = cv2.Canny(mask, 50, 150)
        edge_density = np.sum(edges > 0) / (mask.shape[0] * mask.shape[1])
        
        # Анализ однородности
        mean_intensity = np.mean(mask)
        intensity_std = np.std(mask)
        
        return {
            'edge_sharpness': edge_density,
            'uniformity': 1.0 / (1.0 + intensity_std),
            'overall_quality': (edge_density + (1.0 / (1.0 + intensity_std))) / 2
        }
    
    def _assess_composite_quality(self, composite: np.ndarray) -> Dict[str, float]:
        """Оценка качества композитного изображения"""
        # Анализ контраста
        gray = cv2.cvtColor(composite, cv2.COLOR_RGB2GRAY)
        contrast = np.std(gray)
        
        # Анализ цветового баланса
        mean_color = np.mean(composite, axis=(0, 1))
        color_balance = np.std(mean_color)
        
        return {
            'contrast': contrast / 255.0,
            'color_balance': 1.0 / (1.0 + color_balance),
            'overall_quality': (contrast / 255.0 + (1.0 / (1.0 + color_balance))) / 2
        }
    
    def _save_transparent_image(self, image: np.ndarray, output_path: str) -> bool:
        """Сохранение изображения с прозрачностью"""
        try:
            # Конвертация в BGR для OpenCV
            if image.shape[2] == 4:
                # RGBA to BGRA
                bgra = cv2.cvtColor(image, cv2.COLOR_RGBA2BGRA)
            else:
                bgra = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            success = cv2.imwrite(output_path, bgra)
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения прозрачного изображения: {e}")
            return False
    
    def _save_image(self, image: np.ndarray, output_path: str) -> bool:
        """Сохранение изображения"""
        try:
            # Конвертация в BGR для OpenCV
            if len(image.shape) == 3:
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                image_bgr = image
            
            success = cv2.imwrite(output_path, image_bgr)
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения изображения: {e}")
            return False
    
    def get_available_backgrounds(self) -> List[Dict[str, str]]:
        """Получение списка доступных фонов"""
        backgrounds = []
        
        # Стандартные фоны
        standard_backgrounds = [
            {'name': 'Белый', 'type': 'standard', 'path': 'white'},
            {'name': 'Черный', 'type': 'standard', 'path': 'black'},
            {'name': 'Градиентный', 'type': 'standard', 'path': 'gradient'}
        ]
        
        backgrounds.extend(standard_backgrounds)
        
        # Пользовательские фоны
        custom_bg_path = self.processing_settings.get('custom_background_path')
        if custom_bg_path and Path(custom_bg_path).exists():
            for bg_file in Path(custom_bg_path).glob('*.{jpg,jpeg,png}'):
                backgrounds.append({
                    'name': bg_file.stem,
                    'type': 'custom',
                    'path': str(bg_file)
                })
        
        return backgrounds
