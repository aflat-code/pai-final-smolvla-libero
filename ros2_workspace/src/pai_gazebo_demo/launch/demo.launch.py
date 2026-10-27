from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    world = Path(get_package_share_directory("pai_gazebo_demo")) / "worlds" / "policy_demo.world"
    return LaunchDescription(
        [
            ExecuteProcess(
                cmd=["gzserver", "--verbose", "-s", "libgazebo_ros_init.so", "-s", "libgazebo_ros_factory.so", str(world)],
                output="screen",
            ),
            TimerAction(
                period=4.0,
                actions=[Node(package="pai_gazebo_demo", executable="motion_policy", output="screen")],
            ),
        ]
    )
