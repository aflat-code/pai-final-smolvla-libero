import os

from ament_index_python.packages import get_package_share_directory
from crane_plus_description.robot_description_loader import RobotDescriptionLoader
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    env = {
        "IGN_GAZEBO_SYSTEM_PLUGIN_PATH": os.environ["LD_LIBRARY_PATH"],
        "IGN_GAZEBO_RESOURCE_PATH": os.path.dirname(
            get_package_share_directory("crane_plus_description")
        ),
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }
    world = os.path.join(
        get_package_share_directory("crane_act_demo"), "worlds", "block_grasp.sdf"
    )
    gazebo = ExecuteProcess(
        cmd=["ign", "gazebo", "-r", "-s", world],
        output="screen",
        additional_env=env,
    )

    description_loader = RobotDescriptionLoader()
    description_loader.use_gazebo = "true"
    description_loader.use_ignition = "true"
    description_loader.gz_control_config_package = "crane_plus_control"
    description_loader.gz_control_config_file_path = "config/crane_plus_controllers.yaml"
    description = description_loader.load()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[{"robot_description": description}],
    )
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-topic", "/robot_description", "-name", "crane_plus", "-z", "1.015",
            "-allow_renaming", "true",
        ],
        output="screen",
    )
    controllers = TimerAction(
        period=3.0,
        actions=[
            ExecuteProcess(cmd=["ros2", "run", "controller_manager", "spawner", "joint_state_broadcaster"], output="screen"),
            ExecuteProcess(cmd=["ros2", "run", "controller_manager", "spawner", "crane_plus_arm_controller"], output="screen"),
            ExecuteProcess(cmd=["ros2", "run", "controller_manager", "spawner", "crane_plus_gripper_controller"], output="screen"),
        ],
    )
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock"],
        output="screen",
    )
    image_bridge = Node(
        package="ros_gz_image",
        executable="image_bridge",
        arguments=["/crane_camera"],
        output="screen",
    )
    pose_bridge = Node(
        package="ros_gz_bridge", executable="parameter_bridge",
        arguments=["/world/default/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V"],
        output="screen",
    )
    return LaunchDescription(
        [
            SetParameter(name="use_sim_time", value=True),
            gazebo,
            robot_state_publisher,
            spawn_robot,
            controllers,
            clock_bridge,
            image_bridge,
            pose_bridge,
        ]
    )
