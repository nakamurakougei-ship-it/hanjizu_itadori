import os
import sys
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import japanize_matplotlib
import pandas as pd

# 共通モジュール（テーブル白背景）を読み込む
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)
from streamlit_common import inject_table_white_bg

# --- 1. アプリ設定 ---
st.set_page_config(page_title="TRUNK TECH - 棚板木取り", layout="wide")
inject_table_white_bg(st)

# --- 2. 木取りエンジン (TrunkTechEngine 改良版) ---
class TrunkTechEngine:
    def __init__(self, kerf: float = 3.0):
        self.kerf = kerf  # 刃厚

    def pack_sheets(self, parts, vw, vh):
        """
        パーツを回転させず、定尺板(vw, vh)に詰め込む。
        parts: [{'name': str, 'w': float, 'd': float}, ...]
        """
        # 面積の大きい順にソートして詰め込み効率を上げる
        sorted_parts = sorted(parts, key=lambda x: (x['w'], x['d']), reverse=True)
        sheets = []

        def pack(p):
            for s in sheets:
                for r in s['rows']:
                    if r['h'] >= p['d'] and (vw - r['used_w']) >= p['w']:
                        r['parts'].append({'n': p['name'], 'x': r['used_w'], 'y': r['y'], 'w': p['w'], 'h': p['d']})
                        r['used_w'] += p['w'] + self.kerf
                        return True
                if (vh - s['used_h']) >= p['d']:
                    s['rows'].append({'y': s['used_h'], 'h': p['d'], 'used_w': p['w'] + self.kerf, 
                                      'parts': [{'n': p['name'], 'x': 0, 'y': s['used_h'], 'w': p['w'], 'h': p['d']}]})
                    s['used_h'] += p['d'] + self.kerf
                    return True
            return False

        for p in sorted_parts:
            if not pack(p):
                sheets.append({'id': len(sheets)+1, 'used_h': p['d'] + self.kerf, 
                               'rows': [{'y': 0, 'h': p['d'], 'used_w': p['w'] + self.kerf, 
                                         'parts': [{'n': p['name'], 'x': 0, 'y': 0, 'w': p['w'], 'h': p['d']}]}]})
        return sheets

# --- 3. 材料マスタの初期化 ---
if 'material_master' not in st.session_state:
    st.session_state.material_master = pd.DataFrame([
        {"用途": "下地材", "材料名": "ポリ板 (ホワイト)", "厚み(mm)": 2.5, "3x6単価": 4500, "4x8単価": 7200},
        {"用途": "下地材", "材料名": "ラワンランバー", "厚み(mm)": 15.0, "3x6単価": 2250, "4x8単価": 3600},
    ])

# --- 4. UI: 棚板入力セクション ---
st.title("🪚 TRUNK TECH：棚板木取り・ネスティング")

with st.expander("📊 1. 材料リストの管理 (大福帳)"):
    edited_master = st.data_editor(st.session_state.material_master, num_rows="dynamic", use_container_width=True)
    if st.button("マスタ更新"):
        st.session_state.material_master = edited_master
        st.rerun()

st.divider()

col_in1, col_in2 = st.columns([2, 1])

with col_in1:
    st.subheader("📋 棚板リストの入力")
    # 初期データ
    if 'shelf_list' not in st.session_state:
        st.session_state.shelf_list = pd.DataFrame([
            {"名称": "棚板A", "巾(W)": 900.0, "奥行(D)": 450.0, "枚数": 4},
            {"名称": "棚板B", "巾(W)": 600.0, "奥行(D)": 300.0, "枚数": 6}
        ])
    
    shelf_df = st.data_editor(st.session_state.shelf_list, num_rows="dynamic", use_container_width=True, key="shelf_editor")

with col_in2:
    st.subheader("⚙️ 設定")
    m_df = st.session_state.material_master
    m_list = m_df["材料名"].tolist()
    selected_mat = st.selectbox("使用する材料", m_list)
    L_INFO = m_df[m_df["材料名"] == selected_mat].iloc[0]
    
    size_mode = st.radio("板サイズ選定", ["自動選定 (コスト優先)", "3x6固定", "4x8固定"])
    kerf = st.number_input("刃物径 (mm)", value=3.0, step=0.1)

# --- 5. 木取り計算実行 ---
if st.button("🧮 木取り図を作成する"):
    # 全パーツをフラットなリストに展開
    all_parts = []
    for _, row in shelf_df.iterrows():
        for i in range(int(row["枚数"])):
            all_parts.append({"name": f"{row['名称']}-{i+1}", "w": row["巾(W)"], "d": row["奥行(D)"]})

    engine = TrunkTechEngine(kerf=kerf)
    
    # 3x6と4x8の両方でシミュレーション
    s36_dim = (1810, 900, L_INFO["3x6単価"], "3x6")
    s48_dim = (2414, 1202, L_INFO["4x8単価"], "4x8")
    
    sim_results = []
    for vw, vh, price, label in [s36_dim, s48_dim]:
        if price > 0:
            sheets = engine.pack_sheets(all_parts, vw, vh)
            sim_results.append({"label": label, "sheets": sheets, "total_cost": len(sheets) * price, "vw": vw+10, "vh": vh+10, "price": price})

    # 最適解の選定
    if "自動" in size_mode:
        best = min(sim_results, key=lambda x: x["total_cost"])
    else:
        best = next(r for r in sim_results if r["label"] in size_mode)

    # --- 6. 結果表示 ---
    st.divider()
    st.success(f"💡 最適結果：**{best['label']}板** を **{len(best['sheets'])}枚** 使用（合計材料費：{int(best['total_cost']):,}円）")

    for s in best["sheets"]:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_xlim(0, best["vw"]); ax.set_ylim(0, best["vh"]); ax.set_aspect('equal')
        ax.add_patch(patches.Rectangle((0,0), best["vw"], best["vh"], fc='#fdf5e6', ec='#8b4513', lw=2))
        ax.set_title(f"【{selected_mat}】 {best['label']} ID:{s['id']}")
        
        for r in s['rows']:
            for p in r['parts']:
                ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", ha='center', va='center', fontsize=8, fontweight='bold')
        st.pyplot(fig)

    # 見積明細
    st.subheader("📋 部材・材料明細")
    st.table(pd.DataFrame([{"項目": "使用材料", "内容": f"{selected_mat} ({best['label']})"},
                           {"項目": "枚数", "内容": f"{len(best['sheets'])}枚"},
                           {"項目": "単価", "内容": f"{int(best['price']):,}円"},
                           {"項目": "合計金額", "内容": f"{int(best['total_cost']):,}円"}]))
