"""Create the final Japanese report from the measured block-pushing results."""
import json
from pathlib import Path
import statistics

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results'/'block_push'
OUT=ROOT/'report'/'説明資料_PAI最終課題_Kamamoto.pdf'
pdfmetrics.registerFont(TTFont('JP','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
BODY=ParagraphStyle('body',fontName='JP',fontSize=10,leading=16,spaceAfter=6)
SMALL=ParagraphStyle('small',parent=BODY,fontSize=8,leading=12)
H1=ParagraphStyle('h1',parent=BODY,fontSize=17,leading=23,textColor=colors.HexColor('#174B6C'),spaceBefore=7,spaceAfter=10)
H2=ParagraphStyle('h2',parent=BODY,fontSize=12,leading=18,textColor=colors.HexColor('#087F8C'),spaceBefore=6,spaceAfter=5)
TITLE=ParagraphStyle('title',parent=H1,fontSize=22,leading=31,alignment=TA_CENTER)


def p(text,style=BODY):return Paragraph(text,style)


def table(rows,widths):
    t=Table([[p(str(c),SMALL) for c in row] for row in rows],colWidths=[w*mm for w in widths],repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E0EDF4')),
        ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#B1C4CE')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t


def footer(canvas,doc):
    canvas.setFont('JP',8);canvas.setFillColor(colors.HexColor('#60727C'))
    canvas.drawString(18*mm,12*mm,'Physical AI 応用1 最終課題 / Kamamoto')
    canvas.drawRightString(A4[0]-18*mm,12*mm,str(doc.page))


def main():
    before=json.loads((RESULTS/'before_summary.json').read_text())
    after=json.loads((RESULTS/'after_summary.json').read_text())
    training=json.loads((RESULTS/'comparison_training.json').read_text())
    video=json.loads((RESULTS/'video_info.json').read_text())
    b=training['before'];a=training['after']
    n_before=sum(r['success'] for r in before);n_after=sum(r['success'] for r in after)
    err_b=statistics.mean(r['distance_m'] for r in before)*1000
    err_a=statistics.mean(r['distance_m'] for r in after)*1000
    if n_after>n_before:
        interpretation='今回の固定5条件では、追加学習後に成功数が増えた。ただし試行数が少なく、成功率の一般的な向上を保証する結果ではない。'
    elif n_after<n_before:
        interpretation='今回の固定5条件では、追加学習後に成功数が減った。学習損失の低下だけでは、接触を含む実行成功を保証しないことが確認された。'
    elif err_a<err_b:
        interpretation='成功数は前後で同じだった。今回の実行では追加学習後の平均到達誤差が小さくなったが、接触のばらつきと各条件1回という制約があり、追加学習の優位性を断定しない。'
    else:
        interpretation='成功数は前後で同じで、平均到達誤差の改善も認められなかった。この課題では基準学習ですでに動作を獲得できており、学習量を増やすだけでは実行結果が改善するとは限らない。'
    story=[Spacer(1,5*mm),p('赤いブロックを青いゴールへ<br/>ACT追加学習によるロボット動作の比較',TITLE),
           p('Physical AI 応用1 最終課題 / アカウント名: Kamamoto',ParagraphStyle('center',parent=BODY,alignment=TA_CENTER)),Spacer(1,5*mm)]
    frame=RESULTS/'task_frame.jpg'
    if frame.exists():story += [Image(str(frame),width=174*mm,height=97.875*mm),Spacer(1,3*mm)]
    story += [p('1. 課題の概要と目的',H1),
      p('CRANE+ V2のグリッパーを押し具として使い、一辺4cmの赤いブロックを約9cm先の青いエリアへ移動する。把持や持ち上げを必要としない卓上整列作業として設計し、接触による物体移動を映像で確認できる課題にした。'),
      p('成功条件は、動作終了時のブロック中心が青いゴール中心から3cm以内で、机上の高さを保っていること。ゴールは9×10cm、ブロック質量は25g。開始位置は標準位置とその周辺の固定5条件を使う。'),
      p('AIの役割と独自の工夫',H2),
      p('AIにはLeRobotのACT（Action Chunking with Transformers）を用いる。関節状態・動作の進行度・初期ブロック位置から、5軸の関節指令を16手まとめて推定する。講義の構成を基に、押しタスクの物理環境、教師軌道、データ収集、追加学習、同条件比較、動画記録を独自に実装した。'),
      p('動画で動いているのは学習済みACTの推論結果である。教師軌道を実行した映像は、学習モデルの成果として使用しない。',SMALL),
      PageBreak(),p('2. システムと学習方法',H1),
      table([['構成','実装内容'],['Docker','講義配布のUbuntu / ROS 2 Humble環境を利用'],
             ['Gazebo','Ignition Gazebo 6.16.0。剛体ブロックと机、CRANE+の衝突・接触を計算'],
             ['ROS 2','/joint_statesを購読し、arm / gripperのjoint_trajectoryへ指令'],
             ['AI推論','状態5次元＋環境状態3次元 → ACT → 16×5次元の行動列'],
             ['撮影','/crane_cameraの画像topicを直接記録。英語字幕を下部に配置']], [33,141]),
      Spacer(1,4*mm),p('教師データ',H2),
      p('逆運動学とsmoothstep補間で「接近 → 下降 → 押す → 退避」の教師動作を生成し、実際にGazeboで実行した。20Hzで実測関節状態と教師指令を保存した。関節は名前で順序を揃え、joint1 / joint2 / joint4 / joint3 / gripperの順とする。'),
      p(f'基準学習は標準配置で収集した{b["episodes"]}エピソード、{b["frames"]:,}フレーム。追加学習は開始位置のx・yを各±8mm変えた20エピソードを追加し、計{a["episodes"]}エピソード、{a["frames"]:,}フレームを使用した。追加学習では基準モデルの重みを読み込み、optimizerを新規作成して継続した。'),
      table([['項目','設定'],['モデル','ACT / hidden 128 / 4 heads / encoder 2層 / decoder 1層 / VAE無効'],
             ['Action Chunk','chunk_size=16、n_action_steps=16、指令周期20Hz'],
             ['学習量',f'基準{b["steps_this_stage"]} steps → 追加{a["steps_this_stage"]} steps（累計{b["steps_this_stage"]+a["steps_this_stage"]}）'],
             ['主な設定','batch 16 / AdamW / lr 3e-4 / weight decay 1e-4 / grad clip 1.0'],
             ['その他','seed 42 / dropout 0.1 / CPU / 全ACTパラメータを学習（VAE無効のためKL項なし）'],
             ['学習パラメータ数',f'{b["num_parameters"]:,}'],
             ['正規化','関節と行動は基準データの統計値。基台回転・進行度・初期座標には共通の非ゼロ固定スケールを使用']], [35,139]),
      Spacer(1,3*mm),p('入力と比較の範囲',H2),
      p('カメラ画像は撮影に使用し、今回のACT入力には含めない。進行度と既知の初期座標を与える状態ベースの模倣学習であり、未知物体の画像認識は扱わない。物体位置を設定する処理は各試行開始前のリセットに限定し、実行中の移動はロボットとの物理接触で発生する。'),
      PageBreak(),p('3. 結果と考察',H1)]
    rows=[['条件','開始 x / y (m)','基準 誤差(mm)','追加後 誤差(mm)','成功 前 → 後']]
    for x,y in zip(before,after):
        rows.append([str(x['trial']+1),f"{x['start'][0]:.3f} / {x['start'][1]:.3f}",f"{x['distance_m']*1000:.1f}",f"{y['distance_m']*1000:.1f}",f"{'○' if x['success'] else '×'} → {'○' if y['success'] else '×'}"])
    story += [table(rows,[14,43,38,38,41]),Spacer(1,4*mm),
      p(f'成功数は基準 {n_before}/5、追加学習後 {n_after}/5。平均のゴール中心誤差は {err_b:.1f}mm → {err_a:.1f}mm。標準配置1条件は学習時と同一で、残り4条件は収集時に指定しなかった開始座標である。同じ5条件で各1回実行した。'),
      p('考察と限界',H2),
      p(interpretation),
      p('追加学習ではデータ数・開始位置の多様性・学習ステップ数を同時に増やしたため、結果の差を一つの要因だけに帰属することはできない。各条件1回の小規模比較であり、統計的な優劣や未知環境への汎用性を示すものではない。探索にも同じ5配置を使用しており、独立した未使用テストではない。シミュレーション速度や接触の微小差も結果に影響し得る。'),
      p('当初の腕振り動作は達成条件が不明確で、ボール把持は横滑りを生じて持ち上げに至らなかった。初回のブロック比較（VAE有効）は基準4/5、追加後1/5で、グリッパーの開始姿勢にも差があった。最終比較はVAEを無効にし、home姿勢への到達確認を加えた。これらを同時変更したため、初回の悪化原因の厳密な切り分けは未了である。今後は画像入力と未使用配置での反復評価へ発展させる。'),
      p('提出動画',H2),
      p(f'長さ {float(video["format"]["duration"]):.1f}秒、1280×720、H.264。追加学習前後の5試行ずつを収録し、試行番号と学習条件を英語で表示する。再生速度は動画内の表示に従う。全編Gazeboの実行映像とし、タイトル静止画は挿入しない。'),
      p('出典・バージョン・権利',H2),
      p('LeRobot: huggingface/lerobot、commit 768e36660d1408c71118a2760f831c037fbfa17d（Apache-2.0）。CRANE+: AI-Robot-Book-Humble/crane_plus、commit 19c1d6069126cd27488bf1bbefd410704bfc515d（Apache-2.0）。講義教材: matsuolab/pai_training、commit b4d6b5459066a80433475a83567504988875248a。依存コードは配布元の条件に従う。',SMALL),
      p('自作コード・自作シミュレーションデータ・本課題で新規学習した重みはApache-2.0で公開する。外部の事前学習重みは使用していない。ROS 2、Gazebo、Docker imageには各配布元のライセンスが適用される。第三者ソースを取得するURLと固定revisionはGitHubの再現手順に記載した。',SMALL),
      p('基準チェックポイント SHA-256: '+b['checkpoint_sha256'],SMALL),
      p('追加学習後チェックポイント SHA-256: '+a['checkpoint_sha256'],SMALL)]
    SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=14*mm,bottomMargin=19*mm,
        title='赤いブロックを青いゴールへ：ACT追加学習によるロボット動作の比較',author='Kamamoto').build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUT)


if __name__=='__main__':main()
