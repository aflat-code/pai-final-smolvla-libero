# SmolVLAの主要機構実装とLIBEROロボット操作

Physical AI応用1講座の最終課題として、Vision-Language-Action (VLA) モデルの主要機構をPyTorchで実装し、LIBERO-plusシミュレーションで学習・評価したプロジェクトです。

## 概要

- 入力: 前方カメラ画像、自然言語のタスク指示、ロボット状態
- 出力: 7次元のロボット操作量を8ステップ分まとめたAction chunk
- AI: SmolVLM2-500Mを凍結したVision-Language encoderとして使用
- 学習部: Flow Matching TransformerをPyTorchで実装
- 評価: LIBERO-Spatialのロボットタスク

## 実装した要素

1. sinusoidal time embedding
2. ノイズと教師actionのFlow Matching補間
3. 目標速度ベクトルの計算
4. Euler法によるaction復元
5. 画像・言語・ロボット状態の統合
6. Action chunkingによる連続操作

## 実験条件

| 項目 | 値 |
|---|---:|
| 学習タスク | LIBERO-Spatial 10タスク |
| 学習エピソード | 50（各タスク5） |
| 学習ステップ | 300 |
| batch size | 1 |
| learning rate | 3e-4 |
| warmup | 30 steps |
| Action chunk | 8 |
| Flow steps | 10 |
| seed | 42 |

## 結果

- 最終学習loss: `0.591484785079956`
- 自作モデル評価: 2 rollout中0成功
- チェックポイントSHA-256: `33d9185ff59ded644db54b19c867c0c2c0e72172acce8a19a1a3b84c775188b3`

成功率0%も含めて実験結果です。ベースラインの成功例と比較し、学習300ステップ、50エピソード、小規模Action headでは操作ポリシーの習得が不十分だったことを考察しています。

## 実行方法

Google ColabのGPUランタイムで `notebooks/smolvla_libero_final.ipynb` を上から順に実行します。実行には数GBのLIBERO-plusアセットが必要です。

## ディレクトリ

```text
notebooks/   完了済み実装を含むColabノートブック
results/     実行結果と設定値
video/       提出用動画
report/      提出用PDF
```

## 注意とライセンス

本リポジトリは教育目的の実験記録です。Hugging Face、LeRobot、SmolVLM2、LIBERO/LIBERO-plusなどの第三者コード・モデル・データには、それぞれの配布元ライセンスが適用されます。学習済み重みや大容量アセットは本リポジトリに含めていません。
