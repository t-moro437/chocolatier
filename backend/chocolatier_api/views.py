# =========================================================
# views.py
# - API の「窓口」を置くファイル
# - urls.py で URL とこのファイルのクラスが結びつけられ、
#   リクエストが来るとクラスの get / post などが呼ばれる
# - 認証（誰か？）と権限（使ってよいか？）は settings.py の REST_FRAMEWORK で
#   全 API 共通に設定済み。例外にしたい View だけ、クラス変数で上書きする
#     - authentication_classes : 認証クラス（Cookie の JWT を読むかどうか）
#     - permission_classes     : 権限クラス（ログイン必須かどうか）
# =========================================================
from django.conf import settings                                   # settings.py の値（Cookie 名・有効期限など）
from django.utils.decorators import method_decorator               # 関数用デコレーターをクラスに付けるため
from django.views.decorators.csrf import ensure_csrf_cookie        # csrftoken Cookie を必ず発行するデコレーター
from rest_framework import generics, status                        # generics: 一覧・詳細などの定型 View / status: HTTP ステータスコード
from rest_framework.exceptions import AuthenticationFailed         # 認証失敗の例外（パスワード違いなど）
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser  # AllowAny: 誰でも可 / IsAuthenticated: ログイン必須
from rest_framework.response import Response                       # API のレスポンス（JSON）を返すクラス
from rest_framework.views import APIView                           # 自分で get / post を書く基本の View
from rest_framework_simplejwt.exceptions import TokenError         # JWT が不正・期限切れのときの例外
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer  # ログイン用 / refresh 用のトークン発行処理

from .models import Snap,Tag
from .pagination import SnapCursorPagination
from .serializers import (
    SnapSerializer,
    SnapCreateSerializer,
    SnapUpdateSerializer,
    SnapDeleteSerializer,
    UserSerializer
)

# =========================================================
# SnapList
# - get: 一覧取得：/snaps/
# - ログインユーザー自身のスナップのみ、新しい順で返す
# - permission_classes を書いていないので、settings.py の
#   IsAuthenticated（ログイン必須）が適用される
# =========================================================
class SnapList(generics.ListAPIView):
    serializer_class = SnapSerializer

    # 12 件ずつ返す（pagination.py の SnapCursorPagination）
    # - レスポンスが配列から { next, previous, results } の形に変わる
    # - ?tag=〇〇 は next の URL にそのまま引き継がれる（絞り込んだまま続きを取れる）
    pagination_class = SnapCursorPagination

    # 一覧に出すデータを決めるメソッド
    def get_queryset(self):
        # ① 自分の Snap を新しい順で取得（File と tags はまとめて取得して N+1 を防ぐ）
        #    - self.request.user は、Cookie の JWT から特定したログインユーザー
        queryset = (
            Snap.objects
            .filter(user=self.request.user)
            .select_related('file')   # 多対1：JOIN で一緒に取る
            .prefetch_related('tags') # 多対多：別の SQL 1 回で取る
            .order_by('-created_at')
        )

        # ② URL の ?tag=〇〇 を読む（例：/snaps/?tag=旅行 → "旅行"、指定なしなら None）
        tag =self.request.query_params.get('tag')

        # ③ tag が指定されていたら、そのタグが付いた Snap だけに絞る
        #    - tags__name：Snap → tags → name の順にたどる（__ で関連先の項目を指定する）
        if tag:
            queryset = queryset.filter(tags__name=tag)

        return queryset

