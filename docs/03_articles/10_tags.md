# タグ（多対多）

- 改修案件3で、Snap に自由なタグ（例：「旅行」「カフェ」）を付けて、一覧を絞り込めるようにした。
- Django の多対多（`ManyToManyField`）、シリアライザーでの配列の受け渡し、N+1 問題の対策、React のタグ入力をまとめる。
- 改修の記録（計画からの変更点・確認結果）は [05_改修案件/03_タグ.md](../05_改修案件/03_タグ.md)。

- [タグ（多対多）](#タグ多対多)
  - [0. 考え方](#0-考え方)
    - [■ 多対多と中間テーブル](#-多対多と中間テーブル)
    - [■ タグの表は全ユーザーで共通](#-タグの表は全ユーザーで共通)
    - [■ 作る順番](#-作る順番)
  - [1. プロジェクトディレクトリ](#1-プロジェクトディレクトリ)
    - [■ 設定（settings.py）:上限値](#-設定settingspy上限値)
  - [2. アプリディレクトリ](#2-アプリディレクトリ)
    - [■ モデル(models.py)とマイグレーション](#-モデルmodelspyとマイグレーション)
    - [■ 管理画面(admin.py)](#-管理画面adminpy)
    - [■ シリアライザー(serializers.py):返すとき](#-シリアライザーserializerspy返すとき)
    - [■ シリアライザー(serializers.py):受け取るとき](#-シリアライザーserializerspy受け取るとき)
    - [■ ビュー(views.py):絞り込みと N+1 対策](#-ビューviewspy絞り込みと-n1-対策)
    - [■ ビュー(views.py):絞り込みの候補](#-ビューviewspy絞り込みの候補)
  - [3. フロントエンド](#3-フロントエンド)
    - [■ タグ入力(TagInput.tsx)](#-タグ入力taginputtsx)
    - [■ チェック関数とエラー表示](#-チェック関数とエラー表示)
    - [■ 画面(SnapshotPage.tsx)](#-画面snapshotpagetsx)
  - [4. テスト手順(PowerShellでCurlコマンドを実行)](#4-テスト手順powershellでcurlコマンドを実行)
  - [5. つまずきやすいところ](#5-つまずきやすいところ)


## 0. 考え方

### ■ 多対多と中間テーブル
- 1 つの Snap に複数のタグが付き、1 つのタグも複数の Snap に付く。これが**多対多**。
- 多対多は、2 つの表だけでは表せない。「どの Snap にどのタグが付いているか」を持つ**中間テーブル**を使う。

```
snap                       snap_tags（中間テーブル）       tag
┌────┬─────────┐          ┌─────────┬────────┐          ┌────┬────────┐
│ id │ comment │          │ snap_id │ tag_id │          │ id │ name   │
├────┼─────────┤          ├─────────┼────────┤          ├────┼────────┤
│ 1  │ 京都    │ ───────▶ │ 1       │ 1      │ ◀─────── │ 1  │ 旅行   │
│ 2  │ 喫茶店  │ ───┐     │ 1       │ 2      │ ◀──┐     │ 2  │ カフェ │
└────┴─────────┘    └───▶ │ 2       │ 2      │ ───┘     └────┴────────┘
                          └─────────┴────────┘
→ Snap 1 には「旅行」「カフェ」、Snap 2 には「カフェ」が付いている
```

- Django では `ManyToManyField` を書くだけで、中間テーブルを自動で作ってくれる。`snap` の表には列は増えない。

### ■ タグの表は全ユーザーで共通
- alice の「旅行」と bob の「旅行」は、`tag` の表の同じ 1 行を使う（`name` に一意制約がある）。
- それでも、他のユーザーのタグは見えない。絞り込みの候補は「自分の Snap に付いているタグ」だけを返すため。
- ユーザーごとに表を分ける方法もあるが、「同じ名前のタグを何行も持つ」ことになり、一意制約も複雑になるので選ばなかった。

### ■ 作る順番
- データに近い層から作る（→ [09_djangoStructure.md の「開発の順番」](09_djangoStructure.md#5-開発の順番)）。

| 順番 | 層 | すること |
|---|---|---|
| 1 | `models.py` | `Tag` と、Snap との多対多を決める |
| 2 | マイグレーション | `tag` と `snap_tags` を DB に作る |
| 3 | `admin.py` | 管理画面でタグを付けてみて、関係が正しいか確かめる |
| 4 | `serializers.py` | レスポンスに `tags` を出す。作成・更新でタグを受け取る |
| 5 | `views.py` → `urls.py` | `?tag=` の絞り込みと、`tags/` の API |
| 6 | フロントエンド | タグ入力と、絞り込みのチップ |


## 1. プロジェクトディレクトリ

### ■ 設定（settings.py）:上限値
- 上限値は `serializers.py` に直書きせず、`settings.py` にまとめる（→ [08_validation.md](08_validation.md)）。

```python
# 1 つの Snap に付けられるタグの最大数
# - 空のタグと重複を除いた「後」の個数で数える
MAX_TAGS_PER_SNAP = 10

# タグ 1 つの最大文字数（models.py の Tag.name の max_length と同じ値）
MAX_TAG_LENGTH = 30
```


## 2. アプリディレクトリ

### ■ モデル(models.py)とマイグレーション

```python
class Snap(models.Model):
    # ...（user・file・comment は変更なし）
    tags = models.ManyToManyField(
        'Tag',                 # Tag はこのファイルの下で定義しているので、文字列で指定する
        related_name='snaps',  # タグ側から tag.snaps.all() で「このタグが付いた Snap」を取れる
        blank=True,            # タグなしでも保存できる
    )


class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=30, unique=True)  # 同じ名前のタグは 1 つだけ
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']  # 並び順を指定しないときは名前順
```

- `ManyToManyField` に `null=True` は意味がない（値は中間テーブルに入るため）。「なくてもよい」は `blank=True` で表す。

```powershell
python manage.py makemigrations chocolatier_api   # → 0002_tag_snap_tags.py ができる
python manage.py sqlmigrate chocolatier_api 0002  # 実行される SQL を確認（任意）
python manage.py migrate
```

### ■ 管理画面(admin.py)
- API を作る前に、管理画面でタグを付けてみて、関係が正しいか確かめる。

```python
from django.db.models import Count


@admin.register(Snap)
class SnapAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'file', 'comment', 'tag_list', 'created_at', 'updated_at')
    list_filter = ('user', 'file', 'tags')
    filter_horizontal = ('tags',)  # 多対多の入力欄を「左右 2 つのリスト＋矢印」にする

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tags')  # N+1 対策（後述）

    @admin.display(description='タグ')
    def tag_list(self, obj):
        return ', '.join(tag.name for tag in obj.tags.all())


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'snap_count', 'created_at')
    search_fields = ('name',)

    def get_queryset(self, request):
        # タグごとに「付いている Snap の数」を SQL で数える（'snaps' は related_name）
        return super().get_queryset(request).annotate(snap_count=Count('snaps'))

    @admin.display(description='Snap数', ordering='snap_count')
    def snap_count(self, obj):
        return obj.snap_count
```

### ■ シリアライザー(serializers.py):返すとき
- タグはオブジェクト（`{"id": 1, "name": "旅行"}`）ではなく、**名前の配列**で返す。フロントが扱いやすいため。
- `SlugRelatedField` は、関連先のオブジェクトを、その 1 つの項目（`slug_field`）で表す。

```python
class SnapSerializer(serializers.ModelSerializer):
    filePath = serializers.CharField(source='file.path', read_only=True)
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = Snap
        fields = ['id', 'file', 'filePath', 'comment', 'tags', 'created_at', 'updated_at']
```

```json
{"id": 1, "file": 1, "filePath": "uploads/kyoto.png", "comment": "京都", "tags": ["カフェ", "旅行"], ...}
```

### ■ シリアライザー(serializers.py):受け取るとき
- 受け取るのも名前の配列。作成と更新の両方で使う処理は、関数にまとめる。

```python
# 受け取ったタグ名の配列を整えて、チェックする
# 例：[" 旅行", "カフェ", "", "旅行"] → ["旅行", "カフェ"]
def clean_tag_names(names):
    cleaned = []
    for name in names:
        name = name.strip()          # 前後の空白を取る
        if not name:                 # 空のタグは捨てる
            continue
        if len(name) > settings.MAX_TAG_LENGTH:
            raise serializers.ValidationError(
                f'タグ「{name}」が長すぎます。{settings.MAX_TAG_LENGTH}文字以内にしてください'
            )
        if name not in cleaned:      # 重複を除く
            cleaned.append(name)
    if len(cleaned) > settings.MAX_TAGS_PER_SNAP:
        raise serializers.ValidationError(f'タグは{settings.MAX_TAGS_PER_SNAP}個までにしてください')
    return cleaned


# Snap に付いているタグを、names の内容に入れ替える
def set_snap_tags(snap, names):
    tags = [Tag.objects.get_or_create(name=name)[0] for name in names]  # あれば取得、なければ作成
    snap.tags.set(tags)  # 足りないものは追加し、余分なものは削除する
```

- 作成用のシリアライザー。`tags` は Snap の「列」ではないので、`create` で先に取り出してから、Snap を保存したあとに付ける。

```python
class SnapCreateSerializer(serializers.ModelSerializer):
    # ...（upload・filePath は変更なし）
    tags = serializers.ListField(
        child=serializers.CharField(allow_blank=True),  # 空文字もいったん受け取り、clean_tag_names で捨てる
        required=False,
        write_only=True,
    )

    class Meta:
        model = Snap
        fields = ['id', 'comment', 'upload', 'filePath', 'tags']

    def validate_tags(self, value):
        return clean_tag_names(value)

    def create(self, validated_data):
        upload = validated_data.pop('upload')
        tag_names = validated_data.pop('tags', [])  # 取り出さずに Snap.objects.create に渡すと TypeError
        # ...（File の保存は変更なし）
        snap = Snap.objects.create(file=file_obj, **validated_data)
        set_snap_tags(snap, tag_names)  # Snap に id ができてから付ける（中間テーブルに snap_id が必要）
        return snap

    def to_representation(self, instance):
        return SnapSerializer(instance, context=self.context).data  # 一覧と同じ形で返す
```

- 更新用のシリアライザーも同じ形。ただし、**`tags` を送らなかった**ときと、**空の配列を送った**ときを区別する。

```python
    def update(self, instance, validated_data):
        tag_names = validated_data.pop('tags', None)  # None：送られていない / []：全部外したい
        instance = super().update(instance, validated_data)
        if tag_names is not None:
            set_snap_tags(instance, tag_names)
        return instance
```

| 送ったもの | 結果 |
|---|---|
| `{"comment": "..."}`（tags なし） | タグはそのまま |
| `{"tags": []}` | タグをすべて外す |
| `{"tags": ["カフェ"]}` | 「カフェ」だけになる |

> 💡 **multipart で配列を送るには**：作成は画像を送るので multipart。multipart には「配列」の書き方がないので、**同じキーを繰り返す**（`tags=旅行` と `tags=カフェ`）。DRF の `ListField` は、同じキーの値をまとめて配列として受け取ってくれる。更新は JSON なので、普通に配列で送る。

### ■ ビュー(views.py):絞り込みと N+1 対策
- `?tag=旅行` が付いていたら、そのタグが付いた Snap だけに絞る。`tags__name` は「Snap → tags → name」とたどる書き方。

```python
class SnapList(generics.ListAPIView):
    serializer_class = SnapSerializer

    def get_queryset(self):
        queryset = (
            Snap.objects
            .filter(user=self.request.user)
            .select_related('file')    # 多対1：JOIN で一緒に取る
            .prefetch_related('tags')  # 多対多：別の SQL 1 回でまとめて取る
            .order_by('-created_at')
        )
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__name=tag)
        return queryset
```

- **N+1 問題**：シリアライザーは、Snap 1 件ごとに `snap.file.path` と `snap.tags.all()` を読む。何もしないと、そのたびに SQL が発行される。

| | 12 件の一覧で発行される SQL |
|---|---|
| 対策なし | Snap の一覧 1 回 ＋ file 12 回 ＋ tags 12 回 ＝ **25 回** |
| 対策あり | Snap と file を JOIN で 1 回 ＋ tags をまとめて 1 回 ＝ **件数によらず同じ回数**（ログインユーザーの取得なども含めて 3 回ほど） |

| メソッド | 使う関係 | 仕組み |
|---|---|---|
| `select_related` | 多対1・1対1（ForeignKey） | JOIN で、同じ SQL の中で一緒に取る |
| `prefetch_related` | 多対多・逆参照 | 別の SQL を 1 回だけ発行して、Python 側で組み合わせる |

### ■ ビュー(views.py):絞り込みの候補
- 自分の Snap に付いているタグだけを、重複なしで返す。

```python
class TagList(APIView):
    def get(self, request):
        names = (
            Tag.objects
            .filter(snaps__user=request.user)   # 'snaps' は related_name。タグ → Snap → user とたどる
            .distinct()                         # 複数の Snap に付いていても 1 つにする
            .values_list('name', flat=True)     # 名前だけの配列にする
        )
        return Response(list(names))
```

```python
# urls.py
path('tags/', TagList.as_view(), name='tag-list'),
```


## 3. フロントエンド

### ■ タグ入力(TagInput.tsx)
- Enter で追加、× で削除する。タグの配列は親（SnapshotPage）が持ち、TagInput は増減を `onChangeTags` で伝えるだけ。
- 既存の `TextInput` を使うため、`TextInput` に `onKeyDown` と `placeholder` を追加した。

```tsx
const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
  if (e.key !== 'Enter') return;
  if (e.nativeEvent.isComposing) return;  // 日本語変換中の Enter（変換の確定）は無視する
  e.preventDefault();                     // <form> の中で、フォームが送信されないように

  const name = text.trim();
  if (!name || tags.includes(name)) {     // 空・重複は、追加せずに入力欄だけ空にする
    setText('');
    return;
  }

  const message = validateTagName(name, tags);  // 個数・文字数
  setError(message);
  if (message) return;                    // NG なら入力欄の文字は残す（直して Enter できるように）

  onChangeTags([...tags, name]);          // 新しい配列を作って渡す（push だと React が変化に気づかない）
  setText('');
};
```

- × ボタンは `type="button"` にする。書かないと submit 扱いになり、フォームが送信されてしまう。
- playground（`TagInputTemplate`）で、画面に組み込む前に動きを試せる。

### ■ チェック関数とエラー表示
- `validators.ts`：上限値を Backend とそろえ、`validateTagName` を追加した。
  - 個数を先に見る（上限なら、文字数を直しても追加できないため）。

```ts
export const MAX_TAGS_PER_SNAP = 10;
export const MAX_TAG_LENGTH = 30;

export const validateTagName = (name: string, tags: string[]): string | null => {
  if (tags.length >= MAX_TAGS_PER_SNAP) {
    return `タグは ${MAX_TAGS_PER_SNAP} 個までです`;
  }
  if (name.length > MAX_TAG_LENGTH) {
    return `タグは ${MAX_TAG_LENGTH} 文字以内で入力してください（現在 ${name.length} 文字）`;
  }
  return null;
};
```

- `apiError.ts`：`tags` の要素ごとのエラーは `{"tags": {"0": ["..."]}}` のように入れ子で返ってくる。中身を取り出して平らにする関数を追加した。

```ts
const flattenMessages = (value: unknown): string[] => {
  if (Array.isArray(value)) return value.flatMap(flattenMessages);
  if (value && typeof value === 'object') return Object.values(value).flatMap(flattenMessages);
  return [String(value)];
};
```

### ■ 画面(SnapshotPage.tsx)
- **作成**：`tags` を同じキーで繰り返し `FormData` に入れる。

```tsx
tags.forEach((tag) => formData.append('tags', tag));
```

- **更新**：JSON で `{ comment: text, tags }` を送る。レスポンスは一覧と同じ形なので、一覧の 1 件をそのまま置き換える。
- **絞り込み**：一覧の上に「すべて」と `tags/` の結果をチップで並べる。押すと `?tag=〇〇` を付けて一覧を取り直す（axios の `params` に渡すと、日本語も自動でエンコードされる）。
- 作成・更新・削除のあとは、`tags/` を取り直す（タグが増減するため）。選んでいたタグが候補から消えたら、「すべて」に戻す。
- 絞り込み中に、そのタグが付いていない Snap を作った・タグを外したときは、一覧に出さない。


## 4. テスト手順(PowerShellでCurlコマンドを実行)
- 事前に [07_cookieAuth.md](07_cookieAuth.md) のテスト手順 1〜4 で、ログインと `$csrf` の設定を済ませておく。

1. **タグを付けて作成**（同じキー `tags` を繰り返す） → 201、`"tags":["カフェ","旅行"]`
    ```bash
    curl.exe -b cookies.txt -X POST http://localhost:8000/chocolatier_api/snap/create/ `
      -H "X-CSRFToken: $csrf" `
      -F "upload=@C:/kyoto.png" -F "comment=京都" -F "tags=旅行" -F "tags=カフェ"
    ```

2. **タグで絞り込み**（日本語は `--data-urlencode` でエンコードする）
    ```bash
    curl.exe -b cookies.txt -G http://localhost:8000/chocolatier_api/snap/ --data-urlencode "tag=旅行"
    ```

3. **絞り込みの候補** → `["カフェ","旅行"]`
    ```bash
    curl.exe -b cookies.txt http://localhost:8000/chocolatier_api/tags/
    ```

4. **タグを入れ替える**（ID は 1 の作成結果に合わせる） → 200、`"tags":["カフェ"]`
    ```bash
    curl.exe -b cookies.txt -X PATCH http://localhost:8000/chocolatier_api/snap/1/ `
      -H "Content-Type: application/json" `
      -H "X-CSRFToken: $csrf" `
      -d '{\"tags\":[\"カフェ\"]}'
    ```

5. **11 個送る** → 400 `{"tags":["タグは10個までにしてください"]}`

- PowerShell 5.1 で日本語が文字化けするときは、Postman で試すか、タグを英語（`travel` など）にして確かめる。


## 5. つまずきやすいところ

| 症状 | 原因 |
|---|---|
| 作成で `TypeError: Direct assignment to the forward side of a many-to-many set is prohibited` | `tags` を `validated_data` から取り出さずに `Snap.objects.create(**validated_data)` に渡している |
| 作成でタグが付かない | `set_snap_tags` を `Snap.objects.create` より前に呼んでいる（まだ id がない） |
| コメントだけ更新したら、タグが全部消えた | `validated_data.pop('tags', [])` のように既定値を `[]` にしている（`None` にして区別する） |
| multipart でタグが 1 つしか届かない | `tags=旅行,カフェ` のように 1 つの値にまとめている（キーを繰り返す） |
| 一覧の表示が遅い・SQL がたくさん出る | `select_related` / `prefetch_related` を付けていない（N+1 問題） |
| `tags/` に他のユーザーのタグが出る | `filter(snaps__user=request.user)` を書いていない |
| `tags/` に同じタグが何回も出る | `.distinct()` を書いていない |
| 日本語を変換して Enter しただけでタグが追加される | `e.nativeEvent.isComposing` を見ていない |
| エラーが `タグ：[object Object]` と表示される | `apiError.ts` が入れ子のエラーに対応していない |
