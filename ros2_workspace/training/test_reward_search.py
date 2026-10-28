"""Reward and geometric-contract tests; run in the sourced ROS container."""
import math
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import subprocess
import numpy as np
from reward_search import command,score,BOUNDS,INITIAL
from block_experiment import block_pose


class RewardContractTests(unittest.TestCase):
    def test_pose_read_retries_transient_client_abort(self):
        valid=SimpleNamespace(stdout='name: "red_block" position { x: 0.13 y: 0.02 z: 1.03 }')
        with patch('block_experiment.subprocess.run',side_effect=[subprocess.CalledProcessError(-6,['ign']),valid]) as mocked:
            with patch('block_experiment.time.sleep'):
                self.assertEqual(block_pose(),[.13,.02,1.03])
            self.assertEqual(mocked.call_count,2)

    def test_pose_read_failure_does_not_fabricate_position(self):
        with patch('block_experiment.subprocess.run',side_effect=subprocess.TimeoutExpired(['ign'],5)):
            with patch('block_experiment.time.sleep'):
                with self.assertRaises(RuntimeError):block_pose()

    def test_no_motion_not_preferred_to_successful_carry(self):
        stationary=score(math.hypot(.018,.09),0.,INITIAL,1.03)[0]
        carry=score(.01,.003,[.5,.04],1.03)[0]
        self.assertGreater(carry,stationary)

    def test_sliding_has_cost(self):
        self.assertGreater(score(.01,0.,INITIAL,1.03)[0],score(.01,.09,INITIAL,1.03)[0])

    def test_holding_above_goal_not_terminal_success(self):
        terms=score(.01,0.,[.5,.04],1.10)[1]
        self.assertEqual(terms['goal_bonus'],0.)
        self.assertLess(terms['terminal_height_penalty'],0.)

    def test_all_bounded_commands_reachable_and_within_joint_limits(self):
        limits=[(-2.61,2.61),(-1.82,1.78),(-1.84,1.76),(-2.55,2.45),(-.70,.66)]
        for grip in np.linspace(*BOUNDS[0],5):
            for lift in np.linspace(*BOUNDS[1],8):
                for t in np.linspace(0.,25.,101):
                    action=command([grip,lift],t)
                    self.assertTrue(all(math.isfinite(v) and lo<=v<=hi for v,(lo,hi) in zip(action,limits)))


if __name__=='__main__':unittest.main()
