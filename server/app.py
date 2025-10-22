from flask import Flask, request, jsonify
import os
import sys
import subprocess
from datetime import datetime
import logging
import time
import base64
import hashlib
import hmac
import json
import ssl
import websocket
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import _thread as thread
import requests  # 添加requests库用于HTTP请求

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)

# 配置保存文件的目录 - 使用绝对路径
# 获取当前脚本所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(CURRENT_DIR, 'uploads')

# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 树莓派配置 - 请根据实际情况修改IP地址和端口
RASPBERRY_PI_IP = "192.168.43.132"  # 修改为您的树莓派IP地址
RASPBERRY_PI_PORT = 8080  # 修改为树莓派监听的端口

# 讯飞开放平台配置
APPID = "1afbccad"
API_KEY = "e22e826af89befd6431fb57c010b50c2"
API_SECRET = "N2UyMTcxMDUxNzI5MDczY2Q0YTYxODgy"

STATUS_FIRST_FRAME = 0
STATUS_CONTINUE_FRAME = 1
STATUS_LAST_FRAME = 2

class Ws_Param(object):
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile
        self.iat_params = {
            "domain": "iat",
            "language": "zh_cn",
            "accent": "mandarin",
            "dwa": "wpgs",
            "result": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "plain"
            }
        }

    def create_url(self):
        url = 'wss://iat-api.xfyun.cn/v2/iat'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        signature_origin = "host: " + "iat-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        v = {
            "authorization": authorization,
            "date": date,
            "host": "iat-api.xfyun.cn"
        }
        url = url + '?' + urlencode(v)
        return url

def preprocess_audio(input_file, output_file):
    """
    使用ffmpeg将音频转换为单声道16K采样率16bit PCM wav文件
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_file, "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", output_file
    ]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        app.logger.error(f"音频预处理失败: {e}")
        return False
    return True

def recognize_audio(audio_file, result_file):
    """
    使用讯飞API识别音频并将结果保存到文本文件
    """
    processed_audio = audio_file + "_processed.wav"
    
    # 预处理音频
    if not preprocess_audio(audio_file, processed_audio):
        app.logger.error("音频预处理失败")
        return False
    
    # 识别结果
    recognition_result = []
    
    # 回调函数
    def on_message(ws, message):
        try:
            message_json = json.loads(message)
            if "code" in message_json and message_json["code"] != 0:
                app.logger.error(f"请求错误: {message_json}")
                ws.close()
                return
            
            if "data" in message_json and "result" in message_json["data"]:
                ws_list = message_json["data"]["result"]["ws"]
                result = ""
                for ws_item in ws_list:
                    for cw_item in ws_item["cw"]:
                        result += cw_item["w"]
                app.logger.info(f"识别结果: {result}")
                recognition_result.append(result)
            
            if "data" in message_json and "status" in message_json["data"] and message_json["data"]["status"] == 2:
                ws.close()
        except Exception as e:
            app.logger.error(f"解析返回数据时出错: {e}")
            app.logger.error(f"原始消息: {message}")
            ws.close()
    
    def on_error(ws, error):
        app.logger.error(f"WebSocket错误: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        app.logger.info("WebSocket连接关闭")
        # 将识别结果写入文件
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(' '.join(recognition_result))
        app.logger.info(f"识别结果已保存到: {result_file}")
    
    def on_open(ws):
        def run(*args):
            frameSize = 1280
            intervel = 0.04
            status = STATUS_FIRST_FRAME
            with open(wsParam.AudioFile, "rb") as fp:
                while True:
                    buf = fp.read(frameSize)
                    audio = str(base64.b64encode(buf), 'utf-8')
                    if not buf:
                        status = STATUS_LAST_FRAME
                    if status == STATUS_FIRST_FRAME:
                        d = {
                            "common": {
                                "app_id": wsParam.APPID
                            },
                            "business": {
                                "language": "zh_cn",
                                "domain": "iat",
                                "accent": "mandarin",
                                "dwa": "wpgs"
                            },
                            "data": {
                                "status": 0,
                                "format": "audio/L16;rate=16000",
                                "encoding": "raw",
                                "audio": audio
                            }
                        }
                        ws.send(json.dumps(d))
                        status = STATUS_CONTINUE_FRAME
                    elif status == STATUS_CONTINUE_FRAME:
                        d = {
                            "data": {
                                "status": 1,
                                "audio": audio
                            }
                        }
                        ws.send(json.dumps(d))
                    elif status == STATUS_LAST_FRAME:
                        d = {
                            "data": {
                                "status": 2,
                                "audio": audio
                            }
                        }
                        ws.send(json.dumps(d))
                        break
                    time.sleep(intervel)
        thread.start_new_thread(run, ())
    
    # 创建WebSocket连接
    wsParam = Ws_Param(APPID, API_KEY, API_SECRET, processed_audio)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    
    return True

def send_message_to_raspberry_pi(message):
    """向树莓派发送消息"""
    try:
        url = f"http://{RASPBERRY_PI_IP}:{RASPBERRY_PI_PORT}/message"
        data = {"message": message}
        response = requests.post(url, json=data, timeout=5)
        
        if response.status_code == 200:
            app.logger.info(f"成功向树莓派发送消息: {message}")
            return True
        else:
            app.logger.error(f"向树莓派发送消息失败，状态码: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        app.logger.error(f"向树莓派发送消息时出错: {str(e)}")
        return False

@app.route('/upload', methods=['POST'])
def upload_files():
    """接收并保存树莓派发送的图片和音频文件"""
    try:
        if 'image1' not in request.files or 'image2' not in request.files or 'audio' not in request.files:
            return jsonify({'error': '缺少必要的文件'}), 400
        
        # 获取当前时间作为文件夹名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = os.path.join(UPLOAD_FOLDER, timestamp)
        
        # 创建保存文件的目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # 保存第一张图片
        image1 = request.files['image1']
        image1_path = os.path.join(save_dir, f"image1_{timestamp}.jpg")
        image1.save(image1_path)
        
        # 保存第二张图片
        image2 = request.files['image2']
        image2_path = os.path.join(save_dir, f"image2_{timestamp}.jpg")
        image2.save(image2_path)
        
        # 保存音频文件
        audio = request.files['audio']
        audio_path = os.path.join(save_dir, f"audio_{timestamp}.wav")
        audio.save(audio_path)
        
        app.logger.info(f"文件已保存到 {save_dir}")
        
        # 向树莓派发送消息
        send_message_to_raspberry_pi("{1,2}")
        
        # 使用讯飞API识别音频并保存结果
        result_path = os.path.join(save_dir, f"recognition_{timestamp}.txt")
        
        # 在新线程中处理语音识别，避免阻塞响应
        def process_audio():
            recognize_audio(audio_path, result_path)
        
        thread.start_new_thread(process_audio, ())
        
        return jsonify({
            'success': True,
            'message': '文件上传成功，正在进行语音识别，已通知树莓派',
            'files': {
                'image1': image1_path,
                'image2': image2_path,
                'audio': audio_path,
                'recognition': result_path
            }
        })
    
    except Exception as e:
        app.logger.error(f"上传文件时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """简单的首页，用于测试服务器是否正常运行"""
    return "服务器正在运行"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)