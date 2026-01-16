# RexLapisLib/core/visualizer.py
import os
import subprocess
import pickle
import sys

def show_dashboard(results_dict):
    """
    Saves results and launches the Streamlit dashboard automatically.
    """
    print("--- Launching Visual Dashboard ---")
    
    # 1. Save results to a temporary pickle file
    # This allows the independent Streamlit process to read the data
    output_file = "latest_simulation.pkl"
    with open(output_file, 'wb') as f:
        pickle.dump(results_dict, f)
    
    print(f"Data saved to {output_file}")

    # 2. Find the path to the internal viewer.py
    # This logic finds where RexLapisLib is installed on your disk
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to RexLapisLib, then into ui/viewer.py
    # Adjust path logic based on your exact folder structure
    # Assuming: RexLapisLib/core/visualizer.py -> ../ui/viewer.py
    viewer_path = os.path.join(os.path.dirname(current_dir), 'ui', 'viewer.py')

    if not os.path.exists(viewer_path):
        print(f"Error: Dashboard file not found at {viewer_path}")
        return

    # 3. Launch Streamlit as a subprocess
    try:
        # Check if running on Windows or Unix
        cmd = [sys.executable, "-m", "streamlit", "run", viewer_path]
        print(f"Executing: {' '.join(cmd)}")
        print("Waiting for browser to open...")
        
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nDashboard closed.")