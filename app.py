import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ================================================================
# CONFIG
# ================================================================
st.set_page_config(page_title="Planificación Jubilación Suiza", layout="wide")
st.title("🇨🇭 Planificador Financiero Familiar")
st.markdown("Simulador de Jubilación, Estrategia de Escudos y Protección Familiar.")

EDAD_ACTUAL = 43
EDAD_RETIRO = 65
EDAD_FINAL = 120

# Puntos PK (extracto real)
PK_PUNTOS_A = {43: 152030, 58: 569666, 59: 605705, 60: 642196, 61: 679142, 62: 716550, 63: 754426, 64: 792775, 65: 831603}
PK_PUNTOS_B = {43: 152030, 58: 623156, 59: 666095, 60: 710001, 61: 754895, 62: 800799, 63: 847736, 64: 895729, 65: 944801}

def interpolar_pk(puntos_ref, factor_sal):
    """Interpolación lineal entre puntos conocidos del PK, escalada por salario."""
    edades = sorted(puntos_ref.keys())
    valores = [puntos_ref[e] * factor_sal for e in edades]
    todas_edades = list(range(EDAD_ACTUAL, EDAD_RETIRO + 1))
    interpolado = np.interp(todas_edades, edades, valores)
    return {e: v for e, v in zip(todas_edades, interpolado)}

# Tasas contribución empleado (EE)
TASAS_EE = {
    'Standard': {'E1_ahorro': 3.70, 'E1_riesgo': 1.00, 'E2_ahorro': 4.40, 'E2_riesgo': 1.60, 'CSP': 1.00},
    'Medium':   {'E1_ahorro': 6.00, 'E1_riesgo': 1.00, 'E2_ahorro': 6.70, 'E2_riesgo': 1.60, 'CSP': 1.00},
    'Plus':     {'E1_ahorro': 8.30, 'E1_riesgo': 1.00, 'E2_ahorro': 9.00, 'E2_riesgo': 1.60, 'CSP': 1.00},
}

# Referencias Portal (salario ref 142'271)
CAPITAL_META_REF = {'Standard': 831603, 'Medium': 913174, 'Plus': 994745}
RENTA_REF = {'Standard': 42024, 'Medium': 46260, 'Plus': 50508}
SALARIO_REF = 142271

# Prestaciones riesgo (escala salario)
RENTA_VIUDA_REF = 35424
RENTA_HUERFANO_REF = 11808
CAPITAL_MUERTE_REF = 188492

# VIAC
APORTE_ANUAL_3A = 7056
CAPITAL_3A_ACTUAL = 3 * APORTE_ANUAL_3A

def calc_contribuciones_ee(e1, e2, tasas):
    e1_total_pct = tasas['E1_ahorro'] + tasas['E1_riesgo']
    e2_total_pct = tasas['E2_ahorro'] + tasas['E2_riesgo']
    csp_pct = tasas['CSP']
    ee_e1 = e1 * e1_total_pct / 100 / 12
    ee_e2 = e2 * e2_total_pct / 100 / 12
    ee_csp = e1 * csp_pct / 100 / 12
    return ee_e1, ee_e2, ee_csp, ee_e1 + ee_e2 + ee_csp

def calc_pk_strategy(pk_data_capital, pk_data_renta, estrategia_retiro, tax_rate):
    """
    Devuelve:
    - cap_pk_bruto / impuesto / neto (según estrategia)
    - renta_pk_mensual (según estrategia)
    """
    if estrategia_retiro == '100% Capital':
        cap_pk_bruto = pk_data_capital
        cap_pk_impuesto = cap_pk_bruto * tax_rate
        cap_pk_neto = cap_pk_bruto - cap_pk_impuesto
        renta_pk_mensual = 0

    elif estrategia_retiro == 'Mixto 50/50':
        cap_pk_bruto = pk_data_capital / 2
        cap_pk_impuesto = cap_pk_bruto * tax_rate
        cap_pk_neto = cap_pk_bruto - cap_pk_impuesto
        renta_pk_mensual = (pk_data_renta / 2) / 12

    else:  # '100% Renta'
        cap_pk_bruto = 0
        cap_pk_impuesto = 0
        cap_pk_neto = 0
        renta_pk_mensual = pk_data_renta / 12

    return cap_pk_bruto, cap_pk_impuesto, cap_pk_neto, renta_pk_mensual

