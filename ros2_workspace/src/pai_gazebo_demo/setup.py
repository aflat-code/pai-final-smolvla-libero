from glob import glob
from setuptools import setup

package_name = "pai_gazebo_demo"

setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/worlds", glob("worlds/*.world")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Kamamoto",
    maintainer_email="aflat-code@users.noreply.github.com",
    description="Reliable ROS 2 and Gazebo policy demonstration",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "motion_policy = pai_gazebo_demo.motion_policy:main",
            "video_recorder = pai_gazebo_demo.video_recorder:main",
        ],
    },
)
