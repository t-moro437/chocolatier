# Cookie 認証（HttpOnly Cookie + JWT + CSRF）

- 改修案件1で、JWT の保存場所を localStorage から **HttpOnly Cookie** に変えた。あわせて、API に権限（ログイン必須・持ち主だけ）を設定した。
- この記事は [03_signin.md](03_signin.md)（Bearer 認証）の後継。今の実装はこちらを参照する。

- [Cookie 認証（HttpOnly Cookie + JWT + CSRF）](#cookie-認証httponly-cookie--jwt--csrf)
  - [0. なぜ Cookie にしたか](#0-なぜ-cookie-にしたか)
    - [■ localStorage の問題](#-localstorage-の問題)
    - [■ Cookie にすると増える問題（CSRF）と対策](#-cookie-にすると増える問題csrfと対策)
    - [■ 変更前と変更後の流れ](#-変更前と変更後の流れ)
  - [1. プロジェクトディレクトリ](#1-プロジェクトディレクトリ)
    - [■ 設定（settings.py）:ミドルウェアの順番](#-設定settingspyミドルウェアの順番)
    - [■ 設定（settings.py）:CORS と CSRF](#-設定settingspycors-と-csrf)
    - [■ 設定（settings.py）:認証・権限と Cookie](#-設定settingspy認証権限と-cookie)
    - [■ ルーティング(urls.py):認証 API を差し替え](#-ルーティングurlspy認証-api-を差し替え)
  - [2. アプリディレクトリ](#2-アプリディレクトリ)
    - [■ 認証クラス(authentication.py)](#-認証クラスauthenticationpy)
    - [■ ビュー(views.py):ログイン・refresh・ログアウト・CSRF](#-ビューviewspyログインrefreshログアウトcsrf)
    - [■ ビュー(views.py):持ち主だけに絞る](#-ビューviewspy持ち主だけに絞る)
  - [3. フロントエンド](#3-フロントエンド)
    - [■ 共通の axios(src/api/client.ts)](#-共通の-axiossrcapiclientts)
    - [■ ログイン状態(src/contexts/AuthContext.tsx)](#-ログイン状態srccontextsauthcontexttsx)
    - [■ ログイン必須のページ(ProtectedRoute.tsx)](#-ログイン必須のページprotectedroutetsx)
  - [4. テスト手順(PowerShellでCurlコマンドを実行)](#4-テスト手順powershellでcurlコマンドを実行)
  - [5. Postman で使うとき](#5-postman-で使うとき)
  - [6. つまずきやすいところ](#6-つまずきやすいところ)


## 0. なぜ Cookie にしたか

### ■ localStorage の問題
- localStorage は JavaScript から自由に読める。
- 画面に悪意のあるスクリプトが入り込む（XSS）と、`localStorage.getItem('access_token')` でトークンを盗まれ、外部に送られてしまう。

### ■ Cookie にすると増える問題（CSRF）と対策
- **HttpOnly** を付けた Cookie は、JavaScript から読めない。そのため、XSS でトークンそのものを盗まれることはない。
- ただし Cookie は**ブラウザが自動で送る**ため、悪意のある別サイトから「ログイン中のあなた」としてリクエストを送られる危険がある（CSRF）。
- 対策として、Django の CSRF トークンを組み合わせる。
  1. `csrftoken` Cookie（HttpOnly ではないので JS から読める）を配る。
  2. フロントは、その値を `X-CSRFToken` ヘッダーにコピーして送る。
  3. サーバーは、Cookie とヘッダーの値が一致しているか確かめる。
  - 別サイトは `csrftoken` の値を読めないので、ヘッダーを正しく付けられない。

### ■ 変更前と変更後の流れ

| 場面 | 変更前 | 変更後 |
|---|---|---|
| ログイン | `token/` がトークンを本文で返し、JS が localStorage に保存 | `token/` が Cookie をセット。JS はトークンに触れない |
| API 呼び出し | JS が `Authorization: Bearer ...` を付ける | ブラウザが Cookie を自動で送る。更新系は `X-CSRFToken` も付ける |
| 期限切れ（60分） | 401 でサインイン画面へ | 401 のとき自動で `token/refresh/` を呼んでやり直す |
| ログアウト | localStorage を消す | `logout/` を呼び、サーバーが Cookie を消す |
| 投稿の作成 | フロントが JWT を読んで user_id を送る | サーバーがログインユーザーを使う |


## 1. プロジェクトディレクトリ

### ■ 設定（settings.py）:ミドルウェアの順番
- `CorsMiddleware` は、`CommonMiddleware` より前に置く。
- 後ろにあると、CORS ヘッダーが付く前にレスポンスが返り、ブラウザで CORS エラーになることがある。

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CommonMiddleware より前に置く
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # ...
]
```

### ■ 設定（settings.py）:CORS と CSRF
- Cookie 付きの通信では、ブラウザの仕様で `CORS_ALLOW_ALL_ORIGINS = True`（`*`）が使えない。許可するオリジンを明示する。
- `CSRF_TRUSTED_ORIGINS` がないと、CSRF トークンが正しくても `CSRF Failed: Origin checking failed` の 403 になる。

```python
CORS_ALLOWED_ORIGINS = ['http://localhost:3000']
CORS_ALLOW_CREDENTIALS = True  # Cookie の送受信を許可（フロントの withCredentials とセット）
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000']
```

### ■ 設定（settings.py）:認証・権限と Cookie
- **認証**（誰か？）は、Cookie から JWT を読む自作クラスにする。
- **権限**（使ってよいか？）は、デフォルトを「ログイン必須」にする。ログインなどの例外は、View ごとに上書きする。

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'chocolatier_api.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

AUTH_COOKIE_ACCESS = 'access_token'
AUTH_COOKIE_REFRESH = 'refresh_token'
AUTH_COOKIE_SECURE = not DEBUG   # 開発(http)では False、本番(https)では True
AUTH_COOKIE_SAMESITE = 'Lax'     # localhost:3000 と :8000 は「同じサイト」扱いなので Lax でも送られる
```

### ■ ルーティング(urls.py):認証 API を差し替え
- simplejwt 標準の `TokenObtainPairView` / `TokenRefreshView` は、トークンを本文で返す。そのため、Cookie 版の View に差し替える。

```python
from chocolatier_api.views import CookieLoginView, CookieRefreshView, LogoutView, CsrfView

urlpatterns = [
    # ...
    path('token/', CookieLoginView.as_view(), name='token_obtain_pair'),        # POST: ログイン
    path('token/refresh/', CookieRefreshView.as_view(), name='token_refresh'),  # POST: access を取り直す
    path('logout/', LogoutView.as_view(), name='logout'),                       # POST: Cookie を削除
    path('csrf/', CsrfView.as_view(), name='csrf'),                             # GET : csrftoken を配布
]
```


## 2. アプリディレクトリ

### ■ 認証クラス(authentication.py)
- `JWTAuthentication` を継承し、「どこからトークンを読むか」だけを Cookie に変える。
- Cookie 認証では CSRF チェックが必須。DRF の `SessionAuthentication.enforce_csrf` と同じ処理を呼ぶ。
- 戻り値のルール
  - `(ユーザー, トークン)` を返す → ログイン中
  - `None` を返す → 未ログイン（ログイン必須の API なら 401）
  - 例外を発生させる → その場でエラー

```python
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication


def enforce_csrf(request):
    def dummy_get_response(request):
        return None

    check = CSRFCheck(dummy_get_response)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS)
        if raw_token is None:
            return None  # 未ログイン扱い（→ 401）

        validated_token = self.get_validated_token(raw_token)  # 期限切れ・改ざんなら 401
        enforce_csrf(request)                                  # GET などはチェックされない
        return self.get_user(validated_token), validated_token
```

### ■ ビュー(views.py):ログイン・refresh・ログアウト・CSRF
- この4つは未ログイン（または期限切れ）の状態で呼ばれるため、`authentication_classes = []` と `AllowAny` にする。
  - DRF はどの View でも、処理の前に必ず認証を実行する。認証を外さないと、**期限切れの Cookie が残っているだけで 401** になり、ログインすらできない。
- ログイン失敗のメッセージでは、ユーザー名とパスワードのどちらが違うかを教えない。存在するユーザー名を推測されないようにするため。

```python
def set_auth_cookies(response, access, refresh=None):
    cookie_options = {
        'httponly': True,                           # JS から読めない（XSS 対策）
        'secure': settings.AUTH_COOKIE_SECURE,
        'samesite': settings.AUTH_COOKIE_SAMESITE,
        'path': '/',
    }
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS, access,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        **cookie_options
    )
    if refresh:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH, refresh,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            **cookie_options
        )


class CookieLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError):
            return Response({"detail": "ユーザー名またはパスワードが違います"},
                            status=status.HTTP_401_UNAUTHORIZED)

        response = Response({"message": "ログインしました"})   # 本文にトークンは入れない
        set_auth_cookies(response, serializer.validated_data['access'], serializer.validated_data['refresh'])
        return response


class CookieRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)  # 本文ではなく Cookie から読む
        if refresh is None:
            return Response({"detail": "refresh token がありません"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={'refresh': refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError):
            return Response({"detail": "refresh token が無効です"}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response({"message": "トークンを更新しました"})
        set_auth_cookies(response, serializer.validated_data['access'], serializer.validated_data.get('refresh'))
        return response


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # HttpOnly Cookie は JS から消せないので、サーバーが消す
        # set_cookie と同じ path / samesite を指定しないと、別の Cookie 扱いになって消えない
        response = Response({"message": "ログアウトしました"})
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS, path='/', samesite=settings.AUTH_COOKIE_SAMESITE)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH, path='/', samesite=settings.AUTH_COOKIE_SAMESITE)
        return response


@method_decorator(ensure_csrf_cookie, name='dispatch')  # csrftoken Cookie を必ず発行する
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "CSRF cookie set"})
```

### ■ ビュー(views.py):持ち主だけに絞る
- `queryset = Snap.objects.all()` をやめて、`get_queryset` でログインユーザーの Snap だけに絞る。
- 他人の Snap の ID を指定すると、403 ではなく 404 になる。「その ID の投稿が存在すること」自体を知らせないため。
- 投稿者はフロントから受け取らず、`perform_create` でサーバー側のログインユーザーを入れる（なりすまし防止）。

```python
class SnapList(generics.ListAPIView):
    serializer_class = SnapSerializer

    def get_queryset(self):
        return Snap.objects.filter(user=self.request.user).order_by('-created_at')


class SnapDetail(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return Snap.objects.filter(user=self.request.user)
    # ...


class SnapCreate(generics.CreateAPIView):
    queryset = Snap.objects.all()
    serializer_class = SnapCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

- あわせて、`SnapCreateSerializer` の `fields` から `'user'` を削除する。


## 3. フロントエンド

### ■ 共通の axios(src/api/client.ts)
- API を呼ぶときは、`axios` を直接使わずにこの `client` を使う。
- 主な設定
  - `withCredentials`：Cookie を送受信する
  - `withXSRFToken` / `xsrfCookieName` / `xsrfHeaderName`：`csrftoken` の値を `X-CSRFToken` ヘッダーに自動で付ける
- 401 になったら、`/token/refresh/` を1回だけ呼んでから元のリクエストを再送する。refresh にも失敗したら、ログイン切れとして扱う。

```ts
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
export const MEDIA_URL = `${API_BASE_URL}/media/`;

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    // 401 以外・再送済み・認証系の URL は、そのままエラーにする（無限ループ防止）
    if (error.response?.status !== 401 || !original || original._retry || AUTH_URLS.includes(original.url ?? '')) {
      return Promise.reject(error);
    }
    original._retry = true;
    try {
      // 同時に複数のリクエストが 401 になっても、refresh は1回だけ
      if (!refreshPromise) {
        refreshPromise = client.post('/token/refresh/').then(() => undefined).finally(() => { refreshPromise = null; });
      }
      await refreshPromise;
      return client(original);
    } catch (refreshError) {
      onUnauthorized?.();  // AuthContext が登録した setUser(null)
      return Promise.reject(refreshError);
    }
  }
);
```

### ■ ログイン状態(src/contexts/AuthContext.tsx)
- トークンは JS から読めないので、「ログイン中かどうか」はサーバーに `user-info/` を問い合わせて判断する。
- 起動時に、`csrf/` → `user-info/` の順に呼ぶ。
- `logout` は `/logout/` を呼んでから `user` を空にする。戻り値は `Promise<void>` に変わる。

```tsx
useEffect(() => {
  setOnUnauthorized(() => setUser(null));  // ログイン切れ → user を空に

  const init = async () => {
    try {
      await client.get('/csrf/');
      await fetchUserInfo();
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };
  init();

  return () => setOnUnauthorized(null);
}, []);
```

- ヘッダーのログイン判定も、`localStorage` ではなく `useAuth().user` で行う。`user` は state なので、ログイン・ログアウトするとすぐに表示が切り替わる。

### ■ ログイン必須のページ(ProtectedRoute.tsx)
```tsx
function ProtectedRoute() {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/signin" replace />;
  }
  return <Outlet />;
}
```

- `App.tsx` で、ログインが必要なページを囲む。
```tsx
<Route element={<ProtectedRoute />}>
  <Route path="/snaps" element={<SnapshotPage />} />
</Route>
```


## 4. テスト手順(PowerShellでCurlコマンドを実行)

- `-c` で受け取った Cookie をファイルに保存し、`-b` でそのファイルの Cookie を送る。これでブラウザと同じように Cookie を使える。
- 更新系（POST / PATCH / DELETE）は、`X-CSRFToken` ヘッダーが必要。

1. **CSRF Cookie を受け取る**
    ```bash
    curl.exe -c cookies.txt http://localhost:8000/csrf/
    ```

2. **ログイン**（`access_token` / `refresh_token` の Cookie が cookies.txt に保存される）
    ```bash
    curl.exe -b cookies.txt -c cookies.txt -X POST http://localhost:8000/token/ `
      -H "Content-Type: application/json" `
      -d '{\"username\":\"alice\",\"password\":\"your-secret-password\"}'
    ```
    - レスポンス（成功）：`{"message":"ログインしました"}`。本文にトークンは入らない。

3. **ユーザー情報取得**（Authorization ヘッダーは不要）
    ```bash
    curl.exe -b cookies.txt http://localhost:8000/chocolatier_api/user-info/
    ```

4. **CSRF トークンの値を変数に入れる**
    ```powershell
    $csrf = (Select-String -Path cookies.txt -Pattern "csrftoken\s+(\S+)$").Matches[0].Groups[1].Value
    ```

5. **コメント更新**（`X-CSRFToken` がないと 403 になる）
    ```bash
    curl.exe -b cookies.txt -X PATCH http://localhost:8000/chocolatier_api/snap/1/ `
      -H "Content-Type: application/json" `
      -H "X-CSRFToken: $csrf" `
      -d '{\"comment\":\"curl から更新\"}'
    ```

6. **アクセストークン更新**（refresh は Cookie から読まれるので、本文は不要）
    ```bash
    curl.exe -b cookies.txt -c cookies.txt -X POST http://localhost:8000/token/refresh/
    ```

7. **ログアウト**（cookies.txt から access_token / refresh_token が消える）
    ```bash
    curl.exe -b cookies.txt -c cookies.txt -X POST http://localhost:8000/logout/
    ```

- 期待する結果

| 確認すること | 結果 |
|---|---|
| ログインせずに `/chocolatier_api/snap/` | 401 |
| `X-CSRFToken` なしで PATCH | 403（`CSRF Failed`） |
| 別ユーザーの Snap の ID で GET / PATCH / DELETE | 404 |
| 作成時に `user` を送る | 無視され、ログインユーザーが投稿者になる |


## 5. Postman で使うとき
- Postman は、受け取った Cookie を自動で保持して次のリクエストで送る。
- 手順
  1. `GET http://localhost:8000/csrf/`
  2. `POST http://localhost:8000/token/`（Body → raw → JSON で username / password）
  3. 以降の API を呼ぶ
- 更新系の `X-CSRFToken` は、コレクションの **Pre-request Script（Scripts → Pre-request）** に次を書くと自動で付く。

```js
// csrftoken Cookie の値を X-CSRFToken ヘッダーに付ける
const csrf = pm.cookies.get('csrftoken');
if (csrf) {
  pm.request.headers.upsert({ key: 'X-CSRFToken', value: csrf });
}
```


## 6. つまずきやすいところ

| 症状 | 原因 |
|---|---|
| 更新系が 403 `CSRF Failed: CSRF token missing` | `X-CSRFToken` ヘッダーがない。または先に `/csrf/` を呼んでいない |
| 更新系が 403 `CSRF Failed: Origin checking failed` | `CSRF_TRUSTED_ORIGINS` にフロントのオリジンがない |
| ブラウザで CORS エラー | `CORS_ALLOW_CREDENTIALS` がない、または `CorsMiddleware` の位置が後ろすぎる |
| ログインしても Cookie が保存されない | フロントの `withCredentials: true` がない |
| ログアウトしても Cookie が消えない | `delete_cookie` の `path` / `samesite` が `set_cookie` と違う |
| 期限切れの Cookie が残っているとログインできない | ログイン View に `authentication_classes = []` がない |
