import cadquery as cq
import numpy as np
from sklearn.linear_model import LinearRegression
import optuna
import matplotlib.pyplot as plt
import os

# -----------------------------
# 1) Surrogate training (fake physics data)
# -----------------------------
# Cooling vs diameter: made-up but nonlinear-ish curve
diameters_train = np.array([2, 3, 4, 5, 6]).reshape(-1, 1)
cooling_train = np.array([8, 18, 32, 50, 70])  # synthetic cooling trend
cooling_model = LinearRegression().fit(diameters_train, cooling_train)

# -----------------------------
# 2) Constraint checker
# -----------------------------
def is_valid(diameter, wall_thickness):
    """
    Hard rules:
    - wall_thickness >= 1.0 mm
    - 2.0 mm <= diameter <= 6.0 mm
    """
    if wall_thickness < 1.0:
        return False
    if diameter < 2.0 or diameter > 6.0:
        return False
    return True

# -----------------------------
# 3) Geometry generator
# -----------------------------
def generate_geometry(diameter, angle_deg=20, count=3, spacing=10.0,
                      side_channels=False, bottom_channels=False):
    """
    Multi-face cooling block:
    - Top channels (always on)
    - Optional side channels
    - Optional bottom channels
    """

    block = cq.Workplane("XY").box(50, 30, 20)

    # -----------------------------
    # Top channels (existing)
    # -----------------------------
    start_x = - (spacing * (count - 1)) / 2.0
    for i in range(count):
        x = start_x + i * spacing
        block = (
            block
            .faces(">Z")
            .workplane()
            .center(x, 0)
            .transformed(rotate=(angle_deg, 0, 0))
            .hole(diameter, 30)
        )

    # -----------------------------
    # Side channels (new)
    # -----------------------------
    if side_channels:
        start_z = -5
        for i in range(count):
            z = start_z + i * 5
            block = (
                block
                .faces(">X")  # right face
                .workplane()
                .center(0, z)
                .transformed(rotate=(0, angle_deg, 0))
                .hole(diameter, 40)
            )

    # -----------------------------
    # Bottom channels (new)
    # -----------------------------
    if bottom_channels:
        start_x = - (spacing * (count - 1)) / 2.0
        for i in range(count):
            x = start_x + i * spacing
            block = (
                block
                .faces("<Z")  # bottom face
                .workplane()
                .center(x, 0)
                .transformed(rotate=(-angle_deg, 0, 0))
                .hole(diameter, 30)
            )

    return block

# -----------------------------
# 4) Surrogate physics models
# -----------------------------
def predict_cooling(diameter):
    """
    Cooling surrogate: uses trained linear model on diameter.
    Higher = better.
    """
    return float(cooling_model.predict([[diameter]])[0])

def predict_pressure_penalty(diameter):
    """
    Simple analytic surrogate:
    Smaller diameter -> higher pressure drop.
    We treat 1/diameter as a 'penalty' to minimize.
    """
    return 1.0 / diameter

# -----------------------------
# 5) Objective function + trial logging
# -----------------------------
all_trials = []

def objective(trial):
    # Design variables
    diameter = trial.suggest_float("diameter", 2.0, 6.0)
    wall_thickness = trial.suggest_float("wall", 0.5, 3.0)

    valid = is_valid(diameter, wall_thickness)

    if not valid:
        cooling_score = None
        pressure_penalty = None
        score = -1e6  # very bad
    else:
        cooling_score = predict_cooling(diameter)
        pressure_penalty = predict_pressure_penalty(diameter)

        # Multi-objective → scalar: maximize cooling, minimize pressure penalty.
        # You can tune weights later.
        score = cooling_score - 0.5 * pressure_penalty

    # Log trial for Pareto / analysis
    all_trials.append(
        {
            "diameter": diameter,
            "wall": wall_thickness,
            "valid": valid,
            "cooling": cooling_score,
            "pressure": pressure_penalty,
            "score": score,
        }
    )

    return score

# -----------------------------
# 6) Optimization loop
# -----------------------------
def run_optimization(n_trials=50):
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    best_value = study.best_value
    print("Best design:", best_params)
    print("Best score:", best_value)

    return best_params

# -----------------------------
# 7) Build Pareto front and plot
# -----------------------------
def build_and_save_pareto_plot(filename="pareto_cooling_pressure.png"):
    valid_points = [
        (t["cooling"], t["pressure"])
        for t in all_trials
        if t["valid"] and t["cooling"] is not None and t["pressure"] is not None
    ]

    if not valid_points:
        print("No valid designs to build Pareto front.")
        return

    coolings = np.array([p[0] for p in valid_points])
    pressures = np.array([p[1] for p in valid_points])

    # Simple Pareto: non-dominated points (maximize cooling, minimize pressure)
    pareto_mask = []
    for i in range(len(valid_points)):
        c_i, p_i = valid_points[i]
        dominated = False
        for j in range(len(valid_points)):
            if j == i:
                continue
            c_j, p_j = valid_points[j]
            # j dominates i if:
            # - j has >= cooling and <= pressure
            # - and is strictly better in at least one
            if (c_j >= c_i and p_j <= p_i) and (c_j > c_i or p_j < p_i):
                dominated = True
                break
        pareto_mask.append(not dominated)

    pareto_c = coolings[pareto_mask]
    pareto_p = pressures[pareto_mask]

    plt.figure()
    plt.scatter(pressures, coolings, alpha=0.4, label="All valid designs")
    plt.scatter(pareto_p, pareto_c, color="red", label="Pareto front")
    plt.xlabel("Pressure penalty (lower is better)")
    plt.ylabel("Cooling score (higher is better)")
    plt.title("Cooling vs Pressure trade-off")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filename, dpi=200)
    plt.close()
    print(f"Saved Pareto plot: {filename}")

# -----------------------------
# 8) Generate CAD for best design
# -----------------------------
def export_best_geometry(best_params):
    diameter = best_params["diameter"]
    # For now, fix count & spacing; you can later promote them to design variables.
    best_geom = generate_geometry(diameter=diameter, count=3, spacing=10.0)

    step_file = os.path.abspath("best_design.step")
    stl_file = os.path.abspath("best_design.stl")

    cq.exporters.export(best_geom, step_file)
    cq.exporters.export(best_geom, stl_file)

    print(f"CAD files exported:\n  {step_file}\n  {stl_file}")

# -----------------------------
# 9) Main
# -----------------------------
if __name__ == "__main__":
    best_params = run_optimization(n_trials=80)
    build_and_save_pareto_plot()
    export_best_geometry(best_params)