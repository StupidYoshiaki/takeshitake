import os
import re
import discord
import asyncio
import unicodedata
from pykakasi import kakasi
from dotenv import load_dotenv

# 環境変数からトークンを取得
load_dotenv()
TOKEN = os.getenv("TOKEN")

# クライアントのインスタンス
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)

# 漢字かな変換のためのインスタンス
kakasi = kakasi()
kakasi.setMode("J", "H")
conv = kakasi.getConverter()

# imgフォルダ内のファイル名を取得
filenames = os.listdir("./img")
yomi_to_filename = {}
for filename in filenames:
    filename = filename.replace(".png", "")
    filename = unicodedata.normalize("NFKC", filename)
    yomi = kakasi.do(filename)
    yomi_to_filename[yomi] = filename


# 部分一致でファイル名を取得する関数
def get_filename(query, yomi_to_filename=yomi_to_filename):
    query_yomi = conv.do(query)
    pattern = re.compile(re.escape(query_yomi))
    match = next(
        (file for file in yomi_to_filename.keys() if pattern.search(file)), None
    )
    return match if match else None


# ログイン時の処理
@client.event
async def on_ready():
    print("ログインしました")


# メッセージ受信時の処理
@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content
    result = get_filename(content)
    if result:
        result = yomi_to_filename[result]
        file_path = f"./img/{result}.png"
        await message.channel.send(file=discord.File(file_path))


client.run(TOKEN)
