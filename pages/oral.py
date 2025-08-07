import streamlit as st
import numpy as np
import platform
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import sys
import matplotlib.ticker as ticker


from functions import get_google_sheet

BODY_WEIGHT = 70

# Streamlit 설정
st.set_page_config(layout="centered")
st.title("💊 경구 약물 농도 시뮬레이션")

system = platform.system()
if system == "Windows":
    font_path = "C:/Windows/Fonts/malgun.ttf"
elif system == "Darwin":  # macOS
    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
elif system == "Linux":
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
else:
    font_path = None

if font_path and os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = font_prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    print(f"✅ 폰트 설정됨: {font_prop.get_name()} ({system})")
else:
    print(f"⚠️ 해당 OS({system})에서 폰트를 찾을 수 없습니다.")

# 약동학 모델 함수
def plot_drug_concentration_with_onset(drug_name, D, F, V_d, t_half, t_max, body_weight, onset_time_hour, t_end):
    import numpy as np
    import matplotlib.pyplot as plt
    import streamlit as st
    import math

    # 파라미터 계산
    Vd_total = V_d * body_weight
    k = math.log(2) / t_half
    ka = (math.log(2) / t_max) + k
    total_time = t_half * 7
    time = np.linspace(0, total_time, 1000)

    # 혈중 농도 계산
    C1_mg_per_L = (ka * F * D) / (Vd_total * (ka - k)) * (np.exp(-k * time) - np.exp(-ka * time))
    C1_mg_per_L[C1_mg_per_L < 0] = 0
    C1_ng_per_mL = C1_mg_per_L * 1000

    # Tmax 계산
    t_max_index = np.argmax(C1_ng_per_mL)
    t_max_time = time[t_max_index]
    c_max_value = C1_ng_per_mL[t_max_index]

    # onset 농도 계산
    onset_concentration = (ka * F * D) / (Vd_total * (ka - k)) * \
                          (math.exp(-k * onset_time_hour) - math.exp(-ka * onset_time_hour)) * 1000  # ng/mL

    # Tmax 이후에 onset_concentration 으로 감소하는 지점 찾기
    time_after_peak = time[t_max_index:]
    conc_after_peak = C1_ng_per_mL[t_max_index:]

    try:
        fall_index = np.where(conc_after_peak < onset_concentration)[0][0]
        falling_time = time_after_peak[fall_index]
        falling_onset_concentration = C1_ng_per_mL[t_max_index + fall_index]
    except IndexError:
        falling_time = None
        falling_onset_concentration = None

    # ✅ time과 농도 배열을 falling_time + t_end까지 자르기
    if falling_time is not None:
        plot_end_time = falling_time + t_end
        mask = time <= plot_end_time
        time = time[mask]
        C1_ng_per_mL = C1_ng_per_mL[mask]
    else:
        plot_end_time = time[-1]  # fallback

    st.markdown(f"""
    | 항목 | 값 |
    |------|------|
    | 용량 (D) | {D} mg |
    | 생체이용률 (F) | {F*100:.1f}% |
    | 분포용적 (Vd) | {V_d:.2f} L/kg × {body_weight}kg = {Vd_total} |
    | 반감기 (t½) | {t_half} hr |
    | Tmax | {t_max} hr |    
    | 약효 시작 | {onset_time_hour} hr |
    """)

    # ✅ 그래프
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time, C1_ng_per_mL, label='혈중 농도 (C₁)', color='blue', linewidth=2)

    ax.axvline(x=onset_time_hour, color='green', linestyle='--', label=f'약효 시작: {onset_time_hour:.1f}h')
    ax.plot(t_max_time, c_max_value, 'kv', markersize=8, label=f'Cmax: {c_max_value:.2f} ng/mL')

    if falling_time is not None:
        ax.axhline(y=onset_concentration,
                   xmin=0, xmax=1,
                   color='blue', linestyle='--', linewidth=2,
                   label=f'약효 기준 농도: {onset_concentration:.2f} ng/mL')
        ax.axvline(x=falling_time, color='orange', linestyle='--',
                   label=f'약효 종료 시간: {falling_time:.1f}h')
        ax.axvline(x=plot_end_time, color='gray', linestyle=':',
                   label=f'그래프 종료: {plot_end_time:.1f}h')

    ax.set_title(f'{drug_name} - 혈중 농도 및 약효 시간')
    ax.set_xlabel("시간 (hours)")
    ax.set_ylabel("혈중 농도 (ng/mL)")
    ax.grid(True, linestyle=':')
    ax.legend()
    ax.set_xlim(0, plot_end_time)
    ax.set_ylim(0)

    st.pyplot(fig)
# === 데이터 불러오기 및 필터링 ===
def main():

    df = get_google_sheet()
    filtered_df = df[(df['Use'] == 'Y') & (df['route_of_administration'].isin(['경구일반', '경구서방']))]
    st.markdown("---")

    for _, row in filtered_df.iterrows():
        st.subheader(f"🧪 {row['drug_name']}")
        plot_drug_concentration_with_onset(
            drug_name=row['drug_name'],
            D=float(row['D']),
            F=float(row['F']) * 0.01,
            V_d=float(row['V_d']),
            t_half=float(row['t_half']),
            t_max=float(row['t_max']),
            body_weight=BODY_WEIGHT,
            onset_time_hour=float(row['onset_time_hour']),
            t_end = float(row['t_end'])
        )
        st.markdown("---")

if __name__ == "__main__":
    main()
