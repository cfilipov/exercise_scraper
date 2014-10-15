#!/usr/bin/env python

from __future__ import print_function

"""A script for scraping data from the ExRx.net exercise database."""

__author__ = 'jason.a.parent@gmail.com (Jason Parent)'

# Standard library imports...
import json
import re
import sys
import time
import urlparse

# Third-party imports...
import bs4
import requests


EXRX_URL = 'http://www.exrx.net/'
EXRX_LISTS_URL = 'http://www.exrx.net/Lists/'


def is_exercise_page(html):
    # Check has instructions...
    has_instructions = html.find_all(lambda t: t.name == 'h2' and t.string == 'Instructions')

    if not has_instructions:
        print('No instructions')

    # Check has comments...
    # has_comments = html.find_all(lambda t: t.name == 'h2' and t.string == 'Comments')
    #
    # if not has_comments:
    #     print('No comments')

    # Check has classification...
    has_classification = html.find_all(lambda t: t.name == 'h2' and t.string == 'Classification')

    if not has_classification:
        print('No classification')

    # Check has muscles...
    has_muscles = html.find_all(lambda t: t.name == 'h2' and t.string == 'Muscles')

    if not has_muscles:
        print('No muscles')

    return bool(has_instructions and has_classification and has_muscles)
    # return bool(has_instructions and has_comments and has_classification and has_muscles)


def create_exercise_object(html):
    exercise = dict()

    # Add gif...
    try:
        def gif_filter(tag):
            src = tag.attrs.get('src', '')
            return tag.name == 'img' and '.gif' in src and 'AnimatedEx' in src

        gif = html.find(gif_filter)
        gif = gif.attrs.get('src', '').lstrip('../../')

        if gif:
            exercise['gif'] = urlparse.urljoin(EXRX_URL, gif)
    except Exception:
        raise Exception('Error adding gif...')

    # Add name...
    try:
        name = html.find(lambda t: t.name == 'a' and t.parent.name == 'h1').string
        name = re.sub(r'\s+', ' ', name)
        exercise['name'] = name
    except Exception:
        raise Exception('Error adding name...')

    # Add instructions...
    def get_instructions_sub(title):
        p = html.find(lambda t: t.name == 'p' and t.string == title)
        sibling = p.next_sibling

        while not isinstance(sibling, bs4.element.Tag) and sibling.name != 'dl':
            sibling = sibling.next_sibling            

        return ''.join([re.sub(r'\s+', ' ', tag.string) for tag in sibling.dd]).strip()

    try:
        preparation = get_instructions_sub('Preparation')
        execution = get_instructions_sub('Execution')
        exercise['instructions'] = {
            'preparation': preparation,
            'execution': execution
        }
    except Exception:
        raise Exception('Error adding instructions...')

    # Add comments...
    # def get_comments_sub():
    #     h2 = html.find(lambda t: t.name == 'h2' and t.string == 'Comments')
    #     sibling = h2.next_sibling
    #
    #     while not isinstance(sibling, bs4.element.Tag) and sibling.name != 'dl':
    #         sibling = sibling.next_sibling
    #
    #     return ''.join([re.sub(r'\s+', ' ', tag.string) for tag in sibling.dd]).strip()
    #
    # comments = get_comments_sub()
    #
    # exercise['comments'] = comments

    # Add classification...
    classification_table = html.find('blockquote').find('table')

    def find_classification_value(key):
        def is_td(tag):
            return (tag.name == 'td' and
                    tag.b and
                    tag.b.string and
                    tag.b.string.find(key) != -1)

        td = classification_table.find(is_td)
        sibling = td.next_sibling

        while not isinstance(sibling, bs4.element.Tag) and sibling.name != 'td':
            sibling = sibling.next_sibling

        return ''.join([re.sub(r'\s+', ' ', s) for s in sibling.strings]).strip()

    try:
        utility = find_classification_value('Utility')
        mechanics = find_classification_value('Mechanics')
        force = find_classification_value('Force')
        exercise['classification'] = {
            'utility': utility,
            'mechanics': mechanics,
            'force': force
        }
    except Exception:
        raise Exception('Error adding classification...')

    # Add muscles...
    def get_muscles_sub(title):
        p = html.find(lambda t: t.name == 'p' and t.string == title)
        sibling = p.next_sibling

        while not isinstance(sibling, bs4.element.Tag) and sibling.name != 'ul':
            sibling = sibling.next_sibling

        return [re.sub(r'\s+', ' ', ''.join(li.strings)).strip()
                for li in sibling.find_all('li') if li.strings]

    try:
        target = ''.join(get_muscles_sub('Target'))
        # synergists = get_muscles_sub('Synergists')
        # stabilizers = get_muscles_sub('Stabilizers')
        exercise['muscles'] = {
            'target': target,
            # 'synergists': synergists,
            # 'stabilizers': stabilizers
        }
    except Exception:
        raise Exception('Error adding muscles...')

    return exercise


def exercise_scraper():
    exercises = list()

    # Retrieve the exercises main page...
    exercises_dir_url = urlparse.urljoin(EXRX_LISTS_URL, 'Directory.html')
    exercises_dir_request = requests.get(exercises_dir_url)

    if exercises_dir_request.status_code == requests.codes.ok:
        exercises_dir_html = bs4.BeautifulSoup(exercises_dir_request.content)

        # Get all links that lead to exercise groups...
        def is_exercise_group_link(tag):
            return (tag.name == 'a' and 
                    tag.has_attr('href') and 
                    tag['href'].startswith('ExList') and 
                    tag['href'].find('#') == -1)

        for link in exercises_dir_html.find_all(is_exercise_group_link):
            href = link['href']
            url = urlparse.urljoin(EXRX_LISTS_URL, href)
            request = requests.get(url)

            if request.status_code == requests.codes.ok:
                weight_exercises_dir_html = bs4.BeautifulSoup(request.content)

                # Get all links that lead to exercises...
                def is_exercise_link(tag):
                    return (tag.name == 'a' and 
                            tag.has_attr('href') and 
                            tag['href'].find('WeightExercises') != -1)

                for link in weight_exercises_dir_html.find_all(is_exercise_link):
                    href = link['href']
                    url = urlparse.urljoin(url, href)
                    request = requests.get(url)

                    if request.status_code == requests.codes.ok:
                        exercise_html = bs4.BeautifulSoup(request.content)

                        if is_exercise_page(exercise_html):
                            try:
                                exercise = create_exercise_object(exercise_html)
                                exercises.append(exercise)
                            except Exception, error:
                                print(error, url)

                        else:
                            print('Not exercise page:', url)

    return exercises


def main():
    exercises = exercise_scraper()
    exercises_json = json.dumps({
        'exercises': exercises
    })

    with open('exercises.json', 'wt') as exercises_file:
        exercises_file.write(exercises_json)

    return 0


if __name__ == '__main__':
    start = time.time()
    status = main()
    print('Total time:', time.time() - start)
    sys.exit(status)