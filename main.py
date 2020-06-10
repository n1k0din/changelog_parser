import typing as t
import csv
from collections import namedtuple

common_log = namedtuple('common_log', ['name', 'version', 'date', 'changelog'])
spec_log = namedtuple('spec_log', ['name', 'changelog'])

IE_NAME_PATTERN = "Версия {}."
IC_GROUP2_INDICATORS = {
    'lb6': 'ЛБ 6 CM3',
    'lb6pro': 'ЛБ 6.1 Pro CM3',
    'lb7': 'ЛБ 7.2'
}

CHANGELOG_TYPES = {
    'ЛБv6': 'lb6',
    'ЛБv6Pro': 'lb6pro',
    'ЛБv7': 'lb7'
}

# 'у О.В.': 'на сайте'
REPLACERS = {
    'CLASSIC': 'Релейный',
    'iAStar': 'iASTAR',
    'KONE_ESC': 'KONE ESC',
    'SODIMAS_QI': 'SODIMAS QI',
    'THYSSEN': 'THYSSEN TCM',
    'FT9x0': 'THYSSEN FT9X',
    'ШУЛК17': 'ШУЛК 17',
    'ШУЛК32': 'ШУЛК 32'
}


def strip_text_in_list(lst: t.List, pattern='- \n') -> t.List[str]:
    new_lst = []
    for elem in lst:
        new_lst.append(elem.strip(pattern))
    return new_lst


def strip_prefix(string: str, prefix='- \n') -> str:
    return string.lstrip(prefix)


def get_first_word(line: str) -> str:
    return line[:line.find(" ")]


def is_block_end(line: str) -> bool:
    return line == "" or line.startswith("===")


def extract_common_changelog(lst: t.List[str], k: int) -> common_log:
    name = CHANGELOG_TYPES[get_first_word(lst[k])]
    _, version, _, date = lst[k + 1].split()
    version = dotted_str_to_int(version)
    log_list = []
    i = k + 2
    while not is_block_end(lst[i]):
        log_list.append(strip_prefix(lst[i]))
        i += 1

    return common_log(name, version, date, log_list)


def extract_spec_changelog(lst: t.List[str], k: int) -> spec_log:
    name = lst[k].strip("- :")
    if name in REPLACERS:
        name = REPLACERS[name]
    log_list = []
    i = k + 1
    while not is_block_end(lst[i]):
        log_list.append(strip_prefix(lst[i]))
        i += 1

    return spec_log(name, log_list)


def find_start_of_common_part(lst: list):
    for i in range(len(lst)):
        if lst[i].find("Общая часть") != -1:
            yield i


def find_start_of_special_part(lst: t.List[str]):
    pattern = "^- (.+):"
    for i in range(len(lst)):
        if lst[i].startswith('- ') and lst[i].endswith(':'):
            yield i


def print_spec(spec: spec_log):
    print(spec.name)
    for change in spec.changelog:
        print(change)
    print('_' * 30)


def csv_to_list(filename: str) -> t.List[dict]:
    csv.register_dialect('win', delimiter=';')
    example = []
    with open(filename, encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file, dialect='win')
        for row in reader:
            example.append(row)

    return example


def find_row(lst: t.List[dict], version: int, lbtype: str) -> dict:
    formatted_version = IE_NAME_PATTERN.format(int_to_dotted_str(version))
    for row in lst:
        if row['IE_NAME'] == formatted_version and \
                row['IC_GROUP2'] == IC_GROUP2_INDICATORS[lbtype]:
            yield row


def file_to_list(filename: str) -> t.List[str]:
    source = []
    with open(filename, encoding='utf-8') as f:
        for elem in f:
            source.append(elem.rstrip())
    return source


def dotted_str_to_int(string: str) -> int:
    return int(''.join(string.split('.')))


def int_to_dotted_str(n: int) -> str:
    return '.'.join(str(n))


def get_last_names(lst: t.List[dict], last_version: int, lb_type='lb7') -> set:
    last_names = set()
    for row in find_row(lst, last_version, lb_type):
        last_names.add(row['IC_GROUP1'])
    return last_names

# было dd.mm.yy. стало dd.mm.20yy

def fix_date(date: str) -> str:
    d, m, y = date.rstrip('.').split('.')
    y = '20' + y
    return '.'.join([d, m, y])


def list_to_html(lst):
    html = "<ul>"
    for elem in lst:
        html += "<li>{}</li>".format(elem)
    html += "</ul>"
    return html



def main():
    try:
        source = file_to_list('changes.txt')
    except Exception:
        exit("Для работы необходим файл с изменениями changes.txt!")

    common_logs = {}
    for i in find_start_of_common_part(source):
        log = extract_common_changelog(source, i)
        common_logs[log.name] = log

    # for log in common_logs:
    #     print(f"Пред. версию для {log}"
    #           f" ищем по шаблону {IE_NAME_PATTERN.format(int_to_dotted_str(common_logs[log].version - 1))}")

    spec_logs = {}
    for i in find_start_of_special_part(source):
        log = extract_spec_changelog(source, i)
        spec_logs[log.name] = log

    try:
        example = csv_to_list('export.csv')
    except Exception:
        exit("Для работы необходим файл-выгрузка export.csv!")

    spec_names = spec_logs.keys()

    last_lb7_version = common_logs['lb7'].version - 1
    last_names = get_last_names(example, last_lb7_version)

    not_in = spec_names - last_names
    if not_in:
        print("ВАЖНО! Есть в списке изменений, но нет в выгрузке с сайта: ")
        print(*not_in, sep='\n')

    res = []
    res_row = {}
    for lb_type in common_logs:
        new_v = common_logs[lb_type].version
        prev_v = new_v - 1
        for row in find_row(example, prev_v, lb_type):
            res_row['IE_XML_ID'] = row['IE_XML_ID'].replace(str(prev_v), str(new_v))
            res_row['IE_NAME'] = IE_NAME_PATTERN.format(int_to_dotted_str(new_v))

            changelog = common_logs[lb_type].changelog.copy()
            if row['IC_GROUP1'] in spec_logs:
                changelog += spec_logs[row['IC_GROUP1']].changelog
            res_row['IE_PREVIEW_TEXT'] = list_to_html(changelog)

            res_row['IE_SORT'] = int(row['IE_SORT']) + 10
            res_row['IP_PROP12'] = fix_date(common_logs[lb_type].date)
            res_row['IP_PROP23'] = row['IP_PROP23'].replace(str(prev_v), str(new_v))
            res_row['IC_GROUP0'] = row['IC_GROUP0']
            res_row['IC_GROUP1'] = row['IC_GROUP1']
            res_row['IC_GROUP2'] = row['IC_GROUP2']

            res.append(res_row.copy())

    with open('res.csv', 'w', newline='') as csvfile:
        field_names = res[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=field_names, dialect='win')

        writer.writeheader()
        for row in res:
            writer.writerow(row)
        print(f"Ок, записано строк: {len(res)}. Нажмите любую клавишу для завершения...")
        input()


if __name__ == '__main__':
    main()
