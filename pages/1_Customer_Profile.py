import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from conn1 import MySQLDatabase

# =========================
# Page / Sidebar
# =========================
st.set_page_config(page_title="👤 Client Profile & Insights", layout="wide")
st.sidebar.title("Client Selection")

db = MySQLDatabase()
db.connect()

clients = db.get_all_clients()
selected_client = st.sidebar.selectbox("Select a Client", clients)

# Define month order (same labels as your DB returns)
month_order = ['All', 'Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']
ordered_months = ['Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'August', 'September']

selected_month = st.selectbox("Select a Month for Product Breakdown", month_order)

# -------------------------
# Helpers
# -------------------------
def cv(series: pd.Series) -> float:
    s = series.dropna().astype(float)
    if s.mean() == 0:
        return 0.0
    return float(s.std(ddof=0) / s.mean()) * 100

def ema_forecast(series: pd.Series, alpha: float = 0.4, horizon: int = 3) -> pd.Series:
    s = series.dropna().astype(float)
    if s.empty:
        return pd.Series([0]*horizon)
    level = s.iloc[0]
    for val in s.iloc[1:]:
        level = alpha*val + (1-alpha)*level
    return pd.Series([level]*horizon)

def month_sort_cat(s: pd.Series) -> pd.Series:
    cat = pd.CategoricalDtype(categories=ordered_months, ordered=True)
    return s.astype(str).astype(cat)

def pct(n, d):
    return 0 if d in [0, None] else round(n/d*100, 1)

def safe_sum(df, col):
    return 0 if df.empty or col not in df.columns else float(df[col].sum())

def build_boolean_basket_matrix(csd: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a boolean month x product matrix (1 if qty > 0 in that month for that product).
    """
    if csd.empty:
        return pd.DataFrame()
    mm = csd.pivot_table(index='month', columns='item_description',
                         values='total_quantity_sold', aggfunc='sum').fillna(0)
    # keep only ordered months & cast to bool
    mm = mm.loc[mm.index.isin(ordered_months)]
    mm = (mm > 0).astype(int)
    return mm

def cross_sell_metrics(mm_bool: pd.DataFrame) -> pd.DataFrame:
    """
    Compute pair metrics for A->B:
      - co_tx: months both A & B purchased
      - support: co_tx / total months
      - conf_A_B: co_tx / months(A)
      - lift: support / (support(A) * support(B))
    Returns a long DataFrame with columns:
      ['A','B','co_tx','support_%','conf_A_B_%','lift','months_A','months_B','total_months']
    """
    if mm_bool.empty or mm_bool.shape[1] < 2 or mm_bool.shape[0] < 1:
        return pd.DataFrame(columns=['A','B','co_tx','support_%','conf_A_B_%','lift','months_A','months_B','total_months'])

    total_months = mm_bool.shape[0]
    prod_counts = mm_bool.sum(axis=0)  # months purchased per product

    rows = []
    cols = list(mm_bool.columns)
    for i, A in enumerate(cols):
        a_count = int(prod_counts[A])
        if a_count == 0:
            continue
        for j, B in enumerate(cols):
            if A == B:
                continue
            b_count = int(prod_counts[B])
            if b_count == 0:
                continue
            co_tx = int((mm_bool[A] & mm_bool[B]).sum())
            if co_tx == 0:
                continue
            support = co_tx / total_months
            conf_A_B = co_tx / a_count
            # base probabilities
            pA = a_count / total_months
            pB = b_count / total_months
            lift = (support / (pA * pB)) if (pA > 0 and pB > 0) else 0
            rows.append({
                'A': A, 'B': B,
                'co_tx': co_tx,
                'support_%': round(support*100, 1),
                'conf_A_B_%': round(conf_A_B*100, 1),
                'lift': round(lift, 2),
                'months_A': a_count,
                'months_B': b_count,
                'total_months': total_months
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(['conf_A_B_%','lift','co_tx'], ascending=[False, False, False])
    return df

# -------------------------
# Stop early if no client
# -------------------------
if not selected_client:
    st.info("Please select a client from the sidebar.")
    st.stop()

st.title(f"👤 Client Profile — {selected_client}")

# =========================
# DATA LOADS (single source of truth)
# =========================
all_clients_product_sales_df = db.get_all_clients_product_sales(selected_month)
client_product_sales_df = db.get_client_product_sales(selected_client, selected_month)
client_sales_detailed = db.get_client_product_sales_detailed(selected_client)
client_sales_route_df = db.get_client_sales(selected_client)

# Ensure month ordering where applicable
for df_ in [client_sales_detailed, client_sales_route_df]:
    if not df_.empty and 'month' in df_.columns:
        df_['month'] = pd.Categorical(df_['month'], categories=month_order, ordered=True)
        df_.sort_values('month', inplace=True)

# =========================
# SUMMARY METRICS BLOCKS
# =========================
# 1) Basket depth/breadth
if not client_sales_detailed.empty:
    csd = client_sales_detailed[client_sales_detailed['month'].isin(ordered_months)].copy()
else:
    csd = client_sales_detailed.copy()

basket_breadth = csd['item_description'].nunique() if not csd.empty else 0
total_qty_all = safe_sum(csd, 'total_quantity_sold')
avg_qty_per_product_per_month = 0
if not csd.empty:
    months_active = csd['month'].nunique()
    if months_active > 0 and basket_breadth > 0:
        avg_qty_per_product_per_month = round(total_qty_all / (basket_breadth * months_active), 2)

top_dep_1 = top_dep_3 = top_dep_5 = 0
if not csd.empty:
    top_by_qty = csd.groupby('item_description')['total_quantity_sold'].sum().sort_values(ascending=False)
    tot = float(top_by_qty.sum()) if top_by_qty.sum() else 1.0
    top_dep_1 = round(top_by_qty.iloc[:1].sum() / tot * 100, 1) if len(top_by_qty) >= 1 else 0
    top_dep_3 = round(top_by_qty.iloc[:3].sum() / tot * 100, 1) if len(top_by_qty) >= 3 else 0
    top_dep_5 = round(top_by_qty.iloc[:5].sum() / tot * 100, 1) if len(top_by_qty) >= 5 else 0

# Repeat purchase ratio
repeat_ratio = 0
if not csd.empty:
    counts = csd.groupby('item_description')['month'].nunique()
    if len(counts) > 0:
        repeat_ratio = round((counts[counts >= 2].size / counts.size) * 100, 1)

# 2) Consistency & volatility
consistency_index = 0
cv_spend = 0.0
purchase_gaps = []
monthly_totals = pd.DataFrame()
if not csd.empty:
    monthly_totals = csd.groupby('month').agg(qty=('total_quantity_sold','sum'),
                                              sales=('sales_amt','sum')).reset_index()
    monthly_totals = monthly_totals[monthly_totals['month'].isin(ordered_months)]
    months_observed = len(ordered_months)
    months_bought = (monthly_totals['qty'] > 0).sum() if not monthly_totals.empty else 0
    consistency_index = round((months_bought / months_observed) * 100, 1)
    cv_spend = round(cv(monthly_totals['sales']) if monthly_totals['sales'].sum() > 0 else cv(monthly_totals['qty']), 1)
    bought_months = monthly_totals.loc[monthly_totals['qty'] > 0, 'month'].astype(str).tolist()
    idx_map = {m:i for i,m in enumerate(ordered_months)}
    gaps = []
    for a, b in zip(bought_months, bought_months[1:]):
        gaps.append(idx_map[b] - idx_map[a])
    purchase_gaps = gaps

# 3) Cross-sell metrics (client-level)
mm_bool = build_boolean_basket_matrix(csd)
xsell_df = cross_sell_metrics(mm_bool)  # A->B metrics per pair

# 4) Route & peer
route_name = "Unknown Route"
share_trend = pd.DataFrame()
client_vs_route_trend = None
if not client_sales_route_df.empty:
    route_name = client_sales_route_df['route'].dropna().astype(str).iloc[0] if 'route' in client_sales_route_df.columns else "Unknown Route"
    route_totals = []
    shares = []
    for _, r in client_sales_route_df.iterrows():
        m = r['month']
        if pd.isna(m):
            route_totals.append(np.nan); shares.append(np.nan); continue
        total_route = db.get_route_sales_for_client(route_name, m)
        route_totals.append(total_route)
        shares.append((r['total_sold_to_client'] / total_route * 100) if total_route else 0)
    client_sales_route_df['total_route_sales'] = route_totals
    client_sales_route_df['client_share_%'] = np.round(shares, 1)
    share_trend = client_sales_route_df.loc[client_sales_route_df['month'].isin(ordered_months), ['month','client_share_%']].dropna()

    months_series = client_sales_route_df['month'].astype(str).reset_index(drop=True)
    client_mom = client_sales_route_df['total_sold_to_client'].pct_change().reset_index(drop=True) * 100
    route_mom = pd.Series(route_totals).pct_change().reset_index(drop=True) * 100
    min_len = min(len(months_series), len(client_mom), len(route_mom))
    client_vs_route_trend = pd.DataFrame({
        'month': months_series.iloc[:min_len],
        'client_mom_%': client_mom.iloc[:min_len].round(1),
        'route_mom_%' : route_mom.iloc[:min_len].round(1),
    })

# 5) Forecast & risk (adds human‑readable churn reasons)
forecast_basis = None
if not csd.empty:
    monthly_totals_fc = csd.groupby('month').agg(qty=('total_quantity_sold','sum'),
                                                 sales=('sales_amt','sum')).reset_index()
    monthly_totals_fc = monthly_totals_fc[monthly_totals_fc['month'].isin(ordered_months)].copy()
    if monthly_totals_fc['sales'].sum() > 0:
        forecast_basis = monthly_totals_fc.set_index('month')['sales']
    else:
        forecast_basis = monthly_totals_fc.set_index('month')['qty']
forecast_next3 = ema_forecast(forecast_basis, alpha=0.4, horizon=3) if forecast_basis is not None else pd.Series([0,0,0])
lifetime_value = round(float(forecast_basis.mean() * 12), 0) if forecast_basis is not None and forecast_basis.mean() > 0 else 0

# ---- Churn classification + reasons (based on month gaps) ----
churn_risk = "Low"
churn_reason = "Insufficient history to evaluate."
if not monthly_totals.empty:
    # Build active month index list
    act = monthly_totals.loc[monthly_totals['qty'] > 0, 'month'].astype(str).tolist()
    idx_map = {m:i for i,m in enumerate(ordered_months)}
    active_idx = [idx_map[m] for m in act if m in idx_map]

    if active_idx:
        # Last observed month in dataset (max month index present at all)
        available_months = monthly_totals['month'].astype(str).dropna().unique().tolist()
        available_idx = [idx_map[m] for m in available_months if m in idx_map]
        last_available_idx = max(available_idx) if available_idx else max(active_idx)

        last_active_idx = max(active_idx)
        gap_months = last_available_idx - last_active_idx  # months since last purchase in the observed window

        # Average purchase cycle (mean gap between active months)
        avg_cycle = None
        if len(active_idx) >= 2:
            diffs = np.diff(sorted(active_idx))
            avg_cycle = float(np.mean(diffs)) if len(diffs) else None

        # Classify
        if avg_cycle is None or avg_cycle == 0:
            # Not enough history for a cycle; fall back to simple rule
            churn_risk = "Low" if gap_months <= 1 else ("Medium" if gap_months == 2 else "High")
            churn_reason = f"Last purchase was **{gap_months} month(s)** ago; not enough history to learn a usual cycle."
        else:
            mult = gap_months / avg_cycle if avg_cycle > 0 else 0
            if gap_months <= avg_cycle * 1.5:
                churn_risk = "Low"
                churn_reason = f"Last purchase **{gap_months} month(s)** ago, within normal cycle (~{avg_cycle:.1f} months)."
            elif gap_months <= avg_cycle * 2.5:
                churn_risk = "Medium"
                churn_reason = f"Last purchase **{gap_months} month(s)** ago, about **{mult:.1f}×** longer than usual cycle. **Recommend follow‑up.**"
            else:
                churn_risk = "High"
                churn_reason = f"Last purchase **{gap_months} month(s)** ago, over **{mult:.1f}×** longer than usual. **Urgent recovery action needed.**"

# =========================
# SUMMARY INSIGHTS (clear language)
# =========================
# Friendly cross-sell summary (top 3 for the client's top product if available)
xsell_summary_line = None
if not xsell_df.empty:
    # Find the client's top product by total qty to anchor the recommendation
    top_prod = (csd.groupby('item_description')['total_quantity_sold'].sum().sort_values(ascending=False).index[0]
                if not csd.empty else None)
    if top_prod and top_prod in xsell_df['A'].values:
        top_recos = xsell_df[xsell_df['A'] == top_prod].head(3)
        parts = [f"{row['B']} (conf {row['conf_A_B_%']}%, lift {row['lift']})" for _, row in top_recos.iterrows()]
        if parts:
            xsell_summary_line = f"When **{selected_client}** buys **{top_prod}**, they also tend to buy: " + "; ".join(parts) + "."

summary_lines = []
summary_lines.append(f"• Basket breadth: **{basket_breadth}** products; avg depth **{avg_qty_per_product_per_month}** units/product/month.")
summary_lines.append(f"• Top item dependence: Top 1 **{top_dep_1}%**, Top 3 **{top_dep_3}%**, Top 5 **{top_dep_5}%** of volume.")
summary_lines.append(f"• Purchase consistency: **{consistency_index}%** of months active; volatility (CV): **{cv_spend}%**.")
if purchase_gaps:
    summary_lines.append(f"• Typical gap between purchases: **{np.median(purchase_gaps):.0f}** month(s).")
if xsell_summary_line:
    summary_lines.append(f"• Cross‑sell: {xsell_summary_line}")
if isinstance(share_trend, pd.DataFrame) and not share_trend.empty:
    st_last = share_trend.dropna().tail(1)['client_share_%'].values
    if st_last.size > 0:
        summary_lines.append(f"• Route share (latest): **{st_last[0]}%** in **{route_name}**.")
summary_lines.append(f"• Forecast next 3 (EMA): **{', '.join([f'{v:,.0f}' for v in forecast_next3])}**; 12‑mo value ≈ **{lifetime_value:,.0f}**.")
summary_lines.append(f"• **Churn risk: {churn_risk}** — {churn_reason}")

with st.expander("🧠 Summary Insights", expanded=True):
    for line in summary_lines:
        st.markdown(line)

# =========================
# CROSS‑SELL RECOMMENDATIONS (per client)
# =========================
st.subheader("🛒 Cross‑sell Recommendations (per client)")

if xsell_df.empty:
    st.info("Not enough purchase history to compute cross‑sell recommendations for this client.")
else:
    # Choose anchor product (A). Default = client's top product.
    default_anchor = (csd.groupby('item_description')['total_quantity_sold'].sum().sort_values(ascending=False).index[0]
                      if not csd.empty else xsell_df['A'].iloc[0])
    anchor_choices = sorted(xsell_df['A'].unique())
    default_idx = anchor_choices.index(default_anchor) if default_anchor in anchor_choices else 0
    anchor = st.selectbox("Anchor product (when the client buys this…)", anchor_choices, index=default_idx)
    min_co = st.slider("Minimum co‑purchase months", 1, 12, 2, step=1)
    top_n = st.slider("Max recommendations to show", 3, 15, 5, step=1)
    # Filter and sort
    recos = xsell_df[(xsell_df['A'] == anchor) & (xsell_df['co_tx'] >= min_co)].copy()
    recos = recos.sort_values(['conf_A_B_%','lift','co_tx'], ascending=[False, False, False]).head(top_n)

    if recos.empty:
        st.warning("No recommendations meet the current thresholds. Try lowering the minimum co‑purchase months.")
    else:
        # Friendly bullets
        bullets = []
        for _, r in recos.iterrows():
            bullets.append(
                f"- **{r['B']}** — together in **{int(r['co_tx'])}/{int(r['total_months'])}** months "
                f"(*support* **{r['support_%']}%**; *confidence* **{r['conf_A_B_%']}%**; *lift* **{r['lift']}**)"
            )
        st.markdown(f"**When this client buys** _{anchor}_, they also tend to buy:")
        st.markdown("\n".join(bullets))

        # Transparent table
        nice = recos[['B','co_tx','support_%','conf_A_B_%','lift','months_A','months_B','total_months']].rename(
            columns={
                'B':'Recommended Item',
                'co_tx':'Co‑purchase Months',
                'support_%':'Support (%)',
                'conf_A_B_%':'Confidence (A→B) (%)',
                'lift':'Lift',
                'months_A':'Months A Bought',
                'months_B':'Months B Bought',
                'total_months':'Observed Months'
            }
        )
        st.dataframe(nice, use_container_width=True)

# =========================
# VISUALS & TABLES (your existing charts)
# =========================
# --- Treemap for ALL clients (basket composition baseline)
if not all_clients_product_sales_df.empty:
    total_all = all_clients_product_sales_df['total_quantity_sold'].sum()
    all_clients_product_sales_df['percentage'] = np.where(
        total_all > 0,
        (all_clients_product_sales_df['total_quantity_sold'] / total_all * 100).round().astype(int),
        0
    )
    fig_treemap_all = px.treemap(
        all_clients_product_sales_df,
        path=['item_description'],
        values='total_quantity_sold',
        title="Average Customer Basket: Product Distribution (All Clients)",
        labels={'total_quantity_sold': 'Quantity Sold'},
        custom_data=['percentage']
    )
    fig_treemap_all.update_traces(
        hovertemplate='<b>%{label}</b><br>Quantity Sold: %{value}<br>Percentage: %{customdata[0]}%'
    )
    st.plotly_chart(fig_treemap_all, use_container_width=True)

# --- Treemap: Selected client's basket
if not client_product_sales_df.empty:
    total_client = client_product_sales_df['total_quantity_sold'].sum()
    client_product_sales_df['percentage'] = np.where(
        total_client > 0,
        (client_product_sales_df['total_quantity_sold'] / total_client * 100).round().astype(int),
        0
    )
    fig_treemap_client = px.treemap(
        client_product_sales_df,
        path=['item_description'],
        values='total_quantity_sold',
        title=f"{selected_client}'s Basket: Product Distribution",
        labels={'total_quantity_sold': 'Quantity Sold'},
        custom_data=['percentage']
    )
    fig_treemap_client.update_traces(
        hovertemplate='<b>%{label}</b><br>Quantity Sold: %{value}<br>Percentage: %{customdata[0]}%'
    )
    st.plotly_chart(fig_treemap_client, use_container_width=True)

# --- Grouped bar: sales per month per product (client)
if not client_sales_detailed.empty:
    tmp = client_sales_detailed.copy()
    tmp['month'] = tmp['month'].astype(str)
    fig_bar = px.bar(
        tmp, x='month', y='sales_amt', color='item_description',
        title=f"Sales per Month for Each Product — {selected_client}",
        labels={'sales_amt':'Sales Amount','month':'Month'},
        category_orders={"month": month_order}
    )
    fig_bar.update_layout(barmode='group', hovermode="x unified")
    st.plotly_chart(fig_bar, use_container_width=True)

# --- Month-to-month change tables & lines (client sales by product)
if not client_sales_detailed.empty:
    csd2 = client_sales_detailed.copy()
    csd2['month'] = month_sort_cat(csd2['month'])
    csd2 = csd2.sort_values(['item_description','month'])

    csd2['qty_change'] = csd2.groupby('item_description')['total_quantity_sold'].diff().fillna(0)
    csd2['sales_change'] = csd2.groupby('item_description')['sales_amt'].diff().fillna(0)
    csd2['pct_change'] = (csd2.groupby('item_description')['total_quantity_sold'].pct_change() * 100).fillna(0)

    st.subheader("Product Detail")
    sel_prod = st.selectbox("Select a product", sorted(csd2['item_description'].unique()))
    det = csd2[csd2['item_description'] == sel_prod][['month','total_quantity_sold','qty_change','pct_change','sales_amt']].copy()
    det = det.rename(columns={
        'total_quantity_sold':'Quantity Sold',
        'qty_change':'Quantity Change',
        'pct_change':'Percentage Change (%)',
        'sales_amt':'Sales Value'
    })
    st.dataframe(det, use_container_width=True)

    # Line: Actual change in sales (per product)
    st.subheader("Actual Change in Sales Amount — by Product")
    fig_sales_chg = go.Figure()
    for prod in csd2['item_description'].unique():
        p = csd2[csd2['item_description'] == prod]
        fig_sales_chg.add_trace(go.Scatter(
            x=p['month'].astype(str),
            y=p['sales_change'],
            mode='lines+markers',
            name=prod,
            hoverinfo='text',
            text=[f"{prod}: {v:,.0f} Ksh" for v in p['sales_change']]
        ))
    fig_sales_chg.update_layout(xaxis_title="Month", yaxis_title="Δ Sales Amount (Ksh)", hovermode="x unified")
    fig_sales_chg.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_sales_chg, use_container_width=True)

    # Line: Quantity change (per product)
    st.subheader("Quantity Change — by Product")
    fig_qty_chg = go.Figure()
    for prod in csd2['item_description'].unique():
        p = csd2[csd2['item_description'] == prod]
        fig_qty_chg.add_trace(go.Scatter(
            x=p['month'].astype(str),
            y=p['qty_change'],
            mode='lines+markers',
            name=prod,
            hoverinfo='text',
            text=[f"{prod}: {v:,.0f} units" for v in p['qty_change']]
        ))
    fig_qty_chg.update_layout(xaxis_title="Month", yaxis_title="Δ Quantity (units)", hovermode="x unified")
    fig_qty_chg.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_qty_chg, use_container_width=True)

# --- Route share & peer benchmark
if not client_sales_route_df.empty and 'total_route_sales' in client_sales_route_df.columns:
    st.subheader(f"Route Share & Peer Trend — {route_name}")

    # Percentage share lines
    fig_share = go.Figure()
    fig_share.add_trace(go.Scatter(
        x=client_sales_route_df['month'].astype(str),
        y=client_sales_route_df['client_share_%'],
        mode='lines+markers',
        name=f"{selected_client} Share (%)"
    ))
    fig_share.update_layout(xaxis_title="Month", yaxis_title="Client Share of Route (%)", hovermode="x unified")
    st.plotly_chart(fig_share, use_container_width=True)

    # MoM growth comparison
    if client_vs_route_trend is not None and not client_vs_route_trend.empty:
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatter(
            x=client_vs_route_trend['month'].astype(str),
            y=client_vs_route_trend['client_mom_%'],
            mode='lines+markers',
            name=f"{selected_client} MoM %"
        ))
        fig_cmp.add_trace(go.Scatter(
            x=client_vs_route_trend['month'].astype(str),
            y=client_vs_route_trend['route_mom_%'],
            mode='lines+markers',
            name=f"{route_name} Route MoM %"
        ))
        fig_cmp.update_layout(title="Client vs Route — MoM Growth", xaxis_title="Month", yaxis_title="MoM %", hovermode="x unified")
        st.plotly_chart(fig_cmp, use_container_width=True)

# --- Simple forecast chart
if forecast_basis is not None:
    st.subheader("📈 Simple 3‑Month Forecast (EMA)")
    hist = forecast_basis.copy()
    hist.index = hist.index.astype(str)
    fut_idx = ["Next1","Next2","Next3"]
    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(x=list(hist.index), y=list(hist.values), mode='lines+markers', name="Actual"))
    fig_fc.add_trace(go.Scatter(x=fut_idx, y=list(forecast_next3.values), mode='lines+markers', name="Forecast"))
    fig_fc.update_layout(xaxis_title="Month", yaxis_title=("Sales Amount" if hist.name=='sales' else "Quantity"), hovermode="x unified")
    st.plotly_chart(fig_fc, use_container_width=True)
