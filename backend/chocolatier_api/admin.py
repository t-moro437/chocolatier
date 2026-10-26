from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count          # タグごとの Snap 数を数えるため
from .models import User, File, Snap, Tag   # Tag を追加

# =========================================================
# カスタムUserモデル用管理画面
# =========================================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    カスタムUserモデル管理画面設定
    - DjangoデフォルトのUserAdminを継承
    - 一覧表示、検索、フィルター、作成フォームの設定を追加
    """
    # 管理画面一覧で表示するカラム
    list_display = ('id', 'username', 'email', 'is_staff', 'is_active')
    
    # 検索バーで検索できるフィールド
    search_fields = ('username', 'email')
    
    # サイドバーでフィルタリングできるフィールド
    list_filter = ('is_staff', 'is_active', 'is_superuser')

    # ユーザー編集画面のフィールド構成
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),  # 基本情報
        ('権限', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),  # 権限関連
    )

    # ユーザー作成フォームのフィールド構成
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    # 一覧表示のデフォルト並び順
    ordering = ('id',)


# =========================================================
# Fileモデル用管理画面
# =========================================================
@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """
    ファイル管理用管理画面設定
    - ファイル情報の一覧表示・検索・編集を簡単にする
    """
    # 管理画面一覧で表示するカラム
    list_display = ('id', 'name', 'path', 'created_at', 'updated_at')
    
    # 検索バーで検索できるフィールド
    search_fields = ('name', 'path')
    
    # 作成・更新日時は自動管理されるため編集不可に設定
    readonly_fields = ('created_at', 'updated_at')


# =========================================================
# Snapモデル用管理画面
# =========================================================
@admin.register(Snap)
class SnapAdmin(admin.ModelAdmin):
    """
    スナップ管理用管理画面設定
    - ユーザーとファイルに紐づくスナップ情報を管理
    - 外部キーのユーザー名・ファイル名で表示される
    """
    # 一覧表示するカラム
    list_display = ('id', 'user', 'file', 'comment', 'tag_list', 'created_at', 'updated_at')
    
    # 検索バーで検索可能なフィールド
    # 外部キーの関連フィールドも __ で検索可能
    search_fields = ('comment', 'user__username', 'file__name')
    
    # 作成・更新日時は自動管理されるため編集不可
    readonly_fields = ('created_at', 'updated_at')
    
    # サイドバーでユーザー・ファイルで絞り込み可能
    list_filter = ('user', 'file', 'tags')

    # 多対多の入力欄を「左右 2 つのリスト＋矢印」の形にする
    # - 左：選べるタグ全部 / 右：この Snap に付いているタグ
    # - 指定しないと、Ctrl を押しながら選ぶ複数選択リストになり、使いにくい
    filter_horizontal = ('tags',)

    # 一覧画面で使うデータの取り方
    # - prefetch_related('tags')：タグを「まとめて 1 回の SQL」で取ってくる
    # - N+1 問題対策
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tags')

    # 一覧の「タグ」列に表示する値
    # - obj は 1 行分の Snap
    # - obj.tags.all() は prefetch_related 済みなので、ここでは SQL が発行されない
    @admin.display(description='タグ')
    def tag_list(self, obj):
        return ', '.join(tag.name for tag in obj.tags.all())


# =========================================================
# Tagモデル用管理画面
# =========================================================
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    タグ管理用管理画面設定
    - タグ名と、そのタグが付いている Snap の数を表示する
    """
    # 一覧表示するカラム（snap_count は下で定義するメソッド）
    list_display = ('id', 'name', 'snap_count', 'created_at')

    # 検索バーで検索可能なフィールド
    search_fields = ('name',)

    # 作成日時は自動管理されるため編集不可
    readonly_fields = ('created_at',)

    # 一覧画面で使うデータの取り方
    # - annotate(snap_count=Count('snaps'))：タグごとに「付いている Snap の数」を SQL で数えて、
    #   各タグに snap_count という値を追加する
    # - 'snaps' は、models.py の Snap.tags で付けた related_name（タグ → Snap の方向の名前）
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(snap_count=Count('snaps'))

    # 一覧の「Snap数」列に表示する値
    # - ordering='snap_count'：列の見出しをクリックすると、Snap 数で並べ替えられる
    @admin.display(description='Snap数', ordering='snap_count')
    def snap_count(self, obj):
        return obj.snap_count

