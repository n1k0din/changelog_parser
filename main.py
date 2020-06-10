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
    name = get_first_word(lst[k])
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


def main():
    source = file_to_list('multi_with_spec.txt')

    common_logs = []
    for i in find_start_of_common_part(source):
        common_logs.append(extract_common_changelog(source, i))

    for log in common_logs:
        print(f"Пред. версию для {log.name}"
              f" ищем по шаблону {IE_NAME_PATTERN.format(int_to_dotted_str(log.version - 1))}")

    for i in find_start_of_special_part(source):
        print_spec(extract_spec_changelog(source, i))

    example = csv_to_list('from_lkds.ru.csv')

    for row in find_row(example, 711, 'lb7'):
        print(row['IE_XML_ID'])
    print(len(list(find_row(example, 711, 'lb7'))))

    # print(*source, sep='\n')


if __name__ == '__main__':
    main()
