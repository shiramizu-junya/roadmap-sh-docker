# P4: Compose で EC を組み上げる

このフェーズの問いは1つです。**「何個もの箱を、どうやって1つの EC として動かすのか」**

全6ステップと、PJ2、フェーズ末パックです。P3 の長い `docker run` を `compose.yaml` にまとめ、画面・カート・サムネイルを足します。

> 検証環境: Docker Desktop / Docker Engine 29.8.0 / Docker Compose v5.5.1 / macOS 26.6.2（Apple シリコン）
> 使うイメージ: `mysql:8.4`（8.4.13）/ `redis:8-alpine`（8.10.3）/ `node:24-alpine`（Node 24.22.2）/ `python:3.13-slim`
> 作業場所: **リポジトリのいちばん上**（`roadmap-sh-docker/`）。P3 の `apps/api/` ではありません。特に断りがなければ、コマンドはすべてここで実行します。
> 使う名前: サービス `db` `api` `web` `redis` `worker` / volume `db-data` `media` / ネットワーク `front` `back`

---

## P4-1: 長いコマンドを compose.yaml にする

**❓ この回の問い**: P3 の答えは「データは volume、つながりはネットワーク、設定は環境変数」だった。でも `docker run` の行がとても長く、毎回打つのは大変だった。
→ **この長いコマンドの束を、どうまとめるのか？**

**作るもの / 確かめること**: `api` と `db` を、`compose.yaml` 1つから起動する
**重要度**: 🔴 毎日使う — 2つ以上のコンテナを動かすなら、ほぼ必ず Compose を使うから
**前ステップとの接続**: P3-4 の `docker run` 2つを、ファイルに書き写す

### 1-0. このステップの初出トークン

**Docker**: `services:` `docker compose up` `docker compose down`
**補助**: `image:` `ports:` `environment:`（`docker run` の指定をそのまま書き写したもの）
**Linux**: YAML
**その他**: なし

### 1-1. 実践

#### 始める前に: P3 の片付け

P3 の最後の片付けをまだしていなければ、ここで行います。`ec-api` が 8000 番を使ったままだと、このあとの起動がぶつかります。

```bash
docker rm -f ec-api ec-db
docker network rm ec-net
```

✅ 検証済み: Docker Engine 29.8.0

#### イメージを作り直す

P3-4 の最後で `makemigrations` を実行し、`apps/api/src/catalog/migrations/0001_initial.py` ができました。P3 の `ec-api:step6` は、その前にビルドしたイメージです。だから、このファイルが入っていません。作り直して、新しいタグを付けます。

```bash
docker build -t ec-api:step7 apps/api
```

最後の `apps/api` は、ビルドコンテキストです（P2-4）。いまはリポジトリのいちばん上にいるので、`.` ではなくフォルダを指定します。

✅ 検証済み: Docker Engine 29.8.0

#### compose.yaml を書く

**ファイル**: `compose.yaml`（リポジトリのいちばん上に新規・全文）

```yaml
services:
  db:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: root-pass
      MYSQL_DATABASE: ec
      MYSQL_USER: ec
      MYSQL_PASSWORD: ec-pass

  api:
    image: ec-api:step7
    ports:
      - "8000:8000"
    environment:
      DB_HOST: db
      DB_NAME: ec
      DB_USER: ec
      DB_PASSWORD: ec-pass
```

> 🐧 **Linux注**: YAML は、字下げで入れ子を表す設定ファイルの書き方です。字下げは**空白**で書きます。タブを使うとエラーになります。

P3 との違いは1つです。`DB_HOST` が `ec-db` ではなく `db` になりました。理由は 1-2 で見ます。

#### 起動する

まず `db` だけを起動し、準備ができるのを待ちます。

```bash
docker compose up -d db
until docker logs roadmap-sh-docker-db-1 2>&1 | grep -q 'port: 3306'; do sleep 1; done; echo ready
```

```text
 Network roadmap-sh-docker_default Created
 Container roadmap-sh-docker-db-1 Created
 Container roadmap-sh-docker-db-1 Started
ready
```

✅ 検証済み: Docker Compose v5.5.1。初回の初期化は約5秒だった。

次に、残りを起動します。

```bash
docker compose up -d
docker compose ps
```

```text
 Container roadmap-sh-docker-db-1 Running
 Container roadmap-sh-docker-api-1 Created
 Container roadmap-sh-docker-api-1 Started
NAME                       IMAGE          COMMAND                   SERVICE   CREATED          STATUS          PORTS
roadmap-sh-docker-api-1    ec-api:step7   "./entrypoint.sh .ve…"   api       4 seconds ago    Up 4 seconds    0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
roadmap-sh-docker-db-1     mysql:8.4      "docker-entrypoint.s…"   db        10 seconds ago   Up 10 seconds   3306/tcp, 33060/tcp
```

✅ 検証済み: Docker Compose v5.5.1

`docker compose ps` は、**この `compose.yaml` のコンテナだけ**を一覧にします。`docker ps` はすべてのコンテナを出すので、ほかの作業のコンテナも混ざります。

DB は空なので、表を作って商品を入れます。コンテナ名は Compose が付けた名前です。

```bash
docker exec roadmap-sh-docker-api-1 .venv/bin/python src/manage.py migrate
docker exec roadmap-sh-docker-api-1 .venv/bin/python src/manage.py loaddata products
curl -s localhost:8000/api/products | grep -o '"id"' | wc -l
```

```text
Operations to perform:
  Apply all migrations: catalog
Running migrations:
  Applying catalog.0001_initial... OK
Installed 3 object(s) from 1 fixture(s)
       3
```

✅ 検証済み: Docker Compose v5.5.1 / MySQL 8.4.13

> 💡補足: リポジトリを別の名前のフォルダに置いた場合、コンテナ名の `roadmap-sh-docker` の部分が、そのフォルダの名前になります。`docker compose ps` の `NAME` 列で確かめてください。

### 1-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `compose.yaml` | Compose ファイル | 動かしたいコンテナの一覧を書いた設計図。Compose はこれを読んで、Docker デーモンに `docker run` 相当の依頼を出す |
| `services:` | サービスの定義 | 1つのサービスが、1種類のコンテナを表す。キーの名前（`db`、`api`）がサービス名になる |
| `docker compose up -d` | 起動 | 足りないネットワーク・コンテナを作り、起動する。すでに同じ設定で動いているものには手を付けない |
| `docker compose down` | 停止と削除 | コンテナと、Compose が作ったネットワークを消す。**volume とイメージは消さない** |
| `image:` `ports:` `environment:` | （補助） | それぞれ `docker run` の最後のイメージ名、`-p`、`-e` と同じ |

> 🧒 **かみくだくと**: Compose = 引っ越しの「段取り表」。どの段ボール（イメージ）を、どの部屋（コンテナ）で、どの設定で開けるかを1枚に書いておく。サービス = 段取り表の1行。「DB の部屋」「API の部屋」のような、部屋の役割です。

`docker run` の指定と `compose.yaml` の行は、1対1で対応しています。

```text
docker run -d --name ec-api --network ec-net -p 8000:8000 -e DB_HOST=ec-db ... ec-api:step6
              │             │                │            │                    │
              ▼             ▼                ▼            ▼                    ▼
              サービス名    （自動）         ports:       environment:         image:
              api:
```

**見てほしいところ**: `--network` に対応する行がありません。`--name` も書いていません。コンテナ名はサービス名をもとに、ネットワークは丸ごと、Compose が自動で決めます。

自動で決めたものを確かめます。

```bash
docker network ls --filter name=roadmap-sh-docker
docker exec roadmap-sh-docker-api-1 getent hosts db
```

```text
NETWORK ID     NAME                        DRIVER    SCOPE
9a029337d88e   roadmap-sh-docker_default   bridge    local
172.20.0.2      db
```

✅ 検証済み: Docker Compose v5.5.1。ID と IP アドレスは環境で変わる。

Compose は、**プロジェクト**ごとに名前の付いたネットワークを1つ作り、すべてのサービスをつなぎます。プロジェクト名は、`compose.yaml` を置いたフォルダの名前です。P3-3 の自作ネットワークと同じなので、**サービス名で相手を呼べます**。だから `DB_HOST` は `db` です。

> 🧒 **かみくだくと**: プロジェクト = 1枚の段取り表で建てた部屋のまとまり。Compose は、名前の頭にプロジェクト名を付けて、ほかのまとまりと混ざらないようにします。

| 何に付く名前か | 決まり方 | 例 |
| --- | --- | --- |
| コンテナ | プロジェクト名-サービス名-番号 | `roadmap-sh-docker-api-1` |
| ネットワーク | プロジェクト名_default | `roadmap-sh-docker_default` |
| サービス名（DNS で引ける名前） | `services:` のキー | `db`、`api` |

なぜを下っていきます。

```text
なぜ、compose.yaml にまとめるのか
  → 長い docker run を毎回打つと、打ち間違えるから
      → なぜ、ファイルにすると打ち間違えないのか
          → 設定がファイルに残り、毎回同じものが使われるから
              → なぜ、ネットワークを書かなくてよいのか
                  → Compose がプロジェクトごとに1つ作り、全サービスをつなぐから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | `package.json` の `scripts` に近い。ただし Compose は「打つコマンド」ではなく「あるべき状態」を書く。`up` は、いまの状態をその形に合わせる |
| **なぜこの設計か** | 複数のコンテナの設定を1か所に集め、リポジトリで共有できるようにするため |
| **ビルド時かランタイム時か** | ランタイム。`compose.yaml` は `docker run` の代わりで、イメージは作らない（`build:` は P4-4） |
| **ホストからの見え方** | `docker compose ps`。`docker ps` でも見えるが、ほかのコンテナと混ざる |
| **失敗時の挙動** | YAML の字下げを間違えると、起動前に止まる。下の例 |

```text
go-yaml load error in parser (while parsing a block mapping) at L2.C3-L4.C5: did not find expected key
```

✅ 検証済み: Docker Compose v5.5.1。3行目の `image:` の前に空白を1つ足して起こした。`L2.C3` は「2行目の3文字目」で、どこで読めなくなったかを示す。

### 1-3. 🐧 Linux注

> 🐧 **Linux注**: `getent hosts db` は、`db` という名前を IP アドレスに変換して表示します（P3-3）。

### 1-4. 解説 — なぜこうするか

Compose は Docker の外側にある道具です。Compose が Docker デーモンに依頼する中身は、P1〜P3 で手で打った `docker run` や `docker network create` と同じです。だから、コンテナは `docker ps` や `docker logs` でも見えます。

🧠 **Docker の考え方**: `docker run` は「いまこれをして」という命令。`compose.yaml` は「この形であってほしい」という宣言。`up` が、いまの状態を宣言に近づける。

### 1-5. 🔓 教材用の簡略化

> 🔓 **教材用の簡略化**: パスワードを `compose.yaml` に直接書いています。このファイルはリポジトリに入るので、誰でも読めます。
> **本番では**: P6-3 で secrets を使います。
> 根拠: https://docs.docker.com/compose/how-tos/use-secrets/

### 1-6. 🔮 予測 → 動作確認

**問い**: `docker compose down` のあと、もう一度 `up` すると、商品は何件になるでしょうか。

先に、いまの DB がどこに書かれているかを控えておきます。

```bash
docker inspect roadmap-sh-docker-db-1 --format '{{range .Mounts}}{{.Name}}{{end}}'
```

```text
30cb90849685fedc9ecda817f82f77ec85a85d30c90bb9f6d1c28ea0ad3bcb9c
```

**名前の無い volume** です（P3-1）。`compose.yaml` に volume を書かなかったので、`mysql:8.4` のイメージの指定で自動に作られました。この名前を控えておきます。

```bash
docker compose down
docker compose up -d db
until docker logs roadmap-sh-docker-db-1 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker compose up -d
sleep 4
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/products
```

```text
 Container roadmap-sh-docker-api-1 Removed
 Container roadmap-sh-docker-db-1 Removed
 Network roadmap-sh-docker_default Removed
