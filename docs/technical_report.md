# 4. Proposed System Implementation

本章では、構築した「深層アブダクション・ナッジ生成システム」の実装詳細について述べる。本システムは、ユーザーの表面的な発話から潜在的な意図（Deep Intent）を推論し、行動変容を促すナッジを生成するために、自律エージェント群が協調して動作するアーキテクチャを採用している。

## 4.1 System Overview
我々は、従来の線形的な処理フローではなく、**「議長（Controller）」を中心としたスター型トポロジー**を採用した自律エージェントシステムを実装した。
実装には `LangGraph` を使用し、エージェント間の対話、記憶の保持、および循環的な推論プロセス（ループ）を状態遷移グラフとして定義している。

システムは以下の主要コンポーネントで構成される：

```mermaid
graph TD;
    Input[Input Processor] --> Chair[Profiler Chair];
    Chair -- "Need Intuition?" --> Validator[Witness (COMET)];
    Validator --> Chair;
    Chair -- "Need Validation?" --> Explorer[Explorer Agent (Google Search)];
    Explorer --> Chair;
    Chair -- "TENTATIVE Conclusion" --> Critic[Critic Agent];
    Critic -- "REJECT (Loop)" --> Chair;
    Critic -- "APPROVE" --> Memory[Memory Node (PKG Write)];
    Memory --> Nudge[Nudge Agent];
```

1.  **Profiler Chair (議長)**: 推論プロセス全体を指揮するメタ認知エージェント。
2.  **Specialized Tools**: 直感（System 1）と論理（System 2）を担当するサブエージェント群。
3.  **Dynamic Loop**: 証拠が不足していると判断した場合、自律的に調査を継続するフィードバックループ。

このアーキテクチャにより、複雑なユーザーの文脈に対しても、単一のプロンプト処理では不可能な深層的な推論が可能となる。

## 4.2 Knowledge Graph & GraphRAG
本システムの中核には、ユーザー理解の深化とエージェント間の情報統一を目的とした **Personal Knowledge Graph (PKG)** が存在する。

### データの共有と統一 (Information Unification)
PKGは、各エージェントがバラバラに動作するのではなく、共通の「ユーザー像」に基づいて推論を行うための基盤である。
システムは以下のデータをグラフに格納する：
*   **Static Profile**: 属性（例：エンジニア、京都好き）。
*   **Active Context**: ユーザーの現在の発話（Active Node）。
*   **Evidence Log**: 推論過程で得られた全ての証拠（COMETの直感、検索結果）。
*   **Latent Needs**: 最終的に特定された深層意図（Deep Intent）。

### Continuous Update (連続的な更新)
本実装の特徴は、議論の結論だけでなく、**プロセス全体をリアルタイムに記録**する点にある。
*   `Input Processor` が入力を受け取った瞬間。
*   `Witness (COMET)` が直感的推論を行った瞬間。
*   `Explorer` が外部検索を行った瞬間。
これら全てのタイミングで即座に PKG への書き込みが行われる（`store_evidence`）。これにより、エージェントは常に最新の議論状態を共有できる。

### GraphRAGによる推論支援
議長エージェント（Chair）は、意思決定の際に **GraphRAG (Retrieval-Augmented Generation)** を用いて PKG を参照する。
単にユーザーの属性を見るだけでなく、**「過去にどのようなDeep Intentを持っていたか」**や**「現時点での議論ログ（Evidence Log）」**をコンテキストとして取り込むことで、文脈に即した適切な指示（ツール呼び出し）を行うことが可能となっている。

## 4.3 Abductive Reasoning (Abduction)
ユーザーの潜在的な意図を仮説形成（Abduction）するために、二重過程理論に基づいた推論エンジンを実装した。

### Dual-Process Tools
1.  **System 1 (Witness Agent)**:
    *   **モデル**: `atomic2020` (COMET)
    *   **役割**: ユーザーの発話から、明示されていない「願望（xWant）」や「意図（xIntent）」を常識推論によって補完する。これは人間の「直感」に相当する。
2.  **System 2 (Explorer Agent)**:
    *   **モデル**: Google Custom Search (RAG)
    *   **役割**: 直感を裏付けるための類似事例や解決策を外部知識から検索する。これは人間の「分析・検証」に相当する。

### The Chair Controller (議長による制御)
推論は一方通行ではなく、**Profiler Chair** による動的な制御下で行われる。
*   **判断ロジック**: 議長は現在の証拠状況を評価し、「直感が足りない（Call COMET）」「裏付けが必要（Call Explorer）」「結論が出た（Finalize）」のいずれかを決定する。
*   **History-Awareness**: 無限ループを防ぐため、議長は自身のアクション履歴（History）を認識しており、「同じ調査を繰り返さない」よう自律的に戦略を変更する。

## 4.4 Behavioral Nudge Generation
アブダクションによって特定された `Deep Intent` （例：「雨でも京都を楽しみたい」）に基づき、最終的な行動変容アプローチを生成する。

### EAST Frameworkの適用
**Nudge Agent** は、Deep Intent を入力として受け取り、行動経済学の **EASTフレームワーク** に基づいて介入を設計する。
*   **Easy (かんたん)**: 実行のハードルを下げる（例：予約不要の場所を提案）。
*   **Attractive (魅力的)**: 感情に訴える（例：「雨の庭園の情緒」を強調）。
*   **Social (社会的)**: 他者の行動を示す（例：「通な楽しみ方」として紹介）。
*   **Timely (タイムリー)**: 今すぐできることを提示。

このプロセスにより、単なる「正論」ではなく、ユーザーが自発的に行動したくなるような「ナッジ」が出力される。
