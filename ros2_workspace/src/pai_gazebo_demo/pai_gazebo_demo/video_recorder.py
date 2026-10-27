import os

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class VideoRecorder(Node):
    def __init__(self) -> None:
        super().__init__("video_recorder")
        self.output = os.environ.get("PAI_VIDEO_OUTPUT", "/tmp/gazebo_raw.mp4")
        self.bridge = CvBridge()
        self.writer = None
        self.frames = 0
        self.create_subscription(Image, "/demo_camera/demo_camera/image_raw", self.on_image, 10)
        self.get_logger().info(f"Recording Gazebo camera to {self.output}")

    def on_image(self, msg: Image) -> None:
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        if self.writer is None:
            height, width = frame.shape[:2]
            self.writer = cv2.VideoWriter(
                self.output, cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (width, height)
            )
        self.writer.write(frame)
        self.frames += 1

    def close(self) -> None:
        if self.writer is not None:
            self.writer.release()
        self.get_logger().info(f"Saved {self.frames} frames")


def main() -> None:
    rclpy.init()
    node = VideoRecorder()
    try:
        rclpy.spin(node)
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
