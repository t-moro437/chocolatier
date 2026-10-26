# サインイン（Django + JWT認証）

> ⚠️ 改修案件1で、認証を Bearer ヘッダーから HttpOnly Cookie に変更しました。この記事は変更前（Bearer 認証）の記録です。今の実装は [07_cookieAuth.md](07_cookieAuth.md) を参照してください。

- [サインイン（Django + JWT認証）](#サインインdjango--jwt認証)
  - [1. プロジェクトディレクトリ](#1-プロジェクトディレクトリ)
    - [■ ライブラリのインストール](#-ライブラリのインストール)
    - [■ 設定（settings.py）:JWT を設定](#-設定settingspyjwt-を設定)
    - [■ ルーティング(urls.py):API エンドポイントを追加](#-ルーティングurlspyapi-エンドポイントを追加)
  - [2. アプリディレクトリ](#2-アプリディレクトリ)
    - [■ ビュー(views.py):ログインユーザーの情報取得](#-ビューviewspyログインユーザーの情報取得)
    - [■ ルーティング(urls.py API側)](#-ルーティングurlspy-api側)
  - [3. テスト手順(PowerShellでCurlコマンドを実行)](#3-テスト手順powershellでcurlコマンドを実行)


## 1. プロジェクトディレクトリ

### ■ ライブラリのインストール
プロジェクト直下（`manage.py` があるフォルダ）でライブラリをインストール。

```bash
pip install djangorestframework-simplejwt
```

### ■ 設定（settings.py）:JWT を設定
```python
INSTALLED_APPS = [
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),   # アクセストークン有効期限 = 60分
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),      # リフレッシュトークン有効期限 = 1日
}
```

### ■ ルーティング(urls.py):API エンドポイントを追加
ユーザー名とパスワードでトークンを発行するエンドポイントと、  
リフレッシュトークンで新しいアクセストークンを発行するエンドポイントを設定。

```python
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

## 2. アプリディレクトリ

### ■ ビュー(views.py):ログインユーザーの情報取得
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer

class UserInfoView(APIView):
    # ログイン中のユーザーのみアクセス可能
    permission_classes = [IsAuthenticated]

    # GET メソッドでユーザー情報を取得
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
```

### ■ ルーティング(urls.py API側)
```python
urlpatterns = [
    path('user-info/', UserInfoView.as_view(), name='user_info'),
]
```

## 3. テスト手順(PowerShellでCurlコマンドを実行)

事前準備：前回作成したサインイン機能でユーザー登録しておく。以下、Curlコマンドでのテストを想定しているが、Postmanなどでも良い。

1. **アクセストークン発行**  
   `/api/token/` にユーザー名・パスワードを `POST` → アクセストークン & リフレッシュトークン取得  

    ```bash
    curl.exe -X POST http://localhost:8000/token/ -H "Content-Type: application/json" -d '{\"username\":\"alice\",\"password\":\"your-secret-password\"}'
    ```

2. **ユーザー情報取得**  
   `/chocolatier_api/user-info/` に手順 1 で取得したアクセストークンを付与して `GET` → ログイン中ユーザー情報が取得できる 
   ```bash
   curl.exe -X GET http://localhost:8000/chocolatier_api/user-info/ `
    -H "Authorization: Bearer <ACCESS_TOKEN>"
   ```

3. **アクセストークン更新**  
   `/token/refresh/` にリフレッシュトークンを `POST` → 新しいアクセストークンが取得できる  
    ```bash
    curl.exe -X POST http://localhost:8000/token/refresh/ -H "Content-Type: application/json" -d '{\"refresh\":\"<REFRESH_TOKEN>\"}'

    ```