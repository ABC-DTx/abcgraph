import streamlit as st
import numpy as np
import platform
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import sys
import matplotlib.ticker as ticker

# Google Sheet 함수 불러오기
sys.path.append('/tf/ABC프로젝트')
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
def calc_k_and_ka_oral(t_half, t_max):
    ln2 = math.log(2)
    k = ln2 / t_half
    ka = ln2 / t_max + k
    return k, ka

def concentration_C1_oral(t, ka, F, D, Vd, k):
    numerator = ka * F * D
    denominator = Vd * (ka - k)
    exp1 = np.exp(-k * t)
    exp2 = np.exp(-ka * t)
    return (numerator / denominator * (exp1 - exp2)) * 1000  # ng/ml

def simulate_concentration_json_oral(row, interval_min, end_threshold):
    t_half = row['t_half']
    t_max = row['t_max']
    F = row['F']
    D = row['D']
    V_d = row['V_d']
    onset_time = row['onset_time']
    drug_name = row['drug_name']
    total_hour = row['total_hour']

    # 약동학 상수 계산
    k, ka = calc_k_and_ka_oral(t_half, t_max)

    # 0 ~ 48시간까지 1분 단위로 시뮬레이션
    #t_all = np.linspace(0, 48, 48 * 60 + 1)
    t_all = np.linspace(0, total_hour, total_hour * 60 + 1)
    C_all = concentration_C1_oral(t_all, ka, F, D, V_d, k)

    # ⏱️ onset time 에 해당하는 농도 계산
    C_onset = concentration_C1_oral(np.array([onset_time]), ka, F, D, V_d, k)[0]

    # 📍 onset 농도와의 교차점 찾기 (상승기 1개 + 하강기 1개)
    def find_crossings(t, y, threshold, max_points=2):
        points = []
        for i in range(1, len(y)):
            if (y[i - 1] < threshold and y[i] >= threshold) or (y[i - 1] > threshold and y[i] <= threshold):
                t0, t1 = t[i - 1], t[i]
                y0, y1 = y[i - 1], y[i]
                slope = (y1 - y0) / (t1 - t0)
                cross_t = t0 + (threshold - y0) / slope
                points.append({
                    "x": round(float(cross_t), 2),
                    "y": round(float(threshold), 2)
                })
            if len(points) >= max_points:
                break
        return points

    onset_points = find_crossings(t_all, C_all, C_onset, max_points=2)

    # ✅ 효과 종료 시점 (하강기에서 end_threshold 아래로 떨어지는 첫 지점)
    end_index = None
    for i in range(np.argmax(C_all), len(C_all)):
        if C_all[i] < end_threshold:
            end_index = i
            break

    # 종료 시점 보간 계산
    end_point = None
    if end_index is not None and end_index > 0:
        t0, t1 = t_all[end_index - 1], t_all[end_index]
        c0, c1 = C_all[end_index - 1], C_all[end_index]
        slope = (c1 - c0) / (t1 - t0)
        cross_t = t0 + (end_threshold - c0) / slope
        end_point = {
            "x": round(float(cross_t), 2),
            "y": round(float(end_threshold), 2)
        }
        # ✂️ 시뮬레이션 결과 잘라내기
        t_all = t_all[:end_index + 1]
        C_all = C_all[:end_index + 1]

    return {
        "drug_name": drug_name,
        "x": [round(float(t), 2) for t in t_all],
        "y": [round(float(c), 2) for c in C_all],
        "onset_points": onset_points,
        "end_point": end_point
    }


def plot_concentration_from_result_oral(result, interval_min=10):
    drug_name = result["drug_name"]
    x = result["x"]
    y = result["y"]
    onset_points = result["onset_points"]
    end_point = result.get("end_point")

    fig, ax = plt.subplots(figsize=(7, 3.5))  # 작게 설정
    ax.plot(x, y, label="Concentration (ng/ml)", color="blue")
    #ax.set_xticks(np.arange(0, max(x) + 0.01, interval_min / 60))
    ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))  #

    if onset_points:
        onset_y = onset_points[0]['y']
        ax.axhline(onset_y, color='red', linestyle='--', label=f"Onset = {onset_y} ng/ml")
        for pt in onset_points:
            if pt['x'] <= x[-1]:
                ax.plot(pt['x'], pt['y'], 'ro')
                ax.annotate(f"({pt['x']}, {pt['y']})", (pt['x'], pt['y']), textcoords="offset points", xytext=(5, 5))

    if end_point and end_point['x'] <= x[-1]:
        ax.plot(end_point['x'], end_point['y'], 'go', label="Effectively 0 ng/ml")
        ax.annotate(f"({end_point['x']}, {end_point['y']})", (end_point['x'], end_point['y']), textcoords="offset points", xytext=(5, -15))

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Concentration (ng/ml)")
    ax.set_title(f"Drug Concentration: {drug_name}")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

# === 데이터 불러오기 및 필터링 ===
df = get_google_sheet()
df = df[df['Use'] == 'Y']
options = df[df['route_of_administration'].isin(['경구일반', '경구서방']) & (df['onset_time_hour'].astype(float) > 0)]

st.subheader("📊 전체 경구 약물 시뮬레이션")

for _, row in options.iterrows():
    drug_name = row['drug_name']
    t_half = float(row['t_half'])
    t_max = float(row['t_max'])
    F = float(row['F']) * 0.01
    D = float(row['D'])
    V_d = float(row['V_d']) * BODY_WEIGHT
    onset_time = float(row['onset_time_hour'])
    interval_min = float(row['interval_min'])
    end_threshold = float(row['end_threshold'])
    total_hour = int(row['total_hour'])

    result = simulate_concentration_json_oral({
        'drug_name': drug_name,
        't_half': t_half,
        't_max': t_max,
        'F': F,
        'D': D,
        'V_d': V_d,
        'onset_time': onset_time,
        'total_hour': total_hour,
    }, interval_min, end_threshold)
    print(result)
    # ❌ with ❌ → ✅ 그냥 호출 ✅
    st.subheader(f"💊 {drug_name}")

    st.markdown(f"""
    - **T₁/₂ (반감기):** {t_half} hr  
    - **Tmax:** {t_max} hr  
    - **F (생체이용률):** {F*100:.1f}%  
    - **D (투여량):** {D} mg  
    - **Vd (분포용적):** {row['V_d']} L/kg × {BODY_WEIGHT} kg = {V_d:.2f} L  
    - **Onset time:** {onset_time} hr  
    - **Sampling interval:** {interval_min} min  
    - **효과 종료 임계값:** {end_threshold} ng/ml
    """)

    plot_concentration_from_result_oral(result, interval_min=interval_min)