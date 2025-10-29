#!/usr/bin/env python3
"""
Основные операции редактирования изображений
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class ImageEditor:
    """Редактор изображений для базовых операций"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("image_editor")

    @retry_on_failure(max_retries=2)
    def resize_image(self, image_path: str, output_path: str, 
                   new_size: Tuple[int, int], keep_aspect_ratio: bool = True) -> Dict[str, Any]:
        """
        Изменение размера изображения

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения
            new_size: Новый размер (ширина, высота)
            keep_aspect_ratio: Сохранять пропорции

        Returns:
            Dict: Результаты операции
        """
        self.logger.info(f"🔄 Изменение размера: {image_path} -> {new_size}")

        try:
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }

            if keep_aspect_ratio:
                resized_image = self._resize_keep_aspect(image, new_size)
            else:
                resized_image = cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)

            save_success = self._save_image(resized_image, output_path)

            result = {
                'success': save_success,
                'original_path': image_path,
                'output_path': output_path if save_success else None,
                'original_size': image.shape[:2],
                'new_size': resized_image.shape[:2]
            }

            if save_success:
                self.logger.info(f"✅ Размер изменен: {output_path}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка изменения размера: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': image_path
            }

    @retry_on_failure(max_retries=2)
    def crop_image(self, image_path: str, output_path: str, 
                 crop_box: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """
        Обрезка изображения

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения
            crop_box: Область обрезки (x, y, width, height)

        Returns:
            Dict: Результаты операции
        """
        self.logger.info(f"✂️ Обрезка изображения: {image_path}")

        try:
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }

            x, y, w, h = crop_box
            cropped_image = image[y:y+h, x:x+w]

            save_success = self._save_image(cropped_image, output_path)

            result = {
                'success': save_success,
                'original_path': image_path,
                'output_path': output_path if save_success else None,
                'crop_box': crop_box,
                'original_size': image.shape[:2],
                'cropped_size': cropped_image.shape[:2]
            }

            if save_success:
                self.logger.info(f"✅ Изображение обрезано: {output_path}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка обрезки: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': image_path
            }

    @retry_on_failure(max_retries=2)
    def adjust_brightness_contrast(self, image_path: str, output_path: str,
                                 brightness: float = 0, contrast: float = 0) -> Dict[str, Any]:
        """
        Коррекция яркости и контраста

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения
            brightness: Коррекция яркости (-100 до 100)
            contrast: Коррекция контраста (-100 до 100)

        Returns:
            Dict: Результаты операции
        """
        self.logger.info(f"🌅 Коррекция яркости/контраста: {image_path}")

        try:
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }

            # Нормализация параметров
            brightness = max(-100, min(100, brightness))
            contrast = max(-100, min(100, contrast))

            # Применение коррекции
            adjusted_image = self._apply_brightness_contrast(image, brightness, contrast)

            save_success = self._save_image(adjusted_image, output_path)

            result = {
                'success': save_success,
                'original_path': image_path,
                'output_path': output_path if save_success else None,
                'brightness': brightness,
                'contrast': contrast
            }

            if save_success:
                self.logger.info(f"✅ Яркость/контраст скорректированы: {output_path}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка коррекции: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': image_path
            }

    @retry_on_failure(max_retries=2)
    def convert_format(self, image_path: str, output_path: str, 
                     new_format: str) -> Dict[str, Any]:
        """
        Конвертация формата изображения

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения
            new_format: Новый формат (jpg, png, webp)

        Returns:
            Dict: Результаты операции
        """
        self.logger.info(f"🔄 Конвертация формата: {image_path} -> {new_format}")

        try:
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }

            # Убедимся, что расширение соответствует формату
            output_path = Path(output_path).with_suffix(f'.{new_format}')
            save_success = self._save_image(image, str(output_path))

            result = {
                'success': save_success,
                'original_path': image_path,
                'output_path': str(output_path) if save_success else None,
                'original_format': Path(image_path).suffix,
                'new_format': new_format
            }

            if save_success:
                self.logger.info(f"✅ Формат конвертирован: {output_path}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка конвертации: {e}")
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

    def _save_image(self, image: np.ndarray, output_path: str) -> bool:
        """Сохранение изображения"""
        try:
            # Конвертация обратно в BGR для OpenCV
            if len(image.shape) == 3:
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            else:
                image_bgr = image

            success = cv2.imwrite(output_path, image_bgr)
            return success

        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения {output_path}: {e}")
            return False

    def _resize_keep_aspect(self, image: np.ndarray, new_size: Tuple[int, int]) -> np.ndarray:
        """Изменение размера с сохранением пропорций"""
        h, w = image.shape[:2]
        target_w, target_h = new_size

        # Вычисление коэффициентов масштабирования
        scale = min(target_w / w, target_h / h)

        new_w = int(w * scale)
        new_h = int(h * scale)

        # Ресайз
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        # Создание изображения с целевым размером и заливкой черным
        result = np.zeros((target_h, target_w, 3), dtype=np.uint8)

        # Вычисление позиции для вставки
        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2

        result[y:y+new_h, x:x+new_w] = resized

        return result

    def _apply_brightness_contrast(self, image: np.ndarray, 
                                 brightness: float, contrast: float) -> np.ndarray:
        """Применение коррекции яркости и контраста"""
        # Преобразование в float для вычислений
        image = image.astype(np.float32)

        # Коррекция яркости
        if brightness != 0:
            if brightness > 0:
                image = image * (1 - brightness/100) + (255 * brightness/100)
            else:
                image = image * (1 + brightness/100)

        # Коррекция контраста
        if contrast != 0:
            factor = (259 * (contrast + 255)) / (255 * (259 - contrast))
            image = factor * (image - 128) + 128

        # Ограничение значений
        image = np.clip(image, 0, 255)

        return image.astype(np.uint8)

    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """
        Получение информации об изображении

        Args:
            image_path: Путь к изображению

        Returns:
            Dict: Информация об изображении
        """
        try:
            image = self._load_image(image_path)
            if image is None:
                return {}

            h, w = image.shape[:2]
            channels = image.shape[2] if len(image.shape) == 3 else 1

            return {
                'path': image_path,
                'width': w,
                'height': h,
                'channels': channels,
                'file_size': Path(image_path).stat().st_size,
                'format': Path(image_path).suffix.lower()
            }

        except Exception as e:
            self.logger.error(f"❌ Ошибка получения информации: {e}")
            return {}
