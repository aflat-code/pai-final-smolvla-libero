"""Build course-compatible LeRobot datasets and compare ACT continuation."""
import argparse
import hashlib
import json
from pathlib import Path
import random

import numpy as np
import torch
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.datasets.utils import dataset_to_policy_features
from lerobot.common.policies.act.configuration_act import ACTConfig
from lerobot.common.policies.act.modeling_act import ACTPolicy
from lerobot.configs.types import FeatureType

FEATURES = {
    'observation.state': {'dtype':'float32','shape':(5,), 'names':['joint1','joint2','joint4','joint3','gripper']},
    'observation.environment_state': {'dtype':'float32','shape':(3,), 'names':['phase','initial_block_x','initial_block_y']},
    'action': {'dtype':'float32','shape':(5,), 'names':['joint1','joint2','joint4','joint3','gripper']},
}


def make_dataset(paths, root, repo_id):
    if root.exists():
        return LeRobotDataset(repo_id=repo_id,root=root,delta_timestamps={
            'observation.state':[0.], 'observation.environment_state':[0.], 'action':[i/20 for i in range(16)]})
    dataset=LeRobotDataset.create(repo_id=repo_id,root=root,fps=20,robot_type='crane_plus',features=FEATURES,use_videos=False)
    for path in paths:
        item=json.loads(path.read_text())
        for row in item['samples']:
            dataset.add_frame({'observation.state':np.asarray(row['state'],dtype=np.float32),
                               'observation.environment_state':np.asarray(row['environment_state'],dtype=np.float32),
                               'action':np.asarray(row['action'],dtype=np.float32),'task':'push_red_block_into_blue_goal'})
        dataset.save_episode()
    return LeRobotDataset(repo_id=repo_id,root=root,delta_timestamps={
        'observation.state':[0.], 'observation.environment_state':[0.], 'action':[i/20 for i in range(16)]})


def train(dataset, output, steps, resume=None):
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    features=dataset_to_policy_features(FEATURES)
    if resume:
        policy=ACTPolicy.from_pretrained(str(resume))
    else:
        # Initial x/y are constant in the baseline set. Use an explicit shared
        # scale so that varied continuation inputs never divide by zero std.
        dataset.meta.stats['observation.environment_state']['mean']=torch.tensor([.5,.20,-.015])
        dataset.meta.stats['observation.environment_state']['std']=torch.tensor([.3,.02,.02])
        # Base rotation is also constant in nominal demonstrations. Give it a
        # shared nonzero scale for both measured state and target action.
        for key in ['observation.state','action']:
            dataset.meta.stats[key]['std'][0]=.05
        policy=ACTPolicy(ACTConfig(
            input_features={k:v for k,v in features.items() if v.type is not FeatureType.ACTION},
            output_features={k:v for k,v in features.items() if v.type is FeatureType.ACTION},
            chunk_size=16,n_action_steps=16,dim_model=128,n_heads=4,dim_feedforward=512,
            n_encoder_layers=2,n_decoder_layers=1,n_vae_encoder_layers=2,latent_dim=16,
            device='cpu',use_vae=False,kl_weight=1.0,dropout=.1,
        ),dataset_stats=dataset.meta.stats)
    policy.train()
    optimizer=torch.optim.AdamW(policy.parameters(),lr=3e-4,weight_decay=1e-4)
    loader=torch.utils.data.DataLoader(dataset,batch_size=16,shuffle=True,num_workers=0,drop_last=True)
    logs=[];step=0
    while step<steps:
        for batch in loader:
            for key in ['observation.state','observation.environment_state']:batch[key]=batch[key][:,-1,:]
            loss,_=policy.forward(batch);loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(),1.)
            optimizer.step();optimizer.zero_grad(set_to_none=True)
            if step%50==0:
                logs.append({'step':step,'loss':loss.item()})
                print(f'{output.name} step {step}/{steps} loss {loss.item():.5f}',flush=True)
            step+=1
            if step>=steps:break
    output.mkdir(parents=True,exist_ok=True);policy.save_pretrained(output)
    info={'algorithm':'ACT','seed':42,'steps_this_stage':steps,'resume_from':str(resume) if resume else None,
          'episodes':dataset.num_episodes,'frames':len(dataset),'chunk_size':16,'n_action_steps':16,
          'batch_size':16,'learning_rate':3e-4,'weight_decay':1e-4,'kl_weight':1.,'device':'cpu',
          'num_parameters':sum(p.numel() for p in policy.parameters()),'logs':logs,'final_loss':loss.item(),
          'use_vae':policy.config.use_vae,'initial_rotation_std':.05,
          'environment_mean':[.5,.20,-.015],'environment_std':[.3,.02,.02]}
    info['checkpoint_sha256']=hashlib.sha256((output/'model.safetensors').read_bytes()).hexdigest()
    (output/'training_info.json').write_text(json.dumps(info,indent=2))
    return info


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',default='/workspace/block_results')
    parser.add_argument('--out',default='/workspace/block_models');parser.add_argument('--base-steps',type=int,default=200)
    parser.add_argument('--extra-steps',type=int,default=1200);args=parser.parse_args()
    torch.set_num_threads(2);torch.manual_seed(42);np.random.seed(42);random.seed(42)
    paths=sorted(Path(args.data).glob('teacher_[0-9][0-9].json'))
    if len(paths)!=30:raise RuntimeError(f'Expected 30 episodes, found {len(paths)}')
    failed=[p.name for p in paths if not json.loads(p.read_text())['summary']['success']]
    print('Teacher failures:',failed,flush=True)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    base=make_dataset(paths[:10],out/'dataset_base','block_push_base')
    b=train(base,out/'before',args.base_steps)
    extended=make_dataset(paths,out/'dataset_extended','block_push_extended')
    a=train(extended,out/'after',args.extra_steps,resume=out/'before')
    (out/'comparison_training.json').write_text(json.dumps({'before':b,'after':a,'teacher_failures':failed},indent=2))


if __name__=='__main__':main()
