import streamlit as st
import numpy as np
import platform
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
eps = 1e-9

from functions import get_google_sheet

BODY_WEIGHT = 70

# Streamlit 설정
st.set_page_config(layout="centered")
st.title("💊 경구약물 연속복용 농도")

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
else:
    print(f"⚠️ 해당 OS({system})에서 폰트를 찾을 수 없습니다.")

# 약동학 모델 함수
def simulate_pk_multi_dose_simple(drug_name, t_max, t_half, V_d, F, D, tau, n_doses, dt, body_weight):
    Vd_total = V_d * body_weight

    # --- k, ka 계산 ---
    k = math.log(2) / t_half
    ka = (math.log(2) / t_max) + k
    if abs(ka - k) < eps:
        ka = k + eps

    # --- 시간축 구성 ---
    total_time = n_doses * tau
    time = np.arange(0.0, total_time + dt, dt)

    # 각 시점의 투여 횟수 및 마지막 투여 후 경과시간
    n = np.floor(time / tau).astype(int) + 1
    n = np.clip(n, 0, n_doses)
    t_since_last = time - (n - 1) * tau
    t_since_last = np.where(n == 0, 0.0, t_since_last)

    # 누적계수
    def accum(r, n_):
        den = 1.0 - np.exp(-r * tau)
        den = np.where(np.abs(den) < eps, eps, den)
        return (1.0 - np.exp(-n_ * r * tau)) / den

    A_k  = accum(k,  n)
    A_ka = accum(ka, n)

    # ---- 농도 계산 (mg/L) -> ng/mL 변환 ----
    coef_mg_per_L = (ka * F * D) / (Vd_total * (ka - k))  # mg/L 계수
    C_mg_per_L = np.zeros_like(time)
    mask = n > 0
    C_mg_per_L[mask] = coef_mg_per_L * (
        A_k[mask]  * np.exp(-k  * t_since_last[mask]) -
        A_ka[mask] * np.exp(-ka * t_since_last[mask])
    )

    # 단일투여식 참고하신 로직과 동일하게 후처리:
    # 1) 음수 절삭
    C_mg_per_L[C_mg_per_L < 0] = 0
    # 2) mg/L -> ng/mL (×1000)
    concentration = C_mg_per_L * 1000.0

    # 그래프
    st.markdown(f"""
        | 항목 | 값 |
        |------|------|
        | 용량 (D) | {D} mg |
        | 생체이용률 (F) | {F * 100:.1f}% |
        | 분포용적 (Vd) | {V_d:.2f} L/kg × {body_weight}kg = {Vd_total} |
        | 반감기 (t½) | {t_half} hr |
        | 투여간격 | {tau} hr |
        | 복용횟수 | {n_doses} |
        """)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time, concentration, lw=2, label='혈중 농도 (C)')
    # 투여 시점 표시(선택)
    for i in range(n_doses):
        ax.axvline(i * tau, linestyle="--", linewidth=0.6, color='gray')

    ax.set_title(f'{drug_name} - 혈중 농도 및 약효 시간')
    ax.set_xlabel("시간 (hours)")
    ax.set_ylabel("혈중 농도 (ng/mL)")   # ★ 단위 수정
    ax.grid(True, linestyle=':')
    ax.legend()
    ax.set_ylim(0)

    st.pyplot(fig)

    #return t, concentration, ka, k
# === 데이터 불러오기 및 필터링 ===
def main():

    df = get_google_sheet()
    filtered_df = df[(df['Use'] == 'Y') & (df['route_of_administration'].isin(['경구일반', '경구서방']))]
    st.markdown("---")

    #변수설명
    #tau: 복약간격
    #dt: 그래프 해상도 (dt=0.05h (≈ 3분) → 0 ~ 48시간을 0.05 간격으로 계산 → 총 961포인트)
    for _, row in filtered_df.iterrows():
        st.subheader(f"🧪 {row['drug_name']}")
        simulate_pk_multi_dose_simple(
            drug_name=row['drug_name'],
            D=float(row['D']),
            F=float(row['F']) * 0.01,
            V_d=float(row['V_d']),
            t_half=float(row['t_half']),
            t_max=float(row['t_max']),
            body_weight=BODY_WEIGHT,
            tau = float(row['tau']),
            n_doses = 4,
            dt = 0.05
        )
        st.markdown("---")

if __name__ == "__main__":
    main()
