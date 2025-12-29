import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURACIÓN ---
file_id = '1ci-O6IP6CPOcLVT2VPvHp241LjTJQhRfnjgLqTol7CY'
url = f'https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx'

def extraer_datos_mes_final(df_raw, nombre_mes):
    try:
        # 1. Localizar la fila donde está el nombre del mes
        idx_mes = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains(f"^{nombre_mes}$", case=False).any(), axis=1)].index
        if idx_mes.empty: return pd.DataFrame()
        
        inicio = idx_mes[0]
        # 2. Buscar la fila de encabezados (la que tiene 'RADIÓLOGOS') debajo del mes
        bloque = df_raw.iloc[inicio : inicio + 15]
        fila_encabezados = bloque[bloque.apply(lambda row: row.astype(str).str.contains("RADIÓLOGOS", case=False).any(), axis=1)].index[0]
        
        # 3. Extraer datos y asignar nombres de columnas limpios
        df_mes = df_raw.iloc[fila_encabezados + 1 : fila_encabezados + 10].copy()
        df_mes.columns = [str(c).strip().upper() for c in df_raw.iloc[fila_encabezados]]
        
        # 4. LIMPIEZA CRÍTICA: Eliminar filas donde el nombre es "RADIÓLOGOS" o "TOTAL" o NaN
        df_mes = df_mes.dropna(subset=[df_mes.columns[0]])
        col_nombre = df_mes.columns[0]
        df_mes = df_mes[~df_mes[col_nombre].str.contains("RADIÓLOGOS|TOTAL|NAN", case=False, na=False)]
        
        return df_mes
    except Exception:
        return pd.DataFrame()

try:
    df_raw = pd.read_excel(url, header=None)
    meses_nombres = ["MAYO", "JUNIO", "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
    
    # Obtener lista de radiólogos única
    df_ref = extraer_datos_mes_final(df_raw, "MAYO")
    if df_ref.empty: df_ref = extraer_datos_mes_final(df_raw, "JUNIO")
    radiologos = [r for r in df_ref.iloc[:, 0].unique() if str(r) != 'nan']

    fig = make_subplots(
        rows=4, cols=1, vertical_spacing=0.07,
        subplot_titles=("Informes Realizados", "Tendencia: Informes", "Cumplimiento (%)", "Tendencia: % Cumplimiento"),
        specs=[[{"type": "bar"}], [{"type": "scatter"}], [{"type": "bar"}], [{"type": "scatter"}]]
    )

    hist_realizados = {r: [] for r in radiologos}
    hist_pct = {r: [] for r in radiologos}

    for mes in meses_nombres:
        df_m = extraer_datos_mes_final(df_raw, mes)
        
        if not df_m.empty:
            # Convertir columnas a números forzando errores a NaN, luego a 0
            realizados = pd.to_numeric(df_m["TOTAL DE INFORMES REALIZADOS"], errors='coerce').fillna(0)
            # Manejo de porcentajes (si vienen como 0.45 o como string "45%")
            pct_raw = df_m["PORCENTAJE COMPLETADO"].astype(str).str.replace('%', '')
            pct = pd.to_numeric(pct_raw, errors='coerce').fillna(0)
            # Si el valor es > 1, asumimos que ya es porcentaje (ej: 45), si es < 1, multiplicamos por 100
            pct = pct.apply(lambda x: x*100 if x < 1 and x > 0 else x)

            # Barras (Visibles para JUNIO por defecto)
            fig.add_trace(go.Bar(x=df_m.iloc[:, 0], y=realizados, name=f"R {mes}", 
                                 visible=(mes=="JUNIO"), marker_color='#2ecc71', text=realizados, textposition='outside'), row=1, col=1)
            fig.add_trace(go.Bar(x=df_m.iloc[:, 0], y=pct, name=f"C {mes}", 
                                 visible=(mes=="JUNIO"), marker_color='#3498db', text=pct.round(1), textposition='outside'), row=3, col=1)

            # Llenar históricos
            for r in radiologos:
                val_r = df_m[df_m.iloc[:, 0] == r]
                if not val_r.empty:
                    val_inf = pd.to_numeric(val_r["TOTAL DE INFORMES REALIZADOS"], errors='coerce').fillna(0).iloc[0]
                    val_p = pd.to_numeric(val_r["PORCENTAJE COMPLETADO"].astype(str).str.replace('%',''), errors='coerce').fillna(0).iloc[0]
                    val_p = val_p*100 if val_p < 1 and val_p > 0 else val_p
                    hist_realizados[r].append(val_inf)
                    hist_pct[r].append(val_p)
                else:
                    hist_realizados[r].append(0)
                    hist_pct[r].append(0)

    # Scatters
    for r in radiologos:
        fig.add_trace(go.Scatter(x=meses_nombres, y=hist_realizados[r], name=r, mode='lines+markers'), row=2, col=1)
        fig.add_trace(go.Scatter(x=meses_nombres, y=hist_pct[r], name=r, mode='lines+markers'), row=4, col=1)

    # Botones
    botones = []
    for i, mes in enumerate(meses_nombres):
        m_vis = [False] * len(fig.data)
        m_vis[i] = True # Bar 1
        m_vis[len(meses_nombres) + i] = True # Bar 2
        m_vis[-(2 * len(radiologos)):] = [True] * (2 * len(radiologos)) # Scatters
        botones.append(dict(label=f"MES: {mes}", method="update", args=[{"visible": m_vis}]))

    fig.update_layout(updatemenus=[dict(active=1, buttons=botones, x=0.01, y=1.03)], 
                      height=2000, title="<b>CONTROL RADIÓLOGOS v3.0</b>", template='plotly_white')
    
    #fig.show()
    fig.write_html("index.html", full_html=True, include_plotlyjs='cdn')
    print("¡Archivo index.html generado con éxito!")

except Exception as e:
    print(f"Error detectado: {e}")
