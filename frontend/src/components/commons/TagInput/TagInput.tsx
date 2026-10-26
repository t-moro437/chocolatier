import { KeyboardEvent, useState } from 'react';
import styles from './TagInput.module.css';
import TextInput from '../TextInput/TextInput';
import Message from '../Message/Message';
import { validateTagName } from '../../../utils/validators';

type TagInputProps = {
  tags: string[];                         // 今付いているタグ（値は親が持っている）
  onChangeTags: (tags: string[]) => void; // タグが増減したら、新しい配列を親に渡す
};

function TagInput({ tags, onChangeTags }: TagInputProps) {
  // ① 入力欄の文字（まだタグになっていない、入力中の文字）
  const [text, setText] = useState('');
  // ①-2 チェックのエラーメッセージ（問題なければ null）
  const [error, setError] = useState<string | null>(null);

  // ② Enter でタグを追加する
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // ②-1 Enter 以外のキーは何もしない
    if (e.key !== 'Enter') return;

    // ②-2 日本語変換中の Enter（変換の確定）は無視する
    //      - これがないと「りょこう」→ Enter で「旅行」に変換した瞬間にタグが追加されてしまう
    //      - isComposing は React のイベントにはないので、元のイベント（nativeEvent）を見る
    if (e.nativeEvent.isComposing) return;

    // ②-3 ブラウザの標準動作を止める
    //      - TagInput が <form> の中にあると、Enter でフォームが送信されてしまうため
    e.preventDefault();

    // ②-4 前後の空白を取る（" 旅行 " → "旅行"）
    const name = text.trim();

    // ②-5 空、またはすでに付いているタグなら、追加せずに入力欄だけ空にする
    if (!name || tags.includes(name)) {
      setText('');
      return;
    }

    // ②-6 個数・文字数のチェック
    //      - NG なら、エラーを出して入力欄の文字は残す（直してもう一度 Enter できるように）
    const message = validateTagName(name, tags);
    setError(message);
    if (message) return;

    // ②-7 新しい配列を作って親に渡し、入力欄を空にする
    //      - tags.push(name) のように元の配列を直接変えると、React が変化に気づかない
    onChangeTags([...tags, name]);
    setText('');
  };

  // ③ × ボタンでタグを削除する
  //    - filter：target 以外のタグだけを残した、新しい配列を作る
  //    - 「10 個まで」のエラーが出ていても、1 つ減れば追加できるので、エラーを消す
  const handleRemove = (target: string) => {
    onChangeTags(tags.filter((tag) => tag !== target));
    setError(null);
  };

  return (
    <div className={styles.tagInput}>
      {/* ④ 付いているタグをチップで並べる（タグがないときは何も出さない） */}
      {tags.length > 0 && (
        <ul className={styles.tagList}>
          {tags.map((tag) => (
            // key：同じタグは重複させないので、タグ名そのものを key にできる
            <li key={tag} className={styles.tag}>
              {tag}
              {/* type="button"：書かないと submit 扱いになり、フォームが送信されてしまう */}
              {/* aria-label：「×」だけでは読み上げで意味が伝わらないので、説明を付ける */}
              <button
                type="button"
                className={styles.removeButton}
                onClick={() => handleRemove(tag)}
                aria-label={`タグ「${tag}」を削除`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* ⑤ 入力欄：TextInput に追加した onKeyDown・placeholder を使う */}
      <TextInput
        value={text}
        onChangeText={setText}
        onKeyDown={handleKeyDown}
        placeholder="タグを入力して Enter"
      />

      {/* ⑥ 個数・文字数のエラー（FileInput と同じ表示） */}
      {error && <Message message={error} mode="error" />}
    </div>
  );
}

export default TagInput;