（省略）
500
```

✅ 検証済み: Docker Compose v5.5.1

**500 になりました。** 表が無いからです。`down` でコンテナが消え、新しいコンテナには新しい名前の無い volume が作られました。控えた volume は、まだ残っています。

```bash
docker volume ls --filter dangling=true
```

`dangling=true` は、どのコンテナにもつながっていない volume だけを出す指定です。控えた名前が出てきます。P4-2 の最初で消します。

✅ 検証済み: Docker Engine 29.8.0

### 1-7. ✅ 想起チェック

1. `compose.yaml` に `--network` を書かなくても、`api` から `db` という名前で DB に届くのは、なぜですか
2. `docker compose down` が消すものと、消さないものは何ですか
3. `docker compose ps` と `docker ps` の違いは何ですか

<details><summary>答え</summary>

1. Compose がプロジェクトごとにネットワークを1つ作り、すべてのサービスをつなぐから。サービス名がそのまま DNS の名前になる
2. コンテナとネットワークを消す。volume とイメージは消さない
3. `docker compose ps` は、その `compose.yaml` のコンテナだけを出す。`docker ps` はすべてを出す

</details>

### 1-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `services:` | 1-1 で実践、1-2 で解剖 |
| `docker compose up` | 1-1 で実践、1-2 で解剖 |
| `docker compose down` | 1-2 で解剖、1-6 で確認 |
| `image:` `ports:` `environment:` | 1-2 で `docker run` と対応。`environment:` は ⏭️ P4-5 で回収 |
| YAML | 1-1 の Linux注 |

### 📇 まとめカード

> **長い `docker run` は `compose.yaml` へ。サービス名で呼び合える。**

**残った問い**: `down` するとデータが消えた。P3 では `-v ec-db-data:...` と書いた。Compose ではどこに書くのか。

---
▶ **次**: P4-2 volume と network を宣言する

---

## P4-2: volume と network を宣言する

**❓ この回の問い**: 前回の答えは「Compose がネットワークを作り、サービス名で呼べる」だった。でも、`down` するとデータが消えた。
→ **Compose で、残すデータの倉庫はどう書くのか？**

**作るもの / 確かめること**: `down` ではデータが残り、`down -v` では消えることを確かめる
**重要度**: 🔴 毎日使う — DB を動かす `compose.yaml` には、必ず volume を書くから
**前ステップとの接続**: P4-1 の `compose.yaml` に、volume とネットワークを書き足す

### 2-0. このステップの初出トークン

**Docker**: `volumes:` `networks:` `docker compose ps`
**Linux**: なし
**その他**: なし

### 2-1. 実践

まず、P4-1 で残った名前の無い volume を片付けます。名前は 1-6 で控えたものです。

```bash
docker compose down -v
docker volume rm 30cb90849685fedc9ecda817f82f77ec85a85d30c90bb9f6d1c28ea0ad3bcb9c
```

`down -v` は、いま使っている名前の無い volume も一緒に消します。2行目は、1つ前の `down` で取り残されたものを消します。名前は自分の控えに置き換えてください。

✅ 検証済み: Docker Compose v5.5.1

**ファイル**: `compose.yaml`（全文を置き換え）

```yaml
services:
  db:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: root-pass
      MYSQL_DATABASE: ec
      MYSQL_USER: ec
      MYSQL_PASSWORD: ec-pass
    volumes:
      - db-data:/var/lib/mysql
    networks:
      - back

  api:
    image: ec-api:step7
    ports:
      - "8000:8000"
    environment:
      DB_HOST: db
      DB_NAME: ec
      DB_USER: ec
      DB_PASSWORD: ec-pass
    networks:
      - back

volumes:
  db-data:

networks:
  back:
```

起動して、商品を入れます。

```bash
docker compose up -d db
until docker logs roadmap-sh-docker-db-1 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker compose up -d
sleep 4
docker exec roadmap-sh-docker-api-1 .venv/bin/python src/manage.py migrate
docker exec roadmap-sh-docker-api-1 .venv/bin/python src/manage.py loaddata products
```

`up` の出力に、新しい行が出ます。

```text
 Volume roadmap-sh-docker_db-data Created
 Network roadmap-sh-docker_back Created
```

✅ 検証済み: Docker Compose v5.5.1

`docker compose ps` は、状態を確かめる道具です。`-a` を付けると、止まっているコンテナも出ます。

```bash
docker compose ps -a --format '{{.Name}} {{.Service}} {{.Status}}'
```

```text
roadmap-sh-docker-api-1 api Up 4 seconds
roadmap-sh-docker-db-1 db Up 10 seconds
```

✅ 検証済み: Docker Compose v5.5.1

**🔮 予測**: `down` してから `up` すると、商品は何件でしょうか。

```bash
docker compose down
docker volume ls --filter name=roadmap-sh-docker
docker compose up -d db
until docker logs roadmap-sh-docker-db-1 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker compose up -d
sleep 4
curl -s localhost:8000/api/products | grep -o '"id"' | wc -l
```

```text
DRIVER    VOLUME NAME
local     roadmap-sh-docker_db-data
（省略）
       3
```

✅ 検証済み: Docker Compose v5.5.1

**残りました。** `down` のあとも、volume `roadmap-sh-docker_db-data` は消えていません。

### 2-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| いちばん外の `volumes:` | トップレベルの volume 定義 | このプロジェクトで使う、名前付きの volume を宣言する。`up` のとき、無ければ作る |
| サービスの中の `volumes:` | サービスの volume 指定 | **ランタイム**に、そのコンテナへ volume をマウントする。`-v` と同じ |
| いちばん外の `networks:` | トップレベルのネットワーク定義 | このプロジェクトで使うネットワークを宣言する。`up` で作り、`down` で消す |
| サービスの中の `networks:` | サービスのネットワーク指定 | そのコンテナを、どのネットワークにつなぐか。`--network` と同じ |
| `docker compose ps` | サービスの一覧 | このプロジェクトのコンテナの状態を出す。`-a` で止まったものも出す |

**名前が似ている2つの `volumes:`** を並べます。

| | いちばん外の `volumes:` | サービスの中の `volumes:` |
| --- | --- | --- |
| 書く場所 | 行の頭（字下げなし） | サービスの下 |
| 意味 | 倉庫を「建てる」宣言 | 部屋の扉を倉庫に「つなぐ」指定 |
| `docker` コマンドでは | `docker volume create` | `docker run -v` |

> 🧒 **かみくだくと**: いちばん外の `volumes:` は「この建物には `db-data` という貸し倉庫がある」という宣言。サービスの中の `volumes:` は「DB の部屋の扉を、その倉庫につなぐ」という工事の指示です。

`down` と `down -v` の違いを図にします。

```text
                       docker compose down    docker compose down -v
コンテナ                     消す                  消す
ネットワーク back            消す                  消す
volume db-data               残す                  消す
イメージ                     残す                  残す
```

**見てほしいところ**: 違いは volume の1行だけです。`-v` を付けると、DB のデータが消えます。

なぜを下っていきます。

```text
なぜ、down してもデータが残るのか
  → データが、名前付きの volume にあるから（P3-1）
      → なぜ、down は名前付きの volume を消さないのか
          → コンテナは作り直すもの、volume は残すものだから
              → なぜ、ネットワークは消してよいのか
                  → ネットワークには何も保存されず、up でいつでも作り直せるから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | 対応物なし。アプリのフレームワークは、DB の置き場所を作ったり消したりしない |
| **なぜこの設計か** | 寿命の違うものを分ける（P3-1）。コンテナとネットワークは使い捨て、データは残す |
| **ビルド時かランタイム時か** | ランタイム |
| **ホストからの見え方** | `docker volume ls` と `docker network ls` に、`プロジェクト名_` の付いた名前で出る |
| **失敗時の挙動** | サービスの中で使った volume をいちばん外に書き忘れると、起動前に止まる。下の例 |

```text
service "db" refers to undefined volume db-data: invalid compose project
```

✅ 検証済み: Docker Compose v5.5.1。いちばん外の `volumes:` を消して起こした。

### 2-3. 🐧 Linux注

なし。

### 2-4. 解説 — なぜこうするか

`networks:` を書く前は、`default` という名前のネットワークが自動で使われていました。自分で書くと、名前を付けて分けられます。今は `back`（裏方）の1つだけです。P4-4 で、画面のための `front`（表側）を足します。分けた理由は、そこで確かめます。

🧠 **Docker の考え方**: `down` は「部屋を片付ける」。`down -v` は「倉庫まで解約する」。`-v` を付けるのは、データを本当に捨てたいときだけ。

### 2-5. ⚠️ アンチパターン

> ⚠️ **アンチパターン**: 調子が悪いときに、反射で `docker compose down -v` を打つ。DB のデータが消え、戻せません。
> まず `down` だけで直るか試します。`-v` は、データを消すと決めたときに使います。
> 根拠: https://docs.docker.com/reference/cli/docker/compose/down/

### 2-6. 🔮 予測 → 動作確認

**問い**: `down -v` のあと `up` すると、`curl` は何を返すでしょうか。

```bash
docker compose down -v
docker compose up -d db
until docker logs roadmap-sh-docker-db-1 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker compose up -d
sleep 4
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/products
```

```text
 Volume roadmap-sh-docker_db-data Removed
（省略）
500
```

✅ 検証済み: Docker Compose v5.5.1

volume ごと消えたので、表がありません。P4-3 は、この空の状態から始めます。

### 2-7. ✅ 想起チェック

1. いちばん外の `volumes:` と、サービスの中の `volumes:` は、それぞれ何をしますか
2. `down` と `down -v` で違うのは何ですか
3. `service "db" refers to undefined volume` が出ました。何を疑いますか

<details><summary>答え</summary>

1. いちばん外は volume を作る宣言。サービスの中は、その volume をコンテナにつなぐ指定
2. `-v` を付けると volume も消える。それ以外は同じ
3. いちばん外の `volumes:` への書き忘れ

</details>

### 2-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `volumes:` | 2-1 で実践、2-2 で解剖 |
| `networks:` | 2-1 で実践、2-2 で解剖。分ける理由は ⏭️ P4-4 で回収 |
| `docker compose ps` | 2-1 で実践、2-2 で解剖 |

### 📇 まとめカード

> **倉庫はいちばん外で宣言し、サービスでつなぐ。`down -v` は倉庫まで消す。**

**残った問い**: ずっと「`db` を先に起動して、待ってから残りを起動する」と2回に分けてきた。1回の `up` ではだめなのか。

---
▶ **次**: P4-3 「起動した」の定義

---

## P4-3: 「起動した」の定義

**❓ この回の問い**: 前回の答えは「倉庫を宣言すればデータが残る」だった。でも、起動はずっと2回に分けていた。
→ **`docker compose up -d` 1回で、全部を正しい順に起動できないのか？**

**作るもの / 確かめること**: DB の準備前に API が起動して落ちる状態を作り、`healthcheck` で直す
**重要度**: 🔴 毎日使う — DB を使うサービスには、ほぼ必ず必要になるから
**前ステップとの接続**: P4-2 の空の DB のまま、`up` を1回にする

### 3-0. このステップの初出トークン

**Docker**: `healthcheck` `depends_on` `condition`
**Linux**: 終了コード
**その他**: なし

### 3-1. 実践

**🔮 予測**: DB を待たずに、1回の `up` で全部を起動すると、どうなるでしょうか。

```bash
docker compose down -v
docker compose up -d
sleep 15
curl -sS localhost:8000/api/products
docker logs roadmap-sh-docker-api-1 2>&1 | grep OperationalError | tail -1
docker compose ps --format '{{.Service}} {{.Status}}'
```

```text
curl: (56) Recv failure: Connection reset by peer
django.db.utils.OperationalError: (2002, "Can't connect to server on 'db' (115)")
api Up 15 seconds
db Up 15 seconds
```

✅ 検証済み: Docker Compose v5.5.1。`curl` の番号は `(52) Empty reply from server` になることもある。

**API が応答しません。でも、コンテナは `Up` のままです。** 15秒待って DB の準備ができても、API は戻りません。

`(2002, "Can't connect to server on 'db'")` は、「`db` という名前は引けたが、3306 番が受け付けていない」という意味です。P3 で見た `(2005, "Unknown server host")` とは違います。

| エラー | 意味 | どの層か |
| --- | --- | --- |
| `(2005, "Unknown server host 'db'")` | 名前が引けない | ネットワーク（DNS） |
| `(2002, "Can't connect to server on 'db'")` | 名前は引けたが、相手が受け付けていない | 相手のプロセス |

直します。

**ファイル**: `compose.yaml`（差分）

