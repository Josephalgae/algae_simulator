
from flask import Flask, render_template, request, send_file
import pandas as pd
import io

app = Flask(__name__)

species_data = {
    "小球藻": {"growth_rate": 0.25, "co2_fix": 1.83, "n_removal": 0.45, "p_removal": 0.08},
    "螺旋藻": {"growth_rate": 0.35, "co2_fix": 1.65, "n_removal": 0.38, "p_removal": 0.05}
}

@app.route("/", methods=["GET", "POST"])
def index():
    results, chart_data = None, {}
    if request.method == "POST":
        vol = float(request.form["volume"])  # L/day
        yield_rate = float(request.form["yield_rate"])  # ug/L
        purify = float(request.form["purify"])
        lyo = float(request.form["lyo"])
        species = request.form["species"]
        in_n = float(request.form["in_n"])
        in_p = float(request.form["in_p"])
        co2_conc = float(request.form["co2_conc"])  # %
        co2_flow_L = 1500  # 預設每天進氣量 1500 L/day

        p = species_data[species]
        algae_kg = vol * p["growth_rate"] / 1000
        exo_mg_raw = vol * yield_ / 1000
        exo_mg_pure = exo_mg_raw * purify
        tff_vol = vol * 1000 / 10
        trehalose_g = 25 * 342.3 / 1000 * (tff_vol / 1000)
        co2_fixed = algae_kg * 1000 * p["co2_fix"]
        n_removed = algae_kg * 1000 * p["n_removal"]
        p_removed = algae_kg * 1000 * p["p_removal"]
        lyo_vol = exo_mg_pure / lyo if lyo > 0 else 0

        n_ppm = n_removed / vol
        p_ppm = p_removed / vol
        n_eff = (n_ppm / in_n) * 100 if in_n > 0 else 0
        p_eff = (p_ppm / in_p) * 100 if in_p > 0 else 0

        # CO2 理論進氣量（g/day）
        co2_mol = (co2_flow_L * co2_conc / 100) / 22.4  # mol/day
        co2_input_g = co2_mol * 44.01
        co2_eff = (co2_fixed / co2_input_g) * 100 if co2_input_g > 0 else 0

        results = {
            "藻種": species,
            "藻泥產量 (kg/day)": round(algae_kg, 2),
            "外泌體原始產量 (mg/day)": round(exo_mg_raw, 2),
            "純化後外泌體 (mg/day)": round(exo_mg_pure, 2),
            "濃縮後體積 (mL/day)": round(tff_vol, 1),
            "保存液 Trehalose 使用量 (g/day)": round(trehalose_g, 2),
            "凍乾分裝體積 (mL/day)": round(lyo_vol, 1),
            "CO2 捕捉量 (g/day)": round(co2_fixed, 2),
            "CO2 去除效率 (%)": round(co2_eff, 1),
            "氮去除量 (ppm/day)": round(n_ppm, 2),
            "磷去除量 (ppm/day)": round(p_ppm, 2),
            "氮去除效率 (%)": round(n_eff, 1),
            "磷去除效率 (%)": round(p_eff, 1)
        }

        chart_data = {
            "labels": list(results.keys())[1:],  # skip 藻種
            "values": list(results.values())[1:]
        }

    return render_template("index.html", results=results, chart_data=chart_data, species_options=species_data.keys())

@app.route("/export", methods=["POST"])
def export_excel():
    df = pd.DataFrame([request.form.to_dict()])
    out = io.BytesIO()
    df.to_excel(out, index=False, engine='openpyxl')
    out.seek(0)
    return send_file(out, as_attachment=True, download_name="simulation_result.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
