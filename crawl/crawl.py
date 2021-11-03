import logging
import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
# TODO: need to install our packages as part of OpenWPM
# from tldextract import extract
from hashlib import md5


import sys
sys.path.append("/opt/OpenWPM")

from openwpm.command_sequence import CommandSequence
from openwpm.commands.browser_commands import GetCommand
from openwpm.commands.profile_commands import DumpProfileCommand
from openwpm.config import BrowserParams, ManagerParams
from openwpm.storage.sql_provider import SQLiteStorageProvider
from openwpm.storage.leveldb import LevelDbProvider
from openwpm.task_manager import TaskManager

from idcac_cookie_selectors import get_idcac_css_selectors
from command_accept_cookies import AcceptCookiesCommand
from command_reject_cookies import RejectCookiesCommand
from command_collect_cookies import CollectCookiesCommand


class Crawl:

    def __init__(
        self,
        url_list,
        data_dir,
        log_dir,
        lists_dir,
        num_browsers,
        display_mode,
        features,
        name
    ):
        self.num_browsers = num_browsers
        self.display_mode = display_mode
        self._setup_directories(
            data_dir=data_dir,
            log_dir=log_dir,
            lists_dir=lists_dir,
            name=name
        )
        self._setup_crawl_features(features)
        self.sites = self._parse_site_list(url_list)

    def do_crawl(self, category):
        manager_params = ManagerParams(num_browsers=self.num_browsers)
        manager_params.data_directory = self.crawl_dir
        manager_params.log_path = self.log_dir.joinpath('crawl-openwpm.log')

        browser_params = self._setup_browser_params()
        with TaskManager(
            manager_params,
            browser_params,
            SQLiteStorageProvider(self.db_path),
            LevelDbProvider(self.crawl_dir.joinpath('crawl-leveldb'))
        ) as tm:
            if category and category == 'test':
                for site in self.sites[:3]:
                    self._browse(tm, site)
                return
            for site in self.sites:
                if category and site['category'] != category:
                    continue
                self._browse(tm, site)

    def _setup_directories(self, data_dir, log_dir, lists_dir, name):
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
            format="%(asctime)s | Crawl | %(message)s",
            handlers=[
                logging.FileHandler(self.log_dir.joinpath('crawl.log')),
                logging.StreamHandler()
            ]
        )

        self.db_path = self.crawl_dir.joinpath('crawl.sqlite')
        logging.info(f'Database set to {self.db_path}')

        self.lists_dir = Path(os.path.realpath(lists_dir))

    def _setup_crawl_features(self, features):
        self.features = features
        if features['accept_banner']:
            self.css_selectors = get_idcac_css_selectors()
        if features['cmp']:
            self.accept_cmp = self.lists_dir.joinpath('accept-cookies.tar')
            self.reject_cmp = self.lists_dir.joinpath('reject-cookies.tar')
        if features['collect_cookies']:
            self.cookie_dir = self.crawl_dir.joinpath('pickled_cookies')
        if features['dump_profiles']:
            self.profiles_dir = self.crawl_dir.joinpath('profiles')

    def _setup_browser_params(self):
        browser_params = [BrowserParams(display_mode=self.display_mode)
                          for _ in range(self.num_browsers)]

        # Update browser configuration (use this for per-browser settings)
        for i in range(self.num_browsers):
            # Record HTTP Requests and Responses
            browser_params[i].http_instrument = self.features['collect_data']
            # Record cookie changes
            browser_params[i].cookie_instrument = self.features['collect_data']
            # Record Navigations
            browser_params[i].navigation_instrument = self.features['collect_data']
            # Record JS Web API calls
            browser_params[i].js_instrument = self.features['collect_data']
            # Record the callstack of all WebRequests made
            browser_params[i].callstack_instrument = self.features['collect_data']
            # Record DNS resolution
            browser_params[i].dns_instrument = self.features['collect_data']
            # Perform bot mitigation: scrolling the page, random pauses
            browser_params[i].bot_mitigation = True
            # Record all body content in leveldb
            browser_params[i].save_content = self.features['collect_content']

        return browser_params

    def _parse_site_list(self, url_list):
        sites = []

        if (url_list.suffix == '.json'):
            with open(self.lists_dir.joinpath(url_list)) as f:
                self.urls = json.load(f)
            rank = 1
            for k, v in self.urls.items():
                logging.info(f"Imported {len(v)} items in the {k} category")
                for url in v:
                    site = {
                        # 'tld': '.'.join(extract(row.url)[1:]),
                        'tld': url,
                        'url': url,
                        'id': rank
                    }
                    sites.append(site)
                    rank += 1
        elif (url_list.suffix == '.sqlite'):
            # TODO: Handle sqlite url lists - see main crawl code
            pass
        else:
            raise ValueError('Unrecognised format for url list file.')

        return sites

    def _browse(self, tm, site):
        if self.features['cmp']:
            self._browse_with_action(tm, site, action='accept_cmp', profile=self.accept_cmp)
            self._browse_with_action(tm, site, action='reject_cmp', profile=self.reject_cmp)
        if self.features['accept_banner']:
            self._browse_with_action(tm, site, action='accept_banner')
        if self.features['reject_banner']:
            self._browse_with_action(tm, site, action='reject_banner')
        if self.features['vanilla']:
            self._browse_with_action(tm, site, action='vanilla')

    def _browse_with_action(self, tm, site, action=None, profile=None):
        def callback(self, success: bool, val: str = site['tld']) -> None:
            print(
                f"CommandSequence for {val} ran {'successfully' if success else 'unsuccessfully'}"
            )
        cs = CommandSequence(
            url=site['tld'], site_rank=site['id'], reset=True, callback=callback)
        cs.append_command(GetCommand(url=site['url'], sleep=3), timeout=60)

        if self.features['collect_cookies'] and (action == 'accept_banner' or
                                                 action == 'reject_banner'):
            cs.append_command(CollectCookiesCommand(stage='pre-accept',
                                                    output_path=self.cookie_dir))

        if action == 'accept_banner':
            cs.append_command(AcceptCookiesCommand(css_selectors=self.css_selectors),
                              timeout=180)

        if action == 'reject_banner':
            cs.append_command(RejectCookiesCommand(cookie_banner_selector=site['selector']))

        if self.features['collect_cookies']:
            if action == 'accept_banner' or action == 'reject_banner':
                stage = 'post_accept'
            else:
                stage = 'vanilla'
            cs.append_command(CollectCookiesCommand(stage=stage,
                                                    output_path=self.cookie_dir))

        if self.features['screenshot']:
            cs.append_command(ScreenshotFullPageCommand(suffix=''))

        if self.features['dump_profiles']:
            hashed_url = md5(site['tld'].encode('utf-8')).hexdigest()
            tar = self.profiles_dir.joinpath(f'{hashed_url}-{action}.tar.gz')
            cs.append_command(DumpProfileCommand(
                tar_path=tar, close_webdriver=True, compress=True))

        tm.execute_command_sequence(cs, seed_tar=profile)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Conduct a crawl of the url list.')
    parser.add_argument('--type', choices=['test','small','full'], default='full')
    parser.add_argument('--cmp', action='store_true')
    parser.add_argument('--accept_banner', action='store_true')
    parser.add_argument('--reject_banner', action='store_true')
    parser.add_argument('--vanilla', action='store_true')
    parser.add_argument('--collect_cookies', action='store_true')
    parser.add_argument('--collect_data', action='store_true')
    parser.add_argument('--collect_content', action='store_true')
    parser.add_argument('--dump_profiles', action='store_true')
    parser.add_argument('--browsers', type=int, default=1)
    parser.add_argument('--display', choices=['native','headless','xvfb'], default='headless')
    parser.add_argument('--screenshots', action='store_true')
    # parser.add_argument('--screenshots', choices=['full','viewport','both','none'], default='none')
    parser.add_argument('--data', type=Path, default=Path('../data'))
    parser.add_argument('--logs', type=Path, default=Path('../logs'))
    parser.add_argument('--lists', type=Path, default=Path('../crawl/lists'))
    parser.add_argument('--urls', type=Path, default=Path('urls.json'))
    parser.add_argument('--name', type=ascii)
    args = parser.parse_args()

    features = {
        'cmp': args.cmp,
        'accept_banner': args.accept_banner,
        'reject_banner': args.reject_banner,
        'vanilla': args.vanilla,
        'collect_cookies': args.collect_cookies,
        'collect_data': args.collect_data,
        'collect_content': args.collect_content,
        'dump_profiles': args.dump_profiles,
        'screenshot': args.screenshots
    }
    # Fix argparse adding quotes to strings
    if args.name:
        args.name = args.name[1:-1]

    if args.type == 'full':
        category = None
    if args.type == 'small':
        category = 'fire'
    if args.type == 'test':
        category = 'test'
        args.browsers = 1

    crawl = Crawl(
        url_list = args.urls,
        data_dir = args.data,
        log_dir = args.logs,
        lists_dir = args.lists,
        num_browsers = args.browsers,
        display_mode = args.display,
        features = features,
        name = args.name
    )

    crawl.do_crawl(category=category)
