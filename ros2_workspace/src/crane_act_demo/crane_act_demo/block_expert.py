"""Contact-based block pushing demonstration; no object pose commands."""
import math
import time

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

NAMES = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint4', 'crane_plus_joint3', 'crane_plus_joint_hand']


def push_pose(tip_x, tip_z=0.040):
    x, z = tip_x - 0.085, tip_z - 0.0714
    elbow = math.acos(max(-1., min(1., (x*x+z*z-0.083**2-0.0935**2)/(2*0.083*0.0935))))
    shoulder = math.atan2(x, z) - math.atan2(0.0935*math.sin(elbow), 0.083+0.0935*math.cos(elbow))
    return [0., shoulder, shoulder+elbow-math.pi/2, -elbow, 0.58]


def target_at(elapsed):
    points = [
        (0., [0., 0., 0., 0., -0.52]),
        (3., push_pose(0.15, 0.13)),
        (5., push_pose(0.15)),
        (11., push_pose(0.25)),
        (13., push_pose(0.25, 0.10)),
    ]
    for (t0, a), (t1, b) in zip(points, points[1:]):
        if elapsed <= t1:
            t = max(0., (elapsed-t0)/(t1-t0))
            t = t*t*(3.-2.*t)
            return [x+(y-x)*t for x,y in zip(a,b)]
    return points[-1][1]


class BlockExpert(Node):
    def __init__(self):
        super().__init__('block_push_expert')
        self.arm = self.create_publisher(JointTrajectory, '/crane_plus_arm_controller/joint_trajectory', 10)
        self.grip = self.create_publisher(JointTrajectory, '/crane_plus_gripper_controller/joint_trajectory', 10)
        self.started = time.monotonic()
        self.create_timer(.05, self.step)

    def step(self):
        values = target_at(time.monotonic()-self.started)
        for pub, names, vals in [(self.arm,NAMES[:4],values[:4]),(self.grip,NAMES[4:],values[4:])]:
            msg=JointTrajectory();msg.joint_names=names
            point=JointTrajectoryPoint();point.positions=vals;point.time_from_start.nanosec=100_000_000
            msg.points=[point];pub.publish(msg)


def main():
    rclpy.init();node=BlockExpert()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
