import logging
import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path


import sys
sys.path.append("/opt/OpenWPM")

from openwpm.command_sequence import CommandSequence
from openwpm.commands.browser_commands import GetCommand
from openwpm.commands.browser_commands import SaveScreenshotCommand
from openwpm.commands.browser_commands import ScreenshotFullPageCommand
from openwpm.config import BrowserParams, ManagerParams
from openwpm.storage.sql_provider import SQLiteStorageProvider
from openwpm.storage.leveldb import LevelDbProvider
from openwpm.task_manager import TaskManager

import sqlite3
from contextlib import closing
from command_accept_cookies import AcceptCookiesCommand
from command_reject_cookies import RejectCookiesCommand
from command_collect_cookies import CollectCookiesCommand
from idcac_cookie_selectors import get_idcac_css_selectors

class Precrawl:

    def __init__(
        self,
        url_list,
        data_dir,
        log_dir,
        lists_dir,
        num_browsers,
        display_mode,
        cmp,
        name
    ):

        if cmp:
            if num_browsers % 3:
                raise ValueError('Number of browsers must be divisible by 3 when running with CMP interaction')
        else:
            cmp = False
        self.cmp = cmp
        self.sites = None

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        self.timestamp = timestamp # so we can set it later for openwmp

        os.chdir('/opt')
        data_dir = Path(os.path.realpath(data_dir))
        if name:
            self.crawl_dir = data_dir.joinpath(name)
        else:
            self.crawl_dir = data_dir.joinpath(f'crawl-{timestamp}')
        # .fake_home will be used as the home directory for crawl duration
        fakehome = data_dir.joinpath('.fake_home')
        fakehome.unlink(missing_ok=True)
        self.home_dir = fakehome.symlink_to(self.crawl_dir)

        self.log_dir = Path(os.path.realpath(log_dir))
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | Precrawl | %(message)s",
            handlers=[
                logging.FileHandler(self.log_dir.joinpath('precrawl.log')),
                logging.StreamHandler()
            ]
        )

        self.num_browsers = num_browsers
        self.display_mode = display_mode
        
        self.db_path = self.crawl_dir.joinpath('precrawl.sqlite')
        logging.info(f'Database set to {self.db_path}')

        self.profiles_dir = self.crawl_dir.joinpath('profiles')

        self.lists_dir = Path(os.path.realpath(lists_dir))
        if (url_list.suffix == '.json'):
            with open(self.lists_dir.joinpath(url_list)) as f:
                self.urls = json.load(f)
            for k, v in self.urls.items():
                logging.info(f"Imported {len(v)} items in the {k} category")
        elif (url_list.suffix == '.sqlite'):
            with closing(sqlite3.connect(self.lists_dir.joinpath(url_list))) as con:
                self.sites = con.execute(f'SELECT ROWID, url, banner_selector FROM {url_list.stem} WHERE banner_selector IS NOT NULL').fetchall()
        else:
            raise ValueError('Unrecognised format for url list file.')

    def do_crawl(self, category='full', cookie_interaction=False, screenshot='none'):

        if not self.sites:
            if(category == 'full'):
                sites = list()
                for _, urls in self.urls.items():
                    sites.extend(urls)
            elif(category == 'test'):
                # Allerdale - CMP, AMP; CNCBuilding... - CMP
                sites = ['https://www.allerdale.gov.uk/en','https://www.cncbuildingcontrol.gov.uk']
                self.num_browsers = 3 if self.cmp else 1
            else:
                sites = self.urls['fire'] # Fire services is small, containing several dozen urls
        else:
            sites = self.sites

        manager_params = ManagerParams(num_browsers=self.num_browsers)
        manager_params.data_directory = self.crawl_dir
        manager_params.log_path = self.log_dir.joinpath('precrawl-cmp-openwpm.log')
        browser_params = [BrowserParams(display_mode=self.display_mode)
                          for _ in range(self.num_browsers)]

        # Update browser configuration (use this for per-browser settings)
        for i in range(self.num_browsers):
            # Record HTTP Requests and Responses
            browser_params[i].http_instrument = True
            # Record cookie changes
            browser_params[i].cookie_instrument = True
            # Record Navigations
            browser_params[i].navigation_instrument = True
            # Record JS Web API calls
            browser_params[i].js_instrument = True
            # Record the callstack of all WebRequests made
            browser_params[i].callstack_instrument = True
            # Record DNS resolution
            browser_params[i].dns_instrument = True
            # Perform bot mitigation: scrolling the page, random pauses
            browser_params[i].bot_mitigation = True
            # Record all body content in leveldb
            # browser_params[i].save_content = "main_frame,ping,script,sub_frame,xmlhttprequest,other"
            browser_params[i].custom_params = {'dump_profile': True, 'profile_dir': str(self.profiles_dir)}

        if self.cmp:
            for i in range(self.num_browsers):
                t = i % 3
                accept_cmp = self.lists_dir.joinpath('accept-cookies.tar')
                reject_cmp = self.lists_dir.joinpath('reject-cookies.tar')
                if(t == 0):
                    browser_params[i].seed_tar = None
                elif(t == 1):
                    browser_params[i].seed_tar = accept_cmp
                elif(t == 2):
                    browser_params[i].seed_tar = reject_cmp

        with TaskManager(
            manager_params,
            browser_params,
            SQLiteStorageProvider(self.db_path),
            LevelDbProvider(self.crawl_dir.joinpath('precrawl-leveldb'))
        ) as manager:

            if cookie_interaction:
                css_selectors = get_idcac_css_selectors()
            # Use this value for assigning browsers during CMP crawls
            offset = 0
            # Visits the sites
            cookiedir=self.crawl_dir.joinpath('pickled-cookies')
            for _, (index, site, selector) in enumerate(sites):

                def callback(success: bool, val: str = site) -> None:
                    print(
                        f"CommandSequence for {val} ran {'successfully' if success else 'unsuccessfully'}"
                    )

                # Parallelize sites over all number of browsers set above.
                command_sequence = CommandSequence(
                    site,
                    site_rank=index,
                    reset=True,
                    callback=callback,
                )

                # Start by visiting the page
                command_sequence.append_command(GetCommand(url=site, sleep=3), timeout=60)

                if cookie_interaction:
                    # command_sequence.append_command(AcceptCookiesCommand(css_selectors=css_selectors), timeout=180)
                    command_sequence.append_command(RejectCookiesCommand(cookie_banner_selector=selector))
                    command_sequence.append_command(CollectCookiesCommand(stage='post-reject', output_path=cookiedir))

                if screenshot:
                    command_sequence.append_command(SaveScreenshotCommand(suffix=''))
                    command_sequence.append_command(ScreenshotFullPageCommand(suffix='full'))

                if not self.cmp:
                    # Run commands across the three browsers (simple parallelization)
                    manager.execute_command_sequence(command_sequence)
                else:
                    # Visit the same site by no-interact/accept/reject CMP browsers
                    for i in range(offset, offset + 3):
                        manager.execute_command_sequence(command_sequence, index=i)
                    offset = 0 if i == self.num_browsers - 1 else i + 1



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Conduct precrawl of the url list.')
    parser.add_argument('--type', choices=['test','small','full'], default='full')
    parser.add_argument('--cmp', action='store_true')
    parser.add_argument('--cookies', action='store_true')
    parser.add_argument('--browsers', type=int, default=1)
    parser.add_argument('--display', choices=['native','headless','xvfb'], default='headless')
    parser.add_argument('--screenshots', choices=['full','viewport','both','none'], default='none')
    parser.add_argument('--data', type=Path, default=Path('../data'))
    parser.add_argument('--logs', type=Path, default=Path('../logs'))
    parser.add_argument('--lists', type=Path, default=Path('../crawl/lists'))
    parser.add_argument('--urls', type=Path, default=Path('urls.json'))
    parser.add_argument('--name', type=ascii)
    args = parser.parse_args()

    crawl = Precrawl(
        url_list = args.urls,
        data_dir = args.data,
        log_dir = args.logs,
        lists_dir = args.lists,
        num_browsers = args.browsers,
        display_mode = args.display,
        cmp = args.cmp,
        name = args.name
    )

    crawl.do_crawl(category=args.type, cookie_interaction=args.cookies, screenshot=args.screenshots)
