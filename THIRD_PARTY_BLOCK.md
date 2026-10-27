# Block-pushing task: dependencies and attribution

The new task, scene, trajectory generator, data collector, ACT training driver,
evaluation driver, report and video assembly scripts are original project code,
licensed under Apache-2.0. New simulation demonstrations and checkpoints are
also distributed under Apache-2.0. No pretrained neural weights are used.

- CRANE+ V2 robot description / meshes / controllers:
  https://github.com/AI-Robot-Book-Humble/crane_plus
  revision `19c1d6069126cd27488bf1bbefd410704bfc515d`, Apache-2.0.
  The project imports the installed robot description and preserves upstream files.
- LeRobot ACT and LeRobotDataset:
  https://github.com/huggingface/lerobot
  revision `768e36660d1408c71118a2760f831c037fbfa17d`, Apache-2.0.
- Course training environment and practical reference:
  https://github.com/matsuolab/pai_training
  revision `b4d6b5459066a80433475a83567504988875248a`.
  Fetched for its environment and LeRobot submodule; no blanket license claim is
  made over course material. The new training/evaluation drivers are in this repo.
- Lecture 5 practical:
  https://skinny-chord-c58.notion.site/5-ROS-2-2-2-2049a7a1061380fc8928e500eafc57d0
- Docker course image:
  `airobotbook/ros2-desktop-ai-robot-book-humble`
  digest `sha256:b58ec74c019aacd9ce4818fa25fc5a9e0a1f22f8c9cd1f5260994bf15cd9eb63`.
- ROS 2 Humble, Ignition Gazebo 6.16.0, PyTorch 2.7.0, torchvision 0.22.0,
  NumPy 2.2.6, datasets 3.6.0, safetensors 0.5.3, draccus 0.10.0,
  Hugging Face Hub 0.32.3: upstream licenses apply to each dependency.
- OpenCV records the camera topic; FFmpeg encodes the output video.
  DejaVu Sans provides the English video captions.

The blue target, red block, table and camera are native SDF primitives authored
for this project. The new submission has no ball attachment / grasp assist.
During trials, the code only commands joints. `set_pose` is used exclusively
before each trial to reset the block.
