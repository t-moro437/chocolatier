import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import styles from './Header.module.css';

function Header() {
  // AuthContextからユーザー情報とログアウト関数を取得
  const { user, logout } = useAuth();

  // ナビゲーション用のフック
  const navigate = useNavigate();

  //ホーム画面に戻る
  const handleGoHome = () => {
    navigate('/');
  }

  // ログイン状態は AuthContext の user で判断する
  // - user は state なので、ログイン／ログアウトするとすぐ再描画される
  // - 以前は localStorage を直接読んでいたため、表示が切り替わらないことがあった
  const isLoggedIn = !!user;

  // ログアウト処理（サーバーに Cookie を消してもらってから移動する）
  const handleLogout = async () => {
    await logout();
    navigate('/signin');
  };

  return (
    // ヘッダー
    <header className={styles.siteHeader}>
      <div className={styles.headerContent}>
        <h1><span onClick={handleGoHome}>Chocolatier</span></h1>
          {isLoggedIn && (
          <span onClick={handleLogout}>ログアウト</span>
        )}
      </div>
    </header>
  );
}

export default Header;
