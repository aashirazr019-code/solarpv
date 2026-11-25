from core.models import Panel, Inverter

PANEL_FAMILIES = [
    {
        "series": "yingli-ylmj-144-m10",
        "description": "YLM-J 144 CELL (M10), 530-550W, N-type Mono, 144 cells, 2.279x1.134m, temp_coeff_voc=-0.27, temp_coeff_isc=0.05, temp_coeff_pmax=-0.35, max_sys=1500V, max_fuse=25A",
        "variants": [
            {"wp": 530.0, "voc": 49.22, "vmp": 41.40, "isc": 13.69, "imp": 12.81},
            {"wp": 535.0, "voc": 49.37, "vmp": 41.55, "isc": 13.76, "imp": 12.88},
            {"wp": 540.0, "voc": 49.52, "vmp": 41.70, "isc": 13.83, "imp": 12.95},
            {"wp": 545.0, "voc": 49.67, "vmp": 41.85, "isc": 13.90, "imp": 13.03},
            {"wp": 550.0, "voc": 49.82, "vmp": 42.00, "isc": 13.97, "imp": 13.10}
        ]
    },
    {
        "series": "yingli-panda3-cf72-550-575",
        "description": "PANDA 3.0 PRO (CF72, 550-575W), N-type TOPCon Bifacial, 144 cells, 2.278x1.134m, 30mm thick, 32kg, temp_coeff_voc=-0.25, temp_coeff_isc=0.046, temp_coeff_pmax=-0.30, max_sys=1500V, max_fuse=30A",
        "variants": [
            {"wp": 550.0, "voc": 50.26, "vmp": 41.57, "isc": 13.99, "imp": 13.24},
            {"wp": 555.0, "voc": 50.46, "vmp": 41.76, "isc": 14.07, "imp": 13.30},
            {"wp": 560.0, "voc": 50.66, "vmp": 41.94, "isc": 14.14, "imp": 13.36},
            {"wp": 565.0, "voc": 50.86, "vmp": 42.13, "isc": 14.20, "imp": 13.42},
            {"wp": 570.0, "voc": 51.06, "vmp": 42.29, "isc": 14.26, "imp": 13.48},
            {"wp": 575.0, "voc": 51.26, "vmp": 42.47, "isc": 14.32, "imp": 13.54}
        ]
    },
    {
        "series": "yingli-panda3-cf72-560-585",
        "description": "PANDA 3.0 PRO (CF72, 560-585W), same physical as above",
        "variants": [
            {"wp": 560.0, "voc": 50.66, "vmp": 41.94, "isc": 14.14, "imp": 13.36},
            {"wp": 565.0, "voc": 50.86, "vmp": 42.13, "isc": 14.20, "imp": 13.42},
            {"wp": 570.0, "voc": 51.06, "vmp": 42.29, "isc": 14.26, "imp": 13.48},
            {"wp": 575.0, "voc": 51.26, "vmp": 42.47, "isc": 14.32, "imp": 13.54},
            {"wp": 580.0, "voc": 51.46, "vmp": 42.65, "isc": 14.38, "imp": 13.60},
            {"wp": 585.0, "voc": 51.66, "vmp": 42.83, "isc": 14.44, "imp": 13.66}
        ]
    },
    {
        "series": "yingli-panda3-pro2-cf66-610-630",
        "description": "PANDA 3.0 Pro 2 (CF66, 610-630W), N-type TOPCon Bifacial, 132 cells, 2.382x1.134m, temp_coeff_voc=-0.24, temp_coeff_isc=0.042, temp_coeff_pmax=-0.29, max_fuse=30A",
        "variants": [
            {"wp": 610.0, "voc": 49.01, "vmp": 41.03, "isc": 15.83, "imp": 14.87},
            {"wp": 615.0, "voc": 49.31, "vmp": 41.34, "isc": 15.86, "imp": 14.88},
            {"wp": 620.0, "voc": 49.08, "vmp": 41.14, "isc": 16.04, "imp": 15.07},
            {"wp": 625.0, "voc": 49.26, "vmp": 41.31, "isc": 16.11, "imp": 15.13},
            {"wp": 630.0, "voc": 49.44, "vmp": 41.47, "isc": 16.18, "imp": 15.19}
        ]
    },
    {
        "series": "yingli-panda3-pro1-c78-635-660",
        "description": "PANDA 3.0 Pro 1 (C78, 635-660W), N-type TOPCon Bifacial, 156 cells, 2.465x1.134m, temp_coeff_voc=-0.24, temp_coeff_isc=0.042, temp_coeff_pmax=-0.29, max_fuse=30A",
        "variants": [
            {"wp": 635.0, "voc": 57.42, "vmp": 47.57, "isc": 14.01, "imp": 13.35},
            {"wp": 640.0, "voc": 57.62, "vmp": 47.73, "isc": 14.05, "imp": 13.41},
            {"wp": 645.0, "voc": 57.82, "vmp": 47.89, "isc": 14.10, "imp": 13.47},
            {"wp": 650.0, "voc": 58.02, "vmp": 48.04, "isc": 14.14, "imp": 13.53},
            {"wp": 655.0, "voc": 58.22, "vmp": 48.21, "isc": 14.19, "imp": 13.59},
            {"wp": 660.0, "voc": 58.42, "vmp": 48.35, "isc": 14.23, "imp": 13.65}
        ]
    },
    # --- Additional Global Tier-1 Manufacturers ---
    {
        "series": "jinko-tiger-neo-72hl4-560-585",
        "manufacturer": "Jinko Solar",
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 144,
        "description": "Tiger Neo 72HL4-BDV (560-585W), N-type TOPCon Bifacial, 144 cells, 2.278x1.134m, temp_coeff_voc=-0.25, temp_coeff_isc=0.045, temp_coeff_pmax=-0.30, max_sys=1500V, max_fuse=30A",
        "variants": [
            {"wp": 560.0, "voc": 50.47, "vmp": 41.95, "isc": 14.07, "imp": 13.35},
            {"wp": 565.0, "voc": 50.67, "vmp": 42.14, "isc": 14.13, "imp": 13.41},
            {"wp": 570.0, "voc": 50.87, "vmp": 42.33, "isc": 14.19, "imp": 13.47},
            {"wp": 575.0, "voc": 51.07, "vmp": 42.52, "isc": 14.25, "imp": 13.53},
            {"wp": 580.0, "voc": 51.27, "vmp": 42.71, "isc": 14.31, "imp": 13.59},
            {"wp": 585.0, "voc": 51.47, "vmp": 42.90, "isc": 14.37, "imp": 13.64}
        ]
    },
    {
        "series": "jinko-tiger-neo-78hl4-610-635",
        "manufacturer": "Jinko Solar",
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 156,
        "description": "Tiger Neo 78HL4-BDV (610-635W), N-type TOPCon Bifacial, 156 cells, 2.465x1.134m, temp_coeff_voc=-0.25, temp_coeff_isc=0.045, temp_coeff_pmax=-0.30, max_sys=1500V, max_fuse=30A",
        "variants": [
            {"wp": 610.0, "voc": 54.70, "vmp": 45.54, "isc": 14.06, "imp": 13.40},
            {"wp": 615.0, "voc": 54.90, "vmp": 45.73, "isc": 14.11, "imp": 13.45},
            {"wp": 620.0, "voc": 55.10, "vmp": 45.92, "isc": 14.16, "imp": 13.50},
            {"wp": 625.0, "voc": 55.30, "vmp": 46.11, "isc": 14.21, "imp": 13.55},
            {"wp": 630.0, "voc": 55.50, "vmp": 46.30, "isc": 14.26, "imp": 13.61},
            {"wp": 635.0, "voc": 55.70, "vmp": 46.49, "isc": 14.31, "imp": 13.66}
        ]
    },
    {
        "series": "longi-himo7-lr5-72hgd-570-590",
        "manufacturer": "LONGi Solar",
        "cell_technology": "HPDC Bifacial Dual-Glass",
        "cell_count": 144,
        "description": "Hi-MO 7 LR5-72HGD (570-590W), HPDC Dual-Glass, 144 cells, 2.278x1.134m, temp_coeff_voc=-0.23, temp_coeff_isc=0.050, temp_coeff_pmax=-0.28, max_sys=1500V, max_fuse=30A",
        "variants": [
            {"wp": 570.0, "voc": 50.70, "vmp": 42.50, "isc": 14.12, "imp": 13.41},
            {"wp": 575.0, "voc": 50.90, "vmp": 42.70, "isc": 14.18, "imp": 13.47},
            {"wp": 580.0, "voc": 51.10, "vmp": 42.90, "isc": 14.24, "imp": 13.52},
            {"wp": 585.0, "voc": 51.30, "vmp": 43.10, "isc": 14.30, "imp": 13.57},
            {"wp": 590.0, "voc": 51.50, "vmp": 43.30, "isc": 14.36, "imp": 13.63}
        ]
    },
    {
        "series": "ja-deepblue4-jam72d42-605-630",
        "manufacturer": "JA Solar",
        "cell_technology": "N-type Bifacial",
        "cell_count": 144,
        "description": "DeepBlue 4.0 Pro JAM72D42 (605-630W), N-type Bifacial, 144 cells, 2.382x1.134m, temp_coeff_voc=-0.26, temp_coeff_isc=0.046, temp_coeff_pmax=-0.30, max_sys=1500V, max_fuse=30A",
        "variants": [
            {"wp": 605.0, "voc": 50.80, "vmp": 42.30, "isc": 15.10, "imp": 14.30},
            {"wp": 610.0, "voc": 51.00, "vmp": 42.50, "isc": 15.16, "imp": 14.35},
            {"wp": 615.0, "voc": 51.20, "vmp": 42.70, "isc": 15.22, "imp": 14.40},
            {"wp": 620.0, "voc": 51.40, "vmp": 42.90, "isc": 15.28, "imp": 14.45},
            {"wp": 625.0, "voc": 51.60, "vmp": 43.10, "isc": 15.34, "imp": 14.50},
            {"wp": 630.0, "voc": 51.80, "vmp": 43.30, "isc": 15.40, "imp": 14.55}
        ]
    }
]

