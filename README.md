**LCEM Cooling‑Channel Block Optimizer & Dashboard**
A surrogate‑based engineering tool for exploring, validating, and optimizing cooling‑channel block designs using LCEM‑style reasoning. This project combines:

- Surrogate physics modeling  
- Constraint‑aware design rule checks (DRC)  
- Parametric CAD generation  
- Multi‑view geometry previews  
- Optuna‑based optimization  
- Streamlit dashboard UI  
- CLI demo runner  
- Pareto trade‑off visualization  

It is designed as a fast, lightweight alternative to full CFD/FEA for early‑stage thermal design and trade studies.



**Overview**
Cooling‑channel blocks are used in propulsion cooling jackets, thermal management systems, and high‑heat‑flux aerospace hardware. This tool provides:

- A **surrogate cooling model** trained on synthetic data  
- A **pressure‑penalty surrogate**  
- A **constraint checker** enforcing manufacturability and geometry rules  
- A **parametric CAD generator** using CadQuery  
- A **Streamlit dashboard** for interactive exploration  
- A **CLI demo** for batch optimization and CAD export  

The result is a rapid design‑space exploration tool suitable for concept development and engineering education.



**Features**
**Surrogate Modeling**
- Linear regression cooling model  
- Analytic pressure‑penalty model  
- Fast evaluation for optimization loops  

**Design Rule Checks (DRC)**
- Diameter limits  
- Wall thickness limits  
- Drill angle limits  
- Side/bottom channel feasibility  
- Powder‑removal constraints  
- Channel exit completeness  

**CAD Generation**
- Parametric cooling block  
- Top, side, and bottom channels  
- Multi‑view SVG previews  
- STEP/STL export for CAD tools  

**Optimization**
- Optuna search over diameter & wall thickness  
- Combined objective: maximize cooling, minimize pressure  
- Pareto front visualization  

**Dashboard UI**
- Real‑time metrics  
- Geometry previews  
- DRC panel  
- CAD export button  
- Optimizer button  



**Project Structure**
```
3D_Cooling_Channel_Optimizer/
│
├── Icem_dashboard.py            # Streamlit dashboard UI
├── Icem_demo.py                 # CLI demo runner (optimizer + CAD export)
│
├── best_design.step             # Exported CAD (demo)
├── best_design.stl              # Exported CAD (demo)
├── dashboard_design.step        # Exported CAD (dashboard)
│
├── preview_top.svg              # Top view
├── preview_side.svg             # Side view
├── preview_iso.svg              # Isometric view
│
├── pareto_cooling_pressure.png  # Pareto plot (demo)
│
├── requirements.txt             # Dependencies
└── README.md                    # Project documentation
```



**Installation**
Install dependencies:

```bash
pip install -r requirements.txt
```



**Running the Dashboard**
Launch the interactive Streamlit UI:

```bash
streamlit run Icem_dashboard.py
```

**Dashboard Features**
- Adjust diameter, wall thickness, and angle  
- Toggle side/bottom channels  
- View cooling score, pressure penalty, and combined score  
- Run DRC checks  
- Preview geometry (top, side, iso)  
- Export CAD as STEP  
- Run full optimization from the UI  



**Running the CLI Demo**
The demo script runs the full optimization pipeline without the UI.

```bash
python Icem_demo.py
```

**What the demo does**
- Trains surrogate cooling model  
- Runs Optuna optimization (80 trials)  
- Builds Pareto front  
- Saves:
  - `pareto_cooling_pressure.png`  
  - `best_design.step`  
  - `best_design.stl`  

**Example output**
```
Best design: {'diameter': 3.82, 'wall': 1.21}
Best score: 39.9
Saved Pareto plot: pareto_cooling_pressure.png
CAD files exported:
  best_design.step
  best_design.stl
```



**Design Parameters**
| Parameter | Range | Notes |
|----------|--------|-------|
| Diameter | 2.0–6.0 mm | Affects cooling & pressure |
| Wall Thickness | 0.5–3.0 mm | Must be ≥ 1.0 mm for validity |
| Angle | −45° to +45° | Drill angle constraint ≤ 35° |
| Side Channels | On/Off | Feasible only for smaller diameters |
| Bottom Channels | On/Off | Requires angle ≥ 10° |

---

**Optimization Logic**
Objective function:

\[
\text{score} = \text{cooling} - 0.5 \cdot \text{pressure penalty}
\]

Where:

- Cooling is predicted by a surrogate model  
- Pressure penalty is \(1 / \text{diameter}\)  

Pareto front identifies non‑dominated designs maximizing cooling while minimizing pressure.



**Example Output (JSON‑style)**
{
  "diameter": 3.8,
  "wall": 1.2,
  "cooling_score": 40.2,
  "pressure_penalty": 0.26,
  "combined_score": 39.9,
  "valid": true,
  "cad_file": "best_design.step"
}
```



**Future Improvements**
- Neural surrogate model  
- Multi‑objective optimization  
- Real‑time 3D viewer  
- Export to GLTF/STL from dashboard  
- Additional DRC rules (vibration, fatigue)  
- Parametric block dimensions  



**Summary**
This project demonstrates:

- Surrogate physics modeling  
- Constraint‑aware engineering design  
- CAD automation  
- Optimization and Pareto analysis  
- UI/UX for engineering tools  

It is a complete, end‑to‑end example of AI‑assisted engineering design suitable for aerospace, thermal systems, and advanced manufacturing workflows.