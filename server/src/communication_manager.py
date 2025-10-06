import logging
import requests

logger = logging.getLogger("Server")


class CommunicationManager:
    """通信管理类，负责与树莓派的通信"""

    def __init__(self, raspberry_pi_ip, raspberry_pi_port):
        self.raspberry_pi_ip = raspberry_pi_ip
        self.raspberry_pi_port = raspberry_pi_port

    def send_message_to_raspberry_pi(self, message):
        """向树莓派发送消息"""
        try:
            url = f"http://{self.raspberry_pi_ip}:{self.raspberry_pi_port}/message"
            data = {"message": message}
            response = requests.post(url, json=data, timeout=5)

            if response.status_code == 200:
                logger.info(f"成功向树莓派发送消息: {message}")
                return True
            else:
                logger.error(f"向树莓派发送消息失败，状态码: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"向树莓派发送消息时出错: {str(e)}")
            return False

    def send_coordinates_to_raspberry_pi(self, coordinates):
        """向树莓派发送坐标数据"""
        try:
            url = f"http://{self.raspberry_pi_ip}:{8080}/coordinates"
            data = {"coordinates": coordinates}

            response = requests.post(url, json=data, timeout=5)

            if response.status_code == 200:
                logger.info(f"成功向树莓派发送坐标数据: {coordinates}")
                return True
            else:
                logger.error(f"向树莓派发送坐标数据失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"向树莓派发送坐标数据时出错: {e}")
            return False