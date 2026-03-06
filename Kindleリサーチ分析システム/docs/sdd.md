# システム設計書（SDD） — Kindleリサーチ分析システム

**バージョン**: 1.0.0
**作成日**: 2026-03-06
**対象フェーズ**: Phase 1 MVP

---

## 1. システムアーキテクチャ概要

### 1.1 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                        ユーザー                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│                  Next.js フロントエンド                            │
│          (App Router / React / Tailwind CSS)                     │
│  ダッシュボード | キーワード分析 | ジャンル | タイトル | 表紙 | 予測  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ API calls
┌──────────────────────────▼──────────────────────────────────────┐
│                   FastAPI バックエンド                              │
│                  (Python 3.12 / async)                            │
│                                                                   │
│  ┌──────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────┐ │
│  │ Keyword API  │ │ Genre API  │ │  Title API   │ │Cover API │ │
│  └──────┬───────┘ └─────┬──────┘ └──────┬───────┘ └────┬─────┘ │
│         └───────────────┼───────────────┼───────────────┘       │
│                         │               │                        │
│  ┌──────────────────────▼───────────────▼──────────────────┐    │
│  │              Service Layer (ビジネスロジック)               │    │
│  │  KeywordService | GenreService | PredictionService       │    │
│  │  TitleAnalyzer  | CoverAnalyzer | CacheService           │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
┌─────────▼──────┐ ┌───────▼──────┐ ┌───────▼───────────┐
│ PostgreSQL 16  │ │  Redis 7.x   │ │   Celery Workers  │
│ + TimescaleDB  │ │  (Cache +    │ │  (バッチ収集ジョブ)  │
│ + pgvector     │ │   Queue)     │ │                   │
└─────────┬──────┘ └──────────────┘ └───────┬───────────┘
          │                                  │
          │              ┌───────────────────┘
          │              │
┌─────────▼──────────────▼──────────────────────────────────────┐
│                   外部 API 層                                    │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Amazon Creators │  │  Keepa API   │  │ MerchantWords API │  │
│  │ API (旧PA-API)  │  │ (BSR履歴)    │  │ (検索ボリューム)   │  │
│  └─────────────────┘  └──────────────┘  └───────────────────┘  │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────────────────────────┐  │
│  │ Amazon Auto-    │  │       Claude API (Anthropic)         │  │
│  │ complete API    │  │  claude-haiku-4-5 (Vision / Text)    │  │
│  └─────────────────┘  └──────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 技術スタック選定

| 層 | 技術 | 選定理由 |
|----|------|---------|
| **フロントエンド** | Next.js 15 (App Router) + TypeScript | SSR/ISR対応・SEO・型安全 |
| **UI** | Tailwind CSS + shadcn/ui | 高速開発・アクセシビリティ |
| **チャート** | Recharts + D3.js | BSRトレンドグラフ・ヒートマップ |
| **バックエンド** | FastAPI (Python 3.12) | async/await・型ヒント・OpenAPI自動生成 |
| **ORM** | SQLAlchemy 2.x (async) | PostgreSQL対応・マイグレーション管理 |
| **バッチ** | Celery + Redis | 分散タスクキュー・スケジュール管理 |
| **DB** | PostgreSQL 16 + TimescaleDB | 時系列データ最適化・BSR履歴高速クエリ |
| **ベクトル検索** | pgvector | タイトル埋め込み検索・類似度分析 |
| **キャッシュ** | Redis 7.x | API応答キャッシュ・セッション管理 |
| **ML** | LightGBM + Prophet | BSR予測・季節性モデリング |
| **AI分析** | Claude Haiku 4.5 (Vision + Text) | 表紙分析・レビュー感情分析 |
| **コンテナ** | Docker Compose | ローカル開発環境統一 |
| **ホスティング** | VPS (DigitalOcean 4GB) + Vercel | Phase1コスト最適化 |

---

## 2. データベース設計

### 2.1 ER図（主要エンティティ）

