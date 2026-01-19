# 評価実行ガイド

**対象**: リフレーミングシステムの本評価実行  
**評価条件**: C0, C1, C2, C3, C4（5条件）  
**シナリオ数**: S1-S10（10シナリオ）  
**推定所要時間**: 30-40分

---

## 📋 前提条件の確認

### システム要件

- [x] Python 3.8+
- [x] Neo4j サーバー稼働中
- [x] Azure OpenAI Service アクセス可能
- [x] 必要なPythonパッケージインストール済み

### 設定ファイル確認

```bash
# 環境変数設定済みか確認
cat config/.env

# 必要な環境変数
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
```

### Neo4jデータ準備

```bash
# テストユーザーデータをNeo4jにシード
python3 scripts/seed_test_data.py
```

**確認事項**: `test_user_001` とその属性（History Buff, Introvert等）がNeo4jに存在すること

---

## 🚀 評価実行手順

### Step 1: 事前確認

```bash
# 作業ディレクトリに移動
cd /home/shimada-m/project_university/reframing

# Neo4j接続確認
python3 -c "from src.services.neo4j_service import Neo4jService; Neo4jService()"

# 出力例: "Neo4j Connected."
```

### Step 2: 条件別評価実行

**各条件で全シナリオ（S1-S10）を実行**

```bash
# C0: Baseline (Single Agent)
python3 evaluation/run_eval.py --condition C0 --episodes 10

# C1: Proposed (Multi-Agent Full)
python3 evaluation/run_eval.py --condition C1 --episodes 10

# C2: Multi-Agent WITHOUT External Knowledge
python3 evaluation/run_eval.py --condition C2 --episodes 10

# C3: Multi-Agent WITHOUT Agreement Steps
python3 evaluation/run_eval.py --condition C3 --episodes 10

# C4: Multi-Agent WITHOUT EAST Nudge
python3 evaluation/run_eval.py --condition C4 --episodes 10
```

**注意事項**:
- 各条件の実行には約6-8分かかります
- エラーが発生した場合（例: S8のContent Filter）は記録し、続行してください
- 実行中は `evaluation/logs/` にログが蓄積されます

### Step 3: メトリクス計算

**全条件の評価完了後、LLM Judgeを実行**

```bash
python3 evaluation/scripts/compute_metrics.py
```

**出力ファイル**:
- `evaluation/results/judge_metrics_YYYYMMDD_HHMMSS.csv`
- `evaluation/results/judge_reasoning_YYYYMMDD_HHMMSS.json`

**所要時間**: 約5-10分（LLM Judgeが全エピソードを評価）

### Step 4: 結果確認

```bash
# CSVをプレビュー
head -20 evaluation/results/judge_metrics_*.csv

# 条件別平均スコアを確認
python3 -c "
import pandas as pd
df = pd.read_csv('evaluation/results/judge_metrics_*.csv')  # 最新ファイルを指定
print(df.groupby('Condition')[['Reframing Score', 'Unexpectedness', 'User Engagement']].mean())
"
```

---

## 📊 生成されるデータファイル

### ログファイル（`evaluation/logs/`）

| ファイル | 説明 |
|---------|------|
| `episode_log_*.jsonl` | エピソード開始/終了記録（条件、成功/失敗、実行時間等） |
| `turn_log_*.jsonl` | ユーザー・システム発話記録 |
| `scenario_detail_*.json` | **詳細プロセスログ**（COMET/Explorer/Reframe出力） |
| `neo4j_snapshots/*_before.json` | エピソード実行前のNeo4j状態 |
| `neo4j_snapshots/*_after.json` | エピソード実行後のNeo4j状態 |

### メトリクス結果（`evaluation/results/`）

| ファイル | 説明 |
|---------|------|
| `judge_metrics_*.csv` | **統合メトリクス**（全条件・全エピソード） |
| `judge_reasoning_*.json` | **Judge推論理由**（なぜそのスコアか） |

---

## 🔍 トラブルシューティング

### エラー: `Neo4j Connection Failed`

**原因**: Neo4jサーバーが起動していない

**対処法**:
```bash
# Neo4jを起動
neo4j start

# 接続確認
neo4j status
```

### エラー: `ResponsibleAIPolicyViolation` (S8等)

**原因**: Azure OpenAIのコンテンツフィルター

**対処法**:
- 該当エピソードをスキップ（論文で制約として記載）
- または、シナリオテキストを調整

### エラー: `KeyError: 'utterance_text'`

**原因**: `turn_log` のカラム名不一致

**対処法**:
- `compute_metrics.py` が最新版であることを確認
- 必要に応じて `turn_log` を再生成

### ログファイルが大量に蓄積

**対処法**:
```bash
# 古いログを削除（本評価前に実施推奨）
rm -rf evaluation/logs/episode_log_*.jsonl
rm -rf evaluation/logs/turn_log_*.jsonl
rm -rf evaluation/logs/scenario_detail_*.json
rm -rf evaluation/logs/neo4j_snapshots/*.json
rm -rf evaluation/results/*
```

---

## 📈 データ分析例

### 条件別平均スコア

```python
import pandas as pd

df = pd.read_csv('evaluation/results/judge_metrics_YYYYMMDD_HHMMSS.csv')

# 条件別平均
summary = df.groupby('Condition')[['Reframing Score', 'Unexpectedness', 'User Engagement']].agg(['mean', 'std'])
print(summary)
```

### Case Study用ログ抽出

```python
import json

# S1のC1詳細ログを読み込み
with open('evaluation/logs/scenario_detail_S1_YYYYMMDD_HHMMSS.json') as f:
    detail = json.load(f)

# COMET推論を確認
for step in detail['process_trace']:
    if step['node'] == 'COMET':
        print("COMET Inferences:", step['inferences'])
```

### Judge推論理由の確認

```python
import json

with open('evaluation/results/judge_reasoning_YYYYMMDD_HHMMSS.json') as f:
    reasoning = json.load(f)

# S1のC1のJudge推論を確認
for entry in reasoning:
    if entry['Episode'] == 'S1' and 'C1' in entry['run_id']:
        print("Reframing Reason:", entry['reasoning']['Reframing Reason'])
```

---

## ⏱️ タイムライン（参考）

| フェーズ | 所要時間 | 累計 |
|---------|---------|------|
| 前提確認 | 5分 | 5分 |
| C0実行（S1-S10） | 5分 | 10分 |
| C1実行（S1-S10） | 8分 | 18分 |
| C2実行（S1-S10） | 12分 | 30分 |
| C3実行（S1-S10） | 6分 | 36分 |
| C4実行（S1-S10） | 8分 | 44分 |
| compute_metrics | 8分 | 52分 |
| **合計** | **約50-60分** | - |

---

## ✅ 実行完了後のチェックリスト

- [ ] 5条件すべてで10エピソード実行完了
- [ ] `judge_metrics_*.csv` 生成確認（50行 = 5条件 × 10エピソード）
- [ ] `judge_reasoning_*.json` 生成確認
- [ ] 各条件の平均スコアが妥当な範囲（C0: 1.0前後、C1: 4.0以上）
- [ ] エラーがあれば記録（論文の制約セクションに記載）

---

## 📝 次のステップ

1. **結果分析**: 統計検定（t-test等）で有意差を確認
2. **可視化**: レーダーチャート、フロー図作成
3. **Case Study**: 代表的なログを選定し、Figure作成
4. **論文執筆**: 実験セクション（Results, Discussion）

---

**本評価の実行準備が整いました。このREADMEに従って評価を実施してください。**
