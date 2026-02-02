import sys
from types import ModuleType

# --- Python 3.12/3.13 互換性パッチ ---
if 'distutils' not in sys.modules:
    d = ModuleType('distutils'); d.version = ModuleType('distutils.version')
    class LooseVersion:
        def __init__(self, vstring): self.vstring = vstring
        def __lt__(self, other): return False
    d.version.LooseVersion = LooseVersion; sys.modules['distutils'] = d; sys.modules['distutils.version'] = d.version

import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import pandas as pd
import base64
import os
import io

# 共通モジュール（テーブル白背景）を読み込む（同フォルダの streamlit_common を参照）
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
from streamlit_common import inject_table_white_bg

# --- 1. アプリ設定・日本語豆腐文字対策 ---
st.set_page_config(page_title="TRUNK TECH - イタドリ (木取り特化)", layout="wide")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['IPAexGothic', 'Noto Sans CJK JP', 'DejaVu Sans']

def _get_japanese_font():
    """日本語を表示するフォントをパスで指定して取得（名前指定では環境で見つからないため）"""
    if getattr(_get_japanese_font, "_cached", None) is not None:
        return _get_japanese_font._cached
    # Windows の標準フォントパスを優先（ドライブは os.environ や os.path で取得）
    windir = os.environ.get("WINDIR", "C:\\Windows")
    candidates = [
        os.path.join(windir, "Fonts", "msgothic.ttc"),
        os.path.join(windir, "Fonts", "msmincho.ttc"),
        os.path.join(windir, "Fonts", "yugothm.ttc"),
        os.path.join(windir, "Fonts", "meiryo.ttc"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                prop = fm.FontProperties(fname=path)
                _get_japanese_font._cached = prop
                return prop
            except Exception:
                continue
    _get_japanese_font._cached = None
    return None

# 木取図のタイトル・部材名に使う日本語フォント（パス指定で確実に表示）
_jp_font = _get_japanese_font()

# --- 背景画像 & 視認性100% 白背景CSS ---
def set_design_theme(image_file):
    if os.path.exists(image_file):
        with open(image_file, "rb") as f:
            img_data = f.read()
        b64_encoded = base64.b64encode(img_data).decode()
        style = f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{b64_encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        /* メインエリアは透過 → itadori.jpg が背後に表示される（強すぎる白指定はしない） */
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stAppViewContainer"] > section,
        [data-testid="stAppViewContainer"] .block-container,
        main .block-container {{
            background-color: transparent !important;
            padding: 3rem !important;
        }}
        /* 棚板リスト：スクロールバーなしで全行表示（高さを自動に） */
        [data-testid="stDataFrame"] .ag-body-viewport,
        [data-testid="stDataFrame"] .ag-center-cols-viewport {{
            overflow: visible !important;
            max-height: none !important;
        }}
        [data-testid="stDataFrame"] .ag-root-wrapper {{
            height: auto !important;
        }}
        /* 半透明にして背景の鳥（itadori.jpg）が透けて見えるように */
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] > div,
        [data-testid="stDataFrame"] .ag-root-wrapper,
        [data-testid="stDataFrame"] .ag-cell,
        [data-testid="stDataFrame"] .ag-header,
        [data-testid="stTable"],
        [data-testid="stTable"] table,
        [data-testid="stTable"] th,
        [data-testid="stTable"] td {{
            background-color: rgba(255, 255, 255, 0.88) !important;
        }}
        /* ラジオ・入力欄が確実にクリックできるように */
        [data-testid="stRadio"] {{ pointer-events: auto !important; }}
        [data-testid="stRadio"] * {{ pointer-events: auto !important; }}
        /* ラベル文字を太くしてクッキリ見せる */
        [data-testid="stWidgetLabel"] p {{ font-weight: bold !important; color: #000 !important; }}
        /* 左カラム幅を 500px で固定（画面比ではなく数値指定） */
        [class*="main_layout_500"] [data-testid="stHorizontalBlock"] > div:first-child {{
            width: 500px !important;
            max-width: 500px !important;
            min-width: 500px !important;
            flex: 0 0 500px !important;
        }}
        [class*="main_layout_500"] [data-testid="stHorizontalBlock"] > div:last-child {{
            flex: 1 1 auto !important;
        }}
        /* スマホ表示時のみカラム幅を 100% に（768px 以下をスマホ・タブレットとみなす） */
        @media (max-width: 768px) {{
            [class*="main_layout_500"] [data-testid="stHorizontalBlock"] > div:first-child {{
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                flex: 1 1 100% !important;
            }}
            [class*="main_layout_500"] [data-testid="stHorizontalBlock"] > div:last-child {{
                display: none !important;
            }}
        }}
        /* 大画面時のみ：スマホ用の木取図ブロック（下に表示）を非表示 → 右カラムで表示 */
        @media (min-width: 769px) {{
            [class*="mokudori_mobile"] {{
                display: none !important;
            }}
        }}
        /* タイトル＋Powered by バッジ（大画面では横並び、狭い画面ではタイトル下に表示） */
        .title-with-badge .title-main {{
            font-size: 2.25rem !important;
            font-weight: 700 !important;
        }}
        .title-with-badge .powered-badge {{
            font-size: 0.65rem !important;
            font-weight: normal !important;
            color: #fff !important;
            background-color: #333 !important;
            padding: 2px 8px !important;
            margin-left: 8px !important;
            border-radius: 4px !important;
        }}
        @media (max-width: 768px) {{
            .title-with-badge .powered-badge {{
                display: block !important;
                margin-left: 0 !important;
                margin-top: 6px !important;
                width: fit-content !important;
            }}
        }}
        </style>
        """
        st.markdown(style, unsafe_allow_html=True)

inject_table_white_bg(st)
set_design_theme("itadori.jpg")

# --- 2. 木取りエンジン (TrunkTechEngine) ---
class TrunkTechEngine:
    def __init__(self, kerf: float = 3.0):
        self.kerf = kerf
    def pack_sheets(self, parts, vw, vh):
        sorted_parts = sorted(parts, key=lambda x: (x['w'], x['d']), reverse=True)
        sheets = []
        def pack(p):
            for s in sheets:
                for r in s['rows']:
                    if r['h'] >= p['d'] and (vw - r['used_w']) >= p['w']:
                        r['parts'].append({'n': p['n'], 'x': r['used_w'], 'y': r['y'], 'w': p['w'], 'h': p['d']})
                        r['used_w'] += p['w'] + self.kerf; return True
                if (vh - s['used_h']) >= p['d']:
                    s['rows'].append({'y': s['used_h'], 'h': p['d'], 'used_w': p['w'] + self.kerf, 
                                      'parts': [{'n': p['n'], 'x': 0, 'y': s['used_h'], 'w': p['w'], 'h': p['d']}]})
                    s['used_h'] += p['d'] + self.kerf; return True
            return False
        for p in sorted_parts:
            if not pack(p):
                sheets.append({'id': len(sheets)+1, 'used_h': p['d'] + self.kerf, 
                               'rows': [{'y': 0, 'h': p['d'], 'used_w': p['w'] + self.kerf, 
                                         'parts': [{'n': p['n'], 'x': 0, 'y': 0, 'w': p['w'], 'h': p['d']}]}]})
        return sheets


def render_sheet_to_png_bytes(sheet, v_w_full, v_h_full, label):
    """1枚の木取図をPNGバイト列で返す（印刷用）"""
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_xlim(0, v_w_full)
    ax.set_ylim(0, v_h_full)
    ax.set_aspect("equal")
    ax.add_patch(patches.Rectangle((0, 0), v_w_full, v_h_full, fc="#fdf5e6", ec="#8b4513", lw=2))
    kw_title = {"fontsize": 10, "fontweight": "bold"}
    if _jp_font is not None:
        kw_title["fontproperties"] = _jp_font
    ax.set_title(f"【木取り図】 ID:{sheet['id']} ({label}：{int(v_w_full)}x{int(v_h_full)})", **kw_title)
    kw_text = {"ha": "center", "va": "center", "fontsize": 6, "fontweight": "bold"}
    if _jp_font is not None:
        kw_text["fontproperties"] = _jp_font
    for r in sheet["rows"]:
        for p in r["parts"]:
            ax.add_patch(patches.Rectangle((p["x"], p["y"]), p["w"], p["h"], lw=1, ec="black", fc="#deb887", alpha=0.8))
            ax.text(p["x"] + p["w"] / 2, p["y"] + p["h"] / 2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", **kw_text)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def build_print_html(best, max_per_page=None):
    """木取図を印刷用HTMLに出力。max_per_page指定時はその枚数でページ分割、未指定時は1枚ずつ1ページ"""
    v_w_full = best["vw"] + 2
    v_h_full = best["vh"] + 2
    label = best["label"]
    images_b64 = []
    for s in best["sheets"]:
        images_b64.append(render_sheet_to_png_bytes(s, v_w_full, v_h_full, label))
    # 固定せず：未指定なら1枚1ページ、指定があればその枚数でまとめる（目安として可変）
    chunk = max_per_page if max_per_page is not None and max_per_page >= 1 else 1
    pages = [images_b64[i : i + chunk] for i in range(0, len(images_b64), chunk)]
    html_parts = []
    html_parts.append("""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@media print { @page { size: A4; margin: 10mm; } body { margin: 0; } }
.diagram-page { page-break-after: always; padding: 0; }
.diagram-page:last-child { page-break-after: auto; }
.diagram-img { width: 100%; max-height: 32%; object-fit: contain; margin-bottom: 2mm; }
h1 { font-size: 14pt; margin-bottom: 4mm; }
</style></head><body>""")
    for i, page_imgs in enumerate(pages):
        html_parts.append(f'<div class="diagram-page"><h1>木取図（{label}）— {i+1}ページ目</h1>')
        for j, b64 in enumerate(page_imgs):
            html_parts.append(f'<img class="diagram-img" src="data:image/png;base64,{b64}" alt="木取図{j+1}"/>')
        html_parts.append("</div>")
    html_parts.append("</body></html>")
    return "".join(html_parts)


# --- 3. UI メインエリア ---
st.markdown(
    '<div class="title-with-badge">'
    '<span class="title-main">イタドリ</span> '
    '<span class="powered-badge">Powered by TrunkTechEngine</span>'
    '</div>',
    unsafe_allow_html=True
)
st.write("定尺板から効率よく木取りを行うためのアプリです。")

# 左寄せ・縦並び：設定 → 板材リスト。左カラム幅は CSS で 500px 固定（main_layout_500）
with st.container(key="main_layout_500"):
    col_main, col_right = st.columns([3, 1])

with col_main:
    # 1. 設定項目（上）
    with st.container(border=True):
        st.subheader("定尺板寸法設定")
        st.write("使用する板の定尺寸法を変更できます")
        st.markdown("**■ 3×6寸法**")
        c36_1, c36_2, c36_3, c36_4, c36_5 = st.columns([1, 4, 2, 4, 1])
        c36_1.markdown("<div style='padding-top:10px;'>縦</div>", unsafe_allow_html=True)
        v36 = c36_2.number_input("v36", value=1820, min_value=1, step=1, label_visibility="collapsed")
        c36_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
        h36 = c36_4.number_input("h36", value=910, min_value=1, step=1, label_visibility="collapsed")
        c36_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
        
        st.markdown("**■ 4×8寸法**")
        c48_1, c48_2, c48_3, c48_4, c48_5 = st.columns([1, 4, 2, 4, 1])
        c48_1.markdown("<div style='padding-top:10px;'>縦</div>", unsafe_allow_html=True)
        v48 = c48_2.number_input("v48", value=2440, min_value=1, step=1, label_visibility="collapsed")
        c48_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
        h48 = c48_4.number_input("h48", value=1220, min_value=1, step=1, label_visibility="collapsed")
        c48_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
        
        st.markdown("**■ 集成材**")
        lam_w = st.number_input("集成材 幅 (mm)", value=500, min_value=500, max_value=600, step=1, key="lam_w")
        lam_l = st.number_input("集成材 長さ (mm)", value=3600, min_value=3000, max_value=4200, step=1, key="lam_l")
        
        st.divider()
        size_choice = st.radio("板サイズの選定方法", ["自動選定 (効率優先)", "3x6固定", "4x8固定", "集成材", "手動入力"], key="size_choice")
        
        if size_choice == "集成材":
            # 集成材は幅×長さ（縦＝長さ、横＝幅で木取り）
            manual_w = float(lam_l)
            manual_h = float(lam_w)
        elif size_choice == "手動入力":
            mc1, mc2 = st.columns(2)
            manual_w = mc1.number_input("板長さ(手動)", value=1820, min_value=1, step=1)
            manual_h = mc2.number_input("板巾(手動)", value=910, min_value=1, step=1)
        
        kerf = st.number_input("刃物厚 (mm)", value=3.0, step=0.1)

    st.divider()

    # 2. 板材リストの入力（下）・4項目：名称｜幅｜奥行｜枚数
    st.subheader("切板リストの入力")
    if 'shelf_list' not in st.session_state:
        st.session_state.shelf_list = pd.DataFrame([
            {"名称": "部材名", "幅": 900.0, "奥行": 450.0, "枚数": 4},
        ])
    else:
        # 旧カラム（巾(W), 奥行(D), 枚_数）を新4項目に移行
        df = st.session_state.shelf_list.copy()
        if "巾(W)" in df.columns or "奥行(D)" in df.columns or "枚_数" in df.columns:
            new_df = pd.DataFrame()
            new_df["名称"] = df["名称"] if "名称" in df.columns else ""
            new_df["幅"] = df["幅"] if "幅" in df.columns else df["巾(W)"]
            new_df["奥行"] = df["奥行"] if "奥行" in df.columns else df["奥行(D)"]
            new_df["枚数"] = df["枚数"] if "枚数" in df.columns else df["枚_数"]
            st.session_state.shelf_list = new_df
    shelf_df = st.data_editor(st.session_state.shelf_list, num_rows="dynamic", use_container_width=True, height="content", key="shelf_editor")

    # --- 4. 木取り計算実行（ボタンは左カラム内） ---
    if st.button("木取り図を作成する", use_container_width=True, key="btn_mokudori"):
        all_parts = []
        for _, row in shelf_df.iterrows():
            qty = row.get("枚数", 0)
            if pd.notna(row.get("名称")) and pd.notna(qty):
                try:
                    n_qty = int(qty)
                except (TypeError, ValueError):
                    n_qty = 0
                for i in range(n_qty):
                    all_parts.append({"n": f"{row['名称']}", "w": float(row.get("幅", 0)), "d": float(row.get("奥行", 0))})

        if not all_parts:
            st.warning("棚板リストを入力してください。")
            if "diagram_result" in st.session_state:
                del st.session_state["diagram_result"]
        else:
            engine = TrunkTechEngine(kerf=kerf)
            # 板寸法は鼻切り分のみ控え（-2mm）にしてネスティング余裕を確保（-10だと3×6で幅方向に積めない）
            s36_dim = (v36 - 2, h36 - 2, "3x6")
            s48_dim = (v48 - 2, h48 - 2, "4x8")
            s_lam_dim = (float(lam_l) - 2, float(lam_w) - 2, "集成材")
            sim_results = []
            if "自動" in size_choice:
                test_modes = [s36_dim, s48_dim, s_lam_dim]
            elif "3x6" in size_choice:
                test_modes = [s36_dim]
            elif "4x8" in size_choice:
                test_modes = [s48_dim]
            elif "集成材" in size_choice:
                test_modes = [s_lam_dim]
            else:
                test_modes = [(manual_w - 2, manual_h - 2, "手動")]
            for vw, vh, label in test_modes:
                sheets = engine.pack_sheets(all_parts, vw, vh)
                total_area = len(sheets) * (vw * vh)
                sim_results.append({
                    "label": label, "sheets": sheets, "sheet_count": len(sheets),
                    "vw": vw, "vh": vh, "score": total_area
                })
            # 枚数優先、同枚数なら面積が小さい板を選択（3×6を優先）
            best = min(sim_results, key=lambda x: (x["sheet_count"], x["score"]))
            st.session_state["diagram_result"] = best

    if "diagram_result" in st.session_state:
        best = st.session_state["diagram_result"]
        st.success(f"💡 木取り完了：**{best['label']}板** を **{best['sheet_count']}枚** 使用します。")
        # A4に3枚/ページの印刷用HTMLダウンロード
        print_html = build_print_html(best)
        st.download_button(
            "🖨️ 木取図を印刷用にダウンロード（A4）",
            data=print_html,
            file_name="mokudori_print.html",
            mime="text/html",
            use_container_width=True,
            key="btn_print_dl"
        )

# 大画面時：右カラムに木取図を表示（スマホでは従来どおり下に表示される）
if "diagram_result" in st.session_state:
    best = st.session_state["diagram_result"]
    with col_right:
        st.subheader("🪚 木取図")
        for s in best["sheets"]:
            fig, ax = plt.subplots(figsize=(8, 4))
            v_w_full, v_h_full = best["vw"] + 2, best["vh"] + 2
            ax.set_xlim(0, v_w_full); ax.set_ylim(0, v_h_full); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), v_w_full, v_h_full, fc='#fdf5e6', ec='#8b4513', lw=2))
            kw_t = {"fontsize": 12, "fontweight": "bold"}
            if _jp_font is not None:
                kw_t["fontproperties"] = _jp_font
            ax.set_title(f"【木取り図】 ID:{s['id']} ({best['label']}：{int(v_w_full)}x{int(v_h_full)})", **kw_t)
            kw_txt = {"ha": "center", "va": "center", "fontsize": 8, "fontweight": "bold"}
            if _jp_font is not None:
                kw_txt["fontproperties"] = _jp_font
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", **kw_txt)
            st.pyplot(fig)
            plt.close(fig)
else:
    # 木取図なし時は従来どおり右は空欄（背景が見える）
    with col_right:
        pass

# スマホ用：木取図を縦並びの下に表示（大画面では CSS で非表示・右カラムで表示）
if "diagram_result" in st.session_state:
    best = st.session_state["diagram_result"]
    with st.container(key="mokudori_mobile"):
        st.subheader("🪚 木取り図")
        for s in best["sheets"]:
            fig, ax = plt.subplots(figsize=(10, 5))
            v_w_full, v_h_full = best["vw"] + 2, best["vh"] + 2
            ax.set_xlim(0, v_w_full); ax.set_ylim(0, v_h_full); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), v_w_full, v_h_full, fc='#fdf5e6', ec='#8b4513', lw=2))
            kw_t2 = {"fontsize": 12, "fontweight": "bold"}
            if _jp_font is not None:
                kw_t2["fontproperties"] = _jp_font
            ax.set_title(f"【木取り図】 ID:{s['id']} ({best['label']}：{int(v_w_full)}x{int(v_h_full)})", **kw_t2)
            kw_txt2 = {"ha": "center", "va": "center", "fontsize": 9, "fontweight": "bold"}
            if _jp_font is not None:
                kw_txt2["fontproperties"] = _jp_font
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", **kw_txt2)
            st.pyplot(fig)
            plt.close(fig)
