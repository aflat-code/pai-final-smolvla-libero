"""Show every learned-policy trial at original speed with English lower captions."""
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    root=Path('/workspace/strategy_results')
    # /workspace is the Docker bind mount of ros2_workspace; host export is separate.
    dest=root/'deliverables';dest.mkdir(exist_ok=True)
    work=root/'encoded';work.mkdir(exist_ok=True)
    clips=[]
    for index in range(3):
        for stage in ['push','grasp']:
            stem=f'policy_{stage}_{index:02d}'
            s=json.loads((root/(stem+'.json')).read_text())['summary']
            title=('Before additional training | Learned push | 500 steps' if stage=='push'
                   else 'After additional training | Learned grasp + transfer | 2500 total steps')
            row1=work/(stem+'_title.txt');row1.write_text(title)
            row2=work/(stem+'_result.txt')
            row2.write_text(f'Trial {index+1}/3 | Lift: {max(0,s["lift_m"])*1000:.1f} mm | '
                            f'Goal error: {s["distance_m"]*1000:.1f} mm | 1x simulation playback')
            font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
            vf=(f'scale=1152:648,pad=1280:720:64:0:black,'
                f'drawtext=fontfile={font}:textfile={row1}:fontcolor=white:fontsize=25:x=(w-text_w)/2:y=650,'
                f'drawtext=fontfile={font}:textfile={row2}:fontcolor=white:fontsize=23:x=(w-text_w)/2:y=689')
            clip=work/(stem+'.mp4')
            subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(root/(stem+'.mp4')),
                            '-vf',vf,'-r','30','-an','-c:v','libx264','-crf','20','-preset','medium',
                            '-pix_fmt','yuv420p',str(clip)],check=True)
            clips.append(clip)
    manifest=work/'concat.txt';manifest.write_text(''.join(f"file '{p}'\n" for p in clips))
    output=dest/'PAI_final_push_to_grasp_comparison.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(manifest),
                    '-c','copy','-movflags','+faststart',str(output)],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams',
                                            '-of','json',str(output)]))
    if not 60<=float(info['format']['duration'])<=180:raise RuntimeError('Video outside assignment duration')
    info['sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    (dest/'video_info.json').write_text(json.dumps(info,indent=2))
    print(output,info['format']['duration'])


if __name__=='__main__':main()
