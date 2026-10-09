from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd
import streamlit as st


DATASETS: Final[dict[str, tuple[str, tuple[str, ...]]]] = {
    "Customers": (
        "customers.csv",
        ("customer_id", "customer_name", "state", "age", "gender", "occupation"),
    ),
    "Policies": (
        "policies.csv",
        (
            "policy_id",
            "customer_id",
            "policy_type",
            "policy_status",
            "policy_start_date",
            "premium_amount",
            "coverage_amount",
        ),
    ),
    "Claims": (
        "claims.csv",
        (
            "claim_id",
            "policy_id",
            "customer_id",
            "claim_date",
            "claim_type",
            "claim_amount",
            "claim_status",
            "damage_severity",
        ),
    ),
    "Vehicles": (
        "vehicles.csv",
        ("vehicle_id", "customer_id", "vehicle_type", "fuel_type", "vehicle_value"),
    ),
    "Payments": (
        "payments.csv",
        ("payment_id", "claim_id", "payment_status", "payment_amount", "payment_method"),
    ),
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOTS = (PROJECT_ROOT / "data", PROJECT_ROOT, Path.home() / "Downloads")

st.set_page_config(
    page_title="Motor Insurance Analytics",
    page_icon=":material/analytics:",
    layout="wide",
)


def find_dataset(filename: str) -> Path | None:
    for folder in DATA_ROOTS:
        path = folder / filename
        if path.is_file():
            return path
    return None


@st.cache_data(ttl=300, show_spinner="Loading the insurance datasets...")
def load_datasets() -> dict[str, pd.DataFrame]:
    loaded: dict[str, pd.DataFrame] = {}
    missing: list[str] = []

    for label, (filename, required_columns) in DATASETS.items():
        path = find_dataset(filename)
        if path is None:
            missing.append(filename)
            continue

        frame = pd.read_csv(path)
        missing_columns = sorted(set(required_columns) - set(frame.columns))
        if missing_columns:
            raise ValueError(
                f"{filename} is missing required columns: {', '.join(missing_columns)}"
            )
        loaded[label] = frame

    if missing:
        raise FileNotFoundError(
            "Could not find required dataset(s): "
            + ", ".join(missing)
            + ". Put the CSV files in the project folder, its data subfolder, "
            "or your Downloads folder."
        )

    for column in ("age",):
        loaded["Customers"][column] = pd.to_numeric(
            loaded["Customers"][column], errors="coerce"
        )
    for label, columns in {
        "Policies": ("premium_amount", "coverage_amount"),
        "Claims": ("claim_amount",),
        "Vehicles": ("vehicle_value",),
        "Payments": ("payment_amount",),
    }.items():
        for column in columns:
            loaded[label][column] = pd.to_numeric(
                loaded[label][column], errors="coerce"
            )
    for label, columns in {
        "Policies": ("policy_start_date",),
        "Claims": ("claim_date",),
    }.items():
        for column in columns:
            loaded[label][column] = pd.to_datetime(
                loaded[label][column], errors="coerce"
            )

    return loaded


def currency(value: float) -> str:
    return f"₹{value:,.0f}"


try:
    data = load_datasets()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    st.title("Motor insurance analytics")
    st.error(str(error))
    st.stop()

customers = data["Customers"]
policies = data["Policies"]
claims = data["Claims"]
vehicles = data["Vehicles"]
payments = data["Payments"]

st.title("Motor insurance analytics")
st.caption("Explore customer, policy, claim, vehicle, and payment data.")

with st.sidebar:
    st.header("Dashboard")
    page = st.radio(
        "Choose a view",
        ("Overview", "Policies", "Claims", "Customers", "Vehicles & payments"),
    )
    st.divider()
    st.caption(
        f"Loaded {len(customers):,} customers, {len(policies):,} policies, "
        f"{len(claims):,} claims, {len(vehicles):,} vehicles, and "
        f"{len(payments):,} payments."
    )

if page == "Overview":
    total_premium = policies["premium_amount"].sum()
    total_claims = claims["claim_amount"].sum()
    settled_claims = claims.loc[
        claims["claim_status"].str.casefold() == "settled", "claim_amount"
    ].sum()
    paid_payments = payments.loc[
        payments["payment_status"].str.casefold() == "completed", "payment_amount"
    ].sum()

    kpis = st.columns(4)
    kpis[0].metric("Customers", f"{len(customers):,}")
    kpis[1].metric("Policies", f"{len(policies):,}")
    kpis[2].metric("Total premiums", currency(total_premium))
    kpis[3].metric("Claims submitted", f"{len(claims):,}")

    amounts = st.columns(3)
    amounts[0].metric("Claim amount", currency(total_claims))
    amounts[1].metric("Settled claim amount", currency(settled_claims))
    amounts[2].metric("Completed payments", currency(paid_payments))

    left, right = st.columns(2)
    with left:
        st.subheader("Policies by type")
        policy_counts = (
            policies.groupby("policy_type", as_index=False)
            .size()
            .rename(columns={"size": "Policies"})
            .sort_values("Policies", ascending=False)
        )
        st.bar_chart(policy_counts, x="policy_type", y="Policies")

    with right:
        st.subheader("Claims by status")
        claim_counts = (
            claims.groupby("claim_status", as_index=False)
            .size()
            .rename(columns={"size": "Claims"})
            .sort_values("Claims", ascending=False)
        )
        st.bar_chart(claim_counts, x="claim_status", y="Claims")

    st.subheader("Customers by state")
    state_counts = (
        customers.groupby("state", as_index=False)
        .size()
        .rename(columns={"size": "Customers"})
        .sort_values("Customers", ascending=False)
    )
    st.bar_chart(state_counts.head(15), x="state", y="Customers", horizontal=True)

elif page == "Policies":
    st.header("Policy analysis")
    type_options = sorted(policies["policy_type"].dropna().unique().tolist())
    status_options = sorted(policies["policy_status"].dropna().unique().tolist())
    filter_columns = st.columns(2)
    selected_types = filter_columns[0].multiselect(
        "Policy type", type_options, default=type_options
    )
    selected_statuses = filter_columns[1].multiselect(
        "Policy status", status_options, default=status_options
    )
    filtered = policies.loc[
        policies["policy_type"].isin(selected_types)
        & policies["policy_status"].isin(selected_statuses)
    ]
    total_premium = filtered["premium_amount"].sum()
    metrics = st.columns(3)
    metrics[0].metric("Matching policies", f"{len(filtered):,}")
    metrics[1].metric("Total premiums", currency(total_premium))
    metrics[2].metric(
        "Average premium",
        currency(filtered["premium_amount"].mean()) if not filtered.empty else "₹0",
    )
    premiums = (
        filtered.groupby("policy_type", as_index=False)["premium_amount"]
        .sum()
        .sort_values("premium_amount", ascending=False)
        .rename(columns={"premium_amount": "Premium amount"})
    )
    st.subheader("Premiums by policy type")
    if not premiums.empty:
        st.bar_chart(premiums, x="policy_type", y="Premium amount")
    st.subheader("Policy records")
    st.dataframe(filtered, hide_index=True)

elif page == "Claims":
    st.header("Claims analysis")
    types = sorted(claims["claim_type"].dropna().unique().tolist())
    statuses = sorted(claims["claim_status"].dropna().unique().tolist())
    severities = sorted(claims["damage_severity"].dropna().unique().tolist())
    filters = st.columns(3)
    selected_types = filters[0].multiselect("Claim type", types, default=types)
    selected_statuses = filters[1].multiselect(
        "Claim status", statuses, default=statuses
    )
    selected_severities = filters[2].multiselect(
        "Damage severity", severities, default=severities
    )
    filtered = claims.loc[
        claims["claim_type"].isin(selected_types)
        & claims["claim_status"].isin(selected_statuses)
        & claims["damage_severity"].isin(selected_severities)
    ]
    metrics = st.columns(3)
    metrics[0].metric("Matching claims", f"{len(filtered):,}")
    metrics[1].metric("Claim amount", currency(filtered["claim_amount"].sum()))
    metrics[2].metric(
        "Average claim",
        currency(filtered["claim_amount"].mean()) if not filtered.empty else "₹0",
    )
    by_month = filtered.dropna(subset=["claim_date"]).copy()
    if not by_month.empty:
        by_month["Month"] = by_month["claim_date"].dt.to_period("M").astype(str)
        trend = (
            by_month.groupby("Month", as_index=False)["claim_amount"]
            .sum()
            .rename(columns={"claim_amount": "Claim amount"})
        )
        st.subheader("Claim amount by month")
        st.line_chart(trend, x="Month", y="Claim amount")
    st.subheader("Claim records")
    st.dataframe(filtered, hide_index=True)

elif page == "Customers":
    st.header("Customer analysis")
    states = sorted(customers["state"].dropna().unique().tolist())
    selected_states = st.multiselect("State", states, default=states)
    filtered = customers.loc[customers["state"].isin(selected_states)]
    metrics = st.columns(3)
    metrics[0].metric("Customers", f"{len(filtered):,}")
    metrics[1].metric(
        "Average age",
        f"{filtered['age'].mean():.1f}" if filtered["age"].notna().any() else "N/A",
    )
    metrics[2].metric("States represented", f"{filtered['state'].nunique():,}")
    left, right = st.columns(2)
    with left:
        st.subheader("Customers by state")
        state_counts = (
            filtered.groupby("state", as_index=False)
            .size()
            .rename(columns={"size": "Customers"})
            .sort_values("Customers", ascending=False)
        )
        if not state_counts.empty:
            st.bar_chart(state_counts, x="state", y="Customers", horizontal=True)
    with right:
        st.subheader("Customers by age")
        ages = filtered.dropna(subset=["age"])
        if not ages.empty:
            age_counts = (
                ages.assign(Age=ages["age"].astype(int))
                .groupby("Age", as_index=False)
                .size()
                .rename(columns={"size": "Customers"})
            )
            st.bar_chart(age_counts, x="Age", y="Customers")
    st.subheader("Customer records")
    st.dataframe(filtered, hide_index=True)

else:
    st.header("Vehicles and payments")
    left, right = st.columns(2)
    with left:
        st.subheader("Vehicles by type and fuel")
        vehicle_summary = (
            vehicles.groupby(["vehicle_type", "fuel_type"], as_index=False)
            .size()
            .rename(columns={"size": "Vehicles"})
            .sort_values("Vehicles", ascending=False)
        )
        st.bar_chart(
            vehicle_summary,
            x="vehicle_type",
            y="Vehicles",
            color="fuel_type",
            stack=True,
        )
        st.caption(
            "Average vehicle value: "
            + currency(vehicles["vehicle_value"].mean())
        )
    with right:
        st.subheader("Payments by status")
        payment_summary = (
            payments.groupby("payment_status", as_index=False)["payment_amount"]
            .sum()
            .rename(columns={"payment_amount": "Payment amount"})
            .sort_values("Payment amount", ascending=False)
        )
        st.bar_chart(payment_summary, x="payment_status", y="Payment amount")
        st.metric("Total payments", currency(payments["payment_amount"].sum()))

    st.subheader("Vehicle records")
    st.dataframe(vehicles, hide_index=True)
    st.subheader("Payment records")
    st.dataframe(payments, hide_index=True)
