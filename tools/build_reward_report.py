"""Measured reward-search report; distinguish learned parameters from human priors."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_block_report import p,table,footer,SMALL,H1,H2,TITLE
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Image,PageBreak,SimpleDocTemplate,Spacer

ROOT=Path(__file__).resolve().parents[1]/'experiments/submission3'


def main():
    result=ROOT/'results'
    load=lambda name:json.loads((result/name).read_text())
    metrics=load('metrics.json');b=metrics['before'];a=metrics['after']
    before=load('before_eval_summary.json');after=load('after_eval_summary.json')
    selected=load('selected.json');ablation=load('slide_cost_ablation.json');video=load('video_info.json')
    pb=json.loads((ROOT/'policies/before_policy.json').read_text())
    pa=json.loads((ROOT/'policies/after_policy.json').read_text())
    hashes=load('policy_sha256.json')
    out=ROOT/'report/説明資料_PAI最終課題_Kamamoto.pdf';out.parent.mkdir(parents=True,exist_ok=True)
    s=[Spacer(1,4*mm),p('報酬で、ブロックの運び方は変わるか<br/>滑りペナルティによる方策探索',TITLE),
       p('Physical AI 応用1 最終課題 / 提出候補③ / Kamamoto'),Spacer(1,4*mm)]
    frame=result/'learned_transport_frame.png'
    if frame.exists():s += [Image(str(frame),width=174*mm,height=97.875*mm),Spacer(1,3*mm)]
    s += [p('1. 課題の目的',H1),
      p('「ゴールへ運ぶと加点し、机に接触したまま滑らせると減点する」という報酬から、ロボットが持ち上げて運ぶ設定を選べるかを試した。提出②のように把持のお手本を追加するのではなく、Gazeboでの実行結果を使って連続値の方策パラメータを更新する。持ち上げ自体への加点は与えない。'),
      p('実験環境はDocker内のROS 2 HumbleとIgnition Gazebo 6.16.0、CRANE+ V2。一辺3cm・8g・摩擦係数2.0の赤いブロックを、開始 (0.130, 0.020)m から青いゴール中心 (0.112, -0.070)m へ運ぶ。物体の固定・吸着・アタッチ補助は使わず、開始前のリセット以外に物体位置を書き換えない。'),
      p('何を自動で学習し、何を人が与えたか',H2),
      p('探索するのは指の閉じ角と運搬時の上昇量の2つ。接近・下降・閉指・移動・開放の順序、接触高さ、方向、逆運動学と到達可能性のための傾きは人が与える。「自由な関節運動から把持をゼロから発明した」のではなく、共通の動作骨格の範囲で、報酬を最大にする設定を選ぶ実験である。'),
      p('提出①・②は別保存した。本候補はACTではなく、CEM（Cross-Entropy Method）による直接方策探索。外部の事前学習重みや把持教師データは使用しない。',SMALL),
      PageBreak(),p('2. 報酬・探索・測定方法',H1),
      table([['項目','設定'],['方策','指の閉じ角 g: -0.52～+0.60rad / IK手首目標の上昇量 h: 0～50mm（物体の実測上昇量とは別）'],
        ['共通の骨格','接触高さ0.14m、運搬方向の回転角-0.70rad、25秒、約20Hzで関節指令'],
        ['初期方策','g=-0.52rad、h=0。人が初期化した開指・押し動作。学習済みACTではない'],
        ['探索','CEM / Python 3.10.12 / NumPy 1.24.4 / seed 20261029 / 3世代×12候補 / 上位3候補で分布を更新'],
        ['探索の維持','初世代はLatin hypercube。以降は一様探索6、正規分布5、最良候補の再試行1'],
        ['選択と評価','スカラー報酬だけで最良方策を凍結し、その後に前後各3回の新しい評価実行']], [30,144]),
      Spacer(1,3*mm),p('報酬関数（主探索の前に固定）',H2),
      p('eを終了時のゴール中心とのXY誤差、sを机との接触中に移動したXY距離、zを終了時のブロック中心高さとする。距離の単位はm。'),
      p('R = 20 exp[-0.5(e/0.03)<super>2</super>] + 8 I(ゴール到達・高さ範囲内)<br/>　- 300s - 0.5{[(g+0.52)/1.12]<super>2</super> + (h/0.055)<super>2</super>} - 100|z-1.03|'),
      p('ゴール到達は e≤0.03 かつ |z-1.03|&lt;0.015。持ち上げ・閉指への正の報酬はない。むしろ不要な閉指と上昇には小さいコストを課す。初期位置で何もしなければ到達加点は得られず、机上の中心高さから15mm以上離れた保持にも到達加点はない。速度による静止判定ではない。全候補で終了前に開指する。'),
      p('接触の計測と再現性',H2),
      p('Gazeboの実接触センサーから、赤ブロックと机の衝突名をROSへ橋渡しする。ブロックのXY変位を約20Hzで合計し、前後いずれかの測定時点で机に接触していた区間を保守的に滑りとして扱う。高さだけから接触を推測していない。ただしサンプリング近似であり、連続時間での厳密な摩擦仕事量ではない。'),
      p('各試行前にhome関節姿勢と物体位置を確認する。物体位置は動的pose topicで測り、名前付きposeと照合する。25秒の制御終了後、1秒待って終端位置を測る。撮影はカメラtopicの直接記録であり、探索後の評価実行を収録する。'),
      p('到達範囲確認用の小規模予備試行後、上昇量の上限を55mmから50mmへ修正した。主探索は初期方策1回＋候補36回の計37回。全候補と報酬成分を保存し、把持や高さのラベルで選別しない。',SMALL),
      PageBreak(),p('3. 凍結した方策の比較結果',H1)]
    rows=[['指標（各3回）','探索前','探索後'],['ゴール到達',f'{b["goal_reached"]}/3',f'{a["goal_reached"]}/3'],
          ['平均報酬',f'{b["mean_return"]:.2f}',f'{a["mean_return"]:.2f}'],
          ['平均机上滑り距離',f'{b["mean_slide_mm"]:.1f}mm',f'{a["mean_slide_mm"]:.1f}mm'],
          ['平均非接触中のXY移動',f'{b["mean_air_xy_mm"]:.1f}mm',f'{a["mean_air_xy_mm"]:.1f}mm'],
          ['平均最大上昇量',f'{b["mean_max_lift_mm"]:.1f}mm',f'{a["mean_max_lift_mm"]:.1f}mm'],
          ['平均ゴール誤差',f'{b["mean_goal_error_mm"]:.1f}mm',f'{a["mean_goal_error_mm"]:.1f}mm'],
          ['選択した g / h',f'{pb["parameters"][0]:.3f}rad / {pb["parameters"][1]*1000:.1f}mm',
                            f'{pa["parameters"][0]:.3f}rad / {pa["parameters"][1]*1000:.1f}mm']]
    s += [table(rows,[62,56,56]),Spacer(1,3*mm)]
    if a['goal_reached']==3 and a['mean_slide_mm']<b['mean_slide_mm'] and a['mean_air_xy_mm']>20:
        s += [p('報酬で選ばれた設定は、初期の押し動作と比べて机上の滑りを減らし、ブロックを持ち上げながらゴールへ運べた。持ち上げそのものへの加点はなく、指の閉じ角と上昇量の組み合わせが実行結果の報酬から選択された。')]
    else:
        s += [p('結果は上表の通りであり、狙った行動変化が安定して成立したかは動画と各試行値を併せて判断する。ゴール到達、滑り抑制、上昇のいずれかが不足した場合、報酬値の上昇だけをもって把持成功とはみなさない。')]
    zero=ablation['winner_without_slide_cost'];full=ablation['winner_with_slide_cost']
    s += [p('滑り減点を外した場合の診断',H2),
      p(f'同じ実測候補群の再採点では、滑り減点なしの最良候補は上昇{max(0,zero["max_lift_m"])*1000:.1f}mm・滑り{zero["slide_m"]*1000:.1f}mmの押し動作、減点ありの最良候補は上昇{max(0,full["max_lift_m"])*1000:.1f}mm・滑り{full["slide_m"]*1000:.1f}mmの運搬だった。これは同じ候補群に対する再順位付けであり、別の乱数・別の探索過程で独立に再学習した対照実験ではない。'),
      p('限界と考察',H2),
      p('報酬による探索は、指の閉じ方と上昇量に限定されている。既知の固定配置・既知寸法に対する時間ベースの方策であり、画像認識、未知配置、実機での汎用的な把持能力を示すものではない。初期方策は人が設定しており、ゴール報酬だけで独立に学習した方策との比較でもない。3反復は小規模な物理再現性の確認であり、学習の因果効果や一般的成功率の統計検定ではない。'),
      p('本実験の意義は、お手本を把持へ変更せず、同じ連続動作骨格に対して報酬の評価から運搬設定を選べるかを可視化する点にある。今後は滑り減点なしの独立探索、複数の学習seed、未知開始位置での評価へ発展させる。'),
      p(f'動画は{float(video["format"]["duration"]):.1f}秒。前後各3回をすべて収録し、画面下部の英語字幕に報酬・滑り・上昇・誤差を表示する。カメラ15fpsのシミュレーション時間基準（1x）で、静止画像による時間延長は行わない。制御は実時間基準であり、描画負荷により動画尺と一致しない。',SMALL),
      p('出典・バージョン・権利',H2),
      p('CEM参考: Szita &amp; Lorincz, ICML 2003, https://cdn.aaai.org/ICML/2003/ICML03-068.pdf 。Duan et al., ICML 2016, https://proceedings.mlr.press/v48/duan16.pdf 。探索は自作NumPy実装。CRANE+ commit 19c1d6069126cd27488bf1bbefd410704bfc515d（Apache-2.0）。講義Docker・ROS・Gazeboの固定情報はTHIRD_PARTY_BLOCK.mdを参照。自作コード・データ・方策パラメータはApache-2.0。ニューラル重みは使用しない。',SMALL),
      p('探索前方策 SHA-256: '+hashes['policies/before_policy.json'],SMALL),
      p('探索後方策 SHA-256: '+hashes['policies/after_policy.json'],SMALL)]
    SimpleDocTemplate(str(out),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=14*mm,bottomMargin=19*mm,
                      title='報酬で、ブロックの運び方は変わるか',author='Kamamoto').build(s,onFirstPage=footer,onLaterPages=footer)
    print(out)


if __name__=='__main__':main()
