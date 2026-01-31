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
st.set_page_config(page_title="TRUNK TECH - イタドリ (棚板木取り)", layout="wide")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['IPAexGothic', 'Noto Sans CJK JP', 'DejaVu Sans']

# --- 背景画像 & 磨りガラス風CSS (Ver. 1.8 修正版) ---
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
        /* 【修正】メインコンテンツの背景透過を強化 */
        [data-testid="stAppViewBlockContainer"] {{
            background-color: rgba(255, 255, 255, 0.78) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            padding: 3rem !important;
            border-radius: 25px;
            margin-top: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }}
        /* 入力エリアの視認性確保 */
        [data-testid="stWidgetLabel"] p {{
            color: #000 !important;
            font-weight: bold !important;
        }}
        [data-testid="stHeader"] {{
            background-color: rgba(0,0,0,0) !important;
        }}
        </style>
        """
        st.markdown(style, unsafe_allow_html=True)

set_design_theme("itadori.jpg")

# --- 2. 木取りエンジン ---
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

# --- 3. データ初期化 & 【重要】KeyError対策のマイグレーション ---
if 'material_master' not in st.session_state:
    st.session_state.material_master = pd.DataFrame([
        {"材料名": "ポリ板", "厚み(mm)": 2.5, "3x6単価": 4500, "4x8単価": 7200},
        {"材料名": "ラワンランバー", "厚み(mm)": 15.0, "3x6単価": 2250, "4x8単価": 3600},
        {"材料名": "ラワンランバー", "厚み(mm)": 21.0, "3x6単価": 3500, "4x8単価": 5100}
    ])
else:
    # 古いセッションデータに「厚み(mm)」がない場合の補完
    if "厚み(mm)" not in st.session_state.material_master.columns:
        st.session_state.material_master["厚み(mm)"] = 15.0

if 'shelf_list' not in st.session_state:
    st.session_state.shelf_list = pd.DataFrame([
        {"名称": "側板", "厚み(mm)": 15.0, "巾(W)": 900.0, "奥行(D)": 450.0, "枚数": 4},
        {"名称": "棚板", "厚み(mm)": 15.0, "巾(W)": 600.0, "奥行(D)": 300.0, "枚数": 6}
    ])
else:
    if "厚み(mm)" not in st.session_state.shelf_list.columns:
        st.session_state.shelf_list["厚み(mm)"] = 15.0

# --- 4. UI: 大福帳セクション ---
st.title("🌱 木取り専用アプリ：イタドリ (ITADORI)")

with st.expander("📊 1. 材料リストの管理 (大福帳)"):
    uploaded_file = st.file_uploader("材料リスト(CSV)読込", type="csv")
    if uploaded_file: 
        st.session_state.material_master = pd.read_csv(uploaded_file)
        st.rerun()
    
    edited_master = st.data_editor(st.session_state.material_master, num_rows="dynamic", use_container_width=True)
    if st.button("マスタを更新して反映"): 
        st.session_state.material_master = edited_master; st.rerun()

st.divider()
col_in1, col_in2 = st.columns([2, 1])

with col_in1:
    st.subheader("📋 棚板リストの入力")
    shelf_df = st.data_editor(st.session_state.shelf_list, num_rows="dynamic", use_container_width=True, key="shelf_editor")

with col_in2:
    st.subheader("⚙️ 設定")
    m_df = st.session_state.material_master.copy()
    # 【KeyError回避策】安全に表示名を作成
    m_df["表示名"] = m_df.apply(lambda x: f"{x.get('材料名', '未設定')} ({x.get('厚み(mm)', 0)}mm)", axis=1)
    sel_mat_name = st.selectbox("材料選択 (定尺材)", m_df["表示名"].tolist())
    L_INFO = m_df[m_df["表示名"] == sel_mat_name].iloc[0]
    
    size_choice = st.radio("板サイズ選定", ["自動選定", "3x6固定", "4x8固定", "手動入力"])
    custom_w, custom_h = 1820.0, 910.0
    if size_choice == "手動入力":
        c1, c2 = st.columns(2)
        custom_w = c1.number_input("板長さ", value=1820.0); custom_h = c2.number_input("板巾", value=910.0)
    kerf = st.number_input("刃物厚 (mm)", value=3.0, step=0.1)

# --- 5. 木取り計算実行 ---
if st.button("🧮 木取り図を作成する", use_container_width=True):
    target_t = float(L_INFO.get("厚み(mm)", 0))
    all_parts = []
    for _, row in shelf_df.iterrows():
        if pd.notna(row.get("名称")) and pd.notna(row.get("枚数")):
            # 板厚が一致するパーツのみ抽出
            if float(row.get("厚み(mm)", 0)) == target_t:
                for i in range(int(row["枚数"])):
                    all_parts.append({"n": f"{row['名称']}", "w": row["巾(W)"], "d": row["奥行(D)"]})

    if not all_parts:
        st.warning(f"厚み {target_t}mm の部材がリストにありません。")
    else:
        engine = TrunkTechEngine(kerf=kerf)
        s36_dim = (1810, 900, L_INFO.get("3x6単価", 0), "3x6")
        s48_dim = (2414, 1202, L_INFO.get("4x8単価", 0), "4x8")
        
        sim_results = []
        test_modes = [s36_dim, s48_dim] if "自動" in size_choice else ([s36_dim] if "3x6" in size_choice else ([s48_dim] if "4x8" in size_choice else [(custom_w-10, custom_h-10, 0, "手動")]))

        for vw, vh, price, label in test_modes:
            if price >= 0:
                sheets = engine.pack_sheets(all_parts, vw, vh)
                sim_results.append({"label": label, "sheets": sheets, "total_cost": len(sheets) * price, "vw": vw, "vh": vh, "price": price})

        best = min(sim_results, key=lambda x: x["total_cost"]) if "自動" in size_choice else sim_results[0]

        st.divider()
        st.success(f"💡 木取り完了：**{L_INFO['材料名']} ({target_t}mm)** / **{best['label']}板** を **{len(best['sheets'])}枚** 使用")

        for s in best["sheets"]:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.set_xlim(0, best["vw"]+10); ax.set_ylim(0, best["vh"]+10); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), best["vw"]+10, best["vh"]+10, fc='#fdf5e6', ec='#8b4513', lw=2))
            ax.set_title(f"【{L_INFO['材料名']} {target_t}mm】 ID:{s['id']} ({best['label']})", fontsize=14, fontweight='bold')
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", ha='center', va='center', fontsize=9, fontweight='bold')
            st.pyplot(fig)

        st.subheader("📋 積算見積明細")
        st.table(pd.DataFrame([
            {"項目": "使用材料", "内容": f"{L_INFO['材料名']} ({target_t}mm)"},
            {"項目": "板サイズ", "内容": f"{best['label']}"},
            {"項目": "単価", "内容": f"{int(best['price']):,} 円"},
            {"項目": "枚数", "内容": f"{len(best['sheets'])} 枚"},
            {"項目": "合計材料費", "内容": f"**{int(best['total_cost']):,} 円**"}
        ]))
