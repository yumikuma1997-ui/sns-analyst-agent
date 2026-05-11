# TikTok Analysis Tool

ローカルで手動入力データを読み込み、TikTok アカウントの分析レポートを Markdown で生成する CLI ツールです。

基本は、ユーザーが手動で保存した CSV / JSON を入力として扱います。追加のPoC機能として、TikTok公式Display APIを使った自アカウント公開動画の取得にも対応しています。非公式スクレイピング、自動ログイン、自動投稿、自動エンゲージメント操作は扱いません。

## できること

- アカウント基本情報、投稿データ、手動調査したトレンド、参考アカウントを読み込み
- 競合・参考アカウントの投稿単位データを読み込み、自アカウントとの差分を整理
- 投稿ごとの KPI を計算
- 伸びた投稿 / 伸びなかった投稿の傾向を整理
- 投稿習慣、コンテンツ設計、トレンド適合、競合情報を分析
- 30日間の運用プラン、動画案、KPI設計、仮説検証リスト、改善バックログを Markdown 出力
- 欠損値や 0 再生でもエラーにせず、「データ不足」として扱う
- TikTok公式OAuth / Video List APIで自アカウント公開動画を取得し、分析用CSVへ正規化
- 任意で外部LLM APIを使い、ローカル入力データだけを根拠に定性分析を追加

## 構成

```text
tiktok-analysis-tool/
  README.md
  requirements.txt
  data/
    account_profile.sample.json
    posts.sample.csv
    trends.sample.json
    competitors.sample.json
    competitor_posts.sample.csv
  reports/
    .gitkeep
  src/
    main.py
    tiktok_api.py
    loaders.py
    metrics.py
    analyzer.py
    report_generator.py
    models.py
    utils.py
  tests/
    test_metrics.py
    test_report_generator.py
    test_tiktok_api.py
```

## セットアップ

Python 3.10 以上を想定しています。外部パッケージは不要です。

```powershell
python --version
```

## サンプル実行

```powershell
python src/main.py `
  --account data/account_profile.sample.json `
  --posts data/posts.sample.csv `
  --trends data/trends.sample.json `
  --competitors data/competitors.sample.json `
  --competitor-posts data/competitor_posts.sample.csv `
  --output reports/sample_report.md
```

出力先:

```text
reports/sample_report.md
```

サブコマンド形式でも同じ処理を実行できます。

```powershell
python src/main.py report `
  --account data/account_profile.sample.json `
  --posts data/posts.sample.csv `
  --trends data/trends.sample.json `
  --competitors data/competitors.sample.json `
  --competitor-posts data/competitor_posts.sample.csv `
  --output reports/sample_report.md
```

## TikTok公式API PoC

この機能は自分のTikTokアカウントをOAuthで認可し、公式Display APIの範囲で公開動画一覧を取得するためのものです。TikTok Studio相当の平均視聴時間、完了率、保存数、流入元などは自動取得しません。

### 1. 認可URLを生成

```powershell
python src/main.py tiktok auth-url `
  --client-key YOUR_CLIENT_KEY `
  --redirect-uri http://127.0.0.1:8765/callback `
  --state local-test
```

表示されたURLをブラウザで開き、TikTokで認可します。ローカルPoCでは、callbackで得た `code` を次のコマンドに渡します。

### 2. tokenを保存

```powershell
python src/main.py tiktok exchange-token `
  --client-key YOUR_CLIENT_KEY `
  --client-secret YOUR_CLIENT_SECRET `
  --redirect-uri http://127.0.0.1:8765/callback `
  --code AUTHORIZATION_CODE
```

保存先は既定で `data/tiktok_tokens.local.json` です。このファイルは `.gitignore` 対象です。

### 3. tokenを更新

```powershell
python src/main.py tiktok refresh-token `
  --client-key YOUR_CLIENT_KEY `
  --client-secret YOUR_CLIENT_SECRET
```

### 4. 自アカウント情報を取得

```powershell
python src/main.py tiktok fetch-user `
  --output data/tiktok_user.raw.json
```

`user.info.stats` scopeが承認されている場合は、フォロワー数などのプロフィール統計も取得対象にできます。scope未承認のfieldは取得できない可能性があります。

### 5. 公開動画一覧を取得

```powershell
python src/main.py tiktok fetch-videos `
  --max-count 20 `
  --max-pages 5 `
  --output data/tiktok_videos.raw.json
```

### 6. 分析用CSVへ正規化

```powershell
python src/main.py tiktok normalize-videos `
  --input data/tiktok_videos.raw.json `
  --output data/tiktok_videos.normalized.csv
