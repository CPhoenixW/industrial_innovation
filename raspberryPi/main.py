import os
import threading
from flask import Flask
from src.logger import setup_logger
from src.sensor_controller import SensorController
from src.communication_interface import CommunicationInterface
from src.data_processor import DataProcessor
from src.main_controller import MainController

def main():
    # 设置日志
    logger = setup_logger()
    logger.info("程序启动")
    
    # 配置参数
    keyword = "冰淇淋"
    server_url = "http://192.168.43.108:5000/upload"
    serial_port = '/dev/ttyAMA2'
    model_path = "vosk-model-small-cn-0.22"
    flask_port = 8080  # 设置Flask服务器端口
    
    # 确保临时文件夹存在
    temp_folder = "temp"
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    
    try:
        # 初始化各个模块
        sensor = SensorController(temp_folder=temp_folder)
        comm = CommunicationInterface(server_url=server_url, serial_port=serial_port)
        processor = DataProcessor(model_path=model_path)
        
        # 创建并启动主控制器
        controller = MainController(
            sensor_controller=sensor,
            communication_interface=comm,
            data_processor=processor,
            keyword=keyword
        )
        
        # 创建Flask应用
        app = Flask(__name__)
        
        # 设置接收坐标数据的端点
        comm.setup_coordinates_endpoint(app, controller)
        
        # 在新线程中启动Flask服务器
        def run_flask_app():
            app.run(host='0.0.0.0', port=flask_port)
        
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()
        
        logger.info(f"Flask服务器已启动，监听端口: {flask_port}")
        
        # 启动主控制器
        controller.start()
        
    except Exception as e:
        logger.error(f"程序发生错误: {e}")
    finally:
        logger.info("程序结束")

if __name__ == "__main__":
    main()