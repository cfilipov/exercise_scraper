#!/usr/bin/env python

from __future__ import print_function

"""A script for scraping data from the ExRx.net exercise database."""

__author__ = 'jason.a.parent@gmail.com (Jason Parent)'

# Standard library imports...
from itertools import chain, imap

import argparse
import json
import re
import sys
import time
import urlparse

# Third-party imports...
import bs4
import requests


EXRX_URL = 'http://localhost:8000'
EXRX_LISTS_URL = 'http://localhost:8000/Lists/'


def reduce_whitespace(text):
    """Removes leading and trailing whitespace and reduces internal whitespace to single spaces."""
    return re.sub(r'\s+', ' ', text).strip()


def find_tag_with_text(html, tag_name, text):
    """Finds a single tag in the given HTML with the specified name and text."""
    return html.find(lambda t: t.name == tag_name and reduce_whitespace(t.get_text()).startswith(text))


def find_tags_with_text(html, tag_name, text):
    """Finds all tags in the given HTML with the specified name and text."""
    return html.find_all(lambda t: t.name == tag_name and reduce_whitespace(t.get_text()).startswith(text))


def find_tag_with_child(html, tag_name, child):
    """
    Finds a single tag in the given HTML with the specified tag name
    that contains the specified child tag name.
    """
    return html.find(lambda t: t.name == tag_name and t.find(child))


def find_tag_with_parent(html, tag_name, parent):
    """
    Finds a single tag in the given HTML with the specified tag name
    that contains the specified parent tag name.
    """
    return html.find(lambda t: t.name == parent and t.find(tag_name)).find(tag_name)


def find_sibling_element(tag, sibling):
    """Finds a sibling tag with the specified name for the specified tag."""
    sibling_node = tag.next_sibling

    while not isinstance(sibling_node, bs4.element.Tag) and sibling_node.name != sibling:
        sibling_node = sibling_node.next_sibling

    return sibling_node


def name(html):
    """The name of the exercise."""
    heading = find_tag_with_parent(html, tag_name='a', parent='h1')

    return re.sub(r'\s+', ' ', heading.get_text())


def gif(html):
    """The animated GIF that demonstrates the exercise."""
    global EXRX_URL
    image = html.find('img', src=re.compile(r'AnimatedEx[^.]*.gif'))

    return urlparse.urljoin(EXRX_URL, image['src'].lstrip('../../'))


def instructions(html, heading_text):
    """Instructions for the exercise."""
    heading = find_tag_with_text(html, tag_name='p', text=heading_text)

    # Handle missing 'Preparation' heading...
    if not heading:
        heading = find_tag_with_text(html, tag_name='h2', text='Instructions')

    content_element = find_sibling_element(heading, sibling='dl')
    text = ''.join([tag.get_text() for tag in content_element.find_all('dd')])

    return reduce_whitespace(text)


def comments(html):
    """Comments for the exercise."""
    heading = find_tag_with_text(html, tag_name='h2', text='Comments')
    content_element = find_sibling_element(heading, sibling='dl')
    text = ''.join([tag.get_text() for tag in content_element.find_all('dd')])

    return reduce_whitespace(text)


def classification(html, heading_text):
    """Classification for the exercise."""
    heading = find_tag_with_text(html, tag_name='td', text=heading_text)
    content_element = find_sibling_element(heading, sibling='td')
    text = content_element.get_text()

    return reduce_whitespace(text)


def muscles(html, heading_text):
    """Muscles for the exercise."""
    heading = find_tag_with_text(html, 'p', text=heading_text)
    content_element = find_sibling_element(heading, sibling='ul')
    muscles_list = content_element.find_all('li')
    return [reduce_whitespace(m.get_text()) for m in muscles_list]


def find_muscle_headings(html):
    title = find_tag_with_text(html, tag_name='h2', text='Muscles')
    muscle_heading = find_sibling_element(title, sibling='p')
    headings = []
    while muscle_heading is not None:
        heading_text = ''.join(muscle_heading.find_all(text=True))
        heading_text = reduce_whitespace(heading_text)
        headings.append(heading_text)
        # print(heading_text)
        muscle_heading = muscle_heading.find_next_sibling('p')
    return headings

