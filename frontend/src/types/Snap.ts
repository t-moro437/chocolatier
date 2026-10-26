// スナップ 1 件（一覧 API の results の 1 要素・作成／更新 API のレスポンス）
export interface Snap {
  id: number;
  comment: string;
  filePath: string;
  tags: string[];  // 付いているタグ名の配列（例：["カフェ", "旅行"]）
}

// 一覧 API（/chocolatier_api/snap/）のレスポンス
// - Backend の pagination.py で、12 件ずつに区切って返している
export interface SnapPage {
  next: string | null;      // 続きを取る URL（最後まで読んだら null）
  previous: string | null;  // 前を取る URL（無限スクロールでは使わない）
  results: Snap[];          // 最大 12 件
}
