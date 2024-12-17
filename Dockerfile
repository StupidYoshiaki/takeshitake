FROM python:3.11-slim
WORKDIR /bot

# ロケール設定と必要なライブラリインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tzdata && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 環境変数設定
ENV LANG=ja_JP.UTF-8 \
    LANGUAGE=ja_JP:ja \
    LC_ALL=ja_JP.UTF-8 \
    TZ=Asia/Tokyo \
    TERM=xterm

# Python依存パッケージのインストール
COPY requirements.txt /bot/
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . /bot

# ポート開放 (uvicorn用)
EXPOSE 8080

# アプリケーションの実行
CMD ["python", "src/main.py"]

# Dockerビルドと実行例
# docker build -t takeshitake .
# docker run -it takeshitake
