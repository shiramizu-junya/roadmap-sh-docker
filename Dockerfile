# P2-1: いちばん短い Dockerfile
# ベースイメージを選んで、起動コマンドを決めるだけ

FROM python:3.12-slim

CMD ["python", "-c", "print('コンテナの中から、こんにちは')"]
