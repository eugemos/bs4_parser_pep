from collections import defaultdict
import datetime as dt
import logging
import re
from urllib.parse import urljoin

from requests import RequestException
import requests_cache
from tqdm import tqdm

from constants import (
    BASE_DIR, MAIN_DOC_URL, MAIN_PEP_URL, DATETIME_FORMAT, EXPECTED_STATUS,
    DOWNLOADS_DIR_NAME
)
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import get_response, find_tag, create_soup
from exceptions import ParserFindTagException, ContentException


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = create_soup(session, whats_new_url)
    main_div = find_tag(
        soup, 'section', attrs={'id': 'what-s-new-in-python'}
    )
    div_with_ul = find_tag(
        main_div, 'div', attrs={'class': 'toctree-wrapper'}
    )
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        soup = create_soup(session, version_link)
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):
    soup = create_soup(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    signature = 'All versions'
    for ul in ul_tags:
        if signature in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ParserFindTagException('Не найден тег ul, содержащий '
                                     f'сигнатуру "{signature}".')

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
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = create_soup(session, downloads_url)
    doc_table = find_tag(soup, 'table', {'class': 'docutils'})
    a_tags = doc_table.find_all('a')
    now = dt.datetime.now()
    archives_dir = (
        BASE_DIR / DOWNLOADS_DIR_NAME / now.strftime(DATETIME_FORMAT)
    )
    archives_dir.mkdir(exist_ok=True, parents=True)
    for a_tag in tqdm(a_tags):
        ref = a_tag['href']
        link = urljoin(downloads_url, ref)
        response = get_response(session, link)
        filename = re.search(r'.*/([^/]+)$', link).group(1)
        with open(archives_dir / filename, 'bw') as out_file:
            out_file.write(response.content)

    logging.info(f'Архив был загружен и сохранён: {archives_dir}')


def pep(session):
    soup = create_soup(session, MAIN_PEP_URL)
    section = find_tag(soup, 'section', {'id': 'numerical-index'})
    tbody = find_tag(section, 'tbody')
    table_rows = tbody.find_all('tr')
    pep_count_by_status = defaultdict(int)
    for table_row in tqdm(table_rows):
        row_cells = table_row.find_all('td')
        pep_status_code = row_cells[0].text[1:]
        pep_ref = row_cells[1].a['href']
        pep_status = get_pep_status(session, pep_ref)
        expected_pep_statuses = EXPECTED_STATUS[pep_status_code]
        if pep_status not in expected_pep_statuses:
            logging.info(
                'Несовпадающие статусы:\n'
                f'{pep_ref}\n'
                f'Статус в карточке: {pep_status}\n'
                f'Ожидаемые статусы: {expected_pep_statuses}.'
            )

        pep_count_by_status[pep_status] += 1

    results = [('Статус', 'Количество')]
    for status, count in pep_count_by_status.items():
        results.append((status, count))

    results.append(('Total', len(table_rows)))
    return results


def get_pep_status(session, ref):
    soup = create_soup(session, urljoin(MAIN_PEP_URL, ref))
    dl_tag = find_tag(soup, 'section', {'id': 'pep-content'}).dl
    dt_tag = find_tag(
        dl_tag, lambda tag: tag.name == 'dt' and 'Status' in tag.text
    )
    dd_tag = dt_tag.next_sibling
    while dd_tag.name != 'dd':
        dd_tag = dd_tag.next_sibling

    return str(dd_tag.string)


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
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
    results = None
    try:
        results = MODE_TO_FUNCTION[parser_mode](session)
    except RequestException as error:
        logging.exception(
            'Возникла ошибка при загрузке страницы.',
            exc_info=error,
        )
    except ContentException as error:
        logging.exception(
            'Возникла ошибка при анализе полученных данных.',
            exc_info=error,
        )

    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
