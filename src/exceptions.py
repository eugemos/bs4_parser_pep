class ApplicationException(Exception):
    """Базовый класс собственных исключений программы."""
    pass


class ContentException(ApplicationException):
    """Вызывается, когда что-то пошло не так при обработке полученных
    данных.
    """
    pass


class EmptyResponseException(ContentException):
    """Вызывается, когда от сайта получен пустой ответ."""
    pass


class ParserFindTagException(ContentException):
    """Вызывается, когда парсер не может найти необходимый тег."""
    pass
