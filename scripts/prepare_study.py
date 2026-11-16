"""Freeze accepted analyses before enrolling a cohort. Never contacts volunteers."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.app.services.study_protocol import prepare, MANIFEST

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents",nargs="+")
    parser.add_argument("--output",type=Path,default=MANIFEST)
    args=parser.parse_args()
    result=prepare(args.documents,args.output)
    print(f"Frozen {len(result['cases'])} cases for {result['pilot_id']}; no participants enrolled.")
