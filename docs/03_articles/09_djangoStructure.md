# Django（DRF）の全体像：ファイルの役割と開発の順番

- Chocolatier の Backend を例に、「どのファイルが何の役割か」「リクエストがどう流れるか」「どの順番で作るか」をまとめる。
- 新しい機能を作るときの地図として使う。

- [Django（DRF）の全体像：ファイルの役割と開発の順番](#djangodrfの全体像ファイルの役割と開発の順番)
  - [1. 全体の地図](#1-全体の地図)
  - [2. フォルダ構成と役割](#2-フォルダ構成と役割)
    - [■ プロジェクト（chocolatier\_core）とアプリ（chocolatier\_api）](#-プロジェクトchocolatier_coreとアプリchocolatier_api)
    - [■ ファイルごとの役割](#-ファイルごとの役割)
  - [3. 各層の役割](#3-各層の役割)
    - [■ manage.py：操作の入口](#-managepy操作の入口)
    - [■ settings.py：全体の設定](#-settingspy全体の設定)
    - [■ ミドルウェア：全リクエストが通る関所](#-ミドルウェア全リクエストが通る関所)
    - [■ urls.py：振り分け表](#-urlspy振り分け表)
    - [■ views.py：窓口](#-viewspy窓口)
    - [■ authentication.py：誰かを判定する](#-authenticationpy誰かを判定する)
    - [■ serializers.py：翻訳係](#-serializerspy翻訳係)
    - [■ models.py：データの設計図](#-modelspyデータの設計図)
    - [■ マイグレーション：設計図を DB に反映する](#-マイグレーション設計図を-db-に反映する)
    - [■ admin.py：管理画面](#-adminpy管理画面)
  - [4. リクエストの流れ（実例）](#4-リクエストの流れ実例)
    - [■ 例1：一覧を取得する（GET）](#-例1一覧を取得するget)
    - [■ 例2：画像を投稿する（POST）](#-例2画像を投稿するpost)
  - [5. 開発の順番](#5-開発の順番)
    - [■ 基本の順番：データに近い層から](#-基本の順番データに近い層から)
    - [■ 例：改修案件3（タグ）の順番](#-例改修案件3タグの順番)
    - [■ 例：改修案件4（無限スクロール）の順番](#-例改修案件4無限スクロールの順番)
  - [6. よく使うコマンド](#6-よく使うコマンド)


## 1. 全体の地図
- リクエストは、**上から下へ**流れて処理される。レスポンスは、逆の順番で戻っていく。

```
ブラウザ / Postman
   │  GET /chocolatier_api/snap/?tag=旅行
   ▼
┌─────────────────────────────────────────────┐
│ settings.py   … アプリ全体の設定（全部の層が参照する）     │
└─────────────────────────────────────────────┘
   ▼
① ミドルウェア      … 全リクエストが通る関所（CORS・CSRF など）
   ▼
② urls.py         … 「この URL はどの View へ？」の振り分け表
   ▼
③ views.py        … 窓口。認証・権限を確認し、処理の流れを決める
   │                 （例：自分の Snap を、?tag で絞って取ってくる）
   ├──▶ authentication.py … 「誰か？」を判定する
   ▼
④ serializers.py  … 翻訳係。JSON ⇔ Python のデータの変換と入力チェック
   ▼
⑤ models.py       … データの設計図。どんな表・列・関係があるか
   ▼
⑥ マイグレーション    … 設計図（models.py）を実際の DB に反映する手順書
   ▼
   DB（db.sqlite3）

⑦ admin.py        … 管理画面（/admin/）の設定（この流れとは別の入口）
```


## 2. フォルダ構成と役割

### ■ プロジェクト（chocolatier_core）とアプリ（chocolatier_api）
- Django では、**プロジェクト**の中に、機能のまとまりである**アプリ**を入れる。
  - **プロジェクト**：サイト全体の設定と、URL の入口を持つ。1つだけ。
  - **アプリ**：機能ごとのまとまり（モデル・View・シリアライザーなど）。複数持てる。
- Chocolatier は、プロジェクトが `chocolatier_core`、アプリが `chocolatier_api` の1つだけ、という構成。

```
backend/
├── manage.py                 … 操作の入口（runserver / migrate など）
├── db.sqlite3                … DB 本体（SQLite）
├── media/uploads/            … アップロードされた画像
├── requirements.txt          … 必要なパッケージの一覧
│
├── chocolatier_core/         … 【プロジェクト】サイト全体
│   ├── settings.py           … 全体の設定
│   ├── urls.py               … URL の入口（ここからアプリの urls.py へ振り分ける）
│   ├── wsgi.py / asgi.py     … 本番サーバーとつなぐ入口（普段は触らない）
│   └── __init__.py
│
└── chocolatier_api/          … 【アプリ】Snap・ユーザー・タグの機能
    ├── models.py             … データの設計図
    ├── migrations/           … DB への反映手順（makemigrations で自動生成）
    │   ├── 0001_initial.py
    │   └── 0002_tag_snap_tags.py
    ├── serializers.py        … JSON ⇔ Python の変換と入力チェック
    ├── views.py              … API の窓口
    ├── urls.py               … アプリ内の URL
    ├── pagination.py         … 一覧を何件ずつ返すか（自作。改修案件4）
    ├── authentication.py     … Cookie の JWT で「誰か」を判定する（自作）
    ├── admin.py              … 管理画面の設定
    ├── apps.py               … アプリの設定（普段は触らない）
    └── tests.py              … 自動テスト
```

### ■ ファイルごとの役割

| ファイル | ひとことで | 変えるのはどんなとき |
|---|---|---|
| `manage.py` | 操作の入口 | ほぼ変えない |
| `settings.py` | 全体の設定 | ライブラリの追加、認証方式の変更、上限値の追加 |
| `chocolatier_core/urls.py` | URL の入口 | アプリ全体に関わる URL（ログインなど）を追加するとき |
| `chocolatier_api/urls.py` | アプリ内の URL | API を追加するとき |
| `views.py` | 窓口 | API の処理の流れ・権限を変えるとき |
| `pagination.py` | 区切り方 | 一覧の件数や並び順、ページングの方式を変えるとき |
| `authentication.py` | 誰かを判定 | 認証方式を変えるとき |
| `serializers.py` | 翻訳係 | レスポンスの形、受け取る項目、入力チェックを変えるとき |
| `models.py` | 設計図 | 表・列・関係を追加・変更するとき（→ マイグレーションが必要） |
| `migrations/` | DB への反映手順 | 自分では書かない（`makemigrations` で作る） |
| `admin.py` | 管理画面 | 管理画面に表示するモデルや項目を変えるとき |


## 3. 各層の役割

### ■ manage.py：操作の入口
- `runserver`・`makemigrations`・`migrate`・`createsuperuser` などは、すべて `manage.py` 経由で動く。
- 最初に「どの settings.py を使うか」（`chocolatier_core.settings`）を Django に教える。
  - そのため、**`backend` フォルダで、venv を有効にしてから**実行する。
  - 別の場所から実行すると `No module named 'chocolatier_core'` になる。

### ■ settings.py：全体の設定
- すべての層が参照する設定。
- Chocolatier で主に使っている設定
  - `INSTALLED_APPS`：使うアプリ・ライブラリ（`rest_framework`・`corsheaders`・`chocolatier_api` など）
  - `MIDDLEWARE`：ミドルウェアの順番
  - `REST_FRAMEWORK`：DRF 全体の認証・権限のデフォルト
  - `AUTH_USER_MODEL`：カスタムユーザーモデル（`chocolatier_api.User`）
  - `MAX_UPLOAD_SIZE` など：自作の定数（上限値）

### ■ ミドルウェア：全リクエストが通る関所
- `settings.py` の `MIDDLEWARE` に、**上から順に**並べる。リクエストは上から、レスポンスは下から通る。
- 例
  - `CorsMiddleware`：別オリジン（localhost:3000）からのアクセスを許可するヘッダーを付ける
  - `CsrfViewMiddleware`：CSRF 対策
- 並び順に意味がある。`CorsMiddleware` は `CommonMiddleware` より前に置く（→ [07_cookieAuth.md](07_cookieAuth.md)）。

### ■ urls.py：振り分け表
- URL と View を結びつける。上から順に照合し、最初に一致した View に処理を渡す。
- プロジェクトの `urls.py` から、`include` でアプリの `urls.py` を取り込む。

```python
# chocolatier_core/urls.py（プロジェクト）
path('chocolatier_api/', include('chocolatier_api.urls')),

# chocolatier_api/urls.py（アプリ）
path('snap/', SnapList.as_view()),   # → 実際の URL は /chocolatier_api/snap/
path('snap/<int:pk>/', SnapDetail.as_view()),  # <int:pk> の数字が View に渡る
```

### ■ views.py：窓口
- リクエストを受け取り、**処理の流れ**を決める。
  - 誰が使ってよいか（`permission_classes`）
  - どのデータを扱うか（`get_queryset`）
  - どのシリアライザーを使うか（`serializer_class`）
- DRF の `generics` を継承すると、よくある処理（一覧・作成・詳細・更新・削除）をほとんど書かずに作れる。

| View の親クラス | できること | Chocolatier での例 |
|---|---|---|
| `APIView` | 自分で `get` / `post` を書く | `UserSignup`・`CookieLoginView` |
| `ListAPIView` | 一覧（GET） | `SnapList` |
| `CreateAPIView` | 作成（POST） | `SnapCreate` |
| `RetrieveUpdateDestroyAPIView` | 詳細・更新・削除 | `SnapDetail` |

- View に書くのは「流れ」だけにして、データの変換や入力チェックはシリアライザーに任せる。

### ■ authentication.py：誰かを判定する
- `settings.py` の `DEFAULT_AUTHENTICATION_CLASSES` に登録すると、View の処理の前に自動で呼ばれる。
- ここで判定したユーザーが `request.user` になる。
- Chocolatier では、Cookie の JWT を読む `CookieJWTAuthentication` を自作している（→ [07_cookieAuth.md](07_cookieAuth.md)）。
- **認証**（誰か？）と**権限**（使ってよいか？）は別もの。
  - 認証：`authentication_classes`。分からなければ 401
  - 権限：`permission_classes`。許可していなければ 403

### ■ serializers.py：翻訳係
- 2つの方向の変換をする。
  - **受け取るとき**：JSON（文字列）→ Python のデータ。あわせて入力チェックも行う（→ [08_validation.md](08_validation.md)）
  - **返すとき**：モデル（Python のオブジェクト）→ JSON
- `ModelSerializer` を使うと、モデルの定義から項目を自動で作ってくれる。
- 「レスポンスにどの項目を出すか」「どの項目を受け取るか」は、ここの `fields` で決める。

### ■ models.py：データの設計図
- 1つのクラスが DB の1つの表、1つの属性が1つの列になる。
- モデルどうしの関係も、ここで定義する。

| 関係 | 書き方 | Chocolatier での例 |
|---|---|---|
| 多対1 | `ForeignKey` | Snap → User（1人のユーザーが複数の Snap を持つ） |
| 多対多 | `ManyToManyField` | Snap ⇔ Tag（中間テーブル `snap_tags` が自動で作られる） |
| 1対1 | `OneToOneField` | （今は未使用） |

- models.py を変えただけでは、DB は変わらない。次のマイグレーションが必要。

### ■ マイグレーション：設計図を DB に反映する
- 2つのステップで行う。

| コマンド | すること | DB は変わる？ |
|---|---|---|
| `makemigrations` | models.py の変更点を「手順書」（`0002_...py`）にする | 変わらない |
| `migrate` | まだ適用していない手順書を、順番に DB に反映する | 変わる |

- 手順書は `dependencies` で順番がつながっている（0002 は 0001 の後）。
- 手順書は git にコミットする。他の環境でも `migrate` するだけで、同じ DB の構造にできる。
- 自分で書くことはほぼない。`makemigrations` が作ったものを確認するだけ。

### ■ admin.py：管理画面
- `/admin/` の管理画面に、どのモデルをどう表示するかを設定する。
- API とは別の入口。API を作る前に、データを入れて動作を確かめる道具としても使える。
- ログインには、`createsuperuser` で作った管理者を使う（Django のセッション認証。API の Cookie JWT とは別）。


## 4. リクエストの流れ（実例）

### ■ 例1：一覧を取得する（GET）
`GET /chocolatier_api/snap/`

| 順番 | 層 | 起きること |
|---|---|---|
| 1 | ミドルウェア | CORS の確認。Cookie を読み込む |
| 2 | `chocolatier_core/urls.py` | `chocolatier_api/` に一致 → アプリの urls.py へ |
| 3 | `chocolatier_api/urls.py` | `snap/` に一致 → `SnapList` へ |
| 4 | `authentication.py` | `access_token` Cookie を検証 → `request.user` = alice |
| 5 | `views.py`（権限） | `IsAuthenticated` → ログイン中なので OK |
| 6 | `views.py`（`get_queryset`） | `Snap.objects.filter(user=alice)`。`?tag=` があればタグで絞る |
| 7 | `pagination.py` | 新しい順に並べて、12 件だけに区切る（続きの URL `next` も作る） |
| 8 | `models.py` → DB | SQL が発行されて、alice の Snap を取得する（file・tags はまとめて取る） |
| 9 | `serializers.py` | Snap のオブジェクト → JSON（`id`・`filePath`・`comment`・`tags` など）。`{next, previous, results}` に包む |
| 10 | ミドルウェア → ブラウザ | CORS ヘッダーを付けて、200 で返す |

### ■ 例2：画像を投稿する（POST）
`POST /chocolatier_api/snap/create/`（multipart：upload, comment）

| 順番 | 層 | 起きること |
|---|---|---|
| 1〜3 | ミドルウェア・urls.py | `SnapCreate` へ |
| 4 | `authentication.py` | Cookie を検証し、**CSRF もチェック**（POST なので） |
| 5 | `views.py` | `SnapCreateSerializer` にデータを渡す |
| 6 | `serializers.py`（チェック） | 画像か？拡張子は？5MB 以下？コメントは 1000 文字以内？ → NG なら 400 |
| 7 | `views.py`（`perform_create`） | `serializer.save(user=request.user)`：投稿者をログインユーザーにする |
| 8 | `serializers.py`（`create`） | 画像を `media/uploads/` に保存して、File と Snap を作る |
| 9 | `models.py` → DB | INSERT の SQL が発行される |
| 10 | `serializers.py` → ブラウザ | 作成した Snap を JSON にして、201 で返す |


## 5. 開発の順番

### ■ 基本の順番：データに近い層から
- 新しい機能は、**データに近い層（下）から、利用者に近い層（上）へ**作る。
- 下の層は、上の層から「部品」として使われる。部品がないと、上の層は書けないし試せない。

```
① models.py        設計図を決める（すべての土台）
   ↓
② マイグレーション     DB に反映する
   ↓
③ admin.py         管理画面でデータを入れて、設計図が正しいか確かめる
   ↓
④ serializers.py   JSON でどう見せるか・どう受け取るかを決める
   ↓
⑤ views.py         serializer を使って、処理の流れと権限を組み立てる
   ↓
⑥ urls.py          URL を登録して、外から呼べるようにする
   ↓
⑦ curl / Postman   API の動作を確かめる
   ↓
⑧ フロントエンド      API を使う画面を作る
```

- 各段階で動作を確かめてから次へ進むと、問題が起きたときに原因の層をすぐ絞り込める。

### ■ 例：改修案件3（タグ）の順番
| 順番 | Step | 層 | 理由 |
|---|---|---|---|
| 1 | B1 | `models.py` | タグの表と、Snap との多対多の関係を決める |
| 2 | B2 | マイグレーション | `snap_tags` の中間テーブルと `tag` の表を DB に作る |
| 3 | B5 | `admin.py` | 管理画面で Snap にタグを付けてみて、関係が正しいか確かめる |
| 4 | B3 | `serializers.py` | レスポンスに `tags: ["旅行"]` を出す。作成・更新でタグを受け取る |
| 5 | B4 | `views.py` → `urls.py` | `?tag=` での絞り込みと、`tags/` の API を追加する |
| 6 | F1〜 | フロントエンド | タグ入力と、絞り込みのチップを作る |

- 詳しくは [10_tags.md](10_tags.md)。

### ■ 例：改修案件4（無限スクロール）の順番
- 表や列は変わらないので、models・マイグレーション・admin は飛ばして、View のまわりから作る。

| 順番 | Step | 層 | 理由 |
|---|---|---|---|
| 1 | B1 | `pagination.py`（新規） | 「12 件ずつ・新しい順」のルールを決める |
| 2 | B2 | `views.py` | `SnapList` に B1 のルールを付ける。レスポンスの形が変わる |
| 3 | — | curl / API 画面 | `next` をたどって、重複や抜けがないか確かめる |
| 4 | F1〜 | フロントエンド | `next` を使って続きを読み込む（返ってくる形が決まってから作る） |

- 詳しくは [11_infiniteScroll.md](11_infiniteScroll.md)。


## 6. よく使うコマンド
- すべて `backend` フォルダで、venv を有効にしてから実行する。

```powershell
cd backend
venv\Scripts\activate
```

| コマンド | すること |
|---|---|
| `python manage.py runserver` | 開発サーバーを起動（http://localhost:8000） |
| `python manage.py check` | 設定やコードに問題がないか確認 |
| `python manage.py makemigrations chocolatier_api` | models.py の変更から、マイグレーションファイルを作る |
| `python manage.py sqlmigrate chocolatier_api 0002` | マイグレーションで実行される SQL を見る |
| `python manage.py showmigrations` | どのマイグレーションが適用済みか見る（`[X]` が適用済み） |
| `python manage.py migrate` | マイグレーションを DB に反映 |
| `python manage.py createsuperuser` | 管理者ユーザーを作る |
| `python manage.py shell` | Django の設定を読み込んだ Python を起動（モデルを直接操作して試せる） |
| `python manage.py test` | 自動テストを実行 |