INVERTER_FAMILIES = [
    {
        "series": "sunways-sth-3-8ktl-ls",
        "description": "STH-3~8KTL-LS (1-Phase Hybrid, LV)",
        "ac_voltage": 230,
        "max_dc_voltage": 600,
        "efficiency": 97.6,
        "string_inputs_per_mppt": 1,
        "variants": [
            {"model": "STH-3KTL-LS", "kw": 3.0, "mppt_count": 1, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25},
            {"model": "STH-3.6KTL-LS", "kw": 3.6, "mppt_count": 1, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25},
            {"model": "STH-4KTL-LS", "kw": 4.0, "mppt_count": 2, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25},
            {"model": "STH-4.6KTL-LS", "kw": 4.6, "mppt_count": 2, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25},
            {"model": "STH-5KTL-LS", "kw": 5.0, "mppt_count": 2, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25},
            {"model": "STH-6KTL-LS", "kw": 6.0, "mppt_count": 2, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25},
            {"model": "STH-7KTL-LS", "kw": 7.0, "mppt_count": 2, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25},
            {"model": "STH-8KTL-LS", "kw": 8.0, "mppt_count": 2, "mppt_range": [80, 550], "max_current": 20, "max_isc": 25}
        ]
    },
    {
        "series": "sunways-sth-4-12ktl-ht-p",
        "description": "STH-4~12KTL-HT-P (3-Phase Hybrid, HV)",
        "ac_voltage": 400,
        "max_dc_voltage": 1000,
        "efficiency": 98.2,
        "string_inputs_per_mppt": 1,
        "variants": [
            {"model": "STH-4KTL-HT-P", "kw": 4.0, "mppt_count": 2, "mppt_range": [150, 850], "max_current": 16, "max_isc": 18},
            {"model": "STH-5KTL-HT-P", "kw": 5.0, "mppt_count": 2, "mppt_range": [150, 850], "max_current": 16, "max_isc": 18},
            {"model": "STH-6KTL-HT-P", "kw": 6.0, "mppt_count": 2, "mppt_range": [200, 850], "max_current": 16, "max_isc": 18},
            {"model": "STH-8KTL-HT-P", "kw": 8.0, "mppt_count": 2, "mppt_range": [200, 850], "max_current": 16, "max_isc": 18},
            {"model": "STH-10KTL-HT-P", "kw": 10.0, "mppt_count": 2, "mppt_range": [200, 850], "max_current": 16, "max_isc": 18},
            {"model": "STH-12KTL-HT-P", "kw": 12.0, "mppt_count": 2, "mppt_range": [200, 850], "max_current": 16, "max_isc": 18}
        ]
    },
    {
        "series": "sunways-sts-3-6ktl-p",
        "description": "STS-3~6KTL-P (1-Phase Grid-tie)",
        "ac_voltage": 230,
        "max_dc_voltage": 600,
        "efficiency": 98.1,
        "string_inputs_per_mppt": 1,
        "variants": [
            {"model": "STS-3KTL-P", "kw": 3.0, "mppt_count": 2, "mppt_range": [100, 550], "max_current": 15, "max_isc": 20},
            {"model": "STS-3.6KTL-P", "kw": 3.6, "mppt_count": 2, "mppt_range": [100, 550], "max_current": 15, "max_isc": 20},
            {"model": "STS-4KTL-P", "kw": 4.0, "mppt_count": 2, "mppt_range": [100, 550], "max_current": 15, "max_isc": 20},
            {"model": "STS-4.6KTL-P", "kw": 4.6, "mppt_count": 2, "mppt_range": [100, 550], "max_current": 15, "max_isc": 20},
            {"model": "STS-5KTL-P", "kw": 5.0, "mppt_count": 2, "mppt_range": [100, 550], "max_current": 15, "max_isc": 20},
            {"model": "STS-6KTL-P", "kw": 6.0, "mppt_count": 2, "mppt_range": [100, 550], "max_current": 15, "max_isc": 20}
        ]
    },
    {
        "series": "sunways-stt-4-25ktl-p",
        "description": "STT-4~25KTL-P (3-Phase Grid-tie)",
        "ac_voltage": 400,
        "max_dc_voltage": 1100,
        "efficiency": 98.6,
        "string_inputs_per_mppt": 1,
        "variants": [
            {"model": "STT-4KTL-P", "kw": 4.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 15, "max_isc": 20},
            {"model": "STT-5KTL-P", "kw": 5.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 15, "max_isc": 20},
            {"model": "STT-6KTL-P", "kw": 6.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 15, "max_isc": 20},
            {"model": "STT-8KTL-P", "kw": 8.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 15, "max_isc": 20},
            {"model": "STT-10KTL-P", "kw": 10.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 15, "max_isc": 40},
            {"model": "STT-12KTL-P", "kw": 12.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 15, "max_isc": 40},
            {"model": "STT-15KTL-P", "kw": 15.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 15, "max_isc": 40},
            {"model": "STT-17KTL-P", "kw": 17.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 30, "max_isc": 40},
            {"model": "STT-20KTL-P", "kw": 20.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 30, "max_isc": 40},
            {"model": "STT-25KTL-P", "kw": 25.0, "mppt_count": 2, "mppt_range": [160, 1000], "max_current": 30, "max_isc": 40}
        ]
    },
    {
        "series": "sunways-stt-80-125ktl",
        "description": "STT-80/100/110/125KTL (3-Phase, Ten MPPT)",
        "ac_voltage": 400,
        "max_dc_voltage": 1100,
        "efficiency": 98.8,
        "string_inputs_per_mppt": 2,
        "variants": [
            {"model": "STT-80KTL", "kw": 80.0, "mppt_count": 8, "mppt_range": [200, 950], "max_current": 26, "max_isc": 40, "max_ac": 127.0, "ac_v": 400, "dc_input": 104.0},
            {"model": "STT-100KTL", "kw": 100.0, "mppt_count": 10, "mppt_range": [200, 950], "max_current": 26, "max_isc": 40, "max_ac": 158.8, "ac_v": 400, "dc_input": 130.0},
            {"model": "STT-110KTL", "kw": 110.0, "mppt_count": 10, "mppt_range": [200, 950], "max_current": 26, "max_isc": 40, "max_ac": 174.8, "ac_v": 400, "dc_input": 143.0},
            {"model": "STT-100KTL-HV", "kw": 100.0, "mppt_count": 10, "mppt_range": [200, 950], "max_current": 26, "max_isc": 40, "max_ac": 127.0, "ac_v": 500, "dc_input": 130.0},
            {"model": "STT-125KTL-HV", "kw": 125.0, "mppt_count": 10, "mppt_range": [200, 950], "max_current": 26, "max_isc": 40, "max_ac": 158.8, "ac_v": 500, "dc_input": 162.5}
        ]
    },
    # --- Additional Global Tier-1 Manufacturers ---
    {
        "series": "huawei-sun2000-8-25ktl-m5",
        "manufacturer": "Huawei",
        "description": "SUN2000-8~25KTL-M5 (3-Phase Grid-tie), max_dc_voltage=1100V, ac_voltage=400V, efficiency=98.4%, string_inputs_per_mppt=2",
        "max_dc_voltage": 1100.0,
        "ac_voltage": 400.0,
        "efficiency": 98.4,
        "string_inputs_per_mppt": 2,
        "variants": [
            {"model": "SUN2000-8KTL-M5", "kw": 8.0, "mppt_count": 2, "mppt_range": (160, 980), "max_current": 30.0, "max_isc": 40.0, "max_ac": 12.8, "dc_input": 12.0},
            {"model": "SUN2000-10KTL-M5", "kw": 10.0, "mppt_count": 2, "mppt_range": (160, 980), "max_current": 30.0, "max_isc": 40.0, "max_ac": 16.0, "dc_input": 15.0},
            {"model": "SUN2000-12KTL-M5", "kw": 12.0, "mppt_count": 2, "mppt_range": (160, 980), "max_current": 30.0, "max_isc": 40.0, "max_ac": 19.3, "dc_input": 18.0},
            {"model": "SUN2000-15KTL-M5", "kw": 15.0, "mppt_count": 2, "mppt_range": (160, 980), "max_current": 30.0, "max_isc": 40.0, "max_ac": 24.1, "dc_input": 22.5},
            {"model": "SUN2000-17KTL-M5", "kw": 17.0, "mppt_count": 2, "mppt_range": (160, 980), "max_current": 30.0, "max_isc": 40.0, "max_ac": 27.3, "dc_input": 25.5},
            {"model": "SUN2000-20KTL-M5", "kw": 20.0, "mppt_count": 2, "mppt_range": (160, 980), "max_current": 30.0, "max_isc": 40.0, "max_ac": 32.0, "dc_input": 30.0},
            {"model": "SUN2000-25KTL-M5", "kw": 25.0, "mppt_count": 2, "mppt_range": (160, 980), "max_current": 30.0, "max_isc": 40.0, "max_ac": 40.0, "dc_input": 37.5}
        ]
    },
    {
        "series": "sungrow-sg5-20rt",
        "manufacturer": "Sungrow",
        "description": "SG5.0~20RT (3-Phase Grid-tie), max_dc_voltage=1100V, ac_voltage=400V, efficiency=98.5%, string_inputs_per_mppt=1",
        "max_dc_voltage": 1100.0,
        "ac_voltage": 400.0,
        "efficiency": 98.5,
        "string_inputs_per_mppt": 1,
        "variants": [
            {"model": "SG5.0RT", "kw": 5.0, "mppt_count": 2, "mppt_range": (160, 1000), "max_current": 12.5, "max_isc": 16.0, "max_ac": 8.0, "dc_input": 7.5},
            {"model": "SG10RT", "kw": 10.0, "mppt_count": 2, "mppt_range": (160, 1000), "max_current": 25.0, "max_isc": 32.0, "max_ac": 16.0, "dc_input": 15.0},
            {"model": "SG15RT", "kw": 15.0, "mppt_count": 2, "mppt_range": (160, 1000), "max_current": 25.0, "max_isc": 32.0, "max_ac": 24.0, "dc_input": 22.5},
            {"model": "SG20RT", "kw": 20.0, "mppt_count": 2, "mppt_range": (160, 1000), "max_current": 25.0, "max_isc": 32.0, "max_ac": 32.0, "dc_input": 30.0}
        ]
    }
]

