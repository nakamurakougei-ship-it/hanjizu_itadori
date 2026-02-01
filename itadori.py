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
        /* メインコンテンツエリアを真っ白（不透明）にして視認性100%確保（複数セレクタで確実に） */
        main,
        [data-testid="stAppViewBlockContainer"],
        [data-testid="stAppViewContainer"] > section,
        [data-testid="stAppViewContainer"] .block-container,
        main .block-container {{
            background-color: #ffffff !important;
            padding: 3rem !important;
            border-radius: 20px;
            margin-top: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
        }}
        /* カラスに隠れないよう：カラム・ブロック・設定パネルも白背景 */
        [data-testid="stVerticalBlock"] > div,
        [data-testid="stHorizontalBlock"] > div,
        div[data-testid="stVerticalBlock"],
        section[data-testid="stSidebar"] + section [data-testid="stVerticalBlock"] {{
            background-color: #ffffff !important;
        }}
        /* 設定パネル（板サイズ選定など）を確実に白く（key付きコンテナ） */
        [data-testid="stVerticalBlock"]:has([data-testid="stRadio"]) {{
            background-color: #ffffff !important;
            padding: 0.5rem 1rem !important;
            border-radius: 8px;
        }}
        /* ラベル文字を太くしてクッキリ見せる */
        [data-testid="stWidgetLabel"] p {{ font-weight: bold !important; color: #000 !important; }}
        </style>
        """
        st.markdown(style, unsafe_allow_html=True)

set_design_theme("itadori.jpg")
inject_table_white_bg(st)

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
st.title("🌱 木取り専用アプリ：イタドリ (ITADORI)")
st.write("定尺板から効率よく木取りを行うための専門機です。")

st.divider()

col_in1, col_in2 = st.columns([1.8, 1.2])

with col_in1:
    st.subheader("📋 棚板リストの入力")
    if 'shelf_list' not in st.session_state:
        st.session_state.shelf_list = pd.DataFrame([
            {"名称": "側板", "巾(W)": 900.0, "奥行(D)": 450.0, "枚数": 4},
            {"名称": "棚板", "巾(W)": 600.0, "奥行(D)": 300.0, "枚_数": 6}
        ])
    # リスト表示（白背景の恩恵を最も受けるエリア）
    shelf_df = st.data_editor(st.session_state.shelf_list, num_rows="dynamic", use_container_width=True, key="shelf_editor")

with col_in2:
    # 【最新機能】border=True のコンテナを使い、設定を物理的な「箱」に閉じ込める（keyで白背景をCSS指定）
    with st.container(border=True, key="settings_panel"):
        st.subheader("⚙️ 設定")
        
        # 3x6寸法入力レイアウト
        st.markdown("**■ 3×6寸法**")
        c36_1, c36_2, c36_3, c36_4, c36_5 = st.columns([1, 4, 2, 4, 1])
        c36_1.markdown("<div style='padding-top:10px;'>縦</div>", unsafe_allow_html=True)
        v36 = c36_2.number_input("v36", value=1820.0, label_visibility="collapsed")
        c36_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
        h36 = c36_4.number_input("h36", value=910.0, label_visibility="collapsed")
        c36_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
        
        # 4x8寸法入力レイアウト
        st.markdown("**■ 4×8寸法**")
        c48_1, c48_2, c48_3, c48_4, c48_5 = st.columns([1, 4, 2, 4, 1])
        c48_1.markdown("<div style='padding-top:10px;'>縦</div>", unsafe_allow_html=True)
        v48 = c48_2.number_input("v48", value=2440.0, label_visibility="collapsed")
        c48_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
        h48 = c48_4.number_input("h48", value=1220.0, label_visibility="collapsed")
        c48_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
        
        st.divider()
        size_choice = st.radio("板サイズの選定方法", ["自動選定 (効率優先)", "3x6固定", "4x8固定", "手動入力"])
        
        if size_choice == "手動入力":
            mc1, mc2 = st.columns(2)
            manual_w = mc1.number_input("板長さ(手動)", value=1820.0)
            manual_h = mc2.number_input("板巾(手動)", value=910.0)
        
        kerf = st.number_input("刃物厚 (mm)", value=3.0, step=0.1)

# --- 4. 木取り計算実行 ---
if st.button("🧮 木取り図を作成する", use_container_width=True):
    all_parts = []
    for _, row in shelf_df.iterrows():
        # 枚数の項目名を柔軟に処理
        qty = row.get("枚数", row.get("枚_数", 0))
        if pd.notna(row.get("名称")) and pd.notna(qty):
            for i in range(int(qty)):
                all_parts.append({"n": f"{row['名称']}", "w": row["巾(W)"], "d": row["奥行(D)"]})

    if not all_parts:
        st.warning("棚板リストを入力してください。")
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

        st.divider()
        st.success(f"💡 木取り完了：**{best['label']}板** を **{best['sheet_count']}枚** 使用します。")

        for s in best["sheets"]:
            fig, ax = plt.subplots(figsize=(12, 6))
            v_w_full, v_h_full = best["vw"] + 10, best["vh"] + 10
            ax.set_xlim(0, v_w_full); ax.set_ylim(0, v_h_full); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), v_w_full, v_h_full, fc='#fdf5e6', ec='#8b4513', lw=2))
            ax.set_title(f"【木取り図】 ID:{s['id']} ({best['label']}：{int(v_w_full)}x{int(v_h_full)})", fontsize=14, fontweight='bold')
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", ha='center', va='center', fontsize=9, fontweight='bold')
            st.pyplot(fig)