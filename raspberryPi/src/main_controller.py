import time
import threading
import logging
import queue
from datetime import datetime
from enum import Enum
import pygame

logger = logging.getLogger("RaspberryPi")

class State(Enum):
    """系统状态枚举"""
    IDLE = 0           # 空闲状态，等待关键词
    PROCESSING = 1     # 处理中状态，正在拍照、录音、发送数据
    WAITING_SERVER = 2 # 等待服务器响应状态
    WAITING_STM32 = 3  # 等待STM32完成任务状态

class MainController:
    """主控类，负责协调各模块工作"""
    
    def __init__(self, sensor_controller, communication_interface, data_processor, keyword="冰淇淋"):
        self.keyword = keyword
        self.running = False
        self.emergency_restart_flag = False
        
        # 初始化各个模块
        self.sensor = sensor_controller
        self.comm = communication_interface
        self.processor = data_processor
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 状态和事件队列
        self.state = State.IDLE
        self.event_queue = queue.Queue()
        
        # 坐标队列，用于存储待发送的坐标
        self.coordinates_queue = queue.Queue()
    
    def start(self):
        """启动主控制器"""
        self.running = True
        
        # 启动主线程
        main_thread = threading.Thread(target=self.main_thread_func)
        main_thread.daemon = True
        main_thread.start()
        
        # 启动位置信息线程
        # position_thread = threading.Thread(target=self.position_thread_func)
        # position_thread.daemon = True
        # position_thread.start()
        
        logger.info("主控制器已启动")
        
        try:
            # 主程序循环
            while self.running:
                if self.emergency_restart_flag:
                    self.emergency_restart()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到键盘中断，正在停止...")
        finally:
            self.stop()
    
    def main_thread_func(self):
        """主控线程函数"""
        logger.info(f"开始监听关键词: '{self.keyword}'")
        
        stream = self.sensor.get_audio_stream()
        
        while self.running:
            try:
                # 根据当前状态执行不同的操作
                if self.state == State.IDLE:
                    # 空闲状态：监听关键词
                    data = stream.read(self.sensor.chunk, exception_on_overflow=False)
                    text = self.processor.recognize_speech(data)
                    
                    if text and self.keyword in text:
                        logger.info(f"检测到关键词: {self.keyword}!")
                        self.state = State.PROCESSING
                        self.event_queue.put(("keyword_detected", None))
                
                elif self.state == State.PROCESSING:
                    # 处理中状态：执行拍照、录音、发送数据等操作
                    event, data = self.event_queue.get(block=False)
                    if event == "keyword_detected":
                        # 处理关键词检测事件
                        self.process_keyword_detection()
                        # 处理完成后转为等待服务器响应状态
                        self.state = State.WAITING_SERVER
                    self.event_queue.task_done()
                
                elif self.state == State.WAITING_SERVER:
                    # 等待服务器响应状态：检查是否有服务器响应
                    # 这里不进行语音识别，只等待服务器响应
                    time.sleep(0.1)  # 减少CPU使用率
                    
                    # 如果收到服务器响应，处理响应并转为等待STM32状态或回到IDLE状态
                    if not self.event_queue.empty():
                        event, data = self.event_queue.get(block=False)
                        if event == "upload_response":
                            self.handle_server_upload_response(data)
                        elif event == "coordinates":
                            self.handle_coordinates_from_server(data)
                        elif event == "server_message":
                            self.handle_server_message(data)
                        self.event_queue.task_done()
                    
                    # 检查是否超时
                    if hasattr(self, 'wait_for_coordinates_timeout'):
                        if time.time() > self.wait_for_coordinates_timeout:
                            logger.warning("等待坐标数据超时，回到空闲状态")
                            self.state = State.IDLE
                            delattr(self, 'wait_for_coordinates_timeout')
                
                elif self.state == State.WAITING_STM32:
                    # 等待STM32完成任务状态：监控STM32任务完成状态
                    stm32_data = self.comm.read_from_stm32()
                    if stm32_data:
                        self.handle_stm32_response(stm32_data)
                        # 如果STM32任务完成，检查是否还有坐标需要发送
                        if "COMPLETE" in stm32_data:
                            if not self.coordinates_queue.empty():
                                # 还有坐标需要发送，发送下一组坐标
                                next_coord = self.coordinates_queue.get()
                                self.send_coordinate_to_stm32(next_coord)
                                # 保持在等待STM32状态
                            else:
                                # 所有坐标已发送完毕，回到空闲状态
                                logger.info("所有坐标已发送完毕")
                                self.state = State.IDLE
                        elif "ERROR" in stm32_data:
                            # 出错时清空坐标队列并回到空闲状态
                            logger.error(f"STM32报告错误: {stm32_data}")
                            while not self.coordinates_queue.empty():
                                self.coordinates_queue.get()
                            self.state = State.IDLE
                        else:
                            logger.warning(f"未识别的STM32响应: {stm32_data}")
                            # 未识别的响应，保持当前状态
            
            except queue.Empty:
                # 队列为空，继续循环
                pass
            except Exception as e:
                logger.error(f"主线程发生错误: {e}")
                if "致命错误" in str(e):  # 根据实际情况定义致命错误条件
                    self.emergency_restart_flag = True
        
        stream.stop_stream()
        stream.close()
    
    def position_thread_func(self):
        """位置信息线程函数"""
        logger.info("位置信息线程已启动")
        
        while self.running:
            try:
                # 读取STM32发送的位置数据
                data = self.comm.read_from_stm32()
                
                if data:
                    # 处理位置数据
                    position_data = self.processor.process_position_data(data)
                    
                    if position_data:
                        # 将位置信息上传至服务器
                        with self.lock:  # 使用锁确保线程安全
                            self.comm.send_position_to_server(position_data)
                
                time.sleep(0.1)  # 避免过度占用CPU
            
            except Exception as e:
                logger.error(f"位置信息线程发生错误: {e}")
        
        logger.info("位置信息线程已停止")
    
    def process_keyword_detection(self):
        """当检测到关键词时的处理流程"""
        logger.info("开始拍照录音...")
        # 播放提示音
        pygame.mixer.init()
        pygame.mixer.music.load("./audio/answer.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        img1_path, img2_path = self.sensor.capture_images()

        audio_path = self.sensor.record_audio()
        
        if img1_path and img2_path and audio_path:
            # 发送到服务器
            response = self.comm.send_to_server(img1_path, img2_path, audio_path)
            
            if response:
                # 将服务器响应放入事件队列
                self.event_queue.put(("upload_response", response))
                return True
            else:
                logger.error("服务器未返回有效响应")
                # 如果服务器未响应，回到空闲状态
                self.state = State.IDLE
                return False
        else:
            logger.error("拍照或录音失败")
            # 如果拍照或录音失败，回到空闲状态
            self.state = State.IDLE
            return False
    
    def handle_server_upload_response(self, response):
        """处理服务器上传响应"""
        logger.info(f"处理服务器响应: {response}")

        if 'success' in response and response['success'] is True:
            logger.info("文件上传成功，等待服务器处理...")
            self.wait_for_coordinates_timeout = time.time() + 30  # 30秒超时
        else:
            logger.warning("文件上传失败")
            self.state = State.IDLE

        '''# 检查响应中是否包含坐标数据
        if 'coordinates' in response:
            coordinates = response['coordinates']
            self.handle_coordinates_from_server(coordinates)
        else:
            # 如果响应中没有坐标数据，但有success字段且为True，说明是文件上传成功的响应
            # 此时应保持在WAITING_SERVER状态，等待后续的坐标数据
            if 'success' in response and response['success'] is True:
                logger.info("文件上传成功，等待服务器处理语音识别并发送坐标")
                self.wait_for_coordinates_timeout = time.time() + 30  # 30秒超时
            else:
                logger.warning("服务器响应中没有坐标数据")
                self.state = State.IDLE'''
                
    def handle_coordinates_from_server(self, coordinates):
        """处理从服务器接收到的坐标数据"""
        logger.info(f"从服务器接收到坐标数据: {coordinates}")
        
        # 清空坐标队列
        while not self.coordinates_queue.empty():
            self.coordinates_queue.get()
        
        if isinstance(coordinates, list):
            # 处理坐标列表
            pygame.mixer.init()
            pygame.mixer.music.load("./audio/order.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            if len(coordinates) == 1:
                logger.info("接收到1组指令，已发送")
                self.send_coordinate_to_stm32(coordinates[0])
                self.state = State.WAITING_STM32
            elif len(coordinates) == 2:
                logger.info("接收到2组指令，已发送第1组指令")
                self.send_coordinate_to_stm32(coordinates[0])
                self.coordinates_queue.put(coordinates[1])
                logger.info("第2组指令已加入队列")
                self.state = State.WAITING_STM32
            else:
                logger.warning(f"接收到意外数量的指令: {len(coordinates)}")
                self.state = State.IDLE
        else:
            logger.error("指令格式错误")
            self.state = State.IDLE
    
    def send_coordinate_to_stm32(self, coordinate):
        """向STM32发送坐标数据"""
        try:
            # 格式化坐标数据为STM32可接受的格式
            # 假设坐标格式为 {x: float, y: float, z: float}
            if 'x' in coordinate and 'y' in coordinate and 'z' in coordinate:
                x, y, z = coordinate['x'], coordinate['y'], coordinate['z']
                command = f"{x} {y} {z}\n\r"
                self.comm.send_to_stm32(command.encode('utf-8'))
                logger.info(f"已向STM32发送坐标: {command}")
                return True
            else:
                logger.error(f"坐标数据格式错误: {coordinate}")
                return False
        except Exception as e:
            logger.error(f"发送坐标到STM32失败: {e}")
            return False
    
    def handle_stm32_response(self, data):
        """处理STM32响应"""
        logger.info(f"处理STM32响应: {data}")
        
        if "COMPLETE" in data:
            logger.info("STM32任务完成")
            # 任务完成后的处理逻辑在主循环中处理
        elif "ERROR" in data:
            logger.error(f"STM32报告错误: {data}")
            self.state = State.IDLE
            # 错误处理逻辑在主循环中处理
    
    def handle_server_message(self, message):
        """处理从服务器接收到的消息"""
        logger.info(f"处理服务器消息: {message}")

        if message.startswith("ERROR:"):
            logger.error(f"服务器报告错误: {message}")
            self.state = State.IDLE
        else:
            # 处理其他类型的消息
            logger.info(f"收到服务器消息: {message}")
    
    def emergency_restart(self):
        """紧急重启功能"""
        logger.warning("执行紧急重启...")
        
        # 停止当前运行
        self.stop()
        
        # 等待资源释放
        time.sleep(2)
        
        # 重置标志和状态
        self.emergency_restart_flag = False
        self.running = True
        self.state = State.IDLE
        self.event_queue = queue.Queue()
        self.coordinates_queue = queue.Queue()
        
        # 重新启动线程
        main_thread = threading.Thread(target=self.main_thread_func)
        main_thread.daemon = True
        main_thread.start()
        
        # position_thread = threading.Thread(target=self.position_thread_func)
        # position_thread.daemon = True
        # position_thread.start()
        
        logger.info("紧急重启完成")
    
    def stop(self):
        """停止主控制器"""
        self.running = False
        
        # 清理资源
        self.sensor.cleanup()
        self.comm.cleanup()
        
        logger.info("主控制器已停止")