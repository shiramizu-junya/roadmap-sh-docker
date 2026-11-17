# EC 全体の地図

2026-11-15 に、`docker compose ps` などのコマンドで本物を1つずつ確かめながら描いた地図。
P4-6c 以降の各ステップの「🧭 全体の中のいま」は、この地図を使う。ステップが進んだら書き足す。

## 1枚の地図

```text
Mac の道具       窓口（④）              Docker の中

                                        【道 front】 web・api
ブラウザ      ── :5173 どこからでも ──▶ web ──▶ api（画面から API を呼ぶ）
curl          ── :8000 どこからでも ──▶ api
Zed           ── :5678 Mac だけ     ──▶ api（デバッガ）

                                        【道 back】 api・worker・db・redis
                                        api ──▶ db、redis
DBeaver       ── :3306 Mac だけ     ──▶ db      倉庫 db-data（消えない）
Redis Insight ── :6379 Mac だけ     ──▶ redis   倉庫なし（作り直すと消える）
                                                0番の部屋: カート / 1番の部屋: 受付箱
（窓口なし）                            worker ──▶ redis の 1番を見張る
                                        api・worker ──▶ 倉庫 media（画像。消えない。P4-6d で追加）
```

**読み方**: 左が Mac の道具、まん中が窓口（④）、右が Docker の中の箱（①）。Mac からは窓口を通って箱に入る。箱どうしは、同じ道（②）にいる相手とだけ話せる。api と worker のコードは、Mac の `apps/api/src` を写して使っている（③ bind mount）。

## 4つの部品

### ① 箱（コンテナ）

| 箱 | 係 |
| --- | --- |
| web | 画面（ブラウザに見せる） |
| api | 窓口。アプリのコードがある |
| worker | 受付箱から仕事のメモを取り出して、サムネイルを作る（裏方） |
| db | 消えたら困るデータを、ディスクにずっと取っておく（商品）。正式名称: RDBMS |
| redis | すぐ変わるデータを、メモリで速く出し入れする（カート・仕事のメモ）。正式名称: in-memory data store |

### ② 道（ネットワーク）

| 道 | いる箱 | なぜ分けるか |
| --- | --- | --- |
| front | web・api | 画面と窓口が話す道 |
| back | api・worker・db・redis | 裏側の道。web は入れない |

両方にいるのは api だけ。web から db へ直接行けないようにしている（**ネットワーク分離 / network segmentation**）。

### ③ 倉庫（volume）

| 種類 | 正式名称 | 箱 | 箱を消すと |
| --- | --- | --- | --- |
| Mac のフォルダを写す | bind mount | api・worker の `src` | Mac にあるので残る |
| 名前付きの倉庫 | named volume | db の `db-data` | 残る |
| 名前付きの倉庫 | named volume | api・worker の `media`（`/app/media`。2つの箱で分け合う。P4-6d で追加） | 残る |
| なし | — | redis | **消える**（2026-11-15 に `cart:test` で確かめた） |

### ④ 窓口（ポート）

| 窓口 | 箱 | 誰が入れるか | 使う道具 |
| --- | --- | --- | --- |
| `0.0.0.0:5173` | web | どこからでも | ブラウザ |
| `0.0.0.0:8000` | api | どこからでも | curl |
| `127.0.0.1:5678` | api | この Mac だけ | Zed のデバッガ |
| `127.0.0.1:3306` | db | この Mac だけ | DBeaver |
| `127.0.0.1:6379` | redis | この Mac だけ | Redis Insight |
| なし | worker | 誰も入れない | — |

worker の `8000/tcp` は、イメージの中のメモ（`EXPOSE`）が見えているだけ。**公開（port publishing）ではない。**

## 🔎 調べ方の地図

分からなくなったら、ここを見る。

| 知りたいこと | 打つもの |
| --- | --- |
| 箱が動いているか | `docker compose ps` |
| 箱が止まった・つながらない理由 | `docker compose logs <サービス名>`（ERROR の行を探す） |
| 箱に何が渡ったか（環境変数・設定） | `docker compose config <サービス名>` |
| どの箱がどの道にいるか | `docker network inspect roadmap-sh-docker_<道の名前>` |
| 名前付きの倉庫の一覧 | `docker volume ls` |
| 箱が使っている倉庫の一覧 | `docker compose config --volumes`（宣言だけで使っていない倉庫は出ない） |
| 箱の中のこの場所が何につながっているか | `docker compose exec <サービス名> sh -c 'mount \| grep /app/'`（`virtiofs` = Mac のフォルダ、`ext4` = 倉庫） |
| どこから入れるか（窓口） | `docker compose ps --format '{{.Service}}  {{.Ports}}'` |
| `compose.yaml` の書き方が正しいか | `docker compose config --quiet`（何も出なければ OK） |

## つまずきメモ

| 起きたこと | 原因 | 直し方 |
| --- | --- | --- |
| `.env` に書いたのに `KeyError` | `env_file:` は**箱を作るときに一度だけ**渡る。古い箱を使い回していた | `docker compose up -d <サービス名>` で作り直す |
| `compose.yaml` が `mapping values are not allowed` | 字下げのずれ（全角スペース・保存時の自動整形） | `.zed/settings.json` で YAML の自動整形を止めた。`watch:` は1行の書き方にした |
