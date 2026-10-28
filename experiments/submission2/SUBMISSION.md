# 提出候補②

提出①は変更せず保存済みです。この候補②を選ぶ場合は、以下を使用します。

1. PDF: `report/説明資料_提出②_押す動作から把持運搬へ.pdf`（3ページ）
2. 動画: `video/PAI_final_push_to_grasp_comparison.mp4`（2分3秒、通常シミュレーション速度）
3. 公開コード: https://github.com/aflat-code/pai-final-smolvla-libero/tree/experiment2-grasp-transfer/experiments/submission2

動画には前後各3試行をすべて収録しています。静止タイトル画面はなく、英語字幕を画面下部に配置しています。
追加学習前は押して移動し、追加学習後は約6.5cm持ち上げて運搬します。
どちらも固定した既知配置で3/3回、ゴール中心から3cm以内へ置けました。

「学習前」は押す動作を500ステップ学習済みのモデルです。その重みを把持データで2000ステップ追加学習しました。
教師データの戦略と進行度の時間設定も異なるので、単純な成功率向上や未知配置での汎用性を主張する比較ではありません。

YouTubeへのアップロードとOmniCampusへの提出は未実施です。
動画をYouTubeへ公開または限定公開でアップロードし、得られたURL、PDF、上記GitHub URLを指定の提出先へ登録してください。
YouTubeタイトルは課題指定に従い `PAI最終課題_Kamamoto` としてください。
