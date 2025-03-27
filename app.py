from flask import Flask, render_template, request, send_file, session, redirect, url_for
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 设置安全密钥

species_data = {
    "小球藻": {
        "growth_rate": 0.25,   # 生長速率 (g/L/day)
        "co2_fix": 1.83,      # CO2固定量 (g/g藻生物量)
        "n_removal": 0.45,    # 氮去除量 (g/g藻生物量)
        "p_removal": 0.08     # 磷去除量 (g/g藻生物量)
    },
    "螺旋藻": {
        "growth_rate": 0.35,
        "co2_fix": 1.65,
        "n_removal": 0.38,
        "p_removal": 0.05
    }
}

def calculate_results(form_data):
    """处理计算逻辑，返回结果字典"""
    try:
        # 解析输入参数
        vol = float(form_data["volume"])          # 每日處理體積 (L/day)
        yield_rate = float(form_data["yield_rate"]) # 外泌體產率 (μg/L)
        purify = float(form_data["purify"])       # 純化效率 (小數形式 0~1)
        lyo = float(form_data["lyo"])             # 凍乾產率 (mg/mL)
        species = form_data["species"]
        in_n = float(form_data["in_n"])           # 進流氮濃度 (ppm)
        in_p = float(form_data["in_p"])           # 進流磷濃度 (ppm)
        co2_conc = float(form_data["co2_conc"])   # CO2濃度 (%)
        co2_flow_L = 1500                         # 每日進氣量 (L/day)

        # 輸入驗證
        if any(val < 0 for val in [vol, yield_rate, purify, lyo, in_n, in_p, co2_conc]):
            raise ValueError("數值不能為負")
        if co2_conc > 100:
            raise ValueError("CO2濃度不能超過100%")
        if purify > 1 or lyo > 1:
            raise ValueError("純化效率和凍乾產率需為小數形式（0~1）")

        # 獲取藻種參數
        species_params = species_data[species]

        # 核心計算邏輯
        algae_kg = vol * species_params["growth_rate"] / 1000  # kg/day
        exo_mg_raw = vol * yield_rate / 1000  # mg/day
        exo_mg_pure = exo_mg_raw * purify
        tff_vol = vol * 1000 / 10  # mL/day
        trehalose_g = 25 * 342.3 / 1000 * (tff_vol / 1000)
        co2_fixed = algae_kg * 1000 * species_params["co2_fix"]  # g/day
        
        # 營養鹽去除計算
        n_removed = algae_kg * 1000 * species_params["n_removal"]  # g/day
        p_removed = algae_kg * 1000 * species_params["p_removal"]
        n_ppm = n_removed / vol
        p_ppm = p_removed / vol
        
        # 效率計算
        n_eff = (n_ppm / in_n) * 100 if in_n > 0 else 0
        p_eff = (p_ppm / in_p) * 100 if in_p > 0 else 0
        
        # CO2效率計算
        co2_mol = (co2_flow_L * co2_conc / 100) / 22.4  # 假設標準狀態下
        co2_input_g = co2_mol * 44.01
        co2_eff = (co2_fixed / co2_input_g) * 100 if co2_input_g > 0 else 0

        # 凍乾體積計算
        lyo_vol = exo_mg_pure / lyo if lyo > 0 else 0

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
            
            # 生成圖表數據（排除非數值項目）
            chart_items = {k:v for k,v in results.items() if isinstance(v, (int, float))}
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
    """導出Excel文件路由"""
    results = session.get('results')
    if not results:
        return redirect(url_for('index'))
    
    # 創建DataFrame並轉換為Excel
    df = pd.DataFrame([results])
    out = io.BytesIO()
    df.to_excel(out, index=False, engine='openpyxl')
    out.seek(0)
    
    return send_file(
        out,
        as_attachment=True,
        download_name="模擬結果.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
