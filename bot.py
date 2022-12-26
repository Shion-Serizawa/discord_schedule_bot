# インストールした discord.py を読み込む
# from os import sync
import discord
from discord.ext import tasks

# pymysqlを読み込む
import pymysql.cursors
import datetime

import time
import schedule
import random
import re

# 自分のBotのアクセストークン
f = open("token.txt", "r")
TOKEN = f.read()
f.close()

# 接続に必要なオブジェクトを生成
client = discord.Client()


def sqlConnectionInit():
    f = open("dbpass.txt", "r")
    dbPassword = f.read()
    f.close()
    return pymysql.connect(
        host="localhost",
        user="bot",
        password=dbPassword,
        db="Schedule_bot",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


# DBからの予定を返す
def dataProcessing():
    connection = sqlConnectionInit()
    try:
        with connection.cursor() as cursor:
            dt_now = datetime.datetime.now()
            sql = "SELECT `key_id`, `start`, `end`, `title` FROM `Schedule_store` WHERE start >= '"
            sql += str(dt_now.year)
            sql += "-"
            sql += str(dt_now.month)
            sql += "-"
            sql += str(dt_now.day)
            sql += " 05:00:00';"

            cursor.execute(sql)

            result = cursor.fetchall()
    finally:
        connection.close()

    # print(result)

    # bot送信用のテキスト生成
    mess = ""
    if result != ():
        mess = result[0]["start"].strftime("%Y/%m/%d") + "\n"
        for sche in result:
            mess += (
                sche["start"].strftime("%H:%M")
                + " ~ "
                + (sche["end"].strftime("%H:%M"))
                + " | "
                + sche["title"]
                + "\n"
            )
    else:
        mess = "本日の予定を決めていないゾ！"
        print("予定なし")
    # print(mess)
    print("mess返り値")
    return mess


# DBより名言取得
def wiseSayingGet():
    connection = sqlConnectionInit()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(`id`) FROM `meigen` WHERE contents != '';"

            cursor.execute(sql)
            result = cursor.fetchall()

            random_num = random.randint(1, int(result[0]["COUNT(`id`)"]))
            sql = "SELECT contents FROM `meigen` WHERE id = "
            sql += str(random_num)
            sql += ";"

            cursor.execute(sql)
            result2 = cursor.fetchall()

            print(result2)
    finally:
        connection.close()
    return result2[0]["contents"] + "\n↓"


# （未完成）スケジュール実行完了をDB反映
def accomplishWriting(event_num):
    return_Bool = False
    connection = sqlConnectionInit()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(`key_id`) FROM `Schedule_store` WHERE key_id = "
            sql += str(event_num)

            cursor.execute(sql)
            result = cursor.fetchall()
            print(result)

            if result[0]["COUNT(`key_id`)"] == 1:
                return_Bool = True
                sql = "UPDATE Schedule_store SET accomplish = '1' WHERE key_id = "
                sql += str(event_num)
                print(sql)
                cursor.execute(sql)
                connection.commit()

    finally:
        connection.close()

    return return_Bool


# select 達成　/ 全予定 = 達成率
# 0~49%頑張ろう。 50~79まあまあ、よく頑張った。　80~100 すげぇ！最強。

# （未完）前日の達成率のメッセージ
def executionResult():
    dt_now = datetime.datetime.utcnow()
    dt_today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    dt_yesterday = dt_today - oneday

    dt_kinou = datetime.datetime(
        dt_yesterday.year, dt_yesterday.month, dt_yesterday.day, 5, 0, 0, 0
    )
    dt_kyou = datetime.datetime(dt_now.year, dt_now.month, dt_now.day, 2, 0, 0, 0)

    connection = sqlConnectionInit()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(`key_id`) FROM `Schedule_store` WHERE  start >= '"
            sql += str(dt_kinou.year)
            sql += "-"
            sql += str(dt_kinou.month)
            sql += "-"
            sql += str(dt_kinou.day)
            sql += " 05:00:00' && end <='"
            sql += str(dt_kyou.year)
            sql += "-"
            sql += str(dt_kyou.month)
            sql += "-"
            sql += str(dt_kyou.day)
            sql += " 02:00:00'"

            cursor.execute(sql)
            result = cursor.fetchall()
            print(result)

            sql = "SELECT COUNT(`key_id`) FROM `Schedule_store` WHERE  start >= '"
            sql += str(dt_kinou.year)
            sql += "-"
            sql += str(dt_kinou.month)
            sql += "-"
            sql += str(dt_kinou.day)
            sql += " 05:00:00' && end <='"
            sql += str(dt_kyou.year)
            sql += "-"
            sql += str(dt_kyou.month)
            sql += "-"
            sql += str(dt_kyou.day)
            sql += " 02:00:00' && accomplish = 1"
            cursor.execute(sql)
            result2 = cursor.fetchall()

    finally:
        connection.close()

    if result[0]["COUNT(`key_id`)"] != 0:
        AchievementRate = (
            result2[0]["COUNT(`key_id`)"] / result[0]["COUNT(`key_id`)"] * 100.0
        )
        returnMessege = "機能の達成率は=>" + str(AchievementRate) + "% です\n↓"
        return returnMessege
    return "resultが0です。"


channel_sent = None

# 稼働　8:00 ~ 23:00
data_start = datetime.time(7, 59, 0)
data_end = datetime.time(23, 1, 0)


@tasks.loop(hours=1)
async def send_message_schedule():
    dt_now = datetime.datetime.now()
    now = dt_now.time()
    mess_sche = dataProcessing()
    mess2 = wiseSayingGet()

    if (now > data_start) & (now < data_end):
        if now < datetime.time(8, 1, 0):
            await channel_sent.send(executionResult())
        await channel_sent.send(mess2)
        await channel_sent.send(mess_sche)


##########################################################
# # test用頻度
# @tasks.loop(seconds=5)
# async def send_message_schedule():
#     dt_now = datetime.datetime.now()
#     # now = dt_now.time()
#     mess_sche = dataProcessing()
#     mess2 = wiseSayingGet()
#     await channel_sent.send(mess2)
#     await channel_sent.send(mess_sche)


##########################################################


@client.event
async def on_ready():
    global channel_sent
    f = open("channelNum.txt", "r")
    channelNum = int(f.read())
    f.close()
    channel_sent = client.get_channel(channelNum)
    send_message_schedule.start()  # 定期実行するメソッドの後ろに.start()をつける


# （未完）DB反映完了 通知
@client.event
async def on_message(message):
    pattern_jump = r"\d+ OK!"
    # メッセージ送信者がBotだった場合は無視する
    if message.author.bot:
        return
    # 予定の実行完了のメッセージが来たら、SQLに反映
    if (re.fullmatch(pattern_jump, message.content)) != None:
        if accomplishWriting(re.sub(r"\D", "", message.content)):
            await message.channel.send("反映したよ！")
        else:
            await message.channel.send("スケジュールがない説")


print("「" + TOKEN + "」")

# schedule.every().day.at("05:10").do(dataProcessing)

# 0分スタート
while True:
    schedule.run_pending()
    dt_now = datetime.datetime.now()
    now = dt_now.time()
    if now.minute == 0:
        print("開始！")
        client.run(TOKEN)
        break
    time.sleep(1)


# # # 1回実行用
# client.run(TOKEN)
#####################################################


while True:
    schedule.run_pending()

    time.sleep(1)
