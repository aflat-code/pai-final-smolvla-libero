"""Freeze main search, three untouched evaluation repeats and diagnostic ablation."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics

BASE=Path(__file__).resolve().parents[1]
SOURCE=BASE/'ros2_workspace/reward_results'
DEST=BASE/'experiments/submission3'


def main():
    results=DEST/'results';raw=results/'raw';raw.mkdir(parents=True,exist_ok=True)
    policies=DEST/'policies';policies.mkdir(exist_ok=True)
    for name in ['before_policy.json','after_policy.json']:
        shutil.copy2(SOURCE/name,policies/name)
    for path in SOURCE.glob('*.json'):
        if path.name.startswith(('search_g','eval_')) or path.name=='initial_baseline.json':
            (raw/(path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
        elif not path.name.endswith('_policy.json'):shutil.copy2(path,results/path.name)
    pilot=BASE/'ros2_workspace/reward_pilot_workspace_check'
    if pilot.exists():
        for path in pilot.glob('*.json'):
            (raw/('pilot_'+path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    for name in ['reward_search.log','reward_search_interruption.log','reward_launch.log','reward_contact_bridge.log','reward_test.log',
                 'reward_eval_before.log','reward_eval_after.log']:
        path=BASE/'ros2_workspace'/name
        if path.is_file():shutil.copy2(path,results/name)
    video=DEST/'video';video.mkdir(exist_ok=True)
    shutil.copy2(SOURCE/'deliverables/PAI_final_reward_driven_transport.mp4',video/'PAI_final_reward_driven_transport.mp4')
    shutil.copy2(SOURCE/'deliverables/video_info.json',results/'video_info.json')
    metrics={}
    for stage in ['before','after']:
        rows=json.loads((results/(stage+'_eval_summary.json')).read_text())
        assert len(rows)==3
        metrics[stage]={'trials':len(rows),'goal_reached':sum(r['goal_reached'] for r in rows),
                        'lifted_3cm':sum(r['lifted_3cm'] for r in rows),
                        'mean_return':statistics.mean(r['reward'] for r in rows),
                        'mean_slide_mm':statistics.mean(r['slide_m']*1000 for r in rows),
                        'mean_air_xy_mm':statistics.mean(r['air_xy_m']*1000 for r in rows),
                        'mean_max_lift_mm':statistics.mean(max(0,r['max_lift_m'])*1000 for r in rows),
                        'mean_goal_error_mm':statistics.mean(r['goal_error_m']*1000 for r in rows)}
    history=json.loads((results/'search_history.json').read_text())
    initial=json.loads((SOURCE/'initial_baseline.json').read_text())['summary']
    pool=[initial,*history]
    no_cost=lambda r:r['reward']-r['reward_terms']['slide_penalty']
    ablation={'scope':'Offline re-scoring of the same observed candidate pool; NOT independently retrained controls',
              'candidate_count':len(pool),'winner_with_slide_cost':max(pool,key=lambda r:r['reward']),
              'winner_without_slide_cost':max(pool,key=no_cost),
              'scores':[{'label':r['label'],'parameters':r['parameters'],
                         'with_slide_cost':r['reward'],'without_slide_cost':no_cost(r)} for r in pool]}
    (results/'slide_cost_ablation.json').write_text(json.dumps(ablation,indent=2))
    (results/'metrics.json').write_text(json.dumps(metrics,indent=2))
    manifest={str(path.relative_to(DEST)):hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(policies.glob('*.json'))}
    (results/'policy_sha256.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(metrics,indent=2))
    print('Offline zero-slide-cost winner:',ablation['winner_without_slide_cost']['label'])


if __name__=='__main__':main()
