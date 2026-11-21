# EC 全体の地図

2026-11-15 に、`docker compose ps` などのコマンドで本物を1つずつ確かめながら描いた地図。
P4-6c 以降の各ステップの「🧭 全体の中のいま」は、この地図を使う。ステップが進んだら書き足す。

🐳 **動く図で見たいとき**: `docs/visual/docker-inside.html` をブラウザで開く（`open docs/visual/docker-inside.html`）。ステップごとに Docker の中を切り替えて見られる。

## 1枚の地図

```text
Mac の道具       窓口（④）              Docker の中

                                        【道 front】 web・api
ブラウザ      ── :5173 どこからでも ──▶ web ──▶ api（画面から API を呼ぶ）
                                        web ──▶ api の /media（画像も中継する。P4-6g で追加）
curl          ── :8000 どこからでも ──▶ api（/media/... で倉庫の画像も返す。P4-6g で追加）
Zed           ── :5678 Mac だけ     ──▶ api（デバッガ）

                                        【道 back】 api・worker・db・redis
                                        api ──▶ db、redis
                                        api ──▶ redis の 1番にメモを入れる（P4-6e で追加）
DBeaver       ── :3306 Mac だけ     ──▶ db      倉庫 db-data（消えない）
Redis Insight ── :6379 Mac だけ     ──▶ redis   倉庫なし（作り直すと消える）
                                                0番の部屋: カート / 1番の部屋: 受付箱
（窓口なし）                            worker ──▶ redis の 1番を見張り、メモが来たら仕事をする
                                        worker ──▶ db（商品を読む・サムネイルの場所を書く。P4-6f で追加）
                                        api・worker ──▶ 倉庫 media（画像。消えない。P4-6d で追加）
                                                        products/ = 元の画像（api が書く）、thumbs/ = サムネイル（worker が書く。P4-6f）
```

**読み方**: 左が Mac の道具、まん中が窓口（④）、右が Docker の中の箱（①）。Mac からは窓口を通って箱に入る。箱どうしは、同じ道（②）にいる相手とだけ話せる。api と worker のコードは、Mac の `apps/api/src` を写して使っている（③ bind mount）。

## 4つの部品

### ① 箱（コンテナ）

| 箱 | 係 |
| --- | --- |
| web | 画面（ブラウザに見せる）。`/api` と `/media` を api へ中継する（Vite の proxy） |
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
| 名前付きの倉庫 | named volume | api・worker の `media`（`/app/media`。2つの箱で分け合う。P4-6d で追加。`products/` に元の画像、`thumbs/` にサムネイル） | 残る |
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
| worker が知っている仕事（task）の一覧 | `docker compose exec worker .venv/bin/celery --workdir src -A config inspect registered`（起動ログの `[tasks]` の下でも分かる） |
| worker にメモが届いて、仕事が終わったか | `docker compose logs -f --since 1m worker` の `received`（受け取った）と `succeeded`（終わった） |
| 受付箱にたまっているメモの枚数 | `docker compose exec redis redis-cli -n 1 LLEN celery`（worker が動いていると、すぐ 0 に戻る） |
| worker から db に届くか | `docker compose exec worker .venv/bin/python src/manage.py shell -c "..."`（worker の中で Django の1行を試す） |
| db の商品の行に何が書かれたか | `docker compose exec db mysql -uec -pec-pass ec -e "SELECT id, image, thumbnail FROM catalog_product"` |
| 設計図（マイグレーション）が db に当たったか | `docker compose exec api .venv/bin/python src/manage.py showmigrations catalog`（`[X]` なら当たっている） |
| ブラウザが画像を取りに行く先で、画像が返るか | `curl -s -I localhost:5173/media/thumbs/1.jpg`（`Content-Type: image/jpeg` なら OK。`text/html` なら web が中継していない） |
| api の箱が画像を返せるか | `curl -s -I localhost:8000/media/thumbs/1.jpg`（`404` なら `urls.py` の `static()` か `DEBUG` を見る） |
| Django がその URL をどう扱ったか | `docker compose logs --since 1m api \| grep media`（行の最後の数字 `200` / `404`） |
| 箱の中のファイルを Mac で見る | `docker compose cp api:/app/media/thumbs/1.jpg /tmp/thumb.jpg` → `open /tmp/thumb.jpg` |

## つまずきメモ

| 起きたこと | 原因 | 直し方 |
| --- | --- | --- |
| `.env` に書いたのに `KeyError` | `env_file:` は**箱を作るときに一度だけ**渡る。古い箱を使い回していた | `docker compose up -d <サービス名>` で作り直す |
| `compose.yaml` が `mapping values are not allowed` | 字下げのずれ（全角スペース・保存時の自動整形） | `.zed/settings.json` で YAML の自動整形を止めた。`watch:` は1行の書き方にした |
| `Unknown column 'catalog_product.thumbnail'` で 500 | `models.py` に列を足して保存した（api は読み直した）が、`migrate` していない。db にはまだ列が無い | `makemigrations` → `migrate` を api から打つ（worker の分も1回で済む） |
| api は `saved` なのに、サムネイルができない | worker が仕事に失敗している。api はメモを入れたらすぐ返事をするので、失敗を知らない | `docker compose logs worker` の `ERROR` と `Traceback` を見る（例: worker に倉庫 `media` が無いと `FileNotFoundError`） |
| `.py` を変えたのに worker が古いまま／`Received unregistered task` | worker（Celery）は、`runserver` と違ってコードを自分で読み直さない。名簿に無い仕事のメモは捨てる | `docker compose restart worker`。`config/celery.py` に `app.autodiscover_tasks()` があるかも見る |
| 画像の `<img>` が出ない。`localhost:5173/media/...` が `200` なのに `text/html` | web の箱の Vite が `/media` を中継していない。自分の画面の HTML を返している | `vite.config.js` の `proxy` に `"/media": "http://api:8000"` を足し、`docker compose up -d --build web` |
| `vite.config.js` を変えたのに効かない（restart してもだめ） | `vite.config.js` はイメージを作るときに `COPY` で写し取ったもの。`watch` も `src/` しか同期しない | `docker compose up -d --build web` でイメージから作り直す |
| `<img src="http://api:8000/...">` の画像が出ない | React はブラウザ（Mac）で動く。Mac は Docker の道にいないので `api` を知らない（`Could not resolve host: api`） | 住所は `/media/...` にして、web に中継させる |
