import datetime as dt
import logging
import csv

from prettytable import PrettyTable

from constants import (
    BASE_DIR, DATETIME_FORMAT, PRETTY_OUT_MODE, FILE_OUT_MODE, RESULTS_DIR_NAME
)


def control_output(results, cli_args):
    output = cli_args.output
    if output == PRETTY_OUT_MODE:
        pretty_output(results)
    elif output == FILE_OUT_MODE:
        file_output(results, cli_args)
    else:
        default_output(results)


def default_output(results):
    for row in results:
        print(*row)


def file_output(results, cli_args):
    results_dir = BASE_DIR / RESULTS_DIR_NAME
    results_dir.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    now_formatted = now.strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='unix')
        writer.writerows(results)

    logging.info(f'Файл с результатами был сохранён: {file_path}')


def pretty_output(results):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)
