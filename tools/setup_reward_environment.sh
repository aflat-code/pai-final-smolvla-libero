#!/usr/bin/env bash
# Run inside the pinned course container; no Torch/Pixi installation is needed.
set -eo pipefail
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
python3 - <<'PY'
import numpy
from ros_gz_interfaces.msg import Contacts
assert numpy.__version__ == '1.24.4', (
    'Exact candidate replay requires NumPy 1.24.4; use the recorded container '
    'environment rather than silently changing this ROS installation.'
)
print('NumPy and ROS contact messages ready.')
PY
cd /workspace
colcon build --packages-select crane_act_demo --symlink-install
echo 'Ready. Source /workspace/install/setup.bash before launch or evaluation.'
