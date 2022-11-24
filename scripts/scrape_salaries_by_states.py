import datetime
from pathlib import Path
import pickle
import sys

sys.path.append("../src")
import pandas as pd
from scraper import SalaryByState

def main():
    scraper = SalaryByState()
    salaries = scraper.get_salary_by_states()
    
    save_dir = Path("../data/salary/by_states")
    if not save_dir.exists():
        save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / "{}.pickle".format(datetime.datetime.today().strftime("%Y%m%d-%H%M%S"))
    with save_path.open(mode="wb") as fp:
        pickle.dump(salaries, fp)
        
if __name__ == "__main__":
    main()