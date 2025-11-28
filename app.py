import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Planificación Jubilación Suiza", layout="wide")

st.title("🇨🇭 Planificador Financiero Familiar")
st.markdown("Simulador de Jubilación, Estrategia de Escudos y Protección Familiar.")

# --- 1. DATOS FIJOS ---
EDAD_ACTUAL = 43
EDAD_RETIRO = 65
EDAD_FINAL = 120

# PK DATOS
DATOS_PK = {
    'Standard': {
        'capital_meta': 786845, 'renta': 39960, 'costo_mensual': 634.55,
        'renta_viuda': 27123, 'renta_huerfano': 9044, 'capital_muerte': 176597 
    },
    'Medium': {
        'capital_meta': 864076, 'renta': 44004, 'costo_mensual': 889.40,
        'renta_viuda': 29865, 'renta_huerfano': 9958, 'capital_muerte': 176597 
    },
    'Plus': {
        'capital_meta': 941307, 'renta': 48060, 'costo_mensual': 1144.25,
        'renta_viuda': 32640, 'renta_huerfano': 10884, 'capital_muerte': 176597 
    }
}

# VIAC
APORTE_ANUAL_3A = 7056
CAPITAL_3A_ACTUAL = 3 * APORTE_ANUAL_3A # Aprox 21k

# --- SIDEBAR (CONTROLES) ---
st.sidebar.header("⚙️ Configuración")

