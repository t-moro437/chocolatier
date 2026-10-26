import { useEffect, useState } from 'react';
import styles from './Message.module.css';

// 文字の大きさ
// - medium：フォントサイズを指定しない（親の大きさをそのまま使う）。省略したときはこれ
// - small / large：Message.module.css の .small / .large で大きさを変える
// - 数値で自由に指定できる形にしないのは、画面ごとに大きさがバラバラにならないようにするため
type MessageSize = 'small' | 'medium' | 'large';

type MessageProps = {
  message: string;
  mode: string;
  duration?: number;
  size?: MessageSize;
};

function Message({ message, mode, duration, size = 'medium' }: MessageProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);

    if(duration){
      const timer = setTimeout(() => {
        setVisible(false);
      }, duration);
      return () => clearTimeout(timer);
    }

  }, [message, duration]);

  return (
    // styles[size]：medium は CSS にクラスがないので undefined になり、何も付かない（今までと同じ見た目）
    <div className={`${styles.message} ${styles[mode]} ${styles[size] ?? ''} ${visible ? '' : styles.fadeOut}`}>
      {message}
    </div>
  );
}

export default Message;