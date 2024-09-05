
import os
import csv
import re
import threading
import time
from typing import Optional, Callable

PRICE_DIR = r"C:\Users\raveg\PycharmProjects\pythonProject32"

CURRENT_PRICES = []

IS_CYCLE_STOP = threading.Event()


def filter_string_list(filtered_strings: list[str], good_patterns: list[str], bad_patterns: Optional[list[str]] = None):

    """
    Фильтрация строк.
    """

    result: list[str] = []

    good_string: list[str] = []

    if good_patterns:
        for link in filtered_strings:
            for regex in good_patterns:
                if re.search(regex, link, re.IGNORECASE):
                    good_string.append(link)
    else:
        good_string = filtered_strings.copy()
    if bad_patterns:
        for found_link in good_string:
            if not any([re.search(regex, found_link, re.IGNORECASE) for regex in bad_patterns]):
                result.append(found_link)
        return result
    else:
        return good_string


class CsvParser:

    @staticmethod
    def parse_csv(path, row_handler: Callable = None, without_headers: bool = True):
        parsed_data = []
        with open(path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            if without_headers:
                next(reader)
            for row in reader:
                if row_handler is not None:
                    parsed_data.append(row_handler(row))
                else:
                    parsed_data.append(tuple(row))
        return parsed_data


class PriceReader:

    def __init__(self, dir_path: str):
        self.__dir_path = dir_path

    def __get_prices_names(self) -> list[str]:
        files = os.listdir(self.__dir_path)
        return filter_string_list(files, good_patterns=[r"price"])

    def read_prices(self) -> list:
        return [(CsvParser.parse_csv(path=os.path.join(self.__dir_path, filename), without_headers=False), filename)
                for filename in self.__get_prices_names()]


class ProductSearch:

    NAME_STRINGS = ["название", "продукт", "товар", "наименование"]
    PRICE_STRINGS = ["цена", "розница"]
    WEIGHT_STRINGS = ["фасовка", "масса", "вес"]

    def _get_indexes(self, headers):
        name_index = None
        price_index = None
        weight_index = None
        for index, header in enumerate(headers):
            if header in self.NAME_STRINGS:
                name_index = index
            elif header in self.PRICE_STRINGS:
                price_index = index
            elif header in self.WEIGHT_STRINGS:
                weight_index = index
        if name_index is not None and price_index is not None and weight_index is not None:
            return name_index, price_index, weight_index
        raise IndexError(f"не все индексы распарсились {name_index} {price_index}, {weight_index}")

    def _get_product_in_price(self, price_data, product_name: str, filename: str):
        products = []
        name_index, price_index, weight_index = self._get_indexes(price_data[0])
        for product in price_data[1:]:
            if product_name.lower() in product[name_index].lower():
                name = product[name_index]
                price = int(product[price_index])
                weight = int(product[weight_index])
                products.append((name, price, weight, filename, round(price /weight, 0)))
        return products

    def search_product(self, products_data: list, product_name: str):
        result = []
        for price_data, filename in products_data:
            result.extend(self._get_product_in_price(price_data, product_name, filename))
        return sorted(result, key=lambda x: x[4])


class ReportGenerator:

    @staticmethod
    def header_string():
        return ("№" + '  ' *5 + "Наименование" + '  ' *50 + "Цена" + '  ' *2 + "Вес"
                + '  ' *5 + "файл" + '  ' *10 + "цена за кг.\n")

    def generate_report(self, data):
        result = self.header_string()
        counter = 1
        for item in data:
            result += (str(counter) + "  " *(6 - len(str(counter))) + item[0] + "  " *(63 - len(item[0]))
                       + str(item[1]) + "  " *(6 - len(str(item[1]))) + str(item[2])
                       + "  " *(8 - len(str(item[2]))) + item[3] + "  " *(14 - len(item[3])) + str(item[4]) + "\n")
            counter += 1
        return result


class PriceMachine:

    def __init__(self):
        self.data = []
        self.result = ''
        self.name_length = 0
        self.__product_search = ProductSearch()
        self.__console_report_generator = ReportGenerator()

    @staticmethod
    def _reading_cycle(reader):
        """
        Метод поллинга прайслистов.
        """
        global CURRENT_PRICES
        while not IS_CYCLE_STOP.is_set():
            CURRENT_PRICES = reader.read_prices()
            time.sleep(1)

    def load_prices(self, file_path):
        '''
            Сканирует указанный каталог. Ищет файлы со словом price в названии.
            В файле ищет столбцы с названием товара, ценой и весом.
            Допустимые названия для столбца с товаром:
                товар
                название
                наименование
                продукт

            Допустимые названия для столбца с ценой:
                розница
                цена

            Допустимые названия для столбца с весом (в кг.)
                вес
                масса
                фасовка
        '''
        reader = PriceReader(dir_path=file_path)
        polling_thread = threading.Thread(target=self._reading_cycle, args=[reader], daemon=True)
        polling_thread.start()

    @staticmethod
    def export_to_html(data, fname='output.html'):

        headers = ('ID', 'Name', 'Value1', 'Comment', 'Value2')

        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Data Table</title>
            <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid black; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h2>Data Table</h2>
            <table>
                <tr>
        """
        for header in headers:
            html_content += f"<th>{header}</th>"
        html_content += "</tr>"
        for row in data:
            html_content += "<tr>"
            for item in row:
                html_content += f"<td>{item}</td>"
            html_content += "</tr>"

        html_content += """
            </table>
        </body>
        </html>
        """
        with open(os.path.join(PRICE_DIR, fname), "w", encoding="utf-8") as file:
            file.write(html_content)

    def find_text(self, text):
        return self.__product_search.search_product(CURRENT_PRICES, text)

    def generate_console_report(self, data):
        return self.__console_report_generator.generate_report(data=data)


pm = PriceMachine()
pm.load_prices(file_path=PRICE_DIR)
command = ""
parsed_data = []
while command != "exit":
    try:
        command = input("Найти продукт: ")
    except (UnicodeDecodeError, KeyboardInterrupt):
        pass
    if command == "exit":
        IS_CYCLE_STOP.set()
        break
    parsed_data = pm.find_text(command)
    report = pm.generate_console_report(data=parsed_data)
    print(report)

print('the end')
pm.export_to_html(parsed_data)