def build_panel(family, variant):
    from core.models import Panel
    
    desc = family.get("description", "")
    
    temp_coeff_voc = -0.27
    temp_coeff_isc = 0.05
    temp_coeff_pmax = -0.35
    max_sys = 1500.0
    max_fuse = 25.0
    length_m = 2.279
    width_m = 1.134
    
    if "temp_coeff_voc=" in desc:
        parts = desc.split("temp_coeff_voc=")[1].split(",")
        temp_coeff_voc = float(parts[0].strip())
    if "temp_coeff_isc=" in desc:
        parts = desc.split("temp_coeff_isc=")[1].split(",")
        temp_coeff_isc = float(parts[0].strip())
    if "temp_coeff_pmax=" in desc:
        parts = desc.split("temp_coeff_pmax=")[1].split(",")
        temp_coeff_pmax = float(parts[0].strip())
    
    if "max_fuse=" in desc:
        parts = desc.split("max_fuse=")[1].split("A")
        max_fuse = float(parts[0].strip())
        
    if "max_sys=" in desc:
        parts = desc.split("max_sys=")[1].split("V")
        max_sys = float(parts[0].strip())
        
    if "2.278x1.134m" in desc:
        length_m, width_m = 2.278, 1.134
    elif "2.382x1.134m" in desc:
        length_m, width_m = 2.382, 1.134
    elif "2.465x1.134m" in desc:
        length_m, width_m = 2.465, 1.134
        
    return Panel(
        id=f"lib-{family['series']}-{variant['wp']}",
        manufacturer=family.get("manufacturer", "Yingli"),
        model=f"{family['series']} {variant['wp']}W",
        rated_power_wp=variant["wp"],
        voc=variant["voc"],
        vmp=variant["vmp"],
        isc=variant["isc"],
        imp=variant["imp"],
        max_system_voltage=max_sys,
        max_series_fuse=max_fuse,
        temp_coeff_voc=temp_coeff_voc,
        temp_coeff_isc=temp_coeff_isc,
        temp_coeff_pmax=temp_coeff_pmax,
        temp_coeff_vmp=None,
        length_m=length_m,
        width_m=width_m,
        thickness_mm=30.0,
        weight_kg=32.0,
        cell_technology=family.get("cell_technology", "N-type"),
        cell_count=family.get("cell_count", 144),
        source="library"
    )

