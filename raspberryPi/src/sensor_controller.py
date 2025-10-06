import os
import time
import cv2
import pyaudio
import wave
import logging
from datetime import datetime

logger = logging.getLogger("RaspberryPi")

class SensorController:
    """传感器控制类，负责摄像头和麦克风的操作"""
    
    def __init__(self, temp_folder="temp"):
        self.temp_folder = temp_folder
        # 确保临时文件夹存在
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        # 初始化PyAudio
        self.audio = pyaudio.PyAudio()
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 4096
        self.record_seconds = 3
    
    def capture_images(self):
        """使用USB摄像头拍摄两张照片"""
        logger.info("正在拍摄照片...")
        cap = cv2.VideoCapture(0)  # 0表示第一个摄像头设备
        
        if not cap.isOpened():
            logger.error("无法打开摄像头")
            return None, None
        
        # 等待摄像头初始化
        time.sleep(1)
        
        # 拍摄第一张照片
        ret1, frame1 = cap.read()
        time.sleep(0.5)  # 间隔0.5秒
        
        # 拍摄第二张照片
        ret2, frame2 = cap.read()
        
        # 释放摄像头
        cap.release()
        
        if not ret1 or not ret2:
            logger.error("拍照失败")
            return None, None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img1_path = os.path.join(self.temp_folder, f"image1_{timestamp}.jpg")
        img2_path = os.path.join(self.temp_folder, f"image2_{timestamp}.jpg")
        
        cv2.imwrite(img1_path, frame1)
        cv2.imwrite(img2_path, frame2)
        
        logger.info(f"照片已保存: {img1_path}, {img2_path}")
        return img1_path, img2_path
    
    def record_audio(self):
        """录制音频"""
        logger.info(f"正在录制 {self.record_seconds} 秒音频...")
        
        stream = self.audio.open(format=self.format,
                            channels=self.channels,
                            rate=self.rate,
                            input=True,
                            frames_per_buffer=self.chunk)
        
        frames = []
        for i in range(0, int(self.rate / self.chunk * self.record_seconds)):
            data = stream.read(self.chunk)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = os.path.join(self.temp_folder, f"audio_{timestamp}.wav")
        
        # 保存录音
        wf = wave.open(audio_path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        logger.info(f"音频已保存: {audio_path}")
        return audio_path
    
    def get_audio_stream(self):
        """获取音频流用于语音识别"""
        return self.audio.open(format=self.format,
                          channels=self.channels,
                          rate=self.rate,
                          input=True,
                          frames_per_buffer=self.chunk)
    
    def cleanup(self):
        """清理资源"""
        self.audio.terminate()