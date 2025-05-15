matching = {
    # Tanks (B201–B204): Level, Temperatur, Druck, Höhe und Fläche
    "B201_Level":               "tank_B201.level",
    "B201_Temperature":         "tank_B201.medium.T",
    "B201_Pressure":            "tank_B201.ports[1].p",
    "B201_Height":              "tank_B201.height",
    "B201_Area":                "tank_B201.crossArea",
    "LIR211_Measurement_Level": "none",  

    # Rohr B201_V201: Durchfluss, Druck, Temperatur, Länge, Durchmesser, Rauheit, Höhenunterschied
    "Pipe_B201_V201_Flow":      "pipe_B201_V201.port_a.m_flow",
    "Pipe_B201_V201_Pressure":  "pipe_B201_V201.port_b.p",
    "Pipe_B201_V201_Temperature": "pipe_B201_V201.flowModel.states[1].T",
    "Pipe_B201_V201_Length":    "pipe_B201_V201.length",
    "Pipe_B201_V201_Diameter":  "pipe_B201_V201.diameter",
    "Pipe_B201_V201_Roughness": "pipe_B201_V201.roughness",
    "Pipe_B201_V201_HDiff":     "pipe_B201_V201.height_ab",
    
    "PIR251_Measurement_Pressure": "pipe_B201_V201.port_b.p",
    
    # Ventil V201
    "V201_State":       "V201.opening",
    "V201_PDropNom":    "V201.dp_nominal",
    "V201_MFNominal":   "V201.m_flow_nominal",
    "V201_Flow":        "V201.m_flow",
    "V201_Pressure":    "V201.port_b.p",
    "V201_Temperature": "V201.port_b_T",
    "YIC201_Measurement_State": "V201.opening",
    
    # Rohr V201_Tee1
    "Pipe_V201_Tee1_Flow":      "pipe_V201_Tee1.port_a.m_flow",
    "Pipe_V201_Tee1_Pressure":  "pipe_V201_Tee1.port_b.p",
    "Pipe_V201_Tee1_Temperature": "pipe_V201_Tee1.flowModel.states[1].T",
    "Pipe_V201_Tee1_Length":    "pipe_V201_Tee1.length",
    "Pipe_V201_Tee1_Diameter":  "pipe_V201_Tee1.diameter",
    "Pipe_V201_Tee1_Roughness": "pipe_V201_Tee1.roughness",
    "Pipe_V201_Tee1_HDiff":     "pipe_V201_Tee1.height_ab",
    
    # Tank B202
    "B202_Level":               "tank_B202.level",
    "B202_Temperature":         "tank_B202.medium.T",
    "B202_Pressure":            "tank_B202.ports[1].p",
    "B202_Height":              "tank_B202.height",
    "B202_Area":                "tank_B202.crossArea",
    "LIR212_Measurement_Level": "tank_B202.level",
    
    # Rohr B202_V202
    "Pipe_B202_V202_Flow":      "pipe_B202_V202.port_a.m_flow",
    "Pipe_B202_V202_Pressure":  "pipe_B202_V202.port_b.p",
    "Pipe_B202_V202_Temperature": "pipe_B202_V202.flowModel.states[1].T",
    "Pipe_B202_V202_Length":    "pipe_B202_V202.length",
    "Pipe_B202_V202_Diameter":  "pipe_B202_V202.diameter",
    "Pipe_B202_V202_Roughness": "pipe_B202_V202.roughness",
    "Pipe_B202_V202_HDiff":     "pipe_B202_V202.height_ab",
    "PIR252_Measurement_Pressure": "pipe_B202_V202.port_b.p",
    
    # Ventil V202
    "V202_State":       "V202.opening",
    "V202_PDropNom":    "V202.dp_nominal",
    "V202_MFNominal":   "V202.m_flow_nominal",
    "V202_Flow":        "V202.m_flow",
    "V202_Pressure":    "V202.port_b.p",
    "V202_Temperature": "V202.port_b_T",
    "YIC202_Measurement_State": "V202.opening",
    
    # Rohr V202_Tee2
    "Pipe_V202_Tee2_Flow":      "pipe_V202_Tee2.port_a.m_flow",
    "Pipe_V202_Tee2_Pressure":  "pipe_V202_Tee2.port_b.p",
    "Pipe_V202_Tee2_Temperature": "pipe_V202_Tee2.flowModel.states[1].T",
    "Pipe_V202_Tee2_Length":    "pipe_V202_Tee2.length",
    "Pipe_V202_Tee2_Diameter":  "pipe_V202_Tee2.diameter",
    "Pipe_V202_Tee2_Roughness": "pipe_V202_Tee2.roughness",
    "Pipe_V202_Tee2_HDiff":     "pipe_V202_Tee2.height_ab",
    
    # Tank B203
    "B203_Level":               "tank_B203.level",
    "B203_Temperature":         "tank_B203.medium.T",
    "B203_Pressure":            "tank_B203.ports[1].p",
    "B203_Height":              "tank_B203.height",
    "B203_Area":                "tank_B203.crossArea",
    "LIR213_Measurement_Level": "tank_B203.level",
    
    # Rohr B203_V203
    "Pipe_B203_V203_Flow":      "pipe_B203_V203.port_a.m_flow",
    "Pipe_B203_V203_Pressure":  "pipe_B203_V203.port_b.p",
    "Pipe_B203_V203_Temperature": "pipe_B203_V203.flowModel.states[1].T",
    "Pipe_B203_V203_Length":    "pipe_B203_V203.length",
    "Pipe_B203_V203_Diameter":  "pipe_B203_V203.diameter",
    "Pipe_B203_V203_Roughness": "pipe_B203_V203.roughness",
    "Pipe_B203_V203_HDiff":     "pipe_B203_V203.height_ab",
    "PIR253_Measurement_Pressure": "pipe_B203_V203.port_b.p",
    
    # Ventil V203
    "V203_State":       "V203.opening",
    "V203_PDropNom":    "V203.dp_nominal",
    "V203_MFNominal":   "V203.m_flow_nominal",
    "V203_Flow":        "V203.m_flow",
    "V203_Pressure":    "V203.port_b.p",
    "V203_Temperature": "V203.port_b_T",
    "YIC203_Measurement_State": "V203.opening",
    
    # Rohr V203_Tee2
    "Pipe_V203_Tee2_Flow":      "pipe_V203_Tee2.port_a.m_flow",
    "Pipe_V203_Tee2_Pressure":  "pipe_V203_Tee2.port_b.p",
    "Pipe_V203_Tee2_Temperature": "pipe_V203_Tee2.flowModel.states[1].T",
    "Pipe_V203_Tee2_Length":    "pipe_V203_Tee2.length",
    "Pipe_V203_Tee2_Diameter":  "pipe_V203_Tee2.diameter",
    "Pipe_V203_Tee2_Roughness": "pipe_V203_Tee2.roughness",
    "Pipe_V203_Tee2_HDiff":     "pipe_V203_Tee2.height_ab",
    
    # Tee1
    "Tee1_Flow":        "Tee1.mb_flow",
    "Tee1_Temperature": "Tee1.medium.T",
    "Tee1_Pressure":    "Tee1.medium.p",
    
    # Rohr Tee1–Tee2 (Tee1_Tee2 bzw. Tee2_Tee1 identisch)
    "Pipe_Tee1_Tee2_Flow":      "pipe_Tee2_Tee1.port_a.m_flow",
    "Pipe_Tee1_Tee2_Pressure":  "pipe_Tee2_Tee1.port_b.p",
    "Pipe_Tee1_Tee2_Temperature": "pipe_Tee2_Tee1.flowModel.states[1].T",
    "Pipe_Tee1_Tee2_Length":    "pipe_Tee2_Tee1.length",
    "Pipe_Tee1_Tee2_Diameter":  "pipe_Tee2_Tee1.diameter",
    "Pipe_Tee1_Tee2_Roughness": "pipe_Tee2_Tee1.roughness",
    "Pipe_Tee1_Tee2_HDiff":     "pipe_Tee2_Tee1.height_ab",
    
    # Tee2
    "Tee2_Flow":        "Tee2.mb_flow",
    "Tee2_Temperature": "Tee2.medium.T",
    "Tee2_Pressure":    "Tee2.medium.p",
    
    # Rohr Tee1–P201
    "Pipe_Tee1_P201_Flow":      "pipe_Tee1_P201.port_a.m_flow",
    "Pipe_Tee1_P201_Pressure":  "pipe_Tee1_P201.port_b.p",
    "Pipe_Tee1_P201_Temperature": "pipe_Tee1_P201.flowModel.states[1].T",
    "Pipe_Tee1_P201_Length":    "pipe_Tee1_P201.length",
    "Pipe_Tee1_P201_Diameter":  "pipe_Tee1_P201.diameter",
    "Pipe_Tee1_P201_Roughness": "pipe_Tee1_P201.roughness",
    "Pipe_Tee1_P201_HDiff":     "pipe_Tee1_P201.height_ab",
    
    # Pump P201 – (Hinweis: Für Pumpen werden Drehzahl, Leistung, Durchfluss und Druck gemessen)
    "P201_State":             "P201_Characteristic.y",  
    "P201_Rotational_Speed":  "P201.N",
    "P201_Power":             "P201.W_total",
    "P201_Flow":              "P201.V_flow",
    "P201_Pressure":          "P201.medium.p",
    "P201_Temperature":       "P201.medium.T",
    "P201_PumpVolume":        "P201.fluidVolume",
    "YIC201P_Measurement_State": "P201_Characteristic.y",
    
    # Rohr P201 FI271 (wird als FI201 abgebildet)
    "Pipe_P201_FI271_Flow":      "pipe_P201_FI201.port_a.m_flow",
    "Pipe_P201_FI271_Pressure":  "pipe_P201_FI201.port_b.p",
    "Pipe_P201_FI271_Temperature": "pipe_P201_FI201.flowModel.states[1].T",
    "Pipe_P201_FI271_Length":    "pipe_P201_FI201.length",
    "Pipe_P201_FI271_Diameter":  "pipe_P201_FI201.diameter",
    "Pipe_P201_FI271_Roughness": "pipe_P201_FI201.roughness",
    "Pipe_P201_FI271_HDiff":     "pipe_P201_FI201.height_ab",
    
    # Rohr FI271 – B204
    "Pipe_FI271_B204_Flow":      "pipe_FI201_B204.port_a.m_flow",
    "Pipe_FI271_B204_Pressure":  "pipe_FI201_B204.port_b.p",
    "Pipe_FI271_B204_Temperature": "pipe_FI201_B204.flowModel.states[1].T",
    "Pipe_FI271_B204_Length":    "pipe_FI201_B204.length",
    "Pipe_FI271_B204_Diameter":  "pipe_FI201_B204.diameter",
    "Pipe_FI271_B204_Roughness": "pipe_FI201_B204.roughness",
    "Pipe_FI271_B204_HDiff":     "pipe_FI201_B204.height_ab",
    
    "FIR271_Measurement_Flow":   "FI201.V_flow",
    
    # Tank B204
    "B204_Level":               "tank_B204.level",
    "B204_Temperature":         "tank_B204.medium.T",
    "B204_Pressure":            "tank_B204.ports[1].p",
    "B204_Height":              "tank_B204.height",
    "B204_Area":                "tank_B204.crossArea",
    "LIR214_Measurement_Level": "tank_B204.level",
    "TIR261_Measurement_Temperature": "tank_B204.medium.T",
    
    # Rohr B204_P202
    "Pipe_B204_P202_Flow":      "pipe_B204_P202.port_a.m_flow",
    "Pipe_B204_P202_Pressure":  "pipe_B204_P202.port_b.p",
    "Pipe_B204_P202_Temperature": "pipe_B204_P202.flowModel.states[1].T",
    "Pipe_B204_P202_Length":    "pipe_B204_P202.length",
    "Pipe_B204_P202_Diameter":  "pipe_B204_P202.diameter",
    "Pipe_B204_P202_Roughness": "pipe_B204_P202.roughness",
    "Pipe_B204_P202_HDiff":     "pipe_B204_P202.height_ab",
    "PIR254_Measurement_Pressure": "pipe_B204_P202.port_b.p",
    
    # Pump P202
    "P202_State":             "P202_Characteristic.y",
    "P202_Rotational_Speed":  "P202.N",
    "P202_Power":             "P202.W_total",
    "P202_Flow":              "P202.V_flow",
    "P202_Pressure":          "P202.medium.p",
    "P202_Temperature":       "P202.medium.T",
    "P202_PumpVolume":        "P202.fluidVolume",
    "YIC202P_Measurement_State": "P202_Characteristic.y",
    
    # Rohr P202_Tee3
    "Pipe_P202_Tee3_Flow":      "pipe_P202_Tee3.port_a.m_flow",
    "Pipe_P202_Tee3_Pressure":  "pipe_P202_Tee3.port_b.p",
    "Pipe_P202_Tee3_Temperature": "pipe_P202_Tee3.flowModel.states[1].T",
    "Pipe_P202_Tee3_Length":    "pipe_P202_Tee3.length",
    "Pipe_P202_Tee3_Diameter":  "pipe_P202_Tee3.diameter",
    "Pipe_P202_Tee3_Roughness": "pipe_P202_Tee3.roughness",
    "Pipe_P202_Tee3_HDiff":     "pipe_P202_Tee3.height_ab",
    
    # Tee3
    "Tee3_Flow":        "Tee3.mb_flow",
    "Tee3_Temperature": "Tee3.medium.T",
    "Tee3_Pressure":    "Tee3.medium.p",
    
    # Rohr Tee3 – V207
    "Pipe_Tee3_V207_Flow":      "pipe_Tee3_V207.port_a.m_flow",
    "Pipe_Tee3_V207_Pressure":  "pipe_Tee3_V207.port_b.p",
    "Pipe_Tee3_V207_Temperature": "pipe_Tee3_V207.flowModel.states[1].T",
    "Pipe_Tee3_V207_Length":    "pipe_Tee3_V207.length",
    "Pipe_Tee3_V207_Diameter":  "pipe_Tee3_V207.diameter",
    "Pipe_Tee3_V207_Roughness": "pipe_Tee3_V207.roughness",
    "Pipe_Tee3_V207_HDiff":     "pipe_Tee3_V207.height_ab",
    
    # Rohr V207_Tee4
    "Pipe_V207_Tee4_Flow":      "pipe_V207_Tee4.port_a.m_flow",
    "Pipe_V207_Tee4_Pressure":  "pipe_V207_Tee4.port_b.p",
    "Pipe_V207_Tee4_Temperature": "pipe_V207_Tee4.flowModel.states[1].T",
    "Pipe_V207_Tee4_Length":    "pipe_V207_Tee4.length",
    "Pipe_V207_Tee4_Diameter":  "pipe_V207_Tee4.diameter",
    "Pipe_V207_Tee4_Roughness": "pipe_V207_Tee4.roughness",
    "Pipe_V207_Tee4_HDiff":     "pipe_V207_Tee4.height_ab",
    
    "FIR272_Measurement_Flow":  "pipe_V207_Tee4.port_a.m_flow",
    
    # Tee4
    "Tee4_Flow":        "Tee4.mb_flow",
    "Tee4_Temperature": "Tee4.medium.T",
    "Tee4_Pressure":    "Tee4.medium.p",
    
    # Rohr Tee4 – V204
    "Pipe_Tee4_V204_Flow":      "pipe_Tee4_V204.port_a.m_flow",
    "Pipe_Tee4_V204_Pressure":  "pipe_Tee4_V204.port_b.p",
    "Pipe_Tee4_V204_Temperature": "pipe_Tee4_V204.flowModel.states[1].T",
    "Pipe_Tee4_V204_Length":    "pipe_Tee4_V204.length",
    "Pipe_Tee4_V204_Diameter":  "pipe_Tee4_V204.diameter",
    "Pipe_Tee4_V204_Roughness": "pipe_Tee4_V204.roughness",
    "Pipe_Tee4_V204_HDiff":     "pipe_Tee4_V204.height_ab",
    
    # Rohr Tee4 – Tee5
    "Pipe_Tee4_Tee5_Flow":      "pipe_Tee4_Tee5.port_a.m_flow",
    "Pipe_Tee4_Tee5_Pressure":  "pipe_Tee4_Tee5.port_b.p",
    "Pipe_Tee4_Tee5_Temperature": "pipe_Tee4_Tee5.flowModel.states[1].T",
    "Pipe_Tee4_Tee5_Length":    "pipe_Tee4_Tee5.length",
    "Pipe_Tee4_Tee5_Diameter":  "pipe_Tee4_Tee5.diameter",
    "Pipe_Tee4_Tee5_Roughness": "pipe_Tee4_Tee5.roughness",
    "Pipe_Tee4_Tee5_HDiff":     "pipe_Tee4_Tee5.height_ab",
    
    # Tee5
    "Tee5_Flow":        "Tee5.mb_flow",
    "Tee5_Temperature": "Tee5.medium.T",
    "Tee5_Pressure":    "Tee5.medium.p",
    
    # Ventil V206
    "V206_State":       "V206.opening",
    "V206_PDropNom":    "V206.dp_nominal",
    "V206_MFNominal":   "V206.m_flow_nominal",
    "V206_Flow":        "V206.m_flow",
    "V206_Pressure":    "V206.port_b.p",
    "V206_Temperature": "V206.port_b_T",

    "YIC206_Measurement_State": "V206.opening",
    
    # Rohr V206 – B203 (hier als pipe_V204_B203 in der Simulation benannt)
    "Pipe_V206_B203_Flow":      "pipe_V204_B203.port_a.m_flow",
    "Pipe_V206_B203_Pressure":  "pipe_V204_B203.port_b.p",
    "Pipe_V206_B203_Temperature": "pipe_V204_B203.flowModel.states[1].T",
    "Pipe_V206_B203_Length":    "pipe_V204_B203.length",
    "Pipe_V206_B203_Diameter":  "pipe_V204_B203.diameter",
    "Pipe_V206_B203_Roughness": "pipe_V204_B203.roughness",
    "Pipe_V206_B203_HDiff":     "pipe_V204_B203.height_ab",
    
    # Rohr Tee5 – V205
    "Pipe_Tee5_V205_Flow":      "pipe_Tee5_V205.port_a.m_flow",
    "Pipe_Tee5_V205_Pressure":  "pipe_Tee5_V205.port_b.p",
    "Pipe_Tee5_V205_Temperature": "pipe_Tee5_V205.flowModel.states[1].T",
    "Pipe_Tee5_V205_Length":    "pipe_Tee5_V205.length",
    "Pipe_Tee5_V205_Diameter":  "pipe_Tee5_V205.diameter",
    "Pipe_Tee5_V205_Roughness": "pipe_Tee5_V205.roughness",
    "Pipe_Tee5_V205_HDiff":     "pipe_Tee5_V205.height_ab",
    
    # Rohr Tee5 – V206
    "Pipe_Tee5_V206_Flow":      "pipe_Tee5_V206.port_a.m_flow",
    "Pipe_Tee5_V206_Pressure":  "pipe_Tee5_V206.port_b.p",
    "Pipe_Tee5_V206_Temperature": "pipe_Tee5_V206.flowModel.states[1].T",
    "Pipe_Tee5_V206_Length":    "pipe_Tee5_V206.length",
    "Pipe_Tee5_V206_Diameter":  "pipe_Tee5_V206.diameter",
    "Pipe_Tee5_V206_Roughness": "pipe_Tee5_V206.roughness",
    "Pipe_Tee5_V206_HDiff":     "pipe_Tee5_V206.height_ab",
    
    # Ventil V204
    "V204_State":       "V204.opening",
    "V204_PDropNom":    "V204.dp_nominal",
    "V204_MFNominal":   "V204.m_flow_nominal",
    "V204_Flow":        "V204.m_flow",
    "V204_Pressure":    "V204.port_b.p",
    "V204_Temperature": "V204.port_b_T",
    "YIC204_Measurement_State": "V204.opening",
    
    # Ventil V205
    "V205_State":       "V205.opening",
    "V205_PDropNom":    "V205.dp_nominal",
    "V205_MFNominal":   "V205.m_flow_nominal",
    "V205_Flow":        "V205.m_flow",
    "V205_Pressure":    "V205.port_b.p",
    "V205_Temperature": "V205.port_b_T",
    "YIC205_Measurement_State": "V205.opening",
    
    # Rohr V205 – B202
    "Pipe_V205_B202_Flow":      "pipe_V205_B202.port_a.m_flow",
    "Pipe_V205_B202_Pressure":  "pipe_V205_B202.port_b.p",
    "Pipe_V205_B202_Temperature": "pipe_V205_B202.flowModel.states[1].T",
    "Pipe_V205_B202_Length":    "pipe_V205_B202.length",
    "Pipe_V205_B202_Diameter":  "pipe_V205_B202.diameter",
    "Pipe_V205_B202_Roughness": "pipe_V205_B202.roughness",
    "Pipe_V205_B202_HDiff":     "pipe_V205_B202.height_ab",
    
    # Rohr V204 – B201
    "Pipe_V204_B201_Flow":      "pipe_V206_B201.port_a.m_flow",
    "Pipe_V204_B201_Pressure":  "pipe_V206_B201.port_b.p",
    "Pipe_V204_B201_Temperature": "pipe_V206_B201.flowModel.states[1].T",
    "Pipe_V204_B201_Roughness": "pipe_V206_B201.roughness",
    "Pipe_V204_B201_HDiff":     "pipe_V206_B201.height_ab",
    
    # Sink (keine direkte Zuordnung)
    "Sink_Temperature": "boundary.T",
    "Sink_Pressure":    "boundary.p",
}    

