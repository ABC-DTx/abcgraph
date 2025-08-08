import streamlit as st
import numpy as np
import platform
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import matplotlib.ticker as ticker
from functions import get_google_sheet

BODY_WEIGHT = 70

# Streamlit 설정
st.set_page_config(layout="centered")
st.title("💊 패치 약물 농도 시뮬레이션")

# 폰트 설정
system = platform.system()
if system == "Windows":
    font_path = "C:/Windows/Fonts/malgun.ttf"
elif system == "Darwin":
    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
elif system == "Linux":
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
else:
    font_path = None

if font_path and os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = font_prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
else:
    print(f"⚠️ 해당 OS({system})에서 폰트를 찾을 수 없습니다.")

# 패치 약물 농도 계산 함수
def plot_patch_concentration(drug_name, D, F, V_d, t_half, t_max, body_weight, onset_time_hour, patch_duration_hour, t_last):

    #파라미터 계산
    D_ng = D * 1e6 #패치형 약물은 천천히 일정 속도로 투입되므로, 정확한 농도 계산을 위해 용량 단위를 ng로 변환한 후 누적/소실 계산에 직접 사용
    k = np.log(2) / t_half
    R0 = (D_ng * F) / patch_duration_hour  # ng/hr
    Vd_total = V_d * body_weight  # L
    total_time = max(patch_duration_hour * 2, t_half * 7)# 패치의 경우 속효성 약품보다 길게 그림

    time = np.linspace(0, total_time, 10000)

    #혈중농도 계산
    concentration = []
    for t in time:
        if t <= patch_duration_hour:
            c = (R0 / (k * Vd_total)) * (1 - np.exp(-k * t))
        else:
            C_end = (R0 / (k * Vd_total) * (1 - np.exp(-k * patch_duration_hour)))
            c = C_end * np.exp(-k * (t - patch_duration_hour))
        concentration.append(c)
    concentration = np.array(concentration)

    #tmax 계산
    t_max_index = np.argmax(concentration)
    t_max_time = time[t_max_index]
    c_max_value = concentration[t_max_index]

    # onset 농도 계산
    if onset_time_hour <= patch_duration_hour: #onset 시간이 patch 붙히고 있는 시간보다 짧다 (거의 이 로직만 탐)
        onset_concentration = (R0 / (k * Vd_total)) * (1 - np.exp(-k * onset_time_hour))
    else:
        C_end = (R0 / (k * Vd_total)) * (1 - np.exp(-k * patch_duration_hour))
        onset_concentration = C_end * np.exp(-k * (onset_time_hour - patch_duration_hour))
        print("어며 여길 탔네")


    # Tmax 이후에 onset_concentration 으로 감소하는 지점 찾기
    time_after_peak = time[t_max_index:]
    conc_after_peak = concentration[t_max_index:]

    try:
        fall_index = np.where(conc_after_peak < onset_concentration)[0][0]
        falling_time = time_after_peak[fall_index]
        falling_onset_concentration = concentration[t_max_index + fall_index]
    except IndexError:
        falling_time = None
        falling_onset_concentration = None

    # ✅ time과 농도 배열을 falling_time + t_last 자르기
    if falling_time is not None:
        plot_end_time = falling_time + t_last
        mask = time <= plot_end_time
        time = time[mask]
        concentration = concentration[mask]
    else:
        plot_end_time = time[-1]  # fallback

    # 표 출력
    st.markdown(f"""
    | 항목 | 값 |
    |------|------|
    | 용량 (D) | {D} mg |
    | 생체이용률 (F) | {F * 100:.1f}% |
    | 분포용적 (Vd) | {V_d:.2f} L/kg × {body_weight}kg = {Vd_total} |
    | 반감기 (t½) | {t_half} hr |
    | Tmax | {t_max} hr |
    | Patch 부착 시간 | {patch_duration_hour} hr |
    | 약효 시작 | {onset_time_hour} hr |
    """)

    # 그래프
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time, concentration, label='혈중 농도', color='blue')
    ax.axvline(x=onset_time_hour, color='green', linestyle='--', label=f'약효 시작: {onset_time_hour:.1f}h')
    ax.plot(t_max_time, c_max_value, 'kv', markersize=8, label=f'Cmax: {c_max_value:.2f} ng/mL')
    #ax.axhline(y=onset_concentration, color='blue', linestyle=':', label=f'약효 기준 농도: {onset_concentration:.2f} ng/mL')
    ax.axhline(y=onset_concentration,
               xmin=0, xmax=1,
               color='blue', linestyle='--', linewidth=2,
               label=f'약효 기준 농도: {onset_concentration:.2f} ng/mL')
    ax.axvline(x=plot_end_time, color='gray', linestyle=':',
               label=f'그래프 종료: {plot_end_time:.1f}h')

    if falling_time is not None:
        ax.axvline(x=falling_time, color='orange', linestyle='--',
                   label=f'약효 종료 시간: {falling_time:.1f}h')

    ax.set_title(f'{drug_name} - 혈중 농도 및 약효 시간')
    ax.set_xlabel("시간 (hours)")
    ax.set_ylabel("혈중 농도 (ng/mL)")
    ax.grid(True, linestyle=':')
    ax.legend()
    ax.set_xlim(0, plot_end_time)
    ax.set_ylim(0)

    st.pyplot(fig)


# === 메인 실행 ===
def main():
    df = get_google_sheet()
    filtered_df = df[(df['Use'] == 'Y') & (df['route_of_administration'].str.contains('패치'))]

    st.markdown("---")

    for _, row in filtered_df.iterrows():
        st.subheader(f"🧪 {row['drug_name']}")
        plot_patch_concentration(
            drug_name=row['drug_name'],
            D=float(row['D']),
            F=float(row['F']) * 0.01,
            V_d=float(row['V_d']),
            t_half=float(row['t_half']),
            t_max=float(row['t_max']),
            body_weight=BODY_WEIGHT,
            onset_time_hour=float(row['onset_time_hour']),
            patch_duration_hour=float(row['patch_duration_hour']),
            t_last = float(row['t_last'])
        )
        st.markdown("---")

if __name__ == "__main__":
    main()
