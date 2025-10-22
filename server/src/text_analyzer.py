import re
import logging

logger = logging.getLogger("Server")


class TextAnalyzer:
    """文本分析类，负责分析识别出的文本，提取数词和名词"""

    def __init__(self):
        # 定义数词映射
        self.number_mapping = {
            '一': 1, '二': 2, '1': 1, '2': 2, '两': 2,
        }

        # 定义工件类型
        self.part_types = ['工件A', '工件B', 'A', 'B', 'a', 'b']

    def extract_info(self, text):
        """
        从文本中提取数词和工件类型
        返回格式: [(数量, 工件类型), ...] 或 错误信息字符串
        """
        if not text:
            logger.warning("文本为空，无法提取信息")
            return "ERROR: 文本为空，无法提取信息"

        logger.info(f"开始分析文本: {text}")

        # 提取数词
        numbers = []
        for word in self.number_mapping:
            if word in text:
                numbers.append(self.number_mapping[word])

        # 如果没有找到数词，返回错误信息
        if not numbers:
            error_msg = "ERROR: 未找到有效的数词"
            logger.warning(error_msg)
            return error_msg

        # 提取工件类型
        parts = []
        for part in self.part_types:
            if part.lower() in text.lower():
                # 统一格式为 "工件A" 或 "工件B"
                if part.lower() in ['a', 'b']:
                    parts.append(f"工件{part.upper()}")
                else:
                    parts.append(part)

        # 如果没有找到工件类型，返回错误信息
        if not parts:
            error_msg = "ERROR: 未找到有效的工件类型"
            logger.warning(error_msg)
            return error_msg

        # 组合结果
        results = []

        # 如果只有一个数词和工件类型
        if len(numbers) == 1:
            results.append((numbers[0], parts[0]))

        # 如果有两个数词但只有一个工件类型，使用相同的工件类型
        elif len(numbers) == 2:
            results.append((numbers[0], parts[0]))
            results.append((numbers[1], parts[0]))


        logger.info(f"提取结果: {results}")
        return results