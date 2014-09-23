#!/usr/bin/env python

"""Module docstring."""

__author__ = 'jason.a.parent@gmail.com (Jason Parent)'

# Standard library imports...
import argparse
import json
import os
import sys

# Third-party imports...
import bs4
import requests


def exercise_scraper():
    exercises = list()

    # Retrieve the exercises main page...
    exercises_dir_url = 'http://www.exrx.net/Lists/Directory.html'
    exercises_dir_request = requests.get(exercises_dir_url)

    if exercises_dir_request.status_code == requests.codes.ok:
        exercises_dir_html = bs4.BeautifulSoup(exercises_dir_request.content)

        # The list of exercises is located in the third table in the page...
        exercises_table_html = exercises_dir_html.select('table[border="1"]')[0]
        exercises_list_html = exercises_table_html.find('ul')

        for item in exercises_list_html.select('li'):
            item_anchor = item.find('a')

            if item_anchor != -1:
                print item_anchor.string, item_anchor['href']


def main():
    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)