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
    results = None
    chart_data = {}
    if request.method == "POST":
        volume = float(request.form["volume"])
        yield_ = float(request.form["yield"])
        purify = float(request.form["purify"])
        lyo = float(request.form["lyo"])
        species = request.form["species"]
        p = species_data[species]

        algae_kg = volume * p["growth_rate"] / 1000
        exo_mg_raw = volume * yield_ / 1000
        exo_mg_pure = exo_mg_raw * purify
        tff_volume = volume * 1000 / 10
        trehalose_g = 25 * 342.3 / 1000 * (tff_volume / 1000)
        co2_g = algae_kg * 1000 * p["co2_fix"]
        n_g = algae_kg * 1000 * p["n_removal"]
        p_g = algae_kg * 1000 * p["p_removal"]
        lyo_vol = exo_mg_pure / lyo if lyo > 0 else 0

        results = {
            "藻種": species,
            "藻泥產量 (kg)": round(algae_kg, 2),
            "CO2 捕捉量 (g)": round(co2_g, 2),
            "氮去除量 (g)": round(n_g, 2),
            "磷去除量 (g)": round(p_g, 2),
            "外泌體原始產量 (mg)": round(exo_mg_raw, 2),
            "純化後外泌體 (mg)": round(exo_mg_pure, 2),
            "濃縮後體積 (mL)": round(tff_volume, 1),
            "保存液 Trehalose 使用量 (g)": round(trehalose_g, 2),
            "凍乾分裝體積 (mL)": round(lyo_vol, 1)
        }

        chart_data = {
            "labels": list(results.keys())[1:],  # 不含藻種
            "values": list(results.values())[1:]
        }

    return render_template("index.html", results=results, chart_data=chart_data, species_options=species_data.keys())

@app.route("/export", methods=["POST"])
def export_excel():
    data = request.form.to_dict()
    df = pd.DataFrame([data])
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="simulation_result.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    app.run(debug=True)
