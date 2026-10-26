import styles from './SnapshotPanel.module.css';
import { MEDIA_URL } from '../../../api/client';  // 画像の URL は client.ts で一元管理
import { Snap } from '../../../types/Snap';

interface SnapshotPanelProps {
  prmPhoto: Snap;       // 個別スナップ情報（型は types/Snap.ts で共通）
  indexNum: number;     // 配列インデックスなど
  onclickAction?: () => void; // クリック時のハンドラ
}

function SnapshotPanel({ prmPhoto, indexNum, onclickAction }: SnapshotPanelProps) {
  return (
    <div className={styles.snapshotPanel} onClick={onclickAction}>
      <img
        src={`${MEDIA_URL}${prmPhoto.filePath}`}
        className={styles.snapshotPanelImg}
        alt={`snap-${indexNum}`}
      />
    </div>
  );
}

export default SnapshotPanel;