import os
import subprocess
import logging
import base64
import hashlib
import hmac
import json
import ssl
import websocket
import time
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import _thread as thread

logger = logging.getLogger("Server")

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


class AudioProcessor:
    """音频处理类，负责音频预处理和语音识别"""

    def __init__(self, appid=APPID, api_key=API_KEY, api_secret=API_SECRET):
        self.appid = appid
        self.api_key = api_key
        self.api_secret = api_secret

    def preprocess_audio(self, input_file, output_file):
        """
        使用ffmpeg将音频转换为单声道16K采样率16bit PCM wav文件
        """
        cmd = [
            "ffmpeg", "-y", "-i", input_file, "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", output_file
        ]
        try:
            subprocess.run(cmd, check=True)
            logger.info(f"音频预处理成功: {output_file}")
            return True
        except Exception as e:
            logger.error(f"音频预处理失败: {e}")
            return False

    def recognize_audio(self, audio_file, result_file):
        """
        使用讯飞API识别音频并将结果保存到文本文件
        """
        processed_audio = audio_file + "_processed.wav"

        # 预处理音频
        if not self.preprocess_audio(audio_file, processed_audio):
            logger.error("音频预处理失败")
            return False

        # 识别结果
        recognition_result = []

        # 回调函数
        def on_message(ws, message):
            try:
                message_json = json.loads(message)
                if "code" in message_json and message_json["code"] != 0:
                    logger.error(f"请求错误: {message_json}")
                    ws.close()
                    return

                if "data" in message_json and "result" in message_json["data"]:
                    ws_list = message_json["data"]["result"]["ws"]
                    result = ""
                    for ws_item in ws_list:
                        for cw_item in ws_item["cw"]:
                            result += cw_item["w"]
                    logger.info(f"识别结果: {result}")
                    recognition_result.append(result)

                if "data" in message_json and "status" in message_json["data"] and message_json["data"]["status"] == 2:
                    ws.close()
            except Exception as e:
                logger.error(f"解析返回数据时出错: {e}")
                logger.error(f"原始消息: {message}")
                ws.close()

        def on_error(ws, error):
            logger.error(f"WebSocket错误: {error}")

        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket连接关闭")
            # 将识别结果写入文件
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(' '.join(recognition_result))
            logger.info(f"识别结果已保存到: {result_file}")

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
        wsParam = Ws_Param(self.appid, self.api_key, self.api_secret, processed_audio)
        websocket.enableTrace(False)
        wsUrl = wsParam.create_url()
        ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
        ws.on_open = on_open
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        return True