import datetime
import itertools
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Literal
from urllib import request

import chromedriver_binary
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from tqdm import tqdm

# from utils import us_states
from utils.processing import text2num


class Salary:
    def __init__(self) -> None:
        self.protocol = "https"
        self.domain = "www.payscale.com"
        self.start_url = self.protocol + "://" + self.domain

class SalaryByCompany(Salary):
    def __init__(self):
        super().__init__()
        self.industries = None
        
    def get_industry_names_and_urls(self):
        start_url = self.start_url + "/research/US/Employer" # URL

        response = request.urlopen(start_url) # request
        soup = BeautifulSoup(response, features='lxml') # response

        industry_names = soup.find_all('div', class_="related-content-card__title") # industry names
        industry_urls = soup.find_all('a', class_="related-content-card") # industry urls

        industries = {}
        for _url, _name in zip(industry_urls, industry_names):
            url = self.start_url + _url.get("href")
            name = _name.get_text()
            industries[name] = {"url": url}

        response.close()
        
        return industries
    
    def _set_industry_names_and_urls(self):
        self.industries = self.get_industry_names_and_urls()
        
    def _get_initial_letter_urls(self, industry:str):
        
        # industryが設定されていない場合
        if self.industries == None:
            self._set_industry_names_and_urls()
        
        # url設定，request, response
        start_url = self.industries[industry]['url']
        response = request.urlopen(start_url)
        soup = BeautifulSoup(response, features='lxml')
        
        alphabet_urls = [
            self.start_url + _.get("href") for _ in soup.find_all('a', class_='alpha-nav__link')
        ]
        
        response.close()
        
        return alphabet_urls
    
    def _get_company_urls_in_particular_industry(
        self,
        industry:str,
        default:Literal["Salary", "Hourly_Rate"]="Salary",
        verbose:bool=False
    ):
        
        initial_letter_urls = self._get_initial_letter_urls(industry)
        
        companies = []
        
        pbar = tqdm(initial_letter_urls) if verbose else initial_letter_urls.copy()
        for url in pbar:
            if verbose: pbar.set_description(url[-1])
            
            response = request.urlopen(url)
            soup = BeautifulSoup(response, features='lxml')
        
            company_tags = soup.find_all('a', class_='subcats__links__item')
            
            for _ in company_tags:
                _name = _.get_text()
                _url = self.start_url + _.get("href")
                _changed = "Salary" if default == "Hourly_Rate" else "Hourly_Rate"
                _url = _url.replace(_changed, default)
                
                companies.append({"name":_name, "url":_url})
                
            # pagination要対応
            # -------------------
            # ページリンクがるかジャッジ
            # 最大ページ数を取得
            # /Page-2とかになるのでここにリクエスト，
            # あとはmax iterまで繰り返し
            #--------------------
                
        return companies
    
    def get_salaries_of_companies_in_particular_industry(
        self, 
        industry:str, 
        verbose:bool=False,
        debug:bool=False
    ):
        if verbose: logging.info("Loading url of each company")
        companies = self._get_company_urls_in_particular_industry(
            industry,
            default='Salary',
            verbose=verbose
        )
        
        salary_info = []
        
        # for debugging
        if debug:
            count = 0
        
        pbar = tqdm(companies) if verbose else companies.copy()
        for company in pbar:
            # for debugging
            if debug:
                count += 1
                if count > 3:
                    break
            
            name = company['name']
            url = company['url']
            
            if verbose: pbar.set_description(name)
            
            with request.urlopen(url) as response:
                soup = BeautifulSoup(response, features='lxml')
                
                salary = soup.find("span", class_="employer-overview__value").get_text()
                if salary == "N/A":
                    salary = None
                else:
                    salary = salary.replace("$", "")
                    salary = text2num(salary)
                    
                bonus = soup.find("div", class_="employer-overview__value")
                if bonus:
                    bonus = bonus.get_text()
                    if bonus == "N/A":
                        bonus = None
                    else:
                        bonus = bonus.replace("$", "")
                        bonus = text2num(bonus)
                    
                rating = soup.find("span", class_="employer-overview__rating-score").get_text()
                if rating == "N/A":
                    rating = None
                else:
                    rating = float(rating)
            
            url = url.replace("Salary", "Hourly_Rate")
            with request.urlopen(url) as response:
                soup = BeautifulSoup(response, features='lxml')
                
                hourly_rate = soup.find("span", class_="employer-overview__value").get_text()
                if hourly_rate == "N/A":
                    hourly_rate = None
                else:
                    hourly_rate = hourly_rate.replace("$", "")
                    hourly_rate = text2num(hourly_rate)
                    
            now_ = datetime.datetime.now()
            
            salary_info.append(
                {
                    'company': name,
                    'url': url,
                    'industry': industry,
                    'salary': salary,
                    'hourly_rate': hourly_rate,
                    "bonus": bonus,
                    "rating": rating,
                    "time_added": now_
                }
            )
            
        return salary_info
    
    def _add_salaries_of_companies_in_particular_industry(
        self,
        industry:str,
        saralies:List,
        verbose:bool=False,
        debug:bool=False
    ):
        saralies.append(
            self.get_salaries_of_companies_in_particular_industry(
                industry,
                verbose=verbose,
                debug=debug
            )
        )
    
    def get_salaries_of_companies_by_industries(
        self,
        verbose:bool=False,
        debug:bool=False
    ):
        if self.industries == None:
            self._set_industry_names_and_urls()
        
        salaries = []
        pbar = tqdm(self.industries)
        
        with ThreadPoolExecutor(max_workers=16) as executor:
            for industry in pbar:
                pbar.set_description(industry)
                executor.submit(
                    self._add_salaries_of_companies_in_particular_industry,
                    industry,
                    salaries,
                    verbose=verbose,
                    debug=debug
                )
        return itertools.chain(*salaries)
    
