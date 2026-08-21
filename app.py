from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from calculator import investment_summary, monthly_series, months_to_target

st.set_page_config(page_title="積立未来シミュレーター", page_icon="🌱", layout="centered")

RATES = [3.0, 4.0, 5.0, 6.0, 7.0, 10.0]

st.markdown(
    """
<style>
:root { --ink:#18362d; --green:#176b4b; --green-dark:#10553b; --paper:#fbfaf5; }
.stApp { background:var(--paper); color:var(--ink); }
.block-container { max-width:720px; padding-top:1.25rem; padding-bottom:2rem; }
h1,h2,h3 { color:var(--ink); }
.app-title { color:var(--ink); font-size:clamp(1.65rem,7vw,2.15rem); font-weight:800;
  line-height:1.15; margin:0; text-align:center; }
.app-subtitle { color:#64746e; font-size:.95rem; margin:.25rem 0 .85rem; text-align:center; }
.result-label { color:#536a61; font-size:1.05rem; font-weight:700; text-align:center; margin-top:.35rem; }
.result-number { color:var(--green); font-size:clamp(2.8rem,13vw,4.7rem); line-height:1.12;
  font-weight:900; letter-spacing:-.04em; text-align:center; white-space:nowrap; margin:.25rem 0 .65rem; }
.section-title { color:var(--ink); font-size:1.18rem; font-weight:800; margin:1.25rem 0 .45rem; }
.breakdown { width:100%; border-collapse:collapse; }
.breakdown td { padding:.35rem .1rem; border-bottom:1px solid #e3e7e3; }
.breakdown td:last-child { font-weight:750; text-align:right; white-space:nowrap; }
.comment { color:#314a41; line-height:1.7; margin:.1rem 0 .75rem; }
.note { color:#68776f; font-size:.79rem; line-height:1.55; margin:.25rem 0; }
.current-rate { color:#536a61; font-size:.82rem; margin-top:-.2rem; }
div[data-testid="stSegmentedControl"] button, div[role="radiogroup"] button {
  min-height:54px; font-size:clamp(.9rem,4vw,1.05rem); font-weight:750; border-radius:12px;
}
div[data-testid="stSegmentedControl"] > div, div[role="radiogroup"] { width:100%; }
div[data-testid="stSegmentedControl"] button { flex:1; }
div.stButton > button, div.stFormSubmitButton > button {
  width:100%; border-radius:14px; font-weight:750;
}
div.stButton > button[kind="primary"], div.stFormSubmitButton > button {
  background:var(--green); color:white; border-color:var(--green); box-shadow:0 4px 12px rgba(23,107,75,.2);
}
div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button:hover {
  background:var(--green-dark); color:white; border-color:var(--green-dark);
}
div.stFormSubmitButton > button { min-height:62px; font-size:1.2rem; margin-top:.35rem; }
.st-key-restart button { min-height:60px; font-size:1.08rem; }
div[data-testid="stPlotlyChart"] { margin-top:-.45rem; }
@media(max-width:640px){
  .block-container{padding: .75rem .85rem 1.5rem}
  div[data-testid="stVerticalBlock"]{gap:.65rem}
  .result-number{margin-bottom:.35rem}
  .section-title{margin-top:1rem}
  div[data-testid="stPlotlyChart"]{margin-left:-.5rem;margin-right:-.5rem}
}
</style>
""",
    unsafe_allow_html=True,
)


def money(value: float) -> str:
    return f"{value:,.0f}万円"


def duration(months: int) -> str:
    years, remainder = divmod(months, 12)
    return f"{years}年{remainder}か月" if remainder else f"{years}年"


def rate_input(prefix: str) -> float:
    choices = ["3%", "4%", "5%", "6%", "7%", "10%", "自由入力"]
    selected = st.selectbox("想定利回り", choices, index=2, key=f"{prefix}_rate_kind")
    if selected == "自由入力":
        return float(st.number_input("利回り（%）", 0.0, 50.0, 5.5, 0.1, key=f"{prefix}_custom_rate"))
    return float(selected.rstrip("%"))


def input_screen() -> None:
    st.markdown(
        '<div class="app-title">積立未来シミュレーター</div>'
        '<div class="app-subtitle">毎月いくらで、未来はいくら？</div>',
        unsafe_allow_html=True,
    )
    mode_label = st.segmented_control(
        "モードを選択",
        ["将来いくら？", "目標達成まで何年？"],
        default=st.session_state.get("mode_label", "将来いくら？"),
        key="mode_label",
        label_visibility="collapsed",
    )
    mode = "future" if mode_label == "将来いくら？" else "target"
    with st.form(f"inputs_{mode}"):
        monthly = float(st.number_input("毎月の積立額（万円）", 1, 100, 3, 1, key=f"{mode}_monthly"))
        if mode == "future":
            years = int(st.number_input("積立期間（年）", 1, 60, 20, 1, key="future_years"))
            target = None
        else:
            choices = ["500万円", "1,000万円", "2,000万円", "3,000万円", "5,000万円", "1億円", "自由入力"]
            target_choice = st.selectbox("目標金額", choices, index=1, key="target_choice")
            values = {"500万円": 500, "1,000万円": 1000, "2,000万円": 2000,
                      "3,000万円": 3000, "5,000万円": 5000, "1億円": 10000}
            target = (float(st.number_input("目標金額（万円）", 1, 1_000_000, 1000, 1, key="custom_target"))
                      if target_choice == "自由入力" else float(values[target_choice]))
            years = None
        rate = rate_input(mode)
        submitted = st.form_submit_button("🌱 未来を見てみる")
    if submitted:
        st.session_state.result = {"mode": mode, "monthly": monthly, "years": years, "target": target, "rate": rate}
        st.session_state.screen = "result"
        st.session_state.scroll_to_result = True
        st.rerun()


