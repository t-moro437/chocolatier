# =========================================================
# tests.py
# - API の自動テスト。改修案件1〜4 の受入条件を、いつでも確かめられるようにする
# - 実行：backend フォルダで venv を有効にしてから
#     python manage.py test chocolatier_api
# - テスト用の DB はテストのたびに作られて消える（db.sqlite3 は変わらない）
# - アップロード画像は一時フォルダに保存し、最後に消す（media/ は変わらない）
# =========================================================
import io
import shutil
import tempfile
from itertools import count
from urllib.parse import parse_qs, urlparse

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient, APITestCase

from .models import Snap, Tag, User

# ---------------------------------------------------------
# テストの共通部品
# ---------------------------------------------------------

# アップロード画像の保存先（テスト用の一時フォルダ）
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

# ファイル名の連番
# - 同じ名前の画像を同じ秒に 2 回アップロードすると、File.path の一意制約で 500 になる（既知の不具合）
# - テストでは毎回違う名前にして避ける
_file_number = count()


# テスト用の設定
# - MEDIA_ROOT：アップロード画像を一時フォルダに保存する
# - PASSWORD_HASHERS：パスワードのハッシュ化を軽いものにして、テストを速くする
#   （本物のハッシュ化は、わざと時間がかかるように作られているため。テストの中だけの設定）
TEST_SETTINGS = override_settings(
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)


def tearDownModule():
    # このファイルのテストがすべて終わったら、一時フォルダを消す
    shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


def make_image(size=(2, 2), random_pixels=False):
    # ① テスト用の PNG 画像を作る
    #    - random_pixels=True：ランダムな色で埋める（PNG は圧縮が効かず、ファイルが大きくなる）
    if random_pixels:
        import os
        image = Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3))
    else:
        image = Image.new('RGB', size, 'white')
    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    # ② アップロードされたファイルの形にする
    return SimpleUploadedFile(f'test{next(_file_number)}.png', buffer.getvalue(), content_type='image/png')


