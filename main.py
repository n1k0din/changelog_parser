import typing as t
import re
from collections import namedtuple

common_log = namedtuple('common_log', ['name', 'version', 'date', 'changelog'])
spec_log = namedtuple('spec_log', ['name', 'changelog'])



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


def main():
    source = []
    with open('multi_with_spec.txt', encoding='utf-8') as f:
        for elem in f:
            source.append(elem.rstrip())


    for i in find_start_of_common_part(source):
        print(extract_common_changelog(source, i))

    for i in find_start_of_special_part(source):
        print_spec(extract_spec_changelog(source, i))



    # print(*source, sep='\n')
if __name__ == '__main__':
    main()