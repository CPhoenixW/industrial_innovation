# 冰淇淋机械臂

本项目是一个基于视觉识别和语音交互的工业机器人抓取系统，主要负责服务器端和树莓派端的软件实现。

## 项目架构

项目分为以下主要部分：
- 服务器端（视觉处理和指令分发）
- 树莓派端（语音交互和数据采集）
- STM32端（机械臂控制）
- 机械结构（CAD设计）

### 服务器端 (`/server`)

服务器端负责处理视觉识别和坐标计算，主要功能包括：
- 图像处理和目标检测（基于YOLO）
- 坐标系转换（基于单应性矩阵）
- 与树莓派的通信管理
- 工件坐标生成

主要组件：
- `app.py`: 主程序入口
- `src/`: 核心功能模块
  - `yolo_detector.py`: YOLO目标检测
  - `homography_processor.py`: 坐标转换处理
  - `audio_processor.py`: 音频处理
  - `text_analyzer.py`: 文本分析
  - `server_controller.py`: 服务器控制器
  - `communication_manager.py`: 通信管理

### 树莓派端 (`/raspberryPi`)

树莓派端负责语音交互和传感器数据采集，主要功能包括：
- 语音识别和命令解析
- 传感器数据采集
- 与服务器的通信

主要组件：
- `main.py`: 主程序入口
- `src/`: 核心功能模块
  - `communication_interface.py`: 通信接口
  - `sensor_controller.py`: 传感器控制
  - `data_processor.py`: 数据处理
  - `main_controller.py`: 主控制器

## 环境要求

### 服务器端
```python
# requirements.txt
opencv-python
numpy
flask
torch
ultralytics  # YOLO目标检测
```

### 树莓派端
```python
# raspberryPi/requirements.txt
vosk  # 语音识别
pyaudio
numpy
requests
```

## 快速开始

1. 服务器端设置
```bash
cd server
pip install -r requirements.txt
python app.py
```

2. 树莓派端设置
```bash
cd raspberryPi
pip install -r requirements.txt
python main.py
```

## 工作流程

1. 树莓派通过语音识别接收用户指令
2. 树莓派将音频和图像数据发送至服务器
3. 服务器进行以下处理：
   - 语音识别和指令解析
   - 图像处理和目标检测
   - 坐标计算和转换
4. 服务器将处理结果返回给树莓派
5. 树莓派将指令转发给STM32控制器

## 注意事项

- 使用前需要进行相机标定和单应性矩阵计算
- 确保服务器和树莓派在同一局域网内
- 图像采集时注意光照条件
- 语音识别需要在较安静的环境下进行

## 维护说明

- 日志文件位于 `server/server.log`
- 模型权重文件存放在 `server/weights/`
- 测试数据集位于 `dataset/`
- 音频文件存放在 `raspberryPi/audio/`

## 相关团队

- 软件开发：phoenixW
- 机械臂控制：三弦乐师
- 机械结构：oort

## 许可证

本项目采用 MIT 许可证。详细信息请查看 [LICENSE](LICENSE) 文件。
