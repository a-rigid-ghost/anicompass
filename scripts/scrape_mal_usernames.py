from bs4 import BeautifulSoup
import requests 

url = "https://myanimelist.net/users.php"
params = {
    "cat": "user",
    "q": "",
    "loc": "",
    "agelow": "10",
    "agehigh": "10",
    "g": "1"
}
r = requests.get(url, params=params)
soup = BeautifulSoup(r.content, "html.parser")

user_table = soup.find_all("table")[1]
username_list = []
user_list = user_table.find_all("div", {"class": "picSurround"})
for user in user_list:
  profile_ref = user.find("a")["href"]
  username_list.append(profile_ref.split("/")[-1])
print(username_list)