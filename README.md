Inboxsense Backend

このREADMEでは、Cloud Run上でFastAPIコンテナを正常に起動・ヘルスチェックをパスさせるための重要ポイントと、利用可能なエンドポイント一覧およびLINE Bot連携方法をまとめています。

1. 利用可能なサブパス（エンドポイント）

実際の機能はルート（/）ではなく、以下のサブパスで提供されます：

POST /analyze-sentiment

POST /generate

POST /summarize

POST /tasks

GET /auth/session

GET /auth/login

GET /auth/callback

POST /webhook  （LINE PlatformからのWebhook受信用）

これらのパスに対して必要なリクエストを送ることで、それぞれの機能（感情分析、メール生成、要約、タスク抽出、認証、LINE Bot連携）が利用できます。

2. ポートのバインディング

Cloud Runは環境変数 PORT（デフォルトは 8080）を設定します。main.py の末尾でこの PORT を読み込み、uvicorn にバインドさせます。

if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

3. DockerfileでのCMD設定

Dockerfile の CMD はシェル形式にして、ランタイムで $PORT が展開されるようにします。

CMD uvicorn main:app --host 0.0.0.0 --port $PORT

または：

CMD ["/bin/sh","-c","uvicorn main:app --host 0.0.0.0 --port $PORT"]

4. 環境変数の設定

PowerShell からデプロイする場合、--set-env-vars は各 KEY=VALUE をクォートで囲み、カンマで区切ります。

gcloud run deploy inboxhackathon-api \
  --image gcr.io/PROJECT_ID/inboxhackathon-api \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars \
"GOOGLE_CLIENT_ID=あなたのクライアントID",`\n"GOOGLE_CLIENT_SECRET=あなたのクライアントシークレット",`\n"GEMINI_API_KEY=あなたのGemini APIキー",`\n"SESSION_SECRET=ランダムな文字列"

= の前後にスペースを入れない

各ペアはクォートで囲み、カンマで区切る

5. ビルドとデプロイ手順

依存パッケージの追加

requirements.txt に itsdangerous を追記

コンテナビルド（ローカル）



docker build -t gcr.io/PROJECT_ID/inboxhackathon-api .
docker push gcr.io/PROJECT_ID/inboxhackathon-api


   またはCloud Buildを利用:

   ```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/inboxhackathon-api

Cloud Runデプロイ
上記の gcloud run deploy コマンドを実行

6. LINE Bot連携

LINE Messaging API を使って、以下の流れでGmail情報を取得・感情分析が可能です：

/login コマンド発行

LINE Bot 上で /login と入力すると、/auth/login?userId=<LINE_USER_ID> へのURLを返信。

ユーザはそのリンクからGoogle認証を行い、Gmail の scope（読み取り・送信）を許可。

/callback でトークン取得

Google からリダイレクトされた /auth/callback?state=<LINE_USER_ID>&code=... を受け取り、access_token をサーバー側 (in-memory または DB) に保存。

/recent または /mail コマンド発行

LINE Bot 上で /recent と入力すると、保存済みのトークンを使って Gmail API から最新メールを取得し、各メールの本文を感情分析。

分析結果は「送信者／件名 → スコア」という形式で返信。

既存の /analyze、/generate、/summarize、/tasks コマンドも引き続き利用可能です。

以上で、Cloud Run + FastAPI + LINE Bot + Gmail API を組み合わせたインボックス分析プラットフォームが完成します。ぜひお試しください！

