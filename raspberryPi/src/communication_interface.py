import serial
import requests
import logging
from datetime import datetime
from flask import request, jsonify

logger = logging.getLogger("RaspberryPi")

class CommunicationInterface:
    """通信接口类，负责与STM32和服务器的通信"""
    
    def __init__(self, server_url, serial_port='/dev/ttyAMA10', baud_rate=115200):
        self.server_url = server_url
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.ser = None
        self.connect_stm32()
    
    def connect_stm32(self):
        """连接STM32"""
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            logger.info(f"成功连接到STM32，端口: {self.serial_port}")
            return True
        except Exception as e:
            logger.error(f"连接STM32失败: {e}")
            return False
    
    def send_to_stm32(self, data):
        """向STM32发送数据"""
        if not self.ser:
            logger.error("STM32未连接")
            return False
        
        try:
            self.ser.write(data)
            logger.info(f"已发送数据到STM32: {data}")
            return True
        except Exception as e:
            logger.error(f"发送数据到STM32失败: {e}")
            return False
    
    def read_from_stm32(self):
        """从STM32读取数据"""
        if not self.ser:
            logger.error("STM32未连接")
            return None
        
        try:
            if self.ser.in_waiting > 0:
                data = self.ser.readline().decode('utf-8').strip()
                logger.info(f"从STM32接收到数据: {data}")
                return data
            return None
        except Exception as e:
            logger.error(f"从STM32读取数据失败: {e}")
            return None
    
    def send_to_server(self, img1_path, img2_path, audio_path):
        """将图片和音频发送到服务器"""
        try:
            files = {
                'image1': open(img1_path, 'rb'),
                'image2': open(img2_path, 'rb'),
                'audio': open(audio_path, 'rb')
            }
            
            response = requests.post(self.server_url, files=files)
            
            # 关闭文件
            for f in files.values():
                f.close()
            
            if response.status_code == 200:
                logger.info("文件成功发送到服务器")
                return response.json()
            else:
                logger.error(f"发送失败，状态码: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"发送文件时出错: {e}")
            return None
    
    def send_position_to_server(self, position_data):
        """将位置信息发送到服务器"""
        try:
            response = requests.post(f"{self.server_url}/position", json=position_data)
            
            if response.status_code == 200:
                logger.info("位置信息成功发送到服务器")
                return True
            else:
                logger.error(f"发送位置信息失败，状态码: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"发送位置信息时出错: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        if self.ser:
            self.ser.close()
            
    def setup_coordinates_endpoint(self, app, main_controller):
        """设置接收坐标数据的端点"""
        @app.route('/coordinates', methods=['POST'])
        def receive_coordinates():
            try:
                data = request.json
                if 'coordinates' in data:
                    logger.info(f"接收到坐标数据: {data['coordinates']}")
                    # 将坐标数据放入事件队列
                    main_controller.event_queue.put(("coordinates", data['coordinates']))
                    return jsonify({"status": "success"})
                else:
                    logger.error("接收到的数据中没有坐标信息")
                    return jsonify({"status": "error", "message": "没有坐标信息"}), 400
            except Exception as e:
                logger.error(f"处理坐标数据时出错: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500