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

# --- 1. アプリ設定・日本語豆腐文字対策 ---
st.set_page_config(page_title="TRUNK TECH - イタドリ (木取り特化)", layout="wide")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['IPAexGothic', 'Noto Sans CJK JP', 'DejaVu Sans']

# --- 背景画像 & 視認性向上CSS ---
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
        /* メインコンテンツの透明度 */
        [data-testid="stAppViewBlockContainer"] {{
            background-color: rgba(255, 255, 255, 0.72) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            padding: 3rem !important;
            border-radius: 20px;
            margin-top: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }}
        /* 設定エリア（右カラム）を一つの半透明カードにする */
        .settings-card {{
            background-color: rgba(255, 255, 255, 0.85) !important;
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(0,0,0,0.1);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        [data-testid="stWidgetLabel"] p {{ font-weight: bold !important; color: #333 !important; }}
        </style>
        """
        st.markdown(style, unsafe_allow_html=True)

set_design_theme("itadori.jpg")

# --- 2. 木取りエンジン (TrunkTechEngine) ---
class TrunkTechEngine:
    def __init__(self, kerf: float = 3.0):
        self.kerf = kerf
    def pack_sheets(self, parts, vw, vh):
        # 面積の大きい順にソート（歩留まり向上の定石）
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
            {"名称": "棚板", "巾(W)": 600.0, "奥行(D)": 300.0, "枚数": 6}
        ])
    shelf_df = st.data_editor(st.session_state.shelf_list, num_rows="dynamic", use_container_width=True, key="shelf_editor")

with col_in2:
    # 設定エリアをHTML divで囲み、CSSを適用
    st.markdown('<div class="settings-card">', unsafe_allow_html=True)
    st.subheader("⚙️ 設定")
    
    # 3x6寸法入力
    st.write("**3×6寸法**")
    c36_1, c36_2, c36_3, c36_4, c36_5 = st.columns([1, 3, 1, 3, 1])
    c36_1.markdown("<div style='padding-top:10px;'>縦</div>", unsafe_allow_html=True)
    v36 = c36_2.number_input("36V", value=1820.0, label_visibility="collapsed")
    c36_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
    h36 = c36_4.number_input("36H", value=910.0, label_visibility="collapsed")
    c36_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
    
    st.write("") # スペース
    
    # 4x8寸法入力
    st.write("**4×8寸法**")
    c48_1, c48_2, c48_3, c48_4, c48_5 = st.columns([1, 3, 1, 3, 1])
    c48_1.markdown("<div style='padding-top:10px;'>縦</div>", unsafe_allow_html=True)
    v48 = c48_2.number_input("48V", value=2440.0, label_visibility="collapsed")
    c48_3.markdown("<div style='padding-top:10px;'>mm × 横</div>", unsafe_allow_html=True)
    h48 = c48_4.number_input("48H", value=1220.0, label_visibility="collapsed")
    c48_5.markdown("<div style='padding-top:10px;'>mm</div>", unsafe_allow_html=True)
    
    st.divider()
    
    size_choice = st.radio("板サイズの選定方法", ["自動選定 (効率優先)", "3x6固定", "4x8固定", "手動入力"])
    
    if size_choice == "手動入力":
        mc1, mc2 = st.columns(2)
        manual_w = mc1.number_input("長さ", value=1820.0)
        manual_h = mc2.number_input("巾", value=910.0)
    
    kerf = st.number_input("刃物厚 (mm)", value=3.0, step=0.1)
    
    st.markdown('</div>', unsafe_allow_html=True) # settings-card 終了

# --- 4. 木取り計算実行 ---
if st.button("🧮 木取り図を作成する", use_container_width=True):
    all_parts = []
    for _, row in shelf_df.iterrows():
        if pd.notna(row.get("名称")) and pd.notna(row.get("枚数")):
            for i in range(int(row["枚数"])):
                all_parts.append({"n": f"{row['名称']}", "w": row["巾(W)"], "d": row["奥行(D)"]})

    if not all_parts:
        st.warning("棚板リストを入力してください。")
    else:
        engine = TrunkTechEngine(kerf=kerf)
        
        # 板寸法の定義 (有効面積のためマージン10mm)
        s36_dim = (v36 - 10, h36 - 10, "3x6")
        s48_dim = (v48 - 10, h48 - 10, "4x8")
        
        sim_results = []
        if "自動" in size_choice:
            test_modes = [s36_dim, s48_dim]
        elif "3x6" in size_choice:
            test_modes = [s36_dim]
        elif "4x8" in size_choice:
            test_modes = [s48_dim]
        else: # 手動
            test_modes = [(manual_w - 10, manual_h - 10, "手動")]

        for vw, vh, label in test_modes:
            sheets = engine.pack_sheets(all_parts, vw, vh)
            # 効率判定：使用枚数が少ないほう、枚数が同じなら板が小さいほう（3x6）を優先
            sim_results.append({
                "label": label, 
                "sheets": sheets, 
                "sheet_count": len(sheets), 
                "vw": vw, "vh": vh,
                "score": len(sheets) * (vw * vh) # 面積ベースのスコア
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
