import { useEffect, useRef } from 'react';

// =====================================================
// 無限スクロール用のフック
// - 一覧の一番下に置いた「目印」の要素が画面に入ったら、onReachEnd を呼ぶ
// - 使い方：
//     const sentinelRef = useInfiniteScroll(loadMore, 続きがある && 読み込み中でない);
//     <div ref={sentinelRef} />   ← 一覧の一番下に置く
// - IntersectionObserver：要素が画面に入った・出たを、ブラウザが知らせてくれる仕組み
//   （scroll イベントで毎回位置を計算するより軽い）
// =====================================================
export const useInfiniteScroll = (onReachEnd: () => void, enabled: boolean) => {
  // ① 目印の要素（<div ref={...} /> を付けた要素が入る）
  const sentinelRef = useRef<HTMLDivElement>(null);

  // ② onReachEnd は最新のものを ref に入れておく
  //    - 呼び出す側で関数が作り直されるたびに、③の監視をやり直さなくて済む
  const onReachEndRef = useRef(onReachEnd);
  useEffect(() => {
    onReachEndRef.current = onReachEnd;
  }, [onReachEnd]);

  // ③ 目印の監視
  useEffect(() => {
    const sentinel = sentinelRef.current;
    // ③-1 続きがない・読み込み中なら監視しない
    if (!enabled || !sentinel) return;

    // ③-2 目印が画面に入ったら onReachEnd を呼ぶ
    //      - rootMargin：画面の下 200px 手前で「入った」扱いにして、早めに読み込み始める
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) onReachEndRef.current();
      },
      { rootMargin: '200px' }
    );
    observer.observe(sentinel);

    // ③-3 enabled が変わったとき・画面を離れるときに監視をやめる
    return () => observer.disconnect();
  }, [enabled]);

  return sentinelRef;
};
