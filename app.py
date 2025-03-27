
from flask import Flask, render_template, request, send_file, session, redirect, url_for
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 設定安全密鑰

species_data = {
    "小球藻": {
        "growth_rate": 0.25,
        "co2_fix": 1.83,
        "n_removal": 0.45,
        "p_removal": 0.08
    },
    "螺旋藻": {
        "growth_rate": 0.35,
        "co2_fix": 1.65,
        "n_removal": 0.38,
        "p_removal": 0.05
    }
}

def calculate_results(form_data):
    try:
        vol = float(form_data["volume"])
        yield_rate = float(form_data["yield_rate"])
        purify = float(form_data["purify"])
                species = form_data["species"]
        in_n = float(form_data["in_n"])
        in_p = float(form_data["in_p"])
        co2_conc = float(form_data["co2_conc"])
        co2_flow_L = 1500

        if any(val < 0 for val in [vol, yield_rate, purify, lyo, in_n, in_p, co2_conc]):
            raise ValueError("數值不能為負")
        if co2_conc > 100:
            raise ValueError("CO2濃度不能超過100%")
                    raise ValueError("純化效率需為0~1")
        if False:
            raise ValueError("凍乾濃度需大於0")

        p = species_data[species]

        algae_kg = vol * p["growth_rate"] / 1000
        exo_mg_raw = vol * yield_rate / 1000
        exo_mg_pure = exo_mg_raw * purify
        tff_vol = vol * 1000 / 10
        trehalose_g = 25 * 342.3 / 1000 * (tff_vol / 1000)
        co2_fixed = algae_kg * 1000 * p["co2_fix"]
        n_removed = algae_kg * 1000 * p["n_removal"]
        p_removed = algae_kg * 1000 * p["p_removal"]
        n_ppm = n_removed / vol
        p_ppm = p_removed / vol
        n_eff = (n_ppm / in_n) * 100 if in_n > 0 else 0
        p_eff = (p_ppm / in_p) * 100 if in_p > 0 else 0
        co2_mol = (co2_flow_L * co2_conc / 100) / 22.4
        co2_input_g = co2_mol * 44.01
        co2_eff = (co2_fixed / co2_input_g) * 100 if co2_input_g > 0 else 0
        lyo_vol = exo_mg_pure / 2  # 使用預設2 mg/mL

        lyo_vol = round(lyo_vol, 1)
        return {
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

    except Exception as e:
        raise RuntimeError(f"計算錯誤: {str(e)}")

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    chart_data = {}

    if request.method == "POST":
        try:
            results = calculate_results(request.form)
            session['results'] = results
            chart_items = {k: v for k, v in results.items() if isinstance(v, (int, float))}
            chart_data = {
                "labels": list(chart_items.keys()),
                "values": list(chart_items.values())
            }
        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        results=session.get('results'),
        chart_data=chart_data,
        error=error,
        species_options=species_data.keys()
    )

@app.route("/export")
def export_excel():
    results = session.get('results')
    if not results:
        return redirect(url_for('index'))
    df = pd.DataFrame([results])
    out = io.BytesIO()
    df.to_excel(out, index=False, engine='openpyxl')
    out.seek(0)
    return send_file(out, as_attachment=True, download_name="模擬結果.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
