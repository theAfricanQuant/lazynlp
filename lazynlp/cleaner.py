from collections import Counter
import lxml
import os
import string
import re

import html
import justext
from unidecode import unidecode

from .utils import *

dir_path = os.path.dirname(os.path.realpath(__file__))


def parse_html(page):
    """ Clean HTML tags for webpages that aren't Gutenberg books
    """
    try:
        parts = justext.justext(page, justext.get_stoplist('English'))
    except lxml.etree.ParserError as e:
        print('Page empty')
        return ''
    except UnicodeDecodeError as e:
        print("Can't decode utf-8")
        return ''
    paragraphs = [part.text for part in parts if not part.is_boilerplate]
    return '\n\n'.join(paragraphs)


def clean_html(txt):
    """ Clean HTML tags of webpages downloaded
    Use this function for Gutenberg book format.
    """
    style_tag_re = re.compile('<style.*?>[^<>]*?</style>')
    txt = re.sub(style_tag_re, ' ', txt)
    script_tag_re = re.compile('<script.*?>[^<>]*?</script>')
    txt = re.sub(script_tag_re, ' ', txt)
    doc_tag_re = re.compile('<!DOCTYPE[^<>]*?>')
    txt = re.sub(doc_tag_re, ' ', txt)
    html_tag_re = re.compile('<.*?>')
    txt = connect_lines(txt)
    return re.sub(html_tag_re, ' ', txt).strip()


def remove_non_alphanumeric(txt):
    """ Remove all non-alphanumeric characters, except space, from the text
    """
    return re.sub(r'[^a-zA-Z0-9 ]+', '', txt)


def remove_non_alpha(txt):
    """ Remove all non-alphabetical characters, except space, from the text
    """
    return re.sub(r'[^a-zA-Z ]+', '', txt)


def transliterate(txt):
    """ Transliterate foreign characters into its Latin spelling.
    For example, '\u5317\u4EB0' will be transliterated to 'Bei Jing'
    """
    return unidecode(txt)


def collapse_white_spaces(txt):
    """Collapse multiple white spaces into one white space
    """
    clean_txt = ''
    prev = None
    for c in txt:
        if c == ' ' and prev == ' ':
            continue
        else:
            clean_txt += c
        prev = c
    return clean_txt


def connect_lines(txt, line_sep='\n'):
    """ This happens when you crawl text from a webpage and
    they have random breaking lines mid-sentence.

    This function is to connect those lines.

    Two consecutive lines are separated by line_sep.
    """
    lines = txt.split('\n')

    result, curr = '', ''
    for line in lines:
        if line := line.strip():
            curr += f'{line} '

        else:
            if curr:
                result += (curr + '\n')
            result += line_sep
            curr = ''
    return result + curr


def clean_page(page):
    try:
        page = page.decode('utf-8')
    except UnicodeDecodeError as e:
        print("Can't decode", e)

    page = page.strip()
    if not page:
        return ''
    txt = parse_html(page)
    txt = transliterate(txt)
    txt = html.unescape(txt)
    return txt


def find_unprintable(txt):
    """Find the list of unprintable character
    and return a Counter of them
    """
    printable = set(string.printable)
    unprintable = [c for c in txt if c not in printable]
    return Counter(unprintable)


def replace_unprintable(txt):
    """Replace non-printable characters with printable characters
    """
    printable = set(string.printable)
    lines = open(f'{dir_path}/unprintable_chars.txt', 'r').readlines()
    chars = {line.strip().split(':')[0]:
             line.strip().split(':')[1] for line in lines}
    return ''.join([c if c in printable else chars[c] for c in txt])


def dedup_lines(files, outfold):
    """
    Files is a list of files
    Remove all duplicated lines across all files
    Start with files[0]:
        remove dupped lines and save it to outfold/files[0]
    ...
    For files[n]:
        remove lines that have appeared in files[:n-1] and also in files[n]
        and save to outfold/files[n]

    """
    os.makedirs(outfold, exist_ok=True)
    total, unique = 0, 0

    if isinstance(files, str):
        files = [files]

    seen = set()
    for i, file in enumerate(files):
        print('Processing:', file)
        filename = get_filename(file)
        with open(os.path.join(outfold, f'{str(i)}_{filename}'), 'w') as out:
            with open(file, 'r') as f_in:
                while line := f_in.readline():
                    hashed = get_hash(line.strip())
                    if hashed not in seen:
                        out.write(line)
                        seen.add(hashed)
                        unique += 1
                    total += 1
    if total == 0:
        raise ValueError('The files list seems to be empty')
    print(f'{unique} unique lines out of {total}: {unique / total}')


def dedup_lines_from_new_file(original_files, new_file, outfile):
    """ Get unique lines from new_file that aren't already in original_files
    """
    seen = set()

    if isinstance(original_files, str):
        original_files = [original_files]

    for original_file in original_files:
        with open(original_file, 'r') as f_in:
            while line := f_in.readline():
                seen.add(get_hash(line.strip()))
    with open(outfile, 'w') as out:
        total, unique = 0, 0
        with open(new_file, 'r') as f_in:
            while line := f_in.readline():
                hashed = get_hash(line.strip())
                if hashed not in seen:
                    out.write(line)
                    seen.add(hashed)
                    unique += 1
                total += 1
    print(f'{unique} unique lines out of {total}: {unique / total}')
