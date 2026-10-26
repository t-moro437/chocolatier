import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import '../SnapshotPage/SnapshotPage.css';
import SnapshotPanel from '../../components/snap/SnapshotPanel/SnapshotPanel';
import Container from '../../components/commons/Container/Container';
import BasicButton from '../../components/commons/BasicButton/BasicButton';
import Modal from '../../components/commons/Modal/Modal';
import LongText from '../../components/commons/LongText/LongText';
import FileInput from '../../components/commons/FileInput/FileInput';
import Message from '../../components/commons/Message/Message';
import TagInput from '../../components/commons/TagInput/TagInput';
import client, { MEDIA_URL } from '../../api/client';  // API 呼び出しは共通の client を使う
import { getApiErrorMessages } from '../../utils/apiError';
import { MAX_COMMENT_LENGTH, validateComment } from '../../utils/validators';
import { Snap, SnapPage } from '../../types/Snap';
import { useInfiniteScroll } from '../../hooks/useInfiniteScroll';

// Snapshotページのメインコンポーネント
function SnapshotPage() {
  // =====================================================
  // 状態管理
  // =====================================================
  const [snaps, setSnaps] = useState<Snap[]>([]);      // スナップ一覧
  const [snap, setSnap] = useState<Snap | null>();     // モーダルで選択中のスナップ
  const [showModal, setShowModal] = useState(false);   // モーダル開閉状態
  const [text, setText] = useState('');                // コメント入力
  const [file, setFile] = useState<File | null>(null); // 新規作成用ファイル
  const [errorMessages, setErrorMessages] = useState<string[]>([]); // モーダルに出すエラー
  const [tags, setTags] = useState<string[]>([]);                   // モーダルで編集中のタグ
  const [tagOptions, setTagOptions] = useState<string[]>([]);       // 絞り込みの候補（自分が使っているタグ）
  const [selectedTag, setSelectedTag] = useState<string | null>(null); // 絞り込み中のタグ（null は「すべて」）
  const [nextUrl, setNextUrl] = useState<string | null>(null); // 続きを取る URL（null なら最後まで読んだ）
  const [loading, setLoading] = useState(false);               // 一覧を読み込み中か

  // =====================================================
  // ファイルプレビューURLの生成とクリーンアップ
  // - file が変わるたび新しい previewUrl を生成（useMemo）
  // - 古い URL は useEffect で破棄（メモリリーク防止）
  // - useState と違い、更新関数（setter）は不要
  // =====================================================
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

    useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // =====================================================
  // ファイル選択・モーダル操作
  // =====================================================
  const handleFileUpload = useCallback((selectedFile: File | null) => {
    setFile(selectedFile);
  }, []);

  const openModal = (prmSnap?: Snap) => {
    if (prmSnap) {
      setSnap(prmSnap);
      setText(prmSnap.comment);
      setTags(prmSnap.tags);
    } else {
      setSnap(null);
      setTags([]);
    }
    setErrorMessages([]);  // 前回のエラーを残さない
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setFile(null);
    setText('');
    setTags([]);
    setErrorMessages([]);
  };

  // =====================================================
  // データ取得・初期化（12 件ずつ）
  // - 最初の 12 件：初回とタグを切り替えたときに取り直す
  // - 続き：一覧の一番下が見えたら、nextUrl の続きを取って後ろに足す
  // - 認証は Cookie で自動送信されるので、ヘッダーの指定は不要
  // =====================================================

  // ① 何回目のリクエストかを数える
  //    - 読み込み中にタグを切り替えると、古いタグの結果があとから届くことがある
  //    - 最後に出したリクエストの結果だけを使うために、番号で見分ける
  //    - useRef：値が変わっても再描画しない。画面に出さない値の保存に使う
  const requestIdRef = useRef(0);

  // ② 1 ページ分を取得して、一覧に反映する（③と④で使う共通の処理）
  //    - append=false：一覧を置き換える（最初の 12 件）
  //    - append=true ：一覧の後ろに足す（続き）
  const fetchPage = useCallback(
    async (url: string, params: Record<string, string>, append: boolean) => {
      // ②-1 このリクエストの番号を取る
      const requestId = ++requestIdRef.current;
      setLoading(true);
      try {
        // ②-2 取得する
        //      - params：axios が URL の ?tag=〇〇 を作ってくれる（日本語も自動でエンコードされる）
        const response = await client.get<SnapPage>(url, { params });

        // ②-3 待っている間に、新しいリクエストが出ていたら捨てる
        if (requestId !== requestIdRef.current) return;

        // ②-4 一覧と、続きの URL を反映する
        setSnaps((prev) => (append ? [...prev, ...response.data.results] : response.data.results));
        setNextUrl(response.data.next);
      } catch (error) {
        // ②-5 失敗したら、自動での読み込みを止める
        //      - nextUrl を残すと、目印が見えている間ずっと失敗をくり返してしまうため
        //      - 一覧の取得失敗はモーダルの外なので、ログだけ出す
        console.error('一覧の取得に失敗しました:', error);
        if (requestId === requestIdRef.current) setNextUrl(null);
      } finally {
        // ②-6 最後に出したリクエストのときだけ、読み込み中を解除する
        if (requestId === requestIdRef.current) setLoading(false);
      }
    },
    []
  );

  // ③ 最初の 12 件（初回と、タグを切り替えたとき）
  //    - 前のタグの一覧と続きの URL を消してから取り直す
  //    - 「すべて」のときは params を空にして、絞り込まない
  useEffect(() => {
    setSnaps([]);
    setNextUrl(null);
    fetchPage('/chocolatier_api/snap/', selectedTag ? { tag: selectedTag } : {}, false);
  }, [selectedTag, fetchPage]);

  // ④ 続きの 12 件（一覧の一番下が見えたとき）
  //    - nextUrl には cursor と tag がすでに入っているので、params は空でよい
  const loadMore = useCallback(() => {
    if (!nextUrl || loading) return;
    fetchPage(nextUrl, {}, true);
  }, [nextUrl, loading, fetchPage]);

  // ⑤ 一覧の一番下の目印を監視する（続きがあって、読み込み中でないときだけ）
  const sentinelRef = useInfiniteScroll(loadMore, nextUrl !== null && !loading);

  // 絞り込みの候補（自分の Snap に付いているタグ）を取得する
  // - 初回と、作成・更新・削除のあと（タグが増減するため）に呼ぶ
  const fetchTags = useCallback(async () => {
    try {
      const response = await client.get<string[]>('/chocolatier_api/tags/');
      setTagOptions(response.data);
      // 絞り込み中のタグが、どの Snap からも外れて候補から消えたら「すべて」に戻す
      // （そのままだと、0 件の一覧が表示されたままになるため）
      setSelectedTag((prev) => (prev && !response.data.includes(prev) ? null : prev));
    } catch (error) {
      console.error('タグの取得に失敗しました:', error);
    }
  }, []);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  // 作成・更新したスナップが、今の絞り込みに合うか
  // - 「すべて」のときは常に合う
  const matchesFilter = (target: Snap) => !selectedTag || target.tags.includes(selectedTag);

  // =====================================================
  // CRUD操作
  // =====================================================
  // 新規作成
  const handleCreateSubmit = async () => {
    // 送る前のチェック（画像の形式・サイズは FileInput で選択時にチェック済み）
    const errors = [
      !file ? '画像を選択してください' : null,
      validateComment(text),
    ].filter((message): message is string => message !== null);
    if (errors.length > 0 || !file) return setErrorMessages(errors);

    // FormData を渡すと、axios が Content-Type（multipart/form-data）を自動で付ける
    const formData = new FormData();
    formData.append('comment', text);
    formData.append('upload', file);
    // tags は同じキーで繰り返し入れる（tags=旅行 & tags=カフェ）
    // - Backend の ListField が、同じキーの値をまとめて配列として受け取る
    // - タグがなければ何も入れない（Backend では「タグなし」になる）
    tags.forEach((tag) => formData.append('tags', tag));
    // user は送らない（サーバーがログインユーザーを設定する。なりすまし防止）

    try {
      const response = await client.post('/chocolatier_api/snap/create/', formData);
      // 一覧は新しい順なので先頭に追加（絞り込みに合わないときは追加しない）
      if (matchesFilter(response.data)) {
        setSnaps((prev) => [response.data, ...prev]);
      }
      fetchTags();  // 新しいタグが増えたかもしれないので、候補を取り直す
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // 更新
  const handleUpdateSubmit = async () => {
    if (!snap) return;

    // 送る前のチェック
    const commentError = validateComment(text);
    if (commentError) return setErrorMessages([commentError]);

    try {
      // 画像は変えないので JSON で送る
      // - tags は配列のまま送る。空の配列 [] なら、タグをすべて外す
      const response = await client.patch<Snap>(
        `/chocolatier_api/snap/${snap.id}/`,
        { comment: text, tags }
      );

      // レスポンスは一覧と同じ形（id・filePath・tags なども入っている）なので、そのまま置き換える
      // - 絞り込み中のタグを外したときは、一覧から取り除く
      const updated = response.data;
      setSnaps((prevSnaps) =>
        matchesFilter(updated)
          ? prevSnaps.map((s) => (s.id === updated.id ? updated : s))
          : prevSnaps.filter((s) => s.id !== updated.id)
      );
      fetchTags();  // タグが増減したかもしれないので、候補を取り直す
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // 削除
  const handleDeleteSubmit = async () => {
    if (!snap) return;

    if (!window.confirm('本当に削除しますか？')) return;

    try {
      await client.delete(`/chocolatier_api/snap/${snap.id}/`);
      setSnaps((prevSnaps) => prevSnaps.filter((s) => s.id !== snap.id));
      fetchTags();  // そのタグを使っていた最後の Snap なら、候補から消える
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // =====================================================
  // エラーハンドリング
  // - API のエラー（400 の入力チェックなど）をモーダル内に表示する
  //   例：{"upload": ["画像サイズは5MB以下にしてください"]} → 「画像：画像サイズは5MB以下にしてください」
  // - 401（ログイン切れ）は client.ts が refresh を試し、
  //   それでもダメなら ProtectedRoute がサインイン画面へ移動させる
  // =====================================================
  const handleApiError = (error: unknown) => {
    console.error('APIエラー:', error);
    setErrorMessages(getApiErrorMessages(error));
  };

  // =====================================================
  // クリーンアップ（ファイルURLの解放）
  // - file が変わるたび新しい previewUrl を生成する。
  // =====================================================
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // =====================================================
  // JSXレンダリング
  // =====================================================
  return (
    <Container className="container">
      <div>
        <BasicButton onclickAction={() => openModal()}>新規作成</BasicButton>

        {/* タグの絞り込み：「すべて」＋自分が使っているタグをチップで並べる */}
        <div className="tagFilter">
          <button
            type="button"
            className={`tagFilterChip ${selectedTag === null ? 'tagFilterChipActive' : ''}`}
            onClick={() => setSelectedTag(null)}
          >
            すべて
          </button>
          {tagOptions.map((tag) => (
            <button
              key={tag}
              type="button"
              className={`tagFilterChip ${selectedTag === tag ? 'tagFilterChipActive' : ''}`}
              onClick={() => setSelectedTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>

        <div className="flexArea">
          {snaps.map((snap, index) => (
            <SnapshotPanel
              key={snap.id}
              prmPhoto={snap}
              indexNum={index}
              onclickAction={() => openModal(snap)}
            />
          ))}
        </div>

        {/* 無限スクロールの目印：これが画面に入ったら続きを読み込む */}
        <div ref={sentinelRef} className="scrollSentinel" />
        {loading && <p className="loadingText">読み込み中...</p>}
      </div>

      <Modal show={showModal} setShow={closeModal}>
        <div className="modalFlexArea">
          <div className="modalContents">
            <div className="modalDeleteArea">
              {snap && (
                <div className="modalDeleteButton" onClick={handleDeleteSubmit}>
                  削除
                </div>
              )}
            </div>

            <h2>{snap ? 'スナップ詳細' : 'スナップ作成'}</h2>

            {/* エラーメッセージ（送る前のチェック・API のエラー） */}
            {errorMessages.map((message) => (
              <Message key={message} message={message} mode="error" />
            ))}

            {!snap && <FileInput onUploadFile={handleFileUpload} />}

            {(file || snap) && (
              <img
                className="filePreview"
                src={previewUrl ? previewUrl : `${MEDIA_URL}${snap?.filePath}`}
                alt="preview"
              />
            )}

            <LongText
              placeholder="思い出話など自由に書いてください"
              value={text}
              onChangeText={setText}
              rows={5}
            />
            {/* 文字数カウンター：上限を超えたら赤くする */}
            <div
              className="commentCounter"
              style={text.length > MAX_COMMENT_LENGTH ? { color: '#c62828' } : undefined}
            >
              {text.length} / {MAX_COMMENT_LENGTH}
            </div>

            {/* タグ：Enter で追加・× で削除。値（tags）はこのページが持つ */}
            <div className="modalTagArea">
              <TagInput tags={tags} onChangeTags={setTags} />
            </div>
            <div>
              <BasicButton
                type="submit"
                value="save"
                onclickAction={snap ? handleUpdateSubmit : handleCreateSubmit}
              >
                保存
              </BasicButton>
            </div>
          </div>
        </div>
      </Modal>
    </Container>
  );
}

export default SnapshotPage;
