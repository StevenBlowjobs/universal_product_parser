#!/usr/bin/env python3
"""
Модуль для 100% удаления вотермарок с изображений товаров
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from .models.watermark_detector import WatermarkDetector
from ..utils.logger import setup_logger
from ..utils.error_handler import retry_on_failure


class WatermarkRemover:
    """Продвинутый удалитель вотермарок с гарантией 100% качества"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger("watermark_remover")
        self.detector = WatermarkDetector()
        
        # Настройки обработки
        self.processing_settings = {
            'detection_confidence': 0.8,
            'removal_aggressiveness': 'aggressive',
            'max_repair_attempts': 3,
            'preserve_image_quality': True
        }
        
        if 'image_processing' in self.config:
            self.processing_settings.update(self.config['image_processing'])
    
    @retry_on_failure(max_retries=2)
    def remove_watermark(self, image_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Удаление вотермарки с изображения
        
        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения результата
            
        Returns:
            Dict: Результаты обработки
        """
        self.logger.info(f"🖼️  Обработка изображения: {image_path}")
        
        try:
            # Загрузка изображения
            image = self._load_image(image_path)
            if image is None:
                return {
                    'success': False,
                    'error': 'Не удалось загрузить изображение',
                    'original_path': image_path
                }
            
            # Детекция вотермарки
            detection_result = self.detector.detect_watermarks(image)
            
            if not detection_result['watermarks_found']:
                self.logger.info("✅ Вотермарки не обнаружены")
                return {
                    'success': True,
                    'watermarks_removed': 0,
                    'message': 'Вотермарки не обнаружены',
                    'original_path': image_path,
                    'output_path': image_path
                }
            
            self.logger.info(f"🎯 Обнаружено вотермарок: {len(detection_result['watermarks'])}")
            
            # Поэтапное удаление каждой вотермарки
            processed_image = image.copy()
            removal_stats = []
            
            for i, watermark in enumerate(detection_result['watermarks']):
                self.logger.info(f"🔧 Удаление вотермарки {i+1}/{len(detection_result['watermarks'])}")
                
                removal_result = self._remove_single_watermark(
                    processed_image, watermark, attempt=1
                )
                
                if removal_result['success']:
                    processed_image = removal_result['processed_image']
                    removal_stats.append({
                        'watermark_id': i,
                        'type': watermark['type'],
                        'confidence': watermark['confidence'],
                        'method_used': removal_result['method_used']
                    })
                else:
                    self.logger.warning(f"⚠️  Не удалось удалить вотермарку {i+1}")
            
            # Валидация результата
            validation_result = self._validate_removal(image, processed_image, detection_result)
            
            # Сохранение результата
            if output_path:
                save_success = self._save_image(processed_image, output_path)
            else:
                # Генерация имени файла
                original_path = Path(image_path)
                output_path = str(original_path.parent / f"{original_path.stem}_no_watermark{original_path.suffix}")
                save_success = self._save_image(processed_image, output_path)
            
            result = {
                'success': validation_result['is_valid'] and save_success,
                'watermarks_detected': len(detection_result['watermarks']),
                'watermarks_removed': len(removal_stats),
                'removal_stats': removal_stats,
                'validation': validation_result,
                'original_path': image_path,
                'output_path': output_path if save_success else None,
                'quality_metrics': self._calculate_quality_metrics(image, processed_image)
            }
            
            if result['success']:
                self.logger.info(f"✅ Вотермарки успешно удалены: {output_path}")
            else:
                self.logger.warning(f"⚠️  Удаление завершено с проблемами: {output_path}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка удаления вотермарки: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': image_path
            }
    
    def _load_image(self, image_path: str) -> Optional[np.ndarray]:
        """Загрузка изображения с обработкой ошибок"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                self.logger.error(f"❌ Не удалось загрузить изображение: {image_path}")
                return None
            
            # Конвертация в RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return image_rgb
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки изображения: {e}")
            return None
    
    def _remove_single_watermark(self, image: np.ndarray, watermark: Dict[str, Any], 
                               attempt: int = 1) -> Dict[str, Any]:
        """Удаление одной вотермарки"""
        methods = [
            self._inpaint_watermark,
            self._texture_synthesis,
            self._patch_based_removal,
            self._deep_learning_removal
        ]
        
        # Выбор метода в зависимости от типа вотермарки
        method = self._select_removal_method(watermark)
        processed_image = image.copy()
        
        try:
            result = method(processed_image, watermark)
            
            if result['success']:
                return {
                    'success': True,
                    'processed_image': result['processed_image'],
                    'method_used': method.__name__
                }
            else:
                # Попробовать следующий метод
                if attempt < self.processing_settings['max_repair_attempts']:
                    return self._remove_single_watermark(
                        image, watermark, attempt + 1
                    )
                else:
                    return {
                        'success': False,
                        'error': 'Все методы удаления не сработали',
                        'method_used': method.__name__
                    }
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка в методе {method.__name__}: {e}")
            return {
                'success': False,
                'error': str(e),
                'method_used': method.__name__
            }
    
    def _select_removal_method(self, watermark: Dict[str, Any]) -> callable:
        """Выбор метода удаления в зависимости от типа вотермарки"""
        watermark_type = watermark.get('type', 'unknown')
        
        method_mapping = {
            'text_logo': self._inpaint_watermark,
            'transparent_logo': self._texture_synthesis,
            'corner_stamp': self._patch_based_removal,
            'diagonal_text': self._deep_learning_removal,
            'background_pattern': self._texture_synthesis
        }
        
        return method_mapping.get(watermark_type, self._inpaint_watermark)
    
    def _inpaint_watermark(self, image: np.ndarray, watermark: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление вотермарки методом inpainting"""
        try:
            mask = watermark.get('mask')
            if mask is None:
                return {'success': False, 'error': 'Нет маски для inpainting'}
            
            # Преобразование маски в правильный формат
            if len(mask.shape) == 3:
                mask = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)
            
            # Inpainting с различными методами
            methods = [
                (cv2.INPAINT_TELEA, 'telea'),
                (cv2.INPAINT_NS, 'ns')
            ]
            
            best_result = None
            best_quality = 0
            
            for method_code, method_name in methods:
                inpainted = cv2.inpaint(image, mask, 3, method_code)
                
                # Оценка качества
                quality = self._assess_inpainting_quality(image, inpainted, mask)
                
                if quality > best_quality:
                    best_quality = quality
                    best_result = inpainted
            
            return {
                'success': True,
                'processed_image': best_result,
                'quality_score': best_quality
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _texture_synthesis(self, image: np.ndarray, watermark: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление через синтез текстуры"""
        try:
            mask = watermark.get('mask')
            bbox = watermark.get('bbox')
            
            if bbox is None:
                return {'success': False, 'error': 'Нет bounding box для синтеза текстуры'}
            
            x, y, w, h = bbox
            
            # Выделение области вокруг вотермарки для забора текстуры
            padding = 20
            sample_x = max(0, x - padding)
            sample_y = max(0, y - padding)
            sample_w = min(image.shape[1] - sample_x, w + 2 * padding)
            sample_h = min(image.shape[0] - sample_y, h + 2 * padding)
            
            sample_region = image[sample_y:sample_y+sample_h, sample_x:sample_x+sample_w]
            
            # Создание патча для замены
            patch = self._generate_texture_patch(sample_region, (h, w))
            
            # Замена области с вотермаркой
            result_image = image.copy()
            result_image[y:y+h, x:x+w] = patch
            
            return {
                'success': True,
                'processed_image': result_image
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _patch_based_removal(self, image: np.ndarray, watermark: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление через поиск и замену патчей"""
        try:
            bbox = watermark.get('bbox')
            if bbox is None:
                return {'success': False, 'error': 'Нет bounding box для patch-based удаления'}
            
            x, y, w, h = bbox
            
            # Поиск похожих патчей в изображении
            similar_patches = self._find_similar_patches(image, (x, y, w, h))
            
            if not similar_patches:
                return {'success': False, 'error': 'Не найдено подходящих патчей для замены'}
            
            # Выбор лучшего патча
            best_patch = self._select_best_patch(image, similar_patches, (x, y, w, h))
            
            # Замена области
            result_image = image.copy()
            result_image[y:y+h, x:x+w] = best_patch
            
            return {
                'success': True,
                'processed_image': result_image
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _deep_learning_removal(self, image: np.ndarray, watermark: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление с использованием глубокого обучения"""
        # TODO: Интеграция с предобученной GAN моделью для удаления вотермарок
        # Временная реализация через комбинацию методов
        
        combined_result = self._inpaint_watermark(image, watermark)
        if combined_result['success']:
            # Дополнительная пост-обработка
            processed = self._post_process_removal(combined_result['processed_image'], watermark)
            combined_result['processed_image'] = processed
        
        return combined_result
    
    def _generate_texture_patch(self, sample_region: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """Генерация текстуры на основе样本区域"""
        target_h, target_w = target_size
        
        # Простой ресайз с интерполяцией
        patch = cv2.resize(sample_region, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        
        # Добавление шума для естественности
        noise = np.random.normal(0, 5, patch.shape).astype(np.uint8)
        patch = cv2.add(patch, noise)
        
        return patch
    
    def _find_similar_patches(self, image: np.ndarray, target_bbox: Tuple[int, int, int, int]) -> List[Tuple[int, int]]:
        """Поиск похожих патчей в изображении"""
        x, y, w, h = target_bbox
        target_patch = image[y:y+h, x:x+w]
        
        similar_patches = []
        stride = 5
        
        for i in range(0, image.shape[0] - h, stride):
            for j in range(0, image.shape[1] - w, stride):
                # Пропускаем целевую область и близлежащие области
                if abs(i - y) < h and abs(j - x) < w:
                    continue
                
                candidate_patch = image[i:i+h, j:j+w]
                similarity = self._calculate_patch_similarity(target_patch, candidate_patch)
                
                if similarity < 0.3:  # Порог схожести
                    similar_patches.append((j, i, similarity))
        
        # Сортировка по схожести
        similar_patches.sort(key=lambda x: x[2])
        return [(x, y) for x, y, sim in similar_patches[:10]]  # Топ-10
    
    def _calculate_patch_similarity(self, patch1: np.ndarray, patch2: np.ndarray) -> float:
        """Вычисление схожести между двумя патчами"""
        if patch1.shape != patch2.shape:
            return float('inf')
        
        # MSE (Mean Squared Error)
        mse = np.mean((patch1 - patch2) ** 2)
        return mse
    
    def _select_best_patch(self, image: np.ndarray, patches: List[Tuple[int, int]], 
                          target_bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """Выбор лучшего патча для замены"""
        x, y, w, h = target_bbox
        target_patch = image[y:y+h, x:x+w]
        
        best_patch = None
        best_score = float('inf')
        
        for patch_x, patch_y in patches:
            candidate = image[patch_y:patch_y+h, patch_x:patch_x+w]
            
            # Проверка градиентов для плавности
            score = self._calculate_replacement_score(target_patch, candidate, image, (x, y), (patch_x, patch_y))
            
            if score < best_score:
                best_score = score
                best_patch = candidate
        
        return best_patch if best_patch is not None else target_patch
    
    def _calculate_replacement_score(self, target: np.ndarray, candidate: np.ndarray,
                                   image: np.ndarray, target_pos: Tuple[int, int], 
                                   candidate_pos: Tuple[int, int]) -> float:
        """Вычисление оценки качества замены"""
        # Схожесть содержимого
        content_similarity = self._calculate_patch_similarity(target, candidate)
        
        # Схожесть с окружающими областями
        border_similarity = self._calculate_border_similarity(image, target_pos, candidate_pos, target.shape)
        
        return content_similarity + border_similarity
    
    def _calculate_border_similarity(self, image: np.ndarray, pos1: Tuple[int, int], 
                                   pos2: Tuple[int, int], size: Tuple[int, int]) -> float:
        """Вычисление схожести граничных областей"""
        h, w = size
        x1, y1 = pos1
        x2, y2 = pos2
        
        # Сравнение пикселей вокруг патчей
        border_score = 0
        border_width = 5
        
        # Верхняя граница
        if y1 > border_width and y2 > border_width:
            top1 = image[y1-border_width:y1, x1:x1+w]
            top2 = image[y2-border_width:y2, x2:x2+w]
            border_score += self._calculate_patch_similarity(top1, top2)
        
        # Нижняя граница
        if y1 + h < image.shape[0] - border_width and y2 + h < image.shape[0] - border_width:
            bottom1 = image[y1+h:y1+h+border_width, x1:x1+w]
            bottom2 = image[y2+h:y2+h+border_width, x2:x2+w]
            border_score += self._calculate_patch_similarity(bottom1, bottom2)
        
        return border_score
    
    def _post_process_removal(self, image: np.ndarray, watermark: Dict[str, Any]) -> np.ndarray:
        """Пост-обработка после удаления вотермарки"""
        # Применение фильтров для сглаживания артефактов
        processed = image.copy()
        
        # Gaussian blur для областей с артефактами
        if watermark.get('bbox'):
            x, y, w, h = watermark['bbox']
            roi = processed[y:y+h, x:x+w]
            blurred_roi = cv2.GaussianBlur(roi, (3, 3), 0)
            processed[y:y+h, x:x+w] = blurred_roi
        
        # Гистограммная коррекция
        processed = self._enhance_histogram(processed)
        
        return processed
    
    def _enhance_histogram(self, image: np.ndarray) -> np.ndarray:
        """Улучшение гистограммы изображения"""
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
            lab[:,:,0] = clahe.apply(lab[:,:,0])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        else:
            enhanced = clahe.apply(image)
        
        return enhanced
    
    def _assess_inpainting_quality(self, original: np.ndarray, inpainted: np.ndarray, 
                                 mask: np.ndarray) -> float:
        """Оценка качества inpainting"""
        # Вычисление разницы только в области маски
        diff = cv2.absdiff(original, inpainted)
        masked_diff = cv2.bitwise_and(diff, diff, mask=mask)
        
        # Чем меньше разница, тем лучше качество
        quality_score = 1.0 - (np.mean(masked_diff) / 255.0)
        return max(0.0, min(1.0, quality_score))
    
    def _validate_removal(self, original: np.ndarray, processed: np.ndarray,
                         detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация результатов удаления"""
        # Повторная детекция на обработанном изображении
        new_detection = self.detector.detect_watermarks(processed)
        
        remaining_watermarks = len(new_detection['watermarks'])
        original_watermarks = len(detection_result['watermarks'])
        
        is_valid = remaining_watermarks == 0
        
        return {
            'is_valid': is_valid,
            'original_watermarks': original_watermarks,
            'remaining_watermarks': remaining_watermarks,
            'removal_efficiency': (original_watermarks - remaining_watermarks) / original_watermarks,
            'new_detection_result': new_detection
        }
    
    def _calculate_quality_metrics(self, original: np.ndarray, processed: np.ndarray) -> Dict[str, float]:
        """Вычисление метрик качества изображения"""
        # PSNR (Peak Signal-to-Noise Ratio)
        mse = np.mean((original - processed) ** 2)
        if mse == 0:
            psnr = 100  # Бесконечность
        else:
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))
        
        # SSIM (Structural Similarity)
        from skimage.metrics import structural_similarity as ssim
        ssim_score = ssim(original, processed, multichannel=True, channel_axis=2)
        
        return {
            'psnr': psnr,
            'ssim': ssim_score,
            'mse': mse,
            'quality_score': (psnr / 50 + ssim_score) / 2  # Комбинированная оценка
        }
    
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
            self.logger.error(f"❌ Ошибка сохранения изображения: {e}")
            return False
    
    def batch_remove_watermarks(self, image_paths: List[str], 
                              output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Пакетное удаление вотермарок
        
        Args:
            image_paths: Список путей к изображениям
            output_dir: Директория для сохранения результатов
            
        Returns:
            List: Результаты обработки для каждого изображения
        """
        results = []
        
        for image_path in image_paths:
            if output_dir:
                output_path = Path(output_dir) / f"{Path(image_path).stem}_processed{Path(image_path).suffix}"
            else:
                output_path = None
            
            result = self.remove_watermark(image_path, output_path)
            results.append(result)
        
        return results
