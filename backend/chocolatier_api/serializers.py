from rest_framework import serializers #シリアライザーをインポート
from django.conf import settings                             # settings.py の上限値を読むため
from django.core.validators import FileExtensionValidator    # 拡張子チェック用の Django 標準バリデーター
from .models import Snap, User, File, Tag
from datetime import datetime
import os

# =========================================================
# タグの共通処理（作成・更新の両方で使う）
# =========================================================

# ---------------------------------------------------------
# clean_tag_names：受け取ったタグ名の配列を整えて、チェックする
# - 例：[" 旅行", "カフェ", "", "旅行"] → ["旅行", "カフェ"]
# - NG なら ValidationError を発生させる（→ 400 で {"tags": ["..."]} が返る）
# ---------------------------------------------------------
def clean_tag_names(names):
    # 整えた結果を入れる箱
    cleaned = []

    for name in names:
        # 前後の空白を除く（" 旅行 " → "旅行"）
        name = name.strip()

        # 空のタグは捨てて、次のタグへ
        #（空白だけのタグや、フロントが空文字を送ってきた場合）
        if not name:
            continue

        # タグの文字数をチェック（settings.py の MAX_TAG_LENGTH = 30）
        # どのタグが長いのか分かるように、メッセージにタグ名を入れる
        if len(name) > settings.MAX_TAG_LENGTH:
            raise serializers.ValidationError(
                f'タグ「{name}」が長すぎます。{settings.MAX_TAG_LENGTH}文字以内にしてください'
            )

        #　重複を除く：まだ箱に入っていないタグだけ追加する
        if name not in cleaned:
            cleaned.append(name)

    # タグの個数をチェック（settings.py の MAX_TAGS_PER_SNAP = 10）
    # 空のタグと重複を除いた「後」の個数で数える
    if len(cleaned) > settings.MAX_TAGS_PER_SNAP:
        raise serializers.ValidationError(f'タグは{settings.MAX_TAGS_PER_SNAP}個までにしてください')

    # 整えた配列を返す（これが validated_data['tags'] になる）
    return cleaned

# ---------------------------------------------------------
# set_snap_tags：Snap に付いているタグを、names の内容に入れ替える
# - 例：今「旅行」が付いている Snap に ["カフェ"] を渡す → 「カフェ」だけになる
# - 空の配列 [] を渡すと、タグをすべて外す
# ---------------------------------------------------------
def set_snap_tags(snap, names):
    # ① タグ名から Tag オブジェクトを用意する
    #    get_or_create：その名前のタグがあれば取得、なければ作成する
    #    戻り値は (タグ, 新しく作ったかどうか) のタプルなので、[0] でタグだけ取り出す
    tags = [Tag.objects.get_or_create(name=name)[0] for name in names]

    # ② 中間テーブル（snap_tags）を、①のタグの組み合わせに入れ替える
    #    set()：足りないものは追加し、余分なものは削除してくれる
    snap.tags.set(tags)

# =========================================================
# スナップモデルの一覧表示用シリアライザー
# - get: 一覧取得：/snaps/
# - get: 詳細取得：/snaps/1/
# - putch: 更新：/snaps/1/ ※この時ファイル情報は更新しない
# =========================================================
class SnapSerializer(serializers.ModelSerializer):
    filePath = serializers.CharField(source='file.path', read_only=True)

    # tags：付いているタグを、名前の配列で返す（例：["カフェ", "旅行"]）
    # - SlugRelatedField：関連先のオブジェクトを、その 1 つの項目（slug_field）で表す
    # - many=True：多対多なので配列になる
    # - read_only=True：このシリアライザーは表示専用（受け取りは作成・更新用で行う）
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = Snap
        fields = ['id', 'file', 'filePath', 'comment', 'tags', 'created_at', 'updated_at']

