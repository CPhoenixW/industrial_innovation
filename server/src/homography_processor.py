import cv2
import numpy as np
import logging
import os

logger = logging.getLogger("HomographyProcessor")

class HomographyProcessor:
    """处理单应性矩阵计算和坐标映射"""
    def __init__(self, matrix_file="../weights/homography.npy"):
        self.pixel_points = []
        self.world_points = []
        self.H = None
        self.matrix_file = matrix_file
        self.mode = "calibration"  # 默认标定模式

    def load_homography(self):
        """加载单应性矩阵"""
        if os.path.exists(self.matrix_file):
            self.H = np.load(self.matrix_file)
            logger.info(f"已加载单应性矩阵: {self.matrix_file}")
            return True
        else:
            logger.warning(f"没有找到保存的单应性矩阵文件，需要重新标定。{self.matrix_file}")
            return False

    def save_homography(self):
        """保存单应性矩阵"""
        if self.H is not None:
            np.save(self.matrix_file, self.H)
            logger.info(f"单应性矩阵已保存到 {self.matrix_file}")

    def compute_homography(self):
        """计算单应性矩阵"""
        if len(self.pixel_points) >= 4:
            pts_img = np.array(self.pixel_points, dtype=np.float32)
            pts_world = np.array(self.world_points, dtype=np.float32)
            self.H, _ = cv2.findHomography(pts_img, pts_world)
            logger.info("成功计算单应性矩阵")
            return True
        else:
            logger.warning("至少需要4个点来计算单应性矩阵")
            return False

    def pixel_to_world(self, u, v):
        """将像素坐标转换为真实坐标"""
        if self.H is None:
            logger.error("单应性矩阵未初始化")
            return None
        pixel = np.array([u, v, 1]).reshape(3, 1)
        world = np.dot(self.H, pixel)
        world /= world[2, 0]
        return world[0, 0], world[1, 0]

    def interactive_calibration(self, img_path):
        """交互式标定"""
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"无法加载图像: {img_path}")
            return False

        def click_event(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                logger.info(f"标定点像素坐标: ({x}, {y})")
                self.pixel_points.append([x, y])
                try:
                    X = float(input("请输入该点对应的真实 X 坐标: "))
                    Y = float(input("请输入该点对应的真实 Y 坐标: "))
                    self.world_points.append([X, Y])
                    cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
                    cv2.putText(img, f"({X:.1f},{Y:.1f})", (x+5, y-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    cv2.imshow("image", img)
                except ValueError:
                    logger.error("输入的坐标值无效")
                    self.pixel_points.pop()

        cv2.imshow("image", img)
        cv2.setMouseCallback("image", click_event)
        logger.info("进入标定模式：点击图像点并输入真实坐标，至少4个点，按 'q' 结束")
        while True:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()
        return self.compute_homography()

    def interactive_query(self, img_path, count):
        """交互式查询坐标"""
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"无法加载图像: {img_path}")
            return []

        coordinates = []
        def click_event(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(coordinates) < count:
                world_coords = self.pixel_to_world(x, y)
                if world_coords:
                    X, Y = world_coords
                    logger.info(f"像素点 ({x},{y}) → 真实坐标: ({X:.3f}, {Y:.3f})")
                    coordinates.append({"x": X/10-7, "y": Y/10-5.2, "z": 0.0})  # 保持 z=5.0 与原代码一致
                    cv2.circle(img, (x, y), 5, (255, 0, 0), -1)
                    cv2.putText(img, f"({X:.1f},{Y:.1f})", (x+5, y-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                    cv2.imshow("image", img)

        cv2.imshow("image", img)
        cv2.setMouseCallback("image", click_event)
        logger.info(f"进入查询模式：点击 {count} 个点获取真实坐标，按 'q' 退出")
        while len(coordinates) < count:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()
        return coordinates