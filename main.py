from typing import List


def strip_text_in_list(lst: List, pattern='- \n'):
    new_lst = []
    for elem in lst:
        new_lst.append(elem.strip(pattern))
    return new_lst


def main():
    source = []
    with open('to_html_list.txt', encoding='utf-8') as f:
        for elem in f:
            source.append(elem)

    text = strip_text_in_list(source)

    for x in text:
        print(x)

if __name__ == '__main__':
    main()