```

このCSVは既存の `--posts` 入力として使えます。

```powershell
python src/main.py report `
  --posts data/tiktok_videos.normalized.csv `
  --output reports/tiktok_api_report.md
```

## 自分のデータで実行する

サンプルファイルをコピーして編集してください。

- `data/account_profile.sample.json`: アカウント基本情報
- `data/posts.sample.csv`: 投稿ごとの実績
- `data/trends.sample.json`: 手動で調べたトレンド
- `data/competitors.sample.json`: 参考アカウント
- `data/competitor_posts.sample.csv`: 競合・参考アカウントの投稿単位メモ
- `data/tiktok_videos.normalized.csv`: TikTok公式APIから取得した動画一覧の正規化CSV

CSV は英語キーと一部日本語キーに対応しています。最低限、`date`, `title`, `views` があると分析しやすくなります。再生数が未入力または 0 の投稿は、率の計算では「データ不足」として扱います。

## 安全な競合分析の方針

このツールはTikTokページをスクレイピングしません。競合分析は、次のような安全な入力だけを対象にします。

- ユーザーがTikTokアプリやブラウザで目視確認した公開情報のメモ
- TikTok Studioや分析画面など、ユーザーが正当に確認できる自アカウント情報
- TikTok Creative Centerなどでユーザーが手動調査したトレンド情報
- 参考アカウントの投稿URL、冒頭フック、構成、ハッシュタグ、公開数値を手動でCSV化したもの
- 許可済みの公式APIや正規エクスポートから得たデータ

実装しないもの:

- TikTokへの自動ログイン
- ログイン後画面や投稿ページの自動巡回
- スクレイピングによるデータ収集
- 自動投稿、自動いいね、自動フォロー、自動コメント

## 公式APIで自動取得しない指標

次の指標は、公式Display APIのVideo Objectでは確認できないため、Studioを見て手動CSVで補完してください。

- 保存数
- 平均視聴時間
- 完了率
- フォロワー増加数
- プロフィール閲覧数
- 視聴者属性
- 流入元
- 日別推移

## 任意の外部LLM分析

LLM連携は任意です。APIキーを設定しない場合、ローカルのルールベース分析だけで動きます。

OpenAI Responses APIを使う例:

```powershell
$env:OPENAI_API_KEY="your_api_key"
python src/main.py `
  --account data/account_profile.sample.json `
  --posts data/posts.sample.csv `
  --trends data/trends.sample.json `
  --competitors data/competitors.sample.json `
  --competitor-posts data/competitor_posts.sample.csv `
  --llm-provider openai `
  --llm-model your_model_id `
  --output reports/sample_report.md
```

Anthropic Messages APIを使う例:

```powershell
$env:ANTHROPIC_API_KEY="your_api_key"
python src/main.py `
  --account data/account_profile.sample.json `
  --posts data/posts.sample.csv `
  --trends data/trends.sample.json `
  --competitors data/competitors.sample.json `
  --competitor-posts data/competitor_posts.sample.csv `
  --llm-provider anthropic `
  --llm-model your_model_id `
  --output reports/sample_report.md
```

LLMに送るのは、ローカルCSV/JSONから作った要約テキストだけです。TikTokへアクセスさせたり、外部サイトを推測させたりしない前提のプロンプトにしています。

## テスト

```powershell
python -m unittest discover -s tests
```

## 入力データの注意

- 個人情報やセンシティブ情報は入れないでください。
- 参考動画 URL や参考アカウントは、分析メモとしてのみ扱います。
- 他人のコンテンツを無断転載するための機能はありません。
- レポートは仮説生成を目的としており、成長やバズを保証しません。

## Phase 1 の制約

- TikTok 上の現在トレンドは自動取得しません。
- トレンド情報はユーザーが `trends.json` に手動入力します。
- TikTok公式API PoCは自アカウントの認可済み公開動画のみを対象にします。
- TikTok Studio詳細指標は公式APIで確認できるまで手動補完扱いです。
- 外部 LLM API は任意です。未設定時の定性分析はルールベースです。
- 小規模データでは「暫定仮説」として扱います。

## 今後の改善バックログ

- TikTok Creative Center の手動調査結果取り込み
- Google Trends との比較
- YouTube Shorts / Instagram Reels の参考情報取り込み
- 投稿ネタ管理
- 投稿カレンダー生成
- 動画台本生成
- 冒頭フック生成
- サムネイル文言生成
- 過去レポートとの比較
- ダッシュボード化
- LLM API 連携による定性分析強化
