import os
import json
import logging
from vosk import Model, KaldiRecognizer
from datetime import datetime

logger = logging.getLogger("RaspberryPi")

class DataProcessor:
    """数据处理类，负责语音识别和位置信息处理"""
    
    def __init__(self, model_path="vosk-model-small-cn-0.22", rate=16000):
        self.model_path = model_path
        self.rate = rate
        
        # 加载VOSK模型
        if not os.path.exists(self.model_path):
            logger.error(f"请确保VOSK模型位于 {self.model_path}")
            raise FileNotFoundError(f"VOSK模型不存在: {self.model_path}")
        
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, self.rate)
    
    def recognize_speech(self, audio_data):
        """语音识别"""
        if self.recognizer.AcceptWaveform(audio_data):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "")
            logger.info(f"识别到: {text}")
            return text
        return ""
    
    def process_position_data(self, data):
        """处理位置数据"""
        try:
            # 假设数据格式为 "POS:x,y,z"
            if data and data.startswith("POS:"):
                parts = data[4:].split(',')
                if len(parts) == 3:
                    x, y, z = map(float, parts)
                    return {
                        "x": x,
                        "y": y,
                        "z": z,
                        "timestamp": datetime.now().isoformat()
                    }
            return None
        except Exception as e:
            logger.error(f"处理位置数据失败: {e}")
            return None