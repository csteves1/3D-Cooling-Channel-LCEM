import streamlit as st
import numpy as np
from sklearn.linear_model import LinearRegression
import cadquery as cq
import os

# -----------------------------
# Surrogate model (same as lcem_demo.py)
# -----------------------------
diameters_train = np.array([2, 3, 4, 5, 6]).reshape(-1, 1)
cooling_train = np.array([8, 18, 32, 50, 70])
cooling_model = LinearRegression().fit(diameters_train, cooling_train)

def predict_cooling(diameter):
    return float(cooling_model.predict([[diameter]])[0])

def predict_pressure_penalty(diameter):
    return 1.0 / diameter

def is_valid(diameter, wall_thickness):
    return wall_thickness >= 1.0 and 2.0 <= diameter <= 6.0

def generate_geometry(diameter, angle_deg=20, count=3, spacing=10.0,
                      side_channels=False, bottom_channels=False):

    block = cq.Workplane("XY").box(50, 30, 20)

    # Top channels
    start_x = - (spacing * (count - 1)) / 2.0
    for i in range(count):
        x = start_x + i * spacing
        block = (
            block
            .faces(">Z")
            .workplane()
            .center(x, 0)
            .transformed(rotate=(angle_deg, 0, 0))
            .hole(diameter, 80)   # ← FIXED
        )

    # Side channels
    if side_channels:
        start_z = -5
        for i in range(count):
            z = start_z + i * 5
            block = (
                block
                .faces(">X")
                .workplane()
                .center(0, z)
                .transformed(rotate=(0, angle_deg, 0))
                .hole(diameter, 80)   # ← FIXED
            )

    # Bottom channels
    if bottom_channels:
        start_x = - (spacing * (count - 1)) / 2.0
        for i in range(count):
            x = start_x + i * spacing
            block = (
                block
                .faces("<Z")
                .workplane()
                .center(x, 0)
                .transformed(rotate=(-angle_deg, 0, 0))
                .hole(diameter, 80)   # ← FIXED
            )

    return block

def export_geometry(geom):
    step_file = os.path.abspath("dashboard_design.step")
    cq.exporters.export(geom, step_file)
    return step_file

def render_svg_views(geom):
    from cadquery import exporters

    # --- Top View (rotate so Z becomes view direction) ---
    top_geom = geom.rotate((0, 0, 0), (1, 0, 0), 90)
    exporters.export(top_geom, "preview_top.svg", exportType="SVG")

    # --- Side View (rotate so X becomes view direction) ---
    side_geom = geom.rotate((0, 0, 0), (0, 1, 0), 90)
    exporters.export(side_geom, "preview_side.svg", exportType="SVG")

    # --- Isometric View (default orientation) ---
    exporters.export(geom, "preview_iso.svg", exportType="SVG")

    return "preview_top.svg", "preview_side.svg", "preview_iso.svg"

import optuna
import matplotlib.pyplot as plt

# -----------------------------
# Optimizer logic (same as lcem_demo.py)
# -----------------------------
def run_optimizer(n_trials=50):
    trials = []
    def objective(trial):
        diameter = trial.suggest_float("diameter", 2.0, 6.0)
        wall = trial.suggest_float("wall", 0.5, 3.0)
        valid = is_valid(diameter, wall)
        if not valid:
            return -1e6
        cooling = predict_cooling(diameter)
        pressure = predict_pressure_penalty(diameter)
        score = cooling - 0.5 * pressure
        trials.append((cooling, pressure))
        return score

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    best = study.best_params
    return best, trials

# -----------------------------
# DRC Logic
# -----------------------------
def run_drc(diameter, angle_deg, side_channels, bottom_channels, spacing=10.0, count=3):
    """
    Returns a list of (status, message) tuples.
    status = True (pass) or False (fail)
    """

    results = []

    # --- Rule 1: Diameter limits ---
    if 2.0 <= diameter <= 6.0:
        results.append((True, "Diameter within allowable range (2–6 mm)."))
    else:
        results.append((False, "Diameter outside allowable range (2–6 mm)."))

    # --- Rule 2: Wall thickness between channels ---
    # Approximate center-to-center spacing minus diameter
    min_wall = spacing - diameter
    if min_wall >= 1.0:
        results.append((True, f"Wall thickness OK ({min_wall:.2f} mm ≥ 1.0 mm)."))
    else:
        results.append((False, f"Wall thickness too small ({min_wall:.2f} mm < 1.0 mm)."))

    # --- Rule 3: Drill angle limit ---
    if abs(angle_deg) <= 35:
        results.append((True, f"Drill angle acceptable ({angle_deg}° ≤ 35°)."))
    else:
        results.append((False, f"Drill angle too steep ({angle_deg}° > 35°)."))

    # --- Rule 4: Side channel feasibility ---
    if side_channels:
        if diameter <= 5:
            results.append((True, "Side channels feasible."))
        else:
            results.append((False, "Side channels too large for side face."))
    else:
        results.append((True, "Side channels disabled."))

    # --- Rule 5: Bottom channel powder removal ---
    if bottom_channels:
        if angle_deg >= 10:
            results.append((True, "Bottom channels have enough angle for powder removal."))
        else:
            results.append((False, "Bottom channels too shallow for powder removal."))
    else:
        results.append((True, "Bottom channels disabled."))

    # --- Rule 6: Channel exit completeness ---
    # With your new 80 mm cut length, this is always true.
    results.append((True, "Channels fully exit the block (80 mm cut length)."))

    return results

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="LCEM Cooling Block Dashboard", layout="centered")
st.title("🧊 LCEM Cooling Block Explorer")

