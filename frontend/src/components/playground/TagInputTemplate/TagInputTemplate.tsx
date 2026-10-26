import { useState } from 'react';
import TagInput from '../../commons/TagInput/TagInput';

function TagInputTemplate() {
  // ① タグの配列は親（ここ）が持つ。TagInput は増減を onChangeTags で知らせるだけ
  const [tags, setTags] = useState<string[]>(['旅行', 'カフェ']);

  return (
    <div>
      <h2>TagInput</h2>
      {/* ② 今の値を確認できるように、配列をそのまま表示する */}
      <p>現在のタグ: {JSON.stringify(tags)}</p>
      <TagInput tags={tags} onChangeTags={setTags} />
    </div>
  );
}

export default TagInputTemplate;
