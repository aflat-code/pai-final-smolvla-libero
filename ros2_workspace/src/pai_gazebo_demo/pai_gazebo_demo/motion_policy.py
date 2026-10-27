import math
import time

import rclpy
from gazebo_msgs.msg import EntityState
from gazebo_msgs.srv import SetEntityState
from rclpy.node import Node


class MotionPolicy(Node):
    """A deterministic waypoint policy using a Gazebo state-control service."""

    def __init__(self) -> None:
        super().__init__("motion_policy")
        self.client = self.create_client(SetEntityState, "/set_entity_state")
        self.timer = self.create_timer(0.05, self.control_step)
        self.started = time.monotonic()
        self.duration_per_side = 8.0
        self.last_side = -1
        self.finished = False
        one_lap = [
            (-0.7, -0.7),
            (-0.7, 0.65),
            (0.65, 0.65),
            (0.65, -0.7),
            (-0.7, -0.7),
        ]
        self.points = one_lap + one_lap[1:]
        self.total_sides = len(self.points) - 1
        self.get_logger().info("Policy ready: two-lap, eight-waypoint trajectory")

    @staticmethod
    def smoothstep(value: float) -> float:
        return value * value * (3.0 - 2.0 * value)

    def control_step(self) -> None:
        if self.finished or not self.client.service_is_ready():
            return
        elapsed = time.monotonic() - self.started
        side = min(int(elapsed / self.duration_per_side), self.total_sides)
        if side >= self.total_sides:
            self.finished = True
            self.get_logger().info("Task complete: eight waypoints reached; robot stopped")
            return
        if side != self.last_side:
            self.last_side = side
            self.get_logger().info(
                f"Moving to waypoint {side + 1}/{self.total_sides}"
            )

        phase = self.smoothstep(
            (elapsed - side * self.duration_per_side) / self.duration_per_side
        )
        x0, y0 = self.points[side]
        x1, y1 = self.points[side + 1]
        yaw = math.atan2(y1 - y0, x1 - x0)

        request = SetEntityState.Request()
        request.state = EntityState()
        request.state.name = "robot"
        request.state.reference_frame = "world"
        request.state.pose.position.x = x0 + (x1 - x0) * phase
        request.state.pose.position.y = y0 + (y1 - y0) * phase
        request.state.pose.position.z = 0.16
        request.state.pose.orientation.z = math.sin(yaw / 2.0)
        request.state.pose.orientation.w = math.cos(yaw / 2.0)
        self.client.call_async(request)


def main() -> None:
    rclpy.init()
    node = MotionPolicy()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