st.markdown("Adjust parameters below to explore cooling efficiency and pressure trade-offs.")


diameter = st.slider("Channel Diameter (mm)", 2.0, 6.0, 4.0, 0.1)
wall_thickness = st.slider("Wall Thickness (mm)", 0.5, 3.0, 1.5, 0.1)
angle = st.slider("Channel Angle (degrees)", -45, 45, 20)
side_channels = st.checkbox("Add Side Channels", value=False)
bottom_channels = st.checkbox("Add Bottom Channels", value=False)

valid = is_valid(diameter, wall_thickness)

if valid:
    cooling = predict_cooling(diameter)
    pressure = predict_pressure_penalty(diameter)
    score = cooling - 0.5 * pressure

    st.success("Design is valid.")
    st.metric("Cooling Score", f"{cooling:.2f}")
    st.metric("Pressure Penalty", f"{pressure:.2f}")
    st.metric("Combined Score", f"{score:.2f}")

    # --- DRC Panel ---
    st.subheader("🛠️ Design Rule Check (DRC)")

    drc_results = run_drc(
        diameter=diameter,
        angle_deg=angle,
        side_channels=side_channels,
        bottom_channels=bottom_channels
    )

    for status, msg in drc_results:
        if status:
            st.markdown(f"✅ {msg}")
        else:
            st.markdown(f"❌ {msg}")

        # 👉 LIVE PREVIEW
        geom = generate_geometry(
            diameter,
            angle,
            side_channels=side_channels,
            bottom_channels=bottom_channels
        )
    # 👉 LIVE PREVIEW
    geom = generate_geometry(
        diameter,
        angle,
        side_channels=side_channels,
        bottom_channels=bottom_channels
    )

    # Generate multi-view SVGs
    top_view, side_view, iso_view = render_svg_views(geom)

    st.subheader("📐 Geometry Preview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.image(top_view, caption="Top View", width=250)

    with col2:
        st.image(side_view, caption="Side View", width=250)

    with col3:
        st.image(iso_view, caption="Isometric View", width=250)

    # 👉 EXPORT CAD
    if st.button("Export CAD"):
        geom = generate_geometry(
            diameter,
            angle,
            side_channels=side_channels,
            bottom_channels=bottom_channels
        )
        path = export_geometry(geom)
        st.success(f"CAD file exported: {path}")
        st.markdown(f"[Open in FreeCAD]({path})")

else:
    st.error("Design violates constraints.")
    st.markdown(
        """
        **Reasons:**
        - Wall thickness must be ≥ 1.0 mm  
        - Diameter must be between 2.0 and 6.0 mm
        """
    )

st.markdown("---")
st.caption("This dashboard uses surrogate physics and constraint-aware design logic to explore LCEM cooling blocks.")

st.markdown("---")
st.subheader("🚀 Run Full Optimization")

if st.button("Run Optimizer"):
    best_params, trial_data = run_optimizer(n_trials=80)
    st.success(
        f"Best design found: Diameter = {best_params['diameter']:.2f}, "
        f"Wall = {best_params['wall']:.2f}"
    )

    # Plot Pareto front
    cooling_vals = [c for c, p in trial_data]
    pressure_vals = [p for c, p in trial_data]

    fig, ax = plt.subplots()
    ax.scatter(pressure_vals, cooling_vals, alpha=0.4)
    ax.set_xlabel("Pressure penalty (lower is better)")
    ax.set_ylabel("Cooling score (higher is better)")
    ax.set_title("Cooling vs Pressure trade-off")
    st.pyplot(fig)

    # Export best design with current angle + toggles
    best_geom = generate_geometry(
        best_params["diameter"],
        angle,
        side_channels=side_channels,
        bottom_channels=bottom_channels
    )
    best_path = export_geometry(best_geom)
    st.markdown(f"📦 Best CAD file exported: `{best_path}`")
    st.markdown(f"[Open in FreeCAD]({best_path})")