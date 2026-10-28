"""Reward-search world, including an actual block contact sensor."""
from pathlib import Path
import runpy
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    source=Path(get_package_share_directory('crane_act_demo'))/'launch/block_grasp.launch.py'
    return runpy.run_path(str(source))['create_launch']('block_reward.sdf',contacts=True)