# ---------------------------------------------------------
# BaseAPITestCase：Snap を扱うテストの共通の準備
# - alice と bob の 2 人を作り、alice でログインした状態から始める
# - force_authenticate：Cookie のログインを省略して「alice としてリクエストする」
#   （Cookie 認証そのものは CookieAuthTests で確かめる）
# ---------------------------------------------------------
@TEST_SETTINGS
class BaseAPITestCase(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', email='alice@example.com', password='alice-pass')
        self.bob = User.objects.create_user(username='bob', email='bob@example.com', password='bob-pass')
        self.client.force_authenticate(self.alice)

    # Snap を API で作る（multipart）。tags は同じキーで繰り返し送られる
    def create_snap(self, comment='テスト', tags=None):
        data = {'comment': comment, 'upload': make_image()}
        if tags is not None:
            data['tags'] = tags
        return self.client.post('/chocolatier_api/snap/create/', data, format='multipart')


# =========================================================
# 改修案件1：Cookie 認証
# =========================================================
@TEST_SETTINGS
class CookieAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='alice@example.com', password='alice-pass')

    def test_login_sets_httponly_cookies_and_hides_tokens(self):
        # ① ログインすると、access / refresh が HttpOnly の Cookie に入る
        response = self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        self.assertEqual(response.status_code, 200)
        for name in ['access_token', 'refresh_token']:
            self.assertIn(name, response.cookies)
            self.assertTrue(response.cookies[name]['httponly'])
        # ② レスポンス本文にはトークンを入れない（JS に渡さない）
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_login_with_wrong_password_returns_401(self):
        response = self.client.post('/token/', {'username': 'alice', 'password': 'wrong'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_cookie_is_sent_automatically_after_login(self):
        # ログインで受け取った Cookie を、テスト用のクライアントが次のリクエストで自動で送る
        self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = self.client.get('/chocolatier_api/user-info/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'alice')

    def test_refresh_issues_new_access_cookie(self):
        self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = self.client.post('/token/refresh/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.cookies)

    def test_refresh_without_cookie_returns_401(self):
        response = self.client.post('/token/refresh/')
        self.assertEqual(response.status_code, 401)

    def test_logout_deletes_cookies(self):
        # Cookie の削除は「値を空にして、有効期限を 0 にする」形で返ってくる
        self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = self.client.post('/logout/')
        self.assertEqual(response.status_code, 200)
        for name in ['access_token', 'refresh_token']:
            self.assertEqual(response.cookies[name].value, '')
            self.assertEqual(response.cookies[name]['max-age'], 0)

    def test_post_without_csrf_token_returns_403(self):
        # enforce_csrf_checks=True：本物のブラウザと同じく CSRF をチェックする
        # （テスト用のクライアントは、ふだんは CSRF のチェックを省略している）
        client = APIClient(enforce_csrf_checks=True)
        client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = client.post('/chocolatier_api/snap/create/', {'upload': make_image()}, format='multipart')
        self.assertEqual(response.status_code, 403)

    def test_post_with_csrf_token_succeeds(self):
        # ① /csrf/ で csrftoken Cookie を受け取る
        client = APIClient(enforce_csrf_checks=True)
        client.get('/csrf/')
        client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        csrf_token = client.cookies['csrftoken'].value
        # ② 同じ値を X-CSRFToken ヘッダーにも付ける（フロントでは axios が自動で付ける）
        response = client.post(
            '/chocolatier_api/snap/create/',
            {'upload': make_image()},
            format='multipart',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 201)


# =========================================================
# 改修案件1：権限（ログイン必須・自分の Snap だけ）
# =========================================================
class PermissionTests(BaseAPITestCase):
    def test_anonymous_requests_return_401(self):
        self.client.force_authenticate(None)  # ログインしていない状態にする
        for url in ['/chocolatier_api/snap/', '/chocolatier_api/tags/', '/chocolatier_api/user-info/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)

    def test_list_returns_only_own_snaps(self):
        self.create_snap('alice の投稿')
        self.client.force_authenticate(self.bob)
        self.create_snap('bob の投稿')

        response = self.client.get('/chocolatier_api/snap/')
        comments = [snap['comment'] for snap in response.data['results']]
        self.assertEqual(comments, ['bob の投稿'])

    def test_other_users_snap_returns_404(self):
        # alice の Snap を、bob が取得・更新・削除しようとする → どれも 404
        snap_id = self.create_snap().data['id']
        self.client.force_authenticate(self.bob)
        url = f'/chocolatier_api/snap/{snap_id}/'

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {'comment': '書き換え'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(Snap.objects.filter(id=snap_id).exists())  # 消えていない

    def test_user_field_from_client_is_ignored(self):
        # なりすまし防止：user に bob の ID を送っても、投稿者はログインユーザー（alice）になる
        response = self.client.post(
            '/chocolatier_api/snap/create/',
            {'upload': make_image(), 'user': self.bob.id},
            format='multipart',
        )
        self.assertEqual(Snap.objects.get(id=response.data['id']).user, self.alice)

    def test_owner_can_update_and_delete(self):
        snap_id = self.create_snap().data['id']
        url = f'/chocolatier_api/snap/{snap_id}/'

        response = self.client.patch(url, {'comment': '更新しました'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comment'], '更新しました')

        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Snap.objects.filter(id=snap_id).exists())


# =========================================================
# 改修案件2：入力チェックとサインアップの権限
# =========================================================
class ValidationTests(BaseAPITestCase):
    def test_png_can_be_uploaded(self):
        self.assertEqual(self.create_snap().status_code, 201)

    def test_image_over_5mb_returns_400(self):
        # 1500×1500 のランダムな色の PNG は、約 6.4MB になる
        big_image = make_image(size=(1500, 1500), random_pixels=True)
        self.assertGreater(big_image.size, 5 * 1024 * 1024)

        response = self.client.post('/chocolatier_api/snap/create/', {'upload': big_image}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('5MB', response.data['upload'][0])

    def test_text_file_with_png_extension_returns_400(self):
        # 中身がテキストの .png（Pillow が画像として読めない）
        fake = SimpleUploadedFile('fake.png', b'this is not an image', content_type='image/png')
        response = self.client.post('/chocolatier_api/snap/create/', {'upload': fake}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('upload', response.data)

    def test_bmp_returns_400(self):
        # 中身は本物の画像でも、許可していない拡張子は弾く
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2)).save(buffer, 'BMP')
        bmp = SimpleUploadedFile('photo.bmp', buffer.getvalue(), content_type='image/bmp')
        response = self.client.post('/chocolatier_api/snap/create/', {'upload': bmp}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('bmp', response.data['upload'][0])

    def test_comment_over_1000_chars_returns_400(self):
        # 作成・更新の両方で弾く（片方だけだと、更新で 1001 文字にできてしまう）
        self.assertEqual(self.create_snap('あ' * 1000).status_code, 201)
        self.assertEqual(self.create_snap('あ' * 1001).status_code, 400)

        snap_id = self.create_snap().data['id']
        response = self.client.patch(f'/chocolatier_api/snap/{snap_id}/', {'comment': 'あ' * 1001}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('comment', response.data)


class SignupPermissionTests(BaseAPITestCase):
    SIGNUP_DATA = {'username': 'carol', 'email': 'carol@example.com', 'password': 'carol-pass'}

    def test_anonymous_returns_401(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/chocolatier_api/signup/', self.SIGNUP_DATA, format='json').status_code, 401)

    def test_general_user_returns_403(self):
        # alice は一般ユーザー（is_staff=False）
        self.assertEqual(self.client.post('/chocolatier_api/signup/', self.SIGNUP_DATA, format='json').status_code, 403)

    def test_admin_can_signup(self):
        admin = User.objects.create_user(username='admin', email='admin@example.com', password='admin-pass', is_staff=True)
        self.client.force_authenticate(admin)
        response = self.client.post('/chocolatier_api/signup/', self.SIGNUP_DATA, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(User.objects.get(username='carol').is_staff)  # 作られるのは一般ユーザー


# =========================================================
# 改修案件3：タグ
# =========================================================
class TagTests(BaseAPITestCase):
    def test_create_with_tags(self):
        # multipart で同じキーを繰り返して送る → 名前順の配列で返る
        response = self.create_snap(tags=['旅行', 'カフェ'])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['tags'], ['カフェ', '旅行'])

    def test_create_without_tags(self):
        response = self.create_snap()
        self.assertEqual(response.data['tags'], [])

    def test_tag_names_are_cleaned(self):
        # 前後の空白を取り、空のタグと重複は捨てる
        response = self.create_snap(tags=[' 旅行 ', '', '旅行', 'カフェ'])
        self.assertEqual(response.data['tags'], ['カフェ', '旅行'])

    def test_same_tag_name_is_shared(self):
        # alice と bob が同じ名前のタグを使っても、tags の表には 1 行だけ
        self.create_snap(tags=['旅行'])
        self.client.force_authenticate(self.bob)
        self.create_snap(tags=['旅行'])
        self.assertEqual(Tag.objects.filter(name='旅行').count(), 1)

    def test_too_many_tags_returns_400(self):
        self.assertEqual(self.create_snap(tags=[f'タグ{i}' for i in range(10)]).status_code, 201)
        response = self.create_snap(tags=[f'タグ{i}' for i in range(11)])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['tags'], ['タグは10個までにしてください'])

    def test_tag_over_30_chars_returns_400(self):
        self.assertEqual(self.create_snap(tags=['あ' * 30]).status_code, 201)
        response = self.create_snap(tags=['あ' * 31])
        self.assertEqual(response.status_code, 400)
        self.assertIn('30文字以内', response.data['tags'][0])

    def test_null_tag_returns_nested_error(self):
        # 要素ごとのエラーは {"tags": {0: [...]}} の入れ子になる（フロントの apiError.ts が対応している形）
        snap_id = self.create_snap().data['id']
        response = self.client.patch(f'/chocolatier_api/snap/{snap_id}/', {'tags': [None]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn(0, response.data['tags'])

    def test_update_replaces_tags(self):
        snap_id = self.create_snap(tags=['旅行', 'カフェ']).data['id']
        url = f'/chocolatier_api/snap/{snap_id}/'

        # ① 送った内容に入れ替わる
        response = self.client.patch(url, {'tags': ['夜景']}, format='json')
        self.assertEqual(response.data['tags'], ['夜景'])
        # ② コメントだけ送ったときは、タグはそのまま
        response = self.client.patch(url, {'comment': 'コメントだけ'}, format='json')
        self.assertEqual(response.data['tags'], ['夜景'])
        # ③ 空の配列を送ると、全部外れる
        response = self.client.patch(url, {'tags': []}, format='json')
        self.assertEqual(response.data['tags'], [])

    def test_filter_by_tag(self):
        self.create_snap('京都', tags=['旅行'])
        self.create_snap('喫茶店', tags=['カフェ'])
        response = self.client.get('/chocolatier_api/snap/', {'tag': '旅行'})
        self.assertEqual([snap['comment'] for snap in response.data['results']], ['京都'])

    def test_tag_list_returns_only_own_tags(self):
        # ① alice は「旅行」を 2 回、「カフェ」を 1 回使う → 重複なし・名前順
        self.create_snap(tags=['旅行'])
        self.create_snap(tags=['旅行', 'カフェ'])
        # ② bob だけが使っているタグは、alice には見えない
        self.client.force_authenticate(self.bob)
        self.create_snap(tags=['bob のタグ'])

        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get('/chocolatier_api/tags/').data, ['カフェ', '旅行'])

    def test_list_query_count_does_not_grow(self):
        # N+1 対策：件数が増えても、一覧の SQL の回数は変わらない
        for i in range(3):
            self.create_snap(tags=['旅行', f'タグ{i}'])
        with self.assertNumQueries(2):  # Snap と File を JOIN で 1 回 ＋ tags をまとめて 1 回
            self.client.get('/chocolatier_api/snap/')


# =========================================================
# 改修案件4：ページング（12 件ずつ・cursor 方式）
# =========================================================
class PaginationTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        # 14 件作る。偶数番目にだけ「旅行」タグを付ける（7 件）
        self.snap_ids = []
        for i in range(14):
            tags = ['旅行'] if i % 2 == 0 else []
            self.snap_ids.append(self.create_snap(str(i), tags=tags).data['id'])
        self.newest_first = self.snap_ids[::-1]

    def ids(self, response):
        return [snap['id'] for snap in response.data['results']]

    def test_first_page_has_12_newest_snaps(self):
        response = self.client.get('/chocolatier_api/snap/')
        self.assertEqual(set(response.data.keys()), {'next', 'previous', 'results'})
        self.assertEqual(self.ids(response), self.newest_first[:12])
        self.assertIn('cursor=', response.data['next'])
        self.assertIsNone(response.data['previous'])

    def test_next_page_has_the_rest(self):
        first = self.client.get('/chocolatier_api/snap/')
        second = self.client.get(first.data['next'])
        self.assertEqual(self.ids(second), self.newest_first[12:])
        self.assertIsNone(second.data['next'])  # 最後まで読んだ

    def test_no_duplicates_when_snap_is_added_while_reading(self):
        # 1 ページ目を読んだあとに新しい投稿が増えても、2 ページ目に重複や抜けがない
        first = self.client.get('/chocolatier_api/snap/')
        self.create_snap('途中で増えた投稿')
        second = self.client.get(first.data['next'])
        self.assertEqual(self.ids(first) + self.ids(second), self.newest_first)

    def test_tag_is_kept_in_next_url(self):
        # 絞り込みでも次のページがあるように、1 ページの件数を一時的に 2 件にする
        from .pagination import SnapCursorPagination
        original = SnapCursorPagination.page_size
        SnapCursorPagination.page_size = 2
        self.addCleanup(setattr, SnapCursorPagination, 'page_size', original)

        response = self.client.get('/chocolatier_api/snap/', {'tag': '旅行'})
        self.assertEqual(parse_qs(urlparse(response.data['next']).query)['tag'], ['旅行'])

        # 最後までたどると、タグ付きの 7 件が重複なく新しい順で取れる
        collected = self.ids(response)
        while response.data['next']:
            response = self.client.get(response.data['next'])
            collected += self.ids(response)
        tagged = [snap_id for i, snap_id in enumerate(self.snap_ids) if i % 2 == 0]
        self.assertEqual(collected, tagged[::-1])

    def test_invalid_cursor_returns_404(self):
        # 不正な cursor は、DRF が NotFound（404）として返す
        response = self.client.get('/chocolatier_api/snap/', {'cursor': 'invalid'})
        self.assertEqual(response.status_code, 404)