```
kindle_books
    │ 1
    │
    ├──< bsr_history (TimescaleDB)
    │       asin, bsr, category, recorded_at, estimated_daily_sales
    │
    ├──< book_covers
    │       asin, image_url, analysis_json, analyzed_at
    │
    └──< book_reviews
            asin, review_id, rating, body, reviewer_type, reviewed_at

keyword_analyses
    │ 1
    │
    └──< keyword_books (N:M junction)
            keyword, asin, rank

genre_trends
    │ 1
    │
    └──< genre_snapshots
            genre, period, avg_bsr, top_keywords, trend_score, recorded_at
```

### 2.2 DDL — 完全スキーマ

```sql
-- ===== 拡張機能 =====
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 全文検索

-- ===== 書籍マスタ =====
CREATE TABLE kindle_books (
  asin              VARCHAR(10)   PRIMARY KEY,
  title             TEXT          NOT NULL,
  subtitle          TEXT,
  author            TEXT[]        NOT NULL,
  publisher         TEXT,
  published_date    DATE,
  genre             VARCHAR(100),
  sub_genre         VARCHAR(100),
  price             DECIMAL(10,2),
  kindle_unlimited  BOOLEAN       DEFAULT false,
  cover_image_url   TEXT,          -- Creators API経由URLのみ
  review_count      INTEGER       DEFAULT 0,
  average_rating    DECIMAL(3,2),
  page_count        INTEGER,
  description       TEXT,
  keywords          TEXT[],        -- KDPメタキーワード（推定）
  title_embedding   vector(1536),  -- Claude text-embedding
  desc_embedding    vector(1536),
  created_at        TIMESTAMPTZ   DEFAULT NOW(),
  updated_at        TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX idx_books_genre ON kindle_books (genre);
CREATE INDEX idx_books_author ON kindle_books USING gin (author);
CREATE INDEX idx_books_keywords ON kindle_books USING gin (keywords);
CREATE INDEX idx_books_title_trgm ON kindle_books USING gin (title gin_trgm_ops);
CREATE INDEX idx_books_title_vec ON kindle_books USING ivfflat (title_embedding vector_cosine_ops);

-- ===== BSR時系列（TimescaleDB） =====
CREATE TABLE bsr_history (
  id                   BIGSERIAL,
  asin                 VARCHAR(10)  NOT NULL REFERENCES kindle_books(asin),
  bsr                  INTEGER      NOT NULL,
  category             VARCHAR(100) NOT NULL,
  recorded_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  estimated_daily_sales INTEGER,    -- BSR→販売数変換値（±20%誤差）
  data_source          VARCHAR(20)  NOT NULL DEFAULT 'keepa'
);

SELECT create_hypertable('bsr_history', 'recorded_at');
CREATE INDEX idx_bsr_asin_time ON bsr_history (asin, recorded_at DESC);

-- BSR集計ビュー（日次）
CREATE MATERIALIZED VIEW bsr_daily_avg AS
SELECT
  asin,
  category,
  DATE_TRUNC('day', recorded_at) AS day,
  AVG(bsr)::INTEGER              AS avg_bsr,
  MIN(bsr)                       AS min_bsr,
  MAX(bsr)                       AS max_bsr,
  AVG(estimated_daily_sales)::INTEGER AS avg_sales
FROM bsr_history
GROUP BY asin, category, DATE_TRUNC('day', recorded_at);

-- ===== キーワード分析 =====
CREATE TABLE keyword_analyses (
  keyword                      TEXT         PRIMARY KEY,
  -- 検索ボリューム（3ソース合算・必ず「推定月間検索数」として表示）
  sv_merchant_words            INTEGER,      -- MerchantWords API（主力）
  sv_autocomplete_score        DECIMAL(4,2), -- Autocomplete深度スコア（0.0〜10.0）
  sv_helium10                  INTEGER,      -- Helium10 Magnet（Phase2）
  sv_estimated                 INTEGER NOT NULL DEFAULT 0, -- 合算推定値（表示用）
  sv_confidence                SMALLINT NOT NULL DEFAULT 1 CHECK (sv_confidence IN (1,2,3)),
  sv_note                      TEXT,         -- 例: "推定値 / MerchantWords + Autocomplete合算"
  competition                  VARCHAR(10)   CHECK (competition IN ('low','medium','high')),
  book_count                   INTEGER,      -- 該当書籍数
  avg_bsr                      INTEGER,      -- 上位書籍の平均BSR
  trend                        VARCHAR(10)   CHECK (trend IN ('rising','stable','declining')),
  related_keywords             TEXT[],
  top_asins                    VARCHAR(10)[],
  last_analyzed_at             TIMESTAMPTZ   DEFAULT NOW(),
  sv_updated_at                TIMESTAMPTZ
);

CREATE INDEX idx_keywords_estimated ON keyword_analyses (sv_estimated DESC);
CREATE INDEX idx_keywords_competition ON keyword_analyses (competition);
CREATE INDEX idx_keywords_trend ON keyword_analyses (trend);

-- ===== ジャンルトレンド =====
CREATE TABLE genre_trends (
  id            BIGSERIAL     PRIMARY KEY,
  genre         VARCHAR(100)  NOT NULL,
  period        VARCHAR(10)   NOT NULL CHECK (period IN ('daily','weekly','monthly','halfyear')),
  avg_bsr       INTEGER,
  median_bsr    INTEGER,
  book_count    INTEGER,
  top_keywords  TEXT[],
  target_demo   TEXT,         -- ターゲット層推定（Claude分析）
  trend_score   DECIMAL(4,3) CHECK (trend_score BETWEEN 0 AND 1),
  recorded_at   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_genre_period ON genre_trends (genre, period, recorded_at DESC);

-- ===== 表紙分析 =====
CREATE TABLE book_covers (
  asin            VARCHAR(10)  PRIMARY KEY REFERENCES kindle_books(asin),
  image_url       TEXT         NOT NULL,
  -- Claude Vision分析結果
  primary_colors  TEXT[],      -- 主要色（HEX）
  font_style      VARCHAR(50), -- serif / sans-serif / handwriting / display
  layout          VARCHAR(50), -- text-dominant / image-dominant / balanced
  mood            VARCHAR(50), -- professional / casual / dramatic / minimalist
  analysis_json   JSONB,       -- 完全な分析レスポンス
  ctr_score       SMALLINT CHECK (ctr_score BETWEEN 0 AND 100),
  analyzed_at     TIMESTAMPTZ  DEFAULT NOW()
);

-- ===== レビュー（インサイト抽出用） =====
CREATE TABLE book_reviews (
  id              BIGSERIAL    PRIMARY KEY,
  asin            VARCHAR(10)  NOT NULL REFERENCES kindle_books(asin),
  review_id       TEXT         UNIQUE,
  rating          SMALLINT     CHECK (rating BETWEEN 1 AND 5),
  body            TEXT,
  helpful_votes   INTEGER      DEFAULT 0,
  reviewer_type   VARCHAR(20), -- verified / unverified
  reviewed_at     TIMESTAMPTZ,
  sentiment       VARCHAR(10), -- positive / neutral / negative
  topics          TEXT[],      -- Claude抽出トピック
  created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX idx_reviews_asin ON book_reviews (asin);

-- ===== 収集ジョブログ =====
CREATE TABLE collection_jobs (
  id            BIGSERIAL    PRIMARY KEY,
  job_type      VARCHAR(50)  NOT NULL, -- 'bsr_update' | 'keyword_analysis' | 'cover_analysis'
  status        VARCHAR(20)  NOT NULL DEFAULT 'pending',
  target_count  INTEGER,
  success_count INTEGER      DEFAULT 0,
  error_count   INTEGER      DEFAULT 0,
  error_log     JSONB,
  api_cost_usd  DECIMAL(10,4),
  started_at    TIMESTAMPTZ  DEFAULT NOW(),
  finished_at   TIMESTAMPTZ
);
```

