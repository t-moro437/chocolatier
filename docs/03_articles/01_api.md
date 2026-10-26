# CORSの設定

> ⚠️ 改修案件1で Cookie 認証にしたため、`CORS_ALLOW_ALL_ORIGINS = True` は使えなくなりました（Cookie 付きの通信では `*` が許可されないため）。今は `CORS_ALLOWED_ORIGINS` と `CORS_ALLOW_CREDENTIALS = True` を使い、フロントは共通の axios（`src/api/client.ts`）で `withCredentials: true` を付けています。詳しくは [07_cookieAuth.md](07_cookieAuth.md) を参照してください。

- [CORSの設定](#corsの設定)
  - [1. Django (プロジェクトディレクトリ)](#1-django-プロジェクトディレクトリ)
    - [■ CORSの設定](#-corsの設定)
    - [■ 設定（settings.py）:JWT を設定](#-設定settingspyjwt-を設定)
  - [2. フロントエンド](#2-フロントエンド)
    - [■ 連携例（axios）使用](#-連携例axios使用)


## 1. Django (プロジェクトディレクトリ)

### ■ CORSの設定
- CORS (Cross-Origin Resource Sharing) は、ブラウザが「異なるオリジン（ドメイン・ポート・プロトコルが違うサイト）」からのリクエストを制御する仕組み
- プロジェクト直下（`manage.py` があるフォルダ）でライブラリをインストール。

```bash
pip install django-cors-headers
```

### ■ 設定（settings.py）:JWT を設定

- すべてのオリジン（アクセス元ドメイン）からのリクエストを許可する設定。
```python
INSTALLED_APPS = [
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True
```

- 許可するオリジンを制限する方法
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000", # フロントエンド開発環境
    "https://example.com", # 本番フロントエンド
]
```

## 2. フロントエンド

### ■ 連携例（axios）使用
- `npm install axios`でインストール
- 連携例↓
```js
import { useState, useEffect } from "react";
import axios from "axios";

function App() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    axios.get("http://localhost:8000/api/users/")
      .then(res => setUsers(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div>
      <h2>ユーザー一覧</h2>
      <ul>
        {users.map(user => (
          <li key={user.id}>{user.username}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;

```