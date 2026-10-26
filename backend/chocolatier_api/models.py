from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  # Snapモデルで使用するため必須

# =========================================================
# Snapモデル
# - ユーザーとファイルに紐づくスナップ情報を管理
# =========================================================
class Snap(models.Model):
    id = models.BigAutoField(primary_key=True)  # BIGINT 主キー、自動採番
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # カスタムユーザーに紐付け
        on_delete=models.CASCADE,  # ユーザー削除時にスナップも削除
        related_name='snaps'       # user.snaps で逆参照可能
    )
    # ---------------------------------------------------------
    # Fileモデルに紐付け（文字列で指定すると順序の制約が緩和）
    # ファイル削除時にスナップも削除
    # file.snaps で逆参照可能
    # ---------------------------------------------------------
    file = models.ForeignKey(
        'File',                     
        on_delete=models.CASCADE,
        related_name='snaps'
    )


    # コメントは任意
    comment = models.TextField(blank=True, null=True)
    
    # ---------------------------------------------------------
    # tags：この Snap に付いているタグ（多対多）
    # - 'Tag'：Tag モデルはこのファイルの下の方で定義しているので、文字列で指定する
    # - related_name='snaps'：タグ側から tag.snaps.all() で「このタグが付いた Snap」を取れる
    # - blank=True：タグなしでも保存できる（管理画面やバリデーションで必須にしない）
    #   ※ ManyToManyField に null=True は意味がない（値は中間テーブルに入るため）
    # - DB の snap テーブル自体には列は増えず、中間テーブル
    #   chocolatier_api_snap_tags（id, snap_id, tag_id）が自動で作られる
    # ---------------------------------------------------------
    tags = models.ManyToManyField(
        'Tag',
        related_name='snaps',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)  # 作成日時（自動）
    updated_at = models.DateTimeField(auto_now=True)      # 更新日時（自動）

    def __str__(self):
        # 管理画面やシェルで見やすい表示
        return f"{self.id} - {self.user.username} - {self.file.name}"


# =========================================================
# カスタムユーザーモデル
# - username: テキストフィールドに変更、ユニーク
# - first_name / last_name: 不要のため削除
# =========================================================
class User(AbstractUser):
    # デフォルトのCharFieldからTextFieldに変更
    username = models.TextField(unique=True)  

    # 不要フィールドを削除
    first_name = None
    last_name = None

    def __str__(self):
        # 管理画面やprintで表示される文字列表現
        return self.username

# =========================================================
# Fileモデル
# =========================================================
class File(models.Model):
    id = models.BigAutoField(primary_key=True)  # BIGINT 主キー
    name = models.CharField(max_length=255, blank=True, null=True)  # ファイル名（任意）
    path = models.CharField(max_length=500, unique=True) # ファイルパス（ユニーク推奨）
    created_at = models.DateTimeField(auto_now_add=True) # 登録日時（自動）
    updated_at = models.DateTimeField(auto_now=True) # 更新日時（自動）

    def __str__(self):
        # ファイル名があれば表示、なければID表示
        return self.name or str(self.id)

# =========================================================
# Tagモデル
# - Snap の分類に使うタグ（例：旅行、カフェ）
# - 全ユーザーで共通の表。同じ名前のタグは 1 行だけ作られる
#   （alice の「旅行」と bob の「旅行」は同じ行を共有する）
# - 絞り込みの候補には「自分の Snap に付いているタグ」だけを出すので、
#   他のユーザーのタグが見えることはない（views.py の TagList で絞る）
# =========================================================
class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)  # BIGINT 主キー
    # タグ名
    # - max_length=30：1 タグ 30 文字まで（DB の列の長さ）
    # - unique=True：同じ名前のタグを 2 つ作れない（DB の一意制約）
    name = models.CharField(max_length=30, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)  # 作成日時（自動）

    class Meta:
        # 並び順を指定しない取得（Tag.objects.all() など）は、名前順で返す
        ordering = ['name']

    def __str__(self):
        # 管理画面やシェルで見やすい表示
        return self.name