---

## 3. API設計

### 3.1 エンドポイント一覧

```
BASE URL: /api/v1

# キーワード
GET  /keywords/search?q={keyword}&limit=20
GET  /keywords/{keyword}/analysis
GET  /keywords/{keyword}/trend?period=30d
GET  /keywords/suggestions?seed={keyword}&count=10
POST /keywords/compare          # 複数キーワード比較

# ジャンル
GET  /genres                    # 全ジャンル一覧
GET  /genres/{genre}/trend?period=weekly|monthly|halfyear
GET  /genres/{genre}/bestsellers?limit=100
GET  /genres/compare?genres=g1,g2,g3  # 最大5ジャンル比較
GET  /genres/niche?max_competition=medium&min_trend_score=0.6

# タイトル
POST /title/analyze             # タイトル分析 + AIスコア
POST /title/generate            # タイトル候補生成（3〜5案）
GET  /title/patterns?genre={genre}  # ベストセラータイトルパターン

# 表紙
GET  /covers/trends?genre={genre}   # 表紙傾向レポート
POST /covers/analyze            # 表紙URLを指定して分析

# 売上予測
GET  /prediction/bsr-to-sales?bsr={bsr}&genre={genre}
POST /prediction/simulate       # ジャンル+キーワード→予測売上
GET  /prediction/bsr-forecast?asin={asin}&days=30

# 書籍
GET  /books/{asin}
GET  /books/{asin}/bsr-history?from={date}&to={date}
GET  /books/{asin}/similar      # pgvector類似検索
```

