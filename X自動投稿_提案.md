# X自動投稿システム 設計提案書

**作成日**: 2026-03-05
**目的**: キーワード指定 → 最新情報収集 → X投稿文生成 → 1日3回自動投稿

---

## システム概要

```
[キーワード設定]
      ↓
[情報収集エンジン]
  Grok-4 / Tavily / NewsAPI / Exa
      ↓
[投稿文生成エンジン]
  Claude API (Haiku 4.5)
      ↓
[スケジューラー]
  cron / n8n / GitHub Actions
      ↓
[X API (v2) 投稿]
```

---

## 1. ジャンル・キーワード指定

### 設定ファイル形式（config.yaml）

```yaml
topics:
  - keyword: "生成AI"
    expand:
      - "LLM最新動向"
      - "AI エージェント"
      - "OpenAI Anthropic Google"
    language: "en,ja"
    region: "US,EU,JP"
    tone: "情報提供・まとめ系"

  - keyword: "Web3"
    expand:
      - "DeFi NFT Blockchain"
      - "crypto regulation"
    tone: "解説系"

post_schedule:
  times:
    - "08:00"   # 朝
    - "12:00"   # 昼
    - "20:00"   # 夜
  timezone: "Asia/Tokyo"
```

### キーワード拡張ロジック

- 指定キーワードから関連語をAIが自動展開
- 英語・日本語の両方で検索
- 海外情報（US/EU）を優先的に収集

---

## 2. 情報収集エンジン

### 使用API（優先順位順）

| API | 用途 | コスト |
|-----|------|--------|
| Grok-4 (xAI) | リアルタイムX/Web検索 | $0.01〜/リクエスト |
| Tavily | AI特化検索・要約 | 無料枠1,000回/月 |
| NewsAPI | 最新ニュース収集 | 無料枠100回/日 |
| Exa | セマンティック検索 | 無料枠1,000回/月 |

### 収集フロー

```
1. キーワードから英語・日本語クエリを生成
2. Grok-4でX上のトレンド投稿を取得
3. Tavily/NewsAPIで海外最新ニュースを収集
4. 重複排除・品質フィルタリング
5. 上位3〜5件の情報を選定
```

### 収集対象

- X（旧Twitter）のトレンド投稿・著名人発言
- 海外テックメディア（TechCrunch, Wired, The Verge等）
- 論文・研究発表（Arxiv等）
- 経済・市場データ

---

## 3. 投稿文生成エンジン

### 投稿パターン（1日3投稿の構成案）

| 投稿 | 時間 | タイプ | 内容 |
|------|------|--------|------|
| 1本目 | 08:00 | ニュースまとめ | 海外最新情報を日本語で要約 |
| 2本目 | 12:00 | 深掘り解説 | 1本目のトピックをさらに詳しく |
| 3本目 | 20:00 | 考察・意見 | トレンドに対する洞察・未来予測 |

### 生成プロンプト例

```
あなたはXのインフルエンサーです。
以下の最新情報をもとに、日本語のX投稿文を作成してください。

【収集情報】
{collected_news}

【条件】
- 140文字以内（日本語）
- 冒頭に絵文字1つ
- 海外情報を日本語でわかりやすく翻訳・要約
- ハッシュタグ2〜3個を末尾に追加
- 「なぜ重要か」を必ず含める

【トーン】
{tone}（情報提供系 / 解説系 / 考察系）
```

### 生成モデル

- **Claude Haiku 4.5**（コスト効率最高）
- 1投稿あたり約 $0.001 以下
- 月90投稿（3投稿×30日）= 約$0.09

---

## 4. 自動投稿実行

### X API v2 の要件

| 項目 | 内容 |
|------|------|
| 必要なプラン | Basic（$100/月）以上 ※無料プランは読み取り専用 |
| 投稿エンドポイント | `POST /2/tweets` |
| レート制限 | 17投稿/15分（Basicプラン） |
| 必要なキー | API Key, API Secret, Access Token, Access Secret |

