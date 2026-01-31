import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np

# --- 0. 文字化け（豆腐）対策：日本語フォント設定 ---
# Streamlit CloudのLinux環境でも比較的安定して日本語を表示するための設定
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'IPAexGothic', 'DejaVu Sans']

# --- 1. アプリ設定 ---
st.set_page_config(page_title="TRUNK TECH - 棚板木取り Ver. 1.2", layout="wide")

# --- 2. 木取りエンジン (TrunkTechEngine) ---
class TrunkTechEngine:
    def __init__(self, kerf: float = 3.0):
        self.kerf = kerf  # 刃物厚

    def pack_sheets(self, parts, vw, vh):
        # 順序列を尊重しつつ、指定がない場合は面積順にソート
        sorted_parts = parts.copy()
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

# --- 3. 材料マスタ（大福帳）の管理 ---
if 'material_master' not in st.session_state:
    st.session_state.material_master = pd.DataFrame([
        {"用途": "下地材", "材料名": "ポリ板 (ホワイト)", "厚み(mm)": 2.5, "3x6単価": 4500, "4x8単価": 7200},
        {"用途": "下地材", "材料名": "ラワンランバー", "厚み(mm)": 15.0, "3x6単価": 2250, "4x8単価": 3600},
    ])

# --- 4. UI: 設定セクション ---
st.title("🪚 TRUNK TECH：棚板木取り・ネスティング Ver. 1.2")

with st.sidebar:
    st.header("⚙️ 全体設定")
    
    # 刃物厚
    kerf = st.number_input("刃物厚 (mm)", value=3.0, step=0.1, help="ノコ目の厚みを入力してください")
    
    st.divider()
    st.subheader("📏 定尺寸法の設定")
    st.info("メーカー公差を含めた有効寸法を入力してください")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        v36_w = st.number_input("3x6 長 (W)", value=1820.0)
        v36_d = st.number_input("3x6 巾 (D)", value=910.0)
    with col_s2:
        v48_w = st.number_input("4x8 長 (W)", value=2424.0)
        v48_d = st.number_input("4x8 巾 (D)", value=1212.0)

    st.divider()
    st.subheader("📂 材料データの読込")
    uploaded_master = st.file_uploader("ローカルの大福帳(CSV)を読み込む", type="csv")
    if uploaded_master:
        st.session_state.material_master = pd.read_csv(uploaded_master)
        st.success("材料リストを更新しました")

# --- 5. 材料選択と棚板入力 ---
with st.expander("📊 材料リストの確認・編集"):
    edited_master = st.data_editor(st.session_state.material_master, num_rows="dynamic", use_container_width=True)
    if st.button("現在の内容をマスタに保存"):
        st.session_state.material_master = edited_master
        st.rerun()

st.subheader("📋 棚板リストの入力")
st.caption("NO列の数字を変えて、木取りの優先順位（並び順）を調整できます")

if 'shelf_list' not in st.session_state:
    st.session_state.shelf_list = pd.DataFrame([
        {"NO": 1, "名称": "側板A", "巾(W)": 900.0, "奥行(D)": 450.0, "枚数": 4},
        {"NO": 2, "名称": "底板", "巾(W)": 600.0, "奥行(D)": 300.0, "枚数": 6}
    ])

# 表示行数を確保するため、高さ(height)を指定せず、内容に合わせて広がるように設定
shelf_df = st.data_editor(
    st.session_state.shelf_list, 
    num_rows="dynamic", 
    use_container_width=True, 
    key="shelf_editor",
    height=400  # 必要に応じて調整
)

col_exec1, col_exec2 = st.columns([1, 1])
with col_exec1:
    m_list = st.session_state.material_master["材料名"].tolist()
    selected_mat = st.selectbox("使用する材料を選択", m_list)
with col_exec2:
    size_mode = st.radio("板サイズ選定", ["自動選定 (コスト優先)", "3x6固定", "4x8固定"], horizontal=True)

# --- 6. 木取り計算と出力 ---
if st.button("🧮 木取り図を作成する", type="primary", use_container_width=True):
    # ソート順を適用
    input_df = shelf_df.sort_values("NO")
    
    all_parts = []
    for _, row in input_df.iterrows():
        if pd.notna(row["名称"]) and pd.notna(row["枚数"]):
            for i in range(int(row["枚数"])):
                all_parts.append({"name": f"{row['名称']}", "w": row["巾(W)"], "d": row["奥行(D)"]})

    if not all_parts:
        st.warning("棚板リストを入力してください。")
    else:
        L_INFO = st.session_state.material_master[st.session_state.material_master["材料名"] == selected_mat].iloc[0]
        engine = TrunkTechEngine(kerf=kerf)
        
        # 定尺寸法の反映
        s36_cfg = (v36_w, v36_d, L_INFO["3x6単価"], "3x6")
        s48_cfg = (v48_w, v48_d, L_INFO["4x8単価"], "4x8")
        
        sim_results = []
        for vw, vh, price, label in [s36_cfg, s48_cfg]:
            if price > 0:
                sheets = engine.pack_sheets(all_parts, vw - 10, vh - 10) # 鼻切り分10mmマイナス
                sim_results.append({
                    "label": label, "sheets": sheets, "total_cost": len(sheets) * price, 
                    "vw": vw, "vh": vh, "price": price
                })

        if "自動" in size_mode:
            best = min(sim_results, key=lambda x: x["total_cost"])
        else:
            best = next((r for r in sim_results if r["label"] in size_mode), sim_results[0])

        st.divider()
        st.success(f"💡 最適結果：**{best['label']}板** を **{len(best['sheets'])}枚** 使用（合計：{int(best['total_cost']):,}円）")

        # 印刷用スクリプト
        st.markdown("""
            <style>
            @media print {
                .stButton, .stFileUploader, .stSelectbox, .stRadio, header { display: none !important; }
                .main { padding: 0 !important; }
            }
            </style>
            """, unsafe_allow_html=True)
        if st.button("🖨️ この画面を印刷する"):
            st.components.v1.html("<script>window.print();</script>", height=0)

        for s in best["sheets"]:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.set_xlim(0, best["vw"]); ax.set_ylim(0, best["vh"]); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), best["vw"], best["vh"], fc='#fdf5e6', ec='#8b4513', lw=2))
            ax.set_title(f"【{selected_mat}】 {best['label']} ID:{s['id']}", fontsize=14, fontweight='bold')
            
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    # 名称を反映（豆腐対策済みのフォントを使用）
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", 
                            ha='center', va='center', fontsize=9, fontweight='bold')
            st.pyplot(fig)

        st.subheader("📋 見積・材料明細")
        st.table(pd.DataFrame([
            {"項目": "使用材料", "内容": f"{selected_mat} ({best['label']})"},
            {"項目": "枚数", "内容": f"{len(best['sheets'])}枚"},
            {"項目": "単価", "内容": f"{int(best['price']):,}円"},
            {"項目": "合計金額", "内容": f"{int(best['total_cost']):,}円"}
        ]))
