import streamlit as st
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(page_title="Lobito Refinery Dashboard", layout="wide", initial_sidebar_state="expanded")

# 2. Sidebar: Inputs (Defaults matched to Excel Base Case)
st.sidebar.header("Macroeconomic Inputs (WACC)")
rf = st.sidebar.slider("US 10-Year Treasury Yield (%)", 0.0, 10.0, 4.30, 0.1) / 100
beta = st.sidebar.slider("Refining Industry Beta", 0.5, 2.0, 1.10, 0.01)
erp = st.sidebar.slider("Equity Risk Premium (%)", 0.0, 10.0, 5.50, 0.1) / 100
crp = st.sidebar.slider("Angola Country Risk Premium (%)", 0.0, 15.0, 7.20, 0.1) / 100

st.sidebar.divider()

st.sidebar.header("Project Stress Tests")
capex_stress = st.sidebar.slider("CAPEX Overrun/Savings (%)", -30, 50, 0, 1) / 100
rev_stress = st.sidebar.slider("Refining Margin Stress (%)", -30, 30, 0, 1) / 100

# 3. Base Project Parameters
base_capex = 4305.8
base_rev = 11050.0
base_opex = 10260.0

# Apply Stress Tests
live_capex = base_capex * (1 + capex_stress)
live_rev = base_rev * (1 + rev_stress)

debt_ratio = 0.70
cost_of_debt = 0.05
debt_term = 15
tax_rate = 0.25
tax_holiday = 15

# Calculate WACC - Target: 8.765%
cost_of_equity = rf + (beta * erp) + crp
wacc = ((1 - debt_ratio) * cost_of_equity) + (debt_ratio * cost_of_debt)

# 4. Cash Flow Timeline Array Generation (2025-2056)
years = np.arange(2025, 2057)
n_years = len(years)

capex_schedule = np.zeros(n_years)
capex_schedule[0], capex_schedule[1], capex_schedule[2] = live_capex*0.20, live_capex*0.40, live_capex*0.40

capacity = np.zeros(n_years)
capacity[3], capacity[4], capacity[5:] = 0.90, 0.95, 1.00 

revenues = capacity * live_rev
opex = capacity * base_opex
ebitda = revenues - opex

depreciation = np.zeros(n_years)
depreciation[3:3+20] = live_capex / 20

# Debt Schedule
total_debt = live_capex * debt_ratio
debt_service = np.zeros(n_years)
interest = np.zeros(n_years)

pmt = total_debt * (cost_of_debt * (1 + cost_of_debt)**debt_term) / ((1 + cost_of_debt)**debt_term - 1)

balance = total_debt
for i in range(n_years):
    if i >= 3 and i < (3 + debt_term):
        interest[i] = balance * cost_of_debt
        debt_service[i] = pmt
        balance -= (pmt - interest[i])

# Tax & CFADS Schedule
ebt = ebitda - depreciation - interest
taxes = np.zeros(n_years)
for i in range(n_years):
    if i >= (3 + tax_holiday) and ebt[i] > 0:
        taxes[i] = ebt[i] * tax_rate

cfads = ebitda - taxes
fcff = ebitda - capex_schedule - taxes

# 5. Valuation Metrics (Unlevered vs Levered)
# Project IRR (Unlevered - Return on Total Assets)
project_irr = npf.irr(fcff)
project_npv = npf.npv(wacc, fcff) 

# Equity IRR (Levered - Return on 30% Owner Funds)
equity_outflow = capex_schedule * (1 - debt_ratio)
equity_inflow = (ebitda - taxes) - debt_service
fcf_equity = equity_inflow - equity_outflow
equity_irr = npf.irr(fcf_equity)

# DSCR Calculation
dscr_array = np.zeros(n_years)
for i in range(n_years):
    if debt_service[i] > 0:
        dscr_array[i] = cfads[i] / debt_service[i]
min_dscr = np.min(dscr_array[dscr_array > 0]) if np.any(dscr_array > 0) else 0

# 6. Main Dashboard Interface
st.title("Lobito Refinery: Project Finance Dashboard")

# Top KPI Banner
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("WACC", f"{wacc*100:.2f}%")
col2.metric("Project IRR", f"{project_irr*100:.2f}%")
col3.metric("Equity IRR (FIRR)", f"{equity_irr*100:.2f}%", f"+{equity_irr*100-project_irr*100:.1f}% Leverage")
col4.metric("NPV (MM USD)", f"${project_npv:,.0f}")
col5.metric("Min DSCR", f"{min_dscr:.2f}x")

st.divider()

# 7. Visualizations
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Cash Flow Profile (Full Life)")
    chart_years = years[3:]
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Bar(x=chart_years, y=cfads[3:], name='CFADS', marker_color='#2CA02C'))
    fig_cf.add_trace(go.Scatter(x=chart_years, y=debt_service[3:], name='Debt Service', mode='lines', line=dict(color='#FF0000', width=3)))
    fig_cf.update_layout(xaxis_title="Year", yaxis_title="MM USD", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_cf, use_container_width=True)

with col_right:
    st.subheader("Leverage Impact: Returns comparison")
    labels = ['Project IRR (Unlevered)', 'Equity IRR (Levered/FIRR)']
    values = [project_irr*100, equity_irr*100]
    fig_irr = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=['#1F77B4', '#FF7F0E'])])
    fig_irr.update_layout(yaxis_title="Return (%)", margin=dict(t=30))
    st.plotly_chart(fig_irr, use_container_width=True)