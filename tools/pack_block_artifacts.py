"""Copy verified experiment evidence into the public submission structure."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    raw=ROOT/'ros2_workspace'/'block_results'
    dest=ROOT/'results'/'block_push';dest.mkdir(parents=True,exist_ok=True)
    for name in ['before_summary.json','after_summary.json','teacher_summary.json','video_info.json']:
        shutil.copy2(raw/name,dest/name)
    exploration=dest/'exploratory_vae';exploration.mkdir(exist_ok=True)
    for name in ['before_summary.json','after_summary.json']:
        shutil.copy2(ROOT/'ros2_workspace/ablation_vae/results'/name,exploration/name)
    shutil.copy2(ROOT/'ros2_workspace/ablation_vae/comparison_training.json',exploration/'comparison_training.json')
    shutil.copy2(ROOT/'ros2_workspace/block_models/comparison_training.json',dest/'comparison_training.json')
    for label in ['before','after']:
        target=ROOT/'models/block_push'/label;target.mkdir(parents=True,exist_ok=True)
        for name in ['model.safetensors','config.json','training_info.json']:
            shutil.copy2(ROOT/'ros2_workspace/block_models'/label/name,target/name)
        for source in sorted(raw.glob(label+'_[0-9][0-9].json')):shutil.copy2(source,dest/source.name)
    episodes={p.stem:json.loads(p.read_text()) for p in sorted(raw.glob('teacher_[0-9][0-9].json'))}
    with gzip.open(dest/'demonstrations.json.gz','wt',encoding='utf-8') as stream:json.dump(episodes,stream,separators=(',',':'))
    with (dest/'comparison.csv').open('w',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['stage','trial','initial_x_m','initial_y_m','final_x_m','final_y_m','goal_error_mm','success'])
        for label in ['before','after']:
            for row in json.loads((dest/(label+'_summary.json')).read_text()):
                writer.writerow([label,row['trial']+1,*row['start'],*row['final'][:2],row['distance_m']*1000,row['success']])
    video=ROOT/'video/PAI_final_block_push_comparison.mp4'
    shutil.copy2(ROOT/'ros2_workspace/video/PAI_final_block_push_comparison.mp4',video)
    after=json.loads((dest/'after_summary.json').read_text())
    best=next((r for r in after if r['success']),after[0])
    source=raw/f'after_{best["trial"]:02d}.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(source)]))
    duration=float(info['format']['duration'])
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(duration*.8),'-i',str(source),'-frames:v','1',str(dest/'task_frame.jpg')],check=True)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [video,ROOT/'models/block_push/before/model.safetensors',ROOT/'models/block_push/after/model.safetensors',dest/'demonstrations.json.gz']}
    (dest/'SHA256.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps(hashes,indent=2))


if __name__=='__main__':main()
