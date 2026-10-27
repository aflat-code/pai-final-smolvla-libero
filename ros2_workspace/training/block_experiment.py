"""Actual Gazebo demonstration collection and ACT comparison trials.

Only reset() may set an object pose, before an episode starts. During each
episode all block movement comes from contact with ROS-controlled robot links.
"""
import argparse
import json
import math
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

sys.path.insert(0, '/workspace/src/crane_act_demo')
from crane_act_demo.block_expert import NAMES, push_pose

DURATION = 13.0
GOAL = [0.29, -0.015]
TEST_STARTS = [[0.20,-0.015], [0.195,-0.02], [0.205,-0.01], [0.198,-0.01], [0.202,-0.02]]


def teacher(t, start):
    dx = start[0]-.20
    yaw = math.atan2(start[1]+.015, start[0])
    def pose(x,z):
        p=push_pose(x,z);p[0]=yaw;return p
    points=[(0.,[0.,0.,0.,0.,-.52]), (3.,pose(.15+dx,.13)),
            (5.,pose(.15+dx,.04)),(11.,pose(.25,.04)),(13.,pose(.25,.10))]
    for (t0,a),(t1,b) in zip(points,points[1:]):
        if t<=t1:
            u=max(0.,(t-t0)/(t1-t0));u=u*u*(3-2*u)
            return [float(x+(y-x)*u) for x,y in zip(a,b)]
    return points[-1][1]


def block_pose():
    result=subprocess.run(['ign','topic','-e','-n','1','-t','/world/default/pose/info'],
                          capture_output=True,text=True,timeout=5,check=True)
    match=re.search(r'name: "red_block".*?position\s*\{\s*x: ([^\s]+)\s*y: ([^\s]+)\s*z: ([^\s]+)',result.stdout,re.S)
    if not match: raise RuntimeError('Block pose unavailable')
    return [float(v) for v in match.groups()]