### スケジューラー選択肢

#### 案A: cron（最シンプル）
```bash
# crontab設定
0 8  * * * python3 /path/to/post.py --time=morning
0 12 * * * python3 /path/to/post.py --time=noon
0 20 * * * python3 /path/to/post.py --time=evening
```
- コスト: 無料（自前サーバー）
- 難易度: 低

#### 案B: GitHub Actions（無料・クラウド）
```yaml
on:
  schedule:
    - cron: '0 23 * * *'  # UTC 23:00 = JST 8:00
    - cron: '0 3 * * *'   # UTC 3:00  = JST 12:00
    - cron: '0 11 * * *'  # UTC 11:00 = JST 20:00
```
- コスト: 無料（パブリックリポジトリ）
- 難易度: 低〜中

#### 案C: n8n（GUI操作・ノーコード）
- ビジュアルでワークフロー設定
- X連携ノードが標準搭載
- コスト: セルフホスト無料 / クラウド$20/月〜

---

## 5. システム構成（推奨）

### ファイル構成

```
x-auto-poster/
├── config/
│   └── topics.yaml          # キーワード・スケジュール設定
├── src/
│   ├── collector.py         # 情報収集（Grok-4/Tavily/NewsAPI）
│   ├── generator.py         # 投稿文生成（Claude Haiku）
│   ├── poster.py            # X API投稿
│   └── scheduler.py         # スケジュール管理
├── logs/
│   └── posts.json           # 投稿履歴（重複防止）
├── .env                     # APIキー管理
└── main.py                  # エントリーポイント
```

### .env に必要なキー

```env
# 情報収集
XAI_API_KEY=xai-xxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxx
NEWSAPI_KEY=xxxxxxxx

# 投稿文生成
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# X API投稿
X_API_KEY=xxxxxxxx
X_API_SECRET=xxxxxxxx
X_ACCESS_TOKEN=xxxxxxxx
X_ACCESS_SECRET=xxxxxxxx
```

---

## 6. 月間コスト試算

| 項目 | 月間コスト |
|------|-----------|
| X API Basic | $100 |
| Claude Haiku（90投稿） | $0.10 |
| Grok-4（情報収集90回） | $1〜3 |
| Tavily（無料枠内） | $0 |
| NewsAPI（無料枠内） | $0 |
| サーバー（GitHub Actions） | $0 |
| **合計** | **約$101〜103/月** |

> 最大のコストはX APIのBasicプラン($100/月)

---

## 7. 実装ロードマップ

### Phase 1（3日）: 基盤構築
- [ ] X API申請・キー取得
- [ ] 情報収集スクリプト作成（collector.py）
- [ ] 手動テスト投稿

### Phase 2（3日）: 自動化
- [ ] 投稿文生成スクリプト作成（generator.py）
- [ ] スケジューラー設定（GitHub Actions or cron）
- [ ] 投稿履歴管理（重複防止）

### Phase 3（2日）: 品質向上
- [ ] 投稿品質チェック機能
- [ ] NG ワードフィルター
- [ ] ログ・モニタリング

---

## 8. リスクと対策

| リスク | 対策 |
|--------|------|
| X API BANリスク | レート制限を厳守、自然な投稿間隔を設定 |
| 品質の低い投稿 | 生成後に品質スコアリング、閾値以下は再生成 |
| 同じ内容の繰り返し | 投稿履歴DBで重複チェック |
| X API料金高騰 | Buffer/Hootsuite等の代替投稿ツールを検討 |
| 情報の正確性 | 複数ソースでクロス検証、不確実な情報はスキップ |

---

## 9. まず始めるべきステップ

1. **X Developer Portal** でAPIキー申請（Basicプラン $100/月）
2. **Anthropic API** でClaude Haikuのキー取得（無料枠あり）
3. `collector.py` → `generator.py` → `poster.py` の順に実装
4. GitHub Actionsでスケジュール自動化

---

*作成日: 2026-03-05*
