"""Freeze reference logs/checkpoints without modifying submission 1 artifacts."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics

BASE=Path(__file__).resolve().parents[1]
SOURCE=BASE/'ros2_workspace'
DEST=BASE/'experiments/submission2'


def main():
    raw=SOURCE/'strategy_results';results=DEST/'results';results.mkdir(parents=True,exist_ok=True)
    compressed=results/'raw';compressed.mkdir(exist_ok=True)
    for name in ['strategy_train_push.log','strategy_train_grasp.log',
                 'strategy_collect_push.log','strategy_collect_grasp.log',
                 'strategy_eval_push.log','strategy_eval_grasp.log']:
        shutil.copy2(SOURCE/name,results/name)
    for path in sorted(raw.glob('*.json')):
        if path.name.endswith('_summary.json'):
            shutil.copy2(path,results/path.name)
        else:
            # mtime=0 makes the compressed audit record reproducible.
            (compressed/(path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    for stage in ['before','after']:
        source=SOURCE/'strategy_models'/stage;dest=DEST/'models'/stage;dest.mkdir(parents=True,exist_ok=True)
        for path in source.iterdir():
            if path.is_file():shutil.copy2(path,dest/path.name)
        metadata=json.loads((dest/'training_info.json').read_text())
        assert hashlib.sha256((dest/'model.safetensors').read_bytes()).hexdigest()==metadata['checkpoint_sha256']
    for strategy in ['push','grasp']:
        items=json.loads((results/f'policy_{strategy}_summary.json').read_text())
        assert len(items)==3
    video=DEST/'video';video.mkdir(exist_ok=True)
    shutil.copy2(raw/'deliverables/PAI_final_push_to_grasp_comparison.mp4',video/'PAI_final_push_to_grasp_comparison.mp4')
    shutil.copy2(raw/'deliverables/video_info.json',results/'video_info.json')
    metrics={}
    for strategy in ['push','grasp']:
        items=json.loads((results/f'policy_{strategy}_summary.json').read_text())
        metrics[strategy]={'trials':len(items),'lifted_over_30mm':sum(r['lifted_3cm'] for r in items),
                           'goal_within_30mm':sum(r['distance_m']<=.03 for r in items),
                           'mean_max_lift_mm':statistics.mean(max(0,r['lift_m'])*1000 for r in items),
                           'mean_goal_error_mm':statistics.mean(r['distance_m']*1000 for r in items)}
    (results/'metrics.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
