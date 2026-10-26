# 無限スクロール（cursor 方式のページング）

- 改修案件4で、Snap 一覧を 12 件ずつ返すようにし、画面では下までスクロールすると続きを読み込む「無限スクロール」にした。
- Backend は DRF の `CursorPagination`、Frontend は `IntersectionObserver` を使う。
- 改修の記録（計画からの変更点・確認結果）は [05_改修案件/04_無限スクロール.md](../05_改修案件/04_無限スクロール.md)。

- [無限スクロール（cursor 方式のページング）](#無限スクロールcursor-方式のページング)
  - [0. 考え方](#0-考え方)
    - [■ 登場人物は 3 つ](#-登場人物は-3-つ)
    - [■ 全体の流れ](#-全体の流れ)
    - [■ ページ番号方式ではなく cursor 方式にした理由](#-ページ番号方式ではなく-cursor-方式にした理由)
  - [1. アプリディレクトリ（Backend）](#1-アプリディレクトリbackend)
    - [■ ページングのルール(pagination.py)](#-ページングのルールpaginationpy)
    - [■ ビュー(views.py)](#-ビューviewspy)
    - [■ レスポンスの形](#-レスポンスの形)
  - [2. フロントエンド](#2-フロントエンド)
    - [■ 型(src/types/Snap.ts)](#-型srctypessnapts)
    - [■ 目印を見張るフック(src/hooks/useInfiniteScroll.ts)](#-目印を見張るフックsrchooksuseinfinitescrollts)
    - [■ 読み込み中は見張りを外す（enabled）](#-読み込み中は見張りを外すenabled)
    - [■ 画面(SnapshotPage.tsx):最初の 12 件と続き](#-画面snapshotpagetsx最初の-12-件と続き)
    - [■ 古いリクエストの結果を捨てる（requestIdRef）](#-古いリクエストの結果を捨てるrequestidref)
    - [■ 作成・更新・削除は変えなくてよい](#-作成更新削除は変えなくてよい)
    - [■ key を snap.id にする](#-key-を-snapid-にする)
  - [3. テスト手順](#3-テスト手順)
  - [4. つまずきやすいところ](#4-つまずきやすいところ)


## 0. 考え方

### ■ 登場人物は 3 つ
細かいコードの前に、仕組みを 3 つの登場人物で押さえる。

| 登場人物 | 役割 | たとえると |
|---|---|---|
| **目印**（一覧の一番下に置いた、見えない `<div>`） | 「ここが一覧の終わり」を示す | 本の最後のページにはさんだしおり |
| **見張り番**（`IntersectionObserver`） | 目印が画面に入ったら知らせてくれる | しおりが見えたら「最後まで来たよ！」と言ってくれる人 |
| **`next` の URL** | 続きの 12 件を取るための URL。Backend が教えてくれる | 「次の巻はこちら」のメモ |

### ■ 全体の流れ

```
① ページを開く
   → GET /chocolatier_api/snap/  で最初の 12 件を取る
   → レスポンスの next（続きの URL）を覚えておく

        ┌──────────────┐
        │ Snap × 12    │  ← 画面
        │              │
        └──────────────┘
          ・目印         ← まだ画面の外（下）

② ユーザーが下にスクロールする
   → 目印が画面に入る
   → 見張り番が「見えたよ！」と知らせる

③ next の URL で続きの 12 件を取り、一覧の後ろに足す
   → 一覧が伸びて、目印はまた画面の外へ押し出される
   → next は「その次の URL」に更新される

④ ②〜③ をくり返す
   → 最後まで読むと next が null になる → 見張りをやめる
```

### ■ ページ番号方式ではなく cursor 方式にした理由
- ページングには、よく使う方式が 2 つある。

| | ページ番号方式（`PageNumberPagination`） | cursor 方式（`CursorPagination`） |
|---|---|---|
| URL | `?page=2` | `?cursor=cD0yMDI2...`（中身は気にしなくてよい） |
| 続きの意味 | 「**13〜24 件目**」 | 「**この投稿より古いもの**から 12 件」 |
| 途中で投稿が増減すると | ずれて、重複や抜けが起きる | ずれない |
| 「5 ページ目に飛ぶ」 | できる | できない（順番にたどるだけ） |

- ページ番号方式で、スクロール中に新しい投稿が 1 件増えたとき：

```
1 ページ目を読んだ時点：  [A B C D E F G H I J K L] [M N ...]
                          ←───── 1〜12 件目 ─────→
新しい投稿 Z が増える：    [Z A B C D E F G H I J K] [L M N ...]
2 ページ目（13〜24 件目）：                            L M N ...
                                                      ↑ L はもう表示済み → 重複！
```

- cursor 方式なら、2 ページ目は「L より古いもの」なので `M N ...` から始まる。無限スクロールには「○ページ目に飛ぶ」機能はいらないので、cursor 方式が向いている。


## 1. アプリディレクトリ（Backend）

### ■ ページングのルール(pagination.py)
- 新しく `chocolatier_api/pagination.py` を作る。一覧 API を「何件ずつ・どう区切って返すか」を決めるファイル。

```python
from rest_framework.pagination import CursorPagination


class SnapCursorPagination(CursorPagination):
    page_size = 12           # 1 回に返す件数
    ordering = '-created_at' # 並び順（新しい順）。cursor はこの項目の値で「どこまで読んだか」を覚える
```

- `ordering` の項目は、**値が変わらず、ほぼ重ならない**ものにする。`created_at` は作成時に決まって変わらないので向いている（`updated_at` は更新で変わるので向かない）。
- `views.py` の `order_by` より、`ordering` の並び順が優先される。

### ■ ビュー(views.py)
- `pagination_class` を 1 行足すだけ。`get_queryset`（自分の Snap・`?tag=` の絞り込み）は変えない。

```python
from .pagination import SnapCursorPagination


class SnapList(generics.ListAPIView):
    serializer_class = SnapSerializer
    pagination_class = SnapCursorPagination  # 12 件ずつ返す
    # get_queryset は変更なし
```

- `settings.py` の `REST_FRAMEWORK` に `DEFAULT_PAGINATION_CLASS` を書くと全 API に効くが、今回は Snap 一覧だけなので View に書いた。

### ■ レスポンスの形
- 配列から、`next`・`previous`・`results` を持つオブジェクトに変わる。**フロントも合わせて変える必要がある**。

```json
// 変更前
[ {"id": 14, ...}, {"id": 13, ...}, ... ]

// 変更後
{
  "next": "http://localhost:8000/chocolatier_api/snap/?cursor=cD0yMDI2LTEw...&tag=%E6%97%85%E8%A1%8C",
  "previous": null,
  "results": [ {"id": 14, ...}, {"id": 13, ...}, ... ]   ← 最大 12 件
}
```

- `next` は**そのまま呼べる完全な URL**。`?tag=旅行` で絞り込んでいれば、`tag` も入っている。フロントは中身を組み立てなくてよい。
- 最後まで読むと `next` は `null` になる。


## 2. フロントエンド

### ■ 型(src/types/Snap.ts)
- `Snap` の型を、SnapshotPage と SnapshotPanel で別々に持っていたので、1 か所にまとめた。一覧のレスポンスの型も置く。

```ts
export interface Snap {
  id: number;
  comment: string;
  filePath: string;
  tags: string[];
}

export interface SnapPage {
  next: string | null;      // 続きを取る URL（最後まで読んだら null）
  previous: string | null;  // 無限スクロールでは使わない
  results: Snap[];          // 最大 12 件
}
```

### ■ 目印を見張るフック(src/hooks/useInfiniteScroll.ts)
- **フック**は、`useState` や `useEffect` を組み合わせた「動きだけの部品」。見た目を持たず、ロジックを使い回すために作る。名前は `use` で始める決まり。
- `IntersectionObserver` は、要素が画面に入った・出たを、ブラウザが知らせてくれる仕組み。scroll イベントで毎回位置を計算するより軽い。

```ts
export const useInfiniteScroll = (onReachEnd: () => void, enabled: boolean) => {
  // ① 目印の要素（<div ref={sentinelRef} /> を付けた要素が入る）
  const sentinelRef = useRef<HTMLDivElement>(null);

  // ② onReachEnd は最新のものを ref に入れておく（関数が作り直されるたびに、監視をやり直さなくて済む）
  const onReachEndRef = useRef(onReachEnd);
  useEffect(() => {
    onReachEndRef.current = onReachEnd;
  }, [onReachEnd]);

  // ③ 目印の監視
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!enabled || !sentinel) return;  // 続きがない・読み込み中なら監視しない

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) onReachEndRef.current();  // 目印が画面に入った
      },
      { rootMargin: '200px' }  // 画面の下 200px 手前で「入った」扱いにして、早めに読み込む
    );
    observer.observe(sentinel);
    return () => observer.disconnect();  // enabled が変わったとき・画面を離れるときに監視をやめる
  }, [enabled]);

  return sentinelRef;
};
```

- 使う側はこう書く。

```tsx
const sentinelRef = useInfiniteScroll(loadMore, nextUrl !== null && !loading);
// ...
<div ref={sentinelRef} className="scrollSentinel" />  {/* 一覧の一番下 */}
```

### ■ 読み込み中は見張りを外す（enabled）
- 一番分かりにくいところ。`IntersectionObserver` は、目印が「見えていない → 見えた」に**変わった瞬間**だけ知らせてくれる。
- そのため、次の 2 つの問題が起きる。

| 問題 | 何が起きるか |
|---|---|
| 二重の読み込み | 読み込みが終わる前にもう一度知らせが来ると、同じ続きを 2 回取りに行く |
| 画面が埋まらない | 画面が縦に長いと、12 件足しても目印が見えたまま。「変わった瞬間」がないので、もう知らせてくれない |

- そこで、**読み込み中は監視を外し（`enabled = false`）、終わったら付け直す（`enabled = true`）**。監視を付け直した直後は、「今見えているか」を 1 回知らせてくれる。

```
時間 →
enabled      true ──┐            ┌── true ──┐            ┌── true
                    └─ false ────┘          └─ false ────┘
目印         見えた！             まだ見えてる！           見えない（画面の外）
             ↓                   ↓                       ↓
             続きを読み込む       もう一度読み込む          何もしない（スクロール待ち）
             （監視を外す）       （画面が埋まるまで自動でくり返す）
```

- `enabled` は `nextUrl !== null && !loading`。最後まで読んで `nextUrl` が `null` になると、監視は付け直されない。

### ■ 画面(SnapshotPage.tsx):最初の 12 件と続き
- state を 2 つ増やす。

```tsx
const [nextUrl, setNextUrl] = useState<string | null>(null); // 続きを取る URL（null なら最後まで読んだ）
const [loading, setLoading] = useState(false);               // 一覧を読み込み中か
```

- 「最初の 12 件」と「続き」は、取る URL と、一覧を**置き換えるか・後ろに足すか**だけが違う。共通の `fetchPage` にまとめる。

```tsx
const fetchPage = useCallback(
  async (url: string, params: Record<string, string>, append: boolean) => {
    const requestId = ++requestIdRef.current;  // このリクエストの番号（次の節で説明）
    setLoading(true);
    try {
      const response = await client.get<SnapPage>(url, { params });
      if (requestId !== requestIdRef.current) return;  // 古いリクエストなら捨てる
      setSnaps((prev) => (append ? [...prev, ...response.data.results] : response.data.results));
      setNextUrl(response.data.next);
    } catch (error) {
      console.error('一覧の取得に失敗しました:', error);
      if (requestId === requestIdRef.current) setNextUrl(null);  // 失敗したら自動での読み込みを止める
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  },
  []
);

// 最初の 12 件（初回と、タグを切り替えたとき）：前のタグの一覧を消してから取り直す
useEffect(() => {
  setSnaps([]);
  setNextUrl(null);
  fetchPage('/chocolatier_api/snap/', selectedTag ? { tag: selectedTag } : {}, false);
}, [selectedTag, fetchPage]);

// 続きの 12 件（目印が見えたとき）：nextUrl に cursor と tag が入っているので、params は空
const loadMore = useCallback(() => {
  if (!nextUrl || loading) return;
  fetchPage(nextUrl, {}, true);
}, [nextUrl, loading, fetchPage]);
```

- `nextUrl` は `http://localhost:8000/...` の完全な URL。axios は、完全な URL を渡すと `baseURL` を付けずにそのまま使う。Cookie の送信（`withCredentials`）などの設定は、共通の `client` のものがそのまま効く。
- 失敗したときに `nextUrl` を残すと、目印が見えている間、`enabled` の付け外しのたびに失敗をくり返してしまう。そのため `null` にして止める（ページを開き直せば、最初から読み込める）。

### ■ 古いリクエストの結果を捨てる（requestIdRef）
- 読み込み中にタグを切り替えると、**前のタグの結果があとから届く**ことがある。

```
時間 →
「旅行」の続きを取りに行く ──────────────────────▶ 結果が届く（旅行の Snap）
              「カフェ」に切り替え → 最初の 12 件を取りに行く ──▶ 結果が届く
                                                      ↑
                         何もしないと、カフェの一覧に旅行の Snap が混ざる
```

- リクエストを出すたびに番号を 1 つ増やし、結果が届いたときに「**自分が最後に出したリクエストか**」を確かめる。違えば捨てる。

```tsx
const requestIdRef = useRef(0);  // useRef：値が変わっても再描画しない。画面に出さない値の保存に使う

const requestId = ++requestIdRef.current;      // 出すとき：番号を取る（例：5）
// ...（待っている間に、別のリクエストで 6 になる）
if (requestId !== requestIdRef.current) return; // 届いたとき：5 ≠ 6 なので捨てる
```

### ■ 作成・更新・削除は変えなくてよい
- `next` は「**この投稿より古いもの**」という意味なので、手元の一覧をどう変えても、続きの範囲はずれない。

| 操作 | 手元の一覧 | 続き（next）への影響 |
|---|---|---|
| 作成 | 先頭に足す | なし（新しい投稿は、続きの範囲＝古いものには入らない） |
| 更新 | その 1 件を置き換える | なし |
| 削除 | その 1 件を消す | なし |

- ページ番号方式だと、削除しただけで続きが 1 件ずれて、抜けが起きる。

### ■ key を snap.id にする
- `key` は、React が「前の描画のどの要素と同じものか」を見分ける目印。
- 配列の番号（`index`）だと、先頭に 1 件足したときに全部の番号がずれて、React が「全部変わった」と思って作り直す。無限スクロールで件数が増えるほど、無駄が大きくなる。
- `snap.id` なら、増えた 1 件だけを足してくれる。

```tsx
{snaps.map((snap, index) => (
  <SnapshotPanel key={snap.id} prmPhoto={snap} indexNum={index} onclickAction={() => openModal(snap)} />
))}
```


## 3. テスト手順
- 事前に [07_cookieAuth.md](07_cookieAuth.md) のテスト手順で、ログインを済ませておく。
- 投稿が 12 件以下なら、確認する間だけ `pagination.py` の `page_size` を 2 にすると試しやすい（終わったら 12 に戻す）。

1. **最初のページ** → `results` が新しい順で最大 12 件、`next` に `?cursor=` 付きの URL
    ```bash
    curl.exe -b cookies.txt http://localhost:8000/chocolatier_api/snap/
    ```

2. **続き**：1 の `next` の URL をそのまま呼ぶ（`&` を含むので、URL は `"` で囲む）
    ```bash
    curl.exe -b cookies.txt "http://localhost:8000/chocolatier_api/snap/?cursor=..."
    ```

3. **タグで絞り込んだ続き** → `next` の URL に `tag=` が残っている
    ```bash
    curl.exe -b cookies.txt -G http://localhost:8000/chocolatier_api/snap/ --data-urlencode "tag=旅行"
    ```

- **ブラウザで確かめる**
  - フロントでログインしたあと、同じブラウザで `http://localhost:8000/chocolatier_api/snap/` を開くと、DRF の API 画面で `next` を押してたどれる（Cookie はポート番号に関係なく `localhost` で共通）。
  - 画面では、DevTools の Network タブで、スクロールしたときに `?cursor=` 付きのリクエストが出ているかを見る。


## 4. つまずきやすいところ

| 症状 | 原因 |
|---|---|
| Backend を変えたら、画面が `snaps.map is not a function` で真っ白になる | レスポンスが配列から `{next, previous, results}` に変わった。フロントで `response.data.results` を使う |
| 下までスクロールしても続きが読み込まれない | 目印の `<div>` に `ref={sentinelRef}` を付けていない。または目印の高さが 0 |
| 画面が大きいと、最初の 12 件のあと止まってしまう | `enabled` を付け外ししていない（監視しっぱなしだと、「見えたまま」では知らせが来ない） |
| 同じ Snap が 2 回表示される | 読み込み中も監視していて、同じ `next` を 2 回取っている。または `key` に `index` を使っていて表示が崩れている |
| タグを切り替えたら、前のタグの Snap が混ざる | 古いリクエストの結果を捨てていない（`requestIdRef`） |
| タグを切り替えても、前のタグの続きが読み込まれる | タグを切り替えたときに `nextUrl` を `null` に戻していない |
| サーバーを止めると、エラーが延々と出続ける | 失敗したときに `nextUrl` を残している |
| `ordering` を `updated_at` にしたら、重複や抜けが出る | cursor の項目が更新で変わるため。作成時に決まって変わらない項目を使う |
