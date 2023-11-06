import datetime as dt
from io import BytesIO
import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from constants import BASE_DIR, MAIN_DOC_URL, DATETIME_FORMAT
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li', attrs={'class': 'toctree-l1'})
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = session.get(version_link) 
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    soup = BeautifulSoup(response.text, features='lxml')
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')

    result = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text = a_tag.text
        text_match = re.search(pattern, text)
        if text_match:
            version, status = text_match.groups()
        else:
            version, status = text, ''

        result.append((link, version, status))

    return result


def download(session):
    now = dt.datetime.now()
    archives_dir = BASE_DIR / 'downloads' / now.strftime(DATETIME_FORMAT)
    archives_dir.mkdir(exist_ok=True)
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    soup = BeautifulSoup(response.text, features='lxml')
    doc_table = find_tag(soup, 'table', {'class': 'docutils'})
    a_tags = doc_table.find_all('a')
    # results = []
    for a_tag in tqdm(a_tags):
        ref = a_tag['href']
        link = urljoin(downloads_url, ref)
        response = get_response(session, link)
        filename = re.search(r'.*/([^/]+)$', link).group(1)
        with open(archives_dir / filename, 'bw') as out_file:
            out_file.write(response.content)
        
        # results.append((link, filename))
    # if response is None:
    #     return
    # return results
    logging.info(f'Архив был загружен и сохранён: {archives_dir}')


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
}


def main():    
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()

    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    
    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.') 


if __name__ == '__main__':
    main()
