# =========================================================
# authentication.py
# - 「リクエストしてきたのは誰か？」を判定する認証クラスを置くファイル
# - settings.py の REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] に
#   登録すると、すべての API でこの判定が自動的に行われる
# =========================================================
from django.conf import settings             # settings.py の値（Cookie 名など）を読むため
from rest_framework import exceptions          # DRF のエラー（403 など）を発生させるため
from rest_framework.authentication import CSRFCheck  # Django の CSRF チェック処理を DRF から使うため
from rest_framework_simplejwt.authentication import JWTAuthentication  # JWT を検証する元のクラス


# =========================================================
# CSRF チェック
# - Cookie は「ブラウザが自動で送る」ため、悪意のある別サイトからでも
#   ログイン中のユーザーとしてリクエストを送れてしまう（CSRF 攻撃）
# - それを防ぐため、Cookie の csrftoken と、ヘッダーの X-CSRFToken が
#   一致しているかを確かめる（別サイトは Cookie の中身を読めないので一致させられない）
# - DRF の SessionAuthentication.enforce_csrf と同じ処理
# - GET などの「データを変えない」メソッドはチェックされない
# =========================================================
def enforce_csrf(request):
  # CSRFCheck は本来 Django のミドルウェアなので、
  # 「次の処理」を表す関数を渡す必要がある。ここでは使わないのでダミー
  def dummy_get_response(request):
    return None

  check = CSRFCheck(dummy_get_response)

  # Cookie から csrftoken を読み込む準備
  check.process_request(request)

  # 実際のチェック。問題がなければ None、あれば「失敗理由」が返ってくる
  reason = check.process_view(request, None, (), {})
  if reason:
    # 403 Forbidden を返す
    raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')


# =========================================================
# CookieJWTAuthentication
# - 元の JWTAuthentication は「Authorization: Bearer <トークン>」ヘッダーから読む
# - このクラスは、代わりに HttpOnly Cookie（access_token）から読む
# - 戻り値のルール（DRF の認証クラス共通）
#   - (ユーザー, トークン) を返す → ログイン中として扱われる
#   - None を返す      → 未ログインとして扱われる（ログイン必須の API は 401）
#   - 例外を発生させる    → その場でエラーレスポンスになる
# =========================================================
class CookieJWTAuthentication(JWTAuthentication):
  def authenticate(self, request):
    # ① Cookie から access_token を取り出す
    #  Cookie 名は settings.py の AUTH_COOKIE_ACCESS で管理する
    raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS)
    if raw_token is None:
      return None  # Cookie がない＝未ログイン扱い（→ 401）

    # ② トークンが正しいか検証する（署名・有効期限）
    #  期限切れや改ざんなら InvalidToken（401）が発生する
    #  → フロントの client.ts がこの 401 を受けて refresh を試す
    validated_token = self.get_validated_token(raw_token)

    # ③ CSRF チェック（Cookie 認証のときは必須）
    #  トークン検証の後に行うことで、未ログインのリクエストには 403 ではなく 401 を返す
    enforce_csrf(request)

    # ④ トークンに入っている user_id から User を取得して返す
    #  ここで返したユーザーが、View の request.user になる
    return self.get_user(validated_token), validated_token