```diff
 services:
   db:
     image: mysql:8.4
     environment:
       MYSQL_ROOT_PASSWORD: root-pass
       MYSQL_DATABASE: ec
       MYSQL_USER: ec
       MYSQL_PASSWORD: ec-pass
+    healthcheck:
+      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]
+      interval: 2s
+      timeout: 5s
+      retries: 30
     volumes:
       - db-data:/var/lib/mysql
     networks:
       - back

   api:
     image: ec-api:step7
+    depends_on:
+      db:
+        condition: service_healthy
     ports:
       - "8000:8000"
```

```bash
docker compose down -v
docker compose up -d
```

```text
 Container roadmap-sh-docker-db-1 Started
 Container roadmap-sh-docker-db-1 Waiting
 Container roadmap-sh-docker-db-1 Healthy
 Container roadmap-sh-docker-api-1 Starting
 Container roadmap-sh-docker-api-1 Started
```

✅ 検証済み: Docker Compose v5.5.1。`up` は約7秒で戻った。

`Waiting` → `Healthy` のあとに、`api` が起動しています。表を作って確かめます。

```bash
docker compose ps --format '{{.Service}} {{.Status}}'
docker exec roadmap-sh-docker-api-1 .venv/bin/python src/manage.py migrate
docker exec roadmap-sh-docker-api-1 .venv/bin/python src/manage.py loaddata products
curl -s localhost:8000/api/products | grep -o '"id"' | wc -l
```

```text
api Up 3 seconds
db Up 9 seconds (healthy)
（省略）
       3
```

✅ 検証済み: Docker Compose v5.5.1

**1回の `up` で、正しい順に起動しました。** これからは `db` を先に起動する手順は要りません。

### 3-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `healthcheck:` | ヘルスチェック | **ランタイム**に、Docker デーモンがコンテナの中で `test` のコマンドを `interval` ごとに実行する。終了コードが 0 なら healthy |
| `test:` | 確かめるコマンド | `CMD` の後ろが、コンテナの中で実行される。ここでは `mysqladmin ping` |
| `interval` `timeout` `retries` | 間隔・時間切れ・回数 | 2秒ごとに試す。5秒で応答が無ければ失敗。30回続けて失敗したら unhealthy |
| `depends_on:` | 依存関係 | `api` は `db` のあとに起動する、という順番の指定 |
| `condition: service_healthy` | 起動の条件 | `db` が healthy になるまで、`api` の起動を待たせる |

> 🧒 **かみくだくと**: ヘルスチェック = 部屋の住人に、定期的に「元気？」と声をかける見回り。返事があれば healthy です。`depends_on` = 「DB の部屋の住人が返事をするまで、API の部屋は開けない」という段取りです。

時間の流れで並べます。

```text
時間 →
db   : 起動 ─ 初期化中（3306 は閉じている）─────── 3306 を開く
           ping ✗    ping ✗    ping ✗              ping ✓ → healthy
api  :                                                      起動
           ↑ condition がないと、api はここで起動して落ちる
```

**見てほしいところ**: 「コンテナが起動した」と「DB が受け付ける」の間に、数秒の差があります。`depends_on` だけでは、この差を待ちません。

見回りの記録は、`docker inspect` で見られます。

```bash
docker inspect roadmap-sh-docker-db-1 --format '{{json .State.Health.Log}}' | head -c 600
```

```text
[{"Start":"...","ExitCode":1,"Output":"mysqladmin: connect to server at '127.0.0.1' failed\nerror: 'Can't connect to MySQL server ..."},
 ...
 {"Start":"...","ExitCode":0,"Output":"mysqladmin: connect to server at '127.0.0.1' failed\nerror: 'Access denied for user 'root'@'localhost' (using password: NO)'"}]
```

✅ 検証済み: Docker Compose v5.5.1 / MySQL 8.4.13。読みやすく整えた。

最後の行は `Access denied` なのに、`ExitCode` が 0 です。`mysqladmin ping` は、**サーバが返事をすれば 0** を返します。パスワードが合わなくても、サーバが動いている証拠になります。だから、ここにパスワードを書く必要はありません。

なぜを下っていきます。

```text
なぜ、1回の up だと API が落ちたのか
  → API が起動したとき、DB がまだ受け付けていなかったから
      → なぜ、起動の順番を決めても足りないのか
          → 「コンテナが起動した」と「中のプログラムが準備できた」は別だから
              → なぜ、Docker は中の準備を知らないのか
                  → Docker が見ているのはプロセスだけで、アプリの中身は知らないから
                      → だから「準備できたか」を確かめるコマンドを、自分で渡す
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | フロントの E2E テストで「サーバが応答するまで待ってから始める」設定に近い。ただし、待つのは Docker 自身 |
| **なぜこの設計か** | 「準備できた」の意味は、アプリごとに違う。Docker はそれを知らないので、確かめ方を利用者に任せる |
| **ビルド時かランタイム時か** | ランタイム。Docker デーモンがコンテナの中でコマンドを実行する |
| **ホストからの見え方** | `docker compose ps` の `(healthy)`、`docker inspect` の `.State.Health` |
| **失敗時の挙動** | 30回続けて失敗すると unhealthy になり、`up` が下のエラーで止まる |

```text
dependency failed to start: container roadmap-sh-docker-db-1 is unhealthy
```

✅ 検証済み: Docker Compose v5.5.1。`test` を `["CMD", "false"]` にし、`retries: 3` で起こした。

### 3-3. 🐧 Linux注

> 🐧 **Linux注**: 終了コード = コマンドが終わるときに返す番号。0 が成功、0 以外が失敗です。シェルでは `echo $?` で見られます。

### 3-4. 解説 — なぜこうするか

`-h 127.0.0.1` には理由があります。MySQL のイメージは、初期化の間だけ、外から接続できない仮のサーバを動かします。`-h` を付けないと、この仮のサーバに返事をもらい、早すぎる healthy になることがあります。`127.0.0.1` を指定すると、本番のサーバが 3306 番を開くまで成功しません。
根拠: https://github.com/docker-library/mysql/blob/master/8.4/docker-entrypoint.sh

`depends_on` は、**起動するとき**の順番だけを決めます。動いている途中で DB が落ちても、API は止まりません（P3-4 の 4-4 と同じ）。

🧠 **Docker の考え方**: Docker が知っているのは「プロセスが動いているか」だけ。「使える状態か」は、ヘルスチェックで教える。

### 3-5. 🏢 実務メモ

> 🏢 **実務メモ**: DB のように準備に時間がかかるサービスには、ヘルスチェックを書き、依存する側は `condition: service_healthy` で待たせます。`depends_on` だけでは、コンテナの起動しか待ちません。
> 根拠: https://docs.docker.com/compose/how-tos/startup-order/

### 3-6. 🔮 予測 → 動作確認

**問い**: `db` だけを止めると、`docker compose ps` の `api` の STATUS はどうなるでしょうか。

```bash
docker compose stop db
docker compose ps -a --format '{{.Service}} {{.Status}}'
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/products
docker compose start db
```

```text
api Up 2 minutes
db Exited (0) 1 second ago
500
```

✅ 検証済み: Docker Compose v5.5.1

`api` は動いたままで、500 を返します。`depends_on` は起動のときだけ働きます。`docker compose start db` で戻ります。

### 3-7. ✅ 想起チェック

1. `depends_on` だけでは、なぜ足りないのですか
2. `mysqladmin ping` が `Access denied` を出しても healthy になるのは、なぜですか
3. `(2002, "Can't connect ...")` と `(2005, "Unknown server host ...")` は、それぞれどの層の問題ですか

<details><summary>答え</summary>

1. コンテナの起動は待つが、中のプログラムの準備は待たないから
2. サーバが返事をすれば終了コード 0 を返すから。返事があること自体が、動いている証拠になる
3. 2002 は相手のプロセスがまだ受け付けていない。2005 は名前が引けない（ネットワーク）

</details>

### 3-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `healthcheck` | 3-1 で実践、3-2 で解剖 |
| `depends_on` | 3-1 で実践、3-2 で解剖 |
| `condition` | 3-2 で解剖 |
| 終了コード | 3-3 の Linux注 |

### 📇 まとめカード

> **「起動した」と「使える」は別。使えるかどうかは、ヘルスチェックで教える。**

**残った問い**: API と DB は1回で起動できた。次は画面がほしい。でも、この Mac には Node.js が入っていない。

---
▶ **次**: P4-4 React の画面を足す

---

## P4-4: React の画面を足す

**❓ この回の問い**: 前回の答えは「ヘルスチェックで準備を待てる」だった。API はそろった。でも、この Mac には Node.js が無い。
→ **Node.js を入れずに、React の開発サーバを動かし、変更をすぐ反映できるのか？**

**作るもの / 確かめること**: React の画面を `web` サービスで動かし、ファイルの変更をコンテナへ同期する
**重要度**: 🔴 毎日使う — 自分のコードを Compose で開発するときの基本形だから
**前ステップとの接続**: P4-3 の `compose.yaml` に `web` を足し、`api` も `compose.yaml` からビルドする

### 4-0. このステップの初出トークン

**Docker**: `build:` `docker compose exec` `docker compose watch`
**Linux**: なし
**その他**: Vite、開発サーバ、プロキシ

### 4-1. 実践

#### 画面のコードを書く

React の画面を `apps/web/` に作ります。商品一覧を出すだけです。

| ファイル | 役割 |
| --- | --- |
| `package.json` | 使う部品の一覧 |
| `vite.config.js` | 開発サーバの設定。`/api` を API に中継する |
| `index.html` | 画面の入口 |
| `src/main.jsx` `src/App.jsx` | 画面のコード |
| `Dockerfile` `.dockerignore` | イメージの作り方 |

> 🧒 **かみくだくと**: Vite（ヴィート）= React のコードを、ブラウザで動く形にしながら配る道具。開発サーバ = 書き換えるとすぐ画面に反映してくれる、開発用の配り係です。

```bash
mkdir -p apps/web/src
```

**ファイル**: `apps/web/package.json`（新規・全文）

```json
{
  "name": "ec-web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0"
  },
  "dependencies": {
    "react": "^19.3.1",
    "react-dom": "^19.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^6.2.1",
    "vite": "^8.3.6"
  }
}
```

`--host 0.0.0.0` は、コンテナの外からの接続を受け付ける指定です（P2-3 の `0.0.0.0` と同じ理由）。

**ファイル**: `apps/web/vite.config.js`（新規・全文）

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // /api で始まるリクエストを、api サービスへ中継する
      "/api": "http://api:8000",
    },
  },
});
```

**ファイル**: `apps/web/index.html`（新規・全文）

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <title>EC</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

**ファイル**: `apps/web/src/main.jsx`（新規・全文）

```jsx
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(<App />);
```

**ファイル**: `apps/web/src/App.jsx`（新規・全文）

```jsx
import { useEffect, useState } from "react";

export default function App() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    fetch("/api/products")
      .then((res) => res.json())
      .then(setProducts);
  }, []);

  return (
    <main>
      <h1>商品一覧</h1>
      <ul>
        {products.map((p) => (
          <li key={p.id}>
            {p.name} — {p.price}円
          </li>
        ))}
      </ul>
    </main>
  );
}
```

#### ロックファイルを作る

`npm ci` で部品を入れるには、`package-lock.json` が要ります。この Mac に Node.js は無いので、P2 の宿題 Lv2 と同じ方法でコンテナの中で作ります。

```bash
docker run --rm -i node:24-alpine sh -c 'cd /tmp && cat > package.json && npm install --package-lock-only --silent && cat package-lock.json' < apps/web/package.json > apps/web/package-lock.json
head -3 apps/web/package-lock.json
```

```text
{
  "name": "ec-web",
  "lockfileVersion": 3,
```

✅ 検証済み: node:24-alpine（Node 24.22.2）。約9秒かかった。

`--package-lock-only` は、部品を入れずにロックファイルだけを作る指定です。

#### Dockerfile を書く

**ファイル**: `apps/web/Dockerfile`（新規・全文）

```dockerfile
FROM node:24-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]
```

P2-4 と同じ順番です。部品の一覧を先に `COPY` し、コードはあとから `COPY` します。

**ファイル**: `apps/web/.dockerignore`（新規・全文）

```text
node_modules
Dockerfile
.dockerignore
```

#### compose.yaml に足す

**ファイル**: `compose.yaml`（全文を置き換え）

