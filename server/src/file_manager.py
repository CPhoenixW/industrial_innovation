import os
import logging
from datetime import datetime

logger = logging.getLogger("Server")

class FileManager:
    """文件管理类，负责处理文件的保存和管理"""
    
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        self._ensure_upload_folder_exists()
    
    def _ensure_upload_folder_exists(self):
        """确保上传文件夹存在"""
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)
            logger.info(f"创建上传文件夹: {self.upload_folder}")
    
    def create_session_folder(self):
        """创建新的会话文件夹，使用时间戳命名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(self.upload_folder, timestamp)
        
        if not os.path.exists(session_folder):
            os.makedirs(session_folder)
            logger.info(f"创建会话文件夹: {session_folder}")
        
        return session_folder, timestamp
    
    def save_file(self, file_obj, folder_path, filename):
        """保存文件到指定文件夹"""
        file_path = os.path.join(folder_path, filename)
        file_obj.save(file_path)
        logger.info(f"文件已保存: {file_path}")
        return file_path
    
    def get_recognition_path(self, folder_path, timestamp):
        """获取识别结果文件路径"""
        return os.path.join(folder_path, f"recognition_{timestamp}.txt")
    
    def read_recognition_result(self, result_path):
        """读取识别结果文件"""
        try:
            if os.path.exists(result_path):
                with open(result_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            else:
                logger.warning(f"识别结果文件不存在: {result_path}")
                return None
        except Exception as e:
            logger.error(f"读取识别结果文件出错: {e}")
            return None