# サインアップ（Django）

> ⚠️ 改修案件2で、サインアップ API を管理者（スタッフ権限のあるユーザー）だけが使えるように変更しました。この記事は変更前（誰でも登録できる）の記録です。今の実装と呼び出し方は [08_validation.md](08_validation.md) と [07_cookieAuth.md](07_cookieAuth.md) を参照してください。

- [サインアップ（Django）](#サインアップdjango)
  - [1. プロジェクトディレクトリ](#1-プロジェクトディレクトリ)
    - [■ カスタムユーザーの設定（settings.py）](#-カスタムユーザーの設定settingspy)
  - [2. アプリディレクトリ](#2-アプリディレクトリ)
    - [■ カスタムユーザーモデルの定義(models.py)](#-カスタムユーザーモデルの定義modelspy)
    - [■ シリアライザー(serializers.py)](#-シリアライザーserializerspy)
    - [ビュー(views.py)](#ビューviewspy)
    - [■ ルーティング(urls.py API側)](#-ルーティングurlspy-api側)
  - [3. マイグレーション](#3-マイグレーション)
    - [■ 事前準備](#-事前準備)
    - [■ 実行手順](#-実行手順)
  - [4. テスト手順(PowerShellでCurlコマンドを実行)](#4-テスト手順powershellでcurlコマンドを実行)

## 1. プロジェクトディレクトリ

### ■ カスタムユーザーの設定（settings.py）
- `settings.py` に以下を追加（`xxx` はアプリ名に置き換える）。

```py
AUTH_USER_MODEL = 'xxx.User'
```

## 2. アプリディレクトリ

### ■ カスタムユーザーモデルの定義(models.py)
- **目的**: Django標準の `User` モデルを拡張・変更し、プロジェクト専用のユーザー定義を行う。
- **ポイント**: 
  - `models.py` にモデルを定義し、これがDBのユーザーテーブルとなる。
  - 今回は `id`・`username`・`password`・`email` を利用。
  - デフォルトのフィールドを一部削除・変更し、`username` を入力必須かつ一意にする。

- デフォルトのUserモデルに含まれる主なフィールド
  - username
  - first_name
  - last_name
  - email
  - password
  - is_staff
  - is_active
  - date_joined

- 不要なフィールドは `フィールド名 = None` で無効化できる。

```py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    カスタムユーザーモデル
    - username: テキストフィールドに変更、ユニーク
    - first_name / last_name: 不要のため削除
    """
    username = models.TextField(unique=True)  # デフォルトのCharFieldからTextFieldに変更

    # 不要フィールドを削除
    first_name = None
    last_name = None

    def __str__(self):
        # 管理画面やprintで表示される文字列表現
        return self.username
```

### ■ シリアライザー(serializers.py)
- **役割**: Pythonオブジェクト ⇔ JSON の変換を行う。
- **使うクラス**: Django REST Frameworkの `ModelSerializer` を継承。
- **設定（Meta情報）**:
  - Userモデルを対象とする。
  - `id`・`username`・`email`・`password` を扱う。
  - `password` は書き込み専用（レスポンスに含めない）。

- **createメソッド**:
  - 新しいユーザー登録時に呼ばれる。
  - `serializer.save()` → `create()` が実行される流れ。
  - `self` はシリアライザー自身、`validated_data` はバリデーション済みの入力データ。
  - `User.objects.create_user()` によりパスワードをハッシュ化して保存。

```py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        # パスワードフィールドを書き込み専用にする
        extra_kwargs = {'password': {'write_only': True}}

    # ユーザー登録処理
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
```

> **シリアライザーとビューの接続性（登録フロー）**  
> 1) クライアントが `POST /signup/` にJSON（`username`,`email`,`password`）を送る  
> 2) ビューで `UserSerializer(data=request.data)` → `serializer.is_valid()`  
> 3) `serializer.save()` が呼ばれると `create(validated_data)` が実行され、DBにユーザーを作成  
> 4) ビューは結果をレスポンスとして返す（201/400など）

### ビュー(views.py)
- **役割**: リクエストを受け取り、レスポンスを返す。
- **流れ**:
  1. クライアントがPOSTリクエストを送信
  2. `UserSerializer` でデータを検証
  3. `serializer.save()` によって `create()` が呼ばれ、新規ユーザーがDBに登録される
  4. 成功時はステータス201とメッセージを返す

```py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer

class UserSignup(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # ← create() が呼ばれる
            return Response({"message": "ユーザー登録が完了しました"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### ■ ルーティング(urls.py API側)
```py
from django.urls import path
from .views import UserSignup

urlpatterns = [
    path('signup/', UserSignup.as_view(), name='user-signup'),
]
```

## 3. マイグレーション

### ■ 事前準備
- すでにデフォルトユーザーテーブルを作っていると、競合してエラーが出ることがある。
- 開発初期なら、DBをリセットして再作成するのが簡単。
- 削除するファイル
  - `db.sqlite3`
  - `{アプリ名}/migrations/000*.py`

### ■ 実行手順
```sh
python manage.py makemigrations
python manage.py migrate
```

## 4. テスト手順(PowerShellでCurlコマンドを実行)
```sh
curl.exe -X POST http://localhost:8000/chocolatier_api/signup/ `
  -H "Content-Type: application/json" `
  -d '{\"username\": \"alice2\", \"email\": \"alice2@example.com\", \"password\": \"your-secret-password\"}'
```
