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
def plot_drug_concentration_with_onset(drug_name, D, F, V_d, t_half, t_max, body_weight, onset_time_hour, end_threshold):
    Vd = V_d * body_weight
    k = math.log(2) / t_half #1차 소실속도 상수
    ka = (math.log(2) / t_max) + k #흡수속도 상수
    time = np.linspace(0, t_half * 7, 1000) #X scale 게산 (반감기 * 7 후, 1000으로 나눠 정밀하게 그림)

    C1_mg_per_L = (ka * F * D) / (Vd * (ka - k)) * (np.exp(-k * time) - np.exp(-ka * time)) # 이게 진짜 농도 계산 수식
    C1_mg_per_L[C1_mg_per_L < 0] = 0
    C1_ng_per_mL = C1_mg_per_L * 1000 # 수식은 ug로 반환하기때문에, mg로 바꾸기 위해 1000 곱함


    onset_concentration = (ka * F * D) / (Vd * (ka - k)) * \
                          (np.exp(-k * onset_time_hour) - np.exp(-ka * onset_time_hour)) #  유효농도 도달시간 기준으로 해당점의 농도 구해서 상승기, 반감기 두번 점찍음 ( 1000 #여기도 농도라서 1000 곱함)

    t_max_index = np.argmax(C1_ng_per_mL)
    t_max_time = time[t_max_index]

    time_after_tmax = time[t_max_index:]
    conc_after_tmax = C1_ng_per_mL[t_max_index:]
    try:
        onset_end_index = np.where(conc_after_tmax < onset_concentration)[0][0]
        onset_end_time = time_after_tmax[onset_end_index]
    except IndexError:
        onset_end_time = None

    try:
        end_threshold_index = np.where(conc_after_tmax < end_threshold)[0][0]
        end_threshold_time = time_after_tmax[end_threshold_index]
    except IndexError:
        end_threshold_time = None

    # ✅ 그래프 외부에 파라미터 출력 (Streamlit markdown)
    st.markdown(f"""    
    | 항목 | 값 |
    |------|------|
    | 용량 (D) | {D} mg |
    | 생체이용률 (F) | {F*100:.1f} % |
    | 분포용적 (Vd) | {V_d:.2f} L/kg × {body_weight}kg = {Vd:.2f} L |
    | 반감기 (t½) | {t_half} hr |
    | Tmax | {t_max} hr |
    | 약효 시작 시간 | {onset_time_hour} hr |
    | 약효 종료 농도 | {end_threshold} ng/mL |
    """)

    # ✅ 그래프
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time, C1_ng_per_mL, label='혈중 농도 (C₁)', color='blue', linewidth=2)

    ax.axvline(x=onset_time_hour, color='green', linestyle='--', label=f'약효 시작: {onset_time_hour:.1f}h')
    if onset_end_time:
        ax.axvline(x=onset_end_time, color='orange', linestyle='--', label=f'약효 종료: {onset_end_time:.1f}h')
        ax.axhline(y=onset_concentration, xmin=0, xmax=1, color='red', linestyle='--', linewidth=1.5,
                   label=f'약효 지속 농도: {onset_concentration:.2f} ng/mL')

    if end_threshold_time:
        ax.axhline(y=end_threshold, color='red', linestyle=':', label=f'종료 농도: {end_threshold} ng/mL')
        ax.plot(end_threshold_time, end_threshold, 'ro', markersize=8, label=f'종료 시점: {end_threshold_time:.1f}h')

    c_max_value = np.max(C1_ng_per_mL)
    ax.plot(t_max_time, c_max_value, 'kv', markersize=8, label=f'Cmax: {c_max_value:.2f} ng/mL')

    ax.set_title(f'{drug_name} - 혈중 농도 및 약효 시간')
    ax.set_xlabel("시간 (hours)")
    ax.set_ylabel("혈중 농도 (ng/mL)")
    ax.grid(True, linestyle=':')
    ax.legend()
    ax.set_xlim(0, time[-1])
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
            end_threshold=float(row['end_threshold'])
        )
        st.markdown("---")

if __name__ == "__main__":
    main()