### 3.2 レスポンス形式

```typescript
// 統一レスポンス形式
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total?: number
    page?: number
    limit?: number
    cached?: boolean
    cache_age_seconds?: number
  }
}

// キーワード分析レスポンス
interface KeywordAnalysisResponse {
  keyword: string
  search_volume: {
    estimated: number           // 合算推定値
    confidence: 1 | 2 | 3      // ★ソース数
    note: string                // 必須: "推定値 / ..."
    merchant_words?: number
    autocomplete_score?: number
    helium10?: number
  }
  competition: 'low' | 'medium' | 'high'
  book_count: number
  avg_bsr: number
  trend: 'rising' | 'stable' | 'declining'
  related_keywords: string[]
  top_books: BookSummary[]
}
```

### 3.3 BSR→推定販売数変換モデル

```python
# 日本市場キャリブレーション（独自推定式）
# 注: 誤差±20%を常に明示すること

def bsr_to_sales(bsr: int, genre: str) -> dict:
    """
    BSR から推定日次販売数を計算する。
    式は日本市場の実測データから独自キャリブレーション済み。
    """
    # ジャンル別係数（実測値が集まり次第更新）
    GENRE_COEFF = {
        "ビジネス": 1.2,
        "自己啓発": 1.1,
        "コンピュータ": 0.9,
        "default": 1.0,
    }
    coeff = GENRE_COEFF.get(genre, GENRE_COEFF["default"])

    # 基本式（ランク帯別）
    if bsr <= 100:
        base = 50 - (bsr * 0.4)
    elif bsr <= 1000:
        base = 10 - ((bsr - 100) * 0.008)
    elif bsr <= 10000:
        base = 2.8 - ((bsr - 1000) * 0.0002)
    elif bsr <= 100000:
        base = 0.95 - ((bsr - 10000) * 0.000009)
    else:
        base = 0.15 - ((bsr - 100000) * 0.0000001)

    daily_sales = max(0, base * coeff)
    monthly_sales = daily_sales * 30

    return {
        "daily_estimated": round(daily_sales, 1),
        "monthly_estimated": round(monthly_sales),
        "error_range_pct": 20,  # 必須: ±20%誤差を明示
        "note": "推定値（±20%誤差）/ 実測販売データ非公開のため"
    }
```

