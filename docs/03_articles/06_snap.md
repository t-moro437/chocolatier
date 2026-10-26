# API作成

> ⚠️ 改修案件1〜4で、次のように変わりました。この記事は変更前の記録です。
> - 自分の Snap だけを扱う（他人の Snap は 404）。投稿者はサーバー側で設定する → [07_cookieAuth.md](07_cookieAuth.md)
> - 作成は `snap/create/`（multipart で画像を送る）。画像・コメントの入力チェックあり → [08_validation.md](08_validation.md)
> - curl ではログインの Cookie と `X-CSRFToken` ヘッダーが必要 → [07_cookieAuth.md のテスト手順](07_cookieAuth.md#4-テスト手順powershellでcurlコマンドを実行)
> - Snap にタグ（`tags`）が付き、一覧を `?tag=` で絞り込める → [10_tags.md](10_tags.md)
> - 一覧は 12 件ずつ `{next, previous, results}` の形で返る → [11_infiniteScroll.md](11_infiniteScroll.md)
- 本APIは Django REST Framework (DRF) を使用して実装している。
- RESTful な CRUD 操作（一覧取得、登録、更新、削除）が可能。
- generics.ListCreateAPIView / RetrieveUpdateDestroyAPIView により CRUD を簡単に実装

- [API作成](#api作成)
  - [1. プロジェクトディレクトリ](#1-プロジェクトディレクトリ)
    - [■ ライブラリのインストール](#-ライブラリのインストール)
    - [■ 設定（settings.py）:JWT を設定](#-設定settingspyjwt-を設定)
  - [2. アプリディレクトリ](#2-アプリディレクトリ)
    - [■ モデルの定義(models.py)](#-モデルの定義modelspy)
      - [【Snap】](#snap)
    - [■ シリアライザー(serializers.py)](#-シリアライザーserializerspy)
    - [■ ビュー(views.py)](#-ビューviewspy)
    - [■ ルーティング(urls.py API側)](#-ルーティングurlspy-api側)
  - [3. テスト手順(PowerShellでCurlコマンドを実行)](#3-テスト手順powershellでcurlコマンドを実行)


## 1. プロジェクトディレクトリ

### ■ ライブラリのインストール
- rest frameworkを使用
- プロジェクト直下（`manage.py` があるフォルダ）でライブラリをインストール。

```bash
pip install django djangorestframework
```

### ■ 設定（settings.py）:JWT を設定
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'chocolatier_api',
]
```

## 2. アプリディレクトリ

### ■ モデルの定義(models.py)

#### 【Snap】
-  ユーザーとファイルに紐づくスナップ情報を管理

```python
from django.db import models
from django.conf import settings 

class Snap(models.Model):
    id = models.BigAutoField(primary_key=True)  # BIGINT 主キー、自動採番
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # カスタムユーザーに紐付け
        on_delete=models.CASCADE,  # ユーザー削除時にスナップも削除
        related_name='snaps'       # user.snaps で逆参照可能
    )
    file = models.ForeignKey(
        'File',                     # Fileモデルに紐付け（文字列で指定すると順序の制約が緩和）
        on_delete=models.CASCADE,    # ファイル削除時にスナップも削除
        related_name='snaps'         # file.snaps で逆参照可能
    )
    comment = models.TextField(blank=True, null=True)  # コメントは任意
    created_at = models.DateTimeField(auto_now_add=True)  # 作成日時（自動）
    updated_at = models.DateTimeField(auto_now=True)      # 更新日時（自動）

    def __str__(self):
        # 管理画面やシェルで見やすい表示
        return f"{self.id} - {self.user.username} - {self.file.name}"

```

### ■ シリアライザー(serializers.py)

```python
class SnapSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    file_name = serializers.CharField(source='file.name', read_only=True)

    class Meta:
        model = Snap
        fields = ['id', 'user', 'user_name', 'file', 'file_name', 'comment', 'created_at', 'updated_at']

```

### ■ ビュー(views.py)
- 一覧表示・新規作成（genericsのListCreateAPIViewを継承）
```python
from urllib import response
from django.shortcuts import render
from rest_framework import generics
from .models import Snap
from .serializers import SnapSerializer

class SnapListCreate(generics.ListCreateAPIView):
    #扱うクエリセットをSnapオブジェクト全てとして設定
    queryset = Snap.objects.all()

    #シリアライザーを設定
    serializer_class = SnapSerializer

```
- 更新・削除（genericsのRetrieveUpdateDestroyAPIViewを継承）
```python
from urllib import response
from django.shortcuts import render
from rest_framework import generics
from .models import Snap
from .serializers import SnapSerializer

class SnapUpdate(generics.RetrieveUpdateDestroyAPIView):
    #扱うクエリセットをSnapオブジェクト全てとして設定
    queryset = Snap.objects.all()

    #シリアライザーを設定
    serializer_class = SnapSerializer

```

### ■ ルーティング(urls.py API側)
```python
from django.urls import path
from .views import SnapListCreate,SnapUpdate

urlpatterns = [
    path('snap/', SnapListCreate.as_view(), name='snap-list-create'),
    path('snap/<int:pk>/',SnapUpdate.as_view(), name='snap-detail'),
]
```

## 3. テスト手順(PowerShellでCurlコマンドを実行)

1. **一覧**  
    ```bash
    curl.exe -X GET "http://localhost:8000/chocolatier_api/snap/" `
      -H "Content-Type: application/json"
    ```

2. **登録**  
   ```bash
    curl.exe -X POST "http://localhost:8000/chocolatier_api/snap/" `
      -H "Content-Type: application/json" `
      -d '{\"user\":1,\"file\":1,\"comment\":\"これはcurlからのテストです\"}'
   ```

3. **更新**   
    ```bash
    curl.exe -X PUT "http://localhost:8000/chocolatier_api/snap/1/" `
      -H "Content-Type: application/json" `
      -d '{\"user\":1,\"file\":1,\"comment\":\"これはcurlから更新したテストです\"}'
    ```

4. **削除**   
    ```bash
    curl.exe -X DELETE "http://localhost:8000/chocolatier_api/snap/1/" `
      -H "Content-Type: application/json"
    ```