FROM python:3.10-slim

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをすべてコピー
COPY . .

# 必要なPythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# ボットを実行
CMD ["python", "src/bot.py"]

# docker build -t takeshitake .
# docker run -it takeshitake