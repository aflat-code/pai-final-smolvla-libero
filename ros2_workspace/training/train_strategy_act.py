"""Fit an ACT pushing policy, then continue its weights on grasp demonstrations."""
import argparse
import json
from pathlib import Path
import time

from train_block_act import make_dataset,train,torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['push','grasp'],required=True)
    args=p.parse_args();torch.set_num_threads(2)
    root=Path('/workspace/strategy_results');out=Path('/workspace/strategy_models');out.mkdir(exist_ok=True)
    paths=sorted(root.glob(f'teacher_{args.stage}_[0-9][0-9].json'))
    if len(paths)!=8:raise RuntimeError(f'Expected eight {args.stage} demonstrations, found {len(paths)}')
    dataset=make_dataset(paths,out/('dataset_'+args.stage),'strategy_'+args.stage,
                         task_name='push_red_block' if args.stage=='push' else 'grasp_and_transfer_red_block')
    if args.stage=='push':
        info=train(dataset,out/'before',500,context_center=(.13,.02),std_overrides={0:.35,4:.5})
    else:
        info=train(dataset,out/'after',2000,resume=out/'before',context_center=(.13,.02),std_overrides={0:.35,4:.5})
    info['training_strategy']=args.stage
    (out/('before' if args.stage=='push' else 'after')/'training_info.json').write_text(json.dumps(info,indent=2))


if __name__=='__main__':main()
