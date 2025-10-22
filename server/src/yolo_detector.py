import cv2
import numpy as np
import logging
from ultralytics import YOLO
from .homography_processor import HomographyProcessor

logger = logging.getLogger("YOLODetector")


class YOLODetector:
    """YOLO物体检测类，集成坐标转换功能"""
    
    def __init__(self, model_path="../weights/best.pt",
                 homography_matrix_file="../weights/homography.npy"):
        """
        初始化YOLO检测器
        
        Args:
            model_path: YOLO模型路径
            homography_matrix_file: 单应性矩阵文件路径
        """
        self.model = YOLO(model_path)
        self.homography_processor = HomographyProcessor(homography_matrix_file)
        
        # 加载单应性矩阵
        if not self.homography_processor.load_homography():
            logger.warning("未找到单应性矩阵，需要先进行标定")
        
        logger.info(f"YOLO检测器初始化完成，模型路径: {model_path}")
    
    def detect_objects(self, image_path, confidence_threshold=0.5):
        """
        检测图像中的物体并返回中心点坐标
        
        Args:
            image_path: 图像路径
            confidence_threshold: 置信度阈值
            
        Returns:
            list: 检测结果列表，每个元素包含像素坐标和真实世界坐标
        """
        try:
            # 进行YOLO检测
            results = self.model(image_path, conf=confidence_threshold)
            
            detections = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        
                        # 计算中心点
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        
                        # 获取置信度和类别
                        confidence = float(box.conf[0])
                        class_id = int(box.cls[0])
                        class_name = self.model.names[class_id]
                        
                        # 转换为真实世界坐标
                        world_coords = self.homography_processor.pixel_to_world(center_x, center_y)
                        
                        detection = {
                            'pixel_coords': {'x': center_x, 'y': center_y},
                            'world_coords': None,
                            'bbox': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
                            'confidence': confidence,
                            'class_id': class_id,
                            'class_name': class_name
                        }
                        
                        if world_coords:
                            world_x, world_y = world_coords
                            detection['world_coords'] = {
                                'x': world_x / 10 - 7,  # 根据HomographyProcessor的转换规则
                                'y': world_y / 10 - 5.2,
                                'z': 0.0
                            }
                        
                        detections.append(detection)
                        
                        logger.info(f"检测到 {class_name}: 像素坐标({center_x}, {center_y}), "
                                  f"真实坐标({detection['world_coords']}), 置信度: {confidence:.2f}")
            
            return detections
            
        except Exception as e:
            logger.error(f"物体检测失败: {str(e)}")
            return []
    
    def detect_and_visualize(self, image_path, output_path=None, confidence_threshold=0.5):
        """
        检测物体并可视化结果
        
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径（可选）
            confidence_threshold: 置信度阈值
            
        Returns:
            list: 检测结果列表
        """
        detections = self.detect_objects(image_path, confidence_threshold)
        
        # 加载图像进行可视化
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"无法加载图像: {image_path}")
            return detections
        
        # 绘制检测结果
        for detection in detections:
            bbox = detection['bbox']
            pixel_coords = detection['pixel_coords']
            world_coords = detection['world_coords']
            
            # 绘制边界框
            cv2.rectangle(img, (int(bbox['x1']), int(bbox['y1'])), 
                         (int(bbox['x2']), int(bbox['y2'])), (0, 255, 0), 2)
            
            # 绘制中心点
            cv2.circle(img, (pixel_coords['x'], pixel_coords['y']), 5, (0, 0, 255), -1)
            
            # 添加标签
            label = f"{detection['class_name']}: {detection['confidence']:.2f}"
            if world_coords:
                label += f"\nWorld: ({world_coords['x']:.2f}, {world_coords['y']:.2f})"
            
            cv2.putText(img, label, (int(bbox['x1']), int(bbox['y1']) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 保存或显示结果
        if output_path:
            cv2.imwrite(output_path, img)
            logger.info(f"检测结果已保存到: {output_path}")
        
        return detections
    
    def get_world_coordinates(self, image_path, confidence_threshold=0.5):
        """
        简化接口：直接返回检测到的物体的真实世界坐标列表
        
        Args:
            image_path: 图像路径
            confidence_threshold: 置信度阈值
            
        Returns:
            list: 真实世界坐标列表，格式为 [{'x': x, 'y': y, 'z': z}, ...]
        """
        detections = self.detect_objects(image_path, confidence_threshold)
        coordinates = []
        
        for detection in detections:
            if detection['world_coords']:
                coordinates.append(detection['world_coords'])
        
        return coordinates