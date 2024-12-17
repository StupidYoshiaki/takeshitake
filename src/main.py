import os
import re
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import unicodedata
from pykakasi import kakasi
from dotenv import load_dotenv

from typing import List
from sudachipy import tokenizer
from sudachipy import dictionary
from langchain_community.retrievers import BM25Retriever

import cv2
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from server import server_thread


# 環境変数からトークンを取得
load_dotenv()
TOKEN = os.getenv("TOKEN")

# クライアントのインスタンス
# intents = discord.Intents.default()
# intents.message_content = True
# intents.messages = True
# client = discord.Client(intents=intents)
# tree = app_commands.CommandTree(client)

intents = discord.Intents.all()
client = commands.Bot(intents=intents, command_prefix="/")
tree = client.tree

# intents = discord.Intents.default() 
# client = discord.Client(intents=intents) 
# tree = discord.app_commands.CommandTree(client)

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
filenames = os.listdir("./img/raw")
yomi_to_filename = {}
for filename in filenames:
    filename = filename.replace(".png", "")
    # filename = unicodedata.normalize("NFKC", filename)
    # yomi = kakasi.do(filename)
    yomi = normalize_text(filename)
    yomi_to_filename[yomi] = filename

# 部分一致でファイル名を取得する関数
def get_filename(query_yomi, yomi_to_filename=yomi_to_filename):
    # query_yomi = conv.do(query)
    # query_yomi = normalize_text(query)
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

# 画像連結関数
def hconcat_resize_min(im_list, interpolation=cv2.INTER_CUBIC):
    h_min = min(im.shape[0] for im in im_list)
    im_list_resize = [cv2.resize(im, (int(im.shape[1] * h_min / im.shape[0]), h_min), interpolation=interpolation) for im in im_list]
    return cv2.hconcat(im_list_resize)

# 画像生成関数
def create_slot_image(base_images_path, output_path, number_images_path, num_selection=3):
    # ベース画像をランダムに10枚選択して数字を割り当てる
    base_images = [os.path.join(base_images_path, img) for img in os.listdir(base_images_path)]
    base_images = random.sample(base_images, 8)

    # 数字画像をロード
    number_images = [os.path.join(number_images_path, img) for img in os.listdir(number_images_path)]
    number_mapping = {base_images[i]: Image.open(number_images[i % len(number_images)]) for i in range(len(base_images))}

    # ランダムに3枚の画像を選択（被りあり）
    selected_images = [random.choice(base_images) for _ in range(num_selection)]

    # 数字を画像に貼り付け
    processed_images = []
    for img_path in selected_images:
        base_img = Image.open(img_path).convert("RGBA")
        number_img = number_mapping[img_path].resize((300, 300))  # 数字画像のサイズを調整

        # 左上に数字画像を貼り付け
        base_img.paste(number_img, (10, 10), number_img)
        processed_images.append(base_img)

    # 画像を横に連結
    processed_images_cv = [cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA) for img in processed_images]
    slot_image = hconcat_resize_min(processed_images_cv)
    # slot_image = cv2.resize(slot_image, dsize=None, fx=1.5, fy=1.5)
    
    # 結果を保存
    cv2.imwrite(output_path, slot_image)


# ログイン時の処理
@client.event
async def on_ready():
    try:
        synced = await tree.sync(guild=discord.Object(id=int(os.getenv("GUILD_ID"))))
        print(f"Synced {len(synced)} command(s): {', '.join([cmd.name for cmd in synced])}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print("ログインしました")

# メッセージ受信時の処理
@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    # メッセージの内容
    content = message.content
    
    # ボットがメンションされている場合、BM25で検索する
    if client.user.mentioned_in(message):
        content = content.replace(f"<@{client.user.id}>", "").strip()
        content = normalize_text(content)
        if content:
            content = bm25_retriever.invoke(content)[0].page_content
            result = yomi_to_filename[content]
            file_path = f"./img/raw/{result}.png"
            await message.channel.send(file=discord.File(file_path))
            
    # メンションされていない場合、メッセージから勝手に反応する
    else:
        content = normalize_text(content)
        # 2文字以下の投稿には反応しない
        if len(content) <= 2:
            return
        content = get_filename(content)
        if content:
            result = yomi_to_filename[content]
            file_path = f"./img/raw/{result}.png"
            await message.channel.send(file=discord.File(file_path))

@tree.command(name="slot", description="CR竹下家", guild=discord.Object(id=int(os.getenv("GUILD_ID"))))
async def slot(interaction: discord.Interaction):
    await interaction.response.defer()
    base_images_path = "./img/raw"
    output_path = "./output/slot.png"
    number_images_path = "./img/slot"
    create_slot_image(base_images_path, output_path, number_images_path)
    await interaction.followup.send(file=discord.File(output_path))

server_thread()
client.run(TOKEN)