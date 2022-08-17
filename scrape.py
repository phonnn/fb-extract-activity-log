import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class Action:
    LIKES = 'LIKEDPOSTS'
    COMMENTS = 'COMMENTSCLUSTER'
    SHARES = 'MANAGEYOURPOSTS'
    GROUP_SHARES = 'GROUPPOSTS'


class Extractor:
    BASE_URL = "https://www.facebook.com"
    MOBILE_URL = "https://m.facebook.com"

    def __init__(self, profile=None):
        self.uid = ''
        self.ulink = ''
        self.targetUid = ''

        self.profileParse(profile)
        self.options = webdriver.ChromeOptions()
        # self.options.add_argument("start-maximized")
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--start-maximized")
        self.options.add_argument('--disable-gpu')

        if profile is not None:
            self.options.add_argument(f"--user-data-dir={self.profile_path}")
            self.options.add_argument(f"--profile-directory={self.profile_name}")
        else:
            raise Exception("Facebook login required!")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        # self.driver.minimize_window()
        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

    def getUserLink(self):
        self.driver.get(self.MOBILE_URL)
        page = self.driver.page_source
        soup = BeautifulSoup(page, 'lxml')
        self.ulink = soup.find("div", {"class": "_5xu4"}).find("a", {"class": "_4kk6"}).get('href')

    def getUid(self, link):
        data = {
            'fburl': link,
            'check': 'Lookup'
        }
        r = requests.post(url='https://lookup-id.com/#', data=data)
        soup = BeautifulSoup(r.text, 'lxml')
        uid = soup.find('span', {'id': 'code'})
        return uid.text

    def rawActions(self, action, fromDate=None, toDate=None):
        if not self.uid:
            self.getUserLink()
            self.uid = self.getUid(self.BASE_URL + self.ulink)

        year = 2021
        if fromDate == 12:
            fromDate = 13
        if not fromDate:
            fromDate = datetime.now().month
        if not toDate:
            toDate = datetime.now().month + 1
        if fromDate == toDate:
            toDate = fromDate + 1

        if fromDate > toDate or fromDate > datetime.now().month + 1 or toDate < 1 or fromDate < 1:
            raise Exception('Invalid period')

        actions = []

        for timeline in range(fromDate, toDate):
            url = f"{self.BASE_URL}/{str(self.uid)}/allactivity?category_key={action}&month={timeline}&year={year}"

            self.driver.get(url)
            self.scroll_end(sleep=1.5)

            # parse all page source
            page = self.driver.page_source
            soup = BeautifulSoup(page, 'lxml')
            dayContainers = soup.select('div.ue3kfks5.hybvsw6c')[1:]

            for container in dayContainers:
                date = container.select_one('span.lrazzd5p span.ojkyduve').text
                _actions = container.select('.oijh8qal .nnctdnn4')
                for _action in _actions:
                    post = _action.parent.get('href')
                    time = _action.find('span', {'class': 'm9osqain'}).text

                    actions.append({
                        'date': date,
                        'time': time,
                        'post': post
                    })

                    if action == Action.SHARES or action == Action.GROUP_SHARES:
                        desc = _action.select_one('.hcukyx3x.c1et5uql').text
                        actions[-1]['desc'] = desc

        return actions

    def getShares(self, action, targetUrl, fromDate=None, toDate=None):
        if action != Action.SHARES and action != Action.GROUP_SHARES:
            raise Exception("Invalid Action")

        if not self.targetUid:
            self.targetUid = self.getUid(targetUrl)

        posts = self.rawActions(action, fromDate, toDate)

        if action == Action.SHARES:
            shares = list(filter(lambda _post: 'shared a post' in _post['desc'], posts))
        else:
            shares = list(filter(lambda _post: not _post['desc'], posts))
        for _share in shares:
            if _share['post'] is not None:
                self.driver.get(_share['post'])
                time.sleep(0.5)
                for i in range(3):
                    try:
                        ownerUrl = self.driver.find_element('xpath', '//*[contains(concat( " ", @class, " " ), concat( " ", "oo9gr5id", " " ))]//*[contains(concat( " ", @class, " " ), concat( " ", "lrazzd5p", " " ))]')
                        ownerUrl = ownerUrl.get_attribute('href')
                        _share['owner'] = ownerUrl
                        break
                    except:
                        time.sleep(0.3)

                if not _share.get('owner'):
                    _share['owner'] = 'undefinded'
            else:
                _share['owner'] = 'undefinded'

        targetFiltered = list(
            filter(lambda _comment: (targetUrl in _comment['owner']) or (self.targetUid in _comment['owner']),
                   shares))

        return targetFiltered

    def getInteractions(self, action, targetUrl, fromDate=None, toDate=None):
        if action != Action.LIKES and action != Action.COMMENTS:
            raise Exception("Invalid Action")

        if not self.targetUid:
            self.targetUid = self.getUid(targetUrl)

        interactions = self.rawActions(action, fromDate, toDate)
        for _interaction in interactions:
            if _interaction['post'] is not None:
                self.driver.get(_interaction['post'])
                time.sleep(0.5)
                for i in range(3):
                    try:
                        ownerUrl = self.driver.find_element('css selector', 'a.gpro0wi8.lrazzd5p')
                        ownerUrl = ownerUrl.get_attribute('href')
                        _interaction['owner'] = ownerUrl
                        break
                    except:
                        time.sleep(0.3)

                if not _interaction.get('owner'):
                    _interaction['owner'] = 'undefinded'
            else:
                _interaction['owner'] = 'undefinded'

        targetFiltered = list(
            filter(lambda _reaction: (targetUrl in _reaction['owner']) or (self.targetUid in _reaction['owner']),
                   interactions))
        targetFilteredNotCmt = list(filter(lambda _reaction: ('comment_id' not in _reaction['post']) and (
                    'reply_comment_id' not in _reaction['owner']), targetFiltered))
        return targetFilteredNotCmt

    def profileParse(self, profile):
        if profile is not None:
            start = profile.rindex('/') + 1
            end = len(profile)
            self.profile_path = profile[: start]
            self.profile_name = profile[start: end]

    def scroll_end(self, sleep=1, scroll_max=None):
        """Scroll down until the end of the current document is reached.

        Args:
            driver (selenium.webdriver.firefox.webdriver.WebDriver): WebDriver used to connect to facebook.
                The current supported driver is only limited to Firefox.
            sleep (int, optional): Sleep delay between each scroll.
                If the sleep delay is too small, the function may exit before the end of the document is reached.
                Defaults to ``3``.
            scroll_max (int, optional): Number of maximum scroll to make. If ``None``, will scroll until the end. Defaults to ``None``.

        .. note::
            The function modify the ``driver`` in place.
        """
        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        if scroll_max is None:
            scroll_max = 99
        while scroll_max > 0:
            scroll_max -= 1
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(sleep)
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def quit(self):
        self.driver.quit()

def exportFile(data, name):
    json_object = json.dumps(data, indent=4)
    with open(f"{name}.json", "w") as outfile:
        outfile.write(json_object)

if __name__ == '__main__':
    PROFILE = 'C:/sers/hungp/AppData/Local/Google/Chrome/User Data/Profile 17'
    api = Extractor(profile=PROFILE)
    start = time.time()

    try:
        reactions = api.getInteractions(Action.LIKES, 'https://www.facebook.com/zingmp3/', 3, 9)
        print(reactions)

        # comments = api.getInteractions(Action.COMMENTS, 'https://www.facebook.com/guitarDUE/', 3, 9)
        # print(comments)
        #
        # uShares = api.getShares(Action.SHARES, 'https://www.facebook.com/100059377971631', 9, 10)
        # print(uShares)
        #
        # gShares = api.getShares(Action.GROUP_SHARES, 'https://www.facebook.com/groups/1046538799390337', 3, 12)
        # print(gShares)
    except Exception:
        api.quit()
        raise Exception
    print(time.time()-start)
    api.quit()

