import streamlit as st

st.set_page_config(
    page_title="Drug Simulation Dashboard",
    layout="wide"
)

st.title("💊 약물 농도 시뮬레이션 대시보드")
st.markdown("""
이 애플리케이션은 **경구** 및 **패치** 투여 방식에 따라  
약물 농도 곡선을 시뮬레이션하고 시각화합니다.

---

### 📂 페이지 안내
- [📈 경구 투여 시뮬레이션](/oral)
- [📉 패치 투여 시뮬레이션](/patch) *(개발 중)*

---

### 📝 기능 설명
- Google Sheet에서 약물 데이터 자동 불러오기
- Tmax, F, Vd 등 PK 파라미터 기반 시뮬레이션
- Onset 및 약효 소실 시점 표시
""")
