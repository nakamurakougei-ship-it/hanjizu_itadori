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
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import base64
import os

# 共通モジュール（テーブル白背景）を読み込む（同フォルダの streamlit_common を参照）
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
from streamlit_common import inject_table_white_bg

# --- 1. アプリ設定・日本語豆腐文字対策 ---
st.set_page_config(page_title="TRUNK TECH - イタドリ (木取り特化)", layout="wide")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['IPAexGothic', 'Noto Sans CJK JP', 'DejaVu Sans']

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

# --- 3. UI メインエリア ---
st.markdown(
    '# イタドリ '
    '<span style="font-size: 0.35em; font-weight: normal; color: #fff; background-color: #333; padding: 2px 8px; margin-left: 8px; border-radius: 4px;">  Powered by TrunkTechEngine  </span>',
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
        v36 = c36_2.number_input("v36", value=1820.0, label_visibility="collapsed")
        c36_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
        h36 = c36_4.number_input("h36", value=910.0, label_visibility="collapsed")
        c36_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
        
        st.markdown("**■ 4×8寸法**")
        c48_1, c48_2, c48_3, c48_4, c48_5 = st.columns([1, 4, 2, 4, 1])
        c48_1.markdown("<div style='padding-top:10px;'>縦</div>", unsafe_allow_html=True)
        v48 = c48_2.number_input("v48", value=2440.0, label_visibility="collapsed")
        c48_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
        h48 = c48_4.number_input("h48", value=1220.0, label_visibility="collapsed")
        c48_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
        
        st.divider()
        size_choice = st.radio("板サイズの選定方法", ["自動選定 (効率優先)", "3x6固定", "4x8固定", "手動入力"], key="size_choice")
        
        if size_choice == "手動入力":
            mc1, mc2 = st.columns(2)
            manual_w = mc1.number_input("板長さ(手動)", value=1820.0)
            manual_h = mc2.number_input("板巾(手動)", value=910.0)
        
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
    shelf_df = st.data_editor(st.session_state.shelf_list, num_rows="dynamic", use_container_width=True, key="shelf_editor")

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
            s36_dim = (v36 - 10, h36 - 10, "3x6")
            s48_dim = (v48 - 10, h48 - 10, "4x8")
            sim_results = []
            if "自動" in size_choice:
                test_modes = [s36_dim, s48_dim]
            elif "3x6" in size_choice:
                test_modes = [s36_dim]
            elif "4x8" in size_choice:
                test_modes = [s48_dim]
            else:
                test_modes = [(manual_w - 10, manual_h - 10, "手動")]
            for vw, vh, label in test_modes:
                sheets = engine.pack_sheets(all_parts, vw, vh)
                sim_results.append({
                    "label": label, "sheets": sheets, "sheet_count": len(sheets),
                    "vw": vw, "vh": vh, "score": len(sheets) * (vw * vh)
                })
            best = min(sim_results, key=lambda x: x["score"])
            st.session_state["diagram_result"] = best

    if "diagram_result" in st.session_state:
        best = st.session_state["diagram_result"]
        st.success(f"💡 木取り完了：**{best['label']}板** を **{best['sheet_count']}枚** 使用します。")

# 大画面時：右カラムに木取図を表示（スマホでは従来どおり下に表示される）
if "diagram_result" in st.session_state:
    best = st.session_state["diagram_result"]
    with col_right:
        st.subheader("🪚 木取図")
        for s in best["sheets"]:
            fig, ax = plt.subplots(figsize=(8, 4))
            v_w_full, v_h_full = best["vw"] + 10, best["vh"] + 10
            ax.set_xlim(0, v_w_full); ax.set_ylim(0, v_h_full); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), v_w_full, v_h_full, fc='#fdf5e6', ec='#8b4513', lw=2))
            ax.set_title(f"【木取り図】 ID:{s['id']} ({best['label']}：{int(v_w_full)}x{int(v_h_full)})", fontsize=12, fontweight='bold')
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", ha='center', va='center', fontsize=8, fontweight='bold')
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
            v_w_full, v_h_full = best["vw"] + 10, best["vh"] + 10
            ax.set_xlim(0, v_w_full); ax.set_ylim(0, v_h_full); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), v_w_full, v_h_full, fc='#fdf5e6', ec='#8b4513', lw=2))
            ax.set_title(f"【木取り図】 ID:{s['id']} ({best['label']}：{int(v_w_full)}x{int(v_h_full)})", fontsize=12, fontweight='bold')
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", ha='center', va='center', fontsize=9, fontweight='bold')
            st.pyplot(fig)
            plt.close(fig)
