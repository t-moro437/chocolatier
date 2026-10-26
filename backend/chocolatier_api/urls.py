# =========================================================
# chocolatier_api/urls.py（アプリの API の URL）
# - chocolatier_core/urls.py の path('chocolatier_api/', include(...)) で取り込まれる
#   → ここの 'snap/' は、実際には /chocolatier_api/snap/ になる
# - 認証・権限は settings.py の REST_FRAMEWORK で共通設定済み
#   （signup 以外はすべてログイン必須）
# =========================================================
from django.urls import path
from .views import (
    SnapList,
    SnapCreate,
    SnapDetail,
    TagList,
    UserSignup,
    UserInfoView,
    # FileUpload,  # 削除予定（FileSerializer が未定義で動かないため無効化）
)

urlpatterns = [
       # GET : 自分のスナップ一覧（新しい順）
       path('snap/', SnapList.as_view(), name='snap-list'),
       # POST: スナップ新規作成（multipart: upload, comment）。投稿者はサーバー側で設定
       path('snap/create/', SnapCreate.as_view(), name='snap-create'),
       # GET / PATCH / DELETE: スナップ詳細・更新・削除
       # - <int:pk> は URL の数字部分を pk（主キー）として View に渡す
       # - 他人のスナップの pk を指定すると 404
       path('snap/<int:pk>/',SnapDetail.as_view(), name='snap-detail'),
    # GET : 自分の Snap に付いているタグの一覧（絞り込みの候補）
       path('tags/', TagList.as_view(), name='tag-list'),
       # POST: ユーザー新規登録（ログイン不要）
       path('signup/', UserSignup.as_view(), name='user-signup'),
       # GET : ログイン中のユーザー情報（フロントの AuthContext が起動時に呼ぶ）
       path('user-info/', UserInfoView.as_view(), name='user_info'),
    #    path("files/upload/", FileUpload.as_view(), name="file-upload"),
]
