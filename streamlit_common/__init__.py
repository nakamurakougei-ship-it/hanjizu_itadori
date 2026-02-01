# Streamlit 共通ユーティリティ（イタドリ・判じ図などで共有）
# テーブル・データエディタの白背景問題の共通対策

STREAMLIT_TABLE_WHITE_BG_CSS = """
<style>
/* Streamlit テーブル・データエディタに白背景を強制（標準では背景が透けるため） */

/* st.data_editor / st.dataframe 用（AG Grid 系） */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] .ag-root-wrapper,
[data-testid="stDataFrame"] .ag-body-viewport,
[data-testid="stDataFrame"] .ag-center-cols-viewport,
[data-testid="stDataFrame"] .ag-header,
[data-testid="stDataFrame"] .ag-cell,
[data-testid="stDataFrame"] .ag-row,
[data-testid="stDataFrame"] .ag-row-even,
[data-testid="stDataFrame"] .ag-row-odd { background-color: #ffffff !important; }

/* st.table 用：コンテナと全子孫を白に（Streamlit の DOM で無視されないよう複数指定） */
[data-testid="stTable"],
[data-testid="stTable"] *,
[data-testid="stTable"] table,
[data-testid="stTable"] thead,
[data-testid="stTable"] tbody,
[data-testid="stTable"] tr,
[data-testid="stTable"] th,
[data-testid="stTable"] td { background-color: #ffffff !important; }

/* クラス名でのフォールバック（Streamlit バージョン差に対応） */
.stTable table,
.stTable thead,
.stTable tbody,
.stTable tr,
.stTable th,
.stTable td,
div[data-testid="stTable"] table,
div[data-testid="stTable"] th,
div[data-testid="stTable"] td { background-color: #ffffff !important; }
</style>
"""


def inject_table_white_bg(st):
    """
    st.data_editor / st.dataframe / st.table に白背景を適用する。
    アプリ起動直後（set_page_config の後など）で1回呼ぶ。

    Streamlit 以外（テスト・別フレームワーク・通常の python 実行など）で
    呼ばれた場合は何もしない。悪影響はない。
    """
    if not hasattr(st, "markdown") or not callable(getattr(st, "markdown")):
        return
    st.markdown(STREAMLIT_TABLE_WHITE_BG_CSS, unsafe_allow_html=True)
