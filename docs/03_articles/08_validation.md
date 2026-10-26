# バリデーション（画像・コメント）とサインアップの権限

- 改修案件2で、要件定義書の「画像サイズ制限：最大 5MB / 枚」などの入力チェックを、Backend と Frontend の両方に入れた。
- あわせて、サインアップ API を管理者（スタッフ権限のあるユーザー）だけが使えるようにした。

- [バリデーション（画像・コメント）とサインアップの権限](#バリデーション画像コメントとサインアップの権限)
  - [0. 考え方](#0-考え方)
    - [■ フロントとバックの役割分担](#-フロントとバックの役割分担)
    - [■ DRF のチェックの順番](#-drf-のチェックの順番)
  - [1. プロジェクトディレクトリ](#1-プロジェクトディレクトリ)
    - [■ ライブラリのインストール](#-ライブラリのインストール)
    - [■ 設定（settings.py）:日本語化と上限値](#-設定settingspy日本語化と上限値)
  - [2. アプリディレクトリ](#2-アプリディレクトリ)
    - [■ シリアライザー(serializers.py):画像とコメント](#-シリアライザーserializerspy画像とコメント)
    - [■ ビュー(views.py):サインアップを管理者だけに](#-ビューviewspyサインアップを管理者だけに)
  - [3. フロントエンド](#3-フロントエンド)
    - [■ チェック関数(src/utils/validators.ts)](#-チェック関数srcutilsvalidatorsts)
    - [■ API エラーの変換(src/utils/apiError.ts)](#-api-エラーの変換srcutilsapierrorts)
    - [■ 画面での使い方](#-画面での使い方)
  - [4. テスト手順(PowerShellでCurlコマンドを実行)](#4-テスト手順powershellでcurlコマンドを実行)
  - [5. つまずきやすいところ](#5-つまずきやすいところ)


## 0. 考え方

### ■ フロントとバックの役割分担
| | フロント | バック |
|---|---|---|
| 目的 | 送る前に早く気づかせる（使いやすさ） | 不正なデータを保存させない（守り） |
| 回避できるか | 開発者ツールや curl で回避できる | 回避できない |
| 今回チェックすること | 拡張子・サイズ・文字数 | 拡張子・サイズ・文字数・**中身が本当に画像か** |

- 本当の守りは Backend。フロントのチェックは「おまけ」と考える。
- 上限値は、両方で同じ値にそろえる（Backend は `settings.py`、Frontend は `validators.ts`）。

### ■ DRF のチェックの順番
- DRF は、受け取ったデータを次の順番でチェックする。どこかで失敗すると、その時点で 400 になる。

```
① フィールドの型チェック   … ImageField なら「本当に画像か」（Pillow が中身を確認する）
        ↓
② フィールドの validators … FileExtensionValidator なら「拡張子が許可されたものか」
        ↓
③ validate_<フィールド名>() … 自分で書くチェック（今回はファイルサイズ）
        ↓
④ validate()              … 複数のフィールドにまたがるチェック（今回は使わない）
        ↓
   すべて OK なら create() / update() へ
```

- エラーは、フィールドごとにまとめて返ってくる。
```json
{"upload": ["画像サイズは5MB以下にしてください"], "comment": ["この項目は1000文字より長くならないようにしてください。"]}
```


## 1. プロジェクトディレクトリ

### ■ ライブラリのインストール
- `ImageField` で画像の中身を確認するには、Pillow が必要。

```bash
pip install Pillow
```

- `requirements.txt` に `Pillow==12.3.0` を追加する。
- Windows PowerShell 5.1 で `pip freeze > requirements.txt` を実行すると、UTF-16 で保存されてしまう。次のように書く。
```powershell
pip freeze | Out-File -Encoding utf8 requirements.txt
```

### ■ 設定（settings.py）:日本語化と上限値
- `LANGUAGE_CODE = 'ja'` にすると、DRF / Django 標準のエラーメッセージ（「この項目は必須です。」など）が日本語になる。管理画面も日本語になる。
- 上限値は `serializers.py` に直書きせず、`settings.py` にまとめる。

```python
LANGUAGE_CODE = 'ja'

# アップロード画像の最大サイズ（バイト）：5MB
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

# アップロードを許可する拡張子（小文字で書く。大文字の .JPG も通る）
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']

# コメントの最大文字数（モデルは TextField のまま。シリアライザーで制限するので、マイグレーション不要）
MAX_COMMENT_LENGTH = 1000
```


## 2. アプリディレクトリ

### ■ シリアライザー(serializers.py):画像とコメント
- `upload` を `FileField` から `ImageField` に変えて（チェック順 ①）、拡張子の validator を付ける（②）。
  - `ImageField` だけだと、Pillow が読める形式（`.bmp` `.tiff` など）はすべて通ってしまう。そのため、拡張子で絞る。
- ファイルサイズは、`validate_upload` で自分でチェックする（③）。
- `comment` の最大文字数は `extra_kwargs` で付ける。モデルから自動で作られるフィールドに、オプションを追加する書き方。

```python
from django.conf import settings
from django.core.validators import FileExtensionValidator


class SnapCreateSerializer(serializers.ModelSerializer):
    upload = serializers.ImageField(
        write_only=True,
        validators=[FileExtensionValidator(allowed_extensions=settings.ALLOWED_IMAGE_EXTENSIONS)],
    )
    filePath = serializers.CharField(source='file.path', read_only=True)

    class Meta:
        model = Snap
        fields = ['id', 'comment', 'upload', 'filePath']
        extra_kwargs = {
            'comment': {'max_length': settings.MAX_COMMENT_LENGTH},
        }

    def validate_upload(self, value):
        if value.size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            raise serializers.ValidationError(f'画像サイズは{max_mb}MB以下にしてください')
        return value  # return を忘れると None になる
```

- 更新（`SnapUpdateSerializer`）にも、同じ `extra_kwargs` を付ける。片方だけだと、「作成では弾かれるのに、更新なら 1001 文字にできる」という穴になる。

> 💡 `validate_<フィールド名>` は、名前で自動的に呼ばれる。`validate_update` のように1文字でも間違えると、**エラーにならず黙って無視される**。

### ■ ビュー(views.py):サインアップを管理者だけに
- サインアップ画面は作らない。API は、運用で Postman からユーザーを作るために残す。
- `IsAdminUser` は、`is_staff=True` のユーザーだけを許可する。
  - `createsuperuser` で作ったユーザー → `is_staff=True`
  - この API で作ったユーザー → `is_staff=False`（一般ユーザー）
- 誰がリクエストしたかを知る必要があるので、`authentication_classes = []` は書かない（デフォルトの Cookie 認証を使う）。

```python
from rest_framework.permissions import IsAdminUser


class UserSignup(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        # （変更なし）
```

| リクエストした人 | 結果 |
|---|---|
| 未ログイン | 401（誰か分からない） |
| 一般ユーザー | 403（誰かは分かったが、許可していない） |
| 管理者 | 201（登録できる） |


## 3. フロントエンド

### ■ チェック関数(src/utils/validators.ts)
- 上限値は Backend と同じにする。
- 関数は、問題があればエラーメッセージを、問題なければ `null` を返す。

```ts
export const MAX_UPLOAD_SIZE = 5 * 1024 * 1024;
export const ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
export const IMAGE_ACCEPT = ALLOWED_IMAGE_EXTENSIONS.map((ext) => `.${ext}`).join(',');  // ".jpg,.jpeg,..."
export const MAX_COMMENT_LENGTH = 1000;

export const validateImageFile = (file: File): string | null => {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (!ALLOWED_IMAGE_EXTENSIONS.includes(ext)) {
    return `アップロードできるのは ${ALLOWED_IMAGE_EXTENSIONS.join(' / ')} の画像だけです`;
  }
  if (file.size > MAX_UPLOAD_SIZE) {
    return `画像サイズは ${MAX_UPLOAD_SIZE / (1024 * 1024)}MB 以下にしてください`;
  }
  return null;
};

export const validateComment = (comment: string): string | null => {
  if (comment.length > MAX_COMMENT_LENGTH) {
    return `コメントは ${MAX_COMMENT_LENGTH} 文字以内で入力してください（現在 ${comment.length} 文字）`;
  }
  return null;
};
```

### ■ API エラーの変換(src/utils/apiError.ts)
- DRF のエラーを、画面に出す文章の配列に変える。

| レスポンス | 変換後 |
|---|---|
| `{"upload": ["画像サイズは..."]}` | `画像：画像サイズは...` |
| `{"detail": "このアクションを実行する権限がありません。"}` | `このアクションを実行する権限がありません。` |
| レスポンスなし（サーバーが止まっている） | `サーバーに接続できませんでした。…` |
| 500 番台 | `サーバーでエラーが発生しました` |

```ts
const FIELD_LABELS: Record<string, string> = {
  upload: '画像',
  comment: 'コメント',
};

export const getApiErrorMessages = (error: unknown): string[] => {
  if (!axios.isAxiosError(error)) return ['想定外のエラーが発生しました'];
  if (!error.response) return ['サーバーに接続できませんでした。時間をおいて再度お試しください'];
  if (error.response.status >= 500) return ['サーバーでエラーが発生しました'];

  const data = error.response.data;
  if (data && typeof data === 'object' && typeof data.detail === 'string') return [data.detail];

  if (data && typeof data === 'object') {
    const messages = Object.entries(data).flatMap(([field, value]) => {
      const list = Array.isArray(value) ? value : [value];
      const label = FIELD_LABELS[field];
      return list.map((message) => (label ? `${label}：${message}` : String(message)));
    });
    if (messages.length > 0) return messages;
  }
  return ['エラーが発生しました'];
};
```

### ■ 画面での使い方
- **FileInput.tsx**
  - `accept={IMAGE_ACCEPT}` で、選択ダイアログに許可した拡張子だけを表示する。
  - ドロップでは `accept` が効かない。そのため、選択時とドロップ時の両方で `validateImageFile` を呼び、エラーは `Message`（`mode="error"`）で表示する。
  - あわせて、ドラッグ中の枠表示が消えない不具合を直した。`classList.remove('dragover')` を `classList.remove(styles.dragover)` にする。CSS Modules のクラス名は `FileInput_dragover__a1b2c` のように自動で変換されるため、文字列では外れない。
- **SnapshotPage.tsx**
  - 保存の前に `validateComment` を呼ぶ。API エラーは `getApiErrorMessages` で文章にして、モーダル内に表示する。
  - 文字数カウンター（`123 / 1000`）も付けた。上限を超えると赤くなる。
- **SignInPage.tsx**：未入力とログイン失敗のメッセージを表示する。


## 4. テスト手順(PowerShellでCurlコマンドを実行)
- 事前に [07_cookieAuth.md](07_cookieAuth.md) のテスト手順 1〜4 で、ログインと `$csrf` の設定を済ませておく。

1. **6MB を超える画像** → 400 `{"upload":["画像サイズは5MB以下にしてください"]}`
    ```bash
    curl.exe -b cookies.txt -X POST http://localhost:8000/chocolatier_api/snap/create/ `
      -H "X-CSRFToken: $csrf" `
      -F "upload=@C:/big.png" -F "comment=大きい画像"
    ```

2. **中身がテキストの .png**（テキストファイルの拡張子を変えたもの） → 400 `{"upload":["有効な画像をアップロードしてください。…"]}`
    ```bash
    curl.exe -b cookies.txt -X POST http://localhost:8000/chocolatier_api/snap/create/ `
      -H "X-CSRFToken: $csrf" `
      -F "upload=@C:/fake.png"
    ```

3. **.bmp** → 400 `{"upload":["ファイル拡張子 “bmp” は許可されていません。…"]}`

4. **1001 文字のコメントで更新** → 400 `{"comment":["この項目は1000文字より長くならないようにしてください。"]}`

5. **サインアップ**
    ```bash
    curl.exe -b cookies.txt -X POST http://localhost:8000/chocolatier_api/signup/ `
      -H "Content-Type: application/json" `
      -H "X-CSRFToken: $csrf" `
      -d '{\"username\":\"bob\",\"email\":\"bob@example.com\",\"password\":\"your-secret-password\"}'
    ```
    - 管理者でログインしていれば 201、一般ユーザーなら 403、未ログインなら 401。


## 5. つまずきやすいところ

| 症状 | 原因 |
|---|---|
| 6MB の画像が通ってしまう | `validate_upload` の名前の打ち間違い（例：`validate_update`）。エラーにならず、黙って無視される |
| テキストを .png にしたものが通ってしまう | `upload` が `FileField` のまま |
| `.bmp` が通ってしまう | `FileExtensionValidator` を付けていない |
| エラーメッセージが英語 | `LANGUAGE_CODE` が `'en-us'` のまま |
| requirements.txt が文字化けする | `pip freeze >` で UTF-16 になっている |
