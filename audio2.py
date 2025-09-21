import pyaudio
import wenet
import numpy as np

# 加载 WeNet 模型（替换为你的模型路径）
model = wenet.load_model('path/to/paraformer-zh')  # 例如：/home/user/paraformer-zh

# 录音参数
FORMAT = pyaudio.paInt16  # 16-bit 格式
CHANNELS = 1  # 单声道
RATE = 16000  # 采样率 16kHz
CHUNK = 1024  # 每次读取的音频块大小

# 初始化 PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("请开始说话（按 Ctrl+C 停止）...")

try:
    # 初始化流式识别器
    recognizer = model.create_streaming_recognizer()

    while True:
        # 读取音频块
        data = stream.read(CHUNK, exception_on_overflow=False)
        # 转换为 numpy 数组
        audio_chunk = np.frombuffer(data, dtype=np.int16)

        # 流式识别
        recognizer.accept_waveform(audio_chunk, RATE)
        result = recognizer.get_result()

        if result.partial_text:
            print("实时输出：", result.partial_text)  # 例：你好
        if result.final_text:
            print("完整输出：", result.final_text)  # 例：你好 我是Grok

except KeyboardInterrupt:
    print("\n停止录音")

# 清理资源
stream.stop_stream()
stream.close()
p.terminate()