```yaml
services:
  db:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: root-pass
      MYSQL_DATABASE: ec
      MYSQL_USER: ec
      MYSQL_PASSWORD: ec-pass
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]
      interval: 2s
      timeout: 5s
      retries: 30
    volumes:
      - db-data:/var/lib/mysql
    networks:
      - back

  api:
    build: ./apps/api
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      DB_HOST: db
      DB_NAME: ec
      DB_USER: ec
      DB_PASSWORD: ec-pass
    volumes:
      - ./apps/api/src:/app/src
    networks:
      - front
      - back

  web:
    build: ./apps/web
    ports:
      - "5173:5173"
    depends_on:
      - api
    networks:
      - front
    develop:
      watch:
        - action: sync
          path: ./apps/web/src
          target: /app/src
        - action: rebuild
          path: ./apps/web/package.json

volumes:
  db-data:

networks:
  front:
  back:
```

変えたところは3つです。

- `api` の `image: ec-api:step7` を `build: ./apps/api` にした。これからは、Compose がイメージを作る
- `api` に P3-2 の bind mount を足した。`./apps/api/src` は、`compose.yaml` から見た位置
- `web` を足した。`api` は `front` と `back` の両方、`web` は `front` だけにつないだ

```bash
docker compose up -d --build
```

`--build` は、起動の前にイメージを作り直す指定です。初回は数十秒かかります。

```text
（ビルドのログ。省略）
 Container roadmap-sh-docker-db-1 Healthy
 Container roadmap-sh-docker-api-1 Started
 Container roadmap-sh-docker-web-1 Started
```

✅ 検証済み: Docker Compose v5.5.1 / Vite 8.3.6

ブラウザで http://localhost:5173 を開くと、商品が3つ並びます。

`curl` でも確かめます。**5173 番に `/api/products` を頼んでいる**ところが大事です。

```bash
curl -s localhost:5173/api/products | grep -o '"id"' | wc -l
```

```text
       3
```

✅ 検証済み: Docker Compose v5.5.1

#### コンテナの中を見る: `docker compose exec`

これまで `docker exec roadmap-sh-docker-api-1 ...` と長い名前で打ってきました。`docker compose exec` なら、サービス名で打てます。

```bash
docker compose exec web ls
docker compose exec web getent hosts api
docker compose exec web getent hosts db; echo "exit=$?"
```

```text
index.html
node_modules
package-lock.json
package.json
src
vite.config.js
172.21.0.2        api  api
exit=2
```

✅ 検証済み: Docker Compose v5.5.1

**`web` からは `api` が見えますが、`db` は見えません。** `web` は `front` にしかつながっていないからです。P4-2 で宣言を後回しにした「分けた理由」がこれです。

#### 変更を同期する: `docker compose watch`

```bash
docker compose watch
```

```text
Watch enabled
```

このターミナルは開いたままにします。別のターミナルで `apps/web/src/App.jsx` の `<h1>商品一覧</h1>` を `<h1>商品一覧（watch）</h1>` に書き換えて保存します。

```text
Syncing service "web" after 1 changes were detected
```

✅ 検証済み: Docker Compose v5.5.1。保存のしかたによって、数字が 2 になることがある。

ブラウザの見出しが、再読み込みしなくても変わります。コンテナの中のファイルも変わっています。

```bash
docker compose exec web grep -o '商品一覧[^<]*' src/App.jsx
```

```text
商品一覧（watch）
```

✅ 検証済み: Docker Compose v5.5.1

確かめたら見出しを `商品一覧` に戻し、`watch` のターミナルは Ctrl+C で止めます。止めても、コンテナは動いたままです。

### 4-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `build: ./apps/web` | ビルドの指定 | **ビルド時**に、このフォルダをビルドコンテキストにして `docker build` する。`up --build` か、イメージが無いときに動く |
| `docker compose exec` | サービスでのコマンド実行 | 動いているコンテナで、コマンドを追加で実行する。`docker exec` と同じだが、サービス名で指定できる |
| `develop.watch` | 監視の設定 | `docker compose watch` が使う設定。`up` だけでは働かない |
| `action: sync` | 同期 | `path` のファイルが変わったら、コンテナの `target` へ写す |
| `action: rebuild` | 作り直し | `path` のファイルが変わったら、イメージを作り直し、コンテナを入れ替える |
| `proxy` | プロキシ（Vite の設定） | ブラウザから来た `/api/...` を、Vite が `http://api:8000/api/...` に送り直す |

> 🧒 **かみくだくと**: プロキシ = 取り次ぎ係。ブラウザは Vite にだけ頼み、Vite が裏で API に頼み直す。ブラウザは API の場所を知らなくて済みます。

リクエストの流れを図にします。

```text
ブラウザ（この Mac）
   │ localhost:5173/api/products
   ▼
web コンテナ（Vite）        ネットワーク front
   │ http://api:8000/api/products   ← サービス名で引ける
   ▼
api コンテナ（Django）      ネットワーク front と back
   │ db:3306
   ▼
db コンテナ（MySQL）        ネットワーク back
```

**見てほしいところ**: ブラウザは `api` という名前を引けません。ブラウザはこの Mac で動いていて、Compose のネットワークの外にいるからです。名前で `api` を呼べるのは、同じネットワークの中にいる `web` だけです。

`api` と `web` は、コードの届け方が違います。

| | `api`（bind mount） | `web`（watch の sync） |
| --- | --- | --- |
| 何をつなぐか | Mac の `apps/api/src` を、そのまま `/app/src` に見せる | 変わったファイルを、コンテナの `/app/src` に写す |
| コンテナの中のファイル | Mac と同じ実体 | 写した別の実体 |
| 起動するコマンド | `docker compose up` だけでよい | `docker compose watch` が要る |
| 依存の変更 | 手で `up --build` | `rebuild` で自動 |

`web` に bind mount を使わなかった理由があります。`apps/web` を丸ごとつなぐと、イメージの中の `/app/node_modules` が Mac 側のフォルダで隠れます。Mac 側には `node_modules` が無いので、Vite が起動できません。`src` だけを写せば、`node_modules` はイメージのものが使われます。

なぜを下っていきます。

```text
なぜ、Node.js が無いのに React の開発ができるのか
  → Node.js はイメージの中にあり、Vite はコンテナで動いているから
      → なぜ、Mac で書いた変更がコンテナに届くのか
          → watch が変更を見つけて、コンテナへ写すから
              → なぜ、ブラウザから API に届くのか
                  → Vite がプロキシになり、同じネットワークの api へ送り直すから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | `vite.config.js` の `server.proxy` は、ふだんの React 開発と同じ書き方。違うのは、相手が `localhost` ではなくサービス名である点 |
| **なぜこの設計か** | 開発に要る道具をイメージに閉じ込める。誰の Mac でも同じ版の Node.js で動く |
| **ビルド時かランタイム時か** | `build:` はビルド時。`exec` と `watch` はランタイム |
| **ホストからの見え方** | `docker compose ps` に `web` が出る。`docker image ls` に `roadmap-sh-docker-web` と `roadmap-sh-docker-api` が出る |
| **失敗時の挙動** | `proxy` の相手を `localhost:8000` にすると、`web` コンテナ自身の 8000 番を探して失敗し、`/api` が 502 になる |

✅ 検証済み: Docker Compose v5.5.1。`"/api": "http://localhost:8000"` にすると、`curl` が 502 を返し、Vite のログに `http proxy error: /api/products` と `ECONNREFUSED` が出た。

> 💡補足: `build:` だけで `image:` を書かないと、Compose はイメージに `プロジェクト名-サービス名` という名前を付けます。

### 4-3. 🐧 Linux注

なし。

### 4-4. 解説 — なぜこうするか

`depends_on: - api` には `condition` がありません。この書き方は「`api` のコンテナを先に起動する」だけです。画面は API が遅れて準備できても困らないので、待たせていません。

`api` を `front` と `back` の両方につないだのは、`web` から呼ばれ、`db` を呼ぶからです。`db` を `back` だけにすると、画面のコンテナからは DB に届きません。届かなくてよい相手には、つながない設計です。

🧠 **Docker の考え方**: 道具（Node.js）は箱の中、コードは手元。`watch` が手元と箱の間を写す。

### 4-5. 🏢 実務メモ

> 🏢 **実務メモ**: `node_modules` のように、イメージの中で作るものを bind mount で隠さないために、`watch` の `sync` で必要なフォルダだけを写します。依存の一覧が変わったときは `rebuild` でイメージを作り直します。
> 根拠: https://docs.docker.com/compose/how-tos/file-watch/

### 4-6. 🔮 予測 → 動作確認

**問い**: `watch` を動かしたまま `apps/web/package.json` を書き換えると、何が起きるでしょうか。

`"private": true,` の次に `"version": "0.1.0",` の1行を足して保存します。

```text
 Container roadmap-sh-docker-web-1 Recreate
 Container roadmap-sh-docker-web-1 Recreated
 Container roadmap-sh-docker-web-1 Started
```

✅ 検証済み: Docker Compose v5.5.1

`rebuild` が働き、イメージを作り直して、コンテナを入れ替えました。確かめたら、足した1行を消しておきます。

### 4-7. ✅ 想起チェック

1. ブラウザが `api:8000` に直接アクセスできないのは、なぜですか
2. `web` で bind mount ではなく `watch` の `sync` を使ったのは、なぜですか
3. `docker compose exec` と `docker exec` の違いは何ですか

<details><summary>答え</summary>

1. ブラウザは Mac で動いていて、Compose のネットワークの外にいるから。サービス名はネットワークの中でだけ引ける
2. `apps/web` を丸ごとつなぐと、イメージの中の `node_modules` が隠れるから
3. 中身は同じ。`docker compose exec` は、コンテナ名ではなくサービス名で指定できる

</details>

### 4-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `build:` | 4-1 で実践、4-2 で解剖 |
| `docker compose exec` | 4-1 で実践、4-2 で解剖 |
| `docker compose watch` | 4-1 で実践、4-2 で解剖、4-6 で確認 |
| Vite、開発サーバ、プロキシ | 4-1 と 4-2 で解説 |
| P4-2 の `networks:` を分ける理由 | 4-1 と 4-4 で回収 |

### 📇 まとめカード

> **道具は箱の中、コードは手元。ブラウザは web にだけ頼み、web がサービス名で api を呼ぶ。**

**残った問い**: 設定が `compose.yaml` に直接書いてある。サービスが増えると、この塊はどこへ置けばよいのか。

---
▶ **次**: P4-5 Redis でカートを作る

---

## P4-5: Redis でカートを作る

**❓ この回の問い**: 前回の答えは「web がサービス名で api を呼ぶ」だった。サービスを足すのは簡単だと分かった。でも、`environment:` の塊がどんどん増えていく。
→ **設定を `compose.yaml` の外に出せないのか？ 外に出したとき、何が渡ったかをどう確かめるのか？**

**作るもの / 確かめること**: Redis にカートを保存し、API の設定をファイルに出す
**重要度**: 🔴 毎日使う — 設定ファイルの分け方と確かめ方は、どの Compose でも使うから
**前ステップとの接続**: P4-4 の `compose.yaml` に `redis` を足し、`api` の設定を `.env` に移す

### 5-0. このステップの初出トークン

**Docker**: `environment:` `env_file:` `docker compose config`
**Linux**: なし
**その他**: Redis、ハッシュ

### 5-1. 実践

> 🧒 **かみくだくと**: Redis（レディス）= メモリの上で動く、とても速い置き場。今回は「カート ID ごとに、商品番号と個数を書いたメモ」を置きます。ハッシュ = 1つの名前の下に「項目 → 値」を並べた表です。

カートの決まりは次のとおりです。

| 項目 | 決まり |
| --- | --- |
| カートの区別 | 画面が作った ID を、`X-Cart-Id` ヘッダで送る |
| Redis の置き方 | `cart:<ID>` というハッシュに、`商品番号 → 個数` を入れる |
| API | `GET /api/cart` で中身を返し、`POST /api/cart/items` で1つ足す |

#### API に Redis を足す

**ファイル**: `apps/api/pyproject.toml`（差分）

```diff
 dependencies = [
     "django>=5.2,<5.3",
     "django-ninja>=1.7,<1.8",
     "mysqlclient>=2.3,<2.4",
+    "redis>=8.1,<8.2",
 ]
