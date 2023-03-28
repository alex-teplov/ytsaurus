# -*- coding: utf-8 -*-

import getpass
import os

import yt.wrapper


# Reducer это обычная функция-генератор, она принимает на вход:
#   - текущий ключ
#   - итератор по всем записям входной таблицы с данным ключом
# на выходе она должна вернуть (как и функция mapper) все записи, которые мы хотим записать в выходные таблицы.
def count_names_reducer(key, input_row_iterator):

    # В данном случае ключ у нас состоит лишь из одной колонки "name", но вообще он может состоять из нескольких колонок.
    # Читать конкретные поля ключа можно как из dict'а.
    name = key["name"]

    count = 0
    longest_login = ""
    for input_row in input_row_iterator:
        count += 1
        if len(input_row["login"]) > len(longest_login):
            longest_login = input_row["login"]

    yield {"name": name, "count": count, "longest_login": longest_login}


if __name__ == "__main__":
    # You need to set up cluster address in YT_PROXY environment variable.
    cluster = os.getenv("YT_PROXY")
    if cluster is None or cluster == "":
        raise RuntimeError("Environment variable YT_PROXY is empty")
    client = yt.wrapper.YtClient(cluster)

    sorted_tmp_table = "//tmp/{}-pytutorial-tmp".format(getpass.getuser())
    output_table = "//tmp/{}-pytutorial-name-stat".format(getpass.getuser())

    client.run_sort(
        source_table="//home/dev/tutorial/staff_unsorted", destination_table=sorted_tmp_table, sort_by=["name"]
    )

    client.run_reduce(
        count_names_reducer, source_table=sorted_tmp_table, destination_table=output_table, reduce_by=["name"]
    )

    ui_url = os.getenv("YT_UI_URL")
    print(f"Output table: {ui_url}/#page=navigation&offsetMode=row&path={output_table}")