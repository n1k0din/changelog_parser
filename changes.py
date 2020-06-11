import typing as t
import csv
from collections import namedtuple

common_log = namedtuple('common_log', ['name', 'version', 'date', 'changelog'])
spec_log = namedtuple('spec_log', ['name', 'changelog'])

IE_NAME_PATTERN = "Версия {}."

# в выгрузке и описании ЛБ идентифицируют по-разному
# в программе используются сл. идентификаторы: lb6, lb6pro, lb7

# транслятор из программы в выгрузку
IC_GROUP2_INDICATORS = {
    'lb6': 'ЛБ 6 CM3',
    'lb6pro': 'ЛБ 6.1 Pro CM3',
    'lb7': 'ЛБ 7.2'
}

# транслятор из описания в программу
CHANGELOG_TYPES = {
    'ЛБv6': 'lb6',
    'ЛБv6Pro': 'lb6pro',
    'ЛБv7': 'lb7'
}

# транслятор 'у О.В.' -> 'на сайте'
# можно и нужно пополнять
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


# избавляется от дефиса в начале строки
def strip_prefix(string: str, prefix='- \n') -> str:
    return string.lstrip(prefix)


# возвращает текст до первого пробела
def get_first_word(line: str) -> str:
    return line[:line.find(" ")]


# строка считается концом блока, если она пустая или начинается с ===
def is_block_end(line: str) -> bool:
    return line == "" or line.startswith("===")


# генерирует индекс начала описания общей части
# содержит "Общая часть"
def find_start_of_common_part(lst: list):
    for i in range(len(lst)):
        if lst[i].find("Общая часть") != -1:
            yield i


# генерирует индекс начала описания частостей
# на дефис-пробел начинается, на : заканчивается
def find_start_of_special_part(lst: t.List[str]):
    for i in range(len(lst)):
        if lst[i].startswith('- ') and lst[i].endswith(':'):
            yield i


# формирует описание общей части из списка lst, начиная с индекса k
# пример:
# ЛБv6Pro Общая часть
# Версия 6.3.7 от 07.06.20.
# - Добавлено формирование IFD: сигнатуры
# ...
# - Разрешена отправка признака движения в основном пакете состояния
def extract_common_changelog(lst: t.List[str], k: int) -> common_log:
    name = CHANGELOG_TYPES[get_first_word(lst[k])]  # из первой строки выдираем тип лб
    _, version, _, date = lst[k + 1].split()  # из второй версию и дату
    version = dotted_str_to_int(version)
    log_list = []
    i = k + 2  # и начиная с третьей собираем список
    while not is_block_end(lst[i]):
        log_list.append(strip_prefix(lst[i]))
        i += 1

    return common_log(name, version, date, log_list)


# формирует описание частностей из списка lst, начиная с индекса k
# пример:
# - THYSSEN_GEC:
#   - При остановке эскалатора - формируется признак "Аварийная блокировка"
#   - Для фиксации "Аварийной блокировки" по остановке эскалатора установить триггерность яч119=1
#   - Поддержана спецификация Class4:Type10 - эскалатор
def extract_spec_changelog(lst: t.List[str], k: int) -> spec_log:
    name = lst[k].strip("- :")  # из первой выдираем имя
    if name in REPLACERS:
        name = REPLACERS[name]
    log_list = []
    i = k + 1  # начиная со второй собираем список
    while not is_block_end(lst[i]):
        log_list.append(strip_prefix(lst[i]))
        i += 1

    return spec_log(name, log_list)


# читает csv в словарь, кодировка utf-8, диалект с разделителем ;
def csv_to_list(filename: str) -> t.List[dict]:
    csv.register_dialect('win', delimiter=';')
    example = []
    with open(filename, encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file, dialect='win')
        for row in reader:
            example.append(row)

    return example


# текстовый файл в список с обрезкой справа
def file_to_list(filename: str) -> t.List[str]:
    source = []
    with open(filename, encoding='utf-8') as f:
        for elem in f:
            source.append(elem.rstrip())
    return source


# строка 1.2.3 -> число 123
def dotted_str_to_int(string: str) -> int:
    return int(''.join(string.split('.')))


# число 789 -> строка 7.8.9
def int_to_dotted_str(n: int) -> str:
    return '.'.join(str(n))


# выдает по списку-таблице записи с нужной версией и нужным типом лб
def find_row(lst: t.List[dict], version: int, lbtype: str) -> dict:
    formatted_version = IE_NAME_PATTERN.format(int_to_dotted_str(version))
    for row in lst:
        if row['IE_NAME'] == formatted_version and \
                row['IC_GROUP2'] == IC_GROUP2_INDICATORS[lbtype]:
            yield row


