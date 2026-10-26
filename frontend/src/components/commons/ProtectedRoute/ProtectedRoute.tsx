import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';

// =====================================================
// ProtectedRoute
// - ログインが必要なページを囲むためのルート（App.tsx で使用）
// - 未ログインならサインイン画面へ移動させる
// - ログイン中なら <Outlet />（囲んだ子ルートのページ）をそのまま表示する
// =====================================================
function ProtectedRoute() {
  const { user } = useAuth();

  if (!user) {
    // replace: ブラウザの「戻る」で、ログインが必要なページに戻らないようにする
    return <Navigate to="/signin" replace />;
  }
  return <Outlet />;
}

export default ProtectedRoute;
