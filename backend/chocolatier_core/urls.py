# =========================================================
# chocolatier_core/urls.py（プロジェクト全体の URL の入口）
# - settings.py の ROOT_URLCONF で、このファイルが入口に指定されている
# - リクエストの URL を上から順に照合し、一致した View に処理を渡す
# - アプリ固有の URL は chocolatier_api/urls.py にまとめ、include で取り込んでいる
# =========================================================
from django.contrib import admin
from django.urls import path, include
from django.conf import settings                  # DEBUG / MEDIA_URL / MEDIA_ROOT を読むため
from django.conf.urls.static import static        # 開発中にアップロード画像を配信するため
# 認証まわりの View（Cookie に JWT を出し入れする）
# - 以前は simplejwt 標準の TokenObtainPairView / TokenRefreshView を使っていたが、
#   それらはトークンをレスポンス本文で返すため、Cookie 版に差し替えた
from chocolatier_api.views import CookieLoginView, CookieRefreshView, LogoutView, CsrfView

urlpatterns = [
    # Django 標準の管理画面（こちらは Django のセッション認証で動く）
    path('admin/', admin.site.urls),

    # アプリの API（/chocolatier_api/snap/ など）
    path('chocolatier_api/', include('chocolatier_api.urls')),

    # ---------------------------------------------------------
    # 認証 API
    # - どれも未ログイン（または期限切れ）の状態で呼ばれるため、
    #   View 側で authentication_classes = [] / AllowAny にしている
    # ---------------------------------------------------------
    path('token/', CookieLoginView.as_view(), name='token_obtain_pair'),        # POST: ログイン → Cookie をセット
    path('token/refresh/', CookieRefreshView.as_view(), name='token_refresh'),  # POST: access を取り直す
    path('logout/', LogoutView.as_view(), name='logout'),                       # POST: Cookie を削除
    path('csrf/', CsrfView.as_view(), name='csrf'),                             # GET : csrftoken Cookie を配布
]

# 開発中（DEBUG=True）だけ、Django 自身が /media/ 以下のアップロード画像を配信する
# - これがないと、フロントの <img src="http://localhost:8000/media/..."> が 404 になる
# - 本番では Nginx などの Web サーバーが配信する想定
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
