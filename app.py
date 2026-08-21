from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculator import investment_summary, milestone_months, monthly_series, months_to_target

st.set_page_config(page_title="積立未来シミュレーター", page_icon="🌱", layout="centered")

ASSETS = Path(__file__).parent / "assets"
RATES = [3.0, 4.0, 5.0, 6.0, 7.0, 10.0]

st.markdown(
    """
<style>
:root { --navy:#17324d; --blue:#275b88; --mint:#bfe5d4; --ivory:#fbf8ef; --gold:#e6bd58; }
.stApp { background:var(--ivory); color:var(--navy); }
.block-container { max-width:900px; padding-top:2rem; padding-bottom:3rem; }
h1,h2,h3 { color:var(--navy); letter-spacing:.01em; }
.hero-sub { color:#526575; font-size:1.05rem; margin-top:-.5rem; }
.result-box { background:linear-gradient(135deg,#fff 0%,#f1faf6 100%); border:1px solid #d9e8e1; border-radius:22px; padding:1.5rem; box-shadow:0 8px 28px rgba(23,50,77,.08); }
.result-label { color:#526575; font-weight:700; text-align:center; }
.result-number { color:var(--blue); font-size:clamp(2.4rem,9vw,4.4rem); line-height:1.15; font-weight:800; text-align:center; white-space:nowrap; }
.metric-card,.tree-card,.rate-card { background:#fff; border:1px solid #e5e8e4; border-radius:16px; padding:1rem; box-shadow:0 4px 16px rgba(23,50,77,.055); height:100%; text-align:center; }
.metric-card span,.tree-card span { color:#657585; font-size:.88rem; }
.metric-card strong,.tree-card strong { display:block; color:var(--navy); font-size:1.25rem; margin-top:.25rem; }
.rate-card { padding:.75rem .35rem; margin-bottom:.5rem; }
.rate-card.selected { border:2px solid var(--gold); background:#fffaf0; }
.rate-card strong { display:block; color:var(--blue); }
.note { color:#697887; font-size:.82rem; line-height:1.7; }
div.stButton > button { width:100%; border-radius:14px; min-height:3.2rem; font-weight:700; background:var(--blue); color:white; border:0; }
div.stButton > button:hover { background:#1d496f; color:white; border:0; }
@media(max-width:640px){ .block-container{padding:1.2rem 1rem 2rem} h1{font-size:1.85rem} .result-box{padding:1.1rem .5rem} }
</style>
""",
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    return f"{value:,.0f}万円"


def duration(months: int) -> str:
    years, remainder = divmod(months, 12)
    return f"{years}年{remainder}か月" if remainder else f"{years}年"


def result_image(total: float) -> Path:
    if total >= 2000:
        return ASSETS / "boy_mature_tree.png"
    if total >= 1000:
        return ASSETS / "boy_young_tree.png"
    if total >= 500:
        return ASSETS / "boy_small_tree.png"
    return ASSETS / "boy_sprout.png"


def rate_input(prefix: str) -> float:
    choices = ["3%", "4%", "5%", "6%", "7%", "10%", "自由入力"]
    selected = st.selectbox("想定利回り", choices, index=2, key=f"{prefix}_rate_kind")
    if selected == "自由入力":
        return float(st.number_input("利回り（%）", 0.0, 50.0, 5.5, 0.1, key=f"{prefix}_custom_rate"))
    return float(selected.rstrip("%"))


def input_screen() -> None:
    head, art = st.columns([3, 1], vertical_alignment="center")
    with head:
        st.title("積立未来シミュレーター")
        st.markdown("### 毎月いくらで、未来はいくら？")
        st.markdown('<p class="hero-sub">毎月の積み立てが、未来にどう育つか見てみましょう。</p>', unsafe_allow_html=True)
    with art:
        st.image(ASSETS / "boy_sprout.png", use_container_width=True)

    mode_label = st.segmented_control(
        "シミュレーションモード", ["将来いくらになる？", "目標達成まで何年？"],
        default=st.session_state.get("mode_label", "将来いくらになる？"), key="mode_label"
    )
    mode = "future" if mode_label == "将来いくらになる？" else "target"
    with st.form(f"inputs_{mode}"):
        monthly = float(st.number_input("毎月の積立額（万円）", 1, 100, 3, 1, key=f"{mode}_monthly"))
        if mode == "future":
            years = int(st.number_input("積立期間（年）", 1, 60, 20, 1, key="future_years"))
            target = None
        else:
            target_choice = st.selectbox("目標金額", ["500万円", "1,000万円", "2,000万円", "3,000万円", "5,000万円", "1億円", "自由入力"], index=1)
            values = {"500万円":500, "1,000万円":1000, "2,000万円":2000, "3,000万円":3000, "5,000万円":5000, "1億円":10000}
            target = float(st.number_input("目標金額（万円）", 1, 1_000_000, 1000, 1)) if target_choice == "自由入力" else float(values[target_choice])
            years = None
        rate = rate_input(mode)
        submitted = st.form_submit_button("未来を見てみる")
    if submitted:
        st.session_state.result = {"mode": mode, "monthly": monthly, "years": years, "target": target, "rate": rate}
        st.session_state.screen = "result"
        st.rerun()


def chart(data: list[dict[str, float]]) -> None:
    df = pd.DataFrame(data)
    df["経過期間"] = df["month"].map(lambda m: f"{m // 12}年{m % 12}か月")
    common = "%{customdata[0]}<br>%{fullData.name}：%{y:,.0f}万円<extra></extra>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.month / 12, y=df.principal, customdata=df[["経過期間"]], name="積立元本", stackgroup="asset", line=dict(color="#6bbfa1"), hovertemplate=common))
    fig.add_trace(go.Scatter(x=df.month / 12, y=df.profit, customdata=df[["経過期間"]], name="想定運用益", stackgroup="asset", line=dict(color="#e6bd58"), hovertemplate=common))
    fig.update_layout(hovermode="x unified", xaxis_title="経過年数", yaxis_title="資産額（万円）", template="plotly_white", margin=dict(l=10,r=10,t=20,b=10), height=410, legend=dict(orientation="h", y=1.08), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,.7)")
    fig.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dot")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False, "responsive":True})


def result_screen() -> None:
    p = st.session_state.result
    mode, monthly, rate = p["mode"], p["monthly"], p["rate"]
    months = p["years"] * 12 if mode == "future" else months_to_target(monthly, rate, p["target"])
    summary = investment_summary(monthly, rate, months)
    label = f"{p['years']}年後の想定資産額" if mode == "future" else f"{money(p['target'])}の目標達成まで"
    headline = money(summary["total"]) if mode == "future" else duration(months)
    left, right = st.columns([3, 1], vertical_alignment="center")
    with left:
        st.markdown(f'<div class="result-box"><div class="result-label">{label}</div><div class="result-number">{headline}</div></div>', unsafe_allow_html=True)
    with right:
        st.image(result_image(summary["total"]), use_container_width=True)
    if rate >= 10:
        st.markdown('<p class="note">高い想定利回りが長期間続くとは限りません。比較用の試算としてご覧ください。</p>', unsafe_allow_html=True)

    names = ["積立元本", "想定運用益", "想定資産額" if mode == "future" else "目標到達時の想定資産額"]
    vals = [summary["principal"], summary["profit"], summary["total"]]
    cols = st.columns(3)
    for col, name, value in zip(cols, names, vals):
        col.markdown(f'<div class="metric-card"><span>{name}</span><strong>{money(value)}</strong></div>', unsafe_allow_html=True)

    st.markdown("## 資産の育ち方")
    chart(monthly_series(monthly, rate, months))

    st.markdown("## 未来の木")
    st.write("同じペースで積み立てを続けた場合の節目を見てみましょう。")
    milestones = milestone_months(monthly, rate)
    tree_data = [(500,"icon_sprout.png"),(1000,"icon_young_tree.png"),(2000,"icon_mature_tree.png")]
    for col, (target, icon) in zip(st.columns(3), tree_data):
        with col:
            st.image(ASSETS / icon, width=70)
            st.markdown(f'<div class="tree-card"><span>{money(target)} 到達まで</span><strong>{duration(milestones[target])}</strong></div>', unsafe_allow_html=True)

    st.markdown("## 想定利回りを変えると？")
    compare_rates = RATES + ([rate] if rate not in RATES else [])
    cols = st.columns(3)
    for i, item_rate in enumerate(compare_rates):
        if mode == "future":
            display = money(investment_summary(monthly, item_rate, months)["total"])
        else:
            display = duration(months_to_target(monthly, item_rate, p["target"]))
        selected = " selected" if item_rate == rate else ""
        title = f"現在の設定 {item_rate:g}%" if item_rate not in RATES else f"{item_rate:g}%"
        cols[i % 3].markdown(f'<div class="rate-card{selected}">{title}<strong>{display}</strong></div>', unsafe_allow_html=True)

    st.markdown('<div class="note">※想定利回りをもとにした簡易試算です。<br>※手数料・税金などは簡略化しています。<br>※実際の運用成果を保証するものではありません。<br>※特定の商品への投資を勧めるものではありません。</div>', unsafe_allow_html=True)
    if st.button("条件を変えてもう一度"):
        st.session_state.screen = "input"
        st.rerun()


if "screen" not in st.session_state:
    st.session_state.screen = "input"
input_screen() if st.session_state.screen == "input" else result_screen()