```

ロックファイルを更新します（P3-4 と同じ方法）。`ec-api:step7` を、`uv` の入った道具として使います。

```bash
docker run --rm -i --entrypoint sh ec-api:step7 -c 'cat > pyproject.toml && uv lock -q && cat uv.lock' < apps/api/pyproject.toml > apps/api/uv.lock.new
mv apps/api/uv.lock.new apps/api/uv.lock
grep -A1 'name = "redis"$' apps/api/uv.lock
```

```text
name = "redis"
version = "8.1.0"
```

✅ 検証済み: uv 0.13.6

**ファイル**: `apps/api/src/config/settings.py`（末尾に追記）

```python
REDIS_URL = os.environ["REDIS_URL"]
```

**ファイル**: `apps/api/src/config/api.py`（全文を置き換え）

```python
import redis
from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja import Header, ModelSchema, NinjaAPI, Schema

from catalog.models import Product

api = NinjaAPI()
cart_store = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class ProductOut(ModelSchema):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "description"]


class CartItemIn(Schema):
    product_id: int
    quantity: int = 1


@api.get("/health")
def health(request):
    return {"status": "ok"}


@api.get("/products", response=list[ProductOut])
def list_products(request):
    return Product.objects.order_by("id")


@api.get("/products/{product_id}", response=ProductOut)
def get_product(request, product_id: int):
    return get_object_or_404(Product, id=product_id)


@api.get("/cart")
def get_cart(request, cart_id: str = Header(alias="X-Cart-Id")):
    items = cart_store.hgetall(f"cart:{cart_id}")
    return {"items": {int(k): int(v) for k, v in items.items()}}


@api.post("/cart/items")
def add_cart_item(request, item: CartItemIn, cart_id: str = Header(alias="X-Cart-Id")):
    get_object_or_404(Product, id=item.product_id)
    cart_store.hincrby(f"cart:{cart_id}", item.product_id, item.quantity)
    return get_cart(request, cart_id)
```

`hincrby` は、ハッシュの値に数を足す Redis の命令です。

#### 設定をファイルに出す

`apps/api/.env` を、Compose 用の中身に書き換えます。`DB_HOST` が `ec-db` から `db` に変わります。

**ファイル**: `apps/api/.env`（全文を置き換え）

```text
DB_HOST=db
DB_NAME=ec
DB_USER=ec
DB_PASSWORD=ec-pass
REDIS_URL=redis://redis:6379/0
```

`redis://redis:6379/0` の2つ目の `redis` は、サービス名です。

**ファイル**: `compose.yaml`（差分）

```diff
   api:
     build: ./apps/api
     depends_on:
       db:
         condition: service_healthy
+      redis:
+        condition: service_started
     ports:
       - "8000:8000"
-    environment:
-      DB_HOST: db
-      DB_NAME: ec
-      DB_USER: ec
-      DB_PASSWORD: ec-pass
+    env_file:
+      - ./apps/api/.env
     volumes:
       - ./apps/api/src:/app/src
     networks:
       - front
       - back

+  redis:
+    image: redis:8-alpine
+    networks:
+      - back
+
   web:
```

`condition: service_started` は、「コンテナが起動したら」という条件です。`depends_on: - api` と書いたときと同じ意味です。Redis は起動がとても速いので、ヘルスチェックを付けていません。

#### 渡る設定を確かめる: `docker compose config`

起動する前に、Compose が最終的にどう読んだかを見ます。

```bash
docker compose config api
```

```yaml
name: roadmap-sh-docker
services:
  api:
    build:
      context: /Users/you/.../roadmap-sh-docker/apps/api
      dockerfile: Dockerfile
    depends_on:
      db:
        condition: service_healthy
        required: true
      redis:
        condition: service_started
        required: true
    environment:
      DB_HOST: db
      DB_NAME: ec
      DB_PASSWORD: ec-pass
      DB_USER: ec
      REDIS_URL: redis://redis:6379/0
    （省略）
```

✅ 検証済み: Docker Compose v5.5.1。パスは書き換えた。

**`env_file:` と書いたのに、`environment:` として出ています。** Compose が `.env` を読み、中身を環境変数に展開しました。コンテナに渡るのはこの形です。

#### 起動して試す

```bash
docker compose up -d --build
sleep 4
curl -s localhost:5173/api/cart -H 'X-Cart-Id: demo'
curl -s -X POST localhost:5173/api/cart/items -H 'X-Cart-Id: demo' -H 'Content-Type: application/json' -d '{"product_id": 2}'
curl -s -X POST localhost:5173/api/cart/items -H 'X-Cart-Id: demo' -H 'Content-Type: application/json' -d '{"product_id": 2, "quantity": 2}'
```

```text
{"items": {}}
{"items": {"2": 1}}
{"items": {"2": 3}}
```

✅ 検証済み: Docker Compose v5.5.1 / Redis 8.10.3

Redis の中を直接見ます。

```bash
docker compose exec redis redis-cli HGETALL cart:demo
```

```text
2
3
```

✅ 検証済み: Redis 8.10.3

`2` が商品番号、`3` が個数です。

#### 画面にカートを足す

**ファイル**: `apps/web/src/App.jsx`（全文を置き換え）

```jsx
import { useEffect, useState } from "react";

// カートの ID をブラウザに保存し、次に開いたときも同じカートを使う
function getCartId() {
  let id = localStorage.getItem("cartId");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("cartId", id);
  }
  return id;
}

const headers = { "X-Cart-Id": getCartId(), "Content-Type": "application/json" };

export default function App() {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({});

  useEffect(() => {
    fetch("/api/products")
      .then((res) => res.json())
      .then(setProducts);
    fetch("/api/cart", { headers })
      .then((res) => res.json())
      .then((data) => setCart(data.items));
  }, []);

  function addToCart(productId) {
    fetch("/api/cart/items", {
      method: "POST",
      headers,
      body: JSON.stringify({ product_id: productId }),
    })
      .then((res) => res.json())
      .then((data) => setCart(data.items));
  }

  const count = Object.values(cart).reduce((sum, n) => sum + n, 0);

  return (
    <main>
      <h1>商品一覧</h1>
      <p>カート: {count} 点</p>
      <ul>
        {products.map((p) => (
          <li key={p.id}>
            {p.thumbnail_url && <img src={p.thumbnail_url} alt="" />}
            {p.name} — {p.price}円
            <button onClick={() => addToCart(p.id)}>カートに入れる</button>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

`thumbnail_url` の行は、P4-6 で使います。今は値が無いので、何も出ません。

`docker compose watch` を動かしていれば、保存しただけで画面に届きます。動かしていなければ `docker compose up -d --build` で作り直します。http://localhost:5173 で「カートに入れる」を押すと、`カート: 1 点` になります。再読み込みしても数は残ります。

✅ 検証済み: Docker Compose v5.5.1。ブラウザで押し、再読み込み後も `カート: 1 点` のままであることを確認した。

### 5-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `environment:` | 環境変数の指定 | `compose.yaml` に直接書いた `名前: 値` を、コンテナの環境変数にする。`-e` と同じ。P4-1 の宣言をここで回収する |
| `env_file:` | 環境変数ファイルの指定 | **Compose が** `up` のときにファイルを読み、中身を環境変数にする。`--env-file` と同じ |
| `docker compose config` | 設定の展開表示 | ファイルの読み込み・相対パスの解決・省略値の補完を全部済ませた、最終的な設定を出す。コンテナは作らない |

設定がコンテナに届くまでの順番です。

```text
apps/api/.env ──┐
                ├─ Compose が読んで 1つにまとめる ─→ docker compose config で見える
compose.yaml ───┘                                      │
                                                       ▼
                                          コンテナ api の環境変数
                                                       │ os.environ
                                                       ▼
                                                  Django の設定
```

**見てほしいところ**: `docker compose config` は、Compose がまとめた直後の姿を見せます。コンテナを起動しなくても、何が渡るかを確かめられます。

**名前が似ているもの**を並べます。

| | `env_file:` に書いた `apps/api/.env` | プロジェクト直下の `.env` |
| --- | --- | --- |
| 誰が読むか | Compose が、そのサービスのために読む | Compose が、`compose.yaml` を読む前に自動で読む |
| 何に使うか | コンテナの環境変数になる | `compose.yaml` の中の `${名前}` を置き換える |
| この教材で使うか | 使う | 使わない |

根拠: https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/

なぜを下っていきます。

```text
なぜ、設定を env_file に出すのか
  → compose.yaml には構成を、.env には値を置き、役割を分けたいから
      → なぜ、分けたいのか
          → 値は環境ごとに変わるが、構成は変わらないから
              → なぜ、docker compose config で確かめるのか
                  → 出したファイルが本当に読まれたかは、compose.yaml を見ても分からないから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | `dotenv` で `.env` を読む流れに近い。違うのは、読むのがアプリではなく Compose である点（P3-4 と同じ） |
| **なぜこの設計か** | 同じ `compose.yaml` を、`.env` を差し替えるだけで別の環境に使える |
| **ビルド時かランタイム時か** | ランタイム。`.env` を変えたら、イメージではなくコンテナを作り直す（`up -d` で入れ替わる） |
| **ホストからの見え方** | `docker compose config` と、`docker compose exec api env` |
| **失敗時の挙動** | `env_file:` のパスを間違えると、起動前に止まる。下の例 |

```text
env file /Users/you/.../roadmap-sh-docker/apps/api/.envv not found: stat ...: no such file or directory
```

✅ 検証済み: Docker Compose v5.5.1。パスを `./apps/api/.envv` にして起こした。

### 5-3. 🐧 Linux注

なし。

### 5-4. 解説 — なぜこうするか

カートを DB ではなく Redis に置いたのは、カートが「すぐ変わり、消えても困りが小さい」データだからです。ここで、P4-2 の問いがもう一度出てきます。**Redis のデータは、`down` で残るでしょうか。** 宿題 Lv1 で確かめます。

🧠 **Docker の考え方**: 構成は `compose.yaml`、値は `.env`。そして、渡る形は `docker compose config` で見る。

### 5-5. 🔓 教材用の簡略化

> 🔓 **教材用の簡略化**: Redis にパスワードを付けていません。`ports:` を書いていないので、この Mac の外からは届きません。
> **本番では**: 認証を有効にし、つなぐネットワークも絞ります。
> 根拠: https://redis.io/docs/latest/operate/oss_and_stack/management/security/

### 5-6. 🔮 予測 → 動作確認

**問い**: `X-Cart-Id` を付けずに `GET /api/cart` を呼ぶと、何が返るでしょうか。

```bash
curl -s localhost:5173/api/cart
```

```text
{"detail": [{"type": "missing", "loc": ["header", "X-Cart-Id"], "msg": "Field required"}]}
```

✅ 検証済み: Docker Compose v5.5.1

ヘッダが無いと、Django Ninja が 422 で断ります。存在しない商品番号を足したときは、404 になります。

### 5-7. ✅ 想起チェック

1. `env_file:` に書いたファイルを読むのは、Compose とアプリのどちらですか
2. `docker compose config` は、どんなときに使いますか
3. `env_file:` の `apps/api/.env` と、プロジェクト直下の `.env` の違いは何ですか

<details><summary>答え</summary>

1. Compose
2. ファイルに分けた設定が、最終的にどう読まれたかを、起動する前に確かめたいとき
3. `env_file:` のものはコンテナの環境変数になる。プロジェクト直下の `.env` は、`compose.yaml` の `${名前}` を置き換えるのに使われる

</details>

### 5-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `environment:` | 5-2 で解剖。P4-1 の宣言を回収 |
| `env_file:` | 5-1 で実践、5-2 で解剖 |
| `docker compose config` | 5-1 で実践、5-2 で解剖 |
| Redis、ハッシュ | 5-1 で解説 |

### 📇 まとめカード

> **値は `.env`、構成は `compose.yaml`。渡る形は `docker compose config` で見る。**

**残った問い**: 画像を受け取ったら、縮めてサムネイルを作りたい。でも、重い処理で API の応答を待たせたくない。

---
▶ **次**: P4-6 ワーカーでサムネイルを作る

---

## P4-6: ワーカーでサムネイルを作る

**❓ この回の問い**: 前回の答えは「サービスを足し、設定を外に出せる」だった。次は重い処理だ。
→ **重い処理を、API とは別のコンテナに任せられるのか？ そのコンテナは、どのイメージから作るのか？**

