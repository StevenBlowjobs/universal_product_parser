#!/usr/bin/env python3
"""
Детектор вотермарок на изображениях
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from ...utils.logger import setup_logger
from ...utils.error_handler import retry_on_failure


class WatermarkDetector:
    """Детектор вотермарок с использованием компьютерного зрения"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("watermark_detector")

        # Параметры детекции
        self.detection_params = {
            'min_watermark_area': 100,
            'max_watermark_area': 50000,
            'edge_threshold': 50,
            'texture_threshold': 0.1,
            'corner_confidence': 0.7
        }

        if 'image_processing' in self.config:
            self.detection_params.update(self.config['image_processing'])

    @retry_on_failure(max_retries=2)
    def detect_watermarks(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Детекция вотермарок на изображении

        Args:
            image: Входное изображение

        Returns:
            Dict: Результаты детекции
        """
        self.logger.info("🔍 Детекция вотермарок")

        try:
            watermarks = []
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

            # Комбинирование различных методов детекции
            methods = [
                self._detect_by_edges,
                self._detect_by_texture,
                self._detect_by_corners,
                self._detect_by_contours
            ]

            for method in methods:
                method_result = method(image, gray)
                watermarks.extend(method_result)

            # Фильтрация дубликатов
            filtered_watermarks = self._filter_overlapping_watermarks(watermarks)

            result = {
                'watermarks_found': len(filtered_watermarks) > 0,
                'watermarks': filtered_watermarks,
                'total_detected': len(filtered_watermarks)
            }

            self.logger.info(f"🎯 Обнаружено вотермарок: {len(filtered_watermarks)}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка детекции вотермарок: {e}")
            return {
                'watermarks_found': False,
                'watermarks': [],
                'error': str(e)
            }

    def _detect_by_edges(self, image: np.ndarray, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Детекция по границам"""
        watermarks = []

        # Детекция границ
        edges = cv2.Canny(gray, 50, 150)

        # Поиск контуров
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if self.detection_params['min_watermark_area'] < area < self.detection_params['max_watermark_area']:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Проверка формы (вотермарки часто прямоугольные)
                aspect_ratio = w / h
                if 0.2 < aspect_ratio < 5:
                    watermarks.append({
                        'bbox': (x, y, w, h),
                        'type': 'edge_based',
                        'confidence': min(area / 1000, 1.0),
                        'area': area
                    })

        return watermarks

    def _detect_by_texture(self, image: np.ndarray, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Детекция по текстуре"""
        watermarks = []

        # Вычисление текстурных особенностей
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)

        # Нормализация
        gradient_magnitude = (gradient_magnitude / gradient_magnitude.max() * 255).astype(np.uint8)

        # Пороговая обработка
        _, texture_mask = cv2.threshold(gradient_magnitude, 50, 255, cv2.THRESH_BINARY)

        # Морфологические операции
        kernel = np.ones((3, 3), np.uint8)
        texture_mask = cv2.morphologyEx(texture_mask, cv2.MORPH_CLOSE, kernel)

        # Поиск контуров
        contours, _ = cv2.findContours(texture_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.detection_params['min_watermark_area']:
                x, y, w, h = cv2.boundingRect(contour)
                watermarks.append({
                    'bbox': (x, y, w, h),
                    'type': 'texture_based',
                    'confidence': 0.6,
                    'area': area
                })

        return watermarks

    def _detect_by_corners(self, image: np.ndarray, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Детекция по угловым особенностям"""
        watermarks = []

        # Детектор углов Ши-Томаси
        corners = cv2.goodFeaturesToTrack(gray, 100, 0.01, 10)
        
        if corners is not None:
            corners = np.int0(corners)

            # Группировка углов в кластеры
            corner_clusters = self._cluster_corners(corners)

            for cluster in corner_clusters:
                if len(cluster) >= 4:  # Минимум 4 угла для прямоугольника
                    x_coords = [c[0][0] for c in cluster]
                    y_coords = [c[0][1] for c in cluster]
                    
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    
                    w = x_max - x_min
                    h = y_max - y_min
                    area = w * h

                    if self.detection_params['min_watermark_area'] < area < self.detection_params['max_watermark_area']:
                        watermarks.append({
                            'bbox': (x_min, y_min, w, h),
                            'type': 'corner_based',
                            'confidence': self.detection_params['corner_confidence'],
                            'area': area,
                            'corner_count': len(cluster)
                        })

        return watermarks

    def _detect_by_contours(self, image: np.ndarray, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Детекция по контурам"""
        watermarks = []

        # Адаптивная пороговая обработка
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)

        # Инвертирование
        thresh = cv2.bitwise_not(thresh)

        # Поиск контуров
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.detection_params['min_watermark_area']:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Проверка на текст (высокое соотношение периметра к площади)
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity < 0.5:  # Низкая круглость - возможно текст
                        watermarks.append({
                            'bbox': (x, y, w, h),
                            'type': 'contour_based',
                            'confidence': 0.7,
                            'area': area,
                            'circularity': circularity
                        })

        return watermarks

    def _cluster_corners(self, corners: np.ndarray, max_distance: int = 50) -> List[List]:
        """Кластеризация углов"""
        clusters = []
        used = set()

        for i, corner1 in enumerate(corners):
            if i in used:
                continue

            cluster = [corner1]
            used.add(i)

            for j, corner2 in enumerate(corners):
                if j in used:
                    continue

                # Вычисление расстояния между углами
                dist = np.sqrt((corner1[0][0] - corner2[0][0])**2 + 
                             (corner1[0][1] - corner2[0][1])**2)

                if dist < max_distance:
                    cluster.append(corner2)
                    used.add(j)

            clusters.append(cluster)

        return clusters

    def _filter_overlapping_watermarks(self, watermarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Фильтрация перекрывающихся вотермарок"""
        if not watermarks:
            return []

        # Сортировка по уверенности
        watermarks.sort(key=lambda x: x['confidence'], reverse=True)

        filtered = []
        used_areas = []

        for wm in watermarks:
            bbox = wm['bbox']
            x, y, w, h = bbox
            current_area = (x, y, x + w, y + h)

            # Проверка перекрытия с уже добавленными
            overlap = False
            for used_area in used_areas:
                if self._calculate_iou(current_area, used_area) > 0.3:
                    overlap = True
                    break

            if not overlap:
                filtered.append(wm)
                used_areas.append(current_area)

        return filtered

    def _calculate_iou(self, box1: Tuple, box2: Tuple) -> float:
        """Вычисление Intersection over Union"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        # Вычисление площади пересечения
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)

        inter_area = max(0, inter_x_max - inter_x_min) * max(0, inter_y_max - inter_y_min)

        # Вычисление площади объединения
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = area1 + area2 - inter_area

        return inter_area / union_area if union_area > 0 else 0
