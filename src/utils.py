from bs4 import BeautifulSoup

from exceptions import ParserFindTagException, EmptyResponseException


def get_response(session, url):
    response = session.get(url)
    response.raise_for_status()
    if response.content is None:
        raise EmptyResponseException

    response.encoding = 'utf-8'
    return response


def create_soup(session, url):
    response = get_response(session, url)
    return BeautifulSoup(response.text, features='lxml')


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}.'
        raise ParserFindTagException(error_msg)
    return searched_tag
