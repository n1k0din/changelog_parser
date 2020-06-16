# changelog_parser
Парсер списка изменений от О.В. в csv для сайта.

## Известные важные допущения:
1. Версия в файле с изменениями больше существующей версии ровно на 1.
2. Идентификатор и путь к файлу содержат версию прошивки в трёхзначном виде.

## Известные проблемы:
 1. Многоуровневый список изменений не обрабатывается
 2. (minor) Некоторые элементы списка изменений попадают под некоторые шаблонные индикаторы.
