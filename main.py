import os
import utils
import ui

# Set this to True for the GitHub version to restrict access to demo data
DEMO_MODE = False
if __name__ == "__main__":
    if DEMO_MODE:
        print("Starting in DEMO MODE...")

        # Override the default data directory (data/timeseries) to use data/demo
        # This ensures the app only sees files in the demo folder
        demo_path = os.path.join("data", "demo")

        # Ensure the directory exists (optional safety check)
        if not os.path.exists(demo_path):
            print(f"Warning: Demo directory '{demo_path}' does not exist.")

        utils.set_data_dir(demo_path)
        print(f"Data source restricted to: {utils.get_data_dir()}")
    else:
        print("Starting in FULL MODE...")
        print(f"Data source: {utils.get_data_dir()}")

    # Launch the UI
    ui.main()