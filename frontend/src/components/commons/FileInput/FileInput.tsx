import { useRef, useState } from 'react';
import styles from './FileInput.module.css';
import Message from '../Message/Message';
import { IMAGE_ACCEPT, validateImageFile } from '../../../utils/validators';

type FileInputProps = {
  onUploadFile: (file: File) => void;  // チェックを通過したファイルだけが渡される
};

function FileInput({ onUploadFile }: FileInputProps) {
  const dropAreaRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);  // チェックのエラーメッセージ

  // ファイル処理ロジック（ドロップ・選択両方で使用）
  // - 形式・サイズをチェックし、問題があればエラーを表示して親には渡さない
  const handleFileSelect = (file: File) => {
    const message = validateImageFile(file);
    setError(message);
    if (message) return;
    onUploadFile(file);
  };

  // inputからの選択時
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
    // 値を空に戻す：同じファイルを選び直したときにも onChange が呼ばれるようにする
    e.target.value = '';
  };

  // ドロップ時の処理
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // CSS Modules のクラス名は自動で変換される（例：FileInput_dragover__a1b2c）ため、
    // 文字列 'dragover' ではなく styles.dragover で外す（以前は外れずに枠の色が残っていた）
    dropAreaRef.current?.classList.remove(styles.dragover);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  return (
    <div>
      {/* ドロップでは accept が効かないので、ここでのエラー表示が必要 */}
      {error && <Message message={error} mode="error" />}
      <div className={styles.inputFile}>
        <div
          className={styles.dropArea}
          ref={dropAreaRef}
          onDragOver={(e) => {
            e.preventDefault();
            dropAreaRef.current?.classList.add(styles.dragover);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            dropAreaRef.current?.classList.remove(styles.dragover);
          }}
          onDrop={handleDrop}
        >
          <p>
            ここにファイルをドロップしてください
            <br />
            または
          </p>
          <div className={styles.inputFileWrap}>
            <input
              id="uploadFile"
              type="file"
              accept={IMAGE_ACCEPT}  // 選択ダイアログに、許可した拡張子の画像だけを表示する
              className={styles.uploadFile}
              ref={fileInputRef}
              onChange={handleChange}
              style={{ display: 'none' }}
            />
            <label htmlFor="uploadFile" className={styles.btnInputFile}>
              <span>ファイルを選択する</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FileInput;