# =========================================================
# SnapDetail
# - get: 詳細取得
# - patch: 更新（ファイルは更新しない）
# - delete: 削除
# - 他人のスナップは get_queryset に含まれないため 404 になる
# =========================================================
class SnapDetail(generics.RetrieveUpdateDestroyAPIView):

    # 取得・更新・削除の対象になるデータの範囲
    # - URL の <int:pk> は、この範囲の中から探される
    # - 他人の Snap の ID を指定しても「見つからない」＝ 404 になる
    #   （403 にしないのは「その ID の投稿が存在すること」自体を知らせないため）
    def get_queryset(self):
        return Snap.objects.filter(user=self.request.user)

    # HTTP メソッドごとに使うシリアライザーを切り替える
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SnapUpdateSerializer   # コメントだけ更新
        elif self.request.method == 'DELETE':
            return SnapDeleteSerializer   # 実ファイルも一緒に削除
        return SnapSerializer             # GET（詳細表示）

    def destroy(self, request, *args, **kwargs):
        # get_object() も get_queryset() の範囲から探すので、他人の Snap なら 404
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # ここで SnapDeleteSerializer.delete() を呼ぶ
        serializer.delete(instance)
        return Response(
            {"message": f"Snap {instance.id} and related file deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

# =========================================================
# SnapCreate
# - post: スナップ新規作成
# - 投稿者はフロントから受け取らず、ログインユーザーを使う
# =========================================================
class SnapCreate(generics.CreateAPIView):
    queryset = Snap.objects.all()
    serializer_class = SnapCreateSerializer

    # serializer.save() の直前に呼ばれるメソッド
    # - 以前はフロントが JWT を自分でデコードして user を送っていたため、
    #   値を書き換えれば「他人として投稿」できてしまった
    # - ここでサーバー側のログインユーザーを渡すことで、なりすましを防ぐ
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# =========================================================
# TagList
# - get: 自分の Snap に付いているタグ一覧：/tags/（例：["カフェ", "旅行"]）
# =========================================================
class TagList(APIView):
    def get(self, request):
        # ① 自分の Snap に付いているタグだけ（他の人のタグは出さない）
        # ② distinct：同じタグが複数の Snap に付いていても 1 つにする
        # ③ values_list：名前だけの配列にする
        names = (
            Tag.objects
            .filter(snaps__user=request.user)
            .distinct()
            .values_list('name', flat=True)
        )
        return Response(list(names))



# =========================================================
# UserSignup
# - post: ユーザー新規登録
# - サインアップ画面は作らず、運用で Postman からユーザーを作るために使う
# - 管理者（is_staff=True のユーザー）だけが使える
#   - createsuperuser で作ったユーザーは is_staff=True
#   - この API で作ったユーザーは is_staff=False（一般ユーザー）
# - 以前は authentication_classes = [] / AllowAny で、誰でも登録できてしまっていた
# =========================================================
class UserSignup(APIView):
    # authentication_classes を書かない → settings.py の CookieJWTAuthentication が使われる
    #   （誰がリクエストしたかを知る必要があるため、認証は外さない）
    # IsAdminUser：
    #   - 未ログイン           → 401
    #   - ログイン中だが一般ユーザー → 403
    #   - ログイン中の管理者      → 登録できる
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "ユーザー登録が完了しました"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =========================================================
# UserInfoView
# - get: ログイン中ユーザー情報取得
# - フロントは起動時・ログイン直後にこれを呼び、
#   「今ログインしているのは誰か」を AuthContext に保存する
# - Cookie が無い・期限切れなら 401 → フロントが refresh を試す
# =========================================================
class UserInfoView(APIView):
    # settings.py でも IsAuthenticated にしているが、意図を明確にするため明記
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

# =========================================================
# 認証 Cookie の共通処理
# - ログイン時と refresh 時の両方で使うので関数にまとめている
# - access  : API を呼ぶときに使うトークン（有効期限 60 分）
# - refresh : access を取り直すためのトークン（有効期限 1 日）
#             refresh 時は新しい refresh が発行されないことがあるので省略可能
# =========================================================
def set_auth_cookies(response, access, refresh=None):
    # 2 つの Cookie に共通のオプション
    cookie_options = {
        'httponly': True,                           # JS（document.cookie）から読めない → XSS でトークンを盗まれない
        'secure': settings.AUTH_COOKIE_SECURE,      # True なら HTTPS のときだけ送る（開発は http なので False）
        'samesite': settings.AUTH_COOKIE_SAMESITE,  # 'Lax' : 別サイトからの POST などでは送らない（CSRF の軽減）
        'path': '/',                                # どの URL へのリクエストでも送る
    }

    # access_token の Cookie
    # - max_age（秒）をトークンの有効期限に合わせ、期限が切れたらブラウザからも消えるようにする
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        access,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        **cookie_options  # 上の辞書をキーワード引数として展開する
    )

    # refresh_token の Cookie（渡されたときだけ）
    if refresh:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH,
            refresh,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            **cookie_options
        )