**作るもの / 確かめること**: 同じイメージを別のコマンドで動かし、画像を volume で共有する
**重要度**: 🔴 毎日使う — 「同じイメージで役割だけ変える」は、Compose でよく出る形だから
**前ステップとの接続**: P4-5 の `compose.yaml` に `worker` を足す

### 6-0. このステップの初出トークン

**Docker**: `command:` `docker compose logs -f` `stop_grace_period`
**Linux**: `/proc/1/cmdline`
**その他**: ワーカー、タスクキュー、Celery

### 6-1. 実践

> 🧒 **かみくだくと**: ワーカー = 裏で仕事をこなす係。タスクキュー = 仕事の受付箱。API は「サムネイルを作って」というメモを受付箱（Redis）に入れて、すぐ返事をします。ワーカーが箱からメモを取り出して、仕事をします。Celery（セロリ）は、この仕組みを Python で作る部品です。

```text
curl（画像）
   │
   ▼
api ──① 画像を media に保存
   │──② 「サムネイルを作って」を Redis に入れる
   │──③ すぐ {"status": "queued"} を返す
   ▼
redis（受付箱）
   │
   ▼
worker ──④ メモを取り出す
       ──⑤ media の画像を読み、縮めて media に書く
```

**見てほしいところ**: `api` と `worker` は、同じ `media` を見ています。だから、`api` が置いた画像を `worker` が読めます。

#### API に部品とコードを足す

**ファイル**: `apps/api/pyproject.toml`（差分）

```diff
     "mysqlclient>=2.3,<2.4",
     "redis>=8.1,<8.2",
+    "celery[redis]>=5.6,<5.7",
+    "pillow>=13.0,<13.1",
 ]
```

```bash
docker run --rm -i --entrypoint sh ec-api:step7 -c 'cat > pyproject.toml && uv lock -q && cat uv.lock' < apps/api/pyproject.toml > apps/api/uv.lock.new
mv apps/api/uv.lock.new apps/api/uv.lock
grep -A1 -E 'name = "(celery|pillow)"$' apps/api/uv.lock
```

```text
name = "celery"
version = "5.6.3"
--
name = "pillow"
version = "13.0.0"
```

✅ 検証済み: uv 0.13.6

Pillow は、画像を扱う Python の部品です。

| ファイル | 役割 |
| --- | --- |
| `src/catalog/models.py` | 商品に、画像とサムネイルの列を足す |
| `src/config/celery.py` | Celery の設定 |
| `src/config/__init__.py` | Django の起動時に Celery を読み込む |
| `src/catalog/tasks.py` | サムネイルを作る仕事 |
| `src/config/settings.py` | 受付箱の場所と、画像の置き場所 |
| `src/config/urls.py` | 開発中に、画像を配る |
| `src/config/api.py` | 画像を受け取る API |

**ファイル**: `apps/api/src/catalog/models.py`（差分）

```diff
     description = models.TextField(blank=True)
+    image = models.ImageField(upload_to="products/", blank=True)
+    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True)
```

**ファイル**: `apps/api/src/config/celery.py`（新規・全文）

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
# settings.py の CELERY_ で始まる設定を読む
app.config_from_object("django.conf:settings", namespace="CELERY")
# INSTALLED_APPS の各アプリから tasks.py を探す
app.autodiscover_tasks()
```

**ファイル**: `apps/api/src/config/__init__.py`（空のファイルを置き換え・全文）

```python
from .celery import app as celery_app

__all__ = ["celery_app"]
```

**ファイル**: `apps/api/src/catalog/tasks.py`（新規・全文）

```python
import os
import time
from io import BytesIO

from celery import shared_task
from django.core.files.base import ContentFile
from PIL import Image

from catalog.models import Product


@shared_task
def make_thumbnail(product_id):
    # 重い処理の代わりに待つ。秒数は環境変数で変えられる
    time.sleep(int(os.environ.get("THUMBNAIL_DELAY", "0")))
    product = Product.objects.get(id=product_id)
    with Image.open(product.image.path) as img:
        img.thumbnail((200, 200))
        buffer = BytesIO()
        img.convert("RGB").save(buffer, "JPEG")
    product.thumbnail.save(f"{product_id}.jpg", ContentFile(buffer.getvalue()))
```

`THUMBNAIL_DELAY` は、6-6 で「時間のかかる仕事」を再現するためのものです。ふだんは 0 秒です。

**ファイル**: `apps/api/src/config/settings.py`（末尾に追記）

```python
CELERY_BROKER_URL = os.environ["CELERY_BROKER_URL"]

MEDIA_ROOT = "/app/media"
MEDIA_URL = "/media/"
```

> 🧒 **かみくだくと**: ブローカー = 受付箱の係。Celery では Redis がこの役をします。

**ファイル**: `apps/api/src/config/urls.py`（全文を置き換え）

```python
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from config.api import api

