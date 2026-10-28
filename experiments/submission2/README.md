# Submission 2: from pushing to physical grasp and transfer

提出①は `main` と固定タグ `submission-1-block-push` に保存しています。
このフォルダは別候補②です。提出①の動画・PDF・重みは上書きしません。

## What is being compared

- Before **additional** training: a randomly initialized ACT trained on eight pushing demonstrations for 500 steps.
- After additional training: the **same weights**, continued on eight grasp-and-transfer demonstrations for 2,000 more steps. The optimizer is newly initialized; the old pushing data are not replayed.
- Both policies use the same block, start and goal. This is **behavior replacement with different demonstration strategies**, not a controlled claim of higher success on an unchanged training distribution.
- The input is five measured joint angles plus phase and known initial block coordinates. No images or live block pose enter the policy. Object poses are used only for scoring.
- Time normalization differs: pushing has a 15-second horizon and grasping has a 25-second horizon. Both use 20 Hz target commands and ACT chunks of 16 actions.

The block is 30 mm, 8 g, with SDF friction coefficients 2.0. Start `(0.130, 0.020)` m; goal `(0.112, -0.070)` m. This is not the same scene configuration as submission 1.
Grasping uses actual finger contact and physics. No attachment, suction or pose-moving assist is used during an episode; block pose is reset only before each trial.

## Deliverables

- `video/PAI_final_push_to_grasp_comparison.mp4`: every learned-policy evaluation trial, English lower captions, original playback speed, no static title slides.
- `report/説明資料_提出②_押す動作から把持運搬へ.pdf`: Japanese methods and measured results.
- `models/before` and `models/after`: ACT checkpoints, configs, training settings and SHA-256 hashes.
- `results`: three repeated trials per policy at the known training placement, all summaries, camera metadata and compressed raw demonstrations/evaluation logs. These are **not held-out generalization tests**.

## Measured results

| Policy | Goal within 30 mm | Lift over 30 mm | Mean maximum lift | Mean goal error |
| --- | --- | --- | --- | --- |
| Before: push | 3/3 | 0/3 | 0.006 mm | 7.7 mm |
| After: grasp and transfer | 3/3 | 3/3 | 65.0 mm | 10.9 mm |

The before model keeps the gripper open (maximum measured angle about -0.512 rad).
The after model closes against the block (maximum measured angle about +0.340 rad),
lifts it 63.7 / 65.6 / 65.7 mm, carries it, opens the fingers and leaves it at the goal.
The video is 123.337 seconds long (2 minutes 3 seconds), including all six actual policy trials.
This shows a strategy change, **not an improvement in goal-position error**.

## Reproduce inference in the course Docker environment

The repository-root `compose.block.yaml` mounts this repository at `/submission` and `ros2_workspace` at `/workspace`.
Follow `tools/setup_block_environment.sh` to obtain the fixed course/LeRobot revisions. Do not launch the pushing world and grasping world simultaneously.

Build and launch, in one terminal inside the container:

```bash
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
cd /workspace
colcon build --packages-select crane_act_demo --symlink-install
source /workspace/install/setup.bash
ros2 launch crane_act_demo block_grasp.launch.py
```

In another terminal inside the same container:

```bash
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
source /workspace/install/setup.bash
cd /home/ubuntu/pai_training
.pixi/envs/default/bin/python /workspace/training/strategy_experiment.py eval \
  --strategy push --episodes 3 --model /submission/experiments/submission2/models/before --video
.pixi/envs/default/bin/python /workspace/training/strategy_experiment.py eval \
  --strategy grasp --episodes 3 --model /submission/experiments/submission2/models/after --video
python3 /workspace/training/assemble_strategy_video.py
```

These commands generate new logs and video under `/workspace/strategy_results`, not in the committed reference results.

## Reproduce training

In the launched world, collect eight episodes of each teacher strategy (do not run concurrently):

```bash
python3 /workspace/training/strategy_experiment.py collect --strategy push --episodes 8
python3 /workspace/training/strategy_experiment.py collect --strategy grasp --episodes 8
cd /home/ubuntu/pai_training
.pixi/envs/default/bin/python /workspace/training/train_strategy_act.py --stage push
.pixi/envs/default/bin/python /workspace/training/train_strategy_act.py --stage grasp
```

Use a fresh `strategy_models` directory for a new data collection; existing LeRobot dataset directories are deliberately reused, not overwritten. Saved weights go to `/workspace/strategy_models/{before,after}`.
To train from the exact committed demonstrations, extract the `.json.gz` demonstration files in `results/raw` to `/workspace/strategy_results` first and skip collection.

Model: ACT, 667,939 parameters, hidden 128, four heads, two encoder layers, one decoder layer, VAE disabled, chunk 16 / execution 16. AdamW lr 3e-4, batch 16, weight decay 1e-4, gradient clip 1, dropout 0.1, seed 42, CPU. Shared nonzero normalization scales avoid division by zero on the initially constant gripper command.

## Attribution

See the repository-root `THIRD_PARTY_BLOCK.md` and `LICENSE` for upstream URLs, fixed revisions and third-party terms. Original new code, simulation demonstrations and newly trained weights are Apache-2.0. No external pretrained neural weights are used.
YouTube upload and OmniCampus submission are performed by the user, not by these scripts.