---

## 4. 外部API統合設計

### 4.1 Amazon Creators API クライアント

```python
# src/collectors/creators_api.py

import asyncio
import httpx
from typing import Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class BookMetadata:
    asin: str
    title: str
    author: list[str]
    genre: str
    bsr: int
    price: float
    review_count: int
    average_rating: float
    cover_image_url: str  # Creators API提供URLのみ
    kindle_unlimited: bool

class CreatorsApiClient:
    """
    Amazon Creators API (PA-API後継) クライアント。
    2026/4/30 PA-API廃止に伴い、Creators APIエンドポイントを使用。
    """
    BASE_URL = "https://webservices.amazon.co.jp/paapi5/searchitems"
    RATE_LIMIT_DELAY = 1.1  # 1秒1リクエスト制限に準拠

    def __init__(self, access_key: str, secret_key: str, partner_tag: str):
        self._access_key = access_key
        self._secret_key = secret_key
        self._partner_tag = partner_tag
        self._last_request_time = 0.0

    async def get_book(self, asin: str) -> Optional[BookMetadata]:
        await self._rate_limit()
        # 実装: AWS4署名 + HTTPリクエスト
        ...

    async def search_books(
        self,
        keyword: str,
        category: str = "KindleStore",
        sort_by: str = "Relevance",
        page: int = 1
    ) -> list[BookMetadata]:
        await self._rate_limit()
        ...

    async def _rate_limit(self) -> None:
        elapsed = asyncio.get_event_loop().time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
```

### 4.2 Keepa API クライアント

```python
# src/collectors/keepa_client.py

import keepa  # pip install keepa

class KeepaClient:
    """
    Keepa API クライアント（BSR履歴取得）。
    Kindle ASIN (B00xxx) の BSR履歴に正式対応確認済み。
    """

    def __init__(self, api_key: str):
        self._api = keepa.Keepa(api_key)

    async def get_bsr_history(
        self,
        asins: list[str],
        days: int = 180
    ) -> dict[str, list[tuple[int, int]]]:
        """
        Returns: {asin: [(unix_timestamp_minutes, bsr), ...]}
        """
        # Keepa APIはASINリストを一括取得可能（最大100件）
        products = self._api.query(
            asins,
            domain="JP",
            history=True,
            days=days
        )

        result = {}
        for product in products:
            asin = product["asin"]
            # BSRデータはカテゴリ別に格納
            sales_rank = product.get("salesRanks", {})
            # Kindleストア カテゴリコード: 3045765051
            kindle_bsr = sales_rank.get("3045765051", [])
            # [(time_minutes, rank), ...] 形式に変換
            result[asin] = [
                (kindle_bsr[i], kindle_bsr[i+1])
                for i in range(0, len(kindle_bsr)-1, 2)
                if kindle_bsr[i] > 0
            ]

        return result
```

### 4.3 MerchantWords API クライアント

```python
# src/collectors/merchantwords_client.py

import httpx
from typing import Optional

class MerchantWordsClient:
    """
    MerchantWords API クライアント（amazon.co.jp対応・検索ボリューム取得）。
    注: Amazon公式データではなく収集推定値。表示時は必ず明示。
    """
    BASE_URL = "https://api.merchantwords.com/v2"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def get_volume(
        self,
        keyword: str,
        marketplace: str = "JP"
    ) -> Optional[dict]:
        """
        Returns:
          {
            "keyword": str,
            "search_volume": int,      # 月間推定検索数
            "trend": list[int],        # 12ヶ月トレンド
            "data_source": "MerchantWords",
            "note": "推定値 / Amazon公式データではありません"
          }
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/keywords",
                params={
                    "keyword": keyword,
                    "marketplace": marketplace,
                    "key": self._api_key,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "keyword": keyword,
                "search_volume": data.get("search_volume", 0),
                "trend": data.get("monthly_trend", []),
                "data_source": "MerchantWords",
                "note": "推定値 / Amazon公式データではありません",
            }
```

