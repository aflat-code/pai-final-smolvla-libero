"""All six frozen-policy trials, real camera motion only, English lower captions."""
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    root=Path('/workspace/reward_results');work=root/'encoded';work.mkdir(exist_ok=True)
    dest=root/'deliverables';dest.mkdir(exist_ok=True);clips=[]
    for index in range(3):
        for stage in ['before','after']:
            stem=f'eval_{stage}_{index:02d}'
            result=json.loads((root/(stem+'.json')).read_text())['summary']
            title=('Before reward search | Initial open-finger policy' if stage=='before'
                   else 'After reward search | Policy selected by reward')
            row1=work/(stem+'_title.txt');row1.write_text(f'{title} | Trial {index+1}/3')
            row2=work/(stem+'_metrics.txt')
            row2.write_text(f'Return {result["reward"]:.1f} | Slide {result["slide_m"]*1000:.0f} mm | '
                            f'Lift {max(0,result["max_lift_m"])*1000:.0f} mm | '
                            f'Goal error {result["goal_error_m"]*1000:.0f} mm | 1x simulation')
            font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
            # A fixed, identical camera crop makes small clearances easier to see.
            vf=(f'crop=800:450:80:0,scale=1152:648,pad=1280:720:64:0:black,'
                f'drawtext=fontfile={font}:textfile={row1}:fontcolor=white:fontsize=25:x=(w-text_w)/2:y=650,'
                f'drawtext=fontfile={font}:textfile={row2}:fontcolor=white:fontsize=23:x=(w-text_w)/2:y=689')
            clip=work/(stem+'.mp4')
            subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(root/(stem+'.mp4')),'-vf',vf,
                            '-r','30','-an','-c:v','libx264','-crf','20','-preset','medium',
                            '-pix_fmt','yuv420p',str(clip)],check=True)
            clips.append(clip)
    concat=work/'concat.txt';concat.write_text(''.join(f"file '{p}'\n" for p in clips))
    output=dest/'PAI_final_reward_driven_transport.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),
                    '-c','copy','-movflags','+faststart',str(output)],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(output)]))
    if not 60<=float(info['format']['duration'])<=180:raise RuntimeError('Duration outside 1-3 minutes')
    info['sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    (dest/'video_info.json').write_text(json.dumps(info,indent=2))
    print(output,info['format']['duration'])


if __name__=='__main__':main()
