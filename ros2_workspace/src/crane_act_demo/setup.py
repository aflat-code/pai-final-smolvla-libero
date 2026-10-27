from glob import glob
from setuptools import setup

package_name = "crane_act_demo"
setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/worlds", glob("worlds/*.sdf")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Kamamoto",
    maintainer_email="aflat-code@users.noreply.github.com",
    description="CRANE+ block pushing with ACT continuation and Gazebo camera recording",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "block_expert = crane_act_demo.block_expert:main",
            "video_recorder = crane_act_demo.video_recorder:main",
        ],
    },
)
