# import Libraries and Dependencies
import os
import json
import time
import numpy as np
import pandas as pd

# import the repo wrapper
from FreecadParametricFEA import parametric as pfea

# FreeCAD configuration
FREECAD_PATH = "C:/FreeCAD-0.20/bin"
FREECAD_DOC = "./plate_n.FCStd"          
OUT_CSV = "results_plate_hole_c.csv"

# parametric arrays 
hole_diameter = np.linspace(10, 50, 5)      # mm
vertical_length = np.linspace(60, 200, 5)   # mm
thickness = np.linspace(5, 15, 5)           # mm

MAX_RUNS = None                             # limit total runs if you want


def build_and_run():
    # initialize the wrapper
    fea = pfea(freecad_path=FREECAD_PATH)
    fea.set_model(freecad_document=FREECAD_DOC)

    # config variables using same names as FreeCAD sketch
    variables = [
        {
            "object_name":"Sketch", 
            "constraint_name":"HoleDiameter", 
            "constraint_values":hole_diameter
        },
        
        {
            "object_name":"Sketch", 
            "constraint_name":"VerticalLength", 
            "constraint_values":vertical_length
        },
        
        {
            "object_name":"Pad", 
            "constraint_name":"Length", 
            "constraint_values":thickness
        },
    ]
    fea.set_variables(variables)
    fea.setup_fea(fea_results_name="CCX_Results", solver_name="SolverCcxTools")

    print("Running parametric FEA. This may take time depending on number of cases...")
    results = fea.run_parametric()  
    return results

def normalize_results(raw_results):
    """
    Convert the raw 'results' returned by fea.run_parametric() into a tidy dataframe.
    Returns:
      - list of dicts
      - pandas DataFrame
      - dict mapping jobname -> metrics
    """
    if raw_results is None:
        raise RuntimeError("No results returned from run_parametric(). Aborting.")

    if isinstance(raw_results, pd.DataFrame):
        df = raw_results.copy()
    elif isinstance(raw_results, dict):
        # convert mapping to dataframe
        df = pd.DataFrame.from_dict(raw_results, orient='index').reset_index().rename(columns={'index':'jobname'})
    elif isinstance(raw_results, list):
        # list of dicts
        df = pd.DataFrame(raw_results)
    else:
        # fallback: coerce to dataframe
        df = pd.DataFrame(raw_results)

    # rename probable keys to consistent names
    colmap = {}
    for c in df.columns:
        low = c.lower()
        if 'hole' in low and ('diam' in low or 'diameter' in low):
            colmap[c] = 'HoleDiameter'
        if 'vertical' in low and ('len' in low or 'length' in low):
            colmap[c] = 'PlateWidth'
        if 'thick' in low or ('pad' in low and 'length' in low):
            colmap[c] = 'Thickness'
        if 'von' in low or ('vm' in low) or ('max' in low and 'stress' in low):
            colmap[c] = 'Max_vM_Stress_MPa'
        if 'disp' in low or 'deflect' in low:
            colmap[c] = 'MaxDisp_mm'
    df = df.rename(columns=colmap)

    # fill missing canonical columns with NaN so CSV schema is stable
    for c in ['HoleDiameter','PlateWidth','Thickness','Max_vM_Stress_MPa','MaxDisp_mm']:
        if c not in df.columns:
            df[c] = np.nan

    # add metadata
    df['material'] = 'Al6061'   
    df['timestamp'] = pd.Timestamp.now()
    return df

def main():
    raw = build_and_run()
    df = normalize_results(raw)
    # limit to numeric columns and drop duplicates
    df = df.drop_duplicates().reset_index(drop=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"Saved results to {OUT_CSV}. Rows: {len(df)}")

if __name__ == "__main__":
    main()
