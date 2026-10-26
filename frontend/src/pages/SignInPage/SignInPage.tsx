import { useState } from 'react';
import '../SignInPage/SignInPage.css';
import BasicButton from '../../components/commons/BasicButton/BasicButton';
import TextInput from '../../components/commons/TextInput/TextInput';
import Message from '../../components/commons/Message/Message';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

function SignInPage() {
  // フォームの各項目値をuseStateで管理する。
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);  // 画面に出すエラーメッセージ

  // AuthContextからlogin関数を取得
  const { login } = useAuth();

  // ナビゲーション用のフック
  const navigate = useNavigate();

  // ユーザー名の入力反映
  const handleUsernameChange = (newUsername: string) => {
    setUsername(newUsername);
  };

  // パスワードの入力反映
  const handlePasswordChange = (newPassword: string) => {
    setPassword(newPassword);
  };

  // 送信
  const handleSubmit = async() => {
    // 未入力チェック（空のまま送ってもサーバーで弾かれるので、送る前に知らせる）
    if (!username.trim() || !password) {
      setError('ユーザー名とパスワードを入力してください');
      return;
    }

    setError(null);
    const success = await login(username, password);
    if (success) {
      navigate('/snaps');
    } else {
      // どちらが違うかは教えない（存在するユーザー名を推測されないようにするため）
      setError('ユーザー名またはパスワードが違います');
    }
  };

  return (
    <div className='formArea'>
        <div>
          <h2>Sign In</h2>
          <div className = "formControl">
            <label>username</label>
            <TextInput value={username} onChangeText={handleUsernameChange} />
          </div>
          <div className = "formControl">
            <label>password</label>
            <TextInput type="password" value={password} onChangeText={handlePasswordChange} />
          </div>
          {error && <Message message={error} mode="error" />}
          <div className = "formControl">
            <BasicButton type="submit" value="signin" onclickAction={()=>handleSubmit()}>Sign in</BasicButton>
          </div>
        </div>
    </div>
  );
}

export default SignInPage;
