from bs4 import BeautifulSoup
import requests

from enum import Enum
import traceback
import json
from pathlib import Path
import time

MAL_USERS_URL = "https://myanimelist.net/users.php"
PAGE_SIZE = 24
AGE_LIMIT_LOW = 15
AGE_LIMIT_HIGH = 30
AGE_STEP = 1
COUNTRY_LIST = [
    "Japan",
    "Philippines",
    "China",
    "Malaysia",
    "South Korea",
    "Taiwan",
    "India",
    "United States",
    "Canada",
    "France",
    "United Kingdom"
    "Brazil",
    "Mexico"
]
 
class Gender(Enum):
    MALE = 1
    FEMALE = 2
    NON_BINARY = 3
  
def _scrape_mal_users_page(params, username_set):
    max_page_num = 1
    try:
        r = requests.get(MAL_USERS_URL, params=params)
        soup = BeautifulSoup(r.content, "html.parser")
        user_table = soup.find_all("table")[1]
        user_list = user_table.find_all("div", {"class": "picSurround"})
        for user in user_list:
            profile_ref = user.find("a")["href"]
            username_set.add(profile_ref.split("/")[-1])
        page_num_list = (soup.find_all("div", {"class": "spaceit"})[1]).find_all("a")
        max_page_num = int(page_num_list[-1].string) if len(page_num_list) else 1
    except Exception as e:
        print(f"Error while fetching page with parameters: {params}")
        print(traceback.format_exc())
    return max_page_num


def get_all_usernames_for_filter(agelow, agehigh, location="", gender=""):
    result_set = set()
    cur_page = max_page = 1
    while (cur_page <= max_page):
        print(f"Current Page: {cur_page} and Max Page: {max_page}")
        start_index = (cur_page - 1) * PAGE_SIZE
        page_params = {
            "cat": "user",
            "q": "",
            "loc": location,
            "agelow": agelow,
            "agehigh": agehigh,
            "g": gender,
            "show": start_index
        }
        max_page = max(max_page, _scrape_mal_users_page(page_params, result_set))
        cur_page += 1
    return list(result_set)


def main():
    for country in COUNTRY_LIST[2:3]:
        country_usernames_list = []
        for age in range (AGE_LIMIT_LOW, AGE_LIMIT_HIGH + 1, AGE_STEP):
            lower_limit = age
            upper_limit = age + AGE_STEP - 1
            print(f"Starting retrieval for usernames for country: {country} between age: {lower_limit} and {upper_limit}")
            country_usernames_list.extend(get_all_usernames_for_filter(lower_limit, upper_limit, country))
        unique_country_usernames_list = list(set(country_usernames_list))
        print(f"Fetched {len(unique_country_usernames_list)} users from {country}")

        base_path = Path(__file__).parent
        file_path = (base_path / "../data/mal_usernames.json").resolve()
        prev_list = []
        with open(file_path, 'r') as f:
            prev_list = json.load(f)
        with open(file_path, 'w') as f:
            new_list = list(set(prev_list + unique_country_usernames_list))
            json.dump(new_list, f)
            print(f"Total usernames retrieved till now: {len(new_list)}")


main()