urlpatterns = [
    path("api/", api.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**ファイル**: `apps/api/src/config/api.py`（差分）

```diff
-from ninja import Header, ModelSchema, NinjaAPI, Schema
+from ninja import File, Header, ModelSchema, NinjaAPI, Schema, UploadedFile

 from catalog.models import Product
+from catalog.tasks import make_thumbnail
```

```diff
 class ProductOut(ModelSchema):
     class Meta:
         model = Product
         fields = ["id", "name", "price", "description"]
+
+    thumbnail_url: str | None
+
+    @staticmethod
+    def resolve_thumbnail_url(obj):
+        return obj.thumbnail.url if obj.thumbnail else None
```

`@api.get("/cart")` の**前**に、次の関数を足します。

```python
@api.post("/products/{product_id}/image")
def upload_image(request, product_id: int, image: File[UploadedFile]):
    product = get_object_or_404(Product, id=product_id)
    product.image.save(image.name, image)
    # 重い処理は worker に任せ、すぐに返す
    make_thumbnail.delay(product.id)
    return {"status": "queued"}
```

`make_thumbnail.delay(...)` が、受付箱にメモを入れる1行です。その場でサムネイルは作りません。

**ファイル**: `apps/api/.env`（末尾に追記）

```text
CELERY_BROKER_URL=redis://redis:6379/1
```

カートは Redis の 0 番、受付箱は 1 番を使います。番号で置き場を分けています。

**ファイル**: `apps/web/vite.config.js`（差分）

```diff
       "/api": "http://api:8000",
+      "/media": "http://api:8000",
```

#### compose.yaml に worker を足す

**ファイル**: `compose.yaml`（全文を置き換え）

```yaml
services:
  db:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: root-pass
      MYSQL_DATABASE: ec
      MYSQL_USER: ec
      MYSQL_PASSWORD: ec-pass
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]
      interval: 2s
      timeout: 5s
      retries: 30
    volumes:
      - db-data:/var/lib/mysql
    networks:
      - back

  api:
    build: ./apps/api
    image: ec-api:dev
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "8000:8000"
    env_file:
      - ./apps/api/.env
    volumes:
      - ./apps/api/src:/app/src
      - media:/app/media
    networks:
      - front
      - back

  worker:
    build: ./apps/api
    image: ec-api:dev
    command: [".venv/bin/celery", "--workdir", "src", "-A", "config", "worker", "--loglevel", "info"]
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    env_file:
      - ./apps/api/.env
    volumes:
      - ./apps/api/src:/app/src
      - media:/app/media
    networks:
      - back

  redis:
    image: redis:8-alpine
    networks:
      - back

  web:
    build: ./apps/web
    ports:
      - "5173:5173"
    depends_on:
      - api
    networks:
      - front
    develop:
      watch:
        - action: sync
          path: ./apps/web/src
          target: /app/src
        - action: rebuild
          path: ./apps/web/package.json

volumes:
  db-data:
  media:

networks:
  front:
  back:
```

変えたところは4つです。

- `api` と `worker` の両方に `image: ec-api:dev` を書いた。同じ名前のイメージを使う
- `worker` に `command:` を書いた。イメージの `CMD`（`runserver`）の代わりに、Celery を起動する
- `api` と `worker` の両方に `media:/app/media` をつないだ
- いちばん外の `volumes:` に `media` を足した

```bash
docker compose up -d --build
sleep 5
docker compose exec api .venv/bin/python src/manage.py makemigrations catalog
docker compose exec api .venv/bin/python src/manage.py migrate
docker compose ps --format '{{.Service}} {{.Image}} {{.Status}}'
```

```text
Migrations for 'catalog':
  src/catalog/migrations/0002_product_image_product_thumbnail.py
    + Add field image to product
    + Add field thumbnail to product
（省略）
  Applying catalog.0002_product_image_product_thumbnail... OK
api ec-api:dev Up 6 seconds
db mysql:8.4 Up 3 minutes (healthy)
redis redis:8-alpine Up About a minute
web roadmap-sh-docker-web Up 5 seconds
worker ec-api:dev Up 6 seconds
```

✅ 検証済み: Docker Compose v5.5.1 / Celery 5.6.3

**`api` と `worker` の IMAGE 列が、どちらも `ec-api:dev` です。**

#### ログを追いかける: `docker compose logs -f`

別のターミナルで、`worker` のログを流し続けます。

```bash
docker compose logs -f worker
```

```text
worker-1  | [... INFO/MainProcess] Connected to redis://:**@redis:6379/1
worker-1  | [... INFO/MainProcess] celery@5b314328ce28 ready.
```

✅ 検証済み: Docker Compose v5.5.1。時刻は省略した。`:**@` は、Celery がパスワードの場所を伏せて表示したもの。今回はパスワードを付けていない。

`-f` は、新しい行が出るたびに表示し続ける指定です。Ctrl+C で止めます。ログの頭の `worker-1  |` は、どのコンテナの行かを示します。サービス名を書かなければ、全サービスのログが混ざって流れます。

#### 画像を送る

送る画像を作ります。Pillow が入った `api` のコンテナで作り、この Mac に受け取ります。

```bash
docker compose exec -T api .venv/bin/python -c "import sys; from PIL import Image; Image.new('RGB', (1200, 800), 'tan').save(sys.stdout.buffer, 'JPEG')" > sample.jpg
file sample.jpg
```

```text
sample.jpg: JPEG image data, JFIF standard 1.01, ... 1200x800, components 3
```

✅ 検証済み: Docker Compose v5.5.1

`-T` は、コンテナの出力をそのまま受け取る指定です。付けないと、画面に表示するための変換が混ざり、画像が壊れることがあります。

```bash
curl -s -F image=@sample.jpg localhost:5173/api/products/1/image
sleep 2
curl -s localhost:5173/api/products/1
```

```text
{"status": "queued"}
{"thumbnail_url": "/media/thumbnails/1.jpg", "id": 1, "name": "...", "price": 2800, "description": "..."}
```

✅ 検証済み: Docker Compose v5.5.1 / Pillow 13.0.0

`logs -f` のターミナルには、次の2行が出ます。

```text
worker-1  | [... INFO/MainProcess] Task catalog.tasks.make_thumbnail[ffb1fcb3-...] received
worker-1  | [... INFO/ForkPoolWorker-7] Task catalog.tasks.make_thumbnail[ffb1fcb3-...] succeeded in 0.05s: None
```

✅ 検証済み: Celery 5.6.3

ブラウザで http://localhost:5173 を再読み込みすると、マグカップの横に茶色の四角（サムネイル）が出ます。

✅ 検証済み: Docker Compose v5.5.1。ブラウザで表示を確認した。

### 6-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `command:` | コマンドの上書き | **ランタイム**に、イメージの `CMD` を置き換える。`docker run イメージ 引数...` の引数と同じ（P2-5）。`ENTRYPOINT` はそのまま |
| `image: ec-api:dev`（`build:` と一緒） | ビルド結果の名前 | ビルドしたイメージに、この名前を付ける。2つのサービスで同じ名前にすると、同じイメージを使う |
| `docker compose logs -f` | ログの追跡 | コンテナの標準出力と標準エラーを、流れ続けるように表示する。`docker logs -f` のサービス版 |
| `stop_grace_period` | 停止の猶予 | 6-6 で扱う |

同じイメージが、2つの役割になる様子です。

```text
                 イメージ ec-api:dev
         ENTRYPOINT ["./entrypoint.sh"]
         CMD [".venv/bin/python", "src/manage.py", "runserver", ...]
                │                                  │
     api（CMD をそのまま使う）        worker（command: で CMD を置き換え）
                ▼                                  ▼
  ./entrypoint.sh .venv/bin/python     ./entrypoint.sh .venv/bin/celery
    src/manage.py runserver ...          --workdir src -A config worker ...
```

**見てほしいところ**: `ENTRYPOINT` の `./entrypoint.sh` は、両方で動きます。`exec "$@"`（P2-5）があるので、どちらも本体が PID 1 になります。

`python:3.13-slim` には `ps` が入っていません。PID 1 のコマンドは、`/proc/1/cmdline` で見られます。

```bash
docker compose exec worker cat /proc/1/cmdline | tr '\0' ' '; echo
```

```text
/app/.venv/bin/python .venv/bin/celery --workdir src -A config worker --loglevel info
```

✅ 検証済み: Docker Compose v5.5.1

PID 1 は `celery` です。`celery` は Python で書かれたプログラムなので、頭に `python` が付いています。`entrypoint.sh` は PID 1 に残っていません。

> 🐧 **Linux注**: `/proc/1/cmdline` には、PID 1 の起動コマンドが入っています。区切りが見えない文字なので、`tr '\0' ' '` で空白に置き換えています。

なぜを下っていきます。

```text
なぜ、worker は api と同じイメージでよいのか
  → 仕事のコード（tasks.py）も、DB の設定も、api と同じだから
      → なぜ、同じイメージで別の動きができるのか
          → イメージは「中身」、command は「何を起動するか」で、別々に決められるから
              → なぜ、api が保存した画像を worker が読めるのか
                  → 2つのコンテナが、同じ volume media をマウントしているから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | `package.json` の `scripts` に `dev` と `worker` を並べ、同じコードを別の入口で起動するのに近い |
| **なぜこの設計か** | イメージを1つにすると、api と worker のコードの版がずれない |
| **ビルド時かランタイム時か** | `command:` はランタイム。イメージは作り直さない |
| **ホストからの見え方** | `docker compose ps` の IMAGE 列が同じ。`docker image ls ec-api` は1行だけ |
| **失敗時の挙動** | `worker` に `media` をつなぎ忘れると、`worker` のログに `FileNotFoundError` が出て、サムネイルができない |

✅ 検証済み: Docker Compose v5.5.1。`worker` から `media:/app/media` を外して起こした。

> 💡補足: `up --build` の出力に、`Image ec-api:dev Built` が2回出ます。Compose は2つのサービスを、それぞれビルドします。中身は同じなので、2回目はキャッシュですぐ終わります。

### 6-3. 🐧 Linux注

`/proc/1/cmdline` は 6-2 で説明しました。

### 6-4. 解説 — なぜこうするか

`api` は `{"status": "queued"}` を、サムネイルを待たずに返しました。重い処理を `worker` に回すと、利用者を待たせずに済みます。そして、`worker` だけを増やしたり止めたりできます。

`worker` は `front` につないでいません。画面から呼ばれることはないからです。

🧠 **Docker の考え方**: イメージは中身、`command:` は役割。1つの中身を、役割ごとに別のコンテナで動かす。

### 6-5. 🔓 教材用の簡略化

> 🔓 **教材用の簡略化**: 画像を Django の `runserver` で配っています。`runserver` は開発用で、`static()` は `DEBUG = True` のときにだけ働きます。worker も root で動いています。
> **本番では**: P6-1 で Nginx に配らせ、P6-2 で root をやめます。
> 根拠: https://docs.djangoproject.com/en/5.2/howto/static-files/#serving-files-uploaded-by-a-user-during-development

### 6-6. 🔮 予測 → 動作確認

**問い**: 仕事の途中で `docker compose stop worker` を打つと、仕事は終わるでしょうか。

時間のかかる仕事を再現するため、`worker` に15秒待たせます。

**ファイル**: `compose.yaml`（`worker` に差分）

```diff
     command: [".venv/bin/celery", "--workdir", "src", "-A", "config", "worker", "--loglevel", "info"]
+    environment:
+      THUMBNAIL_DELAY: 15
```

```bash
docker compose up -d worker
sleep 4
curl -s -F image=@sample.jpg localhost:5173/api/products/2/image
sleep 2
time docker compose stop worker
docker compose ps -a --format '{{.Service}} {{.Status}}' | grep worker
curl -s localhost:5173/api/products/2 | grep -o '"thumbnail_url": [^,]*'
```

```text
{"status": "queued"}
 Container roadmap-sh-docker-worker-1 Stopped
docker compose stop worker  ... 3.0 total
worker Exited (137) Less than a second ago
"thumbnail_url": null
```

✅ 検証済み: Docker Compose v5.5.1

**仕事は終わりませんでした。** `Exited (137)` は、SIGKILL で強制終了された印です（P2-5）。ログには `Warm shutdown` が出ています。Celery は SIGTERM を受け取り、仕事を終えてから止まろうとしました。でも、待ち時間が先に切れました。

> 💡補足: 待ち時間は、公式では既定 10 秒です。この検証環境では、P2-5 と同じく約3秒で SIGKILL に進みました。どちらでも、15秒の仕事には足りません。

`stop_grace_period` で、待ち時間を延ばします。

**ファイル**: `compose.yaml`（`worker` に差分）

```diff
     environment:
       THUMBNAIL_DELAY: 15
+    stop_grace_period: 30s
```

```bash
docker compose up -d worker
sleep 4
curl -s -F image=@sample.jpg localhost:5173/api/products/2/image
sleep 2
time docker compose stop worker
docker compose ps -a --format '{{.Service}} {{.Status}}' | grep worker
curl -s localhost:5173/api/products/2 | grep -o '"thumbnail_url": [^,]*'
```

```text
{"status": "queued"}
 Container roadmap-sh-docker-worker-1 Stopped
docker compose stop worker  ... 15.0 total
worker Exited (0) Less than a second ago
"thumbnail_url": "/media/thumbnails/2.jpg"
```

✅ 検証済み: Docker Compose v5.5.1 / Celery 5.6.3

**仕事を終えてから、`Exited (0)` で止まりました。** ログにも `succeeded in 15.06s` が出ます。

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `stop_grace_period: 30s` | 停止の猶予 | `stop` や `down` で SIGTERM を送ったあと、SIGKILL まで最大30秒待つ。`docker stop -t 30` と同じ |

確かめたら、`environment:` と `THUMBNAIL_DELAY: 15` の2行を消します。`stop_grace_period: 30s` は残します。最後に `docker compose up -d worker` で入れ替えます。

### 6-7. ✅ 想起チェック

1. `api` と `worker` が同じイメージなのに、違う動きをするのは、なぜですか
2. `api` が保存した画像を、`worker` が読めるのは、なぜですか
3. `worker` が `Exited (137)` で止まり、仕事が終わっていませんでした。何を延ばしますか

<details><summary>答え</summary>

1. `worker` の `command:` が、イメージの `CMD` を置き換えているから
2. 2つのコンテナが、同じ volume `media` を `/app/media` にマウントしているから
3. `stop_grace_period`。SIGTERM のあと、SIGKILL までの待ち時間

</details>

### 6-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `command:` | 6-1 で実践、6-2 で解剖 |
| `docker compose logs -f` | 6-1 で実践、6-2 で解剖 |
| `stop_grace_period` | 6-6 で実践と解剖 |
| ワーカー、タスクキュー、Celery | 6-1 で解説 |
| `/proc/1/cmdline` | 6-2 の Linux注 |

### 📇 まとめカード

> **同じイメージを、`command:` で別の役割にする。止めるときは、仕事が終わるまで待たせる。**

**残った問い**: EC は1回の `up` で動いた。でも、`ec-api:dev` は 600MB を超えている。`gcc` も入ったままだ。本番に出すには重すぎないか。

---

## P4 のなぜなぜの鎖

```text
長い docker run の束を、どうまとめるのか
  → compose.yaml に書く。サービス名で呼び合える
      ↓ down するとデータが消えた。倉庫はどこに書くのか
  → いちばん外で volume を宣言し、サービスでつなぐ
      ↓ 1回の up で、正しい順に起動できないのか
  → ヘルスチェックで「使える」を教え、condition で待たせる
      ↓ Node.js が無いのに、画面を開発できるのか
  → 道具は箱の中。watch で手元の変更を写す。web がサービス名で api を呼ぶ
      ↓ 増える設定を、どこに置くのか
  → 値は .env へ。渡る形は docker compose config で見る
      ↓ 重い処理を、別の箱に任せられるのか
  → 同じイメージを command: で worker にし、volume で画像を共有する
      ↓ では、この重いイメージをどう軽くするのか
```

---

## ▶ ここで PJ2 に取り組む

P4 の6ステップはここまで。**次は自分で組む番**です。

**前提チェック**（すべて ✅ なら着手してよい）

- [ ] `compose.yaml` に `services:` を書き、`docker compose up -d` で起動できる（P4-1）
- [ ] `down` と `down -v` の違いを説明できる（P4-2）
- [ ] `depends_on` だけでは DB の準備を待てない理由を説明できる（P4-3）
- [ ] `docker compose exec` と `docker compose config` で、コンテナと設定を確かめられる（P4-4、P4-5）

1つでも ✅ にできない項目があれば、**該当ステップの 🔬 仕組み解剖だけ**読み返してから着手します。

---

## PJ2: Multi-Container Application

出典: https://roadmap.sh/projects/multi-container-service

### 1. 要件

- Todo を扱う API を作る。認証は無し
- 次の5つの操作を持つ

| 操作 | メソッドとパス |
| --- | --- |
| 一覧 | `GET /todos` |
| 作成 | `POST /todos` |
| 1件取得 | `GET /todos/{id}` |
| 更新 | `PUT /todos/{id}` |
| 削除 | `DELETE /todos/{id}` |

- データは MySQL に保存する
- API と MySQL を、`compose.yaml` 1つで起動する
- API は、この Mac の **3000 番**で受け付ける
- コンテナを止めて起動し直しても、Todo が残る
- 任意: コードを変えると、API が自動で再起動する
- 置き場所は `projects/multi-container-service/`

🔄 **素材からの変更**: Node.js + Express → Django + Django Ninja / MongoDB + Mongoose → MySQL + Django の ORM / nodemon → `runserver` の自動再読み込み / `docker-compose.yml` → `compose.yaml`。出典の Part 2（Terraform と Ansible）は扱いません。Part 3（CI/CD）とボーナス（Nginx）は P6〜P7 で扱います（`docs/00-plan.md` §6）。

### 2. このフェーズで学んだどれを使うか

| 使う | ステップ |
| --- | --- |
| `Dockerfile`（`apt-get` を含む） | P2 全体、P3-4 |
| `ENTRYPOINT` と `exec "$@"` | P2-5 |
| `services:` `ports:` | P4-1 |
| `volumes:`（名前付き） | P4-2 |
| `healthcheck` と `condition: service_healthy` | P4-3 |
| `build:` と `docker compose exec` | P4-4 |
| `env_file:` と `docker compose config` | P4-5 |
| bind mount（任意課題） | P3-2 |

**不要なもの**: `networks:`（サービスが2つで、分ける理由がない）/ `watch`（Python は bind mount で足りる）/ `command:` と `stop_grace_period`（ワーカーがない）/ Redis。

### 3. 判定基準

1. `docker compose up -d --build` の1回だけで、`docker compose ps` に `api` と `db (healthy)` が並ぶ
2. `curl -s -X POST localhost:3000/todos -H 'Content-Type: application/json' -d '{"title": "test"}'` が `"id"` を含む JSON を返し、HTTP の番号が 201
3. `PUT` で `"completed": true` にしたあと、`GET /todos/{id}` が `"completed": true` を返す
4. `DELETE` が 204 を返し、そのあとの `GET /todos/{id}` が 404 を返す
5. `docker compose down` → `docker compose up -d` のあと、`GET /todos` に Todo が残っている
6. 任意: `src/` のコードを変えると、作り直さずに API の応答が変わる

### 4. 詰まったときの確認順

1. **設定の層**: `docker compose config` で、ポート・環境変数・volume が意図どおりか
2. **起動の層**: `docker compose ps -a` で、どのサービスが `Exited` か、`(healthy)` になっているか
3. **プロセスの層**: `docker compose logs api` の最後のエラーは何か。`KeyError`（環境変数）/ `2005`（名前）/ `2002`（DB の準備）/ `1146`（表が無い）のどれか
4. **ネットワークの層**: `docker compose exec api getent hosts db` で名前が引けるか
5. **データの層**: `docker compose exec db mysql -u... -p... <DB名> -e 'SHOW TABLES;'` で表があるか

### 5. ヒント

- `apps/api/` を写して始めると早いです。ただし、`catalog` や Redis など、使わないものは消します
- 表を作るのを、起動のたびに自動にする方法があります。`entrypoint.sh` は、`exec "$@"` の**前に**好きなコマンドを書けます
- `makemigrations` で作ったファイルは、リポジトリに残す必要があります。コンテナの中で作ったファイルを、どうすれば Mac に残せるかを思い出します（P3-4）

<details><summary>解答例（自力で組んでから開く）</summary>

**実行場所**: `projects/multi-container-service/`

```text
projects/multi-container-service/
├── compose.yaml
├── db.env
├── api.env
├── Dockerfile
├── .dockerignore
├── entrypoint.sh
├── pyproject.toml
├── uv.lock
└── src/
    ├── manage.py
    ├── config/
    │   ├── __init__.py   （空）
    │   ├── settings.py
    │   ├── urls.py
    │   └── api.py
    └── todos/
        ├── __init__.py   （空）
        ├── models.py
        └── migrations/
            └── __init__.py （空）
```

**ファイル**: `compose.yaml`

```yaml
services:
  db:
    image: mysql:8.4
    env_file:
      - ./db.env
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]
      interval: 2s
      timeout: 5s
      retries: 30
    volumes:
      - db-data:/var/lib/mysql

  api:
    build: .
    ports:
      - "3000:8000"
    env_file:
      - ./api.env
    volumes:
      - ./src:/app/src
    depends_on:
      db:
        condition: service_healthy

volumes:
  db-data:
```

**ファイル**: `db.env`

```text
MYSQL_ROOT_PASSWORD=root-pass
MYSQL_DATABASE=todo
MYSQL_USER=todo
MYSQL_PASSWORD=todo-pass
```

**ファイル**: `api.env`

```text
DB_HOST=db
DB_NAME=todo
DB_USER=todo
DB_PASSWORD=todo-pass
```

> 🔓 **教材用の簡略化**: パスワードを `db.env` と `api.env` に書き、リポジトリに入れています。
> **本番では**: P6-3 で secrets を使います。
> 根拠: https://docs.docker.com/compose/how-tos/use-secrets/

**ファイル**: `Dockerfile`（`apps/api/Dockerfile` と同じ）

```dockerfile
FROM python:3.13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install uv==0.13.6
COPY pyproject.toml uv.lock ./
RUN uv sync --locked
COPY . .
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD [".venv/bin/python", "src/manage.py", "runserver", "0.0.0.0:8000"]
```

**ファイル**: `.dockerignore`

```text
.venv
__pycache__
.env
Dockerfile
.dockerignore
compose.yaml
```

**ファイル**: `entrypoint.sh`（作ったあと `chmod +x entrypoint.sh`）

```sh
#!/bin/sh
set -e
# 起動のたびに表を最新にしてから、本体を PID 1 にする
.venv/bin/python src/manage.py migrate --noinput
exec "$@"
```

`set -e` は、途中のコマンドが失敗したらそこで止める指定です。表が作れなければ、API を起動しません。

**ファイル**: `pyproject.toml`

```toml
[project]
name = "todo-api"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "django>=5.2,<5.3",
    "django-ninja>=1.7,<1.8",
    "mysqlclient>=2.3,<2.4",
]
```

**ファイル**: `src/manage.py`

```python
import os
import sys

