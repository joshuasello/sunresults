""" sunresults.py

"""

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime

import requests
from Tools.i18n.msgfmt import usage
from bs4 import BeautifulSoup, Tag
from plyer import notification
from tabulate import tabulate

__version__ = "1.0"
__author__ = "Joshua Sello"


def main() -> None:
    # Run setup dialogue

    print("▒█▀▀▀█ ▒█░▒█ ▒█▄░▒█ ▒█▀▀█ ▒█▀▀▀ ▒█▀▀▀█ ▒█░▒█ ▒█░░░ ▀▀█▀▀ ▒█▀▀▀█")
    print("░▀▀▀▄▄ ▒█░▒█ ▒█▒█▒█ ▒█▄▄▀ ▒█▀▀▀ ░▀▀▀▄▄ ▒█░▒█ ▒█░░░ ░▒█░░ ░▀▀▀▄▄")
    print(f"▒█▄▄▄█ ░▀▄▄▀ ▒█░░▀█ ▒█░▒█ ▒█▄▄▄ ▒█▄▄▄█ ░▀▄▄▀ ▒█▄▄█ ░▒█░░ ▒█▄▄▄█ v{__version__}\n")

    print("\nLogin")
    username = input("Username: ").strip()
    password = input('Password: ')

    user = User(username, password)

    current_results = user.fetch_results()

    if not current_results:
        print("Credentials invalid. Could not retrieve results.")
        return

    clear_console()

    print("\nCurrent Results")
    print(tabulate([[module, result.final_mark] for module, result in current_results.items()],
                   headers=['Module', 'Result'], tablefmt='orgtbl'))
    print(f"\nCurrent Average: {get_results_average(current_results)}\n")

    print("Monitoring for new results (Press Ctrl + C to exit)...")

    # Start main event loop
    while True:
        try:
            # Wait for a min
            #time.sleep(60)

            # Extract grades
            recent_results = user.fetch_results()
            updated_results = {
                module: result for module, result in recent_results.items()
                if current_results[module].final_mark != result.final_mark}

            if updated_results:  # Updated result is not empty
                # Update current results
                current_results = recent_results

                # Output updated results to terminal
                print(f"\nUpdated Results ({datetime.now().strftime('%d/%m/%Y %H:%M:%S')})")
                print(tabulate([[module, result.final_mark] for module, result in updated_results.items()],
                               headers=['Module', 'Result'], tablefmt='orgtbl'))
                print(f"\nCurrent Average: {get_results_average(current_results)}\n")

                # Notify user if grade state has been updated.
                notification.notify(
                    title='New Final Results!',
                    message=', '.join([f"{module}: {result.final_mark}" for module, result in updated_results.items()]),
                    app_name='Results Monitor'
                )
        except KeyboardInterrupt:
            print("Exiting...")
            return


# --------------------------------------------------
#   Utilities
# --------------------------------------------------

class BCodes:
    # source: https://stackoverflow.com/questions/287871/how-to-print-colored-text-to-the-terminal
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@dataclass
class Result:
    month: str
    class_mark: int
    progress_mark: int
    final_mark: int


class User:
    LEGACY_LOGIN_DOMAIN = 'https://sso-legacy.sun.ac.za'

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password

    def fetch_results(self) -> dict[str, Result]:
        # Log user in
        login_url = f'{self.LEGACY_LOGIN_DOMAIN}/cas/login?service=https://web-apps.sun.ac.za/AcademicResults/shiro-cas'

        # Fetch login form page content
        form_response: requests.Response = requests.get(url=login_url)
        login_page: BeautifulSoup = BeautifulSoup(form_response.content.decode('utf-8'), 'html.parser')

        # Fill form login data
        login_data: dict[str, str] = {tag.get_attribute_list('name')[0]: tag.get_attribute_list('value')[0]
                                      for tag in login_page.find_all('input')
                                      if tag.get_attribute_list('name')[0] is not None}
        login_data['username'] = self._username
        login_data['password'] = self._password

        results_page_url: str = self.LEGACY_LOGIN_DOMAIN + login_page.form['action']
        cookies = form_response.cookies

        results_response: requests.Response = requests.post(results_page_url, login_data, cookies=cookies)
        results_page: BeautifulSoup = BeautifulSoup(results_response.content.decode('utf-8'), 'html.parser')

        num_columns: int = 6

        results: dict[str, Result] = {}
        row: list[str] = []

        # Populate results array with page content
        for i, tag in enumerate(results_page.select('table[width] > tr > td > .PortletText1')):
            tag: Tag
            if (i + 1) % num_columns == 0:
                result_data = dict(zip(('month', 'module', 'class_mark', 'progress_mark', 'final_mark'), row))
                results[result_data["module"]] = Result(
                    month=result_data["month"],
                    class_mark=int(result_data["class_mark"] if result_data["class_mark"] else 0),
                    progress_mark=int(result_data["progress_mark"] if result_data["progress_mark"] else 0),
                    final_mark=int(result_data["final_mark"] if result_data["final_mark"] else 0)
                )
                row = []
            else:
                content = tag.contents[0]
                row.append(re.sub(' +', ' ', content.strip()) if isinstance(content, str) else None)

        return results


def get_results_average(results: dict[str, Result]) -> float:
    nonempty = [result.final_mark for result in results.values() if result.final_mark]
    return sum(nonempty) / len(nonempty)


def clear_console():
    # source: https://www.delftstack.com/howto/python/python-clear-console/
    command = 'clear'
    if os.name in ('nt', 'dos'):  # If Machine is running on Windows, use cls
        command = 'cls'
    os.system(command)


if __name__ == '__main__':
    main()
