"""
OILTRACE — CLI Demo Scenario Loader
Populates the database with realistic synthetic demonstration data:
- Sentinel-1 SAR scene
- 14.2 km² oil spill event
- Backward Lagrangian drift hindcast
- 5 AIS vessels with differing attribution evidence profiles
"""
import os
import sys

# Ensure backend is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.api.demo import load_demo_investigation

def main():
    print("=" * 70)
    print("OILTRACE — Loading Demonstration Scenario (SIH 2026 Problem SIH26143)")
    print("=" * 70)
    print("Notice: Synthetic demonstration data — not real-world evidence.")
    
    db = SessionLocal()
    try:
        result = load_demo_investigation(db)
        print("\n[SUCCESS] Demo loaded successfully!")
        print(f"  Spill Event ID: #{result['spill_id']}")
        print(f"  Vessels Loaded: {result['vessels_loaded']}")
        print(f"  Candidates Scored: {result['candidates_ranked']}")
        print("\nYou can now open the Web GIS Dashboard at http://localhost:5173")
    except Exception as e:
        print(f"\n[ERROR] Failed to load demo data: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
