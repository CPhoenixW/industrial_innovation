from flask import Flask, request, jsonify
import os
import logging
import sys

# 添加当前目录到路径，以便导入src包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.file_manager import FileManager
from src.audio_processor import AudioProcessor
from src.text_analyzer import TextAnalyzer
from src.communication_manager import CommunicationManager
from src.server_controller import ServerController

# 创建Flask应用
app = Flask(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger("Server")

# 获取当前脚本所在目录
CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(CURRENT_DIR, 'uploads')

# 树莓派配置
RASPBERRY_PI_IP = "192.168.43.181"
RASPBERRY_PI_PORT = 5000

# 初始化组件
file_manager = FileManager(UPLOAD_FOLDER)
audio_processor = AudioProcessor()
text_analyzer = TextAnalyzer()
comm_manager = CommunicationManager(RASPBERRY_PI_IP, RASPBERRY_PI_PORT)

# 创建服务器控制器
server_controller = ServerController(
    file_manager=file_manager,
    audio_processor=audio_processor,
    text_analyzer=text_analyzer,
    communication_manager=comm_manager
)

@app.route('/upload', methods=['POST'])
def upload_files():
    """接收并处理树莓派发送的图片和音频文件"""
    try:
        if 'image1' not in request.files or 'image2' not in request.files or 'audio' not in request.files:
            return jsonify({'error': '缺少必要的文件'}), 400
        
        # 获取文件
        image1 = request.files['image1']
        image2 = request.files['image2']
        audio = request.files['audio']
        
        # 处理上传的文件
        result = server_controller.process_upload(image1, image2, audio)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"上传文件时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """简单的首页，用于测试服务器是否正常运行"""
    return "服务器正在运行"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)