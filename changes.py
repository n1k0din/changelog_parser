import typing as t
import csv
from collections import namedtuple

CommonLog = namedtuple('CommonLog', ['name', 'version', 'date', 'changelog'])
SpecLog = namedtuple('SpecLog', ['name', 'changelog'])

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
def extract_common_changelog(lst: t.List[str], k: int) -> CommonLog:
    name = CHANGELOG_TYPES[get_first_word(lst[k])]  # из первой строки выдираем тип лб
    _, version, _, date = lst[k + 1].split()  # из второй версию и дату
    version = dotted_str_to_int(version)
    log_list = []
    i = k + 2  # и начиная с третьей собираем список
    while not is_block_end(lst[i]):
        log_list.append(strip_prefix(lst[i]))
        i += 1

    return CommonLog(name, version, date, log_list)


# формирует описание частностей из списка lst, начиная с индекса k
# пример:
# - THYSSEN_GEC:
#   - При остановке эскалатора - формируется признак "Аварийная блокировка"
#   - Для фиксации "Аварийной блокировки" по остановке эскалатора установить триггерность яч119=1
#   - Поддержана спецификация Class4:Type10 - эскалатор
def extract_spec_changelog(lst: t.List[str], k: int) -> SpecLog:
    name = lst[k].strip("- :")  # из первой выдираем имя
    if name in REPLACERS:
        name = REPLACERS[name]
    log_list = []
    i = k + 1  # начиная со второй собираем список
    while not is_block_end(lst[i]):
        log_list.append(strip_prefix(lst[i]))
        i += 1

    return SpecLog(name, log_list)


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
# ДОПУЩЕНИЕ: список имён будет одинаковым для всех типов лб
def get_last_names(lst: t.List[dict], last_version: int, lb_type='lb7') -> set:
    last_names = set()
    for row in find_row(lst, last_version, lb_type):
        last_names.add(row['IC_GROUP1'])
    return last_names


def fix_date(date: str) -> str:
    """
    Приводит дату в виде "dd.mm.yy." к "dd.mm.20yy"
    """
    day, month, year = date.rstrip('.').split('.')
    assert len(year) == 2
    year = f'20{year}'
    return f'{day}.{month}.{year}'


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


def get_full_log(type: str, model: str, type_changelist: t.Dict[str, CommonLog],
                 model_changelist: t.Dict[str, SpecLog]) -> t.List[str]:
    """
    Устройство имеет тип type и модель model. Изменяния для типа и модели записаны в type_changelist и model_changelist
    Полный список изменений = изменения для типа + изменения для модели.
    """

    changelog = type_changelist[type].changelog.copy()

    # дополним (если есть чем) описанием модели
    if model in model_changelist:
        changelog.extend(model_changelist[model].changelog)

    return changelog


def replace_with_next_num(string: str, num: int) -> str:
    """
    Заменяет в исходной строке string все вхождения числа num на num + 1
    """
    return string.replace(str(num), str(num + 1))


def format_with_dots(num: int, pattern=IE_NAME_PATTERN) -> str:
    """
    Возвращает число num, разделенное точками и приведенное к формату pattern
    """
    return pattern.format(int_to_dotted_str(num))


def get_next_sort_key(current: int, step=1):
    """
    в месте использования данные сортируются по отдельному ключу по убыванию.
    по какому ключу будет выполнена сортировка далее - неизвестно, поэтому
    при добавлении будем увеличивать значение ключа сортировки на step
    ВНИМАНИЕ: стараемся избегать слишком большого роста ключа, допустимые пределы в месте использования неизвестны!
    """
    return int(current) + step


def fill_row(row, version: int, update_date: str, changelog: t.List[str]):
    """
    Возвращает запись на основе row: выбирает только нужные поля и обновляет ид, имя, описание и всё такое.
    """

    return {
            # новый ID это старый, в котором номер версии заменён на следующий по порядку
            'IE_XML_ID': replace_with_next_num(row['IE_XML_ID'], version),

            'IE_NAME': format_with_dots(version + 1),

            # преобразуем list изменений в html-список
            'IE_PREVIEW_TEXT': list_to_html(changelog),

            'IE_SORT': get_next_sort_key(row['IE_SORT'], step=2),

            # поле даты обновления
            'IP_PROP12': update_date,

            # IP_PROP23 это путь к файлу
            # новый путь это старый путь, в котором номер версии заменён на следующий по порядку
            'IP_PROP23': replace_with_next_num(row['IP_PROP23'], version),

            # это "путь" в логической структуре, его не меняем
            # пример: Лифтовые блоки -> ЛБ 6 -> OTIS
            'IC_GROUP0': row['IC_GROUP0'],
            'IC_GROUP1': row['IC_GROUP1'],
            'IC_GROUP2': row['IC_GROUP2']}


# заполнялка результата
# res это измененый example - для новой версии прошивок
def fill_res(common_logs: t.Dict[str, CommonLog], spec_logs: t.Dict[str, SpecLog], example: t.List[dict]):
    res = []
    for lb_type in common_logs:  # что там было в общей части в описании
        new_v = common_logs[lb_type].version  # новая версия, будем её пихать вместо старой
        prev_v = new_v - 1  # старая версия
        for row in find_row(example, prev_v, lb_type):  # ищем в выгрузке строки нужного типа про пред. версию

            # поле даты обновления: приведём к виду dd.mm.yyyy
            date = fix_date(common_logs[lb_type].date)

            # собираем полный лог из общего и частного
            # в столбце IC_GROUP1 записана модель устройства: otis, thyssen, и т.д.
            full_log = get_full_log(type=lb_type, model=row['IC_GROUP1'],
                                    type_changelist=common_logs, model_changelist=spec_logs)

            res.append(fill_row(row, prev_v, date, full_log))

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
