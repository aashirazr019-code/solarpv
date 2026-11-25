# ☀️ Solar PV Engineering Design Platform

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42.0-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/Tests-221%20Passed-brightgreen?logo=pytest&logoColor=white)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-92%25-success)](tests/)
[![Standards](https://img.shields.io/badge/Standards-BS%207671%20%7C%20IEC%2060364--7--712%20%7C%20IEC%2060269--6%20%7C%20BS%207430-blue)](#engineering-standards-conformance)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#copyright--license)

**Lead PV Systems Engineer:** Eng. Aashir  
**Platform Version:** 2.0.0 (Dynamic Multi-Inverter Release)  
**Copyright:** © 2026 Eng. Aashir. All Rights Reserved. Proprietary & Confidential.

---

## 📌 Overview

The **Solar PV Engineering Design Platform** is a deterministic, code-compliant web application for photovoltaic systems sizing, electrical engineering analysis, equipment matching, and documentation. 

Built with pure Python calculation logic and an interactive multi-page Streamlit UI, the platform covers the entire solar design pipeline from initial energy demand assessment to detailed electrical protection coordination, cable sizing, and automated documentation generation.

---

## 🚀 Key Features

* **🔌 String Sizing & MPPT Matching:** Temperature-corrected string voltage ($V_{oc}$ cold / $V_{mp}$ hot), tracking window verification, and round-robin string allocation across inverter MPPTs.
* **🏗️ Multi-Inverter Combination Engine:** Subset-sum search algorithm matching target AC power with exact and tolerance modes ($\pm 5\%$, closest, oversized, undersized) with multi-criteria ranking.
* **📏 BS 7671 Cable Sizing:** Automated cable selection across 11 installation methods from 23 conductor sizes (1mm² to 1000mm²) incorporating the Kelani Cables Table A1 dataset with coordinated $I_b \le I_n \le I_z$ protective device matching.
* **⚡ AC & DC Voltage Drop Analysis:** Precise temperature-derated resistance and reactance calculation for DC string lines, 3-phase AC feeds, and single-phase circuits.
* **🛡️ Electrical Protection Coordination:** Sizing for IEC 60269-6 gPV string fuses, DC Type II SPDs, DC disconnect switches, standard IEC 60898 MCBs, IEC 60947-2 MCCBs, Type B / Type A RCDs, and busbars.
* **🌍 Earthing Design (BS 7430):** Soil resistivity, earth rod resistance, multi-rod array quantity, and fault conductor cross-sectional area sizing.
* **📉 System Losses & Yield:** Comprehensive 8-factor loss waterfall analysis (soiling, thermal, DC cable, inverter efficiency, AC cable, shading, mismatch, availability) with specific yield ($kWh/kWp/yr$).
* **✅ Design Validation Matrix:** Central health check matrix evaluating string voltages, currents, ratios, and voltage drops against hard electrical limits.
* **📦 Automated Bill of Materials (BOM):** Takeoff schedule deriving equipment quantities directly from calculated design results.
* **📑 Formal Engineering Reports:** One-click generation of:
  * Formal **PDF Engineering Design Report** (watermarked & stamped)
  * Multi-sheet **Excel Engineering Schedules** (`.xlsx`)
  * Component **CSV Data Tables**
  * Standards-compliant **SVG Single Line Diagram (SLD)** with interactive preview

---

## 🏛️ System Architecture

```
solar-pv-platform/
├── app.py                     # Entry point & executive landing dashboard
├── requirements.txt           # Production dependencies
├── Dockerfile                 # Multi-stage production container setup
├── .streamlit/config.toml     # Production theme & server settings
├── setup_and_run.bat          # Automated local setup for Windows
├── run.bat                    # Quick launcher
├── run_tests.bat              # Test suite runner
│
├── core/                      # Pure Python calculation engine (0 UI dependencies)
│   ├── models.py              # Strongly-typed dataclasses (Panel, Inverter, Project, etc.)
│   ├── string_sizing.py       # Temperature-corrected string voltage & limits
│   ├── current_check.py       # Operating & short-circuit current compliance
│   ├── dc_ac_ratio.py         # Overloading ratio determination & margins
│   ├── mppt_allocation.py     # String-to-MPPT allocation logic
│   ├── physical_layout.py     # Geometric array layout (portrait/landscape)
│   ├── combination_search.py  # Exact & tolerance inverter subset-sum search
│   ├── ranking.py             # Multi-criteria composite configuration scoring
│   ├── cable_sizing.py        # BS 7671 Table A1 cable selection & Ib <= In <= Iz
│   ├── protection_sizing.py   # MCB, MCCB, and busbar standard series selection
│   ├── electrical_data.py     # Kelani Cables ampacity table & conductor constants
│   ├── pv_capacity.py         # Required DC capacity from energy demand & PSH
│   ├── panel_quantity.py      # Module count from DC target
│   ├── voltage_drop.py        # DC, 3-Phase AC, and Single-Phase AC impedance
│   ├── dc_protection.py       # String fuse, DC SPD, and isolator switch sizing
│   ├── ac_protection.py       # AC SPD and RCD type determination
│   ├── earthing.py            # BS 7430 earth rod resistance & array sizing
│   ├── system_losses.py       # PR, annual yield, and loss waterfall
│   ├── design_validation.py   # Code compliance matrix health check
│   ├── bom_generator.py       # Derived component takeoff generation
│   ├── pipeline.py            # End-to-end design orchestrator
│   └── validation.py          # Semiconductor & physical sanity validations
│
├── data/
│   ├── library_data.py        # Verified Yingli modules & Sunways inverters catalog
│   └── database.py            # SQLite persistence for projects, revisions & library
│
├── ui/
│   ├── styles.py              # CSS theming, badges, and watermark styles
│   ├── components.py          # Reusable UI widgets (cards, math proof panels, matrices)
│   └── equipment_forms.py     # Equipment selectors & parameter input forms
│
├── pages/                     # 27 interactive multi-page Streamlit views
│   ├── 1_📊_Dashboard.py
│   ├── 2_📁_Projects.py
│   ├── 3_🔋_Panel_Library.py
│   ├── 4_⚡_Inverter_Library.py
│   ├── ... (22 specialized engineering calculators) ...
│   ├── 24_✅_Design_Validation.py
│   ├── 25_📋_Design_Summary.py
│   ├── 26_📦_BOM.py
│   └── 27_📄_Reports.py       # Interactive PDF, Excel, CSV, and SLD exports
│
├── reports/                   # Document & diagram generation engine
│   ├── pdf_report.py          # ReportLab PDF design report with watermark
│   ├── excel_report.py        # OpenPyXL multi-sheet engineering workbook
│   ├── csv_export.py          # CSV BOM & schedule export
│   └── sld_generator.py       # IEC-compliant SVG Single Line Diagram generator
│
└── tests/                     # Automated pytest test suite (159 tests, 100% pass rate)
```

---

## ⚡ Quick Start

### 1. Prerequisites
* Python 3.10, 3.11, or 3.12 ([Download from python.org](https://www.python.org/downloads/))
* Make sure to check **"Add Python to PATH"** during installation.

### 2. Local Setup & Run

#### On Windows:
```cmd
# Navigate to the repository directory, then run:
setup_and_run.bat
```
*For subsequent launches:*
```cmd
run.bat
```

#### On Linux / macOS:
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run app.py
```

The application will open in your browser at:
👉 `http://localhost:8501`

---

## 🧪 Automated Testing

The platform includes a comprehensive test suite with 159 tests covering all core modules and the dynamic multi-inverter sizing engine:
```bash
# Run tests with coverage summary:
run_tests.bat

# Or manually:
pytest tests/ -v --cov=core --cov-report=term-missing
```

---

## 📐 Engineering Standards Conformance

| Standard | Implementation Area |
|---|---|
| **BS 7671:2008 / 2018** | AC & DC cable ampacity tables, installation methods, temperature derating, $I_b \le I_n \le I_z$ rule. |
| **Kelani Cables Table A1** | Copper conductor current-carrying capacities (23 conductor sizes from 1mm² to 1000mm²). |
| **IEC 60364-7-712** | Solar photovoltaic power supply systems requirements, DC disconnect switches, and SPD protection. |
| **IEC 60269-6** | Low-voltage fuses for the protection of solar photovoltaic systems (gPV fuses for $\ge 3$ parallel strings). |
| **IEC 62423 / IEC 62109-2** | Type B RCD residual current protection requirements for transformerless grid-tie inverters. |
| **BS 7430:2011** | Code of practice for protective earthing of electrical installations (earth rod resistance calculations). |

---

## 👨‍💼 Lead Engineer & Author

**Eng. Aashir**  
Lead Photovoltaic Systems Engineer  
*Solar PV Engineering Design Platform*

---

## 📄 Copyright & License

Copyright © 2026 **Eng. Aashir**. All Rights Reserved.  
This software and associated documentation files are proprietary and confidential. Unauthorized copying, distribution, modification, or commercial exploitation without express written permission is strictly prohibited.