gastos_mensuales = st.sidebar.slider('🛒 Gastos Hoy (CHF/mes)', 4000, 12000, 6700, 100)
nivel_pk = st.sidebar.selectbox('🏢 Nivel PK Empresa', ['Standard', 'Medium', 'Plus'], index=0)
aporte_etf = st.sidebar.slider('🚀 Aporte ETF Privado (CHF/mes)', 0, 5000, 1650, 50)
estrategia_retiro = st.sidebar.selectbox('🏦 Estrategia Retiro PK', ['100% Renta', 'Mixto 50/50', '100% Capital'], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Proyecciones")
inflacion_pct = st.sidebar.slider('🎈 Inflación Anual %', 0.0, 5.0, 2.0, 0.1)
ahv_pareja_proyectado = st.sidebar.slider('🇨🇭 AHV Pareja (Proy. 2047)', 1000, 3000, 2406, 1)
edad_herencia = st.sidebar.slider('⚰️ Edad Cálculo Herencia', 66, 110, 85, 1)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Rentabilidades")
r_acum = st.sidebar.slider('Pre-Jubilación (Acumulación) %', 1.0, 10.0, 6.8, 0.1)
r_retiro = st.sidebar.slider('Post-Jubilación (VT/Acciones) %', 0.0, 8.0, 4.0, 0.1)
r_bonos = st.sidebar.slider('Post-Jubilación (Bonos) %', 0.0, 5.0, 1.5, 0.1)
tax = st.sidebar.slider('Impuesto Retiro Capital %', 0.0, 15.0, 8.0, 0.5)


# --- LÓGICA ---
def calcular_deficit_futuro(edad_actual, gastos_base, ahv_base, renta_pk, inflacion, anios_inicio, duracion):
    deficit_total = 0
    for i in range(anios_inicio, anios_inicio + duracion):
        anos_desde_hoy = (edad_actual + i) - 43
        factor = (1 + inflacion)**anos_desde_hoy
        gasto = (gastos_base * 12) * factor
        # AVS Escalera
        pasos_bianuales = (anos_desde_hoy // 2) * 2
        factor_avs = (1 + inflacion)**pasos_bianuales
        ahv = ahv_base * factor_avs
        
        ingreso = ahv + renta_pk
        deficit_anual = gasto - ingreso
        if deficit_anual > 0:
            deficit_total += deficit_anual
    return deficit_total

# --- EJECUCIÓN ---
# Conversiones
inf_rate = inflacion_pct / 100
r_acum_anual = r_acum / 100
r_ret_anual = r_retiro / 100
r_bonos_anual = r_bonos / 100
tax_rate = tax / 100

# Datos Base
ahv_pareja_anual_base = ahv_pareja_proyectado * 12
ahv_individual_base = ahv_pareja_proyectado / 2.0
ahv_viuda_mes = ahv_individual_base * 0.80
ahv_huerfano_mes = ahv_individual_base * 0.40
ahv_viuda_anual = ahv_viuda_mes * 12
ahv_huerfano_anual = ahv_huerfano_mes * 12

pk_data = DATOS_PK[nivel_pk]
costo_plus = DATOS_PK['Plus']['costo_mensual']
ahorro_nomina = costo_plus - pk_data['costo_mensual']

# SECCIÓN 1: ESCUDO FAMILIAR
ingreso_viuda_total = pk_data['renta_viuda'] + ahv_viuda_anual
ingreso_huerfano_total = pk_data['renta_huerfano'] + ahv_huerfano_anual
ingreso_familiar_anual = ingreso_viuda_total + ingreso_huerfano_total
capital_seguro = pk_data['capital_muerte'] + CAPITAL_3A_ACTUAL + (aporte_etf * 24)

# SECCIÓN 2: SIMULACIÓN
tabla_datos = []
saldo_viac = CAPITAL_3A_ACTUAL
saldo_vt = 0 
saldo_bonos = 0
saldo_sparkonto = 0
aporte_etf_anual = aporte_etf * 12 
cuentas_viac_restantes = 5
saldo_por_cuenta_viac_ref = 0
edad_quiebra = None

for edad in range(EDAD_ACTUAL, EDAD_FINAL + 1):
    fila = {'Edad': edad}
    year_index = edad - EDAD_ACTUAL
    
    factor_inflacion_anual = (1 + inf_rate)**year_index
    gasto_nominal_anual = (gastos_mensuales * 12) * factor_inflacion_anual
    
    pasos_bianuales = (year_index // 2) * 2
    factor_inflacion_avs = (1 + inf_rate)**pasos_bianuales
    avs_nominal_anual = ahv_pareja_anual_base * factor_inflacion_avs
    
    if estrategia_retiro == '100% Renta': renta_pk = pk_data['renta']
    elif estrategia_retiro == '100% Capital': renta_pk = 0
    else: renta_pk = pk_data['renta'] / 2
        
    ingresos_fijos = 0

    # FASE 1
    if edad < EDAD_RETIRO:
        saldo_viac = (saldo_viac + APORTE_ANUAL_3A) * (1 + r_acum_anual)
        saldo_vt = (saldo_vt + aporte_etf_anual) * (1 + r_acum_anual)
        saldo_pk = pk_data['capital_meta'] * ((year_index + 1) / (EDAD_RETIRO - EDAD_ACTUAL))
        
        fila.update({
            'PATRIMONIO VIAC': saldo_viac, 'PATRIMONIO 2ND PILAR': saldo_pk, 
            'RETIRADA BRUTA VIAC': 0, 'IMPUESTO VIAC': 0, 'RETIRADA BRUTA PK': 0, 'IMPUESTO PK': 0,
            'INYECCION A SPARKONTO': 0, 'INYECCION A BONOS': 0, 'INYECCION A VT': 0,
            'SALDO SPARKONTO (SEGURIDAD)': 0, 'SALDO BONOS (SEGURIDAD MEDIA)': 0, 'SALDO VT (RIESGO)': saldo_vt,
            'GASTO REAL ANUAL': gasto_nominal_anual, 
            'AVS ANUAL': 0, 'RENTA PK ANUAL': 0, 'TOTAL INGRESOS FIJOS': 0
        })

    # FASE 2
    else:
        ingresos_fijos = avs_nominal_anual + renta_pk
        dinero_entrante_neto = 0
        impuestos_pagados = 0
        retirada_bruta_viac = 0
        impuesto_viac = 0
        retirada_bruta_pk = 0
        impuesto_pk = 0
        
        # VIAC
        if 65 <= edad <= 69 and cuentas_viac_restantes > 0:
            if edad == EDAD_RETIRO: saldo_por_cuenta_viac_ref = saldo_viac / 5
            monto = saldo_por_cuenta_viac_ref
            if monto > saldo_viac: monto = saldo_viac
            saldo_viac -= monto
            cuentas_viac_restantes -= 1
            if saldo_viac > 0:
                saldo_viac *= (1 + r_acum_anual)
                if cuentas_viac_restantes > 0: saldo_por_cuenta_viac_ref = saldo_viac / cuentas_viac_restantes
            retirada_bruta_viac = monto
            impuesto_viac = monto * (tax_rate * 0.8)
            dinero_entrante_neto += (monto - impuesto_viac)

        # PK
        saldo_pk_visual = 0
        if edad == EDAD_RETIRO:
            cap_pk = 0
            if estrategia_retiro == '100% Capital': cap_pk = pk_data['capital_meta']
            elif estrategia_retiro == 'Mixto 50/50': cap_pk = pk_data['capital_meta'] / 2
            if cap_pk > 0:
                retirada_bruta_pk = cap_pk
                impuesto_pk = cap_pk * tax_rate
                dinero_entrante_neto += (cap_pk - impuesto_pk)
        
        if estrategia_retiro != '100% Capital':
            saldo_pk_visual = pk_data['capital_meta'] if estrategia_retiro == '100% Renta' else pk_data['capital_meta']/2

        # CASCADA
        deficit_actual = gasto_nominal_anual - ingresos_fijos
        target_sparkonto = calcular_deficit_futuro(edad, gastos_mensuales, ahv_pareja_anual_base, renta_pk, inf_rate, 0, 3)
        target_bonos = calcular_deficit_futuro(edad, gastos_mensuales, ahv_pareja_anual_base, renta_pk, inf_rate, 3, 5)
        
        falta_sparkonto = max(0, target_sparkonto - saldo_sparkonto)
        iny_sparkonto = 0; iny_bonos = 0; iny_vt = 0
        remanente = dinero_entrante_neto
        
        if remanente > 0:
            if remanente >= falta_sparkonto:
                iny_sparkonto = falta_sparkonto; remanente -= falta_sparkonto
            else:
                iny_sparkonto = remanente; remanente = 0
        
        falta_bonos = max(0, target_bonos - saldo_bonos)
        if remanente > 0:
            if remanente >= falta_bonos:
                iny_bonos = falta_bonos; remanente -= falta_bonos
            else:
                iny_bonos = remanente; remanente = 0
        
        if remanente > 0: iny_vt = remanente
        
        saldo_sparkonto += iny_sparkonto
        saldo_bonos += iny_bonos
        saldo_vt += iny_vt
        
        if deficit_actual > 0:
            if saldo_sparkonto >= deficit_actual:
                saldo_sparkonto -= deficit_actual
            else:
                restante = deficit_actual - saldo_sparkonto
                saldo_sparkonto = 0
                if saldo_bonos >= restante:
                    saldo_bonos -= restante
                else:
                    restante -= saldo_bonos
                    saldo_bonos = 0
                    saldo_vt -= restante
        
        saldo_vt *= (1 + r_ret_anual)
        saldo_bonos *= (1 + r_bonos_anual)
        
        if (saldo_vt + saldo_bonos + saldo_sparkonto) < 0:
            if edad_quiebra is None: edad_quiebra = edad
            saldo_vt = 0; saldo_bonos = 0; saldo_sparkonto = 0

        fila.update({
            'PATRIMONIO VIAC': saldo_viac, 'PATRIMONIO 2ND PILAR': saldo_pk_visual, 
            'RETIRADA BRUTA VIAC': retirada_bruta_viac, 'IMPUESTO VIAC': impuesto_viac,
            'RETIRADA BRUTA PK': retirada_bruta_pk, 'IMPUESTO PK': impuesto_pk,
            'INYECCION A SPARKONTO': iny_sparkonto, 'INYECCION A BONOS': iny_bonos, 'INYECCION A VT': iny_vt,
            'SALDO SPARKONTO (SEGURIDAD)': saldo_sparkonto, 'SALDO BONOS (SEGURIDAD MEDIA)': saldo_bonos, 'SALDO VT (RIESGO)': saldo_vt,
            'GASTO REAL ANUAL': gasto_nominal_anual, 
            'AVS ANUAL': avs_nominal_anual, 'RENTA PK ANUAL': renta_pk, 'TOTAL INGRESOS FIJOS': ingresos_fijos
        })
    
    tabla_datos.append(fila)

df = pd.DataFrame(tabla_datos)

# --- DISPLAY ---
fila_h = df[df['Edad'] == edad_herencia].iloc[0]
herencia_val = fila_h['SALDO VT (RIESGO)'] + fila_h['SALDO BONOS (SEGURIDAD MEDIA)'] + fila_h['SALDO SPARKONTO (SEGURIDAD)'] + fila_h['PATRIMONIO VIAC']
col_h = "#3498db" if herencia_val > 0 else "#e74c3c"
tit_st = f"⚠️ AGOTADO A LOS {edad_quiebra}" if edad_quiebra else "✅ SOSTENIBLE (>120 AÑOS)"
col_st = "#e74c3c" if edad_quiebra else "#27ae60"

st.markdown(f"""
<div style="background-color:#d6eaf8; padding:15px; border-radius:10px; border-left: 6px solid #3498db; margin-bottom:20px;">
    <h3 style="margin:0; color:#2c3e50;">🛡️ ESCUDO FAMILIAR (Si falleces HOY - Nivel {nivel_pk})</h3>
    <div style="display:flex; flex-wrap:wrap; gap:20px; margin-top:10px;">
        <div><b>RENTA MENSUAL (Viuda + Hijo):</b><br><span style="font-size:22px; color:#2980b9;">{ingreso_familiar_anual/12:,.0f} CHF</span></div>
        <div><b>CAPITAL INMEDIATO:</b><br><span style="font-size:22px; color:#27ae60;">{capital_seguro:,.0f} CHF</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div style="background-color:{col_st}; padding:20px; border-radius:10px; color:white; text-align:center;">
        <h3>{tit_st}</h3>
        <p>Estado del Plan de Jubilación</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div style="background-color:{col_h}; padding:20px; border-radius:10px; color:white; text-align:center;">
        <h3>{herencia_val:,.0f} CHF</h3>
        <p>Herencia a los {edad_herencia} años</p>
    </div>
    """, unsafe_allow_html=True)

# GRÁFICO 1
fig, ax = plt.subplots(figsize=(10, 5))
ax.stackplot(df['Edad'], 
              df['SALDO SPARKONTO (SEGURIDAD)'], 
              df['SALDO BONOS (SEGURIDAD MEDIA)'], 
              df['SALDO VT (RIESGO)'], 
              labels=['Sparkonto (Cash)', 'Bonos (5 Años)', 'VT (Crecimiento)'], 
              colors=['#3498db', '#f1c40f', '#2ecc71'], alpha=0.8)
total_liq = df['SALDO SPARKONTO (SEGURIDAD)'] + df['SALDO BONOS (SEGURIDAD MEDIA)'] + df['SALDO VT (RIESGO)']
ax.fill_between(df['Edad'], total_liq, total_liq + df['PATRIMONIO VIAC'], color='orange', alpha=0.3, label='VIAC (Pendiente)')
if estrategia_retiro != '100% Capital':
    ax.plot(df['Edad'], df['PATRIMONIO 2ND PILAR'], color='navy', linestyle='--', alpha=0.4, label='Capital PK')
ax.axvline(65, color='black', linestyle=':')
ax.axvline(edad_herencia, color='blue', linewidth=2)
ax.set_title("Evolución de los 3 Cubos de Dinero")
ax.legend(loc='upper left')
ax.grid(True, alpha=0.3)
st.pyplot(fig)

# GRÁFICO 2
fig2, ax2 = plt.subplots(figsize=(10, 5))
df_ret = df[df['Edad'] >= 65]
ingreso_tot = df_ret['TOTAL INGRESOS FIJOS']
ax2.plot(df_ret['Edad'], df_ret['GASTO REAL ANUAL'], color='#c0392b', linewidth=3, label='Gasto Real')
ax2.plot(df_ret['Edad'], ingreso_tot, color='#2980b9', linewidth=2, linestyle='--', label='Ingresos Fijos')
ax2.fill_between(df_ret['Edad'], ingreso_tot, df_ret['GASTO REAL ANUAL'], where=(df_ret['GASTO REAL ANUAL']>ingreso_tot), color='red', alpha=0.1, label='Déficit')
ax2.set_title("Flujo de Caja (Ingresos vs Gastos Reales)")
ax2.legend()
ax2.grid(True, alpha=0.3)
st.pyplot(fig2)

# TABLA
st.subheader("Detalle Año a Año")
cols_show = ['Edad', 'PATRIMONIO VIAC', 
            'RETIRADA BRUTA VIAC', 'IMPUESTO VIAC', 
            'INYECCION A SPARKONTO', 'INYECCION A BONOS', 'INYECCION A VT',
            'SALDO SPARKONTO (SEGURIDAD)', 'SALDO BONOS (SEGURIDAD MEDIA)', 'SALDO VT (RIESGO)',
            'GASTO REAL ANUAL', 'TOTAL INGRESOS FIJOS']
st.dataframe(df[cols_show].style.format("{:,.0f}"), use_container_width=True)