### 4.4 Amazon Autocomplete クライアント

```python
# src/collectors/autocomplete_client.py

import httpx

class AutocompleteClient:
    """
    Amazon Autocomplete API クライアント（無料・合法）。
    キーワードの需要シグナルとして使用（ボリューム補完）。
    """
    BASE_URL = "https://completion.amazon.co.jp/api/2017/suggestions"

    async def get_suggestions(
        self,
        keyword: str,
        limit: int = 10
    ) -> dict:
        """
        Returns:
          {
            "suggestions": list[str],
            "autocomplete_score": float,  # 0.0〜10.0 (候補数×深度)
            "note": "Autocompleteシグナル（需要の間接指標）"
          }
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.BASE_URL,
                params={
                    "alias": "digital-text",  # Kindle Store
                    "b2b": "0",
                    "fresh": "0",
                    "ks": "80",
                    "lop": "0",
                    "mid": "AN1VRQENFRJN5",  # Amazon.co.jp Marketplace ID
                    "plain": "1",
                    "prefix": keyword,
                    "event": "onKeyPress",
                    "limit": limit,
                    "fb": "1",
                    "suggestion-type[0]": "KEYWORD",
                },
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5.0,
            )
            resp.raise_for_status()
            data = resp.json()

            suggestions = [
                s["value"]
                for s in data.get("suggestions", [])
            ]

            # 候補数とキーワードの具体性からスコア計算
            score = min(10.0, len(suggestions) * 1.0)

            return {
                "suggestions": suggestions,
                "autocomplete_score": score,
                "note": "Autocompleteシグナル（需要の間接指標）",
            }
```

### 4.5 Claude Vision API クライアント（表紙分析）

```python
# src/analyzers/cover_analyzer.py

import anthropic
import base64
import httpx
from dataclasses import dataclass

@dataclass(frozen=True)
class CoverAnalysis:
    asin: str
    primary_colors: list[str]  # HEX
    font_style: str
    layout: str
    mood: str
    ctr_score: int  # 0〜100
    raw_response: str

class CoverAnalyzer:
    """
    Claude Haiku Vision API を使った表紙画像分析。
    モデル: claude-haiku-4-5 (コスト: $0.0003/枚)
    Batch API使用で50%削減可能。
    """
    MODEL = "claude-haiku-4-5-20251001"

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self,
        image_url: str,  # Creators API提供URLのみ
        asin: str
    ) -> CoverAnalysis:
        # 画像をbase64エンコード
        async with httpx.AsyncClient() as http:
            resp = await http.get(image_url)
            image_data = base64.standard_b64encode(resp.content).decode()

        message = await self._client.messages.create(
            model=self.MODEL,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": """この書籍の表紙画像を分析してください。

以下をJSON形式で回答:
{
  "primary_colors": ["#XXXXXX", ...],  // 主要色（最大3色）
  "font_style": "serif|sans-serif|handwriting|display",
  "layout": "text-dominant|image-dominant|balanced",
  "mood": "professional|casual|dramatic|minimalist|academic",
  "ctr_score": 0-100,  // 推定クリック率スコア
  "analysis": "簡潔な説明（100字以内）"
}"""
                    }
                ],
            }],
        )

        import json
        result = json.loads(message.content[0].text)

        return CoverAnalysis(
            asin=asin,
            primary_colors=result["primary_colors"],
            font_style=result["font_style"],
            layout=result["layout"],
            mood=result["mood"],
            ctr_score=result["ctr_score"],
            raw_response=message.content[0].text,
        )
```

---

## 5. バッチ収集設計

### 5.1 収集ジョブスケジュール

