import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import japanize_matplotlib
import pandas as pd
import base64
import os

# --- 1. アプリ設定・日本語豆腐文字対策 ---
st.set_page_config(page_title="判じ図 (Hanjizu) - 職人仕様", layout="wide")

# --- 背景画像 & 半透明ガードCSS (Ver. 27.0 修正版) ---
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
        /* コンテンツエリア全体を半透明の白で浮かせる（現代の透明化手法） */
        .main .block-container {{
            background-color: rgba(255, 255, 255, 0.85);
            padding: 3rem;
            border-radius: 20px;
            margin-top: 2rem;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }}
        /* サイドバーも視認性向上のため半透明化 */
        [data-testid="stSidebar"] {{
            background-color: rgba(240, 242, 246, 0.9);
        }}
        .sidebar-section {{
            padding: 10px; border-radius: 5px; margin-top: 15px; margin-bottom: 10px;
            font-weight: bold; color: white; font-size: 1.1em;
        }}
        .bg-dim {{ background-color: #5d6d7e; }}
        .bg-sub {{ background-color: #2e86c1; }}
        .bg-fin {{ background-color: #d35400; }}
        </style>
        """
        st.markdown(style, unsafe_allow_html=True)

# 画像があればテーマ適用
set_design_theme("itadori.jpg")

st.title("判じ図 (Hanjizu)：厚み連動・視認性向上版 (Ver. 27.0)")

# --- 2. 材料マスタ（大福帳）の初期化 ---
def init_material_master():
    # 変更：厚み項目を追加
    default_data = [
        {"用途": "下地材", "材料名": "ラワンベニヤ", "厚み(mm)": 4.0, "3x6単価": 1200, "4x8単価": 2400},
        {"用途": "下地材", "材料名": "ラワンランバー", "厚み(mm)": 15.0, "3x6単価": 2250, "4x8単価": 3600},
        {"用途": "下地材", "材料名": "ラワンランバー", "厚み(mm)": 21.0, "3x6単価": 3500, "4x8単価": 5100},
        {"用途": "仕上げ材・下地材", "材料名": "シナランバー", "厚み(mm)": 15.0, "3x6単価": 3200, "4x8単価": 5100}
    ]
    if 'material_master' not in st.session_state:
        st.session_state.material_master = pd.DataFrame(default_data)

init_material_master()

# --- 3. 大福帳の管理 ---
with st.expander("📊 材料リストの管理・編集 (光守さんの大福帳)"):
    st.info("厚みごとに単価を登録できます。")
    uploaded_file = st.file_uploader("大福帳読込", type="csv")
    if uploaded_file: st.session_state.material_master = pd.read_csv(uploaded_file)
    
    edited_df = st.data_editor(
        st.session_state.material_master, num_rows="dynamic", use_container_width=True,
        column_config={"用途": st.column_config.SelectboxColumn("用途", options=["仕上げ材", "下地材", "仕上げ材・下地材"], required=True)},
        key="material_editor"
    )
    if st.button("大福帳を更新"):
        st.session_state.material_master = edited_df; st.rerun()

# --- 4. ロジック関数 ---
def split_part_to_fit(name, length, depth, max_l, max_d):
    sub_parts = []
    num_l = -(-length // max_l); num_d = -(-depth // max_d)
    for l_idx in range(int(num_l)):
        for d_idx in range(int(num_d)):
            p_l = max_l if (l_idx + 1) * max_l <= length else length % max_l
            p_d = max_d if (d_idx + 1) * max_d <= depth else depth % max_d
            if p_l <= 0: p_l = max_l
            if p_d <= 0: p_d = max_d
            sub_parts.append({"n": f"{name}({l_idx+1}-{d_idx+1})", "l": p_l, "d": p_d})
    return sub_parts

def pack_sheets_strict_v2(parts, vw, vh, kerf):
    sorted_parts = sorted(parts, key=lambda x: (x['l'], x['d']), reverse=True)
    sheets = []
    def pack(p):
        for s in sheets:
            for r in s['rows']:
                if r['h'] >= p['d'] and (vw - r['used_w']) >= p['l']:
                    r['parts'].append({'n': p['n'], 'x': r['used_w'], 'y': r['y'], 'w': p['l'], 'h': p['d']})
                    r['used_w'] += p['l'] + kerf; return True
            if (vh - s['used_h']) >= p['d']:
                s['rows'].append({'y': s['used_h'], 'h': p['d'], 'used_w': p['l'] + kerf, 'parts': [{'n': p['n'], 'x': 0, 'y': s['used_h'], 'w': p['l'], 'h': p['d']}]})
                s['used_h'] += p['d'] + kerf; return True
        return False
    for p in sorted_parts:
        if not pack(p):
            sheets.append({'id': len(sheets)+1, 'used_h': p['d'] + kerf, 'rows': [{'y': 0, 'h': p['d'], 'used_w': p['l'] + kerf, 'parts': [{'n': p['n'], 'x': 0, 'y': 0, 'w': p['l'], 'h': p['d']}]}]})
    return sheets

# --- 5. サイドバー設定 ---
df = st.session_state.material_master
with st.sidebar:
    st.markdown('<div style="background-color: #fdf5e6; padding: 15px; border-radius: 10px; border: 2px solid #8b4513; text-align: center; margin-bottom: 20px;"><div style="font-size: 1.8em; font-weight: bold; color: #8b4513;">判じ図</div><div style="font-size: 0.8em; color: #5d6d7e;">デジタル伴走者：光守さん</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-section bg-dim">■ 製作寸法</div>', unsafe_allow_html=True)
    W = st.number_input("仕上がり巾 (W)", value=3600.0)
    D = st.number_input("仕上がり奥行 (D)", value=1200.0)
    H = st.number_input("仕上がり高さ (H)", value=300.0)
    
    st.markdown('<div class="sidebar-section bg-sub">■ 下地材の選択</div>', unsafe_allow_html=True)
    l_df = df[df["用途"].str.contains("下地")].copy()
    # 表示名に厚みを含める
    l_df["表示名"] = l_df.apply(lambda x: f"{x['材料名']} ({x['厚み(mm)']}mm)", axis=1)
    sel_l = st.selectbox("使用する下地材", l_df["表示名"].tolist())
    L_INFO = l_df[l_df["表示名"] == sel_l].iloc[0]
    
    size_mode = st.radio("板サイズ選定", ["自動選定 (コスト・効率優先)", "3x6固定", "4x8固定"])
    
    st.markdown('<div class="sidebar-section bg-fin">■ 仕上材の選択</div>', unsafe_allow_html=True)
    f_df = df[df["用途"].str.contains("仕上げ")].copy()
    f_df["表示名"] = f_df.apply(lambda x: f"{x['材料名']} ({x['厚み(mm)']}mm)", axis=1)
    f_long_display = st.selectbox("長手素材", ["仕上げ無し"] + f_df["表示名"].tolist())
    f_short_display = st.selectbox("短手素材", ["仕上げ無し"] + f_df["表示名"].tolist())
    
    KERF = st.number_input("トリマー代 (mm)", min_value=3, value=3)

# --- 6. 計算・描画 ---
if L_INFO is not None:
    # 厚み同期
    L_T = L_INFO["厚み(mm)"]
    T_L = f_df[f_df["表示名"] == f_long_display]["厚み(mm)"].iloc[0] if f_long_display != "仕上げ無し" else 0.0
    T_S = f_df[f_df["表示名"] == f_short_display]["厚み(mm)"].iloc[0] if f_short_display != "仕上げ無し" else 0.0
    ADJ_W, ADJ_D, S_H = W - (T_S * 2), D - (T_L * 2), H - L_T

    sim_configs = [{"mode": "3x6", "w": 1820, "h": 910, "p": L_INFO["3x6単価"]},
                   {"mode": "4x8", "w": 2424, "h": 1212, "p": L_INFO["4x8単価"]}]
    results = []

    for cfg in sim_configs:
        if cfg["p"] <= 0: continue
        vw, vh = cfg["w"] - 10, cfg["h"] - 10
        # 天板・枠・骨材を生成
        parts = split_part_to_fit("天板", ADJ_W, ADJ_D, vw, vh)
        parts += split_part_to_fit("前枠", ADJ_W, S_H, vw, vh)
        parts += split_part_to_fit("後枠", ADJ_W, S_H, vw, vh)
        for i in range(7):
            parts += split_part_to_fit(f"骨材{i+1}", ADJ_D - (L_T * 2), S_H, vw, vh)
        
        sheets = pack_sheets_strict_v2(parts, vw, vh, KERF)
        results.append({"mode": cfg["mode"], "sheets": sheets, "cost": len(sheets) * cfg["p"], "dim": cfg})

    best = min(results, key=lambda x: x["cost"]) if size_mode.startswith("自動") else next(r for r in results if r["mode"] in size_mode)

    st.success(f"💡 光守さんの判断：{best['mode']}板を選択。合計費用 {best['cost']:,}円")

    for s in best["sheets"]:
        fig, ax = plt.subplots(figsize=(15, 8))
        ax.set_xlim(0, best["dim"]["w"]); ax.set_ylim(0, best["dim"]["h"]); ax.set_aspect('equal')
        ax.add_patch(patches.Rectangle((0,0), best["dim"]["w"], best["dim"]["h"], fc='#fdf5e6', ec='#8b4513', lw=2))
        ax.set_title(f"【{L_INFO['材料名']} {L_T}mm】 {best['mode']} ID:{s['id']}", fontsize=18, fontweight='bold')
        for r in s['rows']:
            for p in r['parts']:
                ax.add_patch(patches.Rectangle((p['x'],p['y']), p['w'], p['h'], lw=1.5, ec='black', fc='#deb887', alpha=0.9))
                ax.text(p['x']+p['w']/2, p['y']+p['h']/2, f"{p['n']}\n{int(p['w'])}x{int(p['h'])}", ha='center', va='center', fontweight='bold', fontsize=9)
        st.pyplot(fig)

    st.divider()
    st.header("📋 積算見積明細")
    st.markdown(f"**下地材: {L_INFO['材料名']} ({L_T}mm / {best['mode']}) ＝ {len(best['sheets'])}枚 × {best['dim']['p']:,}円 ＝ {int(best['cost']):,} 円**")
