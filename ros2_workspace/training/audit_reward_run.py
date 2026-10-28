"""Reconstruct seeded proposals and verify selection, actions and reward records."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from reward_search import BOUNDS,SEED,INITIAL,command,score


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='/workspace/reward_results');args=p.parse_args()
    root=Path(args.root);load=lambda name:json.loads((root/name).read_text())
    contract=load('reward_contract.json');history=load('search_history.json')
    baseline=load('initial_baseline.json')['summary'];best=baseline
    rng=np.random.default_rng(SEED);lower,upper=BOUNDS.T
    mean=np.asarray(INITIAL);std=(upper-lower)/2
    population=contract['population'];generations=contract['generations']
    assert len(history)==population*generations
    for gen in range(generations):
        n=population if gen==0 else population//2
        grid=np.column_stack([(rng.permutation(n)+rng.random(n))/n for _ in range(2)])
        candidates=list(lower+grid*(upper-lower))
        if gen:
            candidates.extend(np.clip(rng.normal(mean,std,size=(population-n-1,2)),lower,upper))
            candidates.append(np.asarray(best['parameters']))
        batch=history[gen*population:(gen+1)*population]
        for expected,row in zip(candidates,batch):
            assert np.allclose(expected,row['parameters'],atol=1e-12,rtol=0.)
            if row['reward']>best['reward']:best=row
        elite=sorted(batch,key=lambda x:x['reward'],reverse=True)[:max(2,population//4)]
        matrix=np.array([r['parameters'] for r in elite]);mean=matrix.mean(axis=0)
        std=np.maximum(matrix.std(axis=0),(upper-lower)*.08)
    selected=load('selected.json');policy=load('after_policy.json')
    assert np.array_equal(best['parameters'],policy['parameters'])
    assert selected['best_search_result']['label']==best['label']
    assert selected['policy_sha256']==hashlib.sha256((root/'after_policy.json').read_bytes()).hexdigest()
    paths=[root/'initial_baseline.json',*sorted(root.glob('search_g*.json')),*sorted(root.glob('eval_*.json'))]
    checked=0
    for path in paths:
        data=json.loads(path.read_text());summary=data['summary'];params=summary['parameters']
        reward,terms=score(summary['goal_error_m'],summary['slide_m'],params,summary['final'][2])
        assert abs(reward-summary['reward'])<1e-9
        assert all(abs(terms[k]-v)<1e-9 for k,v in summary['reward_terms'].items())
        # Verify physical-contact distance from raw samples (first sample is stationary).
        rows=data['samples'];slide=0.
        for prev,row in zip(rows,rows[1:]):
            if row['table_contact'] or prev['table_contact']:
                slide+=float(np.linalg.norm(np.asarray(row['block'][:2])-np.asarray(prev['block'][:2])))
        assert abs(slide-summary['slide_m'])<1e-4
        for row in rows:
            assert np.allclose(command(params,row['time']),row['action'],atol=1e-10,rtol=0.)
        if path.name.startswith('eval_'):
            stage='before' if path.name.startswith('eval_before_') else 'after'
            assert params==load(stage+'_policy.json')['parameters']
        checked+=1
    for stage in ['before','after']:assert len(load(stage+'_eval_summary.json'))==3
    report={'passed':True,'seeded_candidate_sequence_verified':True,'selection_by_reward_only_verified':True,
            'frozen_policy_hash_verified':True,'raw_contact_distance_verified':True,
            'raw_actions_and_reward_components_verified':True,'audited_physical_episodes':checked,
            'source_sha256':hashlib.sha256((Path(__file__).parent/'reward_search.py').read_bytes()).hexdigest()}
    (root/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
