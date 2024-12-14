import os
import re
import discord
import asyncio
import unicodedata
from pykakasi import kakasi
from dotenv import load_dotenv

from typing import List
from sudachipy import tokenizer
from sudachipy import dictionary
from langchain.retrievers import BM25Retriever

from server import server_thread


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

# テキスト正規化関数
def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = kakasi.do(text)
    return text

# imgフォルダ内のファイル名を取得
filenames = os.listdir("./img")
yomi_to_filename = {}
for filename in filenames:
    filename = filename.replace(".png", "")
    # filename = unicodedata.normalize("NFKC", filename)
    # yomi = kakasi.do(filename)
    yomi = normalize_text(filename)
    yomi_to_filename[yomi] = filename

# 部分一致でファイル名を取得する関数
def get_filename(query, yomi_to_filename=yomi_to_filename):
    # query_yomi = conv.do(query)
    query_yomi = normalize_text(query)
    pattern = re.compile(re.escape(query_yomi))
    match = next(
        (file for file in yomi_to_filename.keys() if pattern.search(file)), None
    )
    return match if match else None

# トークン化関数の準備
def preprocess_func(text: str) -> List[str]:
    tokenizer_obj = dictionary.Dictionary(dict="small").create()
    mode = tokenizer.Tokenizer.SplitMode.A
    tokens = tokenizer_obj.tokenize(text ,mode)
    words = [token.surface() for token in tokens]
    words = list(set(words))  # 重複削除
    return words
bm25_retriever = BM25Retriever.from_texts(yomi_to_filename.keys(), preprocess_func=preprocess_func, k=1)


# ログイン時の処理
@client.event
async def on_ready():
    print("ログインしました")

# メッセージ受信時の処理
@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    # メッセージの内容
    content = message.content
    
    # 2文字以下の投稿には反応しない
    if len(content) <= 2:
        return
    
    # ボットがメンションされている場合、BM25で検索する
    if client.user.mentioned_in(message):
        content = content.replace(f"<@{client.user.id}>", "").strip()
        content = normalize_text(content)
        if content:
            content = bm25_retriever.invoke(content)[0].page_content
            result = yomi_to_filename[content]
            file_path = f"./img/{result}.png"
            await message.channel.send(file=discord.File(file_path))
            
    # メンションされていない場合、メッセージから勝手に反応する
    else:
        content = get_filename(content)
        if content:
            result = yomi_to_filename[content]
            file_path = f"./img/{result}.png"
            await message.channel.send(file=discord.File(file_path))

server_thread()
client.run(TOKEN)