def create_exercise_object(html):
    # print('muscle headings: {}'.format(find_muscle_headings(html)))
    exercise = dict()

    # Add name...
    try:
        exercise['name'] = name(html)
    except Exception:
        raise Exception('Error adding name...')

    # Add gif...
    try:
        exercise['gif'] = gif(html)
    except Exception:
        raise Exception('Error adding gif...')

    # Add instructions...
    try:
        exercise['instructions'] = {
            'preparation': instructions(html, heading_text='Preparation'),
            'execution': instructions(html, heading_text='Execution')
        }
    except Exception:
        raise Exception('Error adding instructions...')

    # Add comments...
    try:
        exercise['comments'] = comments(html)
    except Exception:
        raise Exception('Error adding comments...')

    # Add classification...
    try:
        exercise['classification'] = {
            'utility': classification(html, 'Utility'),
            'mechanics': classification(html, 'Mechanics'),
            'force': classification(html, 'Force')
        }
    except Exception:
        raise Exception('Error adding classification...')

    # Add muscles...
    try:
        headings = find_muscle_headings(html)
        mm = {}
        for h in headings:
            mm[h] = muscles(html, h)
        exercise['muscles'] = mm
    except Exception:
        # Error probably occurring with specialized exercise (i.e. Turkish Get Up)...
        raise Exception('Error adding muscles...')

    return exercise

# TODO: Use threading...
def exercise_scraper(*equipment):
    global EXRX_LISTS_URL
    exercises = list()
    num_errors = 0

    # Retrieve the exercises main page...
    exercises_dir_url = urlparse.urljoin(EXRX_LISTS_URL, 'Directory.html')
    exercises_dir_request = requests.get(exercises_dir_url)

    if exercises_dir_request.status_code == requests.codes.ok:
        exercises_dir_html = bs4.BeautifulSoup(exercises_dir_request.content, 'lxml')

        # Get all links that lead to exercise groups...
        exercise_group_links = exercises_dir_html.find_all('a', href=re.compile(r'ExList[^#]*#'))

        for link in exercise_group_links:
            url = urlparse.urljoin(EXRX_LISTS_URL, link['href'])
            request = requests.get(url)

            if request.status_code == requests.codes.ok:
                weight_exercises_dir_html = bs4.BeautifulSoup(request.content, 'lxml')

                def top_level_li(tag):
                    return tag.name == 'ul' and tag.parent.name != 'li'
                res = weight_exercises_dir_html.find_all(top_level_li)
                for r in res:
                    top_list = r.find_all('li', recursive=False)
                    for item in top_list:
                        if item.contents[0].name is None:
                            equipment = reduce_whitespace(item.contents[0])
                            links = item.find_all('a')
                            for link in links:
                                url = urlparse.urljoin(url, link['href'])
                                request = requests.get(url)

                                if request.status_code == requests.codes.ok:
                                    exercise_html = bs4.BeautifulSoup(request.content, 'lxml')

                                    # TODO: Print to log instead of console...
                                    try:
                                        exercise = create_exercise_object(exercise_html)
                                        exercise['equipment'] = equipment
                                        exercise['source'] = url
                                        print('Adding:', exercise['name'])
                                        exercises.append(exercise)
                                    except Exception, error:
                                        num_errors += 1
                                        print(error, url)
                # return exercises

    print('# errors:', num_errors)

    return exercises


def main():
    EQUIPMENT_MAP = {
        'barbell': r'/BB',
        'dumbbell': r'/DB'
    }

    parser = argparse.ArgumentParser()
    parser.add_argument('--equipment', dest='equipment', action='store', nargs='+', help='Included equipment')
    parsed = parser.parse_args()

    equipment = (EQUIPMENT_MAP['barbell'], EQUIPMENT_MAP['dumbbell'])

    if parsed.equipment:
        equipment = [EQUIPMENT_MAP[e] for e in parsed.equipment]
    else:
        print('No equipment specified...')

    exercises = exercise_scraper(*equipment)
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