# =========================================================
# スナップモデルの新規作成用シリアライザー
# =========================================================
class SnapCreateSerializer(serializers.ModelSerializer):
    upload = serializers.ImageField(
        write_only=True,  # 受け取るだけで、レスポンスには含めない
        validators=[FileExtensionValidator(allowed_extensions=settings.ALLOWED_IMAGE_EXTENSIONS)],
    )
    filePath = serializers.CharField(source='file.path', read_only=True)  # レスポンス用に追加

    # ---------------------------------------------------------
    # tags：付けるタグ名の配列（任意）
    # - ListField：配列を受け取る。child は配列の 1 要素の型
    # - 作成は multipart で送るので、フロントは tags を同じキーで繰り返し送る
    #   （tags=旅行 & tags=カフェ → ["旅行", "カフェ"]）
    # - allow_blank=True：空文字もいったん受け取り、validate_tags で捨てる
    # - required=False：送らなければタグなし
    # - write_only=True：返すときは to_representation で SnapSerializer の tags を使う
    # ---------------------------------------------------------
    tags = serializers.ListField(
        child = serializers.CharField(allow_blank=True),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Snap
        # - file は upload から自動生成
        # - user はフロントから受け取らない（views.py の SnapCreate.perform_create で
        #   ログインユーザーを渡す）。受け取るとなりすまし投稿ができてしまうため
        fields = ['id', 'comment', 'upload', 'filePath', 'tags']
        # extra_kwargs：モデルから自動で作られるフィールドに、オプションを追加する
        # - comment はモデルが TextField（上限なし）なので、ここで最大文字数を付ける
        # - 超えると「この値は 1000 文字以下でなければなりません。」のようなエラーになる
        extra_kwargs = {
            'comment': {'max_length': settings.MAX_COMMENT_LENGTH},
        }
    
    # ---------------------------------------------------------
    # validate_<フィールド名>：そのフィールドだけの独自チェック（チェック順 ③）
    # - value には、①② を通過した後の値（アップロードされたファイル）が入る
    # - 問題があれば ValidationError を発生させる → 400 で {"upload": ["..."]} が返る
    # - 問題がなければ、value をそのまま return する（return を忘れると None になる）
    # ---------------------------------------------------------
    def validate_upload(self,value):
        # value.size：ファイルサイズ（バイト）
        if value.size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)  # 表示用に MB に直す
            raise serializers.ValidationError(f'画像サイズは{max_mb}MB以下にしてください')
        return value

    # tagsのチェック
    def validate_tags(self, value):
        return clean_tag_names(value)


    def create(self, validated_data):
        upload = validated_data.pop('upload')
        # tags は Snap の「列」ではない（中間テーブルに入る）ので、先に取り出しておく
        # - 取り出さずに Snap.objects.create(tags=...) に渡すと、
        #   「多対多には直接代入できない」という TypeError になる
        tag_names = validated_data.pop('tags', [])

        # FileUploadSerializer を使ってファイル保存
        file_serializer = FileUploadSerializer(data={'upload': upload})
        file_serializer.is_valid(raise_exception=True)
        file_obj = file_serializer.save()

        # Snap 作成
        snap = Snap.objects.create(file=file_obj, **validated_data)
        # Snap が DB に保存されて id ができてから、タグを付ける
        # （中間テーブルには snap_id が必要なため、create より前には付けられない）
        set_snap_tags(snap, tag_names)
        return snap

    # 返すときの形
    # - 一覧・詳細（SnapSerializer）と同じ形で返す
    #   → フロントは、作成した Snap をそのまま一覧に追加できる
    def to_representation(self, instance):
        return SnapSerializer(instance, context=self.context).data