# собирает множество названий исполнений лб определенной версии
# для чего: найдем все исполнения ЛБ7 для которых была посл. версия прошивки и будем считать это образцовым списком
# ДОПУЩЕНИЕ: список имён для семерки, прошки и шестёрки будет одинаковым
def get_last_names(lst: t.List[dict], last_version: int, lb_type='lb7') -> set:
    last_names = set()
    for row in find_row(lst, last_version, lb_type):
        last_names.add(row['IC_GROUP1'])
    return last_names


# было      "dd.mm.yy."
# стало     "dd.mm.20yy"
def fix_date(date: str) -> str:
    d, m, y = date.rstrip('.').split('.')
    assert len(y) == 2
    y = f'20{y}'
    return '.'.join([d, m, y])


# из [row1, row2, ..., rowN] в
# <ul>
# <li>row1</li>
# <li>row2</li>
# ...
# <li>rowN</li>
# </ul>
# только всё в одну строку
def list_to_html(lst):
    html = "<ul>"
    for elem in lst:
        html += "<li>{}</li>".format(elem)
    html += "</ul>"
    return html


# выдергивает из src при помощи extracter для всех найденных finder
def get_logs(src: t.List[str], finder: t.Callable, extractor: t.Callable) -> t.Dict:
    logs = {}
    for i in finder(src):
        log = extractor(src, i)
        logs[log.name] = log
    return logs


#
def get_full_log(lb_type: str, lb_name: str, common_logs: t.Dict[str, common_log],
                 spec_logs: t.Dict[str, spec_log]) -> t.List[str]:
    changelog = common_logs[lb_type].changelog.copy()  # скопируем общую часть
    if lb_name in spec_logs:  # и если есть частность
        changelog += spec_logs[lb_name].changelog  # то и её добавим

    return changelog


def replace_with_next_num(string: str, num: int) -> str:
    """
    Заменяет в исходной строке string все вхождения числа num на num + 1
    """
    return string.replace(str(num), str(num + 1))


# заполнялка одной записи результата
def fill_row(row, lb_type, prev_v, new_v, common_logs, spec_logs):
    return {'IE_XML_ID': replace_with_next_num(row['IE_XML_ID'], prev_v),

            'IE_NAME': IE_NAME_PATTERN.format(int_to_dotted_str(new_v)),

            'IE_PREVIEW_TEXT': list_to_html(get_full_log(lb_type, row['IC_GROUP1'], common_logs, spec_logs)),

            'IE_SORT': int(row['IE_SORT']) + 10,

            'IP_PROP12': fix_date(common_logs[lb_type].date),

            'IP_PROP23': replace_with_next_num(row['IP_PROP23'], prev_v),

            'IC_GROUP0': row['IC_GROUP0'],
            'IC_GROUP1': row['IC_GROUP1'],
            'IC_GROUP2': row['IC_GROUP2']}


# заполнялка результата
# res это измененый example - для новой версии прошивок
def fill_res(common_logs: t.Dict[str, common_log], spec_logs: t.Dict[str, spec_log], example: t.List[dict]):
    res = []
    for lb_type in common_logs:  # что там было в общей части в описании
        new_v = common_logs[lb_type].version  # новая версия, будем её пихать вместо старой
        prev_v = new_v - 1  # старая версия
        for row in find_row(example, prev_v, lb_type):  # ищем в выгрузке строки нужного типа про пред. версию
            res.append(fill_row(row, lb_type, prev_v, new_v, common_logs, spec_logs))

    return res


def write_res(res: t.List[dict], filename='res.csv'):
    with open(filename, 'w', newline='') as csvfile:
        field_names = res[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=field_names, dialect='win')

        writer.writeheader()
        for row in res:
            writer.writerow(row)
        print(f"Ок, записано строк: {len(res)}. Нажмите любую клавишу для завершения...")
        input()


def main():
    try:
        source = file_to_list('changes.txt')  # читаем файл с изменениями в список
    except Exception:
        exit("Для работы необходим файл с изменениями changes.txt!")

    # выдергиваем "общую часть" для лб
    common_logs = get_logs(source, find_start_of_common_part, extract_common_changelog)
    # выдергиваем "частности" для лб
    spec_logs = get_logs(source, find_start_of_special_part, extract_spec_changelog)

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

    res = fill_res(common_logs, spec_logs, example)

    write_res(res)


if __name__ == '__main__':
    main()
