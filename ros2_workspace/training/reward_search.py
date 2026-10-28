"""Continuous CEM policy search in real Gazebo physics; no grasp demonstrations.

The human-provided IK/time skeleton is shared by every policy. The only learned
parameters are finger closure and transit clearance. There is no push/grasp
classifier or hand-coded strategy switch, and no reward for height itself.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

import numpy as np
import rclpy
from ros_gz_interfaces.msg import Contacts
from strategy_experiment import StrategyRobot,HOME,START,GOAL
from block_experiment import block_pose
from grasp_probe import grasp_pose

DURATION=25.
# The arm's geometric reach at x=.13 is z <= .1908 m; stay below it.
BOUNDS=np.array([[-.52,.60],[0.,.050]])
INITIAL=[-.52,0.]
CONTACT_Z=.14
SEED=20261029
REWARD_CONFIG={'goal_sigma_m':.03,'goal_scale':20.,'goal_bonus':8.,
               'slide_cost_per_m':300.,'effort_scale':.5,'terminal_height_cost_per_m':100.}


class RewardRobot(StrategyRobot):
    def __init__(self):
        super().__init__()
        self.contact_received=0
        self.table_contact=False
        self.contact_names=[]
        self.create_subscription(Contacts,'/block_contacts',self.receive_contacts,10)

    def receive_contacts(self,msg):
        self.contact_received+=1
        self.contact_names=[(c.collision1.name,c.collision2.name) for c in msg.contacts]
        self.table_contact=any('table::' in a or 'table::' in b for a,b in self.contact_names)


def command(parameters,t):
    grip,clearance=map(float,parameters)
    # Shared geometric reachability prior, NOT a discrete grasp/push decision.
    # Tilt increases continuously with clearance to keep joint3 in range.
    transit_pitch=math.pi-8.*clearance
    low=lambda yaw=0.,g=-.52:grasp_pose(.13,CONTACT_Z,yaw=yaw,grip=g)
    high=lambda yaw=0.:grasp_pose(.13,CONTACT_Z+clearance,yaw=yaw,grip=grip,pitch=transit_pitch)
    points=[(0.,HOME),(3.,grasp_pose(.13,.16)),(6.,low()),(10.,low(g=grip)),
            (13.,high()),(16.,high(-.70)),(19.,low(-.70,grip)),
            (22.,low(-.70)),(25.,grasp_pose(.13,.16,yaw=-.70))]
    for (t0,a),(t1,b) in zip(points,points[1:]):
        if t<=t1:
            u=np.clip((t-t0)/(t1-t0),0.,1.);u=u*u*(3.-2.*u)
            return [float(x+(y-x)*u) for x,y in zip(a,b)]
    return points[-1][1]


def score(error,slide,parameters,final_z):
    c=REWARD_CONFIG
    # Do-nothing cannot obtain the terminal goal bonus. No lift/grasp bonus.
    goal=c['goal_scale']*math.exp(-.5*(error/c['goal_sigma_m'])**2)
    bonus=c['goal_bonus'] if error<=.03 and abs(final_z-1.03)<.015 else 0.
    grip,clearance=parameters
    effort=c['effort_scale']*(((grip+.52)/1.12)**2+(clearance/.055)**2)
    terms={'goal':goal,'goal_bonus':bonus,'slide_penalty':-c['slide_cost_per_m']*slide,
           'effort_penalty':-effort,'terminal_height_penalty':-c['terminal_height_cost_per_m']*abs(final_z-1.03)}
    return float(sum(terms.values())),terms


def episode(robot,parameters,root,label,video=False):
    parameters=list(map(float,parameters))
    robot.reset(START);robot.hold(HOME,.3)
    if robot.contact_received==0:raise RuntimeError('Missing real contact sensor messages')
    if math.dist(block_pose(),robot.object_position)>.01:raise RuntimeError('Pose bridge ordering mismatch')
    rec=None
    if video:
        env=os.environ.copy();env['CRANE_VIDEO_OUTPUT']=str(root/(label+'.mp4'))
        rec=subprocess.Popen(['/workspace/install/crane_act_demo/lib/crane_act_demo/video_recorder'],env=env,
                             stdout=(root/(label+'_recorder.log')).open('w'),stderr=subprocess.STDOUT)
        robot.hold(HOME,2.)
    rows=[];begin=time.monotonic();next_tick=begin
    previous=robot.object_position[:];previous_contact=robot.table_contact
    slide=0.;air=0.;max_height=previous[2];last_action=HOME
    while time.monotonic()-begin<DURATION:
        rclpy.spin_once(robot,timeout_sec=.002);now=time.monotonic()
        if now<next_tick:continue
        elapsed=now-begin;action=command(parameters,elapsed)
        if not all(math.isfinite(x) for x in action):raise RuntimeError('Invalid action')
        robot.send(action);last_action=action;next_tick=now+.05
        pos=robot.object_position[:];contact=robot.table_contact
        displacement=math.dist(pos[:2],previous[:2])
        # Conservatively count transition intervals as sliding if either end is in contact.
        if contact or previous_contact:slide+=displacement
        else:air+=displacement
        max_height=max(max_height,pos[2])
        rows.append({'time':elapsed,'state':robot.state[:],'action':action,'block':pos,
                     'table_contact':contact,'contact_names':robot.contact_names[:]})
        previous=pos;previous_contact=contact
    robot.hold(last_action,1.)
    final=block_pose()
    if math.dist(final,robot.object_position)>.01:raise RuntimeError('Final pose mismatch')
    error=math.dist(final[:2],GOAL)
    reward,terms=score(error,slide,parameters,final[2])
    summary={'label':label,'parameters':parameters,'reward':reward,'reward_terms':terms,
             'goal_error_m':error,'slide_m':slide,'air_xy_m':air,'max_lift_m':max_height-1.03,
             'goal_reached':error<=.03 and abs(final[2]-1.03)<.015,'lifted_3cm':max_height>1.06,
             'final':final,'samples':len(rows),'contact_sensor_messages':robot.contact_received,
             'duration_wall_s':DURATION,'initial':START,'goal':GOAL}
    (root/(label+'.json')).write_text(json.dumps({'summary':summary,'samples':rows},indent=2))
    if rec:
        rec.send_signal(signal.SIGINT)
        try:rec.wait(timeout=5)
        except subprocess.TimeoutExpired:rec.terminate();rec.wait()
    print(json.dumps(summary),flush=True)
    return summary


def policy_file(root,name,parameters,description):
    data={'kind':'continuous_trajectory_policy','parameters':list(map(float,parameters)),
          'parameter_names':['finger_closure_rad','transit_clearance_m'],
          'fixed_contact_z_m':CONTACT_Z,'duration_wall_s':DURATION,'seed':SEED,
          'reward':REWARD_CONFIG,'human_prior':'fixed IK phase skeleton, block alignment, transfer yaw and continuous reachability tilt',
          'neural_network':False,'demonstrations_used':False,'description':description}
    path=root/(name+'.json');path.write_text(json.dumps(data,indent=2))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def search(robot,root,generations,population,resume=False):
    if (root/'search_history.json').exists() and not resume:raise RuntimeError('Use a fresh output root or --resume')
    rng=np.random.default_rng(SEED);lower,upper=BOUNDS.T
    mean=np.array(INITIAL);std=(upper-lower)/2
    loaded=json.loads((root/'search_history.json').read_text()) if resume else []
    history=[]
    if resume:
        previous=json.loads((root/'reward_contract.json').read_text())
        assert previous['generations']==generations and previous['population']==population
        assert previous['reward']==REWARD_CONFIG and previous['parameters_bounds']==BOUNDS.tolist()
        best=json.loads((root/'initial_baseline.json').read_text())['summary']
    else:
        best=episode(robot,INITIAL,root,'initial_baseline')
        policy_file(root,'before_policy',INITIAL,'Initial open-finger zero-clearance policy; not an ACT checkpoint')
    # An explicit no-motion control tests the reward loophole without moving joints.
    no_motion_error=math.dist(START,GOAL)
    (root/'reward_contract.json').write_text(json.dumps({'reward':REWARD_CONFIG,
       'parameters_bounds':BOUNDS.tolist(),'seed':SEED,'generations':generations,'population':population,
       'selection':'reward only; no height threshold, no grasp label, no manually injected winning policy',
       'no_motion_reference_reward':score(no_motion_error,0.,INITIAL,1.03)[0]},indent=2))
    for gen in range(generations):
        candidates=[]
        n_uniform=population if gen==0 else population//2
        # Latin hypercube: bounded continuous exploration, no discrete behavior library.
        grid=np.column_stack([(rng.permutation(n_uniform)+rng.random(n_uniform))/n_uniform for _ in range(2)])
        candidates.extend(lower+grid*(upper-lower))
        if gen>0:
            candidates.extend(np.clip(rng.normal(mean,std,size=(population-n_uniform-1,2)),lower,upper))
            candidates.append(np.asarray(best['parameters']))
        batch=[]
        for index,params in enumerate(candidates):
            reused=len(history)<len(loaded)
            if reused:
                result=loaded[len(history)]
                assert result['generation']==gen and result['candidate']==index
                assert np.allclose(result['parameters'],params,atol=1e-12,rtol=0.)
            else:
                result=episode(robot,params,root,f'search_g{gen:02d}_{index:02d}')
                result['generation']=gen;result['candidate']=index
            history.append(result);batch.append(result)
            if result['reward']>best['reward']:best=result
            if not reused:(root/'search_history.json').write_text(json.dumps(history,indent=2))
        elites=sorted(batch,key=lambda r:r['reward'],reverse=True)[:max(2,population//4)]
        matrix=np.array([r['parameters'] for r in elites]);mean=matrix.mean(axis=0)
        std=np.maximum(matrix.std(axis=0),(upper-lower)*.08)
        state={'generation_completed':gen,'mean':mean.tolist(),'std':std.tolist(),'best':best}
        (root/'search_state.json').write_text(json.dumps(state,indent=2))
        print('GENERATION_COMPLETE '+json.dumps(state),flush=True)
    digest=policy_file(root,'after_policy',best['parameters'],'Selected by scalar reward from physical CEM trials only')
    (root/'selected.json').write_text(json.dumps({'best_search_result':best,'policy_sha256':digest,
        'episodes':len(history)+1,'selection_frozen_before_evaluation':True},indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['search','eval','probe'])
    p.add_argument('--root',default='/workspace/reward_results');p.add_argument('--generations',type=int,default=3)
    p.add_argument('--population',type=int,default=12);p.add_argument('--episodes',type=int,default=3)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--policy',choices=['before','after'],default='after');args=p.parse_args()
    root=Path(args.root);root.mkdir(parents=True,exist_ok=True)
    rclpy.init();robot=RewardRobot();deadline=time.monotonic()+20
    while (robot.state is None or robot.object_position is None) and time.monotonic()<deadline:
        rclpy.spin_once(robot,timeout_sec=.1)
    if robot.state is None or robot.object_position is None:raise RuntimeError('Simulation unavailable')
    try:
        if args.mode=='search':search(robot,root,args.generations,args.population,args.resume)
        elif args.mode=='probe':episode(robot,INITIAL,root,'probe_initial',video=True)
        else:
            policy=json.loads((root/(args.policy+'_policy.json')).read_text())
            results=[episode(robot,policy['parameters'],root,f'eval_{args.policy}_{i:02d}',video=True) for i in range(args.episodes)]
            (root/(args.policy+'_eval_summary.json')).write_text(json.dumps(results,indent=2))
    finally:
        robot.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
