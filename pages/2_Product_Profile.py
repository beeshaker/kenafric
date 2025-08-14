import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from conn1 import MySQLDatabase

# ---------- Page / Sidebar ----------
st.set_page_config(page_title="📦 Product Profile", layout="wide")
st.sidebar.title("Product Profile")

db = MySQLDatabase()
db.connect()

products = db.get_all_products()  # expects iterable of product names/ids
selected_product = st.sidebar.selectbox("Select a Product", products)

# Standardize months; allow All
month_order = ['All','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
selected_month = st.sidebar.selectbox("Select a Month", month_order)

# Analyst-tunable controls
threshold = st.sidebar.slider("Group small routes below (%)", min_value=0, max_value=10, value=2, step=1)
max_clients = st.sidebar.slider("Max clients to display (chart/table)", 5, 50, 15, step=5)

# ---------- Utils ----------
def group_small_routes(df, value_col, label_col, pct_threshold):
    if df.empty:
        return df.assign(percentage=[])
    total = df[value_col].sum()
    if total == 0:
        return df.assign(percentage=0)
    df = df.copy()
    df['percentage'] = df[value_col] / total * 100
    small = df[df['percentage'] < pct_threshold]
    large = df[df['percentage'] >= pct_threshold]
    if not small.empty:
        other_val = small[value_col].sum()
        other_row = pd.DataFrame({label_col: ['Other'], value_col: [other_val], 'percentage': [other_val/total*100]})
        df_grp = pd.concat([large, other_row], ignore_index=True)
    else:
        df_grp = large
    return df_grp

def concentration_hhi(series_counts: pd.Series) -> float:
    total = series_counts.sum()
    if total == 0:
        return 0.0
    shares = (series_counts / total) ** 2
    return shares.sum()

def pct(n, d):
    return 0 if d == 0 else (n/d*100)

# ---------- Main ----------
if selected_product:
    st.title(f"📦 {selected_product} — Product Profile")
    sublabel = "All Months" if selected_month == "All" else selected_month
    st.caption(f"View: **{sublabel}**")

    # --- Data pulls (expected columns noted below)
    top_clients_df = db.get_top_clients_for_product(selected_product, selected_month)
    # expected: ['customer_name','total_quantity_sold', optional 'total_sales_amount']

    route_distribution_df = db.get_sales_distribution_by_route(selected_product, selected_month)
    # expected: ['route','total_quantity_sold', optional 'total_sales_amount']

    # Optional: monthly series for trend (if available)
    monthly_df = pd.DataFrame()
    try:
        monthly_df = db.get_product_monthly_series(selected_product)
        # expected: ['month','total_quantity_sold', optional 'total_sales_amount', 'unique_clients', 'unique_routes']
        month_cat = pd.CategoricalDtype(categories=month_order[1:], ordered=True)
        if 'month' in monthly_df.columns:
            monthly_df['month'] = monthly_df['month'].astype(str).str[:3].str.title().replace({'Sept':'Sep'})
            monthly_df = monthly_df[monthly_df['month'].isin(month_order[1:])].copy()
            monthly_df['month'] = monthly_df['month'].astype(month_cat)
            monthly_df = monthly_df.sort_values('month')
    except Exception:
        pass

    # --- Totals (prefer route_distribution totals; fall back to clients if needed)
    total_qty_routes = int(route_distribution_df['total_quantity_sold'].sum()) if not route_distribution_df.empty else 0
    total_rev_routes = route_distribution_df['total_sales_amount'].sum() if ('total_sales_amount' in route_distribution_df.columns and not route_distribution_df.empty) else None

    # Fallback from clients if route data is missing
    total_qty_clients = int(top_clients_df['total_quantity_sold'].sum()) if not top_clients_df.empty else 0
    total_rev_clients = top_clients_df['total_sales_amount'].sum() if ('total_sales_amount' in top_clients_df.columns and not top_clients_df.empty) else None

    total_qty = total_qty_routes if total_qty_routes > 0 else total_qty_clients
    total_rev = total_rev_routes if total_rev_routes is not None else total_rev_clients
    avg_price = (total_rev / total_qty) if (total_rev is not None and total_qty > 0) else None

    # --- KPIs
    kpi_cols = st.columns(5)
    kpi_cols[0].metric("Total Quantity", f"{total_qty:,}")
    kpi_cols[1].metric("Total Revenue", f"{total_rev:,.0f}" if total_rev is not None else "—")
    kpi_cols[2].metric("Avg Unit Price", f"{avg_price:,.2f}" if avg_price else "—")
    unique_clients = len(top_clients_df['customer_name'].unique()) if (not top_clients_df.empty and 'customer_name' in top_clients_df.columns) else 0
    unique_routes = len(route_distribution_df['route'].unique()) if (not route_distribution_df.empty and 'route' in route_distribution_df.columns) else 0
    kpi_cols[3].metric("Active Clients", f"{unique_clients}")
    kpi_cols[4].metric("Active Routes", f"{unique_routes}")

    # ---------- Top Clients + Pareto (ALL clients used for 80% calculation) ----------
    if not top_clients_df.empty:
        # Sort & normalize
        tc_all = top_clients_df.copy().rename(columns={'customer_name':'Client', 'total_quantity_sold':'Qty'})
        if 'total_sales_amount' in tc_all.columns:
            tc_all = tc_all.rename(columns={'total_sales_amount':'Revenue'})
        else:
            tc_all['Revenue'] = pd.NA

        tc_all = tc_all.sort_values('Qty', ascending=False).reset_index(drop=True)
        total_qty_all = tc_all['Qty'].sum()

        # Cumulative share on ALL clients
        tc_all['CumQty'] = tc_all['Qty'].cumsum()
        tc_all['CumShare%'] = np.where(total_qty_all > 0, tc_all['CumQty'] / total_qty_all * 100, 0)

        # Number of clients to reach 80%
        if (tc_all['CumShare%'] >= 80).any():
            eighty_idx_all = int((tc_all['CumShare%'] >= 80).idxmax())
            clients_to_80 = eighty_idx_all + 1
            eighty_client = tc_all.loc[eighty_idx_all, 'Client']
            eighty_share = float(tc_all.loc[eighty_idx_all, 'CumShare%'])
        else:
            clients_to_80, eighty_client, eighty_share = None, None, None

        # KPI for “Clients to 80%”
        st.metric(
            "Clients to reach 80% of volume",
            value=f"{clients_to_80}" if clients_to_80 else "Not reached",
            delta=f"Threshold: {eighty_client} ({eighty_share:.1f}%)" if clients_to_80 else None
        )

        # Table / Chart DISPLAY subset (does NOT affect the 80% calculation)
        tc_display = tc_all.head(max_clients)

        c1, c2 = st.columns([1,1])
        with c1:
            st.subheader(f"Top Clients — {selected_product} ({sublabel})")
            st.dataframe(
                tc_display[['Client','Qty','Revenue','CumShare%']].style.format(
                    {'Qty':'{:,.0f}','Revenue':'{:,.0f}','CumShare%':'{:,.1f}'}
                ),
                use_container_width=True
            )
            # Coverage quick stats (using ALL clients)
            top5_cov = (tc_all['Qty'].head(5).sum() / total_qty_all * 100) if total_qty_all else 0
            top10_cov = (tc_all['Qty'].head(10).sum() / total_qty_all * 100) if total_qty_all else 0
            st.caption(f"Top 5 coverage: **{top5_cov:.1f}%** · Top 10 coverage: **{top10_cov:.1f}%**")

        with c2:
            # Pareto chart (display subset; cum% is relative to ALL total)
            fig_pareto = go.Figure()

            # Bars: Qty
            fig_pareto.add_bar(
                x=tc_display['Client'],
                y=tc_display['Qty'],
                name='Qty'
            )

            # Line: Cum Share % relative to ALL total
            tc_display = tc_display.copy()
            tc_display['CumQty_all_ref'] = tc_display['Qty'].cumsum()
            tc_display['CumShare%_all_ref'] = np.where(total_qty_all > 0, tc_display['CumQty_all_ref']/total_qty_all*100, 0)

            fig_pareto.add_trace(go.Scatter(
                x=tc_display['Client'],
                y=tc_display['CumShare%_all_ref'],
                mode='lines+markers',
                name='Cum Share %',
                yaxis='y2'
            ))

            # 80% horizontal benchmark
            fig_pareto.add_shape(
                type="line",
                x0=-0.5, x1=len(tc_display)-0.5,
                y0=80, y1=80,
                line=dict(width=2, dash="dash", color="red"),
                yref="y2"
            )
            fig_pareto.add_annotation(
                x=max(0, len(tc_display)//2),
                y=82,
                text="80% Pareto Threshold",
                showarrow=False,
                font=dict(color="red", size=12),
                yref="y2"
            )

            # Highlight crossing point if it falls within the displayed subset
            if clients_to_80:
                crossing_client = eighty_client
                if crossing_client in list(tc_display['Client']):
                    crossing_y = float(tc_all.loc[eighty_idx_all, 'CumShare%'])
                    fig_pareto.add_trace(go.Scatter(
                        x=[crossing_client],
                        y=[crossing_y],
                        mode='markers+text',
                        name='80% Crossing',
                        yaxis='y2',
                        marker=dict(size=12, symbol='diamond'),
                        text=[f"{clients_to_80} clients"],
                        textposition='top center',
                        hovertemplate="Client: %{x}<br>Cum Share: %{y:.1f}%<extra>80% crossing</extra>"
                    ))

            fig_pareto.update_layout(
                title="Pareto — Cumulative Share of Quantity (Top Clients)",
                xaxis=dict(title=None, tickangle=-30),
                yaxis=dict(title='Qty'),
                yaxis2=dict(title='Cum Share %', overlaying='y', side='right', range=[0, 100]),
                legend=dict(x=0.02, y=0.98, bordercolor="Black", borderwidth=1)
            )

            st.plotly_chart(fig_pareto, use_container_width=True)

        # Client concentration (HHI) based on ALL clients
        client_hhi = concentration_hhi(tc_all['Qty'])
        st.caption(f"Client Concentration (HHI): **{client_hhi:.3f}** (0=diverse, 1=monopoly)")

    # ---------- Route Distribution ----------
    if not route_distribution_df.empty:
        st.subheader(f"Route Distribution — {selected_product} ({sublabel})")

        grouped_route_df = group_small_routes(route_distribution_df.copy(), 'total_quantity_sold', 'route', threshold)

        r_sorted = route_distribution_df.sort_values('total_quantity_sold', ascending=False).rename(
            columns={'route':'Route','total_quantity_sold':'Qty'}
        )

        rc1, rc2 = st.columns([1,1])
        with rc1:
            fig_route_bar = px.bar(r_sorted.head(10), x='Route', y='Qty', title="Top 10 Routes by Quantity", text='Qty')
            fig_route_bar.update_layout(xaxis_title=None, yaxis_title="Qty", xaxis_tickangle=-30, showlegend=False)
            st.plotly_chart(fig_route_bar, use_container_width=True)

        with rc2:
            fig_route_pie = px.pie(grouped_route_df.rename(columns={'route':'Route','total_quantity_sold':'Qty'}),
                                   values='Qty', names='Route', title="Sales Distribution by Route (Grouped)")
            st.plotly_chart(fig_route_pie, use_container_width=True)

        fig_treemap = px.treemap(grouped_route_df.rename(columns={'route':'Route','total_quantity_sold':'Qty'}),
                                 path=['Route'], values='Qty',
                                 title="Treemap — Route Contribution")
        st.plotly_chart(fig_treemap, use_container_width=True)

        route_hhi = concentration_hhi(route_distribution_df.set_index('route')['total_quantity_sold'])
        top3_share = pct(route_distribution_df['total_quantity_sold'].nlargest(3).sum(), total_qty)
        st.caption(f"Route Concentration (HHI): **{route_hhi:.3f}** · Top 3 Routes Coverage: **{top3_share:.1f}%**")

    # ---------- Seasonality & Trend (optional) ----------
    if not monthly_df.empty and selected_month == "All":
        st.subheader("Seasonality & Trend")
        if 'total_quantity_sold' in monthly_df.columns:
            fig_qty_trend = px.line(monthly_df, x='month', y='total_quantity_sold', markers=True,
                                    title="Monthly Quantity Trend")
            fig_qty_trend.update_layout(xaxis_title="Month", yaxis_title="Quantity")
            st.plotly_chart(fig_qty_trend, use_container_width=True)

        if 'total_sales_amount' in monthly_df.columns:
            fig_rev_trend = px.line(monthly_df, x='month', y='total_sales_amount', markers=True,
                                    title="Monthly Revenue Trend")
            fig_rev_trend.update_layout(xaxis_title="Month", yaxis_title="Revenue")
            st.plotly_chart(fig_rev_trend, use_container_width=True)

        meta_cols = [c for c in ['unique_clients','unique_routes'] if c in monthly_df.columns]
        if meta_cols:
            fig_meta = px.bar(monthly_df, x='month', y=meta_cols, barmode='group',
                              title="Monthly Reach — Unique Clients & Routes")
            st.plotly_chart(fig_meta, use_container_width=True)

    # ---------- Empty state ----------
    if top_clients_df.empty and route_distribution_df.empty:
        st.info("No data found for the current selection. Try a different month or product.")
