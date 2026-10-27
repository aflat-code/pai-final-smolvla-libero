"""Encode all paired ACT trials; no title slides, repeats, or slow motion."""
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    raw=Path('/workspace/block_results')
    output=Path('/workspace/video/PAI_final_block_push_comparison.mp4')
    output.parent.mkdir(parents=True,exist_ok=True)
    work=raw/'encoded';work.mkdir(exist_ok=True)
    clips=[]
    for index in range(5):
        for label in ['before','after']:
            stem=f'{label}_{index:02d}'
            data=json.loads((raw/(stem+'.json')).read_text())['summary']
            name='Before additional training' if label=='before' else 'After additional training'
            setting='10 demos / 200 steps' if label=='before' else '30 demos / 1400 total steps'
            row1=work/(stem+'_caption.txt');row2=work/(stem+'_result.txt')
            row1.write_text(f'{name} | Trial {index+1}/5 | {setting}')
            row2.write_text(f'Goal error: {data["distance_m"]*1000:.1f} mm | '+('Success' if data['success'] else 'Goal not reached')+' | 1x simulation playback')
            clip=work/(stem+'.mp4')
            font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
            vf=(f'scale=1152:648,pad=1280:720:64:0:black,'
                f'drawtext=fontfile={font}:textfile={row1}:fontcolor=white:fontsize=27:x=(w-text_w)/2:y=650,'
                f'drawtext=fontfile={font}:textfile={row2}:fontcolor=white:fontsize=23:x=(w-text_w)/2:y=689')
            subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw/(stem+'.mp4')),
                            '-vf',vf,'-r','30','-an','-c:v','libx264','-crf','20','-preset','medium',
                            '-pix_fmt','yuv420p',str(clip)],check=True)
            clips.append(clip)
    concat=work/'concat.txt';concat.write_text(''.join(f"file '{p}'\n" for p in clips))
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),
                    '-c','copy','-movflags','+faststart',str(output)],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(output)]))
    duration=float(info['format']['duration'])
    if not 60<=duration<=180:raise RuntimeError(f'Video length is {duration}s, expected 60-180s')
    info['sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    (raw/'video_info.json').write_text(json.dumps(info,indent=2))
    print(output,duration,flush=True)


if __name__=='__main__':main()
