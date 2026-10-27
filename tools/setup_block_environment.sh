#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
cd /workspace
colcon build --packages-select crane_act_demo

if [ ! -d /home/ubuntu/pai_training/.git ]; then
  git clone https://github.com/matsuolab/pai_training.git /home/ubuntu/pai_training
fi
cd /home/ubuntu/pai_training
git checkout b4d6b5459066a80433475a83567504988875248a
git submodule update --init --recursive
if [ ! -x /home/ubuntu/.pixi/bin/pixi ]; then
  task_tmpdir=$(mktemp -d)
  curl -fL https://github.com/prefix-dev/pixi/releases/download/v0.83.0/pixi-x86_64-unknown-linux-musl.tar.gz -o "$task_tmpdir/pixi.tar.gz"
  mkdir -p /home/ubuntu/.pixi/bin
  tar -xzf "$task_tmpdir/pixi.tar.gz" -C /home/ubuntu/.pixi/bin pixi
fi
/home/ubuntu/.pixi/bin/pixi install --locked

echo 'Ready. Source ROS and /workspace/install/setup.bash before running a trial.'
