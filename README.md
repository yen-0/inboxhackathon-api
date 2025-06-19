## Embox API README

このREADMEでは、Cloud Run上でFastAPIコンテナを正常に起動・ヘルスチェックをパスさせるための重要ポイントをまとめています。

### 1. ルートエンドポイントの追加

Cloud Runはデフォルトで`GET /`をヘルスチェックします。FastAPIアプリに以下のようなルートを追加してください。

```python
@app.get("/", response_class=PlainTextResponse)
async def health_check():
    return "OK"
```

これにより、`GET /`に200 OKで`OK`を返し、コンテナの健全性を示せます。

### 2. ポートのバインディング

Cloud Runは環境変数`PORT`（通常は8080）を設定します。`main.py`の末尾でこの`PORT`を読み込み、uvicornにバインドさせます。

```python
if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
```

### 3. DockerfileでのCMD設定

DockerfileのCMDはシェル形式にして、ランタイムで`$PORT`が展開されるようにします。

```dockerfile
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

もしくは：

```dockerfile
CMD ["/bin/sh","-c","uvicorn main:app --host 0.0.0.0 --port $PORT"]
```

### 4. 環境変数の設定

PowerShellからデプロイする場合、`--set-env-vars`は各`KEY=VALUE`をシングルクォートまたはダブルクォートで囲み、カンマで区切ります。

```powershell
gcloud run deploy inboxhackathon-api \
  --image gcr.io/PROJECT_ID/inboxhackathon-api \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars \
"GOOGLE_CLIENT_ID=あなたのクライアントID",`\n"GOOGLE_CLIENT_SECRET=あなたのクライアントシークレット",`\n"GEMINI_API_KEY=あなたのGemini APIキー",`\n"SESSION_SECRET=ランダムな文字列"
```

* `=`の前後にスペースを入れない
* 各ペアをクォートで囲み、カンマ区切り

### 5. ビルドとデプロイ手順

1. **依存パッケージの追加**: `requirements.txt`に`itsdangerous`を追記
2. **コンテナビルド**（ローカル）

   ```bash
   docker build -t gcr.io/PROJECT_ID/inboxhackathon-api .
   docker push gcr.io/PROJECT_ID/inboxhackathon-api
   ```

   またはCloud Buildを利用:

   ```bash
   ```

gcloud builds submit --tag gcr.io/PROJECT\_ID/inboxhackathon-api

```
3. **Cloud Runデプロイ**: 上記の`gcloud run deploy`コマンドで実行

---

以上の手順を守ることで、Cloud Runコンテナはヘルスチェックをパスし、正常に稼働します。

```
