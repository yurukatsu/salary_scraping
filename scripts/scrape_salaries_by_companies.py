import argparse
import datetime
import pickle
import sys
from pathlib import Path

sys.path.append("../src")

import pandas as pd
from scraper import SalaryByCompany


def main():
    parser = argparse.ArgumentParser(
        description="Scrape salaries of compnies"
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    
    scraper_ = SalaryByCompany()
    salaries = scraper_.get_salaries_of_companies_by_industries(
        verbose=True, 
        debug=args.debug
    )
    
    save_dir = Path("../data/salary/by_companies")
    if not save_dir.exists():
        save_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = save_dir / "{}.pickle".format(datetime.datetime.today().strftime("%Y%m%d-%H%M%S"))
    with save_path.open(mode="wb") as fp:
        pickle.dump(salaries, fp)

if __name__ == "__main__":
    main()