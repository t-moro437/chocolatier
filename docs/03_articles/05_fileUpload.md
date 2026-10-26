# ファイルアップロード

※開発当時にテストとして作成した処理です。本実装と異なります。

> ⚠️ この記事の `files/upload/` API は、改修案件1で削除しました。今のアップロードは `snap/create/` で行い、画像の入力チェックは [08_validation.md](08_validation.md) を参照してください。

- [ファイルアップロード](#ファイルアップロード)
  - [1. プロジェクトディレクトリ](#1-プロジェクトディレクトリ)
    - [■ 設定（settings.py）](#-設定settingspy)
    - [■ ルーティングで配信設定](#-ルーティングで配信設定)
  - [2. アプリディレクトリ](#2-アプリディレクトリ)
    - [■ モデル定義(models.py)](#-モデル定義modelspy)
    - [■ シリアライザー(serializers.py)](#-シリアライザーserializerspy)
    - [■ ビュー(views.py)](#-ビューviewspy)
    - [■ ルーティング(urls.py API側)](#-ルーティングurlspy-api側)
  - [3. テスト手順(PowerShellでCurlコマンドを実行)](#3-テスト手順powershellでcurlコマンドを実行)


## 1. プロジェクトディレクトリ

### ■ 設定（settings.py）
```python
# メディアファイルの保存先
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### ■ ルーティングで配信設定
```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
  # 他のルーティング
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 2. アプリディレクトリ

### ■ モデル定義(models.py)
```python
from django.db import models

class File(models.Model):
    id = models.BigAutoField(primary_key=True)  # BIGINT 主キー
    name = models.CharField(max_length=255, blank=True, null=True)  # 任意ファイル名
    path = models.CharField(max_length=500, unique=True)  # 実際の保存パス
    created_at = models.DateTimeField(auto_now_add=True)  # 登録日時
    updated_at = models.DateTimeField(auto_now=True)      # 更新日時

    def __str__(self):
        return self.name or f"File {self.id}"
```

### ■ シリアライザー(serializers.py)
- ファイルそのものは request.FILES から拾い、DBにはパスを保存する。
```python
from rest_framework import serializers
from .models import File
import os

class FileSerializer(serializers.ModelSerializer):
    upload = serializers.FileField(write_only=True, required=True)  # 受信用フィールド

    class Meta:
        model = File
        fields = ['id', 'name', 'path', 'created_at', 'updated_at', 'upload']
        read_only_fields = ['id', 'path', 'created_at', 'updated_at']

    def create(self, validated_data):
        upload = validated_data.pop('upload')  # アップロードファイル
        filename = upload.name

        # 保存先パス決定
        from django.conf import settings
        save_path = os.path.join("uploads", filename)  # media/uploads/filename

        # 実際に保存
        full_path = os.path.join(settings.MEDIA_ROOT, save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb+") as f:
            for chunk in upload.chunks():
                f.write(chunk)

        # DB保存
        file_obj = File.objects.create(
            name=validated_data.get("name") or filename,
            path=save_path
        )
        return file_obj
```

### ■ ビュー(views.py)
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import FileSerializer

class FileUploadView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = FileSerializer(data=request.data)
        if serializer.is_valid():
            file_obj = serializer.save()
            return Response(FileSerializer(file_obj).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

```

### ■ ルーティング(urls.py API側)
```python
from django.urls import path
from .views import FileUploadView

urlpatterns = [
    path("files/upload/", FileUploadView.as_view(), name="file-upload"),
]
```

## 3. テスト手順(PowerShellでCurlコマンドを実行)
- Curl実行
```
curl.exe -X POST http://127.0.0.1:8000/chocolatier_api/files/upload/ -F "upload=@C:/sample.png" -F "name=サンプル画像"
```
- レスポンス（成功）
```
{"id":2,"name":"サンプル画像","path":"uploads\\sample.png","created_at":"2025-08-26T14:04:53.759287Z","updated_at":"2025-08-26T14:04:53.759329Z"}
```