# =========================================================
# スナップ更新用シリアライザー
# -
# =========================================================
class SnapUpdateSerializer(serializers.ModelSerializer):
    # tags：付けるタグ名の配列（作成と同じ）
    # - 更新は JSON で送るので、["旅行", "カフェ"] の配列をそのまま送る
    # - 空の配列 [] を送ると、タグをすべて外す
    tags = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Snap
        fields = ['comment', 'tags']  # コメントとタグを更新（画像は変えない）
        # 新規作成（SnapCreateSerializer）と同じ上限にする
        extra_kwargs = {
            'comment': {'max_length': settings.MAX_COMMENT_LENGTH},
        }

    def validate_tags(self, value):
        return clean_tag_names(value)

    def update(self, instance, validated_data):
        # None：tags が送られてこなかった（PATCH で comment だけ送った）
        # []  ：タグを全部外したい
        # この 2 つを区別するため、pop の既定値を None にする
        tag_names = validated_data.pop('tags', None)

        # comment など、普通の列の更新は親クラス（ModelSerializer）に任せる
        instance = super().update(instance, validated_data)

        if tag_names is not None:
            set_snap_tags(instance, tag_names)
        return instance

    # 返すときの形も一覧・詳細と同じにする（以前は {"comment": ...} だけだった）
    def to_representation(self, instance):
        return SnapSerializer(instance, context=self.context).data

# =========================================================
# スナップ削除用シリアライザー
# =========================================================
class SnapDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snap
        fields = ['id', 'file', 'comment', 'created_at', 'updated_at']

    def delete(self, instance):
        import os
        from django.conf import settings

        # 1. Snap に紐づく File を先に取得
        file_obj = instance.file
        print("DEBUG: Snap ID:", instance.id)
        print("DEBUG: File object:", file_obj)

        if file_obj:
            # 2. 実ファイルパス確認
            full_path = os.path.join(settings.MEDIA_ROOT, file_obj.path.replace("\\","/"))
            print("DEBUG: Full file path:", full_path)
            print("DEBUG: File exists?", os.path.exists(full_path))

        # 3. Snap 削除
        instance.delete()
        print("DEBUG: Snap deleted")

        # 4. File 削除は FileDeleteSerializer に委譲
        if file_obj:
            print("DEBUG: Calling FileDeleteSerializer.delete_file()")
            FileDeleteSerializer.delete_file(file_obj)
            print("DEBUG: FileDeleteSerializer finished")

        return {"message": f"Snap {instance.id} and related file deleted successfully."}

# =========================================================
# ユーザーモデルのシリアライザー
# =========================================================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password',)
        #パスワードフィールドを書き込み専用にする
        extra_kwargs = {'password':{'write_only': True}}
    
    #create時にcreate_userメソッドを使用
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

# =========================================================
# ファイルモデルのシリアライザー()
# =========================================================
class FileUploadSerializer(serializers.ModelSerializer):
    upload = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = File
        fields = ['id', 'name', 'path', 'created_at', 'updated_at', 'upload']
        read_only_fields = ['id', 'path', 'created_at', 'updated_at']

    def create(self, validated_data):
        upload = validated_data.pop('upload')
        original_name, ext = os.path.splitext(upload.name)

        # 現在日時を yyyymmddHHMMSS 形式で取得
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # 新しいファイル名
        new_filename = f"{original_name}_{timestamp}{ext}"

        # 保存先パス
        from django.conf import settings
        save_path = os.path.join("uploads", new_filename)  # media/uploads/filename

        # 実際に保存
        full_path = os.path.join(settings.MEDIA_ROOT, save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb+") as f:
            for chunk in upload.chunks():
                f.write(chunk)

        # DB保存
        file_obj = File.objects.create(
            name=validated_data.get("name") or new_filename,
            path=save_path
        )
        return file_obj

class FileDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = []

    @staticmethod
    def delete_file(file_obj):
        import os
        from django.conf import settings

        if not file_obj:
            print("DEBUG: No file_obj to delete")
            return

        full_path = os.path.join(settings.MEDIA_ROOT, file_obj.path.replace("\\","/"))
        print("DEBUG: Deleting file at path:", full_path)

        if os.path.exists(full_path):
            os.remove(full_path)
            print("DEBUG: File removed from disk")
        else:
            print("DEBUG: File does not exist on disk")

        # DB 削除
        File.objects.filter(id=file_obj.id).delete()
        print("DEBUG: File deleted from DB")