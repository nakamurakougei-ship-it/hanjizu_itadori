import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import base64
import os

# --- 1. アプリ設定・日本語フォント設定 ---
st.set_page_config(page_title="TRUNK TECH - イタドリ (棚板木取り)", layout="wide")

# Matplotlibの日本語表示設定 (最新環境対応)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['IPAexGothic', 'Noto Sans CJK JP', 'DejaVu Sans']

# --- 背景画像設定 ---
def set_bg_image(image_file):
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
        /* レイアウト崩れ防止：メインコンテンツの背景を調整 */
        .main .block-container {{
            background-color: rgba(255, 255, 255, 0.9);
            padding: 2rem;
            border-radius: 15px;
            margin-top: 1rem;
        }}
        </style>
        """
        st.markdown(style, unsafe_allow_html=True)

set_bg_image("itadori.jpg")

# --- 2. 木取りエンジン (TrunkTechEngine) ---
class TrunkTechEngine:
    def __init__(self, kerf: float = 3.0):
        self.kerf = kerf  # 刃物厚

    def pack_sheets(self, parts, vw, vh):
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

# --- 3. セッション状態の初期化 ---
if 'material_master' not in st.session_state:
    st.session_state.material_master = pd.DataFrame([
        {"材料名": "ポリ板 (ホワイト)", "3x6単価": 4500, "4x8単価": 7200},
        {"材料名": "ラワンランバー", "3x6単価": 2250, "4x8単価": 3600},
    ])
if 'shelf_list' not in st.session_state:
    st.session_state.shelf_list = pd.DataFrame([
        {"名称": "棚板A", "巾(W)": 900.0, "奥行(D)": 450.0, "枚数": 4},
        {"名称": "棚板B", "巾(W)": 600.0, "奥行(D)": 300.0, "枚数": 6}
    ])

# --- 4. UI: 大福帳セクション ---
st.title("🌱 木取り専用アプリ：イタドリ (ITADORI)")

with st.expander("📊 1. 材料リストの管理 (大福帳)"):
    uploaded_file = st.file_uploader("ローカルの材料リスト(CSV)を読み込む", type="csv")
    if uploaded_file:
        st.session_state.material_master = pd.read_csv(uploaded_file)
    
    edited_master = st.data_editor(st.session_state.material_master, num_rows="dynamic", use_container_width=True)
    if st.button("マスタの内容を反映"):
        st.session_state.material_master = edited_master
        st.rerun()

st.divider()

# --- 5. 入力・設定エリア ---
col_in1, col_in2 = st.columns([2, 1])

with col_in1:
    st.subheader("📋 棚板リストの入力")
    st.caption("行の左端をドラッグして並び替え可能です。")
    shelf_df = st.data_editor(st.session_state.shelf_list, num_rows="dynamic", use_container_width=True, key="shelf_editor")

with col_in2:
    st.subheader("⚙️ 設定")
    m_list = st.session_state.material_master["材料名"].tolist()
    selected_mat = st.selectbox("使用する材料", m_list)
    L_INFO = st.session_state.material_master[st.session_state.material_master["材料名"] == selected_mat].iloc[0]
    
    size_choice = st.radio("板サイズ選定", ["自動選定", "3x6固定", "4x8固定", "手動入力"])
    
    custom_w, custom_h = 1820.0, 910.0
    if size_choice == "手動入力":
        col_c1, col_c2 = st.columns(2)
        custom_w = col_c1.number_input("板長さ (mm)", value=1820.0)
        custom_h = col_c2.number_input("板巾 (mm)", value=910.0)
    
    kerf = st.number_input("刃物厚 (mm)", value=3.0, step=0.1)

# --- 6. 木取り計算実行 ---
if st.button("🧮 木取り図を作成する", use_container_width=True):
    all_parts = []
    for _, row in shelf_df.iterrows():
        if pd.notna(row["名称"]) and pd.notna(row["枚数"]):
            for i in range(int(row["枚数"])):
                all_parts.append({"name": f"{row['名称']}", "w": row["巾(W)"], "d": row["奥行(D)"]})

    if not all_parts:
        st.warning("棚板リストを入力してください。")
    else:
        engine = TrunkTechEngine(kerf=kerf)
        s36_dim = (1810, 900, L_INFO.get("3x6単価", 0), "3x6")
        s48_dim = (2414, 1202, L_INFO.get("4x8単価", 0), "4x8")
        
        sim_results = []
        if size_choice == "自動選定":
            for vw, vh, price, label in [s36_dim, s48_dim]:
                if price > 0:
                    sheets = engine.pack_sheets(all_parts, vw, vh)
                    sim_results.append({"label": label, "sheets": sheets, "total_cost": len(sheets) * price, "vw": vw, "vh": vh, "price": price})
            best = min(sim_results, key=lambda x: x["total_cost"])
        elif size_choice == "3x6固定":
            sheets = engine.pack_sheets(all_parts, s36_dim[0], s36_dim[1])
            best = {"label": "3x6", "sheets": sheets, "total_cost": len(sheets) * s36_dim[2], "vw": s36_dim[0], "vh": s36_dim[1], "price": s36_dim[2]}
        elif size_choice == "4x8固定":
            sheets = engine.pack_sheets(all_parts, s48_dim[0], s48_dim[1])
            best = {"label": "4x8", "sheets": sheets, "total_cost": len(sheets) * s48_dim[2], "vw": s48_dim[0], "vh": s48_dim[1], "price": s48_dim[2]}
        else:
            sheets = engine.pack_sheets(all_parts, custom_w - 10, custom_h - 10)
            best = {"label": "カスタム", "sheets": sheets, "total_cost": 0, "vw": custom_w-10, "vh": custom_h-10, "price": 0}

        st.divider()
        st.success(f"💡 木取り完了：**{best['label']}板** を **{len(best['sheets'])}枚** 使用")
        st.markdown('<button onclick="window.print()" style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; width: 100%;">🖨️ 画面を印刷する</button>', unsafe_allow_html=True)

        for s in best["sheets"]:
            fig, ax = plt.subplots(figsize=(12, 6))
            v_w_full, v_h_full = best["vw"] + 10, best["vh"] + 10
            ax.set_xlim(0, v_w_full); ax.set_ylim(0, v_h_full); ax.set_aspect('equal')
            ax.add_patch(patches.Rectangle((0,0), v_w_full, v_h_full, fc='#fdf5e6', ec='#8b4513', lw=2))
            ax.set_title(f"【{selected_mat}】 ID:{s['id']} ({int(v_w_full)}x{int(v_h_full)})", fontsize=14, fontweight='bold')
            for r in s['rows']:
                for p in r['parts']:
                    ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1, ec='black', fc='#deb887', alpha=0.8))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", ha='center', va='center', fontsize=9, fontweight='bold')
            st.pyplot(fig)

        # --- 7. 詳細明細 ---
        st.subheader("📋 積算見積明細")
        bill_data = [
            {"項目": "使用材料", "内容": f"{selected_mat}"},
            {"項目": "板サイズ", "内容": f"{best['label']}"},
            {"項目": "単価", "内容": f"{int(best['price']):,} 円"},
            {"項目": "必要枚数", "内容": f"{len(best['sheets'])} 枚"},
            {"項目": "合計材料費", "内容": f"{int(best['total_cost']):,} 円"}
        ]
        st.table(pd.DataFrame(bill_data))