class Robot(Node):
    def __init__(self):
        super().__init__('block_experiment')
        self.state=None
        self.arm=self.create_publisher(JointTrajectory,'/crane_plus_arm_controller/joint_trajectory',10)
        self.grip=self.create_publisher(JointTrajectory,'/crane_plus_gripper_controller/joint_trajectory',10)
        self.create_subscription(JointState,'/joint_states',self.receive,10)

    def receive(self,msg):
        values=dict(zip(msg.name,msg.position))
        if all(n in values for n in NAMES): self.state=[float(values[n]) for n in NAMES]

    def send(self,values):
        for pub,names,vals in [(self.arm,NAMES[:4],values[:4]),(self.grip,NAMES[4:],values[4:])]:
            msg=JointTrajectory();msg.joint_names=names
            p=JointTrajectoryPoint();p.positions=list(map(float,vals));p.time_from_start.nanosec=100_000_000
            msg.points=[p];pub.publish(msg)

    def hold(self,values,duration):
        end=time.monotonic()+duration
        next_send=0.
        while time.monotonic()<end:
            if time.monotonic()>=next_send:
                self.send(values);next_send=time.monotonic()+.05
            rclpy.spin_once(self,timeout_sec=.01)

    def reset(self,start):
        home=[0.,0.,0.,0.,-.52]
        self.hold(home,3.0)
        deadline=time.monotonic()+12
        while self.state is None or max(abs(a-b) for a,b in zip(self.state,home))>.05:
            if time.monotonic()>deadline:raise RuntimeError(f'Home pose not reached: {self.state}')
            self.hold(home,.5)
        request=f'name: "red_block", position: {{x: {start[0]}, y: {start[1]}, z: 1.036}}, orientation: {{w: 1.0}}'
        p=subprocess.run(['ign','service','-s','/world/default/set_pose','--reqtype','ignition.msgs.Pose',
                          '--reptype','ignition.msgs.Boolean','--timeout','2000','--req',request],capture_output=True,text=True,timeout=4)
        if p.returncode or 'true' not in p.stdout: raise RuntimeError(p.stdout+p.stderr)
        self.hold([0.,0.,0.,0.,-.52],1.0)
        actual=block_pose()
        if math.dist(actual[:2],start)>.006: raise RuntimeError(f'Reset mismatch {actual}, expected {start}')


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['collect','eval'])
    p.add_argument('--root',default='/workspace/block_results');p.add_argument('--model');p.add_argument('--label',default='teacher')
    p.add_argument('--episodes',type=int,default=30);p.add_argument('--start-index',type=int,default=0)
    p.add_argument('--trials',type=int,default=5);p.add_argument('--video',action='store_true')
    args=p.parse_args();root=Path(args.root);root.mkdir(parents=True,exist_ok=True)
    policy=None
    if args.mode=='eval':
        import torch
        from lerobot.common.policies.act.modeling_act import ACTPolicy
        torch.set_num_threads(2)
        policy=ACTPolicy.from_pretrained(args.model).eval().to('cpu')
    rclpy.init();robot=Robot()
    ready=time.monotonic()+15
    while robot.state is None and time.monotonic()<ready: rclpy.spin_once(robot,timeout_sec=.1)
    if robot.state is None: raise RuntimeError('No joint states')
    summaries=[]
    count=args.episodes if args.mode=='collect' else args.trials
    for index in range(args.start_index,args.start_index+count):
        if args.mode=='collect':
            rng=random.Random(5000+index)
            # First ten demonstrations use the nominal position. The next twenty vary it.
            start=[.20,-.015] if index<10 else [.20+rng.uniform(-.008,.008),-.015+rng.uniform(-.008,.008)]
        else: start=TEST_STARTS[index%len(TEST_STARTS)]
        robot.reset(start)
        if policy is not None: policy.reset()
        rec=None
        stem=f'{args.label}_{index:02d}'
        if args.video:
            env=os.environ.copy();env['CRANE_VIDEO_OUTPUT']=str(root/(stem+'.mp4'))
            rec=subprocess.Popen(['/workspace/install/crane_act_demo/lib/crane_act_demo/video_recorder'],env=env,
                                 stdout=(root/(stem+'_recorder.log')).open('w'),stderr=subprocess.STDOUT)
            robot.hold([0.,0.,0.,0.,-.52],.7)
        rows=[];begin=time.monotonic();next_tick=begin
        while time.monotonic()-begin<DURATION:
            rclpy.spin_once(robot,timeout_sec=.002)
            now=time.monotonic()
            if now<next_tick: continue
            elapsed=now-begin;phase=min(elapsed/DURATION,1.)
            env_state=[phase,start[0],start[1]]
            if policy is None: action=teacher(elapsed,start)
            else:
                obs={'observation.state':torch.tensor([robot.state],dtype=torch.float32),
                     'observation.environment_state':torch.tensor([env_state],dtype=torch.float32)}
                with torch.inference_mode(): action=policy.select_action(obs).cpu().numpy().flatten().tolist()
            if not all(math.isfinite(v) for v in action): raise RuntimeError('Non-finite action')
            limits=[(-2.61,2.61),(-1.82,1.78),(-1.84,1.76),(-2.55,2.45),(-.70,.66)]
            action=[max(lo,min(hi,float(v))) for v,(lo,hi) in zip(action,limits)]
            rows.append({'time':elapsed,'state':robot.state[:],'environment_state':env_state,'action':action})
            robot.send(action);next_tick+=.05
        robot.hold(action,.8)
        final=block_pose();error=math.dist(final[:2],GOAL)
        # Center within 3 cm of the target and resting at the table height.
        success=error<=.03 and abs(final[2]-1.035)<.015
        summary={'label':args.label,'trial':index,'start':start,'final':final,'distance_m':error,'success':success,'frames':len(rows),
                 'initial_joint_state':rows[0]['state'],'home_tolerance_rad':.05}
        (root/(stem+'.json')).write_text(json.dumps({'summary':summary,'samples':rows},indent=2))
        if rec:
            rec.send_signal(signal.SIGINT)
            try: rec.wait(timeout=5)
            except subprocess.TimeoutExpired: rec.terminate();rec.wait(timeout=3)
        summaries.append(summary);print(json.dumps(summary),flush=True)
    (root/(args.label+'_summary.json')).write_text(json.dumps(summaries,indent=2))
    robot.destroy_node()
    if rclpy.ok(): rclpy.shutdown()


if __name__=='__main__':main()
