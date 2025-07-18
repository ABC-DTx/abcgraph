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
- Google Spreadsheet: https://docs.google.com/spreadsheets/d/1BXE4oJEHYxY-65O7P4ZDQOlXIBBbdJQzAigmDeTniUc/edit?gid=1824505919#gid=1824505919

---

### 📝 기능 설명
- Google Sheet에서 약물 데이터 자동 불러오기
- Tmax, F, Vd 등 PK 파라미터 기반 시뮬레이션
- Onset 및 약효 소실 시점 표시
- 그래프 Width (X-scale)는 t_half(반감기) * 7

---

### ⏳ 반감기 경과에 따른 약물 잔존 비율
| 경과 시간 (반감기 기준) | 남은 약물 (%) | 설명 |
|-------------------------|----------------|------|
| 1 × t½                  | 50%            | 1회 반감기 후 |
| 2 × t½                  | 25%            |  |
| 3 × t½                  | 12.5%          |  |
| 4 × t½                  | 6.25%          | ✅ 통상 약효 없음 |
| 5 × t½                  | 3.125%         | ✅ 완전히 소실로 간주 |
| 6 × t½                  | 1.56%          | 대부분 측정 불가 수준 |
"""
            )