class SalaryByState(Salary):
    def __init__(self) -> None:
        super().__init__()
        self.states = None
        
    def get_state_names_and_urls(self):
        start_url = self.start_url + "/research/US/Country=United_States/Salary" # url
        
        with request.urlopen(start_url) as response:
            soup = BeautifulSoup(response, features="lxml")
            _states = soup.select("div[id='state-section']>div>div>a")
        
        states = {}
        for _state in _states:
            name = _state.get_text()
            url = _state.get('href')
            states[name] = {"url": url}
            
        return states
    
    def _set_state_names_and_urls(self):
        self.states = self.get_state_names_and_urls()
        
    def get_salary_in_particular_state(self, state:str):
        if self.states == None:
            self._set_state_names_and_urls()
        
        url = self.start_url + self.states[state]['url']
        
        # data info
        salary = {}
        salary["state"] = state
        salary["url"] = url
        salary["date_added"] = datetime.datetime.now()
        
        def _get_value(value_, type_):
            if type_ == "/ year":
                if value_ == "N/A":
                    value_ = None
                else:
                    value_ = text2num(value_.replace("$", ""))
                type__ = "salary"
                
            if type_ == "/ hour":
                if value_ == "N/A":
                    value_ = None
                else:
                    value_ = float(value_.replace("$", ""))
                type__ = "hourly_rate"
            
            return (value_, type__)
        
        # Chrome
        options = Options()
        options.add_argument('---headless')
        with webdriver.Chrome(options=options) as driver:
            driver.get(url)
            
            # 一周目
            value_ = driver.find_element(
                By.CSS_SELECTOR,
                "span[class='location-overview__value']"
            ).text
            type_ = driver.find_element(
                By.CSS_SELECTOR,
                "button[class='pxl-btn dropdown__btn pxl-dropdown__toggle']"
            )
            v, k = _get_value(value_, type_.text)
            salary[k] = v
            
            # 二周目
            type_.click()
            new_type_ = driver.find_element(
                By.CSS_SELECTOR,
                "button[class='location-overview__dropdown-option']"
            )
            new_type_.click()
            type_ = driver.find_element(
                By.CSS_SELECTOR,
                "button[class='pxl-btn dropdown__btn pxl-dropdown__toggle']"
            )
            value_ = driver.find_element(
                By.CSS_SELECTOR,
                "span[class='location-overview__value']"
            ).text
            v, k = _get_value(value_, type_.text)
            salary[k] = v
            
            driver.quit()
            
        return salary
    
    def get_salary_by_states(self):
        if self.states == None:
            self._set_state_names_and_urls()
        
        def _add_salary(salaries:List, state:str):
            salary = self.get_salary_in_particular_state(state)
            salaries.append(salary)
            
        salaries = []
        pbar = tqdm(self.states)
        
        with ThreadPoolExecutor(max_workers=16) as executor:
            for state in pbar:
                pbar.set_description(state)
                executor.submit(
                    _add_salary,
                    salaries,
                    state
                )
        
        return salaries
        
if __name__ == "__main__":
    scraper = SalaryByState()
    salaries = scraper.get_salary_by_states()
    print(salaries)