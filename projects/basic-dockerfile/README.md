# basic-dockerfile

[roadmap.sh](https://roadmap.sh/) の Docker プロジェクト課題「Basic Dockerfile」の解答です。

- **プロジェクトURL: https://roadmap.sh/projects/basic-dockerfile**
- レベル: beginner

Alpine Linux をベースに、実行すると `Hello, Captain!` と表示して終了するイメージを作ります。

## 特徴

- ベースイメージは `alpine:latest`（13.5MB）
- 表示は `echo` の1命令だけで行う
- **名前を差し替えられる**（任意課題）。`docker run` のうしろに書いた名前で挨拶する

## 必要環境

- Docker（Docker Desktop 4.81.0 / Engine 29.6.1 で動作確認）

## 使い方

このディレクトリで実行します。

```bash
docker build -t pj1:hello .
docker run --rm pj1:hello
```

### 実行例

```
$ docker run --rm pj1:hello
Hello, Captain!

$ docker run --rm pj1:hello "Junya!"
Hello, Junya!
```

## 構成

```
basic-dockerfile/
├── Dockerfile
└── README.md
```

### Dockerfile の考え方

```dockerfile
FROM alpine:latest

# 変えない部分
ENTRYPOINT [ "echo", "Hello," ]
# 変わる部分
CMD [ "Captain!" ]
```

| 命令 | 役割 |
| --- | --- |
| `ENTRYPOINT` | **変えない部分**（`echo Hello,`）。`docker run` のうしろに何を書いても残る |
| `CMD` | **既定の引数**（`Captain!`）。`docker run` のうしろに書くと、ここだけが差し替わる |

どちらも配列（exec 形式）で書いているため、コンテナの中で `echo` が PID 1 になります。
`echo` は表示したら終わるので、コンテナもすぐ終了します（終了コード 0）。

追加した2行はどちらもファイルを増やさず、指示を書き込むだけです。`docker history` で見ると層の大きさは 0B です。

## 詰まった記録

| 症状 | 切り分けに使ったコマンド | 原因 |
| --- | --- | --- |
| `exec: ".": executable file not found in $PATH` | エラーメッセージを読む | `docker run` のうしろに `.` を付けていた。`.` は `docker build` 用で、`docker run` に書くと `CMD` を置き換えて「実行するプログラム」扱いになる |
| `exec: "Hello, Captain!": executable file not found in $PATH`（終了コード 127） | `docker image inspect --format '{{.Config.Cmd}}'` | `CMD ["Hello, Captain!"]` と書いていた。配列の1つめは**実行するプログラムの名前**なので、表示するプログラム（`echo`）が要る。Alpine には Python は無いが `echo` はある |
| 出力が `Hello Captain!`（カンマが無い） | 出力を要件の文言と見比べる | `ENTRYPOINT` の `"Hello"` にカンマが無かった |

## 学習の記録

このリポジトリの教材 [`docs/p2-dockerfile.md`](../../docs/p2-dockerfile.md) の「MP: PJ1」として取り組みました。
