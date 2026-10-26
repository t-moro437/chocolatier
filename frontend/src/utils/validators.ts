// =====================================================
// 入力チェック（フロント側）
// - Backend の settings.py と同じ上限値を使う。変えるときは両方そろえる
//   （MAX_UPLOAD_SIZE / ALLOWED_IMAGE_EXTENSIONS / MAX_COMMENT_LENGTH /
//     MAX_TAGS_PER_SNAP / MAX_TAG_LENGTH）
// - フロントのチェックは「送る前に早く気づかせる」ためのもの
//   本当の守りは Backend のチェック（フロントのチェックは開発者ツール等で回避できるため）
// - 各関数は、問題があればエラーメッセージ、問題なければ null を返す
// =====================================================

// アップロード画像の最大サイズ（バイト）：5MB
export const MAX_UPLOAD_SIZE = 5 * 1024 * 1024;

// アップロードを許可する拡張子（小文字）
export const ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp'];

// <input type="file" accept="..."> に渡す形式（".jpg,.jpeg,.png,..."）
// - ファイル選択ダイアログで、許可した拡張子だけが表示されるようになる
export const IMAGE_ACCEPT = ALLOWED_IMAGE_EXTENSIONS.map((ext) => `.${ext}`).join(',');

// コメントの最大文字数
export const MAX_COMMENT_LENGTH = 1000;

// 1 つの Snap に付けられるタグの最大数
export const MAX_TAGS_PER_SNAP = 10;

// タグ 1 つの最大文字数
export const MAX_TAG_LENGTH = 30;

// =====================================================
// 画像ファイルのチェック
// - 拡張子とサイズを確認する
// - 「中身が本当に画像か」は Backend（Pillow）が確認する
// =====================================================
export const validateImageFile = (file: File): string | null => {
  // 拡張子：ファイル名の最後の「.」より後ろを小文字で取り出す（"photo.JPG" → "jpg"）
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (!ALLOWED_IMAGE_EXTENSIONS.includes(ext)) {
    return `アップロードできるのは ${ALLOWED_IMAGE_EXTENSIONS.join(' / ')} の画像だけです`;
  }

  // サイズ：file.size はバイト単位
  if (file.size > MAX_UPLOAD_SIZE) {
    const maxMb = MAX_UPLOAD_SIZE / (1024 * 1024);
    return `画像サイズは ${maxMb}MB 以下にしてください`;
  }

  return null;
};

// =====================================================
// コメントのチェック
// =====================================================
export const validateComment = (comment: string): string | null => {
  if (comment.length > MAX_COMMENT_LENGTH) {
    return `コメントは ${MAX_COMMENT_LENGTH} 文字以内で入力してください（現在 ${comment.length} 文字）`;
  }
  return null;
};

// =====================================================
// タグのチェック（TagInput で 1 つ追加するときに使う）
// - name は前後の空白を取ったあとのタグ名
// - tags は今付いているタグ（まだ name は入っていない）
// - 空のタグ・重複は TagInput 側で黙って捨てるので、ここでは見ない
// =====================================================
export const validateTagName = (name: string, tags: string[]): string | null => {
  // ① 個数：すでに上限まで付いていたら、これ以上は追加できない
  //    - 先に見るのは、上限なら文字数を直しても追加できないため
  if (tags.length >= MAX_TAGS_PER_SNAP) {
    return `タグは ${MAX_TAGS_PER_SNAP} 個までです`;
  }

  // ② 文字数：Backend と同じく、空白を取ったあとの長さで数える
  if (name.length > MAX_TAG_LENGTH) {
    return `タグは ${MAX_TAG_LENGTH} 文字以内で入力してください（現在 ${name.length} 文字）`;
  }

  // ③ どのチェックにも引っかからなければ、問題なし
  return null;
};