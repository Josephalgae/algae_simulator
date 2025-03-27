
from flask import Flask, render_template, request, send_file, session, redirect, url_for
import pandas as pd
import io
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ========= 微藻藻種參數 ========= #
species_data = {
    "小球藻": {
        "growth_rate": 0.25,   # g/L/day
        "co2_fix": 1.83,       # g CO₂ / g biomass
        "n_removal": 0.45,     # g N / g biomass
        "p_removal": 0.08,
        "co2_recommend_m3": 1.5  # m³/day 建議供氣量
    },
    "螺旋藻": {
        "growth_rate": 0.35,
        "co2_fix": 1.65,
        "n_removal": 0.38,
        "p_removal": 0.05,
        "co2_recommend_m3": 2.0
    }
}

# ========= CO₂ 固定計算公式 ========= #
def calculate_co2_removal(mu, X, V, C=0.5, Q_co2=None):
    co2_fixation = mu * X * V * C * (44 / 12)
    efficiency = (co2_fixation / Q_co2) * 100 if Q_co2 else None
    return {
        "co2_fixation_g_per_day": round(co2_fixation, 2),
        "removal_efficiency_percent": round(efficiency, 2) if efficiency is not None else None
    }

# ========= 主邏輯 ========= #
@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    chart_data = {}
    results = {}
    if request.method == "POST":
        try:
            # 讀取表單數值
            vol = float(request.form["volume"])
            yield_rate = float(request.form["yield_rate"])
            purify = float(request.form["purify"])
            in_n = float(request.form["in_n"])
            in_p = float(request.form["in_p"])
            co2_conc = float(request.form["co2_conc"])
            co2_flow_m3 = float(request.form["co2_flow_m3"])  # 新增：m³/day
            species = request.form["species"]

            if any(x < 0 for x in [vol, yield_rate, purify, in_n, in_p, co2_conc, co2_flow_m3]):
                raise ValueError("輸入值不得為負")
            if purify > 1 or co2_conc > 100:
                raise ValueError("純化效率需為 0~1，CO₂ 濃度不得超過 100%")

            p = species_data[species]
            algae_kg = vol * p["growth_rate"] / 1000
            exo_mg_raw = vol * yield_rate / 1000
            exo_mg_pure = exo_mg_raw * purify
            tff_vol = vol * 1000 / 10
            trehalose_g = 25 * 342.3 / 1000 * (tff_vol / 1000)
            lyo_vol = exo_mg_pure / 2

            # 氮磷計算
            n_removed = algae_kg * 1000 * p["n_removal"]
            p_removed = algae_kg * 1000 * p["p_removal"]
            n_ppm = n_removed / vol
            p_ppm = p_removed / vol
            n_eff = (n_ppm / in_n) * 100 if in_n else 0
            p_eff = (p_ppm / in_p) * 100 if in_p else 0

            # 計算 CO₂ 去除效率（使用 m³/day 單位換算）
            co2_flow_L = co2_flow_m3 * 1000
            co2_mol = (co2_flow_L * co2_conc / 100) / 22.4
            co2_input_g = co2_mol * 44.01
            X = (algae_kg * 1000) / vol
            co2_result = calculate_co2_removal(p["growth_rate"], X, vol, Q_co2=co2_input_g)
            co2_eff = min(co2_result["removal_efficiency_percent"], 100)
            co2_fixed = co2_result["co2_fixation_g_per_day"]

            results = {
                "藻種": species,
                "建議進氣量 (m³/day)": p["co2_recommend_m3"],
                "使用者輸入進氣量 (m³/day)": co2_flow_m3,
                "藻泥產量 (kg/day)": round(algae_kg, 2),
                "外泌體原始產量 (mg/day)": round(exo_mg_raw, 2),
                "純化後外泌體 (mg/day)": round(exo_mg_pure, 2),
                "濃縮後體積 (mL/day)": round(tff_vol, 1),
                "保存液 Trehalose 使用量 (g/day)": round(trehalose_g, 2),
                "凍乾分裝體積 (mL/day)": round(lyo_vol, 1),
                "CO2 捕捉量 (g/day)": co2_fixed,
                "CO2 去除效率 (%)": co2_eff,
                "氮去除量 (ppm/day)": round(n_ppm, 2),
                "磷去除量 (ppm/day)": round(p_ppm, 2),
                "氮去除效率 (%)": round(n_eff, 1),
                "磷去除效率 (%)": round(p_eff, 1)
            }

            session['results'] = results
            chart_data = {
                "labels": [k for k, v in results.items() if isinstance(v, (int, float))],
                "values": [v for v in results.values() if isinstance(v, (int, float))]
            }

        except Exception as e:
            error = str(e)

    return render_template("index.html", results=session.get("results"), chart_data=chart_data, error=error, species_options=species_data.keys())

@app.route("/export")
def export_excel():
    results = session.get("results")
    if not results:
        return redirect(url_for("index"))
    df = pd.DataFrame([results])
    out = io.BytesIO()
    df.to_excel(out, index=False, engine='openpyxl')
    out.seek(0)
    return send_file(out, as_attachment=True, download_name="模擬結果.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
