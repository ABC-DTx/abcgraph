import streamlit as st
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import platform
import sys

sys.path.append('/tf/ABCμπροεκτ')
from functions import get_google_sheet

BODY_WEIGHT = 70

# 폰트 설정
system = platform.system()
if system == "Windows":
    font_path = "C:/Windows/Fonts/malgun.ttf"
elif system == "Darwin":
    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
else:
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

if os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = font_prop.get_name()
    plt.rcParams["axes.unicode_minus"] = False
else:
    print("⚠️ 폰트 파일 없음:", font_path)

st.set_page_config(layout="centered")
st.title("🩹 패치 약물 농도 시뮬레이션")

# 파치 모델 시험

def simulate_patch_concentration_2comp(row, duration_hour, total_hour, end_threshold):
    t_half = row['t_half']
    t_max = row['t_max']
    F = row['F']
    R0 = row['R0']
    V_d = row['V_d']
    onset_time = row['onset_time']
    drug_name = row['drug_name']

    ke = math.log(2) / t_half
    ka = ke * 4

    interval_hr = 1 / 60  # 1분 해상도 고정
    t_all = np.arange(0, total_hour + interval_hr, interval_hr)

    Dose = R0 * duration_hour
    C_all = []

    for ti in t_all:
        if ti <= duration_hour:
            c = (F * Dose * ka / (V_d * (ka - ke))) * (math.exp(-ke * ti) - math.exp(-ka * ti))
        else:
            c_removal = (F * Dose * ka / (V_d * (ka - ke))) * (math.exp(-ke * duration_hour) - math.exp(-ka * duration_hour))
            c = c_removal * math.exp(-ke * (ti - duration_hour))
        C_all.append(c)  # ng/mL

    C_all = np.array(C_all)

    # onset_time 시점의 농목
    onset_idx = (np.abs(t_all - onset_time)).argmin()
    C_onset = C_all[onset_idx]

    def find_crossings(t, y, target, max_points=2):
        points = []
        for i in range(1, len(y)):
            if (y[i - 1] < target <= y[i]) or (y[i - 1] > target >= y[i]):
                t0, t1 = t[i - 1], t[i]
                y0, y1 = y[i - 1], y[i]
                slope = (y1 - y0) / (t1 - t0)
                cross_t = t0 + (target - y0) / slope
                points.append({"x": round(cross_t, 2), "y": round(target, 2)})
            if len(points) >= max_points:
                break
        return points

    onset_points = find_crossings(t_all, C_all, C_onset)

    end_point = None
    for i in range(np.argmax(C_all), len(C_all)):
        if C_all[i] < end_threshold:
            t0, t1 = t_all[i - 1], t_all[i]
            c0, c1 = C_all[i - 1], C_all[i]
            slope = (c1 - c0) / (t1 - t0)
            cross_t = t0 + (end_threshold - c0) / slope
            end_point = {"x": round(cross_t, 2), "y": round(end_threshold, 2)}
            break

    return {
        "drug_name": drug_name,
        "x": [round(float(x), 2) for x in t_all],
        "y": [round(float(c), 4) for c in C_all],
        "ke": round(ke, 5),
        "ka": round(ka, 5),
        "duration_hr": duration_hour,
        "onset_points": onset_points,
        "end_point": end_point
    }

# 그래프 구현

def plot_patch_concentration(result):
    x = result["x"]
    y = result["y"]
    duration_hr = result["duration_hr"]
    onset_points = result.get("onset_points", [])
    end_point = result.get("end_point")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(x, y, label="Concentration (ng/mL)", color='blue')

    ax.axvline(duration_hr, color='red', linestyle='--', label=f"Patch Removed at {duration_hr} hr")

    if onset_points:
        onset_y = onset_points[0]['y']
        ax.axhline(onset_y, color='orange', linestyle='--', label=f"Onset = {onset_y} ng/ml")
        for pt in onset_points:
            ax.plot(pt['x'], pt['y'], 'ro')
            ax.annotate(f"({pt['x']}, {pt['y']})", (pt['x'], pt['y']), textcoords="offset points", xytext=(5, 5))

    if end_point:
        ax.plot(end_point['x'], end_point['y'], 'go', label="Effectively 0 ng/ml")
        ax.annotate(f"({end_point['x']}, {end_point['y']})", (end_point['x'], end_point['y']), textcoords="offset points", xytext=(5, -15))

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Concentration (ng/mL)")
    ax.set_title("Drug Concentration: Transdermal Patch")
    ax.grid(True)
    ax.legend()
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=10))
    st.pyplot(fig)

# 데이터 파출

df = get_google_sheet()
df = df[df['Use'] == 'Y']
patch_df = df[df['route_of_administration'] == '패치']

st.subheader("📊 전체 패치 약물 시뮬레이션")

for _, row in patch_df.iterrows():
    drug_name = row['drug_name']
    t_half = float(row['t_half'])
    t_max = float(row['t_max'])
    c_max = float(row['Cmax(ng/ml)'])
    F = float(row['F']) * 0.01
    D = float(row['D'])
    R0 = D * 1000  # mcg/hr
    V_d = float(row['V_d']) * BODY_WEIGHT
    onset_time = float(row['onset_time_hour'])
    total_hour = float(row['total_hour'])
    duration_hour = float(row['patch_duration_hour'])
    end_threshold = float(row['end_threshold'])

    row_dict = {
        'drug_name': drug_name,
        't_half': t_half,
        't_max': t_max,
        'F': F,
        'R0': R0,
        'V_d': V_d,
        'onset_time': onset_time
    }

    result = simulate_patch_concentration_2comp(row_dict, duration_hour, total_hour, end_threshold)
    if drug_name == "":
        print(result)
    st.subheader(f"🩹 {drug_name}")
    st.markdown(f"""
    - **T₁/₂ (반감기):** {t_half} hr  
    - **Tmax:** {t_max} hr  
    - **F (생체이용률):** {F*100:.1f}%  
    - **R₀ (방출률):** {R0} mcg/hr  
    - **Vd (분포용적):** {row['V_d']} L/kg × {BODY_WEIGHT} kg = {V_d:.2f} L  
    - **Onset time:** {onset_time} hr  
    - **Patch duration:** {duration_hour} hr  
    - **Total simulation:** {total_hour} hr  
    - **End threshold:** {end_threshold} ng/ml
    - **Cmax:** {c_max} ng/ml
    """)
    plot_patch_concentration(result)