# =========================================================
# CookieLoginView
# - post: ログイン。トークンは Cookie にセットし、本文には含めない
# - authentication_classes = [] にしないと、期限切れ Cookie が残っているだけで 401 になる
#   （DRF はどの View でも、処理の前に必ず認証を実行するため）
# - URL: /token/（chocolatier_core/urls.py で登録）
# =========================================================
class CookieLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # simplejwt 標準のログイン処理
        # - username / password を検証し、正しければ access と refresh を発行する
        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError):
            # パスワード違いなど
            # - 「ユーザー名」と「パスワード」のどちらが違うかは、あえて教えない
            #   （存在するユーザー名を推測されないようにするため）
            return Response(
                {"detail": "ユーザー名またはパスワードが違います"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 本文にはトークンを入れない（JS に渡さない）
        response = Response({"message": "ログインしました"}, status=status.HTTP_200_OK)
        # トークンは Cookie に入れて返す → 以降はブラウザが自動で送ってくれる
        set_auth_cookies(
            response,
            serializer.validated_data['access'],
            serializer.validated_data['refresh']
        )
        return response

# =========================================================
# CookieRefreshView
# - post: Cookie の refresh から新しい access を発行する
# - フロントの client.ts が、API で 401 を受けたときに自動で呼ぶ
# - URL: /token/refresh/
# =========================================================
class CookieRefreshView(APIView):
    # access が期限切れの状態で呼ばれる API なので、認証は外す
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # ① Cookie から refresh_token を取り出す（JS は触れないので、本文ではなく Cookie から読む）
        refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if refresh is None:
            # refresh も無い（1 日以上経った・ログアウト済み）→ 再ログインが必要
            return Response({"detail": "refresh token がありません"}, status=status.HTTP_401_UNAUTHORIZED)

        # ② simplejwt 標準の refresh 処理で、新しい access を発行する
        serializer = TokenRefreshSerializer(data={'refresh': refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError):
            # refresh が期限切れ・改ざん、またはユーザーが無効化されている
            return Response({"detail": "refresh token が無効です"}, status=status.HTTP_401_UNAUTHORIZED)

        # ③ 新しい access（と、発行されていれば新しい refresh）を Cookie に入れ直す
        response = Response({"message": "トークンを更新しました"}, status=status.HTTP_200_OK)
        set_auth_cookies(
            response,
            serializer.validated_data['access'],
            serializer.validated_data.get('refresh')  # ローテーション無効時は None
        )
        return response

# =========================================================
# LogoutView
# - post: 認証 Cookie を削除する
# - HttpOnly Cookie は JS から消せないので、サーバーに消してもらう必要がある
# - URL: /logout/
# =========================================================
class LogoutView(APIView):
    # access が期限切れでもログアウトできるように、認証は外す
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({"message": "ログアウトしました"}, status=status.HTTP_200_OK)
        # set_cookie と同じ path / samesite を指定しないと、別の Cookie 扱いになって消えない
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS, path='/', samesite=settings.AUTH_COOKIE_SAMESITE)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH, path='/', samesite=settings.AUTH_COOKIE_SAMESITE)
        return response

# =========================================================
# CsrfView
# - get: csrftoken Cookie を配布する（フロント起動時に呼ぶ）
# - csrftoken は HttpOnly ではない Cookie なので、JS（axios）が読める
#   → axios が値を X-CSRFToken ヘッダーにコピーして送る
#   → authentication.py の enforce_csrf が、Cookie とヘッダーの一致を確かめる
# - URL: /csrf/
# =========================================================
# ensure_csrf_cookie は関数用のデコレーターなので、method_decorator で
# クラスの dispatch（全メソッドの入口）に付ける
@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "CSRF cookie set"})