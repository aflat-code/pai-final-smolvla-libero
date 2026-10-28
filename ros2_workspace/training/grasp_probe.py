"""Submission 2 physical grasp feasibility probe, without attachment plugins."""
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import time

import rclpy

sys.path.insert(0,'/workspace/training')
from block_experiment import Robot,block_pose


def grasp_pose(x,z,yaw=0.,grip=-.52,pitch=math.pi):
    z-=.0714
    e=math.acos((x*x+z*z-.083**2-.0935**2)/(2*.083*.0935))
    q=math.atan2(x,z)-math.atan2(.0935*math.sin(e),.083+.0935*math.cos(e))
    return [yaw,q,q+e-pitch,-e,grip]


def main():
    import os
    root=Path('/workspace/grasp_results');root.mkdir(exist_ok=True)
    rclpy.init();robot=Robot()
    deadline=time.monotonic()+15
    while robot.state is None and time.monotonic()<deadline:rclpy.spin_once(robot,timeout_sec=.1)
    if robot.state is None:raise RuntimeError('No joint states')
    robot.hold([0.,0.,0.,0.,-.52],3.)
    env=os.environ.copy();env['CRANE_VIDEO_OUTPUT']=str(root/'physical_probe.mp4')
    rec=subprocess.Popen(['/workspace/install/crane_act_demo/lib/crane_act_demo/video_recorder'],env=env,
                         stdout=(root/'recorder.log').open('w'),stderr=subprocess.STDOUT)
    robot.hold([0.,0.,0.,0.,-.52],2.)
    points=[(0.,[0.,0.,0.,0.,-.52]),(3.,grasp_pose(.13,.16)),
            (6.,grasp_pose(.13,.14)),(10.,grasp_pose(.13,.14,grip=.58)),
            (13.,grasp_pose(.13,.19,grip=.58,pitch=2.7)),(16.,grasp_pose(.13,.19,yaw=-.70,grip=.58,pitch=2.7)),
            (19.,grasp_pose(.13,.14,yaw=-.70,grip=.58)),(22.,grasp_pose(.13,.14,yaw=-.70)),
            (25.,grasp_pose(.13,.16,yaw=-.70))]
    records=[]
    for (t0,a),(t1,b) in zip(points,points[1:]):
        started=time.monotonic();next_tick=started
        while time.monotonic()-started<t1-t0:
            now=time.monotonic();u=min(1.,(now-started)/(t1-t0));u=u*u*(3.-2.*u)
            if now>=next_tick:
                robot.send([x+(y-x)*u for x,y in zip(a,b)]);next_tick=now+.05
            rclpy.spin_once(robot,timeout_sec=.005)
        robot.hold(b,.5)
        record={'phase_end_s':t1,'block_pose':block_pose(),'joints':robot.state}
        records.append(record);print(json.dumps(record),flush=True)
    rec.send_signal(signal.SIGINT)
    try:rec.wait(timeout=5)
    except subprocess.TimeoutExpired:rec.terminate();rec.wait()
    result={'kind':'scripted_teacher_physical_probe','attachment_plugin':False,'phases':records,
            'lifted_3cm':max(r['block_pose'][2] for r in records)>1.06}
    (root/'physical_probe.json').write_text(json.dumps(result,indent=2))
    robot.destroy_node()
    if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