def calcular_deficit_futuro(edad_actual, gastos_base, ahv_base, renta_pk_anual, inflacion, anios_inicio, duracion):
    deficit_total = 0
    for i in range(anios_inicio, anios_inicio + duracion):
        anos_desde_hoy = (edad_actual + i) - EDAD_ACTUAL
        factor = (1 + inflacion) ** anos_desde_hoy
        gasto = (gastos_base * 12) * factor

        pasos_bianuales = (anos_desde_hoy // 2) * 2
        factor_avs = (1 + inflacion) ** pasos_bianuales
        ahv = ahv_base * factor_avs

        ingreso = ahv + renta_pk_anual
        deficit_anual = gasto - ingreso
        if deficit_anual > 0:
            deficit_total += deficit_anual
    return deficit_total

# ================================================================
# SIDEBAR
# ================================================================
st.sidebar.header("⚙️ Configuración")

st.sidebar.subheader("💰 Salario y PK")
salario = st.sidebar.number_input('Salario Bruto Anual (CHF)', 80000, 300000, SALARIO_REF, 1000)
tope_e1 = st.sidebar.number_input('Tope Salario E1 (CHF)', 50000, 200000, 120960, 100)
nivel_pk = st.sidebar.selectbox('🏢 Nivel PK Empresa', ['Standard', 'Medium', 'Plus'], index=0)
variante_pk = st.sidebar.selectbox('📊 Variante Interés PK', ['A (1.25%)', 'B (2.25%)'], index=0)
gastos_mensuales = st.sidebar.slider('🛒 Gastos Hoy (CHF/mes)', 4000, 12000, 6700, 100)

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Inversión Privada")
aporte_etf = st.sidebar.slider('Aporte Total Privado (CHF/mes)', 0, 5000, 1650, 50)
pct_oro = st.sidebar.slider('🥇 % Asignación a Oro', 0, 100, 0, 5)
estrategia_retiro = st.sidebar.selectbox('🏦 Estrategia Retiro PK', ['100% Renta', 'Mixto 50/50', '100% Capital'], index=2)

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Proyecciones")
inflacion_pct = st.sidebar.slider('🎈 Inflación Anual %', 0.0, 5.0, 2.0, 0.1)
ahv_pareja_proyectado = st.sidebar.slider('🇨🇭 AHV Pareja (Proy. 2047)', 1000, 3000, 2406, 1)
edad_herencia = st.sidebar.slider('⚰️ Edad Cálculo Herencia', 66, 110, 85, 1)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Rentabilidades")
r_acum = st.sidebar.slider('Pre-Jubilación (VT Acumulación) %', 1.0, 10.0, 6.8, 0.1)
r_oro_slider = st.sidebar.slider('Oro (Pre-Jubilación) %', 0.0, 10.0, 4.0, 0.1)
r_retiro = st.sidebar.slider('Post-Jubilación (VT) %', 0.0, 8.0, 4.0, 0.1)
r_oro_retiro = st.sidebar.slider('Post-Jubilación (Oro) %', 0.0, 8.0, 3.0, 0.1)
r_bonos = st.sidebar.slider('Post-Jubilación (Bonos) %', 0.0, 5.0, 1.5, 0.1)
tax = st.sidebar.slider('Impuesto Retiro Capital %', 0.0, 15.0, 8.0, 0.5)

# ================================================================
# INPUTS → DERIVADOS
# ================================================================
e1_salary = min(salario, tope_e1)
e2_salary = max(0, salario - tope_e1)
factor_salario = salario / SALARIO_REF

inf_rate = inflacion_pct / 100
r_acum_anual = r_acum / 100
r_oro_anual = r_oro_slider / 100
r_ret_anual = r_retiro / 100
r_oro_ret_anual = r_oro_retiro / 100
r_bonos_anual = r_bonos / 100
tax_rate = tax / 100

pct_vt = (100 - pct_oro) / 100
pct_oro_dec = pct_oro / 100
aporte_vt_anual = aporte_etf * pct_vt * 12
aporte_oro_anual = aporte_etf * pct_oro_dec * 12

ahv_pareja_anual_base = ahv_pareja_proyectado * 12
ahv_individual_base = ahv_pareja_proyectado / 2.0
ahv_viuda_anual = ahv_individual_base * 0.80 * 12
ahv_huerfano_anual = ahv_individual_base * 0.40 * 12

# Contribuciones EE por nivel
contribuciones = {}
for niv in ['Standard', 'Medium', 'Plus']:
    ee_e1, ee_e2, ee_csp, total = calc_contribuciones_ee(e1_salary, e2_salary, TASAS_EE[niv])
    contribuciones[niv] = {'E1': ee_e1, 'E2': ee_e2, 'CSP': ee_csp, 'Total': total}

# Escalado por salario
pk_capital_meta = {niv: CAPITAL_META_REF[niv] * factor_salario for niv in CAPITAL_META_REF}
pk_renta = {niv: RENTA_REF[niv] * factor_salario for niv in RENTA_REF}

renta_viuda = RENTA_VIUDA_REF * factor_salario
renta_huerfano = RENTA_HUERFANO_REF * factor_salario
capital_muerte = CAPITAL_MUERTE_REF * factor_salario

# Selección base PK según nivel
pk_data_capital = pk_capital_meta[nivel_pk]
pk_data_renta = pk_renta[nivel_pk]

# Interpolación curva PK (según variante)
pk_puntos_base = PK_PUNTOS_A if 'A' in variante_pk else PK_PUNTOS_B
pk_interpolado = interpolar_pk(pk_puntos_base, factor_salario)

# Ajuste simple si eliges Variante B (mantengo tu lógica original)
if 'B' in variante_pk:
    ratio_b_a = {'Standard': 944801 / 831603, 'Medium': 944801 / 831603, 'Plus': 944801 / 831603}
    pk_data_capital = pk_capital_meta[nivel_pk] * ratio_b_a[nivel_pk]
    pk_data_renta = pk_renta[nivel_pk] * (47736 / 42024)

# IMPORTANTÍSIMO: definir estrategia PK aquí (antes de cualquier uso posterior)
cap_pk_bruto, cap_pk_impuesto, cap_pk_neto, renta_pk_mensual = calc_pk_strategy(
    pk_data_capital, pk_data_renta, estrategia_retiro, tax_rate
)

# ================================================================
# ESCUDO FAMILIAR (HOY)
# ================================================================
ingreso_viuda_total = renta_viuda + ahv_viuda_anual
ingreso_huerfano_total = renta_huerfano + ahv_huerfano_anual
ingreso_familiar_anual = ingreso_viuda_total + ingreso_huerfano_total
capital_seguro = capital_muerte + CAPITAL_3A_ACTUAL + (aporte_etf * 24)

# ================================================================
# SIMULACIÓN (AÑO A AÑO)
# ================================================================
tabla_datos = []
saldo_viac = CAPITAL_3A_ACTUAL
saldo_vt = 0
saldo_oro = 0
saldo_bonos = 0
saldo_sparkonto = 0
cuentas_viac_restantes = 5
saldo_por_cuenta_viac_ref = 0
edad_quiebra = None

for edad in range(EDAD_ACTUAL, EDAD_FINAL + 1):
    fila = {'Edad': edad}
    year_index = edad - EDAD_ACTUAL

    factor_inflacion_anual = (1 + inf_rate) ** year_index
    gasto_nominal_anual = (gastos_mensuales * 12) * factor_inflacion_anual

    pasos_bianuales = (year_index // 2) * 2
    factor_inflacion_avs = (1 + inf_rate) ** pasos_bianuales
    avs_nominal_anual = ahv_pareja_anual_base * factor_inflacion_avs

    # renta_pk anual según estrategia
    if estrategia_retiro == '100% Renta':
        renta_pk_anual = pk_data_renta
    elif estrategia_retiro == '100% Capital':
        renta_pk_anual = 0
    else:
        renta_pk_anual = pk_data_renta / 2

    # FASE 1: ACUMULACIÓN
    if edad < EDAD_RETIRO:
        saldo_viac = (saldo_viac + APORTE_ANUAL_3A) * (1 + r_acum_anual)
        saldo_vt = (saldo_vt + aporte_vt_anual) * (1 + r_acum_anual)
        saldo_oro = (saldo_oro + aporte_oro_anual) * (1 + r_oro_anual)
        saldo_pk = pk_interpolado.get(edad, 0)

        fila.update({
            'PATRIMONIO VIAC': saldo_viac,
            'PATRIMONIO 2ND PILAR': saldo_pk,
            'RETIRADA BRUTA VIAC': 0, 'IMPUESTO VIAC': 0,
            'RETIRADA BRUTA PK': 0, 'IMPUESTO PK': 0,
            'INYECCION A SPARKONTO': 0, 'INYECCION A BONOS': 0, 'INYECCION A VT': 0, 'INYECCION A ORO': 0,
            'SALDO SPARKONTO': 0, 'SALDO BONOS': 0,
            'SALDO VT': saldo_vt, 'SALDO ORO': saldo_oro,
            'GASTO REAL ANUAL': gasto_nominal_anual,
            'AVS ANUAL': 0, 'RENTA PK ANUAL': 0, 'TOTAL INGRESOS FIJOS': 0
        })

    # FASE 2: RETIRO
    else:
        ingresos_fijos = avs_nominal_anual + renta_pk_anual
        dinero_entrante_neto = 0
        retirada_bruta_viac = 0
        impuesto_viac = 0
        retirada_bruta_pk = 0
        impuesto_pk = 0

        # VIAC escalonado (65-69)
        if 65 <= edad <= 69 and cuentas_viac_restantes > 0:
            if edad == EDAD_RETIRO:
                saldo_por_cuenta_viac_ref = saldo_viac / 5
            monto = min(saldo_por_cuenta_viac_ref, saldo_viac)
            saldo_viac -= monto
            cuentas_viac_restantes -= 1

            if saldo_viac > 0:
                saldo_viac *= (1 + r_acum_anual)
                if cuentas_viac_restantes > 0:
                    saldo_por_cuenta_viac_ref = saldo_viac / cuentas_viac_restantes

            retirada_bruta_viac = monto
            impuesto_viac = monto * (tax_rate * 0.8)
            dinero_entrante_neto += (monto - impuesto_viac)

        # PK capital (solo a los 65 si hay retiro de capital)
        saldo_pk_visual = 0
        if edad == EDAD_RETIRO:
            saldo_pk_visual = pk_data_capital  # mostrar al llegar a 65

            cap_pk = 0
            if estrategia_retiro == '100% Capital':
                cap_pk = pk_data_capital
            elif estrategia_retiro == 'Mixto 50/50':
                cap_pk = pk_data_capital / 2

            if cap_pk > 0:
                retirada_bruta_pk = cap_pk
                impuesto_pk = cap_pk * tax_rate
                dinero_entrante_neto += (cap_pk - impuesto_pk)

        if edad > EDAD_RETIRO and estrategia_retiro != '100% Capital':
            saldo_pk_visual = pk_data_capital if estrategia_retiro == '100% Renta' else pk_data_capital / 2

        # CUBOS
        deficit_actual = gasto_nominal_anual - ingresos_fijos
        target_sparkonto = calcular_deficit_futuro(edad, gastos_mensuales, ahv_pareja_anual_base, renta_pk_anual, inf_rate, 0, 3)
        target_bonos = calcular_deficit_futuro(edad, gastos_mensuales, ahv_pareja_anual_base, renta_pk_anual, inf_rate, 3, 5)

        falta_sparkonto = max(0, target_sparkonto - saldo_sparkonto)
        iny_sparkonto = 0; iny_bonos = 0; iny_vt = 0; iny_oro = 0
        remanente = dinero_entrante_neto

        # llenar sparkonto
        if remanente > 0:
            iny_sparkonto = min(remanente, falta_sparkonto)
            remanente -= iny_sparkonto

        # llenar bonos
        falta_bonos = max(0, target_bonos - saldo_bonos)
        if remanente > 0:
            iny_bonos = min(remanente, falta_bonos)
            remanente -= iny_bonos

        # resto a VT/Oro
        if remanente > 0:
            iny_vt = remanente * pct_vt
            iny_oro = remanente * pct_oro_dec

        saldo_sparkonto += iny_sparkonto
        saldo_bonos += iny_bonos
        saldo_vt += iny_vt
        saldo_oro += iny_oro

        # consumir déficit
        if deficit_actual > 0:
            restante = deficit_actual

            take = min(saldo_sparkonto, restante); saldo_sparkonto -= take; restante -= take
            take = min(saldo_bonos, restante); saldo_bonos -= take; restante -= take
            take = min(saldo_oro, restante); saldo_oro -= take; restante -= take
            saldo_vt -= restante

        # rentabilidades post-retiro
        saldo_vt *= (1 + r_ret_anual)
        saldo_oro *= (1 + r_oro_ret_anual)
        saldo_bonos *= (1 + r_bonos_anual)

        patrimonio_total = saldo_vt + saldo_oro + saldo_bonos + saldo_sparkonto
        if patrimonio_total < 0:
            if edad_quiebra is None:
                edad_quiebra = edad
            saldo_vt = saldo_oro = saldo_bonos = saldo_sparkonto = 0

        fila.update({
            'PATRIMONIO VIAC': saldo_viac,
            'PATRIMONIO 2ND PILAR': saldo_pk_visual,
            'RETIRADA BRUTA VIAC': retirada_bruta_viac,
            'IMPUESTO VIAC': impuesto_viac,
            'RETIRADA BRUTA PK': retirada_bruta_pk,
            'IMPUESTO PK': impuesto_pk,
            'INYECCION A SPARKONTO': iny_sparkonto,
            'INYECCION A BONOS': iny_bonos,
            'INYECCION A VT': iny_vt,
            'INYECCION A ORO': iny_oro,
            'SALDO SPARKONTO': saldo_sparkonto,
            'SALDO BONOS': saldo_bonos,
            'SALDO VT': saldo_vt,
            'SALDO ORO': saldo_oro,
            'GASTO REAL ANUAL': gasto_nominal_anual,
            'AVS ANUAL': avs_nominal_anual,
            'RENTA PK ANUAL': renta_pk_anual,
            'TOTAL INGRESOS FIJOS': ingresos_fijos
        })

    tabla_datos.append(fila)

df = pd.DataFrame(tabla_datos)

# ================================================================
# DISPLAY — SALARIO & PK
# ================================================================
st.subheader("💰 Salario y Contribuciones PK")

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1: st.metric("Salario Bruto", f"{salario:,.0f} CHF")
with col_s2: st.metric("Salario Asegurado E1", f"{e1_salary:,.0f} CHF")
with col_s3: st.metric("Salario Asegurado E2", f"{e2_salary:,.0f} CHF")

contrib_rows = []
for niv in ['Standard', 'Medium', 'Plus']:
    c = contribuciones[niv]
    marker = " ◀" if niv == nivel_pk else ""
    contrib_rows.append({
        'Nivel': f"{niv}{marker}",
        'E1 (CHF/mes)': f"{c['E1']:,.2f}",
        'E2 (CHF/mes)': f"{c['E2']:,.2f}",
        'CSP (CHF/mes)': f"{c['CSP']:,.2f}",
        'TOTAL EE (CHF/mes)': f"{c['Total']:,.2f}",
        'Capital Meta 65': f"{pk_capital_meta[niv]:,.0f}",
        'Renta Anual 65': f"{pk_renta[niv]:,.0f}",
    })
st.dataframe(pd.DataFrame(contrib_rows), use_container_width=True, hide_index=True)

if salario != SALARIO_REF:
    st.info(f"⚠️ Capital meta y rentas escalados proporcionalmente al salario (factor {factor_salario:.3f}). Para valores exactos, consulta el Portal PK.")

# ================================================================
# ESCUDO FAMILIAR (HOY)
# ================================================================
st.markdown("---")
st.markdown(f"""
<div style="background-color:#d6eaf8; padding:15px; border-radius:10px; border-left: 6px solid #3498db; margin-bottom:20px;">
    <h3 style="margin:0; color:#2c3e50;">🛡️ ESCUDO FAMILIAR (Si falleces HOY - Nivel {nivel_pk})</h3>
    <div style="display:flex; flex-wrap:wrap; gap:20px; margin-top:10px;">
        <div><b>RENTA MENSUAL (Viuda + Hijo):</b><br><span style="font-size:22px; color:#2980b9;">{ingreso_familiar_anual/12:,.0f} CHF</span></div>
        <div><b>CAPITAL INMEDIATO:</b><br><span style="font-size:22px; color:#27ae60;">{capital_seguro:,.0f} CHF</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================================================================
# RESULTADO + HERENCIA
# ================================================================
fila_h = df[df['Edad'] == edad_herencia].iloc[0]
herencia_val = fila_h['SALDO VT'] + fila_h['SALDO ORO'] + fila_h['SALDO BONOS'] + fila_h['SALDO SPARKONTO'] + fila_h['PATRIMONIO VIAC']

col_h = "#3498db" if herencia_val > 0 else "#e74c3c"
tit_st = f"⚠️ AGOTADO A LOS {edad_quiebra}" if edad_quiebra else "✅ SOSTENIBLE (>120 AÑOS)"
col_st = "#e74c3c" if edad_quiebra else "#27ae60"

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
        <p>Herencia líquida a los {edad_herencia} (solo portfolio privado)</p>
    </div>
    """, unsafe_allow_html=True)

# ================================================================
# PROTECCIÓN MARÍA (post-65) — YA SIN NameError
# ================================================================
st.markdown("---")
renta_viuda_pk_mes = renta_pk_mensual * 0.6
ahv_viuda_mes_val = ahv_viuda_anual / 12
total_maria_mensual = renta_viuda_pk_mes + ahv_viuda_mes_val

st.markdown(f"""
<div style="background-color:#fdebd0; padding:15px; border-radius:10px; border-left: 6px solid #e67e22; margin-bottom:20px;">
    <h3 style="margin:0; color:#2c3e50;">👩‍👦 PROTECCIÓN MARÍA (Si falleces a los {edad_herencia} — Estrategia: {estrategia_retiro})</h3>
    <div style="display:flex; flex-wrap:wrap; gap:30px; margin-top:10px;">
        <div>
            <b>INGRESOS MENSUALES VITALICIOS:</b><br>
            <span style="font-size:18px;">AHV Viuda: {ahv_viuda_mes_val:,.0f} CHF/mes</span><br>
            <span style="font-size:18px;">Renta Viuda PK: {renta_viuda_pk_mes:,.0f} CHF/mes</span><br>
            <span style="font-size:22px; color:#e67e22;"><b>Total: {total_maria_mensual:,.0f} CHF/mes</b></span>
        </div>
        <div>
            <b>HERENCIA (una vez):</b><br>
            <span style="font-size:22px; color:#27ae60;">{herencia_val:,.0f} CHF</span><br>
            <span style="font-size:12px; color:#7f8c8d;">(Portfolio privado: VT + Bonos + Sparkonto + VIAC)<br>
            El capital PK {'NO se hereda — genera la renta viuda arriba' if estrategia_retiro != '100% Capital' else 'ya está incluido en los cubos'}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- ASIGNACIÓN INVERSIÓN ---
if pct_oro > 0:
    st.markdown("---")
    st.subheader("🥇 Asignación Inversión Privada")
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        st.metric("Aporte Total", f"{aporte_etf:,} CHF/mes")
    with col_i2:
        st.metric(f"→ VT ({100-pct_oro}%)", f"{aporte_etf * pct_vt:,.0f} CHF/mes")
    with col_i3:
        st.metric(f"→ Oro ({pct_oro}%)", f"{aporte_etf * pct_oro_dec:,.0f} CHF/mes")

# ================================================================
# HOJA DE RUTA — PASO A PASO
# ================================================================
st.markdown("---")
st.subheader("🗺️ Hoja de Ruta — Qué Hacer y Cuándo")

# --- Calcular valores clave para la hoja de ruta ---
fila_65_df = df[df['Edad'] == 65]
if fila_65_df.empty:
    st.error("No se encontró la fila de edad 65 en la simulación. Revisa EDAD_RETIRO/EDAD_ACTUAL.")
    st.stop()
fila_65 = fila_65_df.iloc[0]

viac_al_65 = fila_65['PATRIMONIO VIAC'] + fila_65['RETIRADA BRUTA VIAC']
viac_por_cuenta = viac_al_65 / 5

fila_64_df = df[df['Edad'] == 64]
if fila_64_df.empty:
    vt_al_65 = 0
    oro_al_65 = 0
else:
    vt_al_65 = fila_64_df.iloc[0]['SALDO VT']
    oro_al_65 = fila_64_df.iloc[0]['SALDO ORO']

patrimonio_privado_65 = vt_al_65 + oro_al_65

# (IMPORTANTE) Aquí NO recalculamos cap_pk_* ni renta_pk_mensual.
# Ya vienen de calc_pk_strategy(...) en la parte "limpia".

ahv_mensual = ahv_pareja_proyectado
ingresos_fijos_mensual = ahv_mensual + renta_pk_mensual

# Déficit año 1 jubilación
gasto_65 = fila_65['GASTO REAL ANUAL']
ingreso_fijo_65 = fila_65['TOTAL INGRESOS FIJOS']
deficit_65 = max(0, gasto_65 - ingreso_fijo_65)

# Target cubos
target_spark_65 = fila_65['INYECCION A SPARKONTO'] if fila_65['INYECCION A SPARKONTO'] > 0 else deficit_65 * 3
target_bonos_65 = fila_65['INYECCION A BONOS'] if fila_65['INYECCION A BONOS'] > 0 else deficit_65 * 5

# ================================================================
# FASE 1: HOY (43) HASTA 58 — ACUMULACIÓN
# ================================================================
with st.expander("📅 FASE 1: HOY (43 años) → 58 años — ACUMULACIÓN", expanded=True):
    st.markdown(f"""
    **Objetivo:** Maximizar el crecimiento de tu patrimonio con aportes constantes.

    **Acciones mensuales automáticas:**

    | Acción | Destino | Monto |
    |--------|---------|-------|
    | Aporte 3er Pilar (VIAC) | 5 cuentas VIAC | {APORTE_ANUAL_3A/12:,.0f} CHF/mes |
    | Inversión privada → VT | ETF VT / Acciones | {aporte_etf * pct_vt:,.0f} CHF/mes |
    {"| Inversión privada → Oro | Oro (ETC/físico) | " + f"{aporte_etf * pct_oro_dec:,.0f}" + " CHF/mes |" if pct_oro > 0 else ""}
    | Contribución PK ({nivel_pk}) | Pensionskasse | {contribuciones[nivel_pk]['Total']:,.0f} CHF/mes (automático nómina) |

    **Checklist importante:**
    - ✅ Mantener **5 cuentas VIAC separadas** (para retiro escalonado fiscal)
    - ✅ Revisar anualmente el nivel PK (Standard/Medium/Plus) según tu capacidad de ahorro
    - ✅ Actualizar beneficiarios en el PK si cambia tu situación familiar
    - ✅ Considerar **compras voluntarias** al PK (Einkauf): tienes {389530 * factor_salario:,.0f} CHF de potencial — deducible de impuestos
    """)

# ================================================================
# FASE 2: 58-64 — PRE-JUBILACIÓN
# ================================================================
with st.expander("📅 FASE 2: 58 → 64 años — PREPARACIÓN PRE-JUBILACIÓN"):
    st.markdown(f"""
    **Objetivo:** Preparar la transición. Tu PK a los 58 será ~{pk_interpolado.get(58, 0):,.0f} CHF.

    **Acciones clave (3-5 años antes de los 65):**

    1. **Decisión PK (a los ~60-62):** Comunicar a la Pensionskasse tu elección:
       - Tu opción actual: **{estrategia_retiro}**
       {"- Recibirás **" + f"{cap_pk_bruto:,.0f}" + " CHF brutos** como capital" if cap_pk_bruto > 0 else ""}
       {"- Recibirás **" + f"{renta_pk_mensual:,.0f}" + " CHF/mes** de renta vitalicia" if renta_pk_mensual > 0 else ""}
       - ⚠️ **Esta decisión suele ser irrevocable.** Consulta con un asesor fiscal.

    2. **Últimas compras voluntarias PK (Einkauf):**
       - Las compras en los **3 años anteriores al retiro de capital están bloqueadas** por ley
       - Si planeas retirar capital, haz las compras **antes de los 62**
       - Beneficio fiscal: cada CHF de Einkauf reduce tu base imponible ese año

    3. **Planificación fiscal del retiro:**
       - En el cantón de Lucerna, el impuesto sobre retiro de capital es progresivo
       - Retirar PK y VIAC en **años fiscales diferentes** reduce la tasa total
       - Considera retirar el PK a los 65 y comenzar VIAC a los 65-69 (escalonado)

    4. **Revisar asignación de inversiones:**
       - Reducir gradualmente la volatilidad del portfolio privado si lo deseas
       - Asegurar liquidez suficiente para los primeros años de jubilación
    """)

# ================================================================
# FASE 3: AÑO 65 — EL DÍA D
# ================================================================
with st.expander("📅 FASE 3: 65 años — DÍA DE LA JUBILACIÓN", expanded=True):
    st.markdown(f"### Tu estrategia: **{estrategia_retiro}**")

    st.markdown("#### 💰 Paso 1: Entradas de Capital")

    entradas_data = []
    if cap_pk_bruto > 0:
        entradas_data.append({
            'Fuente': f'Pensionskasse ({estrategia_retiro})',
            'Bruto': f"{cap_pk_bruto:,.0f}",
            'Impuesto': f"-{cap_pk_impuesto:,.0f} ({tax*1:.1f}%)",
            'Neto': f"{cap_pk_neto:,.0f}"
        })

    entradas_data.append({
        'Fuente': 'VIAC Cuenta 1 de 5 (año 65)',
        'Bruto': f"{viac_por_cuenta:,.0f}",
        'Impuesto': f"-{viac_por_cuenta * tax_rate * 0.8:,.0f} ({tax*0.8:.1f}%)",
        'Neto': f"{viac_por_cuenta - viac_por_cuenta * tax_rate * 0.8:,.0f}"
    })

    entradas_data.append({
        'Fuente': 'Portfolio Privado (VT + Oro)',
        'Bruto': f"{patrimonio_privado_65:,.0f}",
        'Impuesto': 'Ya invertido',
        'Neto': f"{patrimonio_privado_65:,.0f}"
    })

    df_entradas = pd.DataFrame(entradas_data)
    st.dataframe(df_entradas, use_container_width=True, hide_index=True)

    total_disponible = cap_pk_neto + (viac_por_cuenta - viac_por_cuenta * tax_rate * 0.8) + patrimonio_privado_65
    st.markdown(f"**💵 Total disponible para invertir/distribuir: ~{total_disponible:,.0f} CHF**")

    st.markdown("#### 📊 Paso 2: Ingresos Fijos Mensuales")

    ingresos_data = [
        {'Fuente': 'AHV/AVS (Pareja)', 'Mensual': f"{ahv_mensual:,.0f} CHF", 'Anual': f"{ahv_mensual*12:,.0f} CHF"},
    ]
    if renta_pk_mensual > 0:
        ingresos_data.append({'Fuente': f'Renta PK ({estrategia_retiro})', 'Mensual': f"{renta_pk_mensual:,.0f} CHF", 'Anual': f"{renta_pk_mensual*12:,.0f} CHF"})
    ingresos_data.append({'Fuente': '**TOTAL FIJOS**', 'Mensual': f"**{ingresos_fijos_mensual:,.0f} CHF**", 'Anual': f"**{ingresos_fijos_mensual*12:,.0f} CHF**"})

    st.dataframe(pd.DataFrame(ingresos_data), use_container_width=True, hide_index=True)

    st.markdown(f"""
    **Gasto proyectado a los 65:** {gasto_65:,.0f} CHF/año ({gasto_65/12:,.0f} CHF/mes)  
    **Déficit anual a cubrir con cubos:** {deficit_65:,.0f} CHF/año ({deficit_65/12:,.0f} CHF/mes)
    """)

    st.markdown("#### 🪣 Paso 3: Distribuir el Capital en los 3 Cubos")

    st.markdown(f"""
    | Cubo | Para qué | Horizonte | Monto Objetivo | Rentabilidad |
    |------|----------|-----------|----------------|-------------|
    | 🔵 **Sparkonto** | Gastos inmediatos | 0-3 años | ~{target_spark_65:,.0f} CHF | 0% (seguro) |
    | 🟡 **Bonos** | Reserva media | 3-8 años | ~{target_bonos_65:,.0f} CHF | {r_bonos}% |
    | 🟢 **VT{' + 🟤 Oro' if pct_oro > 0 else ''}** | Crecimiento | 8+ años | Resto (~{max(0, total_disponible - target_spark_65 - target_bonos_65):,.0f} CHF) | {r_retiro}%{f' / {r_oro_retiro}%' if pct_oro > 0 else ''} |

    **Orden de llenado:** Primero Sparkonto → después Bonos → el resto a VT{'/Oro' if pct_oro > 0 else ''}  
    **Orden de consumo:** Gastas de Sparkonto → cuando se vacía, de Bonos → {'Oro →' if pct_oro > 0 else ''} finalmente VT
    """)

    st.info("💡 **Acción concreta:** Abre una cuenta de ahorro (Sparkonto), una cuenta de bonos/renta fija, y mantén tu broker (VT). Transfiere el capital según los montos de arriba.")

# ================================================================
# FASE 4: 65-69 — RETIRO ESCALONADO VIAC
# ================================================================
with st.expander("📅 FASE 4: 65 → 69 años — RETIRO ESCALONADO VIAC"):
    st.markdown(f"""
    **Objetivo:** Retirar las 5 cuentas VIAC una por año para minimizar impuestos.

    | Año | Edad | Cuenta VIAC | Monto Estimado | Impuesto (~{tax*0.8:.1f}%) | Neto | Destino |
    |-----|------|-------------|---------------|-----------|------|---------|
    | 1 | 65 | Cuenta 1 | {viac_por_cuenta:,.0f} | {viac_por_cuenta*tax_rate*0.8:,.0f} | {viac_por_cuenta*(1-tax_rate*0.8):,.0f} | Rellenar cubos |
    | 2 | 66 | Cuenta 2 | {viac_por_cuenta:,.0f} | {viac_por_cuenta*tax_rate*0.8:,.0f} | {viac_por_cuenta*(1-tax_rate*0.8):,.0f} | Rellenar cubos |
    | 3 | 67 | Cuenta 3 | {viac_por_cuenta:,.0f} | {viac_por_cuenta*tax_rate*0.8:,.0f} | {viac_por_cuenta*(1-tax_rate*0.8):,.0f} | Rellenar cubos |
    | 4 | 68 | Cuenta 4 | {viac_por_cuenta:,.0f} | {viac_por_cuenta*tax_rate*0.8:,.0f} | {viac_por_cuenta*(1-tax_rate*0.8):,.0f} | Rellenar cubos |
    | 5 | 69 | Cuenta 5 | {viac_por_cuenta:,.0f} | {viac_por_cuenta*tax_rate*0.8:,.0f} | {viac_por_cuenta*(1-tax_rate*0.8):,.0f} | Rellenar cubos |

    **Total VIAC:** ~{viac_al_65:,.0f} CHF brutos → ~{viac_al_65*(1-tax_rate*0.8):,.0f} CHF netos

    **Regla de distribución:** Cada año que recibes VIAC:
    1. ¿El Sparkonto tiene menos de 3 años de déficit? → Rellenar
    2. ¿Los Bonos tienen menos de 5 años de déficit? → Rellenar
    3. ¿Sobra? → Al cubo VT{'/Oro' if pct_oro > 0 else ''} para que siga creciendo

    ⚠️ **Importante:** No retirar más de una cuenta VIAC en el mismo año fiscal.
    """)

# ================================================================
# FASE 5: 70+ — PILOTO AUTOMÁTICO
# ================================================================
with st.expander("📅 FASE 5: 70+ años — PILOTO AUTOMÁTICO"):
    edades_criticas = {}
    for _, row in df[df['Edad'] >= 70].iterrows():
        e = int(row['Edad'])
        if row['SALDO SPARKONTO'] <= 0 and 'sparkonto' not in edades_criticas:
            edades_criticas['sparkonto'] = e
        if row['SALDO BONOS'] <= 0 and 'bonos' not in edades_criticas:
            edades_criticas['bonos'] = e
        if pct_oro > 0 and row['SALDO ORO'] <= 0 and 'oro' not in edades_criticas:
            edades_criticas['oro'] = e
        if row['SALDO VT'] <= 0 and 'vt' not in edades_criticas:
            edades_criticas['vt'] = e

    st.markdown(f"""
    **Objetivo:** Vivir del sistema de cubos, rebalanceando una vez al año.

    **Rutina anual (enero de cada año):**
    1. Revisar saldo del Sparkonto: ¿cubre 2-3 años de gastos?
    2. Si no → vender Bonos para rellenar
    3. Si Bonos también bajos → vender {'Oro, luego ' if pct_oro > 0 else ''}VT para rellenar Bonos + Sparkonto
    4. Cobrar AHV ({ahv_mensual:,.0f}/mes) {"+ renta PK (" + f"{renta_pk_mensual:,.0f}" + "/mes)" if renta_pk_mensual > 0 else ""} automáticamente
    """)

    timeline_items = []
    if 'sparkonto' in edades_criticas:
        timeline_items.append(f"- 🔵 Sparkonto se agota a los **~{edades_criticas['sparkonto']}** → empiezas a usar Bonos")
    if 'bonos' in edades_criticas:
        timeline_items.append(f"- 🟡 Bonos se agotan a los **~{edades_criticas['bonos']}** → empiezas a usar {'Oro' if pct_oro > 0 else 'VT'}")
    if pct_oro > 0 and 'oro' in edades_criticas:
        timeline_items.append(f"- 🟤 Oro se agota a los **~{edades_criticas['oro']}** → empiezas a usar VT")
    if 'vt' in edades_criticas:
        timeline_items.append(f"- 🟢 VT se agota a los **~{edades_criticas['vt']}** → ⚠️ solo queda AHV")
    elif edad_quiebra is None:
        timeline_items.append(f"- 🟢 VT **nunca se agota** → patrimonio sostenible de por vida ✅")

    st.markdown('\n'.join(timeline_items))

    if edad_quiebra:
        st.error(f"⚠️ Con los parámetros actuales, el patrimonio se agota a los {edad_quiebra} años. Considera aumentar el ahorro, reducir gastos, o elegir renta PK parcial.")
    else:
        st.success(f"✅ El plan es sostenible hasta los 120+. Herencia estimada a los {edad_herencia}: {herencia_val:,.0f} CHF")

    st.markdown(f"""
    **Para María si falleces después de los 65:**
    {"- Renta viuda PK: " + f"{renta_pk_mensual * 0.6:,.0f}" + " CHF/mes (60% de tu pensión)" if renta_pk_mensual > 0 else "- Sin renta viuda PK (elegiste 100% Capital) → hereda el patrimonio en los cubos"}
    - AHV viuda: ~{ahv_viuda_anual/12:,.0f} CHF/mes
    - Patrimonio en cubos: heredable al 100%
    """)
