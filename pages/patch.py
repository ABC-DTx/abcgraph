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
def plot_patch_concentration(drug_name, D, F, V_d, t_half, t_max, body_weight, onset_time, patch_duration_hour, end_threshold):
    D_ng = D * 1e6
    k = np.log(2) / t_half
    R0 = (D_ng * F) / patch_duration_hour  # ng/hr

    #R0 = D * 1000 / patch_duration_hour  # µg/hr
    Vd_total = V_d * body_weight   # L
    #ke = math.log(2) / t_half      # 1차 소실속도 상수

    total_time = max(patch_duration_hour * 2, t_half * 7)
    time = np.linspace(0, total_time, 1000)

    concentration = []

    for t in time:
        if t <= patch_duration_hour:
            #c = (R0 / (k * Vd_total)) * (1 - np.exp(-k * t))
            c = (R0 / (k * Vd_total)) * (1 - np.exp(-k * t))
        else:
            C_end = (R0 / (k * Vd_total) * (1 - np.exp(-k * patch_duration_hour)))
            c = C_end * np.exp(-k * (t - patch_duration_hour))
        concentration.append(c)

    concentration = np.array(concentration)

    # ▶ onset 시간의 농도 계산
    if onset_time <= patch_duration_hour:
        onset_conc = (R0 / (k * Vd_total)) * (1 - np.exp(-k * onset_time))
    else:
        C_end = (R0 / (k * Vd_total)) * (1 - np.exp(-k * patch_duration_hour))
        onset_conc = C_end * np.exp(-k * (onset_time - patch_duration_hour))

    # 표 출력
    st.markdown(f"""
    | 항목 | 값 |
    |------|------|
    | 용량 (D) | {D} mg |
    | 생체이용률 (F) | {F*100:.1f}% |
    | 분포용적 (Vd) | {V_d:.2f} L/kg × {body_weight}kg = {Vd_total} |
    | 반감기 (t½) | {t_half} hr |
    | Tmax | {t_max} hr |
    | Patch 부착 시간 | {patch_duration_hour} hr |
    | 약효 시작 | {onset_time} hr |
    | 약효 종료 농도 | {end_threshold} ng/mL |
    """)

    # 그래프
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time, concentration, label='혈중 농도', color='blue')

    #ax.axvline(x=onset_time, color='green', linestyle='--', label=f'Onset: {onset_time:.1f}h')
    #ax.axvline(x=t_max, color='purple', linestyle='--', label=f'Tmax: {t_max:.1f}h')
    #ax.axvline(x=patch_duration_hour, color='gray', linestyle='--', label=f'Patch 제거: {patch_duration_hour:.1f}h')
    ax.axvline(x=onset_time, color='green', linestyle='--', label=f'Onset: {onset_time:.1f}h')
    ax.axhline(y=onset_conc, color='green', linestyle=':', label=f'농도 at onset: {onset_conc:.2f} ng/mL')

    ax.axvline(x=t_max, color='purple', linestyle='--', label=f'Tmax: {t_max:.1f}h')
    ax.axvline(x=patch_duration_hour, color='gray', linestyle='--', label=f'Patch 제거: {patch_duration_hour:.1f}h')

    ax.set_title(f"{drug_name} - 패치 농도 곡선")
    ax.set_xlabel("시간 (hr)")
    ax.set_ylabel("혈중 농도 (ng/mL)")
    ax.grid(True, linestyle=':')
    ax.legend()
    ax.set_xlim(0, time[-1])
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
            onset_time=float(row['onset_time_hour']),
            patch_duration_hour=float(row['patch_duration_hour']),
            end_threshold=float(row['end_threshold'])
        )
        st.markdown("---")

if __name__ == "__main__":
    main()
