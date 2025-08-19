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
def plot_patch_concentration(
    drug_name, D, F, V_d, t_half, t_max,
    body_weight, onset_time_hour, patch_duration_hour, t_last
):
    # --- 파라미터 ---
    D_ng = D * 1e6
    k = np.log(2) / t_half                   # 소실속도(1/h)
    R0 = (D_ng * F) / patch_duration_hour    # ng/h (패치 부착 중)
    Vd_total = V_d * body_weight             # L
    total_time = max(patch_duration_hour * 2, t_half * 7)

    # 워시아웃(잔여 흡수) 시간상수: 패치 제거 후 입력이 서서히 0으로
    tau_off = 6.0  # hours (필요하면 3~12h 사이로 튜닝)

    # --- 시간축/수치적분 ---
    time = np.linspace(0, total_time, 20000)
    dt = time[1] - time[0]
    concentration = np.zeros_like(time)

    t_off = patch_duration_hour
    for i in range(1, len(time)):
        t = time[i]
        if t <= t_off:
            R_t = R0
        else:
            R_t = R0 * np.exp(-(t - t_off) / tau_off)  # 부드러운 종료(잔여 흡수 꼬리)

        # 1-컴파트먼트 미분방정식 적분: dc/dt = R(t)/Vd - k*c
        dc = (R_t / Vd_total - k * concentration[i-1]) * dt
        concentration[i] = max(concentration[i-1] + dc, 0.0)

    # --- Tmax, Cmax ---
    t_max_index = np.argmax(concentration)
    t_max_time = time[t_max_index]
    c_max_value = concentration[t_max_index]

    # --- onset 농도(모델 값에서 직접 샘플링) ---
    onset_idx = np.searchsorted(time, onset_time_hour, side="left")
    onset_idx = min(onset_idx, len(time)-1)
    onset_concentration = concentration[onset_idx]

    # --- 약효 종료 시점(피크 이후 농도가 onset 아래로 내려가는 첫 시점) ---
    time_after_peak = time[t_max_index:]
    conc_after_peak = concentration[t_max_index:]
    below = np.where(conc_after_peak < onset_concentration)[0]
    if len(below) > 0:
        fall_index = below[0]
        falling_time = time_after_peak[fall_index]
    else:
        falling_time = None

    # --- 그래프 범위 자르기 ---
    if falling_time is not None:
        plot_end_time = falling_time + t_last
    else:
        plot_end_time = time[-1]
    mask = time <= plot_end_time
    time = time[mask]
    concentration = concentration[mask]

    # --- 표 출력 ---
    st.markdown(f"""
    | 항목 | 값 |
    |------|------|
    | 용량 (D) | {D} mg |
    | 생체이용률 (F) | {F*100:.1f}% |
    | 분포용적 (Vd) | {V_d:.2f} L/kg × {body_weight}kg = {Vd_total} |
    | 반감기 (t½) | {t_half} hr |
    | Tmax | {t_max} hr |
    | Patch 부착 시간 | {patch_duration_hour} hr |
    | 약효 시작 | {onset_time_hour} hr |
    | 워시아웃 τ | {tau_off} hr |
    """)

    # --- 그래프 ---
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time, concentration, label='혈중 농도')
    ax.axvline(x=onset_time_hour, linestyle='--', label=f'약효 시작: {onset_time_hour:.1f}h')
    ax.plot(t_max_time, c_max_value, 'v', label=f'Cmax: {c_max_value:.2f} ng/mL')
    ax.axhline(y=onset_concentration, linestyle='--',
               label=f'약효 기준 농도: {onset_concentration:.2f} ng/mL')
    ax.axvline(x=plot_end_time, linestyle=':',
               label=f'그래프 종료: {plot_end_time:.1f}h')
    if falling_time is not None:
        ax.axvline(x=falling_time, linestyle='--',
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
