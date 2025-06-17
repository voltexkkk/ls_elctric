import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

# 페이지 설정
st.set_page_config(
    page_title="시스템 모니터링 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 설정
st.sidebar.title("🔧 대시보드 설정")
refresh_rate = st.sidebar.selectbox("새로고침 주기", [30, 60, 120, 300], index=1)
st.sidebar.markdown(f"**마지막 업데이트:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 자동 새로고침
if st.sidebar.button("수동 새로고침"):
    st.rerun()

# 메인 제목
st.title("📊 시스템 모니터링 대시보드")
st.markdown("---")

# 샘플 데이터 생성 함수
@st.cache_data(ttl=60)
def generate_sample_data():
    """샘플 모니터링 데이터 생성"""
    # 시간 데이터
    now = datetime.now()
    times = [now - timedelta(minutes=x) for x in range(60, 0, -1)]
    
    # 시스템 메트릭
    cpu_usage = np.random.normal(45, 15, 60).clip(0, 100)
    memory_usage = np.random.normal(65, 10, 60).clip(0, 100)
    disk_io = np.random.exponential(50, 60)
    network_traffic = np.random.normal(1000, 300, 60).clip(0, None)
    
    # 애플리케이션 메트릭
    response_time = np.random.exponential(200, 60)
    error_rate = np.random.poisson(2, 60)
    active_users = np.random.normal(150, 30, 60).clip(0, None).astype(int)
    
    # 비즈니스 메트릭
    transactions = np.random.poisson(20, 60)
    revenue = transactions * np.random.normal(25, 5, 60)
    
    return pd.DataFrame({
        'timestamp': times,
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'disk_io': disk_io,
        'network_traffic': network_traffic,
        'response_time': response_time,
        'error_rate': error_rate,
        'active_users': active_users,
        'transactions': transactions,
        'revenue': revenue
    })

# 데이터 로드
df = generate_sample_data()

# KPI 카드
col1, col2, col3, col4 = st.columns(4)

with col1:
    current_cpu = df['cpu_usage'].iloc[-1]
    st.metric(
        label="CPU 사용률",
        value=f"{current_cpu:.1f}%",
        delta=f"{current_cpu - df['cpu_usage'].iloc[-5]:.1f}%"
    )

with col2:
    current_memory = df['memory_usage'].iloc[-1]
    st.metric(
        label="메모리 사용률",
        value=f"{current_memory:.1f}%",
        delta=f"{current_memory - df['memory_usage'].iloc[-5]:.1f}%"
    )

with col3:
    current_users = int(df['active_users'].iloc[-1])
    st.metric(
        label="활성 사용자",
        value=f"{current_users:,}명",
        delta=f"{current_users - int(df['active_users'].iloc[-5]):,}명"
    )

with col4:
    current_response = df['response_time'].iloc[-1]
    st.metric(
        label="응답시간",
        value=f"{current_response:.0f}ms",
        delta=f"{current_response - df['response_time'].iloc[-5]:.0f}ms",
        delta_color="inverse"
    )

st.markdown("---")

# 시스템 성능 차트
st.subheader("🖥️ 시스템 성능 모니터링")

tab1, tab2, tab3 = st.tabs(["CPU & 메모리", "네트워크 & 디스크", "응답시간 & 에러"])

with tab1:
    fig_system = make_subplots(
        rows=2, cols=1,
        subplot_titles=('CPU 사용률 (%)', '메모리 사용률 (%)'),
        vertical_spacing=0.1
    )
    
    fig_system.add_trace(
        go.Scatter(x=df['timestamp'], y=df['cpu_usage'], 
                  name='CPU', line=dict(color='#FF6B6B')),
        row=1, col=1
    )
    
    fig_system.add_trace(
        go.Scatter(x=df['timestamp'], y=df['memory_usage'], 
                  name='Memory', line=dict(color='#4ECDC4')),
        row=2, col=1
    )
    
    fig_system.update_layout(height=500, showlegend=False)
    fig_system.update_xaxes(title_text="시간")
    fig_system.update_yaxes(title_text="사용률 (%)", row=1, col=1)
    fig_system.update_yaxes(title_text="사용률 (%)", row=2, col=1)
    
    st.plotly_chart(fig_system, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        fig_network = px.line(df, x='timestamp', y='network_traffic',
                             title='네트워크 트래픽 (MB/s)')
        fig_network.update_traces(line_color='#45B7D1')
        st.plotly_chart(fig_network, use_container_width=True)
    
    with col2:
        fig_disk = px.line(df, x='timestamp', y='disk_io',
                          title='디스크 I/O (MB/s)')
        fig_disk.update_traces(line_color='#96CEB4')
        st.plotly_chart(fig_disk, use_container_width=True)

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        fig_response = px.line(df, x='timestamp', y='response_time',
                              title='평균 응답시간 (ms)')
        fig_response.update_traces(line_color='#FFEAA7')
        fig_response.add_hline(y=500, line_dash="dash", line_color="red",
                              annotation_text="임계값 (500ms)")
        st.plotly_chart(fig_response, use_container_width=True)
    
    with col2:
        fig_errors = px.bar(df.tail(20), x='timestamp', y='error_rate',
                           title='에러 발생률 (최근 20분)')
        fig_errors.update_traces(marker_color='#FD79A8')
        st.plotly_chart(fig_errors, use_container_width=True)

st.markdown("---")

# 사용자 활동 및 비즈니스 메트릭
st.subheader("👥 사용자 활동 & 비즈니스 메트릭")

col1, col2 = st.columns(2)

with col1:
    fig_users = px.area(df, x='timestamp', y='active_users',
                       title='활성 사용자 수')
    fig_users.update_traces(fill='tonexty', fillcolor='rgba(74, 144, 226, 0.3)')
    st.plotly_chart(fig_users, use_container_width=True)
    
    # 트랜잭션 히트맵
    hourly_data = pd.DataFrame({
        'hour': np.random.randint(0, 24, 100),
        'day': np.random.randint(0, 7, 100),
        'transactions': np.random.poisson(15, 100)
    })
    pivot_data = hourly_data.pivot_table(values='transactions', 
                                       index='hour', columns='day', 
                                       aggfunc='mean', fill_value=0)
    
    fig_heatmap = px.imshow(pivot_data, 
                           title='시간대별 트랜잭션 히트맵',
                           labels=dict(x="요일", y="시간", color="트랜잭션"))
    st.plotly_chart(fig_heatmap, use_container_width=True)

with col2:
    # 수익 및 트랜잭션
    fig_revenue = make_subplots(
        rows=2, cols=1,
        subplot_titles=('시간당 수익 ($)', '트랜잭션 수'),
        vertical_spacing=0.15
    )
    
    fig_revenue.add_trace(
        go.Scatter(x=df['timestamp'], y=df['revenue'], 
                  name='Revenue', line=dict(color='#00B894')),
        row=1, col=1
    )
    
    fig_revenue.add_trace(
        go.Bar(x=df['timestamp'], y=df['transactions'], 
               name='Transactions', marker_color='#FDCB6E'),
        row=2, col=1
    )
    
    fig_revenue.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_revenue, use_container_width=True)
    
    # 상태 표시기
    st.markdown("### 🚦 시스템 상태")
    
    # 상태 계산
    cpu_status = "🟢 정상" if current_cpu < 70 else "🟡 주의" if current_cpu < 85 else "🔴 위험"
    memory_status = "🟢 정상" if current_memory < 80 else "🟡 주의" if current_memory < 90 else "🔴 위험"
    response_status = "🟢 정상" if current_response < 300 else "🟡 주의" if current_response < 500 else "🔴 위험"
    
    status_data = {
        "컴포넌트": ["CPU", "메모리", "응답시간", "네트워크"],
        "상태": [cpu_status, memory_status, response_status, "🟢 정상"],
        "현재값": [f"{current_cpu:.1f}%", f"{current_memory:.1f}%", 
                 f"{current_response:.0f}ms", "정상"],
        "임계값": ["85%", "90%", "500ms", "N/A"]
    }
    
    st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)

st.markdown("---")

# 알림 및 로그
st.subheader("🔔 최근 알림")

# 샘플 알림 데이터
alerts = [
    {"시간": "2024-01-15 14:30", "레벨": "⚠️ 경고", "메시지": "CPU 사용률이 80%를 초과했습니다"},
    {"시간": "2024-01-15 14:25", "레벨": "ℹ️ 정보", "메시지": "새로운 사용자 100명이 접속했습니다"},
    {"시간": "2024-01-15 14:20", "레벨": "🚨 오류", "메시지": "데이터베이스 연결 오류가 발생했습니다"},
    {"시간": "2024-01-15 14:15", "레벨": "✅ 성공", "메시지": "시스템 백업이 완료되었습니다"},
]

alert_df = pd.DataFrame(alerts)
st.dataframe(alert_df, use_container_width=True, hide_index=True)

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>📊 Real-time Monitoring Dashboard | 
        Last Updated: {} | 
        🔄 Auto-refresh every {} seconds</p>
    </div>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), refresh_rate),
    unsafe_allow_html=True
)

# 자동 새로고침 (개발 환경에서는 주석 처리 권장)
# time.sleep(refresh_rate)
# st.rerun()