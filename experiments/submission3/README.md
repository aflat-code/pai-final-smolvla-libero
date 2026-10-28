# Submission 3: reward-driven choice of transport behavior

This is separate from submissions 1 and 2. They remain at `main` / tag
`submission-1-block-push` and branch `experiment2-grasp-transfer` respectively.

## Scientific question

Can a shared continuous controller find a finger-closing, off-table transport
behavior when the objective rewards reaching the goal and penalizes sliding?

This experiment uses **direct policy search with the cross-entropy method (CEM)**,
not ACT imitation learning, PPO, or a neural policy trained from scratch.
No grasp demonstrations or submission-2 model weights are loaded.
The controller has two continuous learned parameters:

1. Finger closure in `[-0.52, +0.60]` radians.
2. Transit clearance in `[0, 0.050]` meters.

Clearance is the commanded IK wrist-height increase relative to the contact
pose, not the measured lift of the block; the latter is measured separately.

Every candidate uses the same human-defined IK skeleton: approach, lower, change
finger angle, change clearance, rotate toward the goal, lower, open, withdraw.
Contact height (0.14 m relative to the robot base), alignment, phase timings,
target yaw and a continuous reachability tilt are fixed geometric priors inherited
from the known robot setup. With zero clearance and open fingers, this is pushing.
There is **no discrete push/grasp switch**, no strategy classifier, and no
manually inserted successful grasp candidate.
This demonstrates optimization **within a deliberately constrained policy class**,
not discovery of grasping from unrestricted joint-level actions.

## Reward (fixed before the main search)

For terminal XY goal error `e`, contact sliding distance `s`, terminal block center
height `z`, finger parameter `g`, and clearance `h`:

```text
R = 20 exp(-0.5 (e / 0.03)^2)
    + 8 * I(e <= 0.03 and abs(z - 1.03) < 0.015)
    - 300 s
    - 0.5 [((g + 0.52) / 1.12)^2 + (h / 0.055)^2]
    - 100 abs(z - 1.03)
```

There is no positive reward for lifting, closing the fingers or a grasp label.
The small parameter-effort cost actually discourages unnecessary closing and
clearance. No-motion at the given start receives no terminal success bonus.
Holding the block more than 15 mm away from its resting center height also
receives no terminal success bonus. The terminal criterion is a position/height
band, not a velocity-based test of complete rest. Every candidate's shared
skeleton opens the fingers before finishing.

`s` is the sum of XY block displacement during contact with the actual table
collision. Gazebo's contact sensor is bridged to ROS; it is **not inferred only
from block height**. Transition intervals are conservatively counted as contact
if either endpoint has table contact. State and contact are sampled near 20 Hz,
so distances are sampled estimates, not exact continuous-time contact integrals.
The terminal pose is measured after one additional second of settling.

## Search and evaluation protocol

- Initial comparison policy: explicitly initialized open fingers, zero clearance;
  not an untrained neural network and not a separately reward-trained baseline.
- Main search: seed 20261029, three generations, 12 candidates each, three elite
  candidates, 37 physical episodes including the initial baseline.
- First generation: Latin-hypercube continuous exploration over both bounds.
- Later generations: six uniform exploratory candidates, five Gaussian samples
  near elites, and the current best candidate. Minimum standard deviation is 8%
  of the parameter range. Elite mean/std update after each generation.
- Winner: highest scalar reward in the search, with no success/lift filter.
- The winning parameters are frozen **before** three new evaluation trials.
- Before and after use the same world, start, goal, IK template and 25-second
  control horizon. Camera recordings are made only for evaluation.
- The initial placement is known and fixed. Repetitions test physics repeatability,
  not held-out placement generalization or statistical causality.
- A small workspace-validation pilot is retained separately. Before the main
  search, maximum clearance was reduced from 55 to 50 mm to stay within geometric
  reach. No reward weights were tuned to pilot success or failure.
- A transient Ignition pose-client abort interrupted the main search after 21
  completed candidates. Read-only pose retries were added, and `--resume`
  reconstructed the exact same candidate sequence and retained every completed
  result. No reward, bound, random seed or candidate ranking was changed.

Policy JSONs contain the two learned parameters and complete reward configuration;
there is no neural checkpoint. Raw trajectories, contact names, all sampled
parameters, reward components and generation history are included for audit.

## Measured results (three frozen-policy trials each)

