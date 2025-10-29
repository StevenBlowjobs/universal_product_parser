#!/usr/bin/env python3
"""
U2-Net модель для удаления фона
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import onnxruntime as ort
from pathlib import Path
from ...utils.logger import setup_logger
from ...utils.error_handler import retry_on_failure


class U2NetModel:
    """U2-Net модель для сегментации и удаления фона"""

    def __init__(self, model_path: str = None):
        self.logger = setup_logger("u2net_model")
        self.model_path = model_path or "models/u2net.onnx"
        self.session = None
        self._load_model()

    def _load_model(self):
        """Загрузка ONNX модели"""
        try:
            if not Path(self.model_path).exists():
                self.logger.error(f"❌ Модель U2-Net не найдена: {self.model_path}")
                # TODO: Скачать модель если нет
                return

            self.session = ort.InferenceSession(self.model_path)
            self.logger.info("✅ Модель U2-Net загружена")

        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки модели U2-Net: {e}")

    @retry_on_failure(max_retries=2)
    def predict_mask(self, image: np.ndarray) -> np.ndarray:
        """
        Предсказание маски для изображения

        Args:
            image: Входное изображение

        Returns:
            np.ndarray: Маска переднего плана
        """
        if self.session is None:
            self.logger.error("❌ Модель U2-Net не загружена")
            return np.ones(image.shape[:2], dtype=np.uint8) * 255

        try:
            # Предобработка изображения
            input_data = self._preprocess_image(image)

            # Предсказание
            input_name = self.session.get_inputs()[0].name
            output_name = self.session.get_outputs()[0].name
            result = self.session.run([output_name], {input_name: input_data})

            # Постобработка маски
            mask = self._postprocess_mask(result[0][0])

            return mask

        except Exception as e:
            self.logger.error(f"❌ Ошибка предсказания маски: {e}")
            return np.ones(image.shape[:2], dtype=np.uint8) * 255

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Предобработка изображения для модели"""
        # Ресайз до размера модели
        target_size = (320, 320)  # Стандартный размер для U2-Net
        resized = cv2.resize(image, target_size, interpolation=cv2.INTER_CUBIC)

        # Нормализация
        normalized = resized.astype(np.float32) / 255.0

        # Изменение порядка каналов и добавление batch dimension
        input_data = normalized.transpose(2, 0, 1)  # CHW
        input_data = np.expand_dims(input_data, 0)   # NCHW

        return input_data.astype(np.float32)

    def _postprocess_mask(self, mask: np.ndarray, original_shape: Tuple[int, int] = None) -> np.ndarray:
        """Постобработка маски"""
        # Ресайз до оригинального размера если нужно
        if original_shape is not None:
            mask = cv2.resize(mask, (original_shape[1], original_shape[0]), 
                            interpolation=cv2.INTER_CUBIC)

        # Бинаризация маски
        mask = (mask * 255).astype(np.uint8)
        _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        return binary_mask

    def is_loaded(self) -> bool:
        """Проверка загружена ли модель"""
        return self.session is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Получение информации о модели"""
        if self.session is None:
            return {}

        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()

        return {
            'model_path': self.model_path,
            'inputs': [{'name': i.name, 'shape': i.shape} for i in inputs],
            'outputs': [{'name': o.name, 'shape': o.shape} for o in outputs]
        }
