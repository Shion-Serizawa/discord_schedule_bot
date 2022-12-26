# from ast import If
import datetime, re

# from urllib import response
import googleapiclient.discovery
import google.auth

import pymysql.cursors

import schedule
import time


# ①Google APIの準備をする
SCOPES = ["https://www.googleapis.com/auth/calendar"]
calendar_id = "@gmail.com"
# Googleの認証情報をファイルから読み込む
gapi_creds = google.auth.load_credentials_from_file(
    "./calendar-discord-????????.json", SCOPES
)[0]
# APIと対話するためのResourceオブジェクトを構築する
service = googleapiclient.discovery.build("calendar", "v3", credentials=gapi_creds)


def eventAcquisition():
    # ②Googleカレンダーからイベントを取得する
    # 現在時刻を世界協定時刻（UTC）のISOフォーマットで取得する
    dt_now = datetime.datetime.now()
    dt_today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    dt_yesterday = dt_today - datetime.timedelta(days=1)
    dt_tomorrow = dt_today + oneday

    if dt_now.hour >= 20 | (dt_now.hour < 2):
        # print("koko")
        dt = datetime.datetime(
            dt_tomorrow.year, dt_tomorrow.month, dt_tomorrow.day, 16, 59, 0, 0
        )
        dt_kinou = datetime.datetime(
            dt_today.year, dt_today.month, dt_today.day, 17, 0, 0, 1
        )
    else:
        # print("koko2")
        dt = datetime.datetime(dt_today.year, dt_today.month, dt_today.day, 17, 0, 0, 1)
        dt_kinou = datetime.datetime(
            dt_yesterday.year, dt_yesterday.month, dt_yesterday.day, 17, 0, 0, 1
        )
    now = dt.isoformat() + "Z"
    yesterday = dt_kinou.isoformat() + "Z"

    # print(dt_now)
    # print(dt_today)
    # print(dt_yesterday)

    # 直近15件のイベントを取得する
    event_list = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=yesterday,
            timeMax=now,
            maxResults=15,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return event_list


def dataProcessing(event_list):

    # ③イベントの開始時刻、終了時刻、概要を取得する
    events = event_list.get("items", [])
    formatted_events = [
        (
            event["start"].get(
                "dateTime", event["start"].get("date")
            ),  # start time or day
            event["end"].get("dateTime", event["end"].get("date")),  # end time or day
            event["summary"],
        )
        for event in events
    ]

    # ④出力テキストを生成する
    responsekun = [["1999-06-13", "1999-06-14", "kari"]]

    # データの正規化をする (ただしAlldayは取り除く)
    for event in formatted_events:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", event[0]):
            start_date = "{0:%Y-%m-%d}".format(
                datetime.datetime.strptime(event[1], "%Y-%m-%d")
            )

        # For all day events（今回は使用しない）
        else:
            kari1 = event[0].replace("T", " ")
            kari1 = kari1.replace("+09:00", "")
            kari2 = event[1].replace("T", " ")
            kari2 = kari2.replace("+09:00", "")
            responsekun += [[kari1, kari2, event[2]]]

    # 仮部分を削除
    responsekun.pop(0)
    return responsekun


def dbSend(responsekun):
    # Connect to the database
    connection = pymysql.connect(
        host="localhost",
        user="bot",
        password="Dis_bot475",
        db="Schedule_bot",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `Schedule_store` (`start`, `end`, `title`) VALUES (%s, %s, %s)"
            cursor.executemany(sql, responsekun)

        # connection is not autocommit by default. So you must commit to save
        # your changes.
        connection.commit()

    finally:
        connection.close()


def everydayJob():
    eventlist = eventAcquisition()
    responsekun = dataProcessing(eventlist)
    dbSend(responsekun)
    print(responsekun)


# 1回実行用
# print("動いてる？")
# everydayJob()


schedule.every().day.at("05:00").do(everydayJob)


while True:
    schedule.run_pending()
    time.sleep(1)
