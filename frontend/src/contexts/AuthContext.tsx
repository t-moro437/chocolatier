import { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import client, { setOnUnauthorized } from '../api/client';
import { AuthContextType, User } from '../types/AuthContextType';

// AuthContextの作成
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// カスタムフック
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

// AuthProvider の props 型
interface AuthProviderProps {
  children: ReactNode;
}

// =====================================================
// AuthProvider
// - ログイン状態（user）をアプリ全体で共有する
// - トークンは HttpOnly Cookie にあり JS からは読めないため、
//   「ログイン中かどうか」はサーバーに user-info を問い合わせて判断する
//   （以前は localStorage にトークンを保存していた）
// =====================================================
export function AuthProvider({ children }: AuthProviderProps): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);  // 起動時の問い合わせが終わるまで true

  // ユーザー情報取得（Cookie はブラウザが自動で送る）
  const fetchUserInfo = async (): Promise<void> => {
    const response = await client.get<User>('/chocolatier_api/user-info/');
    setUser(response.data);
  };

  // =====================================================
  // 起動時
  // - csrftoken Cookie を受け取る（更新系の API で X-CSRFToken ヘッダーに使う）
  // - Cookie が有効ならログイン中のユーザーを取得する
  //   access_token が期限切れでも、client.ts が自動で refresh してくれる
  // =====================================================
  useEffect(() => {
    // ログイン切れになったら user を空にする（→ ProtectedRoute がサインインへ）
    setOnUnauthorized(() => setUser(null));

    const init = async () => {
      try {
        await client.get('/csrf/');
        await fetchUserInfo();
      } catch {
        setUser(null);  // 未ログイン
      } finally {
        setLoading(false);
      }
    };
    init();

    return () => setOnUnauthorized(null);
  }, []);

  // ログイン（トークンはサーバーが Cookie にセットする）
  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      await client.post('/token/', { username, password });
      await fetchUserInfo();
      return true;
    } catch (error) {
      console.error('Login failed', error);
      return false;
    }
  };

  // ログアウト（HttpOnly Cookie は JS から消せないので、サーバーに消してもらう）
  const logout = async (): Promise<void> => {
    try {
      await client.post('/logout/');
    } finally {
      // 通信に失敗しても、画面上はログアウト状態にする
      setUser(null);
    }
  };

  const value: AuthContextType = { user, setUser, login, logout };

  return (
    <AuthContext.Provider value={value}>
      {/* 問い合わせ中に描画すると、ログイン中でも一瞬サインイン画面に飛ばされるため待つ */}
      {!loading && children}
    </AuthContext.Provider>
  );
}
