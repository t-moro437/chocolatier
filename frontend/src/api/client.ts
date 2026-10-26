import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// =====================================================
// API の接続先
// - .env に REACT_APP_API_BASE_URL を書くと上書きできる（本番の URL など）
// - 以前は 'http://localhost:8000' が各ファイルに直書きされていた
// =====================================================
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
export const MEDIA_URL = `${API_BASE_URL}/media/`;

// =====================================================
// 共通の axios インスタンス
// - API を呼ぶときは axios ではなく、この client を使う
// - withCredentials: 別オリジン（localhost:8000）への通信でも Cookie を送受信する
//   → HttpOnly Cookie の access_token / refresh_token がブラウザから自動で送られる
// - withXSRFToken / xsrfCookieName / xsrfHeaderName:
//   csrftoken Cookie の値を読み取り、X-CSRFToken ヘッダーに自動で付ける
//   → Django 側（authentication.py の enforce_csrf）で CSRF チェックが通る
// =====================================================
const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

// =====================================================
// ログイン切れ（refresh にも失敗した）ときに呼ぶ処理
// - client.ts は React の外にあるので、AuthContext が setUser(null) を登録する
// - user が null になると、ProtectedRoute がサインイン画面へ移動させる
// =====================================================
let onUnauthorized: (() => void) | null = null;
export const setOnUnauthorized = (handler: (() => void) | null) => {
  onUnauthorized = handler;
};

// 401 になっても refresh を試さない URL
// - ログイン失敗や refresh 自体の失敗で refresh を呼ぶと、無限ループになるため
const AUTH_URLS = ['/token/', '/token/refresh/', '/logout/', '/csrf/'];

// 実行中の refresh
// - 一覧取得などで同時に複数のリクエストが 401 になっても、refresh は 1 回だけにする
let refreshPromise: Promise<void> | null = null;

// =====================================================
// レスポンスインターセプタ（すべてのレスポンスが通る共通処理）
// - 401（access_token の期限切れなど）のときは
//   ① /token/refresh/ で access_token を取り直す
//   ② 失敗したリクエストを 1 回だけ再送する
// - refresh にも失敗したら、ログイン切れとして onUnauthorized を呼ぶ
// =====================================================
client.interceptors.response.use(
  // 成功時はそのまま返す
  (response) => response,

  // 失敗時
  async (error: AxiosError) => {
    // _retry: このリクエストを既に再送したかどうかの目印（自前で付けるプロパティ）
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    // 次のどれかなら、何もせずにエラーをそのまま返す
    // - 401 以外のエラー（400 のバリデーションエラーなど）
    // - 再送済みのリクエスト（refresh しても 401 だった）
    // - 認証系の URL
    if (
      error.response?.status !== 401 ||
      !original ||
      original._retry ||
      AUTH_URLS.includes(original.url ?? '')
    ) {
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      // ① refresh（実行中のものがあれば、それが終わるのを待つだけ）
      if (!refreshPromise) {
        refreshPromise = client
          .post('/token/refresh/')
          .then(() => undefined)
          .finally(() => {
            refreshPromise = null;
          });
      }
      await refreshPromise;

      // ② 新しい access_token の Cookie で、元のリクエストを再送
      return client(original);
    } catch (refreshError) {
      // refresh_token も期限切れ → ログイン切れ
      onUnauthorized?.();
      return Promise.reject(refreshError);
    }
  }
);

export default client;
