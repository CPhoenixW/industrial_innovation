import logging
import threading
import os
import json
from datetime import datetime
from src.homography_processor import HomographyProcessor
from src.yolo_detector import YOLODetector

logger = logging.getLogger("Server")

class ServerController:
    """服务器控制器，协调各个组件工作"""

    def __init__(self, file_manager, audio_processor, text_analyzer, communication_manager):
        self.file_manager = file_manager
        self.audio_processor = audio_processor
        self.text_analyzer = text_analyzer
        self.comm = communication_manager
        self.homography_processor = HomographyProcessor()
        self.yolo_detector = YOLODetector()

        # 坐标映射，根据工件类型返回坐标（作为备用）
        self.coordinates_mapping = {
            "工件A": {"x": 10.0, "y": 20.0, "z": 0.0},
            "工件B": {"x": 30.0, "y": 40.0, "z": 0.0}
        }

    def process_upload(self, image1, image2, audio):
        """处理上传的文件"""
        try:
            # 创建会话文件夹
            session_folder, timestamp = self.file_manager.create_session_folder()

            # 保存文件
            image1_path = self.file_manager.save_file(image1, session_folder, f"image1_{timestamp}.jpg")
            image2_path = self.file_manager.save_file(image2, session_folder, f"image2_{timestamp}.jpg")
            audio_path = self.file_manager.save_file(audio, session_folder, f"audio_{timestamp}.wav")

            # 获取识别结果文件路径
            result_path = self.file_manager.get_recognition_path(session_folder, timestamp)

            # 在新线程中处理语音识别
            def process_audio():
                self.audio_processor.recognize_audio(audio_path, result_path)

                # 读取识别结果
                text = self.file_manager.read_recognition_result(result_path)

                # 分析文本，提取数词和工件类型
                extracted_info = self.text_analyzer.extract_info(text)

                # 检查是否返回了错误信息
                if isinstance(extracted_info, str) and extracted_info.startswith("ERROR:"):
                    # 向树莓派发送错误信息
                    self.comm.send_message_to_raspberry_pi(extracted_info)
                    logger.error(f"文本分析错误: {extracted_info}")
                    return

                # 生成坐标信息
                coordinates = self.generate_coordinates(extracted_info, image1_path)

                # 向树莓派发送坐标信息
                self.comm.send_coordinates_to_raspberry_pi(coordinates)

            # 启动线程
            thread = threading.Thread(target=process_audio)
            thread.daemon = True
            thread.start()

            return {
                'success': True,
                'message': '文件上传成功，正在进行语音识别，将向树莓派发送坐标',
                'files': {
                    'image1': image1_path,
                    'image2': image2_path,
                    'audio': audio_path,
                    'recognition': result_path
                }
            }

        except Exception as e:
            logger.error(f"处理上传文件时出错: {str(e)}")
            return {'error': str(e)}

    def generate_coordinates(self, extracted_info, img_path):
        """根据提取的信息和图像生成坐标，支持YOLO自动检测和交互式提取"""
        coordinates = []

        # 检查是否已加载单应性矩阵
        if not self.homography_processor.load_homography():
            # 如果没有单应性矩阵，进入标定模式
            logger.info("未找到单应性矩阵，开始交互式标定")
            if not self.homography_processor.interactive_calibration(img_path):
                logger.error("标定失败，回退到默认坐标映射")
                # 回退到原来的坐标映射逻辑
                for count, part_type in extracted_info:
                    if part_type in self.coordinates_mapping:
                        for _ in range(count):
                            coordinates.append(self.coordinates_mapping[part_type])
                    else:
                        logger.warning(f"未知的工件类型: {part_type}")
                return coordinates
            self.homography_processor.save_homography()

        # 首先尝试使用YOLO自动检测
        try:
            logger.info("尝试使用YOLO自动检测物体坐标")
            yolo_coordinates = self.yolo_detector.get_world_coordinates(img_path)
            
            if yolo_coordinates:
                logger.info(f"YOLO检测到 {len(yolo_coordinates)} 个物体坐标: {yolo_coordinates}")
                
                # 根据语音指令的数量要求筛选坐标
                total_required = sum(count for count, _ in extracted_info)
                
                if len(yolo_coordinates) >= total_required:
                    # 如果检测到的物体数量足够，直接使用前N个
                    coordinates = yolo_coordinates[:total_required]
                    logger.info(f"使用YOLO检测的前 {total_required} 个坐标")
                else:
                    # 如果检测到的物体数量不足，使用所有检测到的坐标
                    coordinates = yolo_coordinates
                    logger.warning(f"YOLO检测到的物体数量({len(yolo_coordinates)})少于要求数量({total_required})")
                
                return coordinates
            else:
                logger.warning("YOLO未检测到任何物体，回退到交互式提取")
                
        except Exception as e:
            logger.error(f"YOLO检测失败: {str(e)}，回退到交互式提取")

        # 如果YOLO检测失败或未检测到物体，使用交互式提取
        logger.info("使用交互式方法提取坐标")
        for count, part_type in extracted_info:
            logger.info(f"处理工件类型 {part_type}，需要 {count} 个坐标")
            coords = self.homography_processor.interactive_query(img_path, count)
            coordinates.extend(coords)

        logger.info(f"生成的坐标: {coordinates}")
        return coordinates