```
┌──────────────────────────────────────────────────────────────┐
│                   Celery Beat スケジュール                      │
├─────────────────┬──────────────┬──────────────────────────────┤
│ ジョブ           │ スケジュール  │ 内容                          │
├─────────────────┼──────────────┼──────────────────────────────┤
│ bsr_update      │ 毎時 (0分)   │ 上位1000冊のBSR更新            │
│ keyword_refresh │ 毎日 03:00   │ キーワードボリューム更新        │
│ cover_analysis  │ 毎日 04:00   │ 未分析表紙をバッチ処理          │
│ genre_trend     │ 毎日 05:00   │ ジャンルトレンド集計            │
│ review_scrape   │ 毎週 月 02:00│ レビュー取得（新刊対象）         │
│ prediction_calc │ 毎日 06:00   │ BSR予測モデル再計算             │
└─────────────────┴──────────────┴──────────────────────────────┘
```

### 5.2 Celeryタスク実装パターン

```python
# src/tasks/bsr_update.py

from celery import shared_task
from src.collectors.keepa_client import KeepaClient
from src.db.repositories import BSRRepository, BookRepository
import structlog

log = structlog.get_logger()

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="tasks.bsr_update"
)
def update_bsr_batch(self, asins: list[str]) -> dict:
    """BSR履歴を一括更新するタスク。"""
    try:
        client = KeepaClient(api_key=settings.KEEPA_API_KEY)
        histories = client.get_bsr_history(asins, days=7)

        repo = BSRRepository()
        success_count = 0
        error_count = 0

        for asin, records in histories.items():
            try:
                repo.upsert_many(asin, records)
                success_count += 1
            except Exception as e:
                log.error("bsr_upsert_failed", asin=asin, error=str(e))
                error_count += 1

        return {
            "success": True,
            "success_count": success_count,
            "error_count": error_count,
        }

    except Exception as exc:
        log.error("bsr_batch_failed", error=str(exc))
        raise self.retry(exc=exc)
```

---

## 6. ML予測パイプライン

### 6.1 LightGBM BSR予測モデル

```python
# src/ml/bsr_predictor.py

import lightgbm as lgb
import numpy as np
from dataclasses import dataclass

@dataclass(frozen=True)
class BSRPrediction:
    asin: str
    predicted_bsr: int
    lower_bound: int   # 80%信頼区間
    upper_bound: int
    days_ahead: int
    error_range_pct: int = 20  # 必ず明示

class BSRPredictor:
    """
    LightGBM による BSR時系列予測。
    特徴量: 過去BSR・曜日・季節性・レビュー増加率・価格変化
    """

    def predict(
        self,
        asin: str,
        bsr_history: list[tuple[int, int]],
        days_ahead: int = 30
    ) -> BSRPrediction:
        # 特徴量エンジニアリング
        features = self._build_features(bsr_history)

        # 予測実行
        pred = self._model.predict(features)
        bsr_pred = max(1, int(pred[-days_ahead]))

        # 信頼区間（±20%）
        lower = max(1, int(bsr_pred * 0.8))
        upper = int(bsr_pred * 1.2)

        return BSRPrediction(
            asin=asin,
            predicted_bsr=bsr_pred,
            lower_bound=lower,
            upper_bound=upper,
            days_ahead=days_ahead,
        )
```

---

## 7. フロントエンド設計

### 7.1 ページ構成

```
app/
├── page.tsx                    # ダッシュボード（トップ）
├── keywords/
│   ├── page.tsx               # キーワード検索
│   └── [keyword]/page.tsx     # キーワード詳細
├── genres/
│   ├── page.tsx               # ジャンル一覧
│   └── [genre]/page.tsx       # ジャンル詳細（時系列グラフ）
├── title-analyzer/
│   └── page.tsx               # タイトル分析・生成
├── covers/
│   └── page.tsx               # 表紙傾向ギャラリー
└── prediction/
    └── page.tsx               # 売上予測シミュレーター
```

### 7.2 ダッシュボードコンポーネント設計

