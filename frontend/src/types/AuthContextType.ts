// ログイン中のユーザー（/chocolatier_api/user-info/ のレスポンス）
export interface User {
  id: number;
  username: string;
  email: string;
}

// useAuth() で取得できる値
export interface AuthContextType {
  user: User | null;  // 未ログインなら null
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  login: (username: string, password: string) => Promise<boolean>;  // 成功なら true
  logout: () => Promise<void>;  // サーバーに Cookie を消してもらうので非同期
}
