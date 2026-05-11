# TikTok Analysis Tool

TikTok公式APIで取得できる公開動画データと、運用者が手入力するTikTok Studio/クリエイティブ/トレンド/参考投稿メモを分けて分析するローカルCLIツールです。

このツールはスクレイピング、自動ログイン、自動投稿、自動いいね、自動フォロー、自動コメントを行いません。

## 入力ファイル

### `data/api_posts.sample.csv`

TikTok公式APIから取得できる投稿データです。

代表カラム:

- `video_id`
- `create_time`
- `posted_at`
- `share_url`
- `title`
- `video_description`
- `duration`
- `view_count`
- `like_count`
- `comment_count`
- `share_count`
- `cover_image_url`
- `embed_link`
- `hashtags`
- `music_id`
- `source`

このファイルだけで分析するKPI:

- 再生数
- いいね数
- コメント数
- シェア数
- いいね率
- コメント率
- シェア率
- 投稿曜日
- 投稿時間帯
- 動画尺分類
- ハッシュタグ出現数
- 中央値再生数
- 平均再生数
- 上位10%除外平均
- 直近10投稿中央値
- 直近30日中央値
- 外れ値バズ投稿候補

### `data/manual_insights.sample.csv`

TikTok Studioやアプリ内インサイトから手動転記する深い指標です。

例:

- `saves`
- `profile_views`
- `follows_from_video`
- `average_watch_time`
- `completion_rate`
- `traffic_source_for_you`
- `audience_gender`
- `audience_age_range`
- `audience_region`

このファイルがない場合、保存率、フォロー転換率、完視聴率、平均視聴時間、プロフィール遷移率は「データ不足」と表示します。

### `data/creative_notes.sample.csv`

運用者が動画を見て記録する定性メモです。

例:

- `account_strategy_category`
- `content_category`
- `is_pr`
- `hook_text`
- `hook_type`
- `first_3sec_summary`
- `video_structure`
- `cta_type`
- `face_visible`
- `voiceover`
- `text_density`
- `save_reason`
- `comment_prompt`

`account_strategy_category` は以下から選びます。

- `beauty_core`
- `beauty_adjacent`
- `lifestyle`
- `personal`
- `unrelated`

### `data/trend_research.sample.csv`

TikTok Creative Center、TikTokアプリ内検索、Google Trendsなどを手動調査して記録するファイルです。自動取得はしません。

### `data/competitor_posts.sample.csv`

参考アカウント・競合アカウントの手動調査結果です。

参考にしてよいもの:

- 冒頭フックの構造
- 動画構成
- CTAパターン
- 尺の傾向
- テロップ密度
- コメント誘導の型
- 保存促しの型

コピーしてはいけないもの:

- 参考投稿のテーマそのもの
- 参考投稿のジャンルそのもの
- 固有表現
- 台本
- 映像構成の丸写し

## レポート生成

```powershell
python src/main.py report `
  --account data/account_profile.sample.json `
  --api-posts data/api_posts.sample.csv `
  --manual-insights data/manual_insights.sample.csv `
  --creative-notes data/creative_notes.sample.csv `
  --trend-research data/trend_research.sample.csv `
  --competitor-posts data/competitor_posts.sample.csv `
  --output reports/sample_report.md
```

実APIから取得したCSVを使う場合:

```powershell
python src/main.py report `
  --account data/account_profile.local.json `
  --api-posts data/tiktok_videos.local.csv `
  --manual-insights data/manual_insights.local.csv `
  --creative-notes data/creative_notes.local.csv `
  --trend-research data/trend_research.local.csv `
  --competitor-posts data/competitor_posts.local.csv `
  --output reports/tiktok_api_report.local.md
```

`manual_insights`、`creative_notes`、`trend_research`、`competitor_posts` は存在しなくても実行できます。その場合、レポート内に不足理由と入力先が表示されます。

## TikTok公式API PoC

OAuth URL生成:

```powershell
python src/main.py tiktok auth-url `
  --client-key YOUR_CLIENT_KEY `
  --redirect-uri http://127.0.0.1:8765/callback `
  --scopes user.info.basic,user.info.profile,user.info.stats,video.list `
  --state local-test `
  --pkce-file data/tiktok_pkce.local.json
```

トークン交換:

```powershell
python src/main.py tiktok exchange-token `
  --client-key YOUR_CLIENT_KEY `
  --client-secret $env:TIKTOK_CLIENT_SECRET `
  --redirect-uri http://127.0.0.1:8765/callback `
  --code AUTHORIZATION_CODE `
  --pkce-file data/tiktok_pkce.local.json
```

ユーザー情報取得:

```powershell
python src/main.py tiktok fetch-user `
  --token-file data/tiktok_tokens.local.json `
  --output data/tiktok_user.local.json
```

公開動画一覧取得:

```powershell
python src/main.py tiktok fetch-videos `
  --token-file data/tiktok_tokens.local.json `
  --max-count 20 `
  --max-pages 10 `
  --output data/tiktok_videos.raw.local.json
```

APIレスポンスを分析用CSVへ変換:

```powershell
python src/main.py tiktok normalize-videos `
  --input data/tiktok_videos.raw.local.json `
  --output data/tiktok_videos.local.csv
```

## レポートの考え方

- 公式APIで取得できる事実
- 手入力が必要な指標
- 推測による改善提案

この3つを明確に分けます。

保存率、プロフィール遷移率、フォロー転換率、完視聴率、平均視聴維持率、流入元別成果は、`manual_insights.csv` に入力がない限り分析しません。

冒頭3秒、動画構成、CTA、顔出し、声出し、PR有無、テロップ密度は、`creative_notes.csv` に入力がない限り断定しません。

## テスト

```powershell
python -m unittest discover -s tests
```

## 今後の拡張候補

- TikTok Creative Centerの手動調査結果CSVを増やす
- Google Trendsの美容キーワードCSVを取り込む
- 過去レポートとの比較
- 投稿カレンダー生成
- LLM APIによる定性分析補助

LLMを使う場合でも、公式APIで取れていない指標を取れている前提で補完しないでください。
