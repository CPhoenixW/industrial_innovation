import json
import pyaudio
from vosk import Model, KaldiRecognizer

# 加载中文模型（替换为你的模型路径）
model_path = r"./vosk-model-small-cn-0.22"
model = Model(model_path)
rec = KaldiRecognizer(model, 16000)  # 16000Hz 采样率

# 初始化 PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,  # 16-bit 格式
                channels=1,  # 单声道
                rate=16000,  # 采样率
                input=True,  # 输入设备
                frames_per_buffer=8000)  # 缓冲区大小

print("请开始说话（按 Ctrl+C 停止）...")

try:
    while True:
        # 读取音频块
        data = stream.read(4000, exception_on_overflow=False)

        # 流式识别
        if rec.AcceptWaveform(data):
            # 完整句子结果
            result = json.loads(rec.Result())
            text = result.get("text", "")
            if text:
                print("完整输出：", text)  # 例：你好 我是Grok
        else:
            # 部分结果（实时输出）
            partial = json.loads(rec.PartialResult())
            partial_text = partial.get("partial", "")
            if partial_text:
                print("实时输出：", partial_text)  # 例：你好 我是

except KeyboardInterrupt:
    print("\n停止录音")

# 清理资源
stream.stop_stream()
stream.close()
p.terminate()