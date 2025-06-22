# HSSAPI-Python  
[![PyPI](https://img.shields.io/badge/-Pypi-000.svg?logo=pypi&style=plastic)](https://pypi.org/project/HSS.py/) <img src="https://img.shields.io/badge/-Python-ffd700.svg?logo=python&style=plastic">
  
## 目的
HSSAPIをPythonで簡単にしようできるようにしたAPIラッパー

# 使用方法
***[HSS API ドキュメント](https://hss-dev-docs.aknet.tech/)***  
***APIラッパーは一部の機能をサポートしています。  API機能を全て活用したい場合や、まだラッパーに実装されていない最新の機能を理容したい場合は、`client._http.get_request`または`client._http.patch_request`を使用することにより処理ができると思われます。***  
## インストール
```
pip install HSS.py
```
### githubから直接インストールする
```
pip install git+https://github.com/HSS-Project/HSS.py.git
```
or 
```
pip install git+git@github.com:HSS-Project/HSS.py.git
```

## 初期設定
***HSS APIのアプリケーション画面でtokenを発行してください。***   
```py
import hss
from hss.timeline import Event, EventTime
from hss import TimelineDayType
import asyncio
import time


client = hss.Client()


async def main():
    token = "HSS API token"
    await client.setup(token=token)

    # Schoolオブジェクトの取得
    school = client.get_school(123)  # school_id
    print(school.classes)  # {2: {1: <Class ...>, 2: <Class ...>, 3: <Class ...>}}

    # Classオブジェクトの取得
    cl = school.classes[2][3]
    print(cl.events)  # <EventTimeline sun=... mon=... ...>

    # 月曜日のイベントを追加する(注意: copyしないと編集が反映されません！)
    monday = cl.events.monday.copy()
    start = int(time.time())
    timedata = EventTime(start=start, end=start+1000, is_end_of_day=False)  # 開始時間や終了時間の設定(秒単位)
    monday.events.append(Event(name="test", place="test", time=timedata))

    await cl.events.edit(TimelineDayType.mon, monday)


async def runner():
    # 処理を終えたあと、正常終了でも異常終了でも、client.closeを行うことを推奨します。
    try:
        await main()
    finally:
        await client.close()

asyncio.run(runner())
```
