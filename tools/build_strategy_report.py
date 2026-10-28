"""Create a separate report for submission 2; never overwrite submission 1."""
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_block_report import p,table,footer,BODY,SMALL,H1,H2,TITLE
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Image,PageBreak,SimpleDocTemplate,Spacer

ROOT=Path(__file__).resolve().parents[1]/'experiments/submission2'


def main():
    results=ROOT/'results'
    before=json.loads((results/'policy_push_summary.json').read_text())
    after=json.loads((results/'policy_grasp_summary.json').read_text())
    b=json.loads((ROOT/'models/before/training_info.json').read_text())
    a=json.loads((ROOT/'models/after/training_info.json').read_text())
    video=json.loads((results/'video_info.json').read_text())
    out=ROOT/'report/説明資料_提出②_押す動作から把持運搬へ.pdf';out.parent.mkdir(parents=True,exist_ok=True)
    s=[Spacer(1,5*mm),p('押す動作から、掴んで運ぶ動作へ<br/>ACT追加学習による行動の切り替え',TITLE),
       p('Physical AI 応用1 最終課題 / 提出候補② / Kamamoto'),Spacer(1,4*mm)]
    frame=results/'learned_grasp_frame.jpg'
    if frame.exists():s += [Image(str(frame),width=174*mm,height=97.875*mm),Spacer(1,3*mm)]
    s += [p('1. 目的と課題設計',H1),
      p('追加学習による変化を映像で明確にするため、学習前は指を開いたままブロックを押し、学習後は指を閉じて持ち上げ、別の場所へ運ぶ比較を設計した。「学習前」は未学習のランダムモデルではなく、押す動作を学習済みの基準モデルを意味する。'),
      p('両者とも同じ机、CRANE+ V2、赤いブロック、青いゴールを使用する。開始中心は (x, y) = (0.130, 0.020)m、ゴール中心は (0.112, -0.070)m。一辺3cm、質量8g、摩擦係数2.0のブロックである。提出①の4cm・25gのブロックとは条件が異なり、提出①との成功率比較は行わない。'),
      p('独自性とAIの役割',H2),
      p('物理接触で成立する把持軌道、押し軌道、教師データ収集、ACTの継続学習、同一配置での反復実行、カメラtopic記録と比較動画を実装した。AIは関節状態から関節指令列を推論する。実行中に教師軌道へ切り替えたり、ブロックをロボットへ固定したりはしない。'),
      PageBreak(),p('2. システム・学習方法',H1),
      table([['構成','内容'],['実行環境','Docker内のROS 2 Humble / Ignition Gazebo 6.16.0'],
        ['通信','関節状態を購読し、arm / gripperのJointTrajectoryへ指令'],
        ['入力','実測関節5次元＋進行度・既知の初期座標3次元'],
        ['出力','ACTの16手×5軸の関節目標角（20Hz、16手ずつ実行）'],
        ['映像','Gazeboカメラtopicを直接記録。カメラ画像はAI入力には使わない']], [30,144]),
      Spacer(1,3*mm),p('教師データと継続学習',H2),
      p(f'逆運動学とsmoothstep補間による教師指令をGazeboで実行し、実測状態と指令を約20Hzで保存した。基準モデルは押す動作{b["episodes"]}エピソード・{b["frames"]:,}フレームで{b["steps_this_stage"]} steps学習した。その同じ重みを読み込み、把持・運搬動作{a["episodes"]}エピソード・{a["frames"]:,}フレームでさらに{a["steps_this_stage"]} steps学習した。後半には押すデータを混ぜず、optimizerは新規に作成した。'),
      table([['項目','設定'],['モデル','ACT / hidden 128 / 4 heads / encoder 2層 / decoder 1層 / VAE無効'],
        ['学習区分','外部事前学習重みなし。全ACTパラメータを学習し、その重みを継続更新'],
        ['学習量',f'500 steps → 追加2000 steps（累計2500 steps）'],
        ['ハイパーパラメータ','batch 16 / AdamW / lr 3e-4 / weight decay 1e-4 / grad clip 1.0'],
        ['その他',f'seed 42 / dropout 0.1 / CPU / {b["num_parameters"]:,} parameters'],
        ['正規化','基準モデルの統計を共有。基台回転std=0.35rad、gripper std=0.5radに固定'],
        ['進行度','押す15秒、把持・運搬25秒を各0-1へ正規化。推論側も対応する時間設定を使用']], [32,142]),
      Spacer(1,3*mm),p('物理的な把持の確認方法',H2),
      p('各試行前にhome姿勢への到達を確認し、ブロックのみを開始位置へリセットする。試行中の物体移動は関節指令とGazeboの接触計算だけで生じる。物体の高さはdynamic pose topicで記録し、試行前後は名前付きの物体位置と照合する。把持用の固定・吸着・アタッチ補助は使用しない。'),
      p('押し動作は指を開いたまま接触させ、把持動作は閉指・上昇・基台回転・下降・開指の順となる。3cmを超える物体上昇と、映像で挟んだ状態の運搬を確認する。高さの増加だけでは把持を完全に証明できないため、映像も併せて確認する。'),
      PageBreak(),p('3. 学習済みモデルの実行結果',H1)]
    rows=[['試行','前: 最大上昇(mm)','後: 最大上昇(mm)','前: 誤差(mm)','後: 誤差(mm)']]
    for x,y in zip(before,after):
        rows.append([x['trial']+1,f'{max(0,x["lift_m"])*1000:.1f}',f'{max(0,y["lift_m"])*1000:.1f}',
                     f'{x["distance_m"]*1000:.1f}',f'{y["distance_m"]*1000:.1f}'])
    s += [table(rows,[14,40,40,40,40]),Spacer(1,4*mm),
      p(f'各モデルを同じ開始配置で3回ずつ実行した。3cm超の上昇は基準モデル{sum(r["lifted_3cm"] for r in before)}/3回、追加学習後{sum(r["lifted_3cm"] for r in after)}/3回。ゴール中心から3cm以内への到達は基準{sum(r["distance_m"]<=.03 for r in before)}/3回、追加学習後{sum(r["distance_m"]<=.03 for r in after)}/3回。'),
      p(f'平均最大上昇量は {statistics.mean(max(0,r["lift_m"]) for r in before)*1000:.1f}mm → {statistics.mean(max(0,r["lift_m"]) for r in after)*1000:.1f}mm。平均ゴール中心誤差は {statistics.mean(r["distance_m"] for r in before)*1000:.1f}mm → {statistics.mean(r["distance_m"] for r in after)*1000:.1f}mm。各試行の生ログと重みをGitHubに保存する。'),
      p('考察と比較上の限界',H2),
      p('この実験は教師データの動作戦略を変更した継続学習であり、同じデータ・条件のままで能力が自然に向上したことを示す比較ではない。データ内容、学習量、進行度の時間設定が同時に異なる。固定した既知配置での軌道模倣であり、未知配置・物体に対する汎用的な把持能力は主張しない。3回は物理接触の反復確認であって、独立した未使用テストセットではない。'),
      p('提出①はそのまま別保存した。本候補②では持ち上げと運搬を明確に観察できることを優先した。今後は初期位置のばらつき、画像入力、異なる質量・摩擦への評価を追加する必要がある。'),
      p('動画と再現情報',H2),
      p(f'動画は{float(video["format"]["duration"]):.1f}秒、1280×720、H.264。前後各3試行のモデル実行をすべて収録し、静止画による時間延長は行わない。英語字幕を画面下部に配置し、通常速度（1x）で再生する。'),
      p('出典・権利',H2),
      p('LeRobot: huggingface/lerobot、commit 768e36660d1408c71118a2760f831c037fbfa17d（Apache-2.0）。CRANE+: AI-Robot-Book-Humble/crane_plus、commit 19c1d6069126cd27488bf1bbefd410704bfc515d（Apache-2.0）。講義環境: matsuolab/pai_training、commit b4d6b5459066a80433475a83567504988875248a。詳細URLとDocker image digestはリポジトリのTHIRD_PARTY_BLOCK.mdに記載する。',SMALL),
      p('自作コード・本課題の自作データ・新規学習重みはApache-2.0。外部の事前学習重みは不使用。各依存ソフトウェアには配布元の条件が適用される。',SMALL),
      p('基準重み SHA-256: '+b['checkpoint_sha256'],SMALL),
      p('追加後重み SHA-256: '+a['checkpoint_sha256'],SMALL)]
    SimpleDocTemplate(str(out),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=14*mm,bottomMargin=19*mm,
                      title='押す動作から、掴んで運ぶ動作へ',author='Kamamoto').build(s,onFirstPage=footer,onLaterPages=footer)
    print(out)


if __name__=='__main__':main()