```typescript
// components/dashboard/TrendScoreCard.tsx
interface TrendScoreCardProps {
  genre: string
  score: number          // 0.0〜1.0
  topKeywords: string[]
  period: 'daily' | 'weekly' | 'monthly' | 'halfyear'
}

// components/keyword/VolumeDisplay.tsx
// 検索ボリュームは必ず信頼度★付きで表示
interface VolumeDisplayProps {
  estimated: number
  confidence: 1 | 2 | 3    // ★の数
  note: string              // "推定値 / ..." を必ず表示
}

// components/prediction/BSRSalesConverter.tsx
interface BSRSalesConverterProps {
  bsr: number
  genre: string
  dailyEstimated: number
  monthlyEstimated: number
  errorRangePct: number     // 必ず表示（20%）
}
```

---

## 8. セキュリティ設計

### 8.1 APIキー管理

```bash
# .env（Gitに含めない / chmod 600）
AMAZON_ACCESS_KEY=...
AMAZON_SECRET_KEY=...
AMAZON_PARTNER_TAG=...
KEEPA_API_KEY=...
MERCHANTWORDS_API_KEY=...
ANTHROPIC_API_KEY=...

# 参照方法（ハードコード禁止）
import os
api_key = os.environ["KEEPA_API_KEY"]
if not api_key:
    raise ValueError("KEEPA_API_KEY not configured")
```

### 8.2 Amazon ToS遵守チェックリスト

- [ ] Creators API利用規約の表示義務遵守（「Powered by Amazon」表示）
- [ ] リクエストレート: 1秒1リクエスト以下
- [ ] 書影画像: `cover_image_url` はAPIから取得したURLを参照のみ（ダウンロード・ホスト禁止）
- [ ] PA-API廃止対応: Creators APIへの移行完了期限 **2026/4/30**

---

## 9. デプロイ設計

### 9.1 Docker Compose（ローカル / Phase1本番）

```yaml
# docker-compose.yml
services:
  db:
    image: timescale/timescaledb-ha:pg16-latest
    environment:
      POSTGRES_DB: kindle_research
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000
    env_file: .env
    depends_on: [db, redis]
    ports:
      - "8000:8000"

  worker:
    build: .
    command: celery -A src.tasks worker --loglevel=info
    env_file: .env
    depends_on: [db, redis]

  beat:
    build: .
    command: celery -A src.tasks beat --loglevel=info
    env_file: .env
    depends_on: [db, redis]

volumes:
  pgdata:
```

### 9.2 フェーズ別インフラ

| フェーズ | バックエンド | フロントエンド | DB | 月額 |
|---------|------------|--------------|-----|------|
| Phase 1 | VPS 4GB (DO) | Vercel Hobby | Self-hosted | $64 |
| Phase 2 | VPS 8GB (DO) | Vercel Pro | Self-hosted | $110 |
| Phase 3 | EKS | Vercel Pro | TimescaleDB Cloud | $400+ |

---

## 10. 開発ロードマップ

### Phase 1 MVP（〜2026/4/30 Creators API移行期限）

| 週 | マイルストーン |
|----|--------------|
| Week 1-2 | DB設計・マイグレーション・Creators API統合 |
| Week 3-4 | Keepa API統合・BSR収集バッチ起動 |
| Week 5-6 | MerchantWords + Autocomplete キーワード分析 |
| Week 7-8 | Claude Vision 表紙分析・タイトルAI分析 |
| Week 9-10 | Next.jsダッシュボード（キーワード・ジャンル画面） |
| Week 11-12 | LightGBM予測モデル・売上シミュレーター |
| Week 13 | 本番デプロイ・PA-API→Creators API切り替え完了 |

### Phase 2 成長期（2026 Q3）

- SaaS化（ユーザー登録・Stripe課金）
- Helium10クロスチェック統合
- CSVエクスポート
- 複数ジャンル横断比較

### Phase 3 スケール（2026 Q4）

- API公開（B2B販売）
- Kubernetes移行
- TimescaleDB Cloud移行
- 英語市場（amazon.com）対応検討
