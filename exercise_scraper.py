#!/usr/bin/env python

from __future__ import print_function

"""Module docstring."""

__author__ = 'jason.a.parent@gmail.com (Jason Parent)'

# Standard library imports...
import argparse
import json
import os
import sys
import urlparse

# Third-party imports...
import bs4
import requests


EXERCISES_LISTS_URL = 'http://www.exrx.net/Lists/'


def exercise_scraper():
    exercises = dict()

    # Retrieve the exercises main page...
    exercises_dir_url = urlparse.urljoin(EXERCISES_LISTS_URL, 'Directory.html')
    exercises_dir_request = requests.get(exercises_dir_url)

    if exercises_dir_request.status_code == requests.codes.ok:
        exercises_dir_html = bs4.BeautifulSoup(exercises_dir_request.content)

        # The list of exercises is located in the third table in the page...
        exercises_table_html = exercises_dir_html.select('table[border="1"]')[0]

        def get_muscle_group_hrefs(table_html):
            exercises_list_html = exercises_table_html.td.ul

            for item in exercises_list_html.select('li'):
                item_anchor = item.find('a')

                if item_anchor != -1:
                    item_href = item_anchor['href']

                    if item_href.startswith('ExList') and item_href.find('#') == -1:
                        muscle_group = item_anchor.string

                        print('Adding muscle group:', muscle_group)

                        # Add first-level directory item to 'exercises' dictionary...
                        exercises[muscle_group] = dict(url=urlparse.urljoin(EXERCISES_LISTS_URL, item_href))

        get_muscle_group_hrefs(exercises_table_html)

        for exercise_key, exercise_value in exercises.items():
            print('Retrieving exercises for muscle group:', exercise_key)

            muscle_group_request = requests.get(exercise_value.get('url'))

            if muscle_group_request.status_code == requests.codes.ok:
                muscle_group_html = bs4.BeautifulSoup(muscle_group_request.content)


def main():
    exercise_scraper()

    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)