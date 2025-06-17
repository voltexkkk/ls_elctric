import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.express as px
import plotly.graph_objects as go
import warnings
import math

warnings.filterwarnings("ignore")

# ─── (1) 페이지 설정 —— 이 한 줄만 st.set_page_config 로! ────────────
st.set_page_config("SHAP 대시보드", layout="wide")

# ─── (2) 글로벌 CSS 삽입 —— 여기서만 st.markdown! ────────────────────
st.markdown(
    """
<style>
    .header-style { background: white; font-size: 1.3rem; font-weight: bold; color: #000000; padding: 2rem; border-radius: 12px; text-align: center; margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-left: 5px solid #3498db; border-right: 5px solid #3498db; }

.header-style1 {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  /* height 제거해서 내용에 맞게 늘어나도록 */
  /* height: 120px; */

  /* custom-card 과 동일한 padding */
  padding: 16px;
  margin-bottom: 2rem;
  text-align: center;

  background-color: #ffffff;
  color: #000000;

  border: 5px solid #3498db;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  min-height: 100px; /* 최소 높이 설정 */
}

/* background 만 custom-card 에 특화 */


/* background 만 header-style1 에 특화 */
.header-style1 {
  background-color: white;
  color: #000;
  border: 5px solid #3498db;
}

.header-style1 .title {
  font-size: 1.0rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.header-style1 .value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}


/* 카드 컨테이너 기본 스타일 */
.custom-card {
  background: linear-gradient(135deg, #6A82FB 0%, #FC5C7D 100%);
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  text-align: center;
  color: white;
}
/* 타이틀 */
.custom-card .title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 4px;
}
/* 숫자값 */
.custom-card .value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}
</style>
""",
    unsafe_allow_html=True,
)


# ─── SHAP 관련 헬퍼 함수 ─────────────────────────────────────
def generate_dummy_shap_values():
    feature_names = st.session_state.feat_data.columns.drop(
        ["id", "측정일시", "target"]
    ).tolist()
    np.random.seed(len(st.session_state.shap_history))
    vals = np.random.randn(len(feature_names))
    return dict(zip(feature_names, vals))


def create_shap_chart():
    if not st.session_state.shap_history:
        return None

    selected_features = [
        "전력사용량(kWh)",
        "지상무효전력량(kVarh)",
        "진상무효전력량(kVarh)",
        "탄소배출량(tCO2)",
        "진상역률_이진",
        "지상역률_이진",
    ]

    mean_abs = {
        f: np.mean([abs(h[f]) for h in st.session_state.shap_history])
        for f in selected_features
        if f in st.session_state.shap_history[0]
    }

    feats_sorted = sorted(mean_abs.items(), key=lambda x: x[1], reverse=True)
    top_feats = [k for k, _ in feats_sorted]
    top_vals = [v for _, v in feats_sorted]

    fig = go.Figure(
        go.Bar(
            x=top_vals[::-1],
            y=top_feats[::-1],
            orientation="h",
            marker_color="#3498db",
            hovertemplate="<b>%{y}</b><br>평균 |SHAP|: %{x:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="누적 절대 평균 SHAP",
        xaxis_title="평균 |SHAP|",
        yaxis_title="특성",
        height=400,
        template="plotly_white",
        margin=dict(l=120, r=20, t=40, b=40),
    )
    return fig


# ─── 세션 상태 초기화 ────────────────────────────────────────
def init_state():
    if "data" not in st.session_state:
        st.session_state.data = pd.read_csv(
            "./models/final_lstm_target.csv", parse_dates=["측정일시"]
        )
    if "feat_data" not in st.session_state:
        st.session_state.feat_data = pd.read_csv(
            "./models/target_pred_feature_lstm.csv", parse_dates=["측정일시"]
        )
    if "start_idx" not in st.session_state:
        df = st.session_state.data
        matches = df.index[df["id"] == 32111].tolist()
        st.session_state.start_idx = matches[0] if matches else 0
        st.session_state.idx = st.session_state.start_idx
    for key in ["time_list", "cost_list", "shap_history"]:
        st.session_state.setdefault(key, [])
    st.session_state.setdefault("running", False)
    st.session_state.setdefault("page", 0)


init_state()

# ─── 사이드바 제어판 ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 제어판")
    if st.button("시작"):
        st.session_state.running = True
    if st.button("정지"):
        st.session_state.running = False
    if st.button("리셋"):
        st.session_state.idx = st.session_state.start_idx
        st.session_state.time_list.clear()
        st.session_state.cost_list.clear()
        st.session_state.shap_history.clear()
        st.session_state.running = False
        st.session_state.page = 0
    st.markdown("---")
    status = "● 실행 중" if st.session_state.running else "● 정지됨"
    color = "#27ae60" if st.session_state.running else "#e74c3c"
    st.markdown(
        f'<span style="color:{color}; font-weight:bold;">{status}</span>',
        unsafe_allow_html=True,
    )


# ─── 테이블 출력 함수 ───────────────────────────────────────
def draw_table():
    # 1) 데이터 준비
    df_slice = st.session_state.feat_data.iloc[
        st.session_state.start_idx : st.session_state.idx
    ].reset_index(drop=True)
    total_rows = len(df_slice)
    page_size = 10
    total_pages = max(math.ceil(total_rows / page_size), 1)

    # 2) 현재 페이지
    page = st.session_state.get("page", 0)

    # 3) 콜백
    def go_prev():
        st.session_state.page = max(0, st.session_state.page - 1)

    def go_next():
        st.session_state.page = min(total_pages - 1, st.session_state.page + 1)

    # 4) 네비게이션 버튼
    nav_l, nav_mid, nav_r = st.columns([1, 2, 1])
    with nav_l:
        st.button("◀ 이전", disabled=(page <= 0), on_click=go_prev, key="prev_btn")
    with nav_mid:
        # 클릭 시 session_state.page 가 바로 업데이트됨
        page = st.session_state.page
        st.write(f"페이지 {page + 1} / {total_pages}")
    with nav_r:
        st.button(
            "다음 ▶",
            disabled=(page >= total_pages - 1),
            on_click=go_next,
            key="next_btn",
        )

    # 5) 클램프(안정화)
    st.session_state.page = max(0, min(st.session_state.page, total_pages - 1))

    # 6) 테이블 출력
    page = st.session_state.page
    start, end = page * page_size, (page + 1) * page_size
    show_cols = [
        "측정일시",
        "전력사용량(kWh)",
        "지상무효전력량(kVarh)",
        "진상무효전력량(kVarh)",
        "탄소배출량(tCO2)",
        "진상역률_이진",
        "지상역률_이진",
    ]
    df_display = df_slice[show_cols]
    st.dataframe(df_display.iloc[start:end], use_container_width=True)


# ─── 메인 구동 루프 ─────────────────────────────────────────
def show_main():
    st.title("실시간 전기요금 모니터링")

    # ─ 위쪽: 전기요금 + 누적 SHAP ─
    start, idx = st.session_state.start_idx, st.session_state.idx
    df_slice = st.session_state.feat_data.iloc[start:idx]
    total_cost = sum(st.session_state.cost_list)  # 누적 전기요금
    total_kwh = df_slice["전력사용량(kWh)"].sum()  # 누적 전력량
    total_kvarh_jisang = df_slice["지상무효전력량(kVarh)"].sum()  # 지상 무효전력량
    total_kvarh_jinsang = df_slice["진상무효전력량(kVarh)"].sum()  # 진상 무효전력량
    total_co2 = df_slice["탄소배출량(tCO2)"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            f"""
        <div class="header-style1">
          <div class="title">누적 전기요금 (원)</div>
          <div class="value">{total_cost:,.0f}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
        <div class="header-style1">
          <div class="title">누적 전력량 (kWh)</div>
          <div class="value">{total_kwh:.2f}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
        <div class="header-style1">
          <div class="title">누적지상무효전력량 (kVarh)</div>
          <div class="value">{total_kvarh_jisang:.2f}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
        <div class="header-style1">
          <div class="title">누적진상무효전력량 (kVarh)</div>
          <div class="value">{total_kvarh_jinsang:.2f}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f"""
        <div class="header-style1">
          <div class="title">누적 탄소배출량 (tCO₂)</div>
          <div class="value">{total_co2:.2f}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns([3, 2])
    with col1:
        df_plot = pd.DataFrame(
            {
                "측정일시": st.session_state.time_list,
                "전기요금(원)": st.session_state.cost_list,
            }
        )
        fig = px.line(
            df_plot,
            x="측정일시",
            y="전기요금(원)",
            title="실시간 전기요금 모니터링",
            markers=True,
        )
        fig.update_layout(xaxis_title="측정일시", yaxis_title="전기요금(원)")
        st.plotly_chart(fig, use_container_width=True, key="line_chart")
    with col2:
        shap_fig = create_shap_chart()
        if shap_fig:
            st.plotly_chart(shap_fig, use_container_width=True, key="accum_chart")
        else:
            st.info("SHAP 데이터 준비 중…")

    # ─── 아래쪽: 왼쪽에 테이블+설명, 오른쪽에 최근 SHAP ────────────
    left_col, right_col = st.columns([3, 2])

    # 왼쪽: 테이블 + 설명 카드
    with left_col:
        # 1) 슬라이스된 데이터
        df_slice = st.session_state.feat_data.iloc[
            st.session_state.start_idx : st.session_state.idx
        ].reset_index(drop=True)
        total_rows = len(df_slice)
        page_size = 10
        total_pages = max(math.ceil(total_rows / page_size), 1)

        # 콜백 함수 정의 (total_pages 는 클로저로 캡처)
        def go_prev():
            st.session_state.page = max(0, st.session_state.page - 1)

        def go_next():
            st.session_state.page = min(total_pages - 1, st.session_state.page + 1)

        # 네비게이션
        nav_l, nav_mid, nav_r = st.columns([1, 2, 1])
        with nav_l:
            st.button(
                "◀ 이전",
                disabled=(st.session_state.page <= 0),
                on_click=go_prev,
                key="prev_page_btn",
            )
        with nav_mid:
            st.write(f"페이지 {st.session_state.page + 1} / {total_pages}")
        with nav_r:
            st.button(
                "다음 ▶",
                disabled=(st.session_state.page >= total_pages - 1),
                on_click=go_next,
                key="next_page_btn",
            )

        # 2) 해당 페이지 데이터만 출력
        start = st.session_state.page * page_size
        end = start + page_size
        show_cols = [
            "측정일시",
            "전력사용량(kWh)",
            "지상무효전력량(kVarh)",
            "진상무효전력량(kVarh)",
            "탄소배출량(tCO2)",
            "진상역률_이진",
            "지상역률_이진",
        ]
        st.dataframe(df_slice[show_cols].iloc[start:end], use_container_width=True)

        # 6) 설명 카드 (테이블 바로 아래)
        exp1, exp2 = st.columns(2)
        with exp1:
            st.markdown(
                """
            <div class="header-style" style="background: #FFFFFF;">
              <div class="title">진상역률_이진</div>
              <div class="value" style="font-size:1rem; font-weight:400;">
                1 = 역률 기준(95%) 이상<br>
                0 = 기준 미만
              </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with exp2:
            st.markdown(
                """
            <div class="header-style" style="background: #FFFFFF;">
              <div class="title">지상역률_이진</div>
              <div class="value" style="font-size:1rem; font-weight:400;">
                1 = 역률 기준(65%) 이상<br>
                0 = 기준 미만
              </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # 오른쪽: 기존 ‘최근 샘플 SHAP 기여도’ 그래프
    with right_col:
        if st.session_state.shap_history:
            last_shap = st.session_state.shap_history[-1]
            show_feats = [
                "전력사용량(kWh)",
                "지상무효전력량(kVarh)",
                "진상무효전력량(kVarh)",
                "탄소배출량(tCO2)",
                "진상역률_이진",
                "지상역률_이진",
            ]
            feats = [f for f in show_feats if f in last_shap]
            vals = [last_shap[f] for f in feats]
            colors = ["#e74c3c" if v > 0 else "#3498db" for v in vals]

            fig = go.Figure(
                go.Bar(
                    x=vals[::-1],
                    y=feats[::-1],
                    orientation="h",
                    marker_color=colors[::-1],
                    hovertemplate="<b>%{y}</b><br>SHAP: %{x:.3f}<extra></extra>",
                )
            )
            fig.update_layout(
                title="최근 샘플 SHAP 기여도",
                xaxis_title="SHAP 값",
                yaxis_title="특성",
                height=400,
                template="plotly_white",
                margin=dict(l=120, r=20, t=40, b=40),
            )
            st.plotly_chart(fig, use_container_width=True, key="latest_chart")
        else:
            st.info("SHAP 데이터가 없습니다.")


if st.session_state.running:
    df = st.session_state.data
    if st.session_state.idx < len(df):
        row = df.iloc[st.session_state.idx]
        st.session_state.time_list.append(row["측정일시"])
        st.session_state.cost_list.append(row["target"])
        st.session_state.idx += 1

        new_shap = generate_dummy_shap_values()
        st.session_state.shap_history.append(new_shap)

        show_main()
        time.sleep(10)
        st.rerun()
    else:
        st.warning("더 이상 불러올 데이터가 없습니다.")
else:
    if st.session_state.time_list:
        show_main()
    else:
        st.info("시작 버튼을 눌러 실시간 모니터링을 시작하세요.")
