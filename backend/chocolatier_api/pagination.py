# =========================================================
# pagination.py
# - 一覧 API を「何件ずつ・どう区切って返すか」を決めるファイル
# - views.py の各 View で pagination_class に指定して使う
# =========================================================
from rest_framework.pagination import CursorPagination


# =========================================================
# SnapCursorPagination
# - Snap 一覧を 12 件ずつ返す（無限スクロール用）
# - レスポンスの形：
#   {
#     "next": 続きを取る URL（最後まで読んだら null）,
#     "previous": 前を取る URL（最初のページなら null）,
#     "results": [Snap, Snap, ...]  ← 最大 12 件
#   }
# =========================================================
class SnapCursorPagination(CursorPagination):
    # ① 1 回に返す件数
    page_size = 12

    # ② 並び順（新しい順）
    #    - cursor 方式は「どこまで読んだか」を、この項目の値で覚える
    #      （例：「created_at が 10:00 より古いものから 12 件」）
    #    - views.py の order_by より、こちらの並び順が優先される
    ordering = '-created_at'