| Metric | Initial open-finger policy | Reward-selected policy |
| --- | --- | --- |
| Goal reached | 3/3 | 3/3 |
| Mean return | 0.83 | 16.62 |
| Mean sliding distance | 89.7 mm | 32.9 mm |
| Mean XY movement without table contact | 0.0 mm | 96.5 mm |
| Mean maximum measured block lift | 0.46 mm | 12.68 mm |
| Mean goal error | 4.7 mm | 9.5 mm |

The selected finger angle is +0.52345 rad and commanded wrist clearance is
17.692 mm. The block's actual lift is smaller and varies between trials.
The change reduces sampled sliding distance by about 63%, **not to zero**, and
does not improve terminal position error. All three after trials reached the goal.

The audit verified 43 physical episodes (37 main-search episodes plus six frozen
evaluation trials), exact seeded proposals, reward-only selection, unchanged
policy hash and the raw actions/contact-distance/reward calculations.
The main search was resumed after a communication failure without discarding
completed samples. The separate workspace-check pilot is not counted as main training.

An **offline diagnostic**, not an independent re-training experiment, re-scores
the same 37 observed candidates without the sliding term. Its winner is a pushing
policy (0.28 mm maximum lift, 90.4 mm sliding). With the sliding cost, the winning
search sample has 14.2 mm lift and 30.6 mm sliding. This supports the reward-ranking
interpretation but does not establish a causal effect across independent runs.

The video contains all six evaluation trials with lower English captions, at
nominal original simulation playback (15 camera frames per simulation second).
The camera topic timing was checked separately using its simulation timestamps.
Control phases run on wall-clock time; Gazebo's real-time factor is below one
and load-dependent. Thus 25 seconds of controller wall time need not occupy
25 seconds of simulation video. No deliberate speed-up or static title padding is used.

## Reproduce

This run uses the container's system Python 3.10.12 and NumPy 1.24.4, not the
separate PyTorch/Pixi ACT training environment used for submission 2.
The captured platform details are in `results/environment.json`.
Use the course Docker image and fixed dependency revisions in the root
`compose.block.yaml` and `THIRD_PARTY_BLOCK.md`.
`tools/setup_reward_environment.sh` checks the system environment and builds only
the ROS package; it does not install Torch/Pixi or download ACT weights.
Do not run multiple Gazebo worlds simultaneously.

Inside the container, launch the contact-enabled world:

```bash
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
cd /workspace
colcon build --packages-select crane_act_demo --symlink-install
source /workspace/install/setup.bash
ros2 launch crane_act_demo block_reward.launch.py
```

In a second, similarly sourced container terminal:

```bash
python3 /workspace/training/test_reward_search.py
python3 -u /workspace/training/reward_search.py search --generations 3 --population 12
python3 -u /workspace/training/reward_search.py eval --policy before --episodes 3
python3 -u /workspace/training/reward_search.py eval --policy after --episodes 3
python3 /workspace/training/audit_reward_run.py
```

The default output is `/workspace/reward_results`. Use a fresh `--root` for a new
search; existing search history is never silently overwritten. To reproduce
evaluation of the committed policies, copy the two policy JSONs from this folder's
`policies` directory to that output root first and skip search.
The audit command requires the full search/evaluation records; when reproducing
inference alone, do not run it against a directory containing only policy JSONs.
For an interrupted main search only, pass `--resume` with the original root,
generation count and population. The audit reconstructs all proposals from the
seed and verifies reward-only selection, frozen policy hashes and raw actions.
For bitwise replay of the proposal generator, use NumPy 1.24.4; the stored candidate
list remains the reference if an upstream random-number implementation changes.

## Method references and attribution

- Szita and Lorincz, *The Cross Entropy Method for Fast Policy Search*, ICML 2003:
  https://cdn.aaai.org/ICML/2003/ICML03-068.pdf
- Duan et al., *Benchmarking Deep Reinforcement Learning for Continuous Control*,
  ICML 2016 (describes CEM exploration in policy-parameter space):
  https://proceedings.mlr.press/v48/duan16.pdf

Our CEM implementation is original NumPy code; the cited papers are methodological
references, not copied software. Original code, simulation logs and parameterized
policies are Apache-2.0. Upstream robot/ROS/Gazebo/Docker dependencies retain their
own licenses. There is no simulated attachment, pose-moving assist during trials,
or imported pretrained model. The block is 3 cm / 8 g with friction 2.0, identical
to submission 2 apart from adding a measurement-only contact sensor.
