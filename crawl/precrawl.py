import logging
import json
import os
from datetime import datetime, timezone
from pathlib import Path


import sys
sys.path.append("/opt/OpenWPM")

from openwpm.command_sequence import CommandSequence
from openwpm.commands.browser_commands import GetCommand
from openwpm.config import BrowserParams, ManagerParams
from openwpm.storage.sql_provider import SQLiteStorageProvider
from openwpm.storage.leveldb import LevelDbProvider
from openwpm.task_manager import TaskManager


class Precrawl:

    def __init__(
        self,
        url_list,
        format='json',
        data_dir='../data',
        log_dir='../logs',
        num_browsers=4,
        display_mode='headless'
    ):

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        self.timestamp = timestamp # so we can set it later for openwmp

        self.log_dir = os.path.realpath(log_dir)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | Precrawl | %(message)s",
            handlers=[
                logging.FileHandler(
                    os.path.join(self.log_dir, f'{timestamp}-precrawl.log')
                ),
                logging.StreamHandler()
            ]
        )

        self.num_browsers = num_browsers
        self.display_mode = display_mode
        
        self.data_dir = os.path.realpath(data_dir)
        self.DB_PATH = os.path.join(self.data_dir, f'{timestamp}-precrawl.sqlite')
        logging.info(f'Database set to {self.DB_PATH}')

        if (format == 'json'):
            with open(url_list) as f:
                self.urls = json.load(f)
            for k, v in self.urls.items():
                logging.info(f"Imported {len(v)} items in the {k} category")

    def crawl(self, category='all', screenshot=False):

        if(category == 'all'):
            sites = list()
            for _, urls in self.urls:
                sites.extend(urls)
        else:
            sites = self.urls[category]

        manager_params = ManagerParams(num_browsers=self.num_browsers)
        manager_params.data_directory = Path(self.data_dir)
        manager_params.log_path = Path(
            os.path.join(self.log_dir, f'{self.timestamp}-precrawl-openwpm.log')
        )
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

        with TaskManager(
            manager_params,
            browser_params,
            SQLiteStorageProvider(Path(self.DB_PATH)),
            LevelDbProvider(Path(self.data_dir).joinpath(f'{self.timestamp}-precrawl-leveldb'))
        ) as manager:

            # Visits the sites
            for index, site in enumerate(sites):

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

                if screenshot:
                    command_sequence.append_command(
                        command_sequence.save_screenshot(suffix=self.timestamp))

                # Run commands across the three browsers (simple parallelization)
                manager.execute_command_sequence(command_sequence)

if __name__ == "__main__":
    crawl = Precrawl('/opt/crawl/lists/urls.json')
    crawl.crawl(category='fire')
