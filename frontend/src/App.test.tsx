import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import WelcomePage from './pages/WelcomePage/WelcomePage';

// =====================================================
// 最小のテスト：Welcome 画面が表示されること
// - 以前は CRA の初期テスト（「learn react」のリンクを探す）のままで、必ず失敗していた
// - App 全体ではなく WelcomePage だけを表示する
//   （App は起動時に AuthContext が API を呼ぶため、テストではサーバーがなくて失敗する）
// - MemoryRouter：ブラウザの URL を使わない Router。useNavigate や Link を使う画面に必要
// - 実行：frontend フォルダで npm test
// =====================================================
test('Welcome 画面にタイトルとサインインへのボタンが表示される', () => {
  // ① WelcomePage を「/」にいる状態で表示する
  render(
    <MemoryRouter initialEntries={['/']}>
      <WelcomePage />
    </MemoryRouter>
  );

  // ② タイトルとボタンがあるか確かめる
  expect(screen.getByRole('heading', { name: 'Chocolatier' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'サインインページはこちら' })).toBeInTheDocument();
});
