"""Submission 2: change a learned pushing strategy into grasp and transfer."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import rclpy
from tf2_msgs.msg import TFMessage

sys.path.insert(0,'/workspace/training')
from block_experiment import Robot,block_pose
from grasp_probe import grasp_pose

HOME=[0.,0.,0.,0.,-.52]
START=[.13,.020]
GOAL=[.112,-.070]


class StrategyRobot(Robot):
    def __init__(self):
        super().__init__()
        self.object_position=None
        self.create_subscription(TFMessage,'/world/default/dynamic_pose/info',self.receive_object,10)

    def receive_object(self,msg):
        # In this fixed world the red block is the first dynamic entity.
        # Verify against the named Ignition entity before and after each trial.
        if msg.transforms:
            t=msg.transforms[0].transform.translation
            self.object_position=[t.x,t.y,t.z]


def waypoints(strategy):
    if strategy=='push':
        return [(0.,HOME),(3.,grasp_pose(.13,.16)),(6.,grasp_pose(.13,.125)),
                (12.,grasp_pose(.13,.125,yaw=-.70)),(15.,grasp_pose(.13,.16,yaw=-.70))]
    return [(0.,HOME),(3.,grasp_pose(.13,.16)),(6.,grasp_pose(.13,.14)),
            (10.,grasp_pose(.13,.14,grip=.58)),(13.,grasp_pose(.13,.19,grip=.58,pitch=2.7)),
            (16.,grasp_pose(.13,.19,yaw=-.70,grip=.58,pitch=2.7)),
            (19.,grasp_pose(.13,.14,yaw=-.70,grip=.58)),(22.,grasp_pose(.13,.14,yaw=-.70)),
            (25.,grasp_pose(.13,.16,yaw=-.70))]


def target(strategy,elapsed):
    points=waypoints(strategy)
    for (t0,a),(t1,b) in zip(points,points[1:]):
        if elapsed<=t1:
            u=max(0.,min(1.,(elapsed-t0)/(t1-t0)));u=u*u*(3.-2.*u)
            return [x+(y-x)*u for x,y in zip(a,b)]
    return points[-1][1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['collect','eval'])
    parser.add_argument('--strategy',choices=['push','grasp'],required=True)
    parser.add_argument('--episodes',type=int,default=8);parser.add_argument('--model')
    parser.add_argument('--root',default='/workspace/strategy_results');parser.add_argument('--video',action='store_true')
    args=parser.parse_args();root=Path(args.root);root.mkdir(parents=True,exist_ok=True)
    policy=None
    if args.mode=='eval':
        import torch
        from lerobot.common.policies.act.modeling_act import ACTPolicy
        torch.set_num_threads(2);policy=ACTPolicy.from_pretrained(args.model).eval()
    duration=waypoints(args.strategy)[-1][0]
    rclpy.init();robot=StrategyRobot();deadline=time.monotonic()+20
    while robot.state is None and time.monotonic()<deadline:rclpy.spin_once(robot,timeout_sec=.1)
    if robot.state is None:raise RuntimeError('No robot state')
    summaries=[]
    label=('teacher_' if args.mode=='collect' else 'policy_')+args.strategy
    for index in range(args.episodes):
        robot.reset(START)
        named_pose=block_pose()
        robot.hold(HOME,.2)
        if robot.object_position is None or math.dist(named_pose,robot.object_position)>.01:
            raise RuntimeError('Dynamic pose bridge ordering mismatch')
        if policy is not None:policy.reset()
        stem=f'{label}_{index:02d}'
        rec=None
        if args.video:
            env=os.environ.copy();env['CRANE_VIDEO_OUTPUT']=str(root/(stem+'.mp4'))
            rec=subprocess.Popen(['/workspace/install/crane_act_demo/lib/crane_act_demo/video_recorder'],env=env,
                                 stdout=(root/(stem+'_recorder.log')).open('w'),stderr=subprocess.STDOUT)
            robot.hold(HOME,2.)
        rows=[];poses=[];begin=time.monotonic();next_tick=begin
        while time.monotonic()-begin<duration:
            rclpy.spin_once(robot,timeout_sec=.002);now=time.monotonic()
            if now<next_tick:continue
            elapsed=now-begin;context=[elapsed/duration,*START]
            if policy is None:action=target(args.strategy,elapsed)
            else:
                obs={'observation.state':torch.tensor([robot.state],dtype=torch.float32),
                     'observation.environment_state':torch.tensor([context],dtype=torch.float32)}
                with torch.inference_mode():action=policy.select_action(obs).cpu().numpy().flatten().tolist()
            if not all(math.isfinite(v) for v in action):raise RuntimeError('Non-finite action')
            limits=[(-2.61,2.61),(-1.82,1.78),(-1.84,1.76),(-2.55,2.45),(-.70,.66)]
            action=[max(lo,min(hi,float(v))) for v,(lo,hi) in zip(action,limits)]
            rows.append({'time':elapsed,'state':robot.state[:],'environment_state':context,'action':action})
            robot.send(action);next_tick=now+.05
            if robot.object_position is not None:
                poses.append({'time':elapsed,'pose':robot.object_position[:]})
        robot.hold(action,1.)
        final=block_pose();max_height=max(p['pose'][2] for p in poses)
        if math.dist(final,robot.object_position)>.01:raise RuntimeError('Final pose bridge mismatch')
        summary={'label':label,'trial':index,'start':START,'goal':GOAL,'final':final,
                 'distance_m':math.dist(final[:2],GOAL),'max_height_m':max_height,
                 'lift_m':max_height-1.03,'lifted_3cm':max_height>1.06,'samples':len(rows),'duration_wall_s':duration,
                 'gripper_max_rad':max(r['state'][4] for r in rows),'initial_joint_state':rows[0]['state']}
        summary['success']=summary['distance_m']<=.03 and (summary['lifted_3cm'] if args.strategy=='grasp' else not summary['lifted_3cm'])
        (root/(stem+'.json')).write_text(json.dumps({'summary':summary,'samples':rows,'poses':poses},indent=2))
        if rec:
            rec.send_signal(signal.SIGINT)
            try:rec.wait(timeout=5)
            except subprocess.TimeoutExpired:rec.terminate();rec.wait()
        summaries.append(summary);print(json.dumps(summary),flush=True)
    (root/(label+'_summary.json')).write_text(json.dumps(summaries,indent=2))
    robot.destroy_node()
    if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