from django.core.management import execute_from_command_line

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
execute_from_command_line(sys.argv)
```

**ファイル**: `src/config/settings.py`

```python
import os

SECRET_KEY = "dev-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = ["todos"]
MIDDLEWARE = []
ROOT_URLCONF = "config.urls"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": os.environ["DB_HOST"],
        "PORT": "3306",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
    }
}
```

**ファイル**: `src/config/urls.py`

```python
from django.urls import path

from config.api import api

urlpatterns = [
    path("", api.urls),
]
```

**ファイル**: `src/todos/models.py`

```python
from django.db import models


class Todo(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
```

**ファイル**: `src/config/api.py`

```python
from django.shortcuts import get_object_or_404
from ninja import ModelSchema, NinjaAPI, Schema

from todos.models import Todo

api = NinjaAPI()


class TodoIn(Schema):
    title: str
    completed: bool = False


class TodoOut(ModelSchema):
    class Meta:
        model = Todo
        fields = ["id", "title", "completed"]


@api.get("/todos", response=list[TodoOut])
def list_todos(request):
    return Todo.objects.order_by("id")


@api.post("/todos", response={201: TodoOut})
def create_todo(request, data: TodoIn):
    return 201, Todo.objects.create(**data.dict())


@api.get("/todos/{todo_id}", response=TodoOut)
def get_todo(request, todo_id: int):
    return get_object_or_404(Todo, id=todo_id)


@api.put("/todos/{todo_id}", response=TodoOut)
def update_todo(request, todo_id: int, data: TodoIn):
    todo = get_object_or_404(Todo, id=todo_id)
    for key, value in data.dict().items():
        setattr(todo, key, value)
    todo.save()
    return todo


@api.delete("/todos/{todo_id}", response={204: None})
def delete_todo(request, todo_id: int):
    get_object_or_404(Todo, id=todo_id).delete()
    return 204, None
```

**手順**

```bash
mkdir -p src/config src/todos/migrations
touch src/config/__init__.py src/todos/__init__.py src/todos/migrations/__init__.py
# ここまでで上のファイルを置く
docker run --rm -i --entrypoint sh ec-api:dev -c 'cd /tmp && cat > pyproject.toml && uv lock -q && cat uv.lock' < pyproject.toml > uv.lock
docker compose up -d --build
docker compose exec api .venv/bin/python src/manage.py makemigrations todos
docker compose restart api
```

最初の起動では `migrations/` が空なので、`entrypoint.sh` の `migrate` は何もしません。`makemigrations` が作ったファイルは、bind mount で `src/todos/migrations/` に残ります。`restart` で `entrypoint.sh` がもう一度動き、表が作られます。

```text
Migrations for 'todos':
  src/todos/migrations/0001_initial.py
    + Create model Todo
```

**判定**

```bash
B=localhost:3000/todos
curl -s -X POST $B -H 'Content-Type: application/json' -d '{"title": "牛乳を買う"}' -w ' %{http_code}\n'
curl -s -X POST $B -H 'Content-Type: application/json' -d '{"title": "Write report"}' -w ' %{http_code}\n'
curl -s -X PUT $B/1 -H 'Content-Type: application/json' -d '{"title": "牛乳を買う", "completed": true}'; echo
curl -s -X DELETE $B/2 -w '%{http_code}\n'
curl -s -o /dev/null -w '%{http_code}\n' $B/2
docker compose down
docker compose up -d
sleep 4
curl -s $B; echo
```

```text
{"id": 1, "title": "...", "completed": false} 201
{"id": 2, "title": "Write report", "completed": false} 201
{"id": 1, "title": "...", "completed": true}
204
404
[{"id": 1, "title": "...", "completed": true}]
```

✅ 検証済み: Docker Compose v5.5.1 / Django 5.2.18 / MySQL 8.4.13。日本語の部分は省略した。

**片付け**

```bash
docker compose down -v --rmi local
```

`--rmi local` は、`build:` で作ったイメージも消す指定です。

</details>

---

## P4 フェーズ末パック（M2）

### ブランクページ再現

> ✍️ **ブランクページ**: リポジトリの `compose.yaml` を閉じて、白紙から再現してください。
> 思い出せなかった行に印を付け、**その行の仕組み解剖だけ**読み返します。

特に、次の4か所を書けるかを確かめます。

1. `db` の `healthcheck` と、`api` の `depends_on` の `condition`
2. いちばん外の `volumes:` と `networks:`
3. `worker` の `command:`
4. `web` の `develop.watch`

**翌日に行うことをすすめます。** 直後は短期記憶で再現できてしまい、定着の負荷が足りません。

### 宿題

#### Lv1 基礎確認: カートを `down` で消さない

**課題**

- いまの `compose.yaml` で、カートに何か入れてから `docker compose down` → `docker compose up -d` をする。カートがどうなるかを確かめる
- `redis` に volume をつなぎ、`down` → `up` のあとも、カートが残るようにする

**ヒント**: `redis:8-alpine` は `/data` にデータを書きます。P4-2 と同じ2か所を書き足します。

**判定基準**: `down` → `up` のあと、`curl -s localhost:5173/api/cart -H 'X-Cart-Id: demo'` が、`down` の前と同じ中身を返す。

<details><summary>解答例</summary>

**ファイル**: `compose.yaml`（差分）

```diff
   redis:
     image: redis:8-alpine
+    volumes:
+      - redis-data:/data
     networks:
       - back
```

```diff
 volumes:
   db-data:
   media:
+  redis-data:
```

```bash
docker compose up -d
sleep 3
curl -s -X POST localhost:5173/api/cart/items -H 'X-Cart-Id: demo' -H 'Content-Type: application/json' -d '{"product_id": 3}'
docker compose down
docker compose up -d
sleep 4
curl -s localhost:5173/api/cart -H 'X-Cart-Id: demo'
docker compose logs redis | grep 'DB loaded'
```

```text
{"items": {"3": 1}}
（省略）
{"items": {"3": 1}}
redis-1  | 1:M ... * DB loaded from disk: 0.000 seconds
```

✅ 検証済み: Docker Compose v5.5.1 / Redis 8.10.3

volume が無いときは、`down` → `up` のあと `{"items": {}}` になります。`redis:8-alpine` には `mysql:8.4` のような volume の指定が無いので、データは書き込み層にあり、コンテナと一緒に消えます。Redis は止まるときに中身を `/data` に書き出し、起動するときに読み戻します（`DB loaded from disk`）。

✅ 検証済み: Docker Compose v5.5.1。volume が無いと空になることも確認した。

</details>

#### Lv2 応用: 画面は API の準備を待つ

**課題**

- `api` にヘルスチェックを付ける。`/api/health` が応答したら healthy にする
- `web` は、`api` が healthy になってから起動する

**ヒント**: `python:3.13-slim` には `curl` も `wget` も入っていません。イメージの中にある Python で、URL を開くことはできます。

**判定基準**: `docker compose down` → `docker compose up -d` の出力で、`api-1 Healthy` の行が `web-1 Started` の行より前に出る。`docker compose ps` の `api` が `(healthy)` になる。

<details><summary>解答例</summary>

**ファイル**: `compose.yaml`（差分）

```diff
   api:
     （省略）
     volumes:
       - ./apps/api/src:/app/src
       - media:/app/media
+    healthcheck:
+      test: ["CMD", ".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]
+      interval: 2s
+      timeout: 5s
+      retries: 30
     networks:
```

```diff
   web:
     build: ./apps/web
     ports:
       - "5173:5173"
     depends_on:
-      - api
+      api:
+        condition: service_healthy
```

```bash
docker compose down
docker compose up -d
docker compose ps --format '{{.Service}} {{.Status}}'
```

```text
 Container roadmap-sh-docker-api-1 Started
 Container roadmap-sh-docker-api-1 Waiting
 Container roadmap-sh-docker-api-1 Healthy
 Container roadmap-sh-docker-web-1 Starting
 Container roadmap-sh-docker-web-1 Started
api Up 2 seconds (healthy)
db Up 4 seconds (healthy)
redis Up 4 seconds
web Up Less than a second
worker Up 2 seconds
```

✅ 検証済み: Docker Compose v5.5.1

`urlopen` は、応答が 200 番台でなければ例外を出し、終了コードが 1 になります。だから、`/api/health` が返事をしたときだけ healthy になります。

</details>

---

## ▶ 次は P5

P4 はここまでです。次のフェーズでは、600MB を超えた `ec-api:dev` を測り、軽くします。

**片付け**（P5 の前に行う）

```bash
docker compose down
rm sample.jpg
```

volume は残します。P5 でも、同じ DB と画像を使います。

**前提チェック**

- [ ] `compose.yaml` のサービス・volume・ネットワークを、白紙から書ける（P4-1、P4-2）
- [ ] 「起動した」と「使える」の違いを説明できる（P4-3）
- [ ] ブラウザが `api` を名前で呼べず、`web` は呼べる理由を説明できる（P4-4）
- [ ] 同じイメージで `api` と `worker` が別の動きをする理由を説明できる（P4-6）