def build_inverter(family, variant):
    from core.models import Inverter
    import math
    
    ac_voltage = variant.get("ac_v", family["ac_voltage"])
    max_dc_input_power_kw = variant.get("dc_input", variant["kw"] * 1.35)
    
    max_ac_current = variant.get("max_ac", None)
    if max_ac_current is None:
        max_ac_current = (variant["kw"] * 1000) / (math.sqrt(3) * ac_voltage)
        max_ac_current = round(max_ac_current, 1)
        
    return Inverter(
        id=f"lib-{variant['model']}",
        manufacturer=family.get("manufacturer", "Sunways"),
        model=variant["model"],
        rated_ac_power_kw=variant["kw"],
        max_dc_input_power_kw=max_dc_input_power_kw,
        max_dc_voltage_v=family["max_dc_voltage"],
        mppt_voltage_min_v=variant["mppt_range"][0],
        mppt_voltage_max_v=variant["mppt_range"][1],
        mppt_count=variant["mppt_count"],
        string_inputs_per_mppt=family["string_inputs_per_mppt"],
        max_input_current_per_mppt_a=variant["max_current"],
        max_isc_per_mppt_a=variant["max_isc"],
        max_total_dc_current_a=variant["max_current"] * variant["mppt_count"],
        ac_voltage=ac_voltage,
        rated_ac_current_a=max_ac_current,
        max_ac_current_a=max_ac_current,
        efficiency_pct=family["efficiency"],
        source="library"
    )
