import logging
import threading
import os
import json
from datetime import datetime

logger = logging.getLogger("Server")


class ServerController:
    """服务器控制器，协调各个组件工作"""

    def __init__(self, file_manager, audio_processor, text_analyzer, communication_manager):
        self.file_manager = file_manager
        self.audio_processor = audio_processor
        self.text_analyzer = text_analyzer
        self.comm = communication_manager

        # 坐标映射，根据工件类型返回坐标
        # 这里只是示例，实际应根据需求修改
        self.coordinates_mapping = {
            "工件A": {"x": 10.0, "y": 20.0, "z": 5.0},
            "工件B": {"x": 30.0, "y": 40.0, "z": 5.0}
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

                # 生成坐标信息
                coordinates = self.generate_coordinates(extracted_info)

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

    def generate_coordinates(self, extracted_info):
        """根据提取的信息生成坐标"""
        coordinates = []

        for count, part_type in extracted_info:
            # 获取工件类型对应的坐标
            if part_type in self.coordinates_mapping:
                for _ in range(count):
                    coordinates.append(self.coordinates_mapping[part_type])
            else:
                logger.warning(f"未知的工件类型: {part_type}")

        logger.info(f"生成的坐标: {coordinates}")
        return coordinates