# このブランチは提出候補③：報酬による運び方の探索

提出候補③の説明・動画・PDF・方策・全探索記録は
[experiments/submission3](experiments/submission3/) にまとめています。
今回は把持のお手本を追加するのではなく、机上の滑りを減点する報酬によって
共通動作骨格の2つの連続パラメータをCEMで探索します。

提出①は `main` / `submission-1-block-push`、提出②は
`experiment2-grasp-transfer` に保存済みです。以下は提出①の記録です。

---

# 赤いブロックを青いゴールへ：ACT追加学習の比較

Physical AI 応用1 最終課題 / アカウント名 **Kamamoto**

CRANE+ V2が一辺4cmの赤いブロックを約9cm押し、青いゴールへ入れる課題です。
ROS 2 Humble、Ignition Gazebo 6、Docker、LeRobot ACTを使います。
実際に収集した教師データによる基準学習と、その重みからの追加学習を比較します。

## 最終比較の結果

| 指標 | 追加学習前 | 追加学習後 |
|---|---:|---:|
| 成功数（固定5条件・各1回） | 3/5 | 3/5 |
| ゴール中心までの平均距離 | 28.2 mm | 38.4 mm |

今回、追加学習による改善は確認できませんでした。損失が下がっても接触動作の精度は改善せず、
基準モデルの方が平均誤差は小さい結果でした。提出動画は成功・失敗を含む全10試行です。

## 提出物

- [提出用動画](video/PAI_final_block_push_comparison.mp4)：5条件 × 追加学習前後。
- [説明資料PDF](report/説明資料_PAI最終課題_Kamamoto.pdf)
- [実測結果](results/block_push/)：試行別の座標・誤差・成功判定・学習条件・ハッシュ。
- [学習済みACT](models/block_push/)：beforeとafterの重み・設定・学習記録。
- [出典とライセンス](THIRD_PARTY_BLOCK.md)

動画はGazeboの`/crane_camera` topicを直接記録した映像です。英語字幕を下部に置き、
静止タイトル画面・繰り返し・スロー再生は使用しません。15fpsで生成されたシミュレーション映像を
通常のシミュレーション時間で再生します。ホスト上の実行時間は負荷により長くなる場合があります。

## AIと物理シミュレーション

ACT入力は実測の5関節状態と、進行度・既知の初期ブロックx/y座標の計8次元です。
画像は録画に使用し、今回の学習モデルは画像認識を行いません。
出力は5軸の関節位置を16手まとめたAction Chunkです。20Hzで16手を順次実行して再推論します。

各試行の開始前だけブロックをリセットします。試行中は関節指令だけを送り、
ブロックの移動はGazeboの物理接触によって起きます。物体の固定・吸着・瞬間移動は使いません。

成功条件は、終了時の中心がゴール中心`(0.290, -0.015)` mから3cm以内で、机上の高さを保つことです。
5条件のうち1条件は標準の学習配置、4条件は収集時に指定しなかった開始座標です。
各モデル・各条件を1回ずつ評価した小規模な比較です。

## 学習条件

| 項目 | 基準 | 追加学習後 |
|---|---|---|
| 実測教師データ | 標準配置10 episodes | 上記10 + 配置変化20 = 30 episodes |
| 学習steps | 200 | 基準重みから追加1,200（累計1,400） |
| optimizer | AdamW、lr 3e-4、weight decay 1e-4 | optimizerは再作成 |
| batch / seed | 16 / 42 | 16 / 42 |
| ACT | hidden 128、4 heads、encoder 2、decoder 1、VAE無効 | 同じ構成 |
| chunk / n_action_steps | 16 / 16 | 16 / 16 |
| dropout | 0.1（VAE無効のためKL項なし） | 同じ構成 |
| 実行環境 | CPU / PyTorch 2.7.0 | CPU / PyTorch 2.7.0 |

全ACTパラメータを新規学習し、外部事前学習重みは使用していません。
追加20 episodesは開始x/yを各±8mmの範囲で変えています。
関節はJointStateの配列位置ではなく名前で揃え、`joint1, joint2, joint4, joint3, gripper`の順にします。
初期座標と基台回転が基準データでは定数なので、環境状態と基台回転には共通の非ゼロ正規化スケールを用います。
正確な件数・パラメータ数・学習ログ・checkpoint SHA-256は`results/block_push/comparison_training.json`にあります。

## Dockerでの再現

Intel/AMD Linux、またはApple Silicon上のDocker Desktopのamd64エミュレーションを使用します。
初回は講義イメージと依存パッケージのダウンロードが必要です。

```bash
docker compose -f compose.block.yaml up -d
docker compose -f compose.block.yaml exec --user ubuntu block-demo bash /submission/tools/setup_block_environment.sh
```

ターミナル1でシミュレータを起動します。

```bash
docker compose -f compose.block.yaml exec --user ubuntu block-demo bash
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
source /workspace/install/setup.bash
ros2 launch crane_act_demo crane_camera.launch.py
```

ターミナル2で、提出モデルを評価します。

```bash
docker compose -f compose.block.yaml exec --user ubuntu block-demo bash
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
source /workspace/install/setup.bash
cd /home/ubuntu/pai_training
./.pixi/envs/default/bin/python /workspace/training/block_experiment.py eval \
  --model /submission/models/block_push/before --label before --video \
  --root /workspace/reproduction_results
./.pixi/envs/default/bin/python /workspace/training/block_experiment.py eval \
  --model /submission/models/block_push/after --label after --video \
  --root /workspace/reproduction_results
```

同じGazebo serverを重複起動しないでください。各試行の開始前にロボットをhomeへ戻し、
ブロック座標をリセットします。乱数seedを揃えても、負荷や接触ソルバの差により数mm以上の差が生じ得ます。
ブラウザGUIは`http://localhost:6080`で利用できますが、動画はGUI画面の録画ではありません。

## データ収集と再学習

同じROS環境を読み込んだターミナルで収集します。出力先は既存の提出結果と分けます。

```bash
python3 /workspace/training/block_experiment.py collect \
  --episodes 30 --root /workspace/new_demonstrations
cd /home/ubuntu/pai_training
./.pixi/envs/default/bin/python /workspace/training/train_block_act.py \
  --data /workspace/new_demonstrations --out /workspace/new_models
```

元の実測教師データは`results/block_push/demonstrations.json.gz`にも保存しています。
この圧縮ファイルは`{teacher_00: {...}, ...}`形式です。再学習する場合は各値を同名のJSONへ展開します。
教師軌道のコードは`block_expert.py`と`block_experiment.py`の`teacher()`、
学習コードは`train_block_act.py`、動画編集コードは`assemble_block_video.py`です。

## 解釈の範囲

追加学習ではエピソード数・配置の多様性・学習量を同時に変えています。
要因別の効果や統計的な優越性は主張しません。狭い卓上配置での状態ベースの軌道模倣であり、
未知物体や大きな配置変更、実機への転移は未検証です。PDFでは失敗も含めて実測結果を示します。
初回のVAE有効モデルでは基準4/5、追加後1/5でした。開始姿勢の差も見つかったため、
最終比較ではVAEを無効にし、開始前にhome姿勢へ到達したことを確認します。
探索中に同じ5配置を使用しており、最終結果は独立した未使用テストの成績ではありません。
探索結果は`results/block_push/exploratory_vae/`に保存しています。

旧LIBERO・腕振り・巡回の実験は[旧記録](README_legacy.md)として残しています。
今回の提出対象はこのページで案内したブロック押し課題です。