def chart(data: list[dict[str, float]]) -> None:
    df = pd.DataFrame(data)
    df["経過期間"] = df["month"].map(lambda m: f"{m // 12}年{m % 12}か月")
    hover = "%{customdata[0]}<br>%{fullData.name}：%{y:,.0f}万円<extra></extra>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.month / 12, y=df.principal, customdata=df[["経過期間"]],
                             name="積立元本", stackgroup="asset", line=dict(color="#63ad8d"), hovertemplate=hover))
    fig.add_trace(go.Scatter(x=df.month / 12, y=df.profit, customdata=df[["経過期間"]],
                             name="想定運用益", stackgroup="asset", line=dict(color="#deb956"), hovertemplate=hover))
    fig.add_trace(go.Scatter(x=df.month / 12, y=df.total, customdata=df[["経過期間"]], name="合計",
                             line=dict(width=0), opacity=0, showlegend=False, hovertemplate=hover))
    fig.update_layout(
        hovermode="x unified", dragmode=False, xaxis_title="経過年数", yaxis_title="資産額（万円）",
        template="plotly_white", margin=dict(l=4, r=4, t=30, b=4), height=300,
        legend=dict(orientation="h", y=1.12), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,.65)",
    )
    fig.update_xaxes(fixedrange=True, showspikes=False)
    fig.update_yaxes(fixedrange=True)
    st.plotly_chart(
        fig, use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "responsive": True},
    )


def set_rate(rate: float) -> None:
    st.session_state.result["rate"] = rate


def result_comment(mode: str, months: int, summary: dict[str, float], target: float | None) -> str:
    if mode == "target":
        first = f"{money(target or 0)}までは約{duration(months)}。"
    else:
        first = f"積立元本{money(summary['principal'])}に対し、想定運用益は{money(summary['profit'])}です。"
    return first + "積立期間が長くなるほど、後半は運用による増加分も少しずつ大きくなる試算です。"


def result_screen() -> None:
    if st.session_state.pop("scroll_to_result", False):
        components.html(
            "<script>window.parent.scrollTo({top:0,left:0,behavior:'instant'});</script>", height=0,
        )
    if st.button("← 条件を変える", key="back_top"):
        st.session_state.screen = "input"
        st.rerun()

    p = st.session_state.result
    mode, monthly, rate = p["mode"], p["monthly"], p["rate"]
    months = p["years"] * 12 if mode == "future" else months_to_target(monthly, rate, p["target"])
    summary = investment_summary(monthly, rate, months)
    label = f"{p['years']}年後の想定資産額" if mode == "future" else f"{money(p['target'])}の目標達成まで"
    headline = money(summary["total"]) if mode == "future" else duration(months)
    st.markdown(
        f'<div class="result-label">{html.escape(label)}</div>'
        f'<div class="result-number">{html.escape(headline)}</div>', unsafe_allow_html=True,
    )
    if rate >= 10:
        st.markdown('<p class="note">高い想定利回りが長期間続くとは限りません。比較用の試算としてご覧ください。</p>', unsafe_allow_html=True)

    names = ["積立元本", "想定運用益", "想定資産額" if mode == "future" else "目標達成時の想定資産額"]
    with st.expander("内訳を見る", expanded=False):
        rows = "".join(f"<tr><td>{name}</td><td>{money(value)}</td></tr>" for name, value in zip(names, summary.values()))
        st.markdown(f'<table class="breakdown">{rows}</table>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">資産の育ち方</div>', unsafe_allow_html=True)
    chart(monthly_series(monthly, rate, months))

    st.markdown('<div class="section-title">利回りを変えて試す</div>', unsafe_allow_html=True)
    cols = st.columns(len(RATES), gap="small")
    for col, item_rate in zip(cols, RATES):
        col.button(f"{item_rate:g}%", key=f"rate_{item_rate:g}", type="primary" if rate == item_rate else "secondary",
                   on_click=set_rate, args=(item_rate,), use_container_width=True)
    if rate not in RATES:
        st.markdown(f'<div class="current-rate">現在の設定：{rate:g}%</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">この積み立てを続けると</div>', unsafe_allow_html=True)
    comment = result_comment(mode, months, summary, p["target"])
    st.markdown(f'<p class="comment">{html.escape(comment)}</p>', unsafe_allow_html=True)
    st.markdown('<div class="note">※想定利回りをもとにした簡易試算です。手数料・税金などは簡略化しています。<br>※実際の運用成果を保証するものではなく、特定の商品への投資を勧めるものではありません。</div>', unsafe_allow_html=True)

    st.markdown('<div class="restart">', unsafe_allow_html=True)
    if st.button("条件を変えてもう一度", type="primary", key="restart", use_container_width=True):
        st.session_state.screen = "input"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


if "screen" not in st.session_state:
    st.session_state.screen = "input"
input_screen() if st.session_state.screen == "input" else result_screen()
