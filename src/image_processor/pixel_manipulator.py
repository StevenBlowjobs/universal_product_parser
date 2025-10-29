#!/usr/bin/env python3
"""
Манипуляции с пикселями для обхода детекции
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class PixelManipulator:
    """Манипулятор пикселей для изменения изображения с целью обхода детекции"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("pixel_manipulator")

        # Настройки манипуляций
        self.manipulation_settings = {
            'perturbation_strength': 0.05,
            'noise_level': 0.01,
            'max_rotation_angle': 5,
            'max_scale_change': 0.1,
            'color_jitter_range': 10
        }

        if 'image_processing' in self.config:
            self.manipulation_settings.update(self.config['image_processing'])

    @retry_on_failure(max_retries=2)
    def perturb_pixels(self, image_path: str, output_path: str, 
                     methods: List[str] = None) -> Dict[str, Any]:
        """
        Применение возмущений к пикселям изображения

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения
            methods: Список методов возмущения

        Returns:
            Dict: Результаты операции
        """
        self.logger.info(f"🎨 Применение возмущений: {image_path}")

        try:
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }

            if methods is None:
                methods = ['noise', 'color_jitter', 'rotation', 'scaling']

            perturbed_image = image.copy()

            # Применение выбранных методов
            applied_methods = []
            for method in methods:
                if method == 'noise':
                    perturbed_image = self._add_random_noise(perturbed_image)
                    applied_methods.append('noise')
                elif method == 'color_jitter':
                    perturbed_image = self._color_jitter(perturbed_image)
                    applied_methods.append('color_jitter')
                elif method == 'rotation':
                    perturbed_image = self._random_rotation(perturbed_image)
                    applied_methods.append('rotation')
                elif method == 'scaling':
                    perturbed_image = self._random_scaling(perturbed_image)
                    applied_methods.append('scaling')
                elif method == 'blur':
                    perturbed_image = self._mild_blur(perturbed_image)
                    applied_methods.append('blur')

            save_success = self._save_image(perturbed_image, output_path)

            result = {
                'success': save_success,
                'original_path': image_path,
                'output_path': output_path if save_success else None,
                'applied_methods': applied_methods,
                'perturbation_strength': self.manipulation_settings['perturbation_strength']
            }

            if save_success:
                self.logger.info(f"✅ Возмущения применены: {output_path}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка применения возмущений: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': image_path
            }

    @retry_on_failure(max_retries=2)
    def add_watermark_detection_evasion(self, image_path: str, output_path: str) -> Dict[str, Any]:
        """
        Добавление изменений для обхода детекции вотермарок

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения

        Returns:
            Dict: Результаты операции
        """
        self.logger.info(f"🕵️  Применение методов обхода детекции: {image_path}")

        try:
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }

            processed_image = image.copy()

            # Комбинация методов для обхода детекции
            methods = [
                self._subtle_color_shift,
                self._add_high_frequency_noise,
                self._local_contrast_adjustment,
                self._edge_enhancement
            ]

            for method in methods:
                processed_image = method(processed_image)

            save_success = self._save_image(processed_image, output_path)

            result = {
                'success': save_success,
                'original_path': image_path,
                'output_path': output_path if save_success else None,
                'evasion_methods': ['color_shift', 'high_freq_noise', 'local_contrast', 'edge_enhancement']
            }

            if save_success:
                self.logger.info(f"✅ Методы обхода применены: {output_path}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка применения методов обхода: {e}")
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

    def _add_random_noise(self, image: np.ndarray) -> np.ndarray:
        """Добавление случайного шума"""
        noise_level = self.manipulation_settings['noise_level']
        noise = np.random.normal(0, noise_level * 255, image.shape).astype(np.uint8)
        noisy_image = cv2.add(image, noise)
        return noisy_image

    def _color_jitter(self, image: np.ndarray) -> np.ndarray:
        """Случайное изменение цветов"""
        jitter_range = self.manipulation_settings['color_jitter_range']
        
        # Случайные изменения для каждого канала
        for c in range(3):
            jitter = np.random.randint(-jitter_range, jitter_range)
            image[:, :, c] = np.clip(image[:, :, c].astype(np.int16) + jitter, 0, 255).astype(np.uint8)
        
        return image

    def _random_rotation(self, image: np.ndarray) -> np.ndarray:
        """Случайный поворот изображения"""
        angle = np.random.uniform(-self.manipulation_settings['max_rotation_angle'], 
                                self.manipulation_settings['max_rotation_angle'])
        
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC)
        
        return rotated_image

    def _random_scaling(self, image: np.ndarray) -> np.ndarray:
        """Случайное масштабирование изображения"""
        scale_factor = 1 + np.random.uniform(-self.manipulation_settings['max_scale_change'], 
                                           self.manipulation_settings['max_scale_change'])
        
        h, w = image.shape[:2]
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        
        scaled_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Обрезка или дополнение до исходного размера
        if scale_factor > 1:
            # Обрезка
            start_x = (new_w - w) // 2
            start_y = (new_h - h) // 2
            scaled_image = scaled_image[start_y:start_y+h, start_x:start_x+w]
        else:
            # Дополнение
            pad_x = (w - new_w) // 2
            pad_y = (h - new_h) // 2
            padded_image = np.zeros((h, w, 3), dtype=np.uint8)
            padded_image[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = scaled_image
            scaled_image = padded_image
        
        return scaled_image

    def _mild_blur(self, image: np.ndarray) -> np.ndarray:
        """Легкое размытие изображения"""
        return cv2.GaussianBlur(image, (3, 3), 0)

    def _subtle_color_shift(self, image: np.ndarray) -> np.ndarray:
        """Незначительный сдвиг цветов"""
        # Сдвиг в HSV пространстве
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
        
        # Случайный сдвиг оттенка
        hue_shift = np.random.uniform(-5, 5)
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
        
        # Случайное изменение насыщенности
        sat_shift = np.random.uniform(-10, 10)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] + sat_shift, 0, 255)
        
        hsv = hsv.astype(np.uint8)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    def _add_high_frequency_noise(self, image: np.ndarray) -> np.ndarray:
        """Добавление высокочастотного шума"""
        # Создание высокочастотного шума
        noise = np.random.normal(0, 2, image.shape[:2]).astype(np.float32)
        
        # Применение шума к каждому каналу
        noisy_image = image.astype(np.float32)
        for c in range(3):
            noisy_image[:, :, c] += noise
        
        return np.clip(noisy_image, 0, 255).astype(np.uint8)

    def _local_contrast_adjustment(self, image: np.ndarray) -> np.ndarray:
        """Локальная корректировка контраста"""
        # Применение CLAHE к каждому каналу
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    def _edge_enhancement(self, image: np.ndarray) -> np.ndarray:
        """Усиление границ"""
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)
