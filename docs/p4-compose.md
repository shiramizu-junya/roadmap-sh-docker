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

| 部品                             | 正式名称         | 実行時に何が起きるか                                                                                            |
| -------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------- |
| `compose.yaml`                   | Compose ファイル | 動かしたいコンテナの一覧を書いた設計図。Compose はこれを読んで、Docker デーモンに `docker run` 相当の依頼を出す |
| `services:`                      | サービスの定義   | 1つのサービスが、1種類のコンテナを表す。キーの名前（`db`、`api`）がサービス名になる                             |
| `docker compose up -d`           | 起動             | 足りないネットワーク・コンテナを作り、起動する。すでに同じ設定で動いているものには手を付けない                  |
| `docker compose down`            | 停止と削除       | コンテナと、Compose が作ったネットワークを消す。**volume とイメージは消さない**                                 |
| `image:` `ports:` `environment:` | （補助）         | それぞれ `docker run` の最後のイメージ名、`-p`、`-e` と同じ                                                     |

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

| 何に付く名前か                 | 決まり方                       | 例                          |
| ------------------------------ | ------------------------------ | --------------------------- |
| コンテナ                       | プロジェクト名-サービス名-番号 | `roadmap-sh-docker-api-1`   |
| ネットワーク                   | プロジェクト名\_default        | `roadmap-sh-docker_default` |
| サービス名（DNS で引ける名前） | `services:` のキー             | `db`、`api`                 |

なぜを下っていきます。

```text
なぜ、compose.yaml にまとめるのか
  → 長い docker run を毎回打つと、打ち間違えるから
      → なぜ、ファイルにすると打ち間違えないのか
          → 設定がファイルに残り、毎回同じものが使われるから
              → なぜ、ネットワークを書かなくてよいのか
                  → Compose がプロジェクトごとに1つ作り、全サービスをつなぐから
```

| 確認すること                 | 内容                                                                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **既知スタックとの対応**     | `package.json` の `scripts` に近い。ただし Compose は「打つコマンド」ではなく「あるべき状態」を書く。`up` は、いまの状態をその形に合わせる |
| **なぜこの設計か**           | 複数のコンテナの設定を1か所に集め、リポジトリで共有できるようにするため                                                                    |
| **ビルド時かランタイム時か** | ランタイム。`compose.yaml` は `docker run` の代わりで、イメージは作らない（`build:` は P4-4）                                              |
| **ホストからの見え方**       | `docker compose ps`。`docker ps` でも見えるが、ほかのコンテナと混ざる                                                                      |
| **失敗時の挙動**             | YAML の字下げを間違えると、起動前に止まる。下の例                                                                                          |

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

| トークン                         | 扱い                                                         |
| -------------------------------- | ------------------------------------------------------------ |
| `services:`                      | 1-1 で実践、1-2 で解剖                                       |
| `docker compose up`              | 1-1 で実践、1-2 で解剖                                       |
| `docker compose down`            | 1-2 で解剖、1-6 で確認                                       |
| `image:` `ports:` `environment:` | 1-2 で `docker run` と対応。`environment:` は ⏭️ P4-5 で回収 |
| YAML                             | 1-1 の Linux注                                               |

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

| 部品                       | 正式名称                       | 実行時に何が起きるか                                                            |
| -------------------------- | ------------------------------ | ------------------------------------------------------------------------------- |
| いちばん外の `volumes:`    | トップレベルの volume 定義     | このプロジェクトで使う、名前付きの volume を宣言する。`up` のとき、無ければ作る |
| サービスの中の `volumes:`  | サービスの volume 指定         | **ランタイム**に、そのコンテナへ volume をマウントする。`-v` と同じ             |
| いちばん外の `networks:`   | トップレベルのネットワーク定義 | このプロジェクトで使うネットワークを宣言する。`up` で作り、`down` で消す        |
| サービスの中の `networks:` | サービスのネットワーク指定     | そのコンテナを、どのネットワークにつなぐか。`--network` と同じ                  |
| `docker compose ps`        | サービスの一覧                 | このプロジェクトのコンテナの状態を出す。`-a` で止まったものも出す               |

**名前が似ている2つの `volumes:`** を並べます。

|                       | いちばん外の `volumes:` | サービスの中の `volumes:`      |
| --------------------- | ----------------------- | ------------------------------ |
| 書く場所              | 行の頭（字下げなし）    | サービスの下                   |
| 意味                  | 倉庫を「建てる」宣言    | 部屋の扉を倉庫に「つなぐ」指定 |
| `docker` コマンドでは | `docker volume create`  | `docker run -v`                |

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

| 確認すること                 | 内容                                                                               |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| **既知スタックとの対応**     | 対応物なし。アプリのフレームワークは、DB の置き場所を作ったり消したりしない        |
| **なぜこの設計か**           | 寿命の違うものを分ける（P3-1）。コンテナとネットワークは使い捨て、データは残す     |
| **ビルド時かランタイム時か** | ランタイム                                                                         |
| **ホストからの見え方**       | `docker volume ls` と `docker network ls` に、`プロジェクト名_` の付いた名前で出る |
| **失敗時の挙動**             | サービスの中で使った volume をいちばん外に書き忘れると、起動前に止まる。下の例     |

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

| トークン            | 扱い                                                |
| ------------------- | --------------------------------------------------- |
| `volumes:`          | 2-1 で実践、2-2 で解剖                              |
| `networks:`         | 2-1 で実践、2-2 で解剖。分ける理由は ⏭️ P4-4 で回収 |
| `docker compose ps` | 2-1 で実践、2-2 で解剖                              |

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

| エラー                                      | 意味                                   | どの層か            |
| ------------------------------------------- | -------------------------------------- | ------------------- |
| `(2005, "Unknown server host 'db'")`        | 名前が引けない                         | ネットワーク（DNS） |
| `(2002, "Can't connect to server on 'db'")` | 名前は引けたが、相手が受け付けていない | 相手のプロセス      |

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

| 部品                           | 正式名称             | 実行時に何が起きるか                                                                                                         |
| ------------------------------ | -------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `healthcheck:`                 | ヘルスチェック       | **ランタイム**に、Docker デーモンがコンテナの中で `test` のコマンドを `interval` ごとに実行する。終了コードが 0 なら healthy |
| `test:`                        | 確かめるコマンド     | `CMD` の後ろが、コンテナの中で実行される。ここでは `mysqladmin ping`                                                         |
| `interval` `timeout` `retries` | 間隔・時間切れ・回数 | 2秒ごとに試す。5秒で応答が無ければ失敗。30回続けて失敗したら unhealthy                                                       |
| `depends_on:`                  | 依存関係             | `api` は `db` のあとに起動する、という順番の指定                                                                             |
| `condition: service_healthy`   | 起動の条件           | `db` が healthy になるまで、`api` の起動を待たせる                                                                           |

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

| 確認すること                 | 内容                                                                                                    |
| ---------------------------- | ------------------------------------------------------------------------------------------------------- |
| **既知スタックとの対応**     | フロントの E2E テストで「サーバが応答するまで待ってから始める」設定に近い。ただし、待つのは Docker 自身 |
| **なぜこの設計か**           | 「準備できた」の意味は、アプリごとに違う。Docker はそれを知らないので、確かめ方を利用者に任せる         |
| **ビルド時かランタイム時か** | ランタイム。Docker デーモンがコンテナの中でコマンドを実行する                                           |
| **ホストからの見え方**       | `docker compose ps` の `(healthy)`、`docker inspect` の `.State.Health`                                 |
| **失敗時の挙動**             | 30回続けて失敗すると unhealthy になり、`up` が下のエラーで止まる                                        |

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

| トークン      | 扱い                   |
| ------------- | ---------------------- |
| `healthcheck` | 3-1 で実践、3-2 で解剖 |
| `depends_on`  | 3-1 で実践、3-2 で解剖 |
| `condition`   | 3-2 で解剖             |
| 終了コード    | 3-3 の Linux注         |

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

| ファイル                     | 役割                                       |
| ---------------------------- | ------------------------------------------ |
| `package.json`               | 使う部品の一覧                             |
| `vite.config.js`             | 開発サーバの設定。`/api` を API に中継する |
| `index.html`                 | 画面の入口                                 |
| `src/main.jsx` `src/App.jsx` | 画面のコード                               |
| `Dockerfile` `.dockerignore` | イメージの作り方                           |

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

| 部品                  | 正式名称                 | 実行時に何が起きるか                                                                                                  |
| --------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `build: ./apps/web`   | ビルドの指定             | **ビルド時**に、このフォルダをビルドコンテキストにして `docker build` する。`up --build` か、イメージが無いときに動く |
| `docker compose exec` | サービスでのコマンド実行 | 動いているコンテナで、コマンドを追加で実行する。`docker exec` と同じだが、サービス名で指定できる                      |
| `develop.watch`       | 監視の設定               | `docker compose watch` が使う設定。`up` だけでは働かない                                                              |
| `action: sync`        | 同期                     | `path` のファイルが変わったら、コンテナの `target` へ写す                                                             |
| `action: rebuild`     | 作り直し                 | `path` のファイルが変わったら、イメージを作り直し、コンテナを入れ替える                                               |
| `proxy`               | プロキシ（Vite の設定）  | ブラウザから来た `/api/...` を、Vite が `http://api:8000/api/...` に送り直す                                          |

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

|                        | `api`（bind mount）                                    | `web`（watch の sync）                           |
| ---------------------- | ------------------------------------------------------ | ------------------------------------------------ |
| 何をつなぐか           | Mac の `apps/api/src` を、そのまま `/app/src` に見せる | 変わったファイルを、コンテナの `/app/src` に写す |
| コンテナの中のファイル | Mac と同じ実体                                         | 写した別の実体                                   |
| 起動するコマンド       | `docker compose up` だけでよい                         | `docker compose watch` が要る                    |
| 依存の変更             | 手で `up --build`                                      | `rebuild` で自動                                 |

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

| 確認すること                 | 内容                                                                                                                            |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **既知スタックとの対応**     | `vite.config.js` の `server.proxy` は、ふだんの React 開発と同じ書き方。違うのは、相手が `localhost` ではなくサービス名である点 |
| **なぜこの設計か**           | 開発に要る道具をイメージに閉じ込める。誰の Mac でも同じ版の Node.js で動く                                                      |
| **ビルド時かランタイム時か** | `build:` はビルド時。`exec` と `watch` はランタイム                                                                             |
| **ホストからの見え方**       | `docker compose ps` に `web` が出る。`docker image ls` に `roadmap-sh-docker-web` と `roadmap-sh-docker-api` が出る             |
| **失敗時の挙動**             | `proxy` の相手を `localhost:8000` にすると、`web` コンテナ自身の 8000 番を探して失敗し、`/api` が 502 になる                    |

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

| トークン                         | 扱い                               |
| -------------------------------- | ---------------------------------- |
| `build:`                         | 4-1 で実践、4-2 で解剖             |
| `docker compose exec`            | 4-1 で実践、4-2 で解剖             |
| `docker compose watch`           | 4-1 で実践、4-2 で解剖、4-6 で確認 |
| Vite、開発サーバ、プロキシ       | 4-1 と 4-2 で解説                  |
| P4-2 の `networks:` を分ける理由 | 4-1 と 4-4 で回収                  |

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

| 項目           | 決まり                                                         |
| -------------- | -------------------------------------------------------------- |
| カートの区別   | 画面が作った ID を、`X-Cart-Id` ヘッダで送る                   |
| Redis の置き方 | `cart:<ID>` というハッシュに、`商品番号 → 個数` を入れる       |
| API            | `GET /api/cart` で中身を返し、`POST /api/cart/items` で1つ足す |

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

const headers = {
    "X-Cart-Id": getCartId(),
    "Content-Type": "application/json",
};

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
                        {p.thumbnail_url && (
                            <img src={p.thumbnail_url} alt="" />
                        )}
                        {p.name} — {p.price}円
                        <button onClick={() => addToCart(p.id)}>
                            カートに入れる
                        </button>
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

| 部品                    | 正式名称               | 実行時に何が起きるか                                                                                          |
| ----------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------- |
| `environment:`          | 環境変数の指定         | `compose.yaml` に直接書いた `名前: 値` を、コンテナの環境変数にする。`-e` と同じ。P4-1 の宣言をここで回収する |
| `env_file:`             | 環境変数ファイルの指定 | **Compose が** `up` のときにファイルを読み、中身を環境変数にする。`--env-file` と同じ                         |
| `docker compose config` | 設定の展開表示         | ファイルの読み込み・相対パスの解決・省略値の補完を全部済ませた、最終的な設定を出す。コンテナは作らない        |

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

|                  | `env_file:` に書いた `apps/api/.env` | プロジェクト直下の `.env`                       |
| ---------------- | ------------------------------------ | ----------------------------------------------- |
| 誰が読むか       | Compose が、そのサービスのために読む | Compose が、`compose.yaml` を読む前に自動で読む |
| 何に使うか       | コンテナの環境変数になる             | `compose.yaml` の中の `${名前}` を置き換える    |
| この教材で使うか | 使う                                 | 使わない                                        |

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

| 確認すること                 | 内容                                                                                                  |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| **既知スタックとの対応**     | `dotenv` で `.env` を読む流れに近い。違うのは、読むのがアプリではなく Compose である点（P3-4 と同じ） |
| **なぜこの設計か**           | 同じ `compose.yaml` を、`.env` を差し替えるだけで別の環境に使える                                     |
| **ビルド時かランタイム時か** | ランタイム。`.env` を変えたら、イメージではなくコンテナを作り直す（`up -d` で入れ替わる）             |
| **ホストからの見え方**       | `docker compose config` と、`docker compose exec api env`                                             |
| **失敗時の挙動**             | `env_file:` のパスを間違えると、起動前に止まる。下の例                                                |

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

| トークン                | 扱い                          |
| ----------------------- | ----------------------------- |
| `environment:`          | 5-2 で解剖。P4-1 の宣言を回収 |
| `env_file:`             | 5-1 で実践、5-2 で解剖        |
| `docker compose config` | 5-1 で実践、5-2 で解剖        |
| Redis、ハッシュ         | 5-1 で解説                    |

### 📇 まとめカード

> **値は `.env`、構成は `compose.yaml`。渡る形は `docker compose config` で見る。**

**残った問い**: 画像を受け取ったら、縮めてサムネイルを作りたい。でも、重い処理で API の応答を待たせたくない。

---

▶ **次**: P4-6 ワーカーでサムネイルを作る

---

## P4-6: ワーカーでサムネイルを作る（小さく分けた版）

> 📝 **作り直しました（2026-11-14）**: 前の P4-6 は、1回で 7つのファイルを変える作りでした。量が多すぎてコピペ作業になりやすかったので、**小さなステップに分けました。** 1回に変えるファイルは1つ、自分で書くのは5行までです。

**P4-6 ぜんたいの地図**（各ステップで、いまどこにいるかを示します）

```text
① api が画像を受け取って保存する
        │
        ▼
② api が「サムネイルを作って」というメモを、受付箱に入れる
        │            （受付箱 ＝ Redis の 1番の部屋）
        ▼
③ worker が受付箱からメモを取り出す
        │
        ▼
④ worker が画像を縮めて、サムネイルとして保存する
        │
        ▼
⑤ 画面にサムネイルが出る
```

**見てほしいところ**: `api` と `worker` は別のコンテナです。**②と③のあいだに受付箱がある**ので、api は worker の仕事が終わるのを待たずに返事ができます。

| ステップ  | やること                                      | 地図     |
| --------- | --------------------------------------------- | -------- |
| **P4-6a** | 受付箱の場所を Celery に教える                | ②③の準備 |
| P4-6b     | worker コンテナを起動する                     | ③        |
| P4-6c     | 画像を受け取って保存する                      | ①        |
| P4-6d     | 画像の倉庫を作って worker と分け合う          | ①④の準備 |
| P4-6e     | メモを受付箱に入れ、worker に届ける           | ②③       |
| P4-6f     | サムネイルを作る                              | ④        |
| P4-6g     | 画面にサムネイルを出す                        | ⑤        |
| P4-6h     | worker を止めるとき、仕事が終わるまで待たせる | ③④       |

P4-6b 以降は、P4-6a が終わってから作ります。

---

## P4-6a: 受付箱の場所を Celery に教える

**❓ この回の問い**: 前回（P4-5）の答えは「設定は `.env` に出し、`docker compose config` で確かめる」だった。
→ **では、重い仕事を頼むための「受付箱」の場所も、同じやり方で渡せるのか？**

**作ること / 確かめること**: Celery（セロリ）を入れ、受付箱の場所が `.env` → `settings.py` → Celery の順に届くことを確かめる
**重要度**: 🔴 毎日使う — 「`.env` から設定を受け取る」形は、どのサービスでも同じだから
**前ステップとの接続**: P4-5 で作った `REDIS_URL` の、すぐ隣に書く

### 🔁 前回の思い出し

**問い**: P4-5 で、カートの置き場所 `REDIS_URL=redis://redis:6379/0` を書いたのは、A と B のどちらでしたか？
A. `compose.yaml`　B. `apps/api/.env`

<details><summary>答え</summary>

**B. `apps/api/.env`**。`compose.yaml` には `env_file: ./apps/api/.env` だけを書き、値はファイルの外に出しました。今日も同じ形を使います。

</details>

### 🗺️ 今日の地図

```text
apps/api/.env              … チャンク1
  BROKER_URL=redis://redis:6379/1
        │ コンテナの環境変数として渡る
        ▼
apps/api/src/config/settings.py   … チャンク2
  CELERY_BROKER_URL = os.environ["BROKER_URL"]
        │ Celery が settings を読む
        ▼
apps/api/src/config/celery.py     … チャンク3
  app（Celery の本体）が受付箱の場所を知る
```

**見てほしいところ**: 値（`redis://redis:6379/1`）を書くのは `.env` の1か所だけです。下の2つのファイルは、それを**受け取って渡すだけ**です。

### 6a-0. このステップの初出

**Docker**: なし（P4-5 までの道具だけで進む） / **Linux**: なし
**その他**: Celery、ブローカー、`config_from_object`

### 準備: Celery を入れる

> 📇 **Celery（セロリ）** — かみくだくと: 「重い仕事を、あとで別の係にやらせる」ための Python の部品。
> 似た言葉との違い: Redis = メモを置いておく**箱**。Celery = 箱にメモを入れたり、取り出して仕事をしたりする**しくみ**。
> この教材では: api がメモを入れ、worker（P4-6b）が取り出す。

ここはコードを書く所ではないので、コマンドをそのまま打ちます。

**実行場所**: リポジトリのいちばん上（`roadmap-sh-docker/`）

```bash
cd apps/api
uv add --no-sync 'celery[redis]>=5.6,<5.7'
cd ../..
grep -A1 'name = "celery"$' apps/api/uv.lock
```

```text
name = "celery"
version = "5.6.3"
```

✅ 検証済み: uv 0.13.7（Mac）/ 2026-11-14

| 部品            | 意味                                                                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `uv add`        | `pyproject.toml` に部品を書き足し、`uv.lock`（使う版の一覧）も書き直す                                                                            |
| `--no-sync`     | **Mac の `.venv` には入れない。** ファイル2つを書き直すだけ。部品を実際に入れるのは、コンテナのビルドのとき（`Dockerfile` の `uv sync --locked`） |
| `celery[redis]` | Celery に「Redis を受付箱として使うための追加部品」も付けて入れる                                                                                 |
| `>=5.6,<5.7`    | 5.6 系だけを使う。勝手に 5.7 に上がらないようにする                                                                                               |

続けて、新しい部品が入ったイメージを作ります。

```bash
docker compose build api
```

<details><summary>💡 なぜ前の P4-6 と入れ方が違うの？</summary>

前の P4-6 では、`docker run ... uv lock` という長いコマンドで、コンテナの中の uv に `uv.lock` を作らせていました。いまは Mac にも uv が入っているので、`uv add --no-sync` の1行で同じことができます。

</details>

---

### チャンク1: 受付箱の場所を書く（`apps/api/.env`）— 地図のいちばん上

> 📇 **ブローカー** — 正式名称: **message broker**（メッセージブローカー）。Celery の設定名は `broker_url`
> かみくだくと: 仕事のメモを**預かる受付窓口**。
> 似た言葉との違い: ワーカー（worker）= メモを取り出して、仕事を**やる係**。
> この教材では: Redis の **1番の部屋**（`redis://redis:6379/1`）。カートは 0番の部屋なので、部屋を分ける。

> 📇 **部屋** — 正式名称: **logical database**（論理データベース）。URL では **database number**（データベース番号）
> かみくだくと: 1つの Redis の中を、番号で区切った部屋。最初から **0〜15番の16個**ある（Redis の設定 `databases 16` で決まっている）。
> 似た言葉との違い: MySQL の「データベース」は名前を付けて作るもの。Redis の部屋は、**最初から番号で用意されている**。作る手順は要らない。
> この教材では: 0番 = カート、1番 = 受付箱。`redis-cli -n 1` のように `-n` で部屋を選べる。
> 根拠: https://redis.io/docs/latest/commands/select/

**🤔 先に考える**: Redis にはカートがもう 0番の部屋に入っています。受付箱も**同じ 0番**に置くと、何か困ると思いますか？ 一言で（「分からない」でも大丈夫です）。

<details><summary>答え</summary>

困ることがあります。カートのデータと仕事のメモが同じ部屋に混ざるので、中を見たときに区別しにくくなります。片方だけ消したいときにも困ります。番号を変えるだけで部屋を分けられるので、分けておきます。

</details>

**🎯 書くもの**: `apps/api/.env` の**いちばん下**に、受付箱の場所を1行足す。名前は `BROKER_URL`、値は「Redis の 1番の部屋」。

**✍️ 自分で書く**（2回目なので穴埋め）: P4-5 で書いた行を見ながら、`___` を埋めます。

```text
REDIS_URL=redis://redis:6379/0
BROKER_URL=redis://___:6379/___
```

<details><summary>ヒント1</summary>

1つ目の `___` は、Redis コンテナの**サービス名**です（P4-1：サービス名で呼び合える）。

</details>

<details><summary>答え合わせ</summary>

```diff
 REDIS_URL=redis://redis:6379/0
+BROKER_URL=redis://redis:6379/1
```

</details>

**▶️ 確かめる**: 書いた値が、コンテナに渡る形になっているかを見ます（P4-5 の道具）。

```bash
docker compose config api | grep BROKER
```

```text
      BROKER_URL: redis://redis:6379/1
```

何も出なかったら、行の名前のつづりと、保存したかを見直します。

**🔬 1行ずつ分解**:

| 部品         | 読み方                                       | 意味                                                               | 無いと / 変えるとどうなる                                                                                                                                      |
| ------------ | -------------------------------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BROKER_URL` | ブローカー ユーアールエル                    | 環境変数の名前。チャンク2 でこの名前を探す                         | つづりを変えると、チャンク2 で `KeyError`（その名前が無い）になる                                                                                              |
| `redis://`   | レディス                                     | 「Redis につなぐ」という印                                         | —                                                                                                                                                              |
| `redis`      | レディス                                     | Redis コンテナの**サービス名**。ネットワークの中で住所として使える | `localhost` にすると、api コンテナ**自身**を探してしまい、つながらない                                                                                         |
| `6379`       | —                                            | Redis が待っている番号（ポート）                                   | —                                                                                                                                                              |
| `/1`         | スラッシュ いち（正式名称: database number） | Redis の中の部屋（論理データベース）の番号。0〜15 がある           | `/0` にすると、カートと同じ部屋に混ざる。`/16` にすると、部屋が無いのでエラー（`ERR DB index is out of range`）。✅ 検証済み: `redis-cli -n 16 PING` / redis 8 |

---

### チャンク2: settings.py で受け取る（`apps/api/src/config/settings.py`）— 地図のまん中

**🤔 先に考える**: このチャンクで書く1行は、P4-5 で書いたどの行と**ほぼ同じ形**になると思いますか？ ファイルを開く前に、行を1つ思い出してみてください。

<details><summary>答え</summary>

`REDIS_URL = os.environ["REDIS_URL"]` です。形は同じです。ただし今回は、**左の名前と右の名前が違います**（下の 🎯 を見てください）。

</details>

**🎯 書くもの**: `settings.py` の**いちばん下**（`REDIS_URL = ...` の下）に、環境変数 `BROKER_URL` を読んで、`CELERY_BROKER_URL` という名前の設定にする1行を書く。

**✍️ 自分で書く**（3回目なので、日本語だけで書きます）

<details><summary>ヒント1: 使う部品</summary>

`os.environ` と `[ ]`。

</details>

<details><summary>答え合わせ</summary>

```diff
 REDIS_URL = os.environ["REDIS_URL"]
+
+CELERY_BROKER_URL = os.environ["BROKER_URL"]
```

</details>

**▶️ 確かめる**: Django が設定を読めているかを、コンテナの中で聞きます。

```bash
docker compose run --rm api .venv/bin/python src/manage.py shell -c "from django.conf import settings; print(settings.CELERY_BROKER_URL)"
```

```text
API を起動します
1 object imported automatically (use -v 2 for details).

redis://redis:6379/1
```

✅ 検証済み: Django 5.2 / Docker 29 系（2026-11-14）。同じイメージを `docker run --env-file` で動かして確認した

最後の行が出れば OK です。上の2行は気にしなくて大丈夫です（1行目は `entrypoint.sh` の `echo`。2行目は Django の `shell` がいつも出すお知らせ）。

**🔬 1行ずつ分解**:

| 部品                      | 読み方                | 意味                                                                          | 無いと / 変えるとどうなる                                                                                           |
| ------------------------- | --------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `CELERY_BROKER_URL`（左） | —                     | Django の設定の名前。**`CELERY_` で始まる**のが大事（チャンク3 で使う）       | 頭の `CELERY_` を外すと、チャンク3 で Celery がこの設定を見つけられない                                             |
| `os.environ`              | オーエス エンバイロン | コンテナに渡された環境変数の一覧                                              | —                                                                                                                   |
| `["BROKER_URL"]`          | 角かっこ              | 一覧から、この名前の値を1つ取り出す。**無ければその場でエラー**（`KeyError`） | `.get("...")` にすると、無くてもエラーにならず `None` になる。設定漏れに気づきにくくなるので、ここでは `[ ]` を使う |

<details><summary>💡 なぜ、左と右で名前を変えたの？</summary>

Celery には「`CELERY_BROKER_URL` という名前の**環境変数**があれば、`settings.py` を通さずに直接読む」という機能があります。`.env` も同じ名前にすると、値が `settings.py` を通らずに Celery へ届いてしまいます。すると、チャンク2 の行を消しても動いてしまい、地図の道が見えなくなります。

この教材では、道を1本にするために `.env` 側を `BROKER_URL` にしました。

</details>

---

### チャンク3: Celery の本体を作る（`apps/api/src/config/celery.py`・新しいファイル）— 地図のいちばん下

**🤔 先に考える**: Celery は、チャンク2 で書いた `CELERY_BROKER_URL` を自分で見つけられると思いますか？
A. 見つけられる（名前で勝手に探す）　B. 「settings.py を読んで」と教える行が要る

<details><summary>答え</summary>

**B** です。Celery は Django とは別の部品なので、どの設定を読めばよいかを1行で教えます。それが下のコードの最後の行です。

</details>

**🎯 書くもの**: `apps/api/src/config/` に `celery.py` を新しく作り、Celery の本体（`app`）を作る。そして「`settings.py` の `CELERY_` で始まる設定を読んで」と教える。

**✍️ 自分で書く**（初めて出る形なので、**先に下の分解表を読んでから、手で打ちます。コピペはしません**）

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
```

**🔬 1行ずつ分解**（打つ前に読む）:

| 部品                         | 読み方                             | 意味                                                                                                                                | 無いと / 変えるとどうなる                                                                                  |
| ---------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `import os`                  | インポート オーエス                | 環境変数を扱う部品を使えるようにする                                                                                                | 次の `os.environ` で `NameError`                                                                           |
| `from celery import Celery`  | —                                  | 準備で入れた Celery から、本体を作る型 `Celery` を取り出す                                                                          | `docker compose build api` をしていないと `ModuleNotFoundError: No module named 'celery'`                  |
| `os.environ.setdefault(...)` | セット デフォルト                  | 「どの設定ファイルを使うか」が**まだ決まっていなければ**、`config.settings`（= `settings.py`）にする                                | `manage.py` を通さずに Celery だけ起動したとき（P4-6b の worker）に、Django が設定ファイルを見つけられない |
| `"DJANGO_SETTINGS_MODULE"`   | ジャンゴ セッティングス モジュール | Django が「設定ファイルの場所」を探す環境変数の名前                                                                                 | —                                                                                                          |
| `app = Celery("config")`     | —                                  | Celery の本体を1つ作り、`app` という名前を付ける。`"config"` はこの本体の名前                                                       | —                                                                                                          |
| `config_from_object(...)`    | コンフィグ フロム オブジェクト     | 「この場所から設定を読んで」と Celery に教える                                                                                      | 消すと、Celery は受付箱の場所を知らないままになる                                                          |
| `"django.conf:settings"`     | —                                  | 読む場所 ＝ Django の設定（`settings.py` の中身）                                                                                   | —                                                                                                          |
| `namespace="CELERY"`         | ネームスペース                     | 「`CELERY_` で始まる名前だけ読む。頭の `CELERY_` は外して読む」。だから `CELERY_BROKER_URL` は、Celery の中では `broker_url` になる | —                                                                                                          |

<details><summary>答え合わせ（新しいファイルの全文）</summary>

上のコードと同じです。1文字ずつ見比べて、違う所があれば直します。

</details>

**▶️ 確かめる**: Celery の本体が、受付箱の場所を知っているかを聞きます。

```bash
docker compose run --rm api .venv/bin/python src/manage.py shell -c "from config.celery import app; print(app.conf.broker_url)"
```

```text
API を起動します
1 object imported automatically (use -v 2 for details).

redis://redis:6379/1
```

✅ 検証済み: Celery 5.6.3 / Django 5.2（2026-11-14）。同じイメージを `docker run --env-file` で動かして確認した

**`broker_url` と聞いたのに、`.env` に書いた値が返ってきました。** 地図の上から下まで、値が届いています。

**🧪 壊してみる**

1. **予想**: `celery.py` の最後の行（`app.config_from_object(...)`）を消して、上の「確かめる」をもう一度打つと、何が出ると思いますか？
   A. 同じ `redis://redis:6379/1`　B. 何か別のもの
2. **実行**: 行を消して保存し、同じコマンドを打ちます
3. **見る**: 最後の行が `None`（何も無い）になります。**Celery は `settings.py` を読みに行かなくなり、受付箱の場所を知らないままになりました。** 分解表の `config_from_object` の行の「無いとどうなる」と同じです
4. **元に戻す**: 消した行を戻し、もう一度打って `redis://redis:6379/1` に戻ることを確かめます

✅ 検証済み: Celery 5.6.3（2026-11-14）

<details><summary>もう1つ試したい人へ</summary>

`settings.py` の左の名前から `CELERY_` を外して `BROKER_URL = os.environ["BROKER_URL"]` にすると、どうなるでしょう。これも `None` になります。`namespace="CELERY"` は「`CELERY_` で始まる名前だけ読む」からです。試したら元に戻します。

</details>

<details><summary>⚠️ Zed で `celery` に赤線が出たら</summary>

`--no-sync` で Mac の `.venv` には Celery を入れていないので、Zed（の型チェック）が Celery を見つけられません。コンテナの中では動くので、教材を進めるのには困りません。気になる場合は、Mac の `.venv` にも入れます（`mysqlclient` のビルドに必要な場所の指定が要ります）。

```bash
cd apps/api
PKG_CONFIG_PATH=/opt/homebrew/opt/mysql-client/lib/pkgconfig uv sync
cd ../..
```

</details>

### 📝 ひとこと

「〜だと思っていたけど、実は〜」を1行書きます。書いたものは `docs/notes.md` に貯めます。うまく書けなければ、書かずに先へ進んでも大丈夫です。

例: 「Celery は設定を勝手に見つけると思っていたけど、実は `config_from_object` で読む場所を教えていた」

### ✅ できるようになったこと

- [x] 受付箱の場所が、`.env` → `settings.py` → `celery.py` の順に届くことを、地図を見ながら説明できる
- [x] `namespace="CELERY"` があるので、`CELERY_BROKER_URL` が `broker_url` として読まれることを説明できる
- [x] `config_from_object` の行を消すと `None` になる理由を、分解表を見ずに言える

**残った問い**: 受付箱の場所は分かった。でも、箱からメモを取り出す係（worker）は、まだどこにもいない。**worker は、どのイメージから作ればいいのか？**

---
▶ **次**: P4-6b worker コンテナを起動する

---

## P4-6b: worker コンテナを起動する

**❓ この回の問い**: 前回（P4-6a）の答えは「受付箱の場所は `.env` → `settings.py` → `celery.py` の順に届く」だった。でも、箱からメモを取り出す係（worker）は、まだどこにもいない。
→ **worker は、どのイメージから作ればいいのか？ api と同じイメージで、別の仕事をさせられるのか？**

**作ること / 確かめること**: api と**同じイメージ**から worker コンテナを作り、受付箱（Redis の 1番の部屋）につながったことをログで確かめる
**重要度**: 🔴 毎日使う — 「同じイメージで、役割だけ変える」は Compose でよく出る形だから
**前ステップとの接続**: P4-6a で作った `celery.py` を、worker が起動のときに読む

**P4-6 ぜんたいの地図での位置**: ③（worker が受付箱からメモを取り出す）の**係を用意する**ところ。

### 🔁 前回の思い出し

**問い**: P4-6a の 🧪 で、`celery.py` の `app.config_from_object(...)` を消したら、受付箱の場所は何と出ましたか？ そして、なぜでしたか？

<details><summary>答え</summary>

`None` と出ました。`config_from_object` は「`settings.py` を読みに行って」と Celery に教える行です。その行が無いと、Celery は `settings.py` を読みに行かなくなります。だから、受付箱の場所を知らないままでした。

</details>

### 🗺️ 今日の地図

```text
イメージ ec-api:dev          … チャンク1 で名前を付ける
（中身: アプリのコード + Celery）
        │
        ├──▶ api コンテナ
        │      イメージの CMD のまま動く
        │      → runserver（Web の窓口）
        │
        └──▶ worker コンテナ      … チャンク2・3 で作る
               command: で CMD を置き換える
               → celery worker（受付箱を見張る係）
                       │
                       ▼
               Redis の 1番の部屋（受付箱）につながる
```

**見てほしいところ**: 中身（イメージ）は**1つ**です。そこから、**起動するときの命令**だけを変えて、2つの係を作ります。

### 6b-0. このステップの初出

**Docker**: `image:`（`build:` と一緒に書く）、`command:`、`docker compose logs -f`
**Linux**: なし（`/proc/1/cmdline` は P4-6 の前の版で一度出ています。今回は 🧪 で使うだけです）
**その他**: なし

---

### チャンク1: api のイメージに名前を付ける（`compose.yaml` の `api`）— 地図のいちばん上

> 📇 **イメージ名** — 正式名称: **image name**（イメージ名）。`:` の後ろは **tag**（タグ）。2つ合わせて **image reference**（イメージの参照名）と呼ぶ
> かみくだくと: 段ボール（イメージ）に貼る**名札**。`ec-api` が品名、`dev` が「開発用」というラベル。
> 似た言葉との違い: コンテナ名（`roadmap-sh-docker-api-1`）= 箱を開けて動かしている**部屋**の名前。イメージ名 = 封をした**段ボール**の名前。
> この教材では: `ec-api:dev`。P2 で付けた `ec-api:step5` などと同じ形。

**🤔 先に考える**: いまの `compose.yaml` の `api` には `image:` が書いてありません。それでも `build:` でイメージは作られています。**そのイメージには、どんな名前が付いていると思いますか？** 一言で（「分からない」でも大丈夫です）。

<details><summary>答え</summary>

`roadmap-sh-docker-api` です。名前を書かないと、Compose が「**プロジェクト名-サービス名**」で自動で付けます。プロジェクト名は、ふつうはフォルダ名（`roadmap-sh-docker`）です。

```bash
docker image ls roadmap-sh-docker-api
```

```text
IMAGE                          ID             DISK USAGE   CONTENT SIZE   EXTRA
roadmap-sh-docker-api:latest   156b14421db3        727MB          174MB
```

✅ 検証済み: 2026-11-14（ID は環境ごとに違います）

</details>

**🎯 書くもの**: `api` の `build: ./apps/api` の**すぐ下**に、作ったイメージへ `ec-api:dev` という名前を付ける1行を足す。

**✍️ 自分で書く**（`image:` は P4-1 で `db` や `redis` に書いたので、穴埋めです）

```yaml
    api:
        build: ./apps/api
        ___: ec-api:dev
        depends_on:
```

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
     api:
         build: ./apps/api
+        image: ec-api:dev
         depends_on:
             db:
```

</details>

**▶️ 確かめる**: イメージを作り直し、名札が付いたかを見ます。

```bash
docker compose build api
docker image ls ec-api
```

```text
IMAGE          ID             DISK USAGE   CONTENT SIZE   EXTRA
ec-api:dev     22b673f15123        727MB          174MB
ec-api:step5   fc84a4e1173c        380MB         91.4MB
ec-api:step6   c5f10c5cf81f        672MB          166MB
ec-api:step7   9a330e022bdb        672MB          166MB
```

✅ 検証済み: Docker Compose v5.5.1（2026-11-14）。手元と同じファイルを別の場所に写し、名前だけ `ec-api:p46b` にして確認した。ID は環境ごとに違います

`ec-api:dev` の行が増えていれば OK です。下の3行は、P2 で自分で作ったイメージです。

**🔬 1行ずつ分解**:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `image:` | イメージ（image） | `build:` と**一緒に書くと**、「作ったイメージに付ける名前」になる | 消すと、名前は自動の `roadmap-sh-docker-api` に戻る |
| `ec-api` | イーシー エーピーアイ（image name / repository） | 品名。何のイメージかを表す | — |
| `:dev` | コロン デブ（tag） | ラベル。同じ品名の中の、どの版かを表す | 書かないと `:latest` が付く |

**📖 しくみ**

- **何をしているか**: `build:` で作ったイメージに、`ec-api:dev` という**名札**（イメージ名とタグ）を貼っています。
- **なぜ必要か**: このあと作る worker も、**同じイメージ**を使いたいからです。名前が決まっていれば、2つのサービスが「`ec-api:dev` を使う」と同じ名前で指せます。
- **どういう原理で動くか**: `image:` の意味は、`build:` があるかどうかで変わります。
  1. `build:` が**無い**とき（`db` の `image: mysql:8.4`）: Compose は、その名前のイメージを**取ってくる**（pull）。
  2. `build:` が**ある**とき（今回）: Compose は、まず `Dockerfile` からイメージを**作る**（build）。そして、できたイメージに `image:` の名前を**付ける**。
  
  どちらでも `image:` は「イメージの名前」です。違うのは、**取ってくるのか、作って名付けるのか**だけです。
  根拠: https://docs.docker.com/reference/compose-file/build/#using-build-and-image

---

### チャンク2: worker を足し、起動する命令を決める（`compose.yaml` の新しい `worker`）— 地図の右下

> 📇 **command:** — 正式名称: **command**（Compose ファイルの `command` 属性）。Dockerfile の **CMD** を**上書きする**もの
> かみくだくと: 段ボールに書いてある「開けたらまずこれをする」（CMD）を、**このコンテナだけ別の指示に貼り替える**付箋。
> 似た言葉との違い: `ENTRYPOINT` = 毎回かならず最初に通る**玄関**（ここでは `./entrypoint.sh`）。`command:` は、玄関を通ったあとに**何をするか**だけを変える。玄関は変わらない。
> この教材では: worker だけ、`runserver` の代わりに `celery worker` を起動する。

**🤔 先に考える**: worker も api と同じイメージ `ec-api:dev` を使います。**何も変えずに起動すると、worker の中では何が動くと思いますか？**
A. Celery のワーカー　B. api と同じ `runserver`

<details><summary>答え</summary>

**B** です。イメージには `CMD [".venv/bin/python", "src/manage.py", "runserver", ...]` が書いてあります（`apps/api/Dockerfile` の最後の行）。何も変えなければ、同じ `runserver` が動きます。だから `command:` で付箋を貼り替えます。（このチャンクの 🧪 で、実際に確かめます）

</details>

**🎯 書くもの**: `api` のブロックの**後ろ**（`redis:` の前）に、新しいサービス `worker` を足す。`api` と同じ場所からビルドし、同じ名前 `ec-api:dev` を付ける。そして、起動する命令を Celery のワーカーに置き換える。

**✍️ 自分で書く**: `build:` と `image:` は、チャンク1 の `api` と同じ2行です。`command:` は**初めて出る形**なので、**先に下の分解表を読んでから、手で打ちます。コピペはしません。**

```yaml
    worker:
        build: ./apps/api
        image: ec-api:dev
        command: [".venv/bin/celery", "--workdir", "src", "-A", "config", "worker", "--loglevel", "info"]
```

**🔬 1行ずつ分解**（打つ前に読む）:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `worker:` | ワーカー（service name） | サービスの名前。`docker compose logs worker` のように、コマンドでこの名前を使う | — |
| `build: ./apps/api` | ビルド | api と**同じ場所**から作る | — |
| `image: ec-api:dev` | イメージ | api と**同じ名前**を付ける。だから中身も同じ | — |
| `command:` | コマンド（command） | イメージの `CMD` を、このサービスだけ置き換える | 消すと `CMD` のまま。worker の中で `runserver` が動く（🧪 で試す） |
| `[ ... ]` | 角かっこ（exec form / JSON 配列の形） | 命令を**1語ずつ区切って**渡す書き方。Dockerfile の `CMD [...]` と同じ形 | 区切りを間違えると、1語のつもりの文字が2語に分かれたりする |
| `".venv/bin/celery"` | セロリ（Celery の command line program） | 準備で入れた Celery の**起動プログラム**。`.venv/bin/` の中にある | — |
| `"--workdir", "src"` | ワークディレクトリ | 「`src` に移動してから始めて」。`config/` は `src/` の中にあるので、そこから探せるようにする | 消すと、`/app` から探すので見つからない。`Unable to load celery application. The module config was not found.` で止まる（✅ 検証済み） |
| `"-A", "config"` | エー（app の略） | 「Celery の本体（app）は `config` にある」。Celery は `config` の中の `celery.py` から `app` を探す | `confg` と打ち間違えると `The module confg was not found.` で止まる（✅ 検証済み） |
| `"worker"` | ワーカー | 「**ワーカーとして**動いて」。受付箱を見張り、メモが来たら仕事をする係 | — |
| `"--loglevel", "info"` | ログレベル（log level） | どこまで細かくログを出すか。`info` = ふつうの知らせまで出す | `warning` にすると、`info` の知らせ（`Connected to ...` など）は出なくなる |

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
             - front
             - back
 
+    worker:
+        build: ./apps/api
+        image: ec-api:dev
+        command: [".venv/bin/celery", "--workdir", "src", "-A", "config", "worker", "--loglevel", "info"]
+
     redis:
         image: redis:8-alpine
```

</details>

**▶️ 確かめる**: まだ起動はしません。Compose が `command:` を**どう区切って受け取ったか**を見ます（P4-5 の `docker compose config`）。

```bash
docker compose config worker | grep -A9 'command:'
```

```text
    command:
      - .venv/bin/celery
      - --workdir
      - src
      - -A
      - config
      - worker
      - --loglevel
      - info
    image: ec-api:dev
```

✅ 検証済み: Docker Compose v5.5.1（2026-11-14）

**1語ずつ、8つに分かれていれば OK です。** 分解表の行と見比べてみてください。

**📖 しくみ**

- **何をしているか**: api と同じイメージから、もう1つのサービス `worker` を作っています。そして、起動するときの命令（**CMD**、つまり段ボールに書いてある「開けたらまずこれ」）を、`command:` で Celery のワーカーに貼り替えています。
- **なぜ必要か**: worker が使うコード（このあと書く `tasks.py`）も、DB の設定も、api と同じだからです。イメージを1つにすると、**api と worker でコードの版がずれません**。違うのは「何を起動するか」だけなので、そこだけを `command:` で変えます。
- **どういう原理で動くか**: コンテナが起動するとき、Docker は **ENTRYPOINT**（玄関）と **CMD**（その後の命令）をつなげて、1本の命令にします。

  ```text
  api:    ./entrypoint.sh  .venv/bin/python src/manage.py runserver 0.0.0.0:8000
          └─ ENTRYPOINT ─┘ └──────────── CMD（イメージのまま）───────────┘

  worker: ./entrypoint.sh  .venv/bin/celery --workdir src -A config worker ...
          └─ ENTRYPOINT ─┘ └──────────── command:（貼り替えた）──────────┘
  ```

  `entrypoint.sh` の最後は `exec "$@"` です（P2-5）。`"$@"` には、後ろの命令がそのまま入ります。そして `exec` で、`entrypoint.sh` 自身がその命令に**入れ替わります**。だから、worker のコンテナでいちばん最初に動くプロセス（**PID 1**）は、`celery` になります。

---

### チャンク3: worker に要るものだけを渡す（`compose.yaml` の `worker` の続き）— 地図のいちばん下

**🤔 先に考える**: `api` には、下の6つの設定があります。**worker にも要るのはどれでしょう？** 1つずつ「要る / 要らない」と、理由を一言で考えてみてください。

| api の設定 | 要る？ |
| --- | --- |
| ① `ports:`（8000 と 5678 を Mac に公開） | ？ |
| ② `env_file: ./apps/api/.env` | ？ |
| ③ `volumes: ./apps/api/src:/app/src` | ？ |
| ④ `networks:` の `front` | ？ |
| ⑤ `networks:` の `back` | ？ |
| ⑥ `depends_on:`（db が healthy、redis が started） | ？ |

<details><summary>ヒント</summary>

worker に話しかけるのは誰でしょう？ Mac のブラウザ？ web コンテナ？ それとも、誰も話しかけない？ そして、worker が話しかける相手は誰でしょう？

</details>

<details><summary>答え</summary>

| api の設定 | 要る？ | 理由 |
| --- | --- | --- |
| ① `ports:` | **要らない** | worker に話しかける人はいない。worker は自分から受付箱を見に行く |
| ② `env_file:` | **要る** | 受付箱の場所 `BROKER_URL`（P4-6a）と、DB の接続先が入っている |
| ③ `volumes:`（src） | **要る** | Mac で書いたコードを、コンテナの中にすぐ写すため。`tasks.py` を書いたとき、作り直さずに使える |
| ④ `front` | **要らない** | `front` は web と api が話す道。worker は画面とは話さない |
| ⑤ `back` | **要る** | Redis と DB がいる道。受付箱（Redis）に行くのに要る |
| ⑥ `depends_on:` | **要る** | 受付箱（Redis）が無いと、つなぐ相手がいない。DB は P4-6f で商品を読むときに使う |

</details>

**🎯 書くもの**: `worker` の `command:` の**下**に、上で「要る」とした ②③⑤⑥ を書く。書き方は `api` と同じ。

**✍️ 自分で書く**（`depends_on:` `env_file:` `volumes:` `networks:` はどれも P4-1〜P4-5 で書いたので、日本語だけで書きます。`api` のブロックを**見ながら**書いてかまいません。ただし、**要らない ①④ は写さない**）

<details><summary>ヒント1: 書く順番</summary>

`depends_on:` → `env_file:` → `volumes:` → `networks:` の順。`api` と同じ順にすると見比べやすい。

</details>

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
         image: ec-api:dev
         command: [".venv/bin/celery", "--workdir", "src", "-A", "config", "worker", "--loglevel", "info"]
+        depends_on:
+            db:
+                condition: service_healthy
+            redis:
+                condition: service_started
+        env_file:
+            - ./apps/api/.env
+        volumes:
+            - ./apps/api/src:/app/src
+        networks:
+            - back
 
     redis:
```

</details>

**▶️ 確かめる**: worker を起動して、ログ（記録）を見ます。

```bash
docker compose up -d worker
docker compose logs worker
```

出力は長いです。**下の2行が出ていれば OK** です（時刻と `celery@` の後ろの英数字は、毎回違います）。

```text
worker-1  | [... INFO/MainProcess] Connected to redis://:**@redis:6379/1
worker-1  | [... INFO/MainProcess] celery@0d42f40193ee ready.
```

✅ 検証済み: Docker Compose v5.5.1 / Celery 5.6.3（2026-11-14）。手元と同じファイルを別の場所に写し、ポートを公開しない設定で起動して確認した

- `Connected to redis://...redis:6379/1` = 受付箱（Redis の 1番の部屋）に**つながった**。`:**@` は、Celery がパスワードの場所を伏せて表示したもの（今回はパスワードを付けていない）
- `ready.` = 準備ができた。メモが来るのを**待っている**

ほかにも、途中に次のような行が出ます。

| 出てくる行 | 意味 |
| --- | --- |
| `SecurityWarning: You're running the worker with superuser privileges` | 「管理者（root）で動いているよ。おすすめしない」という**注意**。止まるわけではない（下の 🔓） |
| `celery@... v5.6.3 (recovery)` | Celery の版。`recovery` は 5.6 系に付いた**愛称**（コードネーム）で、「復旧中」という意味ではない |
| `.> transport: redis://:**@redis:6379/1` | 受付箱の場所。P4-6a で `.env` に書いた値 |
| `.> concurrency: 12 (prefork)` | 同時にこなせる仕事の数。CPU の数で決まる（環境ごとに違う） |
| `[tasks]` の下が空 | **まだ仕事の種類が1つも無い**。P4-6e で作る |

**`docker compose logs -f`**: ログを**流し続けて**見たいときは、`-f` を付けます。

```bash
docker compose logs -f worker
```

> 📇 **logs -f** — 正式名称: `docker compose logs` の **--follow**（追いかける）オプション
> かみくだくと: ログを「いままでの分を見せて終わり」ではなく、**新しい行が出るたびに画面に足し続ける**。
> この教材では: 別のターミナルで開いておき、P4-6e でメモが届く瞬間を見る。止めるときは Ctrl+C。止めても worker は止まらない。

**📖 しくみ**

- **何をしているか**: worker に、仕事に要る3つ（設定 `env_file`、コード `volumes`、道 `networks`）だけを渡しています。要らないもの（公開ポート、`front` の道）は渡していません。
- **なぜ必要か**: コンテナは、渡されたものしか持っていません。`env_file:` が無ければ `BROKER_URL` を知りません。`networks: back` が無ければ、Redis までの道がありません。逆に、要らないものを渡すと、入口が増えて危なくなります。
- **どういう原理で動くか**: 起動すると、次の順に進みます。
  1. Compose が `depends_on:` を見て、db が healthy に、redis が started になるのを待つ
  2. Compose が worker コンテナを作り、`back` の道につなぐ。`.env` の中身を環境変数として渡す
  3. コンテナの中で `entrypoint.sh` → `celery` に入れ替わる（チャンク2）
  4. Celery が `-A config` で `celery.py` を読み、受付箱の場所 `redis://redis:6379/1` を知る（P4-6a の地図）
  5. Celery がサービス名 `redis` で Redis を探し、`back` の道を通ってつなぐ（`Connected to ...`）
  6. 受付箱を見張り始める（`ready.`）

<details><summary>💡 networks を書かないと、どうなる？</summary>

`networks:` を書かないサービスは、Compose が自動で作る **default**（既定の道）につながります。`docker compose config worker` で、`networks: default` と出ることで確かめられます（✅ 検証済み: 2026-11-14）。Redis は `back` にしかいないので、default の道からは届きません。

</details>

<details><summary>🔓 教材用の簡略化: worker が root で動いている</summary>

> 🔓 **教材用の簡略化**: worker は、コンテナの中の管理者（**root**、つまり何でもできる一番えらいユーザー）で動いています。Celery はそれを `SecurityWarning` で注意しています。`id` で見ると `uid=0(root)` です。
> **本番では**: P6-2 で、root ではないユーザーで動かします。
> 根拠: https://docs.celeryq.dev/en/stable/userguide/daemonizing.html#running-the-worker-with-superuser-privileges-root

</details>

**🧪 壊してみる**

1. **予想**: `worker` の `command:` の行を消して `docker compose up -d worker` をすると、worker の中で動く PID 1（いちばん最初のプロセス）は何になると思いますか？
   A. `celery`　B. `runserver`
2. **実行**: 行を消して保存し、次を打ちます。

   ```bash
   docker compose up -d worker
   docker compose exec worker cat /proc/1/cmdline | tr '\0' ' '; echo
   docker compose logs worker
   ```

3. **見る**:

   ```text
   .venv/bin/python src/manage.py runserver 0.0.0.0:8000
   ```

   ```text
   worker-1  | API を起動します
   worker-1  | Watching for file changes with StatReloader
   ```

   ✅ 検証済み: 2026-11-14

   **worker なのに、api と同じ `runserver` が動きました。** 名前が `worker` でも、中身は同じイメージです。`command:` で貼り替えなければ、イメージの `CMD` がそのまま動きます。ログにも `Connected to redis` は出ません。

   > 🐧 **Linux注**: `/proc/1/cmdline` には、PID 1 を起動した命令が入っています。区切りが見えない文字（`\0`）なので、`tr '\0' ' '` で空白に置き換えて読みます。このイメージ（`python:3.13-slim`）には `ps` が入っていないので、代わりにこれを使います。

4. **元に戻す**: `command:` の行を戻して、もう一度 `docker compose up -d worker` を打ちます。PID 1 を見て、次のように出れば元どおりです。

   ```text
   /app/.venv/bin/python .venv/bin/celery --workdir src -A config worker --loglevel info
   ```

   ✅ 検証済み: 2026-11-14

   頭に `python` が付いているのは、`celery` が Python で書かれたプログラムだからです。`entrypoint.sh` は、もう PID 1 に残っていません（チャンク2 の `exec`）。

### ✏️ 自分で地図を描く

冒頭の 🗺️ 今日の地図を**見ずに**、`＿＿＿` を埋めてみてください。紙でも、頭の中でもかまいません。最後の「なぜ」の欄には、一言ずつ書きます。

```text
イメージ ＿＿＿＿＿＿          なぜ1つ？ → ＿＿＿＿＿＿＿＿
        │
        ├──▶ api コンテナ
        │      イメージの ＿＿＿ のまま → runserver
        │
        └──▶ worker コンテナ
               ＿＿＿＿ で置き換える → celery worker
                       │   通る道（network）は ＿＿＿
                       ▼
               Redis の ＿ 番の部屋（受付箱）
```

<details><summary>答え合わせ</summary>

```text
イメージ ec-api:dev           なぜ1つ？ → api と worker でコードの版がずれないように
        │
        ├──▶ api コンテナ
        │      イメージの CMD のまま → runserver
        │
        └──▶ worker コンテナ
               command: で置き換える → celery worker
                       │   通る道（network）は back
                       ▼
               Redis の 1 番の部屋（受付箱）
```

埋められなかった所があれば、そのチャンクの 📖 しくみ だけ読み返します。

</details>

### 📝 ひとこと

「〜だと思っていたけど、実は〜」を1行書きます。書いたものは `docs/notes.md` に貯めます。うまく書けなければ、書かずに先へ進んでも大丈夫です。

例: 「worker は別のイメージが要ると思っていたけど、実は同じイメージで `command:` だけ変えればよかった」

### ✅ できるようになったこと

- [ ] `build:` と一緒に書いた `image:` が「作ったイメージに付ける名前」だと説明できる
- [ ] `command:` を消すと worker の中で何が動くかを、打つ前に予想できる
- [ ] worker に `ports:` と `front` が要らない理由を、一言で言える

**残った問い**: worker は受付箱を見張り始めた。でも、`[tasks]` の下は空っぽで、メモを入れる人もまだいない。そもそも、サムネイルの元になる**画像**は、どこから来るのか？ **api は、送られてきた画像をどこに保存すればいいのか？**

---
▶ **次**: P4-6c 画像を受け取って保存する

---

## P4-6c: 画像を受け取って保存する

**❓ この回の問い**: 前回（P4-6b）の答えは「worker は api と同じイメージで、受付箱を見張り始めた」だった。でも、サムネイルの元になる**画像**は、まだどこにも無い。
→ **api は、送られてきた画像を受け取って、どこに保存すればいいのか？**

**作ること / 確かめること**: Mac の `curl` から画像を送り、api コンテナの中に保存されることを確かめる。さらに、**api を作り直すと画像がどうなるか**を確かめる
**重要度**: 🔴 毎日使う — 「ファイルを受け取って置く」は、Web アプリでよく出る形だから
**前ステップとの接続**: P4-6b までの api に、受け取り口と置き場を足す

**P4-6 ぜんたいの地図での位置**: ①（api が画像を受け取って保存する）

### 🔁 前回の思い出し

**問い**: 全体の地図を描いたとき、redis の箱を消して作り直したら、`cart:test` はどうなりましたか？ そして、なぜでしたか？

<details><summary>答え</summary>

**消えました。** redis には倉庫（volume）が無いので、データは箱の中にしかありません。箱を消すと、データも一緒に消えます。db は倉庫 `db-data` があるので消えません。今日の 🧪 で、同じことが**画像**にも起きるかを確かめます。

</details>

### 🧭 全体の中のいま

`docs/02-system-map.md` の地図に、今日さわる所を ★ で示します。

```text
Mac の道具       窓口（④）              Docker の中

                                        【道 front】 web・api
ブラウザ      ── :5173 どこからでも ──▶ web ──▶ api（画面から API を呼ぶ）
curl          ── :8000 どこからでも ──▶ api   ★ 今日: 画像の受け取り口を足す
Zed           ── :5678 Mac だけ     ──▶ api（デバッガ）
                                        api の中に /app/media     ★ 今日: 画像の置き場（倉庫なし）

                                        【道 back】 api・worker・db・redis
                                        api ──▶ db、redis
DBeaver       ── :3306 Mac だけ     ──▶ db      倉庫 db-data（消えない）
                                                ★ 今日: 商品の表に image の列を足す
Redis Insight ── :6379 Mac だけ     ──▶ redis   倉庫なし（作り直すと消える）
                                                0番の部屋: カート / 1番の部屋: 受付箱
（窓口なし）                            worker ──▶ redis の 1番を見張る
```

**見てほしいところ**: 今日は **api の中**と **db の表**だけをさわります。新しい箱も、新しい道も増えません。

### 🗺️ 今日の地図

```text
Mac の curl
   │ 画像を送る（:8000 の窓口から）
   ▼
③ 受け取り口  api.py の upload_image         … チャンク3
   │
   ├──▶ 画像そのもの
   │      ② 置き場  settings.py の MEDIA_ROOT  … チャンク2
   │         → /app/media/products/sample.jpg（api コンテナの中）
   │
   └──▶ 置き場所の「文字」だけ
          ① 列  models.py の image             … チャンク1
             → db の表 catalog_product の image 列 = "products/sample.jpg"
```

**見てほしいところ**: 画像は**2か所に分かれて**記録されます。画像そのものはコンテナの中のフォルダへ。db には「どこに置いたか」という**文字だけ**が入ります。
作る順番（①→②→③）は、画像が流れる順番（③→②・①）の**逆**です。受け取り口を先に作っても、置き場と列が無ければ保存できないからです。

### 6c-0. このステップの初出

**Docker**: `docker compose exec -T`、`docker compose up --force-recreate`
**Linux**: なし
**その他**: Pillow、`ImageField`、`MEDIA_ROOT`、multipart/form-data

### 準備: Pillow を入れる

> 📇 **Pillow（ピロー）** — 正式名称: **Pillow**（Python Imaging Library の後継）
> かみくだくと: Python で**画像を開いたり、大きさを調べたり、縮めたり**するための部品。
> 似た言葉との違い: Celery（P4-6a）= 仕事を**あとで別の係に頼む**部品。Pillow = **画像そのもの**を扱う部品。
> この教材では: チャンク1 の `ImageField` が、送られてきたものが本当に画像かを調べるのに使う。P4-6f でサムネイルを作るのにも使う。

P4-6a の Celery と同じ入れ方です。コマンドなので、そのまま打ちます。

**実行場所**: リポジトリのいちばん上（`roadmap-sh-docker/`）

```bash
cd apps/api
uv add --no-sync 'pillow>=13.0,<13.1'
cd ../..
grep -A1 'name = "pillow"$' apps/api/uv.lock
```

```text
name = "pillow"
version = "13.0.0"
```

✅ 検証済み: uv 0.13.7（Mac）/ 2026-11-15

部品が入ったイメージを作り直し、api と worker を入れ替えます。2つは同じイメージ `ec-api:dev` を使っているので（P4-6b）、両方を入れ替えます。

```bash
docker compose build api
docker compose up -d api worker
```

`docker compose ps` で、api と worker がどちらも `Up` になっていれば OK です。

---
### チャンク1: 商品の表に「画像の置き場所」の列を足す（`apps/api/src/catalog/models.py`）— 地図の①

**このチャンクの目的**: 商品が「自分の画像はどこにあるか」を覚えておけるようにする。

> 📇 **ImageField** — 正式名称: Django の **ImageField**（画像用のフィールド）。仲間に **FileField**（ファイル用のフィールド）がある
> かみくだくと: 商品の表に足す**「画像の置き場所メモ」の列**。画像そのものではなく、置き場所の文字を覚える。
> 似た言葉との違い: `CharField`（名前の列）= 文字をそのまま覚える。`ImageField` = 文字（置き場所）を覚えるうえに、**保存のときに画像かどうかを Pillow で調べ、ファイルの保存も引き受ける**。
> この教材では: `Product`（商品）に `image` という列を足す。

**🤔 先に考える**: 画像を保存したとき、db（MySQL）の表には何が入ると思いますか？
A. 画像そのもの（写真のデータ）　B. 画像の置き場所を表す**文字**だけ

理由も一言で（「分からない」でも大丈夫です）。

<details><summary>答え</summary>

**B** です。db には `"products/sample.jpg"` のような**文字だけ**が入ります。画像そのものは、ファイルとしてフォルダに置きます（チャンク2）。

このチャンクの ▶️ が終わったら、次のコマンドで、db に足される列を SQL（db への命令文）で見られます。

```bash
docker compose exec api .venv/bin/python src/manage.py sqlmigrate catalog 0002
```

```text
--
-- Add field image to product
--
ALTER TABLE `catalog_product` ADD COLUMN `image` varchar(100) DEFAULT '' NOT NULL;
ALTER TABLE `catalog_product` ALTER COLUMN `image` DROP DEFAULT;
```

✅ 検証済み: Django 5.2 / MySQL 8.4（2026-11-15）

`varchar(100)` は「**100文字までの文字**」という型です。画像そのものを入れる型ではありません。

</details>

**🎯 書くもの**: `models.py` の `description = ...` の**すぐ下**に、`image` という列を1行足す。保存先のフォルダ名は `products/`。画像が無い商品もあってよい。

**🔬 1行ずつ分解**（初めて出る形なので、**先に読んでから手で打ちます**）:

`image = models.ImageField(upload_to="products/", blank=True)`

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `image` | イメージ | 列の名前。db の表では `image` という列になる | 名前を変えると、列の名前も変わる |
| `models.ImageField` | イメージフィールド（ImageField） | 画像の置き場所を覚える列の型 | Pillow が無いと、起動の点検で止まる: `(fields.E210) Cannot use ImageField because Pillow is not installed.`（✅ 検証済み: 2026-11-15） |
| `upload_to="products/"` | アップロード トゥー（upload_to） | 置き場（チャンク2）の中の、**どのフォルダ**に入れるか | 変えると、別のフォルダに入る |
| `blank=True` | ブランク（blank） | 「画像が無い商品があってもよい」 | 消すと、Django の入力チェックで「画像は**必須**」になる。db の列そのものは変わらない。今ある3つの商品は画像を持っていないので、空を許しておく |

**✍️ 自分で書く**: 上の1行を、表を思い出しながら手で打ちます。コピペはしません。

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
     price = models.PositiveIntegerField()
     description = models.TextField(blank=True)
+    image = models.ImageField(upload_to="products/", blank=True)
 
     def __str__(self):
```

</details>

**▶️ 確かめる**: 列を足すための設計図（マイグレーション）を作り、db に当てます。

```bash
docker compose exec api .venv/bin/python src/manage.py makemigrations catalog
docker compose exec api .venv/bin/python src/manage.py migrate
```

```text
Migrations for 'catalog':
  src/catalog/migrations/0002_product_image.py
    + Add field image to product
```

```text
Operations to perform:
  Apply all migrations: catalog
Running migrations:
  Applying catalog.0002_product_image... OK
```

✅ 検証済み: Django 5.2 / MySQL 8.4（2026-11-15）

`Applying ... OK` が出れば、db の表に `image` 列ができています。設計図のファイル `0002_product_image.py` は、bind mount を通って **Mac の `apps/api/src/catalog/migrations/` にも**できています。

**🔎 答えの見つけ方**: 設計図が db に当たったかは `docker compose exec api .venv/bin/python src/manage.py showmigrations catalog`。`[X] 0002_product_image` と、`X` が付いていれば当たっている。どんな SQL になるかは `sqlmigrate`（🤔 の答え）。

**📖 しくみ**

- **何をしているか**: 商品の表 `catalog_product` に、`image` という**文字の列**を足しています。
- **なぜ必要か**: 画像のファイルは、フォルダに置いただけでは「どの商品の画像か」が分かりません。商品の行に置き場所を書いておけば、商品から画像をたどれます。画像そのものを db に入れないのは、db を重く遅くしないためです。Django の公式ドキュメントにも「db に入るのはファイルへの道筋（パス）だけ」と書いてあります。
  根拠: https://docs.djangoproject.com/en/5.2/ref/models/fields/#filefield
- **どういう原理で動くか**:
  1. あなたが `models.py` に1行足す（まだ db は変わらない）
  2. `makemigrations` を打つと、**Django** が `models.py` と今までの設計図を見比べ、差分を `0002_product_image.py` に書く
  3. `migrate` を打つと、**Django** がその設計図を SQL（`ALTER TABLE ... ADD COLUMN`）に直して、**MySQL** に送る
  4. **MySQL** が表に列を足す。db の中身は倉庫 `db-data` にあるので、箱を作り直しても列は残る

---
### チャンク2: 画像そのものの置き場を決める（`apps/api/src/config/settings.py`）— 地図の②

**このチャンクの目的**: 画像のファイルを、コンテナの中の**どのフォルダ**に置くかを決める。

> 📇 **MEDIA_ROOT** — 正式名称: Django の設定 **MEDIA_ROOT**（メディア ルート）。media files（利用者がアップロードしたファイル）の置き場の**根っこ**
> かみくだくと: 送られてきた画像を入れる**いちばん上のフォルダ**。チャンク1 の `upload_to="products/"` は、この中のフォルダ。
> 似た言葉との違い: `MEDIA_URL`（メディア ユーアールエル）= その画像を**ブラウザから見るときの住所**。P4-6g で使う。今日は置き場だけ決める。
> この教材では: `/app/media`（api コンテナの中のフォルダ）。

**🤔 先に考える**: もし `MEDIA_ROOT` を書かずに画像を保存したら、どうなると思いますか？
A. 保存できずにエラーになる　B. エラーにならず、どこか別の場所に置かれる

<details><summary>答え</summary>

**B** です。`MEDIA_ROOT` の初期値は `''`（空っぽ）です。空っぽだと、Django は「いま居るフォルダ」を根っこにします。api コンテナで居るフォルダは `/app`（Dockerfile の `WORKDIR /app`、P2）なので、画像は `/app/products/sample.jpg` に置かれます。コードの近くに、画像がばらばらに散らばってしまいます。

✅ 検証済み: 2026-11-15（`MEDIA_ROOT` を消して送り、`/app/products/sample.jpg` ができるのを確かめた）

</details>

**🎯 書くもの**: `settings.py` の**いちばん下**（`CELERY_BROKER_URL = ...` の下）に、置き場を `/app/media` にする1行を足す。

**✍️ 自分で書く**（`名前 = "値"` の形は P4-5・P4-6a で書いたので、穴埋めです）

```python
CELERY_BROKER_URL = os.environ["BROKER_URL"]

___ = "___"
```

<details><summary>ヒント1</summary>

1つ目の `___` は、📇 カードの名前です。2つ目は、🧭 の地図に書いた api の中のフォルダです。

</details>

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
 REDIS_URL = os.environ["REDIS_URL"]
 CELERY_BROKER_URL = os.environ["BROKER_URL"]
+
+MEDIA_ROOT = "/app/media"
```

</details>

**▶️ 確かめる**: Django が置き場を知っているかを聞きます。

```bash
docker compose exec api .venv/bin/python src/manage.py shell -c "from django.conf import settings; print(settings.MEDIA_ROOT)"
```

```text
1 object imported automatically (use -v 2 for details).

/app/media
```

✅ 検証済み: Django 5.2（2026-11-15）

最後の行が `/app/media` なら OK です。P4-6a の `run` と違って、`exec` は動いている箱の中で打つだけなので、`API を起動します` の行は出ません。

**🔎 答えの見つけ方**: 置き場のフォルダが**本当にあるか**は、`docker compose exec api ls /app/media`。いまは `No such file or directory`（まだ無い）と出ます。フォルダは、最初の画像を保存したときに Django が作ります（チャンク3 で確かめます）。

**🔬 1行ずつ分解**:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `MEDIA_ROOT` | メディア ルート（MEDIA_ROOT） | 送られてきたファイルの置き場の根っこ。Django が決まった名前で探す | 消すと、いま居るフォルダ `/app` が根っこになる（🤔 の答え） |
| `"/app/media"` | — | api コンテナの中のフォルダ。`/` で始まるので、どこに居ても同じ場所を指す（絶対パス） | — |

**📖 しくみ**

- **何をしているか**: 画像のファイルを置く、いちばん上のフォルダを `/app/media` に決めています。
- **なぜ必要か**: 決めないと、画像がコードのすぐ横（`/app/products/`）に散らばります。置き場を1つにまとめておけば、あとで**そのフォルダだけを倉庫（volume）にする**ことができます（P4-6d への伏線）。
- **どういう原理で動くか**: 保存するとき、**Django** が3つをつないで置き場所を決めます。

  ```text
  MEDIA_ROOT        upload_to        送られてきたファイル名
  /app/media   +   products/    +   sample.jpg
        ↓
  /app/media/products/sample.jpg   ← ファイルはここに置く
           products/sample.jpg     ← db の image 列にはここだけ書く
  ```

  db に入るのは、`MEDIA_ROOT` から**先の部分だけ**です。だから、あとで置き場を変えても、db の文字は書き換えなくて済みます。

---
### チャンク3: 画像の受け取り口を作る（`apps/api/src/config/api.py`）— 地図の③

**このチャンクの目的**: Mac から送られてきた画像を受け取り、チャンク1・2 で決めた場所に保存する**窓口**を作る。

> 📇 **multipart/form-data** — 正式名称: **multipart/form-data**（マルチパート フォームデータ）。HTTP でファイルを送るときの**送り方の形**
> かみくだくと: 1回の送信を**いくつかの区切り（パート）**に分けて、文字もファイルもまとめて送れる形。Web ページの「ファイルを選ぶ」ボタン付きフォームが使っているのと同じ。
> 似た言葉との違い: JSON（P4-5 のカート）= **文字だけ**を送る形。画像のような中身（バイナリ）は、そのままでは入れられない。
> この教材では: `curl -F image=@...` が、この形で送る。受け取る側は Django Ninja の `File[UploadedFile]`。

**🤔 先に考える**: カート（P4-5）は JSON で送りました。画像も、同じ JSON の形で送れると思いますか？
A. 送れる　B. 別の形が要る

<details><summary>答え</summary>

**B** です。JSON は文字だけを入れる形です。このチャンクで作る窓口に JSON を送ると、「`image` が無い」と断られます。

```text
{"detail": [{"type": "missing", "loc": ["file", "image"], "msg": "Field required"}]}
```

✅ 検証済み: 2026-11-15（JSON で送ると `422` が返る）

`"loc": ["file", "image"]` は「**ファイルの**区切りの中に `image` が無い」という意味です。窓口は、multipart/form-data の形でファイルが届くのを待っています。

</details>

**🎯 書くもの**: 2か所を変える。

1. いちばん上の `from ninja import ...` の行に、`File` と `UploadedFile` を足す
2. `@api.get("/cart")` の**すぐ前**に、`POST /products/{product_id}/image` の窓口を5行で書く。商品を探し、その商品の `image` に保存し、`{"status": "saved"}` を返す

**✍️ 自分で書く — その1**（import は、足す2つの名前を埋める穴埋めです）

```python
from ninja import ___, Header, ModelSchema, NinjaAPI, Schema, ___
```

<details><summary>答え合わせ</summary>

```diff
-from ninja import Header, ModelSchema, NinjaAPI, Schema
+from ninja import File, Header, ModelSchema, NinjaAPI, Schema, UploadedFile
```

名前は ABC 順（大文字が先）に並べています。順番が違っても動きます。

</details>

**🔬 1行ずつ分解**（窓口の5行は初めて出る形なので、**先に読んでから手で打ちます**）:

```python
@api.post("/products/{product_id}/image")
def upload_image(request, product_id: int, image: File[UploadedFile]):
    product = get_object_or_404(Product, id=product_id)
    product.image.save(image.name, image)
    return {"status": "saved"}
```

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `@api.post(...)` | デコレータ（decorator） | 「`POST` でこの住所に来たら、下の関数を呼ぶ」。P4-5 のカートと同じ形 | `get` にすると、`curl -F` の送信は受け付けられない |
| `{product_id}` | パスパラメータ（path parameter） | 住所の中の、商品番号が入る場所 | — |
| `product_id: int` | — | 住所の `{product_id}` を数として受け取る | — |
| `image: File[UploadedFile]` | アップロードファイル（UploadedFile） | multipart/form-data の中の `image` という区切りを、**ファイルとして**受け取る | `image` を付けずに送ると `422`（`"msg": "Field required"`）。✅ 検証済み |
| `get_object_or_404(...)` | ゲット オブジェクト オア フォーオーフォー | 商品を探す。無ければ `404` を返して止める | 無い番号（999）だと `{"detail": "Not Found: No Product matches the given query."}`。✅ 検証済み |
| `product.image.save(名前, 中身)` | フィールドファイルの save（FieldFile.save） | ①ファイルを置き場に書き、②db の `image` 列に置き場所を書き、③商品の行を保存する。**この1行で3つ** | 消すと、受け取っただけで何も残らない |
| `image.name` | — | 送られてきたファイルの名前（`sample.jpg`） | — |
| `return {"status": "saved"}` | — | 「保存した」と返事をする | — |

**✍️ 自分で書く — その2**: 上の5行を、表を思い出しながら手で打ちます。コピペはしません。`@api.get("/cart")` の**前**に、空行を2行あけて置きます。

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
     return get_object_or_404(Product, id=product_id)
 
 
+@api.post("/products/{product_id}/image")
+def upload_image(request, product_id: int, image: File[UploadedFile]):
+    product = get_object_or_404(Product, id=product_id)
+    product.image.save(image.name, image)
+    return {"status": "saved"}
+
+
 @api.get("/cart")
 def get_cart(request, cart_id: str = Header(alias="X-Cart-Id")):
```

</details>

**▶️ 確かめる**: 送る画像を用意して、送って、置かれたかを見ます。ここはコマンドなので、そのまま打ちます。

まず、送る画像を作ります。Pillow が入った api コンテナで、薄茶色の四角い画像を作り、Mac の `/tmp/sample.jpg` に受け取ります。

```bash
docker compose exec -T api .venv/bin/python -c "import sys; from PIL import Image; Image.new('RGB', (1200, 800), 'tan').save(sys.stdout.buffer, 'JPEG')" > /tmp/sample.jpg
file /tmp/sample.jpg
```

```text
/tmp/sample.jpg: JPEG image data, JFIF standard 1.01, ... 1200x800, components 3
```

`-T` は「コンテナの出力を、そのまま受け取る」指定です。付けないと、画面に表示するための変換が混ざって、画像が壊れることがあります。

次に、送ります。全体の地図（`docs/02-system-map.md`）の `curl ── :8000` の窓口を通ります。

```bash
curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
docker compose exec api ls /app/media/products/
```

```text
{"status": "saved"}
sample.jpg
```

✅ 検証済み: 2026-11-15。手元と同じファイルを別の場所に写して確認した（イメージ名は `ec-api:p46c`。`curl` は Mac からではなく、front の道の中から api に送った）

`sample.jpg` が見えれば、画像は api コンテナの `/app/media/products/` に置かれています。チャンク2 の 🔎 で「まだ無い」と言われたフォルダを、Django が作りました。

> 💡 同じ名前でもう一度送ると、上書きはされません。Django が `sample_LqBfnuc.jpg` のように、後ろに文字を足して別の名前にします（文字は毎回違います）。✅ 検証済み

**🔎 答えの見つけ方**: 送ったのに置かれていないときは、`docker compose logs api` の最後を見ます。`"POST /api/products/1/image HTTP/1.1" 200 19` なら成功、`404` は商品が無い、`422` は送り方の形か名前（`image`）が違う、です。

**📖 しくみ**

- **何をしているか**: Mac から届いた画像を、商品1番の画像として保存する窓口を作りました。
- **なぜ必要か**: サムネイルを作るには、まず元の画像が要ります。worker（P4-6b）が仕事をするための、**材料を受け取る入口**です。
- **どういう原理で動くか**:
  1. **Mac の curl** が、画像を multipart/form-data の形で `localhost:8000` に送る
  2. ポート公開（`8000:8000`）を通って、**api コンテナの runserver** に届く
  3. **Django Ninja** が住所 `/api/products/1/image` を見て、`upload_image` を呼ぶ。`image` の区切りを `UploadedFile` にして渡す
  4. `get_object_or_404` が、**MySQL** から商品1番を探す
  5. `product.image.save` が、**Pillow** で画像かを確かめ、`/app/media/products/sample.jpg` にファイルを書き、**MySQL** の `image` 列に `products/sample.jpg` と書く
  6. `{"status": "saved"}` を返す

**🧪 壊してみる**

今日の画像は、**api コンテナの中のフォルダ**に置きました。全体の地図を描いたときの redis と比べてみましょう。

1. **予想**: api の箱を作り直したら、`/app/media/products/sample.jpg` はどうなると思いますか？
   A. 残る　B. 消える
2. **実行**: `--force-recreate`（設定が変わっていなくても、箱を**作り直す**指定）を付けて、api だけを作り直します。

   ```bash
   docker compose up -d --force-recreate api
   docker compose exec api ls /app/media/products/
   ```

3. **見る**:

   ```text
   ls: cannot access '/app/media/products/': No such file or directory
   ```

   ✅ 検証済み: 2026-11-15

   部品に分けて読みます。

   | 部品 | 意味 |
   | --- | --- |
   | `ls:` | `ls` コマンドからの知らせ |
   | `cannot access '/app/media/products/'` | このフォルダを見られない |
   | `No such file or directory` | **そんなファイルもフォルダも無い** |

   **画像は、フォルダごと消えました。** redis のカートと同じです。api には `/app/media` 用の倉庫（volume）が無いので、ファイルは箱の中にしかありません。箱を作り直すと、一緒に消えます。

4. **db のほうはどうか**: 次を打ちます。

   ```bash
   docker compose exec api .venv/bin/python src/manage.py shell -c "import os; from catalog.models import Product; p = Product.objects.get(id=1); print(p.image.name); print(os.path.exists(p.image.path))"
   ```

   ```text
   1 object imported automatically (use -v 2 for details).

   products/sample.jpg
   False
   ```

   ✅ 検証済み: 2026-11-15

   db の `image` 列には `products/sample.jpg` が**残っています**（db は倉庫 `db-data` があるから）。でも `os.path.exists`（そのファイルは本当にある？）は `False`（無い）です。**db は「ここにある」と言っているのに、ファイルが無い**という食い違いが起きました。

   元に戻すものはありません。画像は P4-6d で倉庫を作ってから、もう一度送ります。

### ✏️ 自分で地図を描く

冒頭の 🗺️ 今日の地図を**見ずに**、`＿＿＿` を埋めてみてください。最後の2つの「なぜ」には、一言ずつ書きます。

```text
Mac の curl
   │ 画像を ＿＿＿＿＿＿＿＿＿ の形で送る（JSON ではない）
   ▼
③ 受け取り口  api.py の upload_image
   │
   ├──▶ 画像そのもの → ＿＿＿＿＿＿/products/sample.jpg
   │                    （settings.py の ＿＿＿＿＿＿ で決めた）
   │
   └──▶ 置き場所の「文字」だけ → db の ＿＿＿＿ 列

なぜ、画像そのものを db に入れない？   → ＿＿＿＿＿＿＿＿
api を作り直すと、画像はどうなる？     → ＿＿＿＿（理由: ＿＿＿＿＿＿＿＿）
```

<details><summary>答え合わせ</summary>

```text
Mac の curl
   │ 画像を multipart/form-data の形で送る（JSON ではない）
   ▼
③ 受け取り口  api.py の upload_image
   │
   ├──▶ 画像そのもの → /app/media/products/sample.jpg
   │                    （settings.py の MEDIA_ROOT で決めた）
   │
   └──▶ 置き場所の「文字」だけ → db の image 列

なぜ、画像そのものを db に入れない？   → db を重く遅くしないため。db には置き場所の文字だけ
api を作り直すと、画像はどうなる？     → 消える（理由: /app/media に倉庫が無く、箱の中にしか無いから）
```

埋められなかった所があれば、そのチャンクの 📖 しくみ だけ読み返します。

</details>

### 📝 ひとこと

「〜だと思っていたけど、実は〜」を1行書きます。書いたものは `docs/notes.md` に貯めます。うまく書けなければ、書かずに先へ進んでも大丈夫です。

例: 「画像は db に入ると思っていたけど、実は db には置き場所の文字だけが入っていた」

### ✅ できるようになったこと

- [ ] 画像を保存したとき、ファイルと db にそれぞれ何が入るかを説明できる
- [ ] `MEDIA_ROOT` と `upload_to` から、ファイルの置き場所を組み立てられる
- [ ] api の箱を作り直したら画像がどうなるかを、打つ前に予想できる

**残った問い**: 画像は、api の箱を作り直すと消えてしまった。それに、worker の箱の中にも `/app/media` は無い（`docker compose exec worker ls /app/media` → `No such file or directory`。✅ 検証済み）。**画像を消えない倉庫に置き、しかも worker からも見えるようにするには、どうすればいいのか？**

---
▶ **次**: P4-6d 画像の倉庫を作って worker と分け合う

---

## P4-6d: 画像の倉庫を作って worker と分け合う

**❓ この回の問い**: 前回（P4-6c）の答えは「画像は api の箱の中に置かれ、箱を作り直すと消える。worker の箱には `/app/media` すら無い」だった。
→ **画像を消えない場所に置き、しかも worker からも見えるようにするには、どうすればいいのか？**

**作ること / 確かめること**: 画像用の倉庫（volume）を1つ作り、api と worker の**両方**につなぐ。api を作り直しても画像が残ること、worker から同じ画像が見えることを確かめる
**重要度**: 🔴 毎日使う — 「データは箱の外の倉庫に置く」「1つの倉庫を2つの箱で分け合う」は、Compose でよく出る形だから
**前ステップとの接続**: P4-6c で api の中に作った `/app/media` を、倉庫につなぎ替える。`compose.yaml` だけを変える。コード（`.py`）は変えない

**P4-6 ぜんたいの地図での位置**: ①④の準備（①で受け取った画像を、④で worker が読めるようにする）

### 🔁 前回の思い出し

**問い**: 画像を保存したとき、db（MySQL）の `image` 列に入ったのは、A と B のどちらでしたか？
A. 画像そのもの　B. 置き場所を表す文字（`products/sample.jpg`）

<details><summary>答え</summary>

**B** です。db には置き場所の**文字だけ**が入り、画像そのものは `/app/media/products/` のファイルでした。だから P4-6c の 🧪 で api を作り直したとき、db には `products/sample.jpg` が**残ったのに**、ファイルは**消えて**、食い違いが起きました。今日はこの食い違いを直します。

</details>

### 🛠️ 先に自分で決める

教材が答えを出す前に、**あなたが直し方を決めます。** このあとのチャンクは、あなたの選んだ方針の答え合わせとして進みます。

**困りごと**（P4-6c の 🧪 と残った問いで見えたこと）

1. api の箱を作り直すと、`/app/media` の画像が消える（db の文字は残るので、食い違う）
2. worker の箱には `/app/media` が無い。これでは worker がサムネイルを作れない

**🤔 どの直し方を選びますか？** 1つ選んで、理由を一言で書いてください（「分からない」でも大丈夫です）。

| 案 | 直し方 |
| --- | --- |
| A | 何もしない。api の箱を作り直さないように気をつける |
| B | **Mac のフォルダ**（例: `apps/api/media`）を、api と worker の `/app/media` に写す（bind mount。`src` と同じやり方） |
| C | **画像用の倉庫**（named volume）を1つ作り、api と worker の `/app/media` につなぐ（db の `db-data` と同じやり方） |

<details><summary>ヒント</summary>

全体の地図（`docs/02-system-map.md`）の「③ 倉庫（volume）」の表を見てください。この EC には、もう**2種類の倉庫**があります。`src`（Mac のフォルダを写す）と `db-data`（名前付きの倉庫）です。画像は「**コード**」と「**データ**」のどちらに近いでしょう？

</details>

<details><summary>答え合わせ</summary>

この教材は **C** で進めます。

| 案 | 判定 | 理由 |
| --- | --- | --- |
| A | ✗ | 箱の作り直しは毎日起きる（`compose.yaml` を変えて `up` したとき、イメージを作り直したとき）。それに、困りごと2（worker から見えない）が直らない |
| B | △ 動く | 実際に動きます。`.gitignore` に `media/` があるので、画像が git に入る心配もありません。ただ、**本番のサーバーには「Mac のフォルダ」がありません**。bind mount は「Mac で書いた**コード**をすぐ箱に写す」ための開発用の道具です |
| C | ◎ | 送られてきた画像は、コードではなく、お客さんや管理者が作った**データ**です。db のデータを `db-data` に置いたのと同じ考え方で、Docker が管理する倉庫に置きます。開発でも本番でも同じ形で使えます |

**B と C のどちらも「箱の外に置く」点は同じです。** 違うのは「どこに置くか」と「何のためか」です。B を選んだ人も、考え方の半分は合っています。

</details>

### 🐳 Docker の中の図（前）

いま（P4-6d を始める前）の、箱の中の様子です。

```text
【道 back】 にいる箱（api は front にもいる）

api の箱
  /app/src                  ◀── Mac の apps/api/src（bind mount）
  /app/media                倉庫なし。箱の中だけ（作り直すと消える）

worker の箱
  /app/src                  ◀── Mac の apps/api/src（bind mount）
  /app/media                無い

db の箱
  /var/lib/mysql            ◀── 倉庫 db-data

倉庫（named volume）: db-data
```

**見てほしいところ**: api の `/app/media` は、倉庫につながっていません。worker には `/app/media` そのものがありません。

### 🧭 全体の中のいま

`docs/02-system-map.md` の地図に、今日さわる所を ★ で示します。

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
                                        api・worker ──▶ 倉庫 media（画像）  ★ 今日: 新しい倉庫
```

**見てほしいところ**: 今日は**新しい倉庫を1つ**足して、api と worker につなぐだけです。新しい箱・道・窓口は増えません。

### 🗺️ 今日の地図

```text
compose.yaml
  │
  ├── ① いちばん外の volumes: に、倉庫 media を宣言する   … チャンク1
  │
  ├── ② api の volumes: で、/app/media を倉庫 media につなぐ  … チャンク2
  │
  └── ③ worker の volumes: で、/app/media を同じ倉庫 media につなぐ … チャンク3
```

**見てほしいところ**: 書くのは `compose.yaml` だけで、**全部で3行**です。①で「倉庫を用意する」、②③で「その倉庫を箱につなぐ」。db の `db-data` も、同じ2段階で書いてあります（P4-2）。

### 6d-0. このステップの初出

**Docker**: `docker compose config --volumes`、`docker volume inspect`
**Linux**: `mount`（何がどこにつながっているかを見るコマンド）
**その他**: なし（named volume・bind mount は P4-2 と全体の地図（`docs/02-system-map.md`）で出た言葉）

---

### チャンク1: 画像用の倉庫を宣言する（`compose.yaml` のいちばん外の `volumes:`）— 地図の①

**このチャンクの目的**: 「`media` という名前の倉庫を使います」と Compose に伝える。

**🤔 先に考える**: いちばん外の `volumes:` に `media:` と書いて保存しただけで、**倉庫は本当にできる**と思いますか？
A. できる　B. まだできない

理由も一言で（「分からない」でも大丈夫です）。

<details><summary>答え</summary>

**B** です。宣言しただけでは、まだどの箱も使っていないので、Compose は倉庫を作りません。✅ 検証済み（2026-11-17）

```bash
docker compose config --volumes
docker volume ls --filter name=roadmap-sh-docker
```

```text
db-data
roadmap-sh-docker_db-data
```

`media` はどちらにも出てきません。`docker compose config --volumes` は「**箱が使っている**倉庫の一覧」なので、宣言しただけの `media` は数に入りません。倉庫ができるのは、チャンク2 で箱につないで `up` したときです。

</details>

**🎯 書くもの**: `compose.yaml` のいちばん下のほうにある、いちばん外の `volumes:` の中に、`db-data:` と並べて `media:` を1行足す。

**✍️ 自分で書く**（P4-2 で `db-data:` を書いたので、日本語だけで書きます）

<details><summary>ヒント1: どこに書く？</summary>

`services:` と同じ深さ（左端）にある `volumes:` です。その下の `db-data:` と、左端をそろえます。

</details>

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
 volumes:
     db-data:
+    media:
 
 networks:
```

</details>

**▶️ 確かめる**: 書き方が正しいかだけを見ます。

```bash
docker compose config --quiet
```

何も出なければ OK です。✅ 検証済み（2026-11-17）

**🔎 答えの見つけ方**: 「倉庫がちゃんと箱に使われているか」は `docker compose config --volumes`。「Docker の中に倉庫が本当にできたか」は `docker volume ls`。この2つは**別のもの**を見ています。

**🔬 1行ずつ分解**:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| いちばん外の `volumes:` | ボリュームズ（top-level volumes） | この `compose.yaml` で使う**倉庫の名簿** | — |
| `media:` | メディア | 名簿に `media` という倉庫を載せる。`:` の後ろが空なのは「設定は全部おまかせ」という意味 | 消すと、チャンク2・3 で `media` を使ったときにエラー（🧪 で確かめる） |

**📖 しくみ**

- **何をしているか**: `media` という名前の倉庫を、名簿に載せました。
- **なぜ必要か**: 箱の `volumes:` で `media` と書いたとき、それが「名前付きの倉庫」なのか「書き間違い」なのかを、Compose が名簿で確かめるためです。
- **どういう原理で動くか**: `docker compose up` のとき、**Compose** は名簿を読み、**どれかの箱が使っている倉庫だけ**を作ります。名前の頭には、フォルダ名から決まる**プロジェクト名**（project name、つまり「この Compose のまとまりの名前」）が付きます。だから本物の名前は `roadmap-sh-docker_media` になります。`db-data` が `roadmap-sh-docker_db-data` なのと同じです。

---

### チャンク2: api の画像置き場を倉庫につなぐ（`compose.yaml` の `api`）— 地図の②

**このチャンクの目的**: api の `/app/media` を、箱の中ではなく倉庫 `media` に置くようにする。

**🤔 先に考える**: これから api の `volumes:` に `- media:/app/media` を足します。すぐ上には `- ./apps/api/src:/app/src` があります。**`media:/app/media` の中で、Mac の場所を指しているのはどこ**だと思いますか？
A. 左の `media`　B. 右の `/app/media`　C. どちらも Mac ではない

<details><summary>答え</summary>

**C** です。左の `media` は**倉庫の名前**、右の `/app/media` は**箱の中の場所**です。

`./apps/api/src:/app/src` のほうは、左が `./` で始まっています。**`./` や `/` で始まると Mac のフォルダ**（bind mount）、**名前だけなら倉庫**（named volume）と、Compose は左側の書き方で見分けます。

</details>

**🎯 書くもの**: `api` の `volumes:` の、`- ./apps/api/src:/app/src` の**すぐ下**に1行足す。倉庫 `media` を、箱の中の `/app/media` につなぐ。

**✍️ 自分で書く**（`db` の `- db-data:/var/lib/mysql` と同じ形の2回目なので、穴埋めです）

```yaml
        volumes:
            - ./apps/api/src:/app/src
            - ___:/app/___
```

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
         volumes:
             - ./apps/api/src:/app/src
+            - media:/app/media
         networks:
             - front
```

</details>

**▶️ 確かめる**: api を作り直して、もう一度画像を送ります。そのあと、**わざと api を作り直して**、画像が残るかを見ます。

```bash
docker compose up -d api
docker compose config --volumes
docker volume ls --filter name=roadmap-sh-docker
```

```text
db-data
media
roadmap-sh-docker_db-data
roadmap-sh-docker_media
```

今度は `media` が両方に出ました。箱につないだので、Compose が倉庫を作りました。

> ⚠️ P4-6c で `DEBUGPY=1` を付けて api を起動していた場合、`docker compose up -d api` で**ふつうの起動に戻ります**（デバッガはつながらなくなります）。デバッグしたいときは、`DEBUGPY=1 docker compose up -d api` で起動し直してください。

画像を送ります。`/tmp/sample.jpg` が無ければ、P4-6c チャンク3 の ▶️ のコマンドで作り直します。

```bash
curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
docker compose exec api ls /app/media/products/
docker compose up -d --force-recreate api
docker compose exec api ls /app/media/products/
```

```text
{"status": "saved"}
sample.jpg
 Container roadmap-sh-docker-api-1 Started
sample.jpg
```

✅ 検証済み: 2026-11-17。手元と同じファイルを別の場所に写して確認した（プロジェクト名は `p46d`、イメージ名は `ec-api:p46d`。`curl` は Mac からではなく、front の道の中から api に送った）

**作り直したあとも `sample.jpg` が残りました。** P4-6c の 🧪 では消えていた画像です。

**🔎 答えの見つけ方**: 「箱の中のこの場所は、何につながっているか」は、箱の中で `mount` を打つと分かります。

```bash
docker compose exec api sh -c 'mount | grep /app/'
```

```text
virtiofs0 on /app/src type virtiofs (rw,nosuid,nodev,relatime,ignore_atime,no_xattr)
/dev/vda1 on /app/media type ext4 (rw,relatime,discard)
```

✅ 検証済み: 2026-11-17

`/app/src` は `virtiofs`（**Mac のフォルダを写す道**）、`/app/media` は `ext4`（**Docker の中のディスク**）です。2つは、つながっている先がまったく違います。

**🔬 1行ずつ分解**:

`- media:/app/media`

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `-` | ハイフン（リストの1項目） | `volumes:` の中の1つ | — |
| `media` | 倉庫の名前（volume name） | チャンク1 で名簿に載せた倉庫。**名前だけ**なので named volume | `./media` と書くと、Mac のフォルダ（bind mount）の意味に変わる |
| `:` | コロン（区切り） | 左が「何を」、右が「箱のどこに」 | — |
| `/app/media` | 箱の中の場所（container path） | `settings.py` の `MEDIA_ROOT`（P4-6c）と同じ場所 | `MEDIA_ROOT` と違う場所にすると、画像は倉庫に入らず、また箱の中に置かれる |

**📖 しくみ**

- **何をしているか**: api の箱の `/app/media` を、倉庫 `media` の**入口**にしました。
- **なぜ必要か**: 箱は作り直すと、中身が最初の状態に戻ります。倉庫は箱の外にあるので、箱を作り直しても残ります。db の `db-data` と同じ理由です。
- **どういう原理で動くか**:
  1. `docker compose up` のとき、**Compose** が倉庫 `roadmap-sh-docker_media` を作る（無ければ）
  2. **Docker** が api の箱を作り、箱の中の `/app/media` に倉庫を**取り付ける**（mount、つまり「その場所を開けると倉庫の中身が見えるようにする」こと）
  3. **Django** が画像を `/app/media/products/` に書くと、実際には倉庫の中に書かれる
  4. 箱を作り直しても、新しい箱に**同じ倉庫**がまた取り付けられるので、中身が見える

> 📇 **named volume（名前付きボリューム）** — 正式名称: **named volume**
> かみくだくと: Docker が管理する、名前の付いた**箱の外の倉庫**。
> 似た言葉との違い: bind mount = **Mac のフォルダ**をそのまま写す。named volume = **Docker の中**に倉庫を作る。
> この教材では: `db-data`（db 用）と `media`（画像用）。

---

### チャンク3: worker にも同じ倉庫をつなぐ（`compose.yaml` の `worker`）— 地図の③

**このチャンクの目的**: worker が、api の保存した画像を読めるようにする。

**🤔 先に考える**: worker に同じ1行を足して起動し直したら、worker の `/app/media/products/` に `sample.jpg` は見えると思いますか？ **worker には、まだ一度も画像を送っていません。**
A. 見える　B. 見えない

<details><summary>答え</summary>

**A** です。worker は、api と**同じ倉庫**につながります。api がチャンク2 で倉庫に置いた `sample.jpg` が、そのまま見えます。倉庫は箱のものではなく、**つないだ箱みんなで分け合う**ものです。

</details>

**🎯 書くもの**: `worker` の `volumes:` の、`- ./apps/api/src:/app/src` の**すぐ下**に、api と同じ倉庫を同じ場所につなぐ1行を足す。

**✍️ 自分で書く**（チャンク2 で書いたばかりの形なので、日本語だけで書きます）

<details><summary>ヒント1</summary>

チャンク2 の分解表を見て、「倉庫の名前」と「箱の中の場所」を思い出します。worker の `MEDIA_ROOT` も、api と同じ `/app/media` です（同じ `settings.py` を使っているから）。

</details>

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
         volumes:
             - ./apps/api/src:/app/src
+            - media:/app/media
         networks:
             - back
```

</details>

**▶️ 確かめる**:

```bash
docker compose up -d worker
docker compose exec worker ls /app/media/products/
```

```text
sample.jpg
```

✅ 検証済み: 2026-11-17（チャンク2 と同じ確かめ方）

P4-6c の終わりでは `No such file or directory` だった worker から、api が保存した画像が見えました。

**🔎 答えの見つけ方**: 「この倉庫は、Docker の中のどこにあるか」は `docker volume inspect` で分かります。

```bash
docker volume inspect roadmap-sh-docker_media --format '{{.Mountpoint}}'
ls /var/lib/docker
```

```text
/var/lib/docker/volumes/roadmap-sh-docker_media/_data
ls: /var/lib/docker: No such file or directory
```

✅ 検証済み: 2026-11-17（プロジェクト名 `p46d` で確認した）

1行目の場所は、**Mac には無い**場所です（2行目で Mac で探すと「無い」）。Docker Desktop は、Mac の中で**小さな Linux**（仮想マシン、P0 で出た言葉）を動かしています。倉庫は、その Linux のディスクの中にあります。チャンク2 の `mount` で `/dev/vda1`（Linux のディスク）と出たのは、このためです。

**🔬 1行ずつ分解**: チャンク2 と同じ1行です（`- media:/app/media`）。違うのは、**書いた箱**が worker であることだけです。

**📖 しくみ**

- **何をしているか**: 1つの倉庫 `media` を、api と worker の**2つの箱**に取り付けました。
- **なぜ必要か**: api が受け取った画像を、worker が読んでサムネイルを作るからです（P4-6f）。worker から画像が見えなければ、仕事ができません。
- **どういう原理で動くか**: **Docker** は、同じ倉庫を何個の箱にでも取り付けられます。api が `/app/media/products/sample.jpg` に書くと、倉庫の中にファイルができます。worker が `/app/media/products/` を開くと、**同じ倉庫の中**を見ているので、そのファイルが見えます。コピーしているのではなく、**同じ場所を2つの入口から見ている**だけです。

---

### 🧪 壊してみる

チャンク1 で書いた名簿の `media:` を外すと、どうなるでしょう。

1. **予想**: いちばん外の `volumes:` から `media:` の1行だけを消して `docker compose config --quiet` を打つと、どうなると思いますか？
   A. 何も出ない（OK）　B. エラーになる
2. **実行**: `media:` の行を消して保存し、打ちます。

   ```bash
   docker compose config --quiet
   ```

3. **見る**:

   ```text
   service "api" refers to undefined volume media: invalid compose project
   ```

   ✅ 検証済み: 2026-11-17（打つたびに `"api"` と `"worker"` のどちらかが出る。どちらも同じ意味）

   部品に分けて読みます。

   | 部品 | 意味 |
   | --- | --- |
   | `service "api"` | api の箱の設定で |
   | `refers to undefined volume media` | **名簿に無い**倉庫 `media` を使おうとしている |
   | `invalid compose project` | だから、この `compose.yaml` は正しくない |

   箱の `volumes:` で `media` と名前だけを書くと、Compose は「名前付きの倉庫だな」と考えて、名簿（いちばん外の `volumes:`）を探します。名簿に無いので、書き間違いかもしれないと止めてくれました。チャンク1 の分解表の「無いとどうなる」と同じです。

4. **元に戻す**: `media:` を戻して保存し、`docker compose config --quiet` で何も出ないことを確かめます。

### 🐳 Docker の中の図（後）

P4-6d が終わったときの、箱の中の様子です。★ が今日変わった所です。

```text
【道 back】 にいる箱（api は front にもいる）

api の箱
  /app/src                  ◀── Mac の apps/api/src（bind mount）
  /app/media                ◀── 倉庫 media  ★
                                │ 同じ倉庫を2つの箱でつなぐ
worker の箱
  /app/src                  ◀── Mac の apps/api/src（bind mount）
  /app/media                ◀── 倉庫 media  ★

db の箱
  /var/lib/mysql            ◀── 倉庫 db-data

倉庫（named volume）: db-data、media ★
```

**見てほしいところ**: 冒頭の「前」の図と並べてください。変わったのは ★ の3か所だけです。api の `/app/media` と worker の `/app/media` が、**同じ倉庫 `media`** を見ています。

> 🗺️ 全体の地図（`docs/02-system-map.md`）にも、倉庫 `media` を書き足しました。

### ✏️ 自分で地図を描く

上の「後」の図を**見ずに**、`＿＿＿` を埋めてみてください。

```text
api の箱
  /app/src                  ◀── Mac の apps/api/src（＿＿＿＿＿＿）
  /app/media                ◀── 倉庫 ＿＿＿＿＿
                                │ 同じ倉庫を2つの箱でつなぐ
worker の箱
  /app/src                  ◀── Mac の apps/api/src（bind mount）
  /app/＿＿＿＿＿           ◀── 倉庫 ＿＿＿＿＿

倉庫を書く場所 1: いちばん外の ＿＿＿＿＿＿: の下（宣言）
倉庫を書く場所 2: 箱の volumes: の下（＿＿＿＿＿＿＿＿＿ の形でつなぐ）
```

<details><summary>答え合わせ</summary>

```text
api の箱
  /app/src                  ◀── Mac の apps/api/src（bind mount）
  /app/media                ◀── 倉庫 media
                                │ 同じ倉庫を2つの箱でつなぐ
worker の箱
  /app/src                  ◀── Mac の apps/api/src（bind mount）
  /app/media                ◀── 倉庫 media

倉庫を書く場所 1: いちばん外の volumes: の下（宣言）
倉庫を書く場所 2: 箱の volumes: の下（倉庫の名前:箱の中の場所 の形でつなぐ）
```

埋められなかった所があれば、そのチャンクの 📖 しくみ だけ読み返します。

</details>

### 📝 ひとこと

「〜だと思っていたけど、実は〜」を1行書きます。書いたものは `docs/notes.md` に貯めます。うまく書けなければ、書かずに先へ進んでも大丈夫です。

例: 「倉庫は箱ごとにあると思っていたけど、実は1つの倉庫を2つの箱で分け合えた」

### ✅ できるようになったこと

- [ ] 画像を「Mac のフォルダ」ではなく「名前付きの倉庫」に置く理由を、コードとデータの違いで説明できる
- [ ] `media:/app/media` と `./apps/api/src:/app/src` を見て、どちらが倉庫でどちらが Mac のフォルダかを言える
- [ ] api を作り直しても画像が残ること、worker から同じ画像が見えることを、打つ前に予想できる

**残った問い**: worker から画像が見えるようになった。でも worker は、**いつ**サムネイルを作ればいいのかを知らない。画像が届いたことを、api はどうやって worker に伝えるのか？ P4-6a で作った**受付箱**の出番だ。

---
▶ **次**: P4-6e メモを受付箱に入れ、worker に届ける

---

## P4-6e: メモを受付箱に入れ、worker に届ける

**❓ この回の問い**: 前回（P4-6d）で、worker からも画像が見えるようになった。でも worker は、**いつ**サムネイルを作ればいいのかを知らない。
→ **「画像が届いたよ。サムネイルを作って」を、api はどうやって worker に伝えるのか？**

**作ること / 確かめること**: worker がやる仕事（task）を1つ作り、api が画像を保存したら、その仕事のメモを受付箱（Redis の 1番の部屋）に入れる。worker がメモを受け取って仕事をしたことを、ログで確かめる。**サムネイルはまだ作らない**（P4-6f）。今日の仕事は「受け取った」と返すだけ
**重要度**: 🔴 毎日使う — 「重い仕事は受付箱にメモを入れて、裏方に任せる」は、Web アプリでとてもよく使う形だから
**前ステップとの接続**: P4-6a で作った受付箱、P4-6b で起動した worker、P4-6c で作った画像の窓口を、今日はじめて**つなげる**。`compose.yaml` は変えない。変えるのは `.py` の3つのファイル

**P4-6 ぜんたいの地図での位置**: ②③（② api がメモを受付箱に入れる → ③ worker が取り出す）

### 🔁 前回の思い出し

**問い**: api が `/app/media/products/sample.jpg` に画像を書いたとき、worker の `/app/media/products/` に見えた `sample.jpg` は、A と B のどちらでしたか？
A. api の画像を**コピーした**もの　B. api と**同じ倉庫の中**にある、同じファイル

<details><summary>答え</summary>

**B** です。倉庫 `media` は1つだけで、api と worker の2つの箱から、同じ場所を見ています。だから今日、worker に渡すメモには**画像そのものを入れなくてよい**のです。「何番の商品か」だけ書けば、worker は倉庫から画像を探せます。

</details>

### 🛠️ 先に自分で決める

教材が答えを出す前に、**あなたが伝え方を決めます。** このあとのチャンクは、あなたの選んだ方針の答え合わせとして進みます。

**困りごと**（P4-6d の残った問い）

- api は画像を受け取って倉庫に保存できる。worker も倉庫の画像を読める
- でも、api が「画像が届いた」ことを worker に伝える方法が**まだ無い**。worker は何もせずに待っている

**🤔 どの伝え方を選びますか？** 1つ選んで、理由を一言で書いてください（「分からない」でも大丈夫です）。

| 案 | 伝え方 |
| --- | --- |
| A | api が worker に**直接**頼む（worker にも窓口を作り、api から HTTP で呼ぶ） |
| B | api が**受付箱**（Redis の 1番の部屋）に「商品 1 のサムネイルを作って」という**メモを入れる**。worker は受付箱を見張っていて、メモが来たら取り出して仕事をする |
| C | 伝えない。**api が自分で**サムネイルを作ってから返事をする |

<details><summary>ヒント</summary>

全体の地図（`docs/02-system-map.md` の「1枚の地図」と「④ 窓口（ポート）」）を見てください。worker には窓口がありますか？ それから、P4-6 ぜんたいの地図（このファイルの「P4-6: ワーカーでサムネイルを作る」の見出しの下）の「見てほしいところ」も読んでみてください。

</details>

<details><summary>答え合わせ</summary>

この教材は **B** で進めます。

| 案 | 判定 | 理由 |
| --- | --- | --- |
| A | △ 動かせる | worker に窓口（Web サーバー）を新しく作る必要があります。それに、worker が止まっている・忙しいと、api は**頼むことすらできず**、エラーになるか待たされます |
| B | ◎ | api はメモを入れたら、**すぐ返事ができます**。worker が止まっていても、メモは受付箱で**待っていて**くれます（チャンク3 の 🔎 で本当に確かめます）。P4-6a で受付箱を、P4-6b で「受付箱を見張る worker」を作ったのは、このためでした |
| C | ✗ | 画像を縮めるのは時間がかかる仕事です。その間、画像を送った人は**ずっと待たされます**。worker を分けた意味がなくなります |

**A と B のちがいは「直接」か「あいだに受付箱があるか」です。** あいだに受付箱があると、頼む側（api）と仕事をする側（worker）が、**お互いの都合を気にしなくてよく**なります。

</details>

### 🐳 Docker の中の図

動く図のページ（`docs/visual/docker-inside.html`。ブラウザで `open docs/visual/docker-inside.html`）で、**「6d」と「6e」のボタンを交互に押して**比べてください。赤く光るのが今日変わる所です。api から redis の 1番の部屋へ向かう矢印（メモを入れる）と、worker が知っている仕事（`make_thumbnail`）が増えます。

### 🧭 全体の中のいま

`docs/02-system-map.md` の「1枚の地図」に、今日さわる所を ★ で示します。

```text
Mac の道具       窓口（④）              Docker の中

                                        【道 front】 web・api
ブラウザ      ── :5173 どこからでも ──▶ web ──▶ api（画面から API を呼ぶ）
curl          ── :8000 どこからでも ──▶ api
Zed           ── :5678 Mac だけ     ──▶ api（デバッガ）

                                        【道 back】 api・worker・db・redis
                                        api ──▶ db、redis
                                        api ──▶ redis の 1番にメモを入れる  ★ 今日
DBeaver       ── :3306 Mac だけ     ──▶ db      倉庫 db-data（消えない）
Redis Insight ── :6379 Mac だけ     ──▶ redis   倉庫なし（作り直すと消える）
                                                0番の部屋: カート / 1番の部屋: 受付箱
（窓口なし）                            worker ──▶ redis の 1番を見張る  ★ 今日: メモを取り出して仕事をする
                                        api・worker ──▶ 倉庫 media（画像。消えない）
```

**見てほしいところ**: 今日は**新しい箱・道・倉庫・窓口は増えません。** P4-6b からずっと「1番を見張って」いた worker に、はじめてメモが届きます。

### 🗺️ 今日の地図

```text
api の箱                                           worker の箱
  ① catalog/tasks.py  仕事の中身を書く  … チャンク1  （同じ src を写しているので、worker にもある）
  ② config/celery.py  仕事の一覧を探させる … チャンク2 ──▶ 起動のとき、① を見つけて覚える
  ③ config/api.py     画像を保存したら、
                      メモを受付箱に入れる … チャンク3
        │
        ▼
   Redis の 1番の部屋（受付箱）にメモが1枚入る
        │
        ▼
  ④ worker がメモを取り出し、① の仕事をする（書くコードは無い。ログで見る）
```

**見てほしいところ**: ①〜③ はすべて `apps/api/src` の中のファイルです。api と worker は**同じ `src` を写している**ので（P4-6b）、①②は worker の中にもあります。**書く場所は1つ、使う箱は2つ**です。

### 6e-0. このステップの初出

**Celery**: `@app.task`、`app.autodiscover_tasks()`、`.delay()`、`celery inspect registered`
**Docker**: `docker compose restart`
**Redis**: `LLEN`（メモの枚数を数える）、`LRANGE`（メモを見る）
**Python**: `@`（デコレータ）、`f"..."`（f文字列）

---

### チャンク1: worker にやらせる仕事を書く（`apps/api/src/catalog/tasks.py`）— 地図の①

**このチャンクの目的**: 「サムネイルを作る」仕事の**入れ物**を作る。中身は、今日は「受け取った」と返すだけ。

**🤔 先に考える**: これから書く `make_thumbnail` を、api の箱の中で**ふつうの関数として**呼んだら（`make_thumbnail(1)`）、仕事をするのは A と B のどちらだと思いますか？
A. api の箱　B. worker の箱

理由も一言で（「分からない」でも大丈夫です）。

<details><summary>答え</summary>

**A** です。ふつうに呼ぶと、**呼んだ箱（api）がその場で**実行します。worker には何も届きません。▶️ 確かめる で、worker のログが静かなままなのを見ます。worker に頼むには、チャンク3 の `.delay()` が要ります。

</details>

**🎯 書くもの**: `apps/api/src/catalog/` に新しいファイル `tasks.py` を作る。Celery の仕事 `make_thumbnail` を1つ書く。商品の番号（`product_id`）を受け取り、「商品 ◯ のメモを受け取った」という文字を返す。

**🔬 1行ずつ分解**（はじめて書く形なので、打つ前に読みます）:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `from config.celery import app` | フロム コンフィグ ドット セロリ インポート アップ | P4-6a で作った Celery アプリ（受付箱の場所を知っている）を借りてくる | 無いと、次の行の `app` が分からず `NameError` |
| `@app.task` | アット アップ ドット タスク（**デコレータ**、decorator） | すぐ下の関数を「Celery の仕事（task）」として登録する。登録すると、関数に `.delay()` などの道具が付く | 消すと、ただの関数に戻る。`.delay()` が無くなる（🧪 で確かめる） |
| `def make_thumbnail(product_id):` | デフ（関数定義） | 仕事の名前と、受け取るもの（商品の番号）を決める | 仕事の本当の名前は、ファイルの場所も含めて `catalog.tasks.make_thumbnail` になる |
| `return f"商品 {product_id} のメモを受け取った"` | リターン、エフ文字列（**f-string**） | 仕事の結果として、文字を返す。`{product_id}` の所に番号が入る | 今日は返すだけ。P4-6f で、ここを「画像を縮める」に入れ替える |

**✍️ 自分で書く**（はじめての形なので、下を見ながら**手で打ちます**。コピペはしません）

```python
from config.celery import app


@app.task
def make_thumbnail(product_id):
    return f"商品 {product_id} のメモを受け取った"
```

<details><summary>💡 補足: Django の解説でよく見る <code>@shared_task</code> を使わない理由</summary>

Celery の Django 向けの説明では、`from celery import shared_task` と `@shared_task` もよく出てきます。ただし `@shared_task` を使うときは、別に `config/__init__.py` にも1行書く必要があります。その1行が無いまま `.delay()` を呼ぶと、api は受付箱の場所を知らない Celery を使ってしまいます。

```text
kombu.exceptions.OperationalError: [Errno 111] Connection refused
```

✅ 検証済み: 2026-11-18（`@shared_task` に変えて、`config/__init__.py` は空のままで画像を送った）

この教材では、書くファイルを減らすために、`config.celery` の `app` を**名指しで**使う `@app.task` にしました。Celery の公式チュートリアル（First Steps）と同じ書き方です。

</details>

**▶️ 確かめる**: api の箱の中で、ふつうの関数として呼んでみます。別のタブ（tmux のペイン）で worker のログを流しておくと、worker が**何もしない**ことも見えます。

```bash
docker compose logs -f --since 1m worker
```

```bash
docker compose exec api .venv/bin/python src/manage.py shell -c "from catalog.tasks import make_thumbnail; print(make_thumbnail.name); print(make_thumbnail(1))"
```

```text
1 object imported automatically (use -v 2 for details).

catalog.tasks.make_thumbnail
商品 1 のメモを受け取った
```

✅ 検証済み: 2026-11-18（1行目は Django の shell が毎回出すお知らせ。気にしなくてよい）

2行目の `catalog.tasks.make_thumbnail` が、この仕事の**本当の名前**です。3行目の答えは、api の箱がその場で出しました。worker のログには何も出ません。

**🔎 答えの見つけ方**: 「この関数は Celery の仕事として登録できているか」は、`.name` を表示してみる。仕事なら `catalog.tasks.make_thumbnail` のような名前が出る。ただの関数なら `AttributeError` になる。

**📖 しくみ**

- **何をしているか**: `make_thumbnail` という関数を作り、`@app.task` で「Celery の仕事」に変えました。
- **なぜ必要か**: worker が受付箱からメモを取り出したとき、メモには「`catalog.tasks.make_thumbnail` を、引数 `1` でやって」としか書いてありません。worker はその名前で**仕事の中身**を探します。中身を書いておく場所が、この `tasks.py` です。
- **どういう原理で動くか**: Python がこのファイルを読むと、まず `make_thumbnail` 関数ができます。すぐに `@app.task` が働き、**Celery アプリ**（`config.celery` の `app`）が、この関数を自分の**仕事の名簿**に `catalog.tasks.make_thumbnail` という名前で載せます。同時に、関数に `.delay()` などの道具を付けます。ふつうに `make_thumbnail(1)` と呼べば、今いる箱でそのまま動きます。

> 📇 **タスク** — 正式名称: **task**（Celery の用語）
> かみくだくと: worker に任せる**仕事1つ分**。中身はふつうの Python の関数。
> 似た言葉との違い: worker = 仕事を**やる人**（箱）。task = やる**仕事の中身**。
> この教材では: `catalog.tasks.make_thumbnail`（今日は「受け取った」と返すだけ。P4-6f でサムネイルを作る）

---

### チャンク2: worker に仕事の名簿を作らせる（`apps/api/src/config/celery.py`）— 地図の②

**このチャンクの目的**: worker が起動するとき、`tasks.py` を**自分で探して**、仕事を覚えるようにする。

**🤔 先に考える**: いま、`tasks.py` はもう `src` の中にあります。worker は同じ `src` を写しています。ここで worker を起動し直したら、worker は `make_thumbnail` を**知っている**と思いますか？
A. 知っている　B. 知らない

<details><summary>答え</summary>

**B** です。ファイルが**ある**ことと、worker がそのファイルを**読んだ**ことは別です。worker は起動のとき、言われたファイルしか読みません。`tasks.py` を読めとは、まだ誰も言っていません。✅ 検証済み（2026-11-18）

```bash
docker compose restart worker
docker compose logs --since 1m worker
```

```text
[tasks]


[2026-11-18 05:52:30,594: INFO/MainProcess] Connected to redis://:**@redis:6379/1
```

起動のお知らせの `[tasks]`（知っている仕事の一覧）の下が、**空っぽ**です。

</details>

**🎯 書くもの**: `apps/api/src/config/celery.py` のいちばん下（`app.config_from_object(...)` の行のすぐ下）に1行足す。Celery アプリに「Django のアプリ（`catalog` など）の中の `tasks.py` を、自分で探して読んで」と頼む。

**🔬 1行ずつ分解**（はじめて書く形なので、打つ前に読みます）:

`app.autodiscover_tasks()`

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `app` | アップ | P4-6a で作った Celery アプリ | — |
| `.autodiscover_tasks` | オート ディスカバー タスクス（**autodiscovery**、自動で見つける） | `settings.py` の `INSTALLED_APPS` に書いた Django アプリを1つずつ見て、その中の `tasks.py` を読み込む | 無いと、worker は `tasks.py` を読まない。メモが届いても「その仕事は知らない」と捨てる |
| `()` | かっこ（呼び出し） | 何も渡さないと「`tasks.py` という名前のファイルを探す」 | — |

**✍️ 自分で書く**（1行なので、上を見ながら**手で打ちます**）

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
 app = Celery("config")
 app.config_from_object("django.conf:settings", namespace="CELERY")
+app.autodiscover_tasks()
```

</details>

**▶️ 確かめる**: worker を起動し直して、`[tasks]` の下を見ます。

```bash
docker compose restart worker
docker compose logs --since 1m worker
```

```text
[tasks]
  . catalog.tasks.make_thumbnail

[2026-11-18 05:53:07,659: INFO/MainProcess] Connected to redis://:**@redis:6379/1
```

✅ 検証済み: 2026-11-18

`[tasks]` の下に、チャンク1 で作った仕事の名前が出ました。

> ⚠️ **worker は、コードを変えても自分では読み直しません。** api（`runserver`）は保存すると自動で読み直しますが、Celery の worker にはその仕組みがありません。`.py` を変えたら、`docker compose restart worker` で起動し直します。`restart` は「同じ箱を止めて、また起動する」だけで、箱を作り直しません。コードは Mac の `src` を写しているので、起動し直すだけで新しいコードが読まれます。

**🔎 答えの見つけ方**: 「worker がいま知っている仕事の一覧」は、動いている worker に直接たずねると分かります。

```bash
docker compose exec worker .venv/bin/celery --workdir src -A config inspect registered
```

```text
->  celery@6dec9345b1ad: OK
    * catalog.tasks.make_thumbnail

1 node online.
```

✅ 検証済み: 2026-11-18（`celery@` の後ろは箱ごとに違う。チャンク2 を書く前に打つと `- empty -` と出る）

`inspect registered` は「登録済みの仕事を調べて」という意味です。起動のログを探さなくても、いつでも打てます。

**📖 しくみ**

- **何をしているか**: Celery アプリに「Django アプリの中の `tasks.py` を探して読み込んで」と頼みました。
- **なぜ必要か**: worker が起動のとき読むのは、`compose.yaml` の `command:` の `-A config` で言われた `config/celery.py` だけです。`tasks.py` は誰にも読まれないので、仕事の名簿に載りません。名簿に無い仕事のメモが届くと、worker は**捨ててしまいます**。
- **どういう原理で動くか**:
  1. **worker** が起動し、`-A config` に従って `config/celery.py` を読む
  2. `app.autodiscover_tasks()` が「Django の準備ができたら探す」と予約する
  3. Django の準備ができると、**Celery** が `INSTALLED_APPS` の各アプリ（`catalog` など）の中に `tasks.py` があるかを見て、あれば読み込む
  4. 読み込まれた `tasks.py` の `@app.task` が働き、`make_thumbnail` が名簿に載る（チャンク1 の 📖）
  5. 準備が終わると、worker は名簿を `[tasks]` としてログに出し、受付箱を見張り始める

<details><summary>💡 補足: チャンク3 のあとで、この行を消しても動いてしまうことがある</summary>

チャンク3 で `config/api.py` に `from catalog.tasks import make_thumbnail` を書くと、**この行を消しても、worker が仕事を知っている**ことがあります。✅ 検証済み（2026-11-18）

理由: worker は起動のとき、Django の**点検**（system checks。設定にまちがいが無いかを調べる仕組み）を走らせます。点検は URL の設定を読み、URL の設定は `api.py` を読み、`api.py` は `tasks.py` を読みます。こうして、**たまたま**名簿に載るのです。

たまたまに頼ると、ある日 `api.py` を書き換えたとたん、worker が仕事を忘れます。だから `autodiscover_tasks()` で**はっきり**探させます。

</details>

> 📇 **タスクの自動発見** — 正式名称: **autodiscovery**（`autodiscover_tasks()`）
> かみくだくと: worker が起動のとき、各アプリの `tasks.py` を**自分で探して**仕事を覚える仕組み。
> 似た言葉との違い: `import` = 1つのファイルを名指しで読む。autodiscovery = 決まった名前（`tasks.py`）のファイルを、アプリ全部から探して読む。
> この教材では: `catalog/tasks.py` が見つかり、`catalog.tasks.make_thumbnail` が名簿（task registry）に載る。

---

### チャンク3: 画像を保存したら、メモを受付箱に入れる（`apps/api/src/config/api.py`）— 地図の③④

**このチャンクの目的**: あなたが 🛠️ で選んだ **B**（受付箱にメモを入れる）を、本当に書く。

**🤔 先に考える**: チャンク1 では `make_thumbnail(1)` と**ふつうに**呼びました。今度は `make_thumbnail.delay(1)` と、`.delay` を付けて呼びます。仕事をするのは A と B のどちらだと思いますか？
A. api の箱　B. worker の箱

<details><summary>答え</summary>

**B** です。`.delay()` は、その場では仕事を**しません**。代わりに「この仕事を、この引数でやって」という**メモ**を作り、受付箱に入れるだけです。仕事をするのは、受付箱を見張っている worker です。

</details>

**🎯 書くもの**: `apps/api/src/config/api.py` に2行足す。

1. いちばん上の `from catalog.models import Product` のすぐ下に、チャンク1 の仕事を読み込む1行
2. 画像の窓口の関数の中で、`product.image.save(...)` のすぐ下（`return` の上）に、商品の番号を付けてメモを入れる1行

**🔬 1行ずつ分解**（はじめて書く形なので、打つ前に読みます）:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `from catalog.tasks import make_thumbnail` | フロム カタログ ドット タスクス インポート | チャンク1 の仕事を api.py で使えるようにする | 無いと、次の行で `NameError` |
| `make_thumbnail` | — | チャンク1 で `@app.task` を付けた仕事 | — |
| `.delay` | ディレイ（遅らせる） | 仕事を**今やらず**、メモにして受付箱に入れる。「あとで worker がやる」ので delay | `.delay` を外して `make_thumbnail(product.id)` にすると、api がその場でやってしまう（チャンク1 と同じ） |
| `(product.id)` | 引数（argument） | メモに書く中身。保存した商品の番号 | 画像そのものは渡さない。worker は倉庫 `media` から読める（🔁 前回の思い出し） |

**✍️ 自分で書く**（はじめての形なので、上を見ながら**手で打ちます**）

```python
from catalog.tasks import make_thumbnail
```

```python
    make_thumbnail.delay(product.id)
```

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
 from catalog.models import Product
+from catalog.tasks import make_thumbnail
 
 api = NinjaAPI()
```

```diff
     product = get_object_or_404(Product, id=product_id)
     product.image.save(image.name, image)
+    make_thumbnail.delay(product.id)
     return {"status": "saved"}
```

2行目は、関数の中なので**4つ分の字下げ**が要ります（上の `product.image.save` と左をそろえる）。

</details>

**▶️ 確かめる**: 片方のタブで worker のログを流したまま、もう片方のタブで画像を送ります（`/tmp/sample.jpg` が無ければ、P4-6c チャンク3 の ▶️ のコマンドで作り直します）。

```bash
docker compose logs -f --since 1m worker
```

```bash
curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
```

```text
{"status": "saved"}
```

worker のログに、次の2行が出れば OK です。

```text
[2026-11-18 05:53:13,460: INFO/MainProcess] Task catalog.tasks.make_thumbnail[34dbdd82-9b89-4208-b258-68ae65b31de8] received
[2026-11-18 05:53:13,460: INFO/ForkPoolWorker-7] Task catalog.tasks.make_thumbnail[34dbdd82-9b89-4208-b258-68ae65b31de8] succeeded in 0.00022425000000225737s: '商品 1 のメモを受け取った'
```

✅ 検証済み: 2026-11-18。手元と同じファイルを別の場所に写して確認した（プロジェクト名は `p46e-verify`、イメージ名は `ec-api:p46e`。`curl` は Mac からではなく、front の道の中から api に送った）。`[...]` の中の番号と時刻は、送るたびに変わる

| 部品 | 意味 |
| --- | --- |
| `MainProcess` | worker の**受付係**。受付箱からメモを取り出した |
| `received` | メモを**受け取った** |
| `[34dbdd82-...]` | メモ1枚ごとに付く**番号**（task id）。`received` と `succeeded` が同じ番号なら、同じメモの話 |
| `ForkPoolWorker-7` | worker の中の**作業係**の7番。受付係から仕事を渡された |
| `succeeded in 0.0002s` | 仕事が**終わった**。かかった時間 |
| `'商品 1 のメモを受け取った'` | チャンク1 の `return` で返した文字 |

**🔎 答えの見つけ方**: 「メモは本当に受付箱を通っているのか」は、**worker を止めて**から送ると見えます。worker が動いていると、メモは一瞬で取り出されて見えないからです。

```bash
docker compose stop worker
curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
docker compose exec redis redis-cli -n 1 LLEN celery
```

```text
{"status": "saved"}{"status": "saved"}(integer) 2
```

（`curl` の返事には改行が無いので、3つの答えが1行につながって見えます）

worker が止まっていても、api はすぐ `saved` と返しました。受付箱の `celery` という場所に、メモが **2枚**たまっています。1枚の中を見てみます。

```bash
docker compose exec redis redis-cli -n 1 LRANGE celery 0 0
```

```text
1) "{\"body\": \"W1sxXSwge30sIHsiY2FsbGJhY2tzIjogbnVsbCwg...\", \"content-encoding\": \"utf-8\", \"content-type\": \"application/json\", \"headers\": {\"lang\": \"py\", \"task\": \"catalog.tasks.make_thumbnail\", \"id\": \"6d9f64ad-6ca8-4845-b720-21769e8283e6\", ... \"argsrepr\": \"(1,)\", ...
```

（長いので途中を `...` で省いています。`\"` は、文字の中の `"` を表す書き方です）

`"task": "catalog.tasks.make_thumbnail"`（どの仕事か）と `"argsrepr": "(1,)"`（引数は 1）が書いてあります。**メモに書いてあるのは、仕事の名前と引数だけ**です。worker を起動し直すと、たまっていたメモが片付きます。

```bash
docker compose start worker
docker compose exec redis redis-cli -n 1 LLEN celery
```

```text
(integer) 0
```

✅ 検証済み: 2026-11-18（起動した worker のログには、`received` と `succeeded` が2組出た）

> 💡 `LLEN` は「リスト（list）の長さ（length）」、`LRANGE celery 0 0` は「リスト `celery` の0番目から0番目まで」を見る Redis の命令です。メモは、Redis の**リスト**（順番つきの並び）に入れられています。`KEYS '*'` で見える `_kombu.binding...` は、Celery が使う道具の印で、気にしなくてよいです。

**📖 しくみ**

- **何をしているか**: 画像を保存したあと、「商品 1 のサムネイルを作って」というメモを受付箱に入れるようにしました。
- **なぜ必要か**: api が自分で重い仕事をすると、画像を送った人がその間ずっと待たされます。メモを入れるだけなら一瞬で終わり、すぐ `saved` と返せます。worker が止まっていても、メモは受付箱で待っています（🔎 で見たとおり）。
- **どういう原理で動くか**:
  1. **api**（Django）が画像を倉庫 `media` に保存する（P4-6c・6d）
  2. **api** が `make_thumbnail.delay(1)` を呼ぶ。Celery が「`catalog.tasks.make_thumbnail` を引数 `1` で」というメモを JSON で作る
  3. **Celery**（api の中）が、`settings.py` の `CELERY_BROKER_URL`（P4-6a）を見て、Redis の 1番の部屋のリスト `celery` にメモを入れる。api はここで返事をする
  4. **worker の受付係**（MainProcess）が、リスト `celery` からメモを取り出す（`received`）
  5. 受付係が仕事の名簿（チャンク2）で `catalog.tasks.make_thumbnail` を探し、**作業係**（ForkPoolWorker）に渡す
  6. 作業係が、チャンク1 の関数を引数 `1` で実行する（`succeeded`）

> 📇 **メッセージ** — 正式名称: **message**（task message）
> かみくだくと: 受付箱に入れる**メモ1枚**。「どの仕事を・どの引数で」だけが書いてある。
> 似た言葉との違い: task = 仕事の**中身**（関数）。message = その仕事を**頼むメモ**。関数そのものは入っていない。
> この教材では: api が `.delay()` で作り、Redis の 1番の部屋のリスト `celery` に入れる。worker が取り出す。

---

### 🧪 壊してみる

チャンク1 の `@app.task` を外すと、どうなるでしょう。

1. **予想**: `catalog/tasks.py` の `@app.task` の1行だけを消して保存し、画像を送ると、どうなると思いますか？
   A. いつもどおり `saved` が返り、worker が仕事をする　B. api がエラーになる
2. **実行**: `@app.task` の行を消して保存し、送ります。

   ```bash
   curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
   docker compose logs --since 1m api
   ```

3. **見る**: api のログの最後のほうに、次が出ます。

   ```text
     File "/app/src/config/api.py", line 56, in uploada_image
       make_thumbnail.delay(product.id)
       ^^^^^^^^^^^^^^^^^^^^
   AttributeError: 'function' object has no attribute 'delay'
   Internal Server Error: /api/products/1/image
   "POST /api/products/1/image HTTP/1.1" 500 348
   ```

   ✅ 検証済み: 2026-11-18（`line 56` の数字と関数の名前は、あなたの `api.py` の書き方で変わる）

   部品に分けて読みます。

   | 部品 | 意味 |
   | --- | --- |
   | `File "/app/src/config/api.py", line 56` | api.py の 56 行目（チャンク3 で書いた行）で止まった |
   | `AttributeError` | 「その**道具**（attribute）は無い」というエラー |
   | `'function' object` | `make_thumbnail` が、**ただの関数**になっている |
   | `has no attribute 'delay'` | ただの関数には `.delay` という道具が付いていない |
   | `500` | api が「中でエラーが起きた」と返した |

   チャンク1 の分解表の「`@app.task` を消すと `.delay()` が無くなる」と同じです。`.delay()` は Python の関数にもともとある道具ではなく、`@app.task` が**後から付けた**道具でした。

   > ⚠️ 画像の保存（`product.image.save`）は、エラーの**前の行**なので、終わっています。倉庫には画像が入り、メモだけが入らなかった状態です。

4. **元に戻す**: `@app.task` を戻して保存します。worker は自分では読み直さないので（チャンク2）、`docker compose restart worker` で起動し直してから、もう一度送り、worker のログに `succeeded` が出ることを確かめます。

### 🐳 Docker の中の図（後）

動く図のページ（`docs/visual/docker-inside.html`）の **「6e」** のボタンを押し、**api の箱をクリック**してみてください。右に出る説明に、今日書いた `.delay()` があります。次に **worker の箱**をクリックして、知っている仕事に `make_thumbnail` があることを確かめます。

> 🗺️ 全体の地図（`docs/02-system-map.md`）の「🔎 調べ方の地図」と「つまずきメモ」にも、今日のコマンドを書き足しました。

### ✏️ 自分で地図を描く

冒頭の 🗺️ 今日の地図を**見ずに**、`＿＿＿` を埋めてみてください。各行の右に「なぜ」を一言ずつ書くのがポイントです。

```text
① catalog/＿＿＿＿.py   仕事の中身を書く。@＿＿＿＿＿＿ を付ける
                         なぜ: ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
② config/celery.py      app.＿＿＿＿＿＿＿＿＿＿＿() を足す
                         なぜ: ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
③ config/api.py         画像を保存したら make_thumbnail.＿＿＿＿＿(product.id)
                         なぜ: ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
        │
        ▼
   Redis の ＿＿番の部屋の、リスト ＿＿＿＿＿＿ にメモが入る
        │
        ▼
④ worker の ＿＿＿＿係がメモを取り出し（received）、＿＿＿＿係が仕事をする（succeeded）
```

<details><summary>答え合わせ</summary>

```text
① catalog/tasks.py      仕事の中身を書く。@app.task を付ける
                         なぜ: worker がメモの名前から、仕事の中身を探せるようにするため
② config/celery.py      app.autodiscover_tasks() を足す
                         なぜ: worker が起動のとき tasks.py を読み、仕事の名簿に載せるため
③ config/api.py         画像を保存したら make_thumbnail.delay(product.id)
                         なぜ: api が自分で仕事をせず、すぐ返事できるようにするため
        │
        ▼
   Redis の 1番の部屋の、リスト celery にメモが入る
        │
        ▼
④ worker の受付係がメモを取り出し（received）、作業係が仕事をする（succeeded）
```

「なぜ」は、言い方がちがっても、意味が合っていれば正解です。埋められなかった所があれば、そのチャンクの 📖 しくみ だけ読み返します。最後に、動く図のページの「6e」と見比べます。

</details>

### 📝 ひとこと

「〜だと思っていたけど、実は〜」を1行書きます。書いたものは `docs/notes.md` に貯めます。うまく書けなければ、書かずに先へ進んでも大丈夫です。

例: 「worker に頼むには worker を直接呼ぶと思っていたけど、実はメモを受付箱に置いておくだけだった」

### ✅ できるようになったこと

- [ ] `make_thumbnail(1)` と `make_thumbnail.delay(1)` で、仕事をする箱がどう違うかを説明できる
- [ ] worker が仕事を知らないとき、`[tasks]` のログや `inspect registered` で確かめられる
- [ ] worker を止めて送ったら、メモが受付箱にたまることを、打つ前に予想できる

**残った問い**: worker にメモが届くようになった。でも今の仕事は「受け取った」と返すだけで、サムネイルはまだ作っていない。**worker は倉庫の画像をどうやって開いて、小さくして、どこに保存すればいいのか？**

---
▶ **次**: P4-6f サムネイルを作る

---

## P4-6f: サムネイルを作る

**❓ この回の問い**: 前回（P4-6e）で、worker にメモが届くようになった。でも worker の仕事は「受け取った」と返すだけで、サムネイルはまだ無い。
→ **worker は倉庫の画像をどうやって開いて、小さくして、どこに保存すればいいのか？**

**作ること / 確かめること**: worker が db から商品を読み、倉庫 `media` の元画像を開いて、縦横 200 以内に縮めたサムネイルを `/app/media/thumbs/` に保存する。db の商品の行に、サムネイルの場所を書く。api の箱からもサムネイルが見えることを確かめる
**重要度**: 🔴 毎日使う — 「裏方が db と倉庫を読み書きして、重い仕事を片付ける」は、Web アプリの裏側でいつも使う形だから
**前ステップとの接続**: P4-6e の `make_thumbnail` の中身を、本物の仕事に入れ替える。`compose.yaml` は変えない（🧪 で一時的に変えるだけ）。変えるのは `catalog/tasks.py` と `catalog/models.py`

**P4-6 ぜんたいの地図での位置**: ④（worker が画像を縮めて、サムネイルとして保存する）

### 🔁 前回の思い出し

**問い**: P4-6e で、`make_thumbnail(1)` と `make_thumbnail.delay(1)` は何が違いましたか？ 一言で。

<details><summary>答え</summary>

`make_thumbnail(1)` は、呼んだ箱（api）が**その場で**仕事をします。`.delay(1)` は、受付箱に**メモを入れるだけ**で、仕事をするのは worker です。今日書く中身は、`.delay()` で頼まれたとおり、**worker の箱の中で**動きます。

</details>

### 🛠️ 先に自分で決める

教材が答えを出す前に、**あなたがサムネイルの残し方を決めます。** このあとのチャンクは、あなたの選んだ方針の答え合わせとして進みます。

**困りごと**（P4-6e の残った問い）

- worker にメモ（「商品 1 のサムネイルを作って」）が届くようになった
- でも、縮めた画像を**どこに・どう残すか**が決まっていない。決めないと、P4-6g で画面に出すときに探せない

**🤔 どの残し方を選びますか？** 1つ選んで、理由を一言で書いてください（「分からない」でも大丈夫です）。

| 案 | 残し方 |
| --- | --- |
| A | 元の画像を縮めて、**同じファイルに上書きする**。db は変えない |
| B | 元の画像はそのまま。縮めた画像を**別のファイル**（`thumbs/1.jpg`）に作り、db の商品の行に**新しい列**を足して、その場所を書く |
| C | 何も残さない。画面に出すたびに、**その場で縮める** |

<details><summary>ヒント</summary>

商品のページでは、大きな画像も見せたいことがあります（拡大表示）。それから、画像を縮めるのは「重い仕事」でした（P4-6e の 🛠️ の C）。

</details>

<details><summary>答え合わせ</summary>

この教材は **B** で進めます。

| 案 | 判定 | 理由 |
| --- | --- | --- |
| A | ✗ | 元の画像が**二度と戻らない**。大きな画像を見せたくなっても、もう無い |
| B | ◎ | 元の画像も残る。db の列を見れば、サムネイルの場所が**すぐ分かる**（P4-6c で画像の場所を `image` 列に書いたのと同じ考え方）。縮めるのは1回だけで済む |
| C | △ 動かせる | 画面を開くたびに重い仕事をすることになる。worker に任せた意味がなくなる |

B のために、今日はチャンク2 で db に列を1つ足します。

</details>

### 🐳 Docker の中の図

動く図のページ（`docs/visual/docker-inside.html`。ブラウザで `open docs/visual/docker-inside.html`）で、**「6e」と「6f」のボタンを交互に押して**比べてください。赤く光るのが今日変わる所です。worker から db への線（商品を読む・サムネイルの場所を書く）と、倉庫 `media` の中の `thumbs/` が増えます。

### 🧭 全体の中のいま

`docs/02-system-map.md` の「1枚の地図」に、今日さわる所を ★ で示します。

```text
Mac の道具       窓口（④）              Docker の中

                                        【道 front】 web・api
ブラウザ      ── :5173 どこからでも ──▶ web ──▶ api（画面から API を呼ぶ）
curl          ── :8000 どこからでも ──▶ api
Zed           ── :5678 Mac だけ     ──▶ api（デバッガ）

                                        【道 back】 api・worker・db・redis
                                        api ──▶ db、redis
                                        api ──▶ redis の 1番にメモを入れる
DBeaver       ── :3306 Mac だけ     ──▶ db      倉庫 db-data（消えない）
Redis Insight ── :6379 Mac だけ     ──▶ redis   倉庫なし（作り直すと消える）
                                                0番の部屋: カート / 1番の部屋: 受付箱
（窓口なし）                            worker ──▶ redis の 1番を見張り、メモが来たら仕事をする
                                        worker ──▶ db（商品を読む・サムネイルの場所を書く）  ★ 今日
                                        api・worker ──▶ 倉庫 media（画像。消えない）
                                                        worker が thumbs/ にサムネイルを書く  ★ 今日
```

**見てほしいところ**: 今日も**新しい箱・道・倉庫・窓口は増えません。** worker が、P4-6b で決めた `depends_on: db` と back の道を通って、**はじめて db と話します。**

### 🗺️ 今日の地図

```text
Redis の 1番の部屋（受付箱）から「商品 1 のサムネイルを作って」のメモ（P4-6e）
        │
        ▼
worker の箱  catalog/tasks.py の make_thumbnail
  ① db から商品 1 を読み、倉庫 media の元画像を開く      … チャンク1（tasks.py）
  ② db の商品の表に、サムネイルの列を足す                … チャンク2（models.py と migrate）
  ③ 縦横 200 以内に縮めて thumbs/ に保存し、
     db の ② の列にその場所を書く                        … チャンク3（tasks.py）
        │
        ├──▶ 倉庫 media の /app/media/thumbs/1.jpg   （api の箱からも見える）
        └──▶ db の catalog_product の thumbnail 列 = "thumbs/1.jpg"
```

**見てほしいところ**: サムネイルも、P4-6c の画像と同じく**2か所に分かれて**残ります。画像そのものは倉庫 `media` へ、db には**場所の文字だけ**です。

### 6f-0. このステップの初出

**Pillow**: `Image.open()`、`.size`、`.thumbnail()`、`.save()`
**Django**: `Product.objects.get()`、`ContentFile`、`FieldFile.save()`（`product.thumbnail.save(...)`）
**Docker**: `docker compose cp`

---

### チャンク1: worker が db と倉庫から材料を集める（`apps/api/src/catalog/tasks.py`）— 地図の①

**このチャンクの目的**: メモに書いてあるのは**商品の番号だけ**（P4-6e）。worker が自分で db から商品を読み、倉庫の元画像を開けることを確かめる。

**🤔 先に考える**: worker は、db（MySQL）と話せると思いますか？
A. 話せる　B. 話せない

理由も一言で（「分からない」でも大丈夫です）。ヒント: 全体の地図（`docs/02-system-map.md` の「② 道（ネットワーク）」）で、worker と db は同じ道にいますか？ worker の `env_file:` には何が入っていましたか？

<details><summary>答え</summary>

**A** です。理由は2つあります。

1. worker と db は、どちらも **back の道**にいます（P4-6b）。同じ道にいれば、`db` という名前で呼べます
2. worker は api と同じ `apps/api/.env` を受け取っています（`env_file:`、P4-6b）。その中の `DB_HOST=db` などを、`settings.py` が読みます

```bash
docker compose exec worker printenv DB_HOST
```

```text
db
```

✅ 検証済み: 2026-11-18

</details>

**🎯 書くもの**: `catalog/tasks.py` を、次のように変える。

1. いちばん上に、Pillow の `Image` と、商品のモデル `Product` を読み込む2行を足す
2. `make_thumbnail` の中で、番号から商品を1つ取り出す。その商品の `image`（元画像）を Pillow で開く
3. `return` を「商品 ◯ の画像は （横, 縦）」と、画像の大きさを返すように変える

**🔬 1行ずつ分解**（はじめて書く形なので、打つ前に読みます）:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `from PIL import Image` | フロム ピル インポート イメージ | Pillow（P4-6c で入れた画像の道具）の `Image` を借りる。Pillow は昔の名前 PIL のまま読み込む | 無いと `NameError: name 'Image' is not defined` |
| `from catalog.models import Product` | — | 商品のモデル（db の表 `catalog_product` の Python 側の姿） | 無いと `NameError` |
| `Product.objects.get(id=product_id)` | オブジェクツ ドット ゲット（**ORM**、Object-Relational Mapping） | db に「id が ◯ の商品を1つ」とたずね、1行を Python の `Product` として受け取る | 無い番号だと `Product.DoesNotExist` |
| `Image.open(product.image)` | イメージ ドット オープン | 商品の `image` 列に書いた場所（`products/...jpg`）のファイルを、`MEDIA_ROOT`（`/app/media`）の下から開く | worker に倉庫 `media` が無いと `FileNotFoundError`（🧪 で確かめる） |
| `img.size` | サイズ | 画像の `(横, 縦)` のピクセル数 | — |

**✍️ 自分で書く**（はじめての形なので、下を見ながら**手で打ちます**。コピペはしません）

```python
from PIL import Image

from catalog.models import Product
from config.celery import app


@app.task
def make_thumbnail(product_id):
    product = Product.objects.get(id=product_id)
    img = Image.open(product.image)
    return f"商品 {product_id} の画像は {img.size}"
```

（`from config.celery import app` と `@app.task`、`def` の行は P4-6e のまま。打つのは、上の2行と、関数の中の3行です）

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
+from PIL import Image
+
+from catalog.models import Product
 from config.celery import app
 
```

```diff
 @app.task
 def make_thumbnail(product_id):
-    return f"商品 {product_id} のメモを受け取った"
+    product = Product.objects.get(id=product_id)
+    img = Image.open(product.image)
+    return f"商品 {product_id} の画像は {img.size}"
```

</details>

**▶️ 確かめる**: worker のログを流したまま、画像を送ります。まずは**保存しただけで**送ってみます。

```bash
docker compose logs -f --since 1m worker
```

```bash
curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
```

```text
... succeeded in 0.0001s: '商品 1 のメモを受け取った'
```

**古い答えのまま**です。worker は、コードを変えても自分では読み直さないからです（P4-6e チャンク2 の ⚠️）。worker を起動し直してから、もう一度送ってください（コマンドは自分で思い出して打ちます）。

<details><summary>ヒント: 起動し直すコマンド</summary>

`docker compose restart worker`

</details>

```text
[2026-11-18 06:57:59,742: INFO/MainProcess] Task catalog.tasks.make_thumbnail[44180ad4-...] received
[2026-11-18 06:57:59,790: INFO/ForkPoolWorker-7] Task catalog.tasks.make_thumbnail[44180ad4-...] succeeded in 0.046464417000152025s: '商品 1 の画像は (1200, 800)'
```

✅ 検証済み: Django 5.2 / Pillow 13.0 / MySQL 8.4（2026-11-18。手元と同じファイルを別の場所に写し、プロジェクト名 `p46f-verify` で確認した）

`(1200, 800)` は、P4-6c で作った `/tmp/sample.jpg`（横 1200・縦 800 の薄茶色の四角）の大きさです。worker が、**db** から商品を読み、**倉庫 `media`** から画像を開けました。

**🔎 答えの見つけ方**: 「worker の中で、ある1行が動くか」を仕事より先に試したいときは、worker の箱で Django の shell を開く。

```bash
docker compose exec worker .venv/bin/python src/manage.py shell -c "from catalog.models import Product; print(Product.objects.get(id=1).image.name)"
```

```text
products/s_kQh8c6c.jpg
```

✅ 検証済み: 2026-11-18（あなたの手元では `products/sample...jpg` のような名前になる）

worker の中で動いた答えが出れば、worker から db に届いています。

**📖 しくみ**

- **何をしているか**: メモに書いてあった番号から、worker が自分で商品を読み、元画像を開きました。
- **なぜ必要か**: メモに入っているのは「仕事の名前と番号」だけです（P4-6e の 📇 メッセージ）。画像そのものや商品の情報は入っていません。だから worker は、**db と倉庫に取りに行く**必要があります。メモを小さくしておけば、受付箱（Redis）も軽いままです。
- **どういう原理で動くか**:
  1. **worker の作業係**が、メモの番号 `1` で `make_thumbnail(1)` を呼ぶ
  2. **Django**（worker の中）が、`settings.py` の `DB_HOST=db` を見て、back の道で **MySQL** に `SELECT ... WHERE id = 1` を送る
  3. **MySQL** が商品の行を返す。`image` 列には `products/sample...jpg` という**文字**が入っている
  4. **Pillow** が、`MEDIA_ROOT`（`/app/media`）＋その文字のファイルを開く。そこは倉庫 `media` なので、api が書いた画像が見える（P4-6d）

> 📇 **Image.open** — 正式名称: Pillow の **`PIL.Image.open()`**
> かみくだくと: 画像のファイルを開いて、Python で**さわれる画像**にする。
> 似た言葉との違い: Python の `open()` = ファイルを**ただのバイトの並び**として開く。`Image.open()` = 「これは JPEG で、横 1200・縦 800」と**画像として**読む。
> この教材では: 倉庫 `media` の元画像を、worker の中で開く。

---

### チャンク2: db にサムネイルの列を足す（`apps/api/src/catalog/models.py`）— 地図の②

**このチャンクの目的**: 🛠️ で選んだ **B**（db に新しい列を足して、サムネイルの場所を書く）のための列を作る。

**🤔 先に考える**: `models.py` に列を1行足して**保存だけ**し、`migrate` を打つ**前に**画像を送ったら、どうなると思いますか？
A. いつもどおり `saved` が返る　B. api がエラーになる

<details><summary>答え</summary>

**B** です。api（`runserver`）は保存すると**自動で読み直す**ので、api の `Product` はもう「`thumbnail` 列がある」と思っています。でも db の表には、まだその列がありません。api が db に「`thumbnail` 列もちょうだい」とたずねて、db に断られます。

```text
django.db.utils.OperationalError: (1054, "Unknown column 'catalog_product.thumbnail' in 'field list'")
"POST /api/products/1/image HTTP/1.1" 500 4201
```

✅ 検証済み: 2026-11-18（`Unknown column` = 「その列は知らない」。`curl` の答えには長いエラーの全文が出る）

試してみたくなったら、保存したあと `migrate` の前に送ってみてください。`migrate` のあとは、また `saved` に戻ります。

</details>

**🎯 書くもの**: `catalog/models.py` の `image = ...` の行のすぐ下に、`thumbnail` という画像の列を1行足す。置き場は `thumbs/`。画像が無い商品もあるので、空でもよいことにする。

**✍️ 自分で書く**（`ImageField` は P4-6c に続いて2回目なので、穴埋めです）

```python
    thumbnail = models.___(upload_to="___", blank=___)
```

<details><summary>ヒント1: 使う部品の名前</summary>

すぐ上の `image = ...` の行と、ほとんど同じです。違うのは置き場のフォルダだけです。

</details>

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
     description = models.TextField(blank=True)
     image = models.ImageField(upload_to="products/", blank=True)
+    thumbnail = models.ImageField(upload_to="thumbs/", blank=True)
 
     def __str__(self):
```

</details>

**▶️ 確かめる**: 設計図（マイグレーション）を作って db に当てます。P4-6c と同じ2つのコマンドです。`___` を埋めて打ちます。

```bash
docker compose exec ___ .venv/bin/python src/manage.py ___ catalog
docker compose exec ___ .venv/bin/python src/manage.py ___
```

<details><summary>答え</summary>

```bash
docker compose exec api .venv/bin/python src/manage.py makemigrations catalog
docker compose exec api .venv/bin/python src/manage.py migrate
```

</details>

```text
Migrations for 'catalog':
  src/catalog/migrations/0003_product_thumbnail.py
    + Add field thumbnail to product
```

```text
Operations to perform:
  Apply all migrations: catalog
Running migrations:
  Applying catalog.0003_product_thumbnail... OK
```

✅ 検証済み: 2026-11-18

> 💡 **migrate は api から1回打てば、worker の分も済みます。** db は1つで、api も worker も同じ db を見ているからです（全体の地図の「② 道」）。設計図のファイル `0003_product_thumbnail.py` も、bind mount で Mac と worker の `src` に同時にできています。

**🔎 答えの見つけ方**: 設計図が db に当たったかは `showmigrations`。`[X] 0003_product_thumbnail` と `X` が付いていればよい（P4-6c と同じ）。どんな SQL になったかは `sqlmigrate`。

```bash
docker compose exec api .venv/bin/python src/manage.py sqlmigrate catalog 0003
```

```text
ALTER TABLE `catalog_product` ADD COLUMN `thumbnail` varchar(100) DEFAULT '' NOT NULL;
ALTER TABLE `catalog_product` ALTER COLUMN `thumbnail` DROP DEFAULT;
```

✅ 検証済み: 2026-11-18（`varchar(100)` = 100文字までの**文字の列**。画像そのものではなく、場所の文字が入る）

**📖 しくみ**

- **何をしているか**: 商品の表 `catalog_product` に、サムネイルの場所を書く**文字の列** `thumbnail` を足しました。
- **なぜ必要か**: P4-6g で画面に出すとき、「商品 1 のサムネイルはどこ？」を db にたずねれば、すぐ分かるようにするためです。フォルダの中を探し回らなくて済みます。
- **どういう原理で動くか**:
  1. あなたが `models.py` に1行足す。**api** は保存で読み直すが、**db** はまだ変わらない（🤔 のエラーはこの間に起きる）
  2. `makemigrations` で、**Django** が差分を `0003_product_thumbnail.py` に書く
  3. `migrate` で、**Django**（api の箱の中）が `ALTER TABLE ... ADD COLUMN` を **MySQL** に送る
  4. **MySQL** が列を足す。worker も同じ db を見ているので、worker が起動し直せば新しい列を使える（チャンク3）

---

### チャンク3: 縮めて保存し、場所を db に書く（`apps/api/src/catalog/tasks.py`）— 地図の③

**このチャンクの目的**: チャンク1 で開いた画像を縦横 200 以内に縮め、`thumbs/` に保存して、チャンク2 の列にその場所を書く。

**🤔 先に考える**: サムネイルを保存するのは **worker の箱**です。保存したあと、**api の箱**から `ls /app/media/thumbs/` を打ったら、サムネイルは見えると思いますか？
A. 見える　B. 見えない

<details><summary>答え</summary>

**A** です。api と worker は、**同じ倉庫 `media`** を `/app/media` につないでいます（P4-6d）。worker が倉庫に書いたものは、api の箱からもそのまま見えます。P4-6d で「api が書いた画像が worker から見える」を確かめたのと、向きが逆なだけです。

</details>

**🎯 書くもの**: `catalog/tasks.py` に5行足す。

1. いちばん上に、Django の `ContentFile` を読み込む1行
2. `img = Image.open(...)` のすぐ下に、次の4行
   - 画像を縦横 200 以内に縮める
   - 中身が空っぽの「メモリの中のファイル」を1つ作る
   - 縮めた画像を、そのファイルに JPEG で書く
   - そのファイルを、商品の `thumbnail` に `商品の番号.jpg` という名前で保存する

`return` の行は**変えません**。同じ `img.size` が、縮めたあとの大きさを返すようになります。

**🔬 1行ずつ分解**（はじめて書く形なので、打つ前に読みます）:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `from django.core.files.base import ContentFile` | コンテントファイル | Django の「メモリの中のファイル」を借りる | 無いと `NameError` |
| `img.thumbnail((200, 200))` | サムネイル（Pillow の `Image.thumbnail()`） | 縦横の比を保ったまま、**どちらも 200 以内**に縮める。`img` そのものを書き換える | `(1200, 800)` は `(200, 133)` になる。もともと小さい画像は**大きくしない**（`(100, 50)` は `(100, 50)` のまま。✅ 検証済み） |
| `thumb = ContentFile(b"")` | ビー（**bytes** の空っぽ） | 中身が空のファイルを、**ディスクではなくメモリの中**に作る | — |
| `img.save(thumb, format="JPEG")` | セーブ、フォーマット | 縮めた画像を JPEG の形にして、`thumb` に書く。ファイルの名前が無いので、形は `format=` で教える | `format=` を消すと `ValueError: unknown file extension:`（名前の拡張子から形を決められない。✅ 検証済み） |
| `product.thumbnail.save(f"{product_id}.jpg", thumb)` | **FieldFile.save()** | `thumbs/1.jpg` として**倉庫に書き**、商品の行の `thumbnail` 列に `"thumbs/1.jpg"` と**書いて db に保存**する。1行で2つの仕事をする | 同じ名前がもうあると、Django が `1_aB3xYz9.jpg` のように後ろに文字を足して、別の名前にする |

**✍️ 自分で書く**（はじめての形なので、上を見ながら**手で打ちます**）

```python
from django.core.files.base import ContentFile
```

```python
    img.thumbnail((200, 200))
    thumb = ContentFile(b"")
    img.save(thumb, format="JPEG")
    product.thumbnail.save(f"{product_id}.jpg", thumb)
```

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
+from django.core.files.base import ContentFile
 from PIL import Image
 
```

```diff
     product = Product.objects.get(id=product_id)
     img = Image.open(product.image)
+    img.thumbnail((200, 200))
+    thumb = ContentFile(b"")
+    img.save(thumb, format="JPEG")
+    product.thumbnail.save(f"{product_id}.jpg", thumb)
     return f"商品 {product_id} の画像は {img.size}"
```

</details>

**▶️ 確かめる**: 今度は、送る**前に**自分で worker を起動し直します（チャンク1 で見たとおり、起動し直さないと古いコードのままです。コマンドは自分で思い出して打ちます）。そのあと画像を送ります。

やることは、チャンク1 の ▶️ と同じ3つです: ① worker を起動し直す → ② worker のログを流す → ③ 別のタブで画像を送る。ログに下のような `succeeded` の行が出れば OK です。

<details><summary>ヒント: 3つのコマンド（チャンク1 の ▶️ に同じものがある）</summary>

```bash
docker compose restart worker
docker compose logs -f --since 1m worker
curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
```

</details>

```text
[2026-11-18 06:58:33,100: INFO/MainProcess] Task catalog.tasks.make_thumbnail[a761d1a0-...] received
[2026-11-18 06:58:33,116: INFO/ForkPoolWorker-7] Task catalog.tasks.make_thumbnail[a761d1a0-...] succeeded in 0.01519662500004415s: '商品 1 の画像は (200, 133)'
```

✅ 検証済み: 2026-11-18

`(1200, 800)` が `(200, 133)` になりました。次に、🤔 の答え合わせです。**api の箱**からサムネイルを探します。

```bash
docker compose exec api ls -l /app/media/thumbs/
```

```text
total 4
-rw-r--r-- 1 root root 1096 Nov 18 12:58 1.jpg
```

✅ 検証済み: 2026-11-18（1096 バイト。元の画像は約 15,000 バイトだった。何度も送ると `1_aB3xYz9.jpg` のような名前が増えていく）

worker が書いたファイルが、api の箱から見えました。

**🔎 答えの見つけ方**: 「db に何が書かれたか」は、商品の行を直接見る。

```bash
docker compose exec db mysql -uec -pec-pass ec -e "SELECT id, image, thumbnail FROM catalog_product"
```

```text
id	image	thumbnail
1	products/s_kQh8c6c.jpg	thumbs/1_YNCivJp.jpg
```

✅ 検証済み: 2026-11-18（検証では送るファイルの名前が `s.jpg` だったので `s_...` になっている。あなたの手元では `sample...` になる。最初に `mysql: [Warning] Using a password on the command line interface can be insecure.` という注意が出る。パスワードをコマンドに書いたことへの注意で、練習用なので気にしなくてよい）

「サムネイルを**目で見たい**」ときは、箱の中のファイルを Mac に写して開く。

```bash
docker compose cp api:/app/media/thumbs/1.jpg /tmp/thumb.jpg
file /tmp/thumb.jpg
open /tmp/thumb.jpg
```

```text
/tmp/thumb.jpg: JPEG image data, JFIF standard 1.01, ... 200x133, components 3
```

✅ 検証済み: 2026-11-18（`docker compose cp` は「箱の中のファイルを Mac にコピーする」。`open` で Mac のプレビューが開き、小さな薄茶色の四角が見える）

**📖 しくみ**

- **何をしているか**: 画像を縮めて、倉庫の `thumbs/` に保存し、db の `thumbnail` 列にその場所を書きました。
- **なぜ必要か**: 一覧の画面に大きな画像を何枚も出すと、表示が遅くなります。小さなサムネイルを**1回だけ**作っておけば、画面はそれを使えます（P4-6g）。
- **どういう原理で動くか**:
  1. **Pillow** が、メモリの中の画像を `(200, 133)` に縮める（ディスクにはまだ何も書いていない）
  2. **Pillow** が、縮めた画像を JPEG の形にして、メモリの中のファイル `thumb` に書く
  3. **Django** が `MEDIA_ROOT` ＋ `upload_to="thumbs/"` ＋ `1.jpg` から `/app/media/thumbs/1.jpg` を組み立て、`thumbs/` フォルダが無ければ作って、ファイルを書く。そこは倉庫 `media` なので、api の箱からも見える
  4. **Django** が、商品の行の `thumbnail` 列に `"thumbs/1.jpg"` を入れて、**MySQL** に `UPDATE` を送る

<details><summary>💡 補足: PNG の画像を送ると失敗することがある</summary>

透明な部分を持つ PNG（Pillow では「RGBA」という形）は、そのまま JPEG にできません。

```text
OSError: cannot write mode RGBA as JPEG
```

✅ 検証済み: Pillow 13.0（2026-11-18）

この教材では JPEG だけを送るので、扱いません。本物のアプリでは、縮める前に `img = img.convert("RGB")` で形をそろえることがよくあります。

</details>

> 📇 **ContentFile** — 正式名称: Django の **`django.core.files.base.ContentFile`**
> かみくだくと: ディスクではなく**メモリの中**にある、Django 用のファイル。
> 似た言葉との違い: P4-6c の `UploadedFile` = 送られてきたファイル。`ContentFile` = プログラムの中で**自分で作った**中身を、ファイルとして扱うための入れ物。
> この教材では: 縮めた画像をいったん入れておき、`product.thumbnail.save(...)` に渡す。

---

### 🧪 壊してみる

worker から倉庫 `media` を外すと、どうなるでしょう。

1. **予想**: `compose.yaml` の **worker の** `volumes:` から `- media:/app/media` の1行だけを消して、`docker compose up -d worker` で worker を作り直します。画像を送ったら、どうなると思いますか？
   A. api がエラー（500）を返す　B. api は `saved` を返すが、worker のログにエラーが出る
2. **実行**: 1行消して保存し、worker を作り直して、送ります（ログは流したままにしておきます）。

   ```bash
   docker compose up -d worker
   curl -s -F image=@/tmp/sample.jpg localhost:8000/api/products/1/image
   ```

3. **見る**: `curl` の答えは、いつもどおりです。

   ```text
   {"status": "saved"}
   ```

   worker のログには、次が出ます。

   ```text
   [2026-11-18 06:58:54,645: INFO/MainProcess] Task catalog.tasks.make_thumbnail[610b0002-...] received
   [2026-11-18 06:58:54,669: ERROR/ForkPoolWorker-7] Task catalog.tasks.make_thumbnail[610b0002-...] raised unexpected: FileNotFoundError(2, 'No such file or directory')
   Traceback (most recent call last):
     ...
     File "/app/src/catalog/tasks.py", line 11, in make_thumbnail
       img = Image.open(product.image)
     ...
   FileNotFoundError: [Errno 2] No such file or directory: '/app/media/products/s_bs27Agn.jpg'
   ```

   ✅ 検証済み: 2026-11-18（`line 11` の数字とファイル名は、あなたの書き方と送ったファイルで変わる）

   部品に分けて読みます。

   | 部品 | 意味 |
   | --- | --- |
   | `ERROR/ForkPoolWorker-7` | worker の作業係が、仕事に**失敗した** |
   | `raised unexpected: FileNotFoundError` | 「ファイルが見つからない」というエラーで止まった |
   | `tasks.py", line 11` / `Image.open(product.image)` | チャンク1 の `Image.open` の行で止まった |
   | `'/app/media/products/s_bs27Agn.jpg'` | db には場所が書いてある（api が書いた）。でも worker の `/app/media` は、倉庫ではなく**ただの空のフォルダ**なので、ファイルが無い |

   答えは **B** です。api は**メモを入れたらすぐ返事をする**ので（P4-6e）、worker が失敗したことを**知りません**。仕事を任せる形にすると、失敗は **worker のログにしか出ない**のです。

   > ⚠️ このとき db の `thumbnail` 列は、**前のサムネイルのまま**です（🔎 の `SELECT` で見られる）。画像は新しいのに、サムネイルは古い。画面だけ見ていると気づけません。

4. **元に戻す**: `- media:/app/media` の行を戻して保存し、`docker compose up -d worker` で作り直します。もう一度送って、worker のログに `succeeded ... (200, 133)` が出ることを確かめます。

### 🐳 Docker の中の図（後）

動く図のページ（`docs/visual/docker-inside.html`）の **「6f」** のボタンを押し、**worker の箱**をクリックしてみてください。右の説明に、今日 worker がするようになったこと（db を読む・倉庫に書く）が出ます。次に **倉庫 media** をクリックして、`thumbs/` が増えたことを確かめます。

> 🗺️ 全体の地図（`docs/02-system-map.md`）の「1枚の地図」「🔎 調べ方の地図」「つまずきメモ」にも、今日の分を書き足しました。

### ✏️ 自分で地図を描く

冒頭の 🗺️ 今日の地図を**見ずに**、`＿＿＿` を埋めてみてください。各行の右に「なぜ」を一言ずつ書くのがポイントです。

```text
受付箱から「商品 1 のサムネイルを作って」のメモ
        │
        ▼
worker の箱  make_thumbnail
  ① ＿＿＿ から商品 1 を読み、倉庫 ＿＿＿＿ の元画像を開く
       なぜ: メモには ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ しか入っていないから
  ② db の商品の表に、＿＿＿＿＿＿＿＿＿ 列を足す（migrate は ＿＿＿ の箱から1回）
       なぜ: ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
  ③ 縦横 ＿＿＿ 以内に縮めて ＿＿＿＿＿/ に保存し、② の列に場所を書く
       なぜ: ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
        │
        ├──▶ 倉庫 media の /app/media/thumbs/1.jpg （＿＿＿ の箱からも見える）
        └──▶ db の thumbnail 列 = "＿＿＿＿＿＿＿＿＿＿＿"
```

<details><summary>答え合わせ</summary>

```text
受付箱から「商品 1 のサムネイルを作って」のメモ
        │
        ▼
worker の箱  make_thumbnail
  ① db から商品 1 を読み、倉庫 media の元画像を開く
       なぜ: メモには 仕事の名前と商品の番号 しか入っていないから
  ② db の商品の表に、thumbnail 列を足す（migrate は api の箱から1回）
       なぜ: サムネイルの場所を、あとで db にたずねればすぐ分かるようにするため
  ③ 縦横 200 以内に縮めて thumbs/ に保存し、② の列に場所を書く
       なぜ: 画面に小さな画像を出せるようにするため。縮めるのは1回だけで済む
        │
        ├──▶ 倉庫 media の /app/media/thumbs/1.jpg （api の箱からも見える）
        └──▶ db の thumbnail 列 = "thumbs/1.jpg"
```

「なぜ」は、言い方がちがっても、意味が合っていれば正解です。埋められなかった所があれば、そのチャンクの 📖 しくみ だけ読み返します。最後に、動く図のページの「6f」と見比べます。

</details>

### 📝 ひとこと

「〜だと思っていたけど、実は〜」を1行書きます。書いたものは `docs/notes.md` に貯めます。うまく書けなければ、書かずに先へ進んでも大丈夫です。

例: 「worker が失敗したら api もエラーになると思っていたけど、実は api は何も知らずに saved を返していた」

### ✅ できるようになったこと

- [ ] worker が db と倉庫 `media` の両方を使えるのはなぜかを、道と倉庫の言葉で説明できる
- [ ] `models.py` を変えたのに `migrate` していないと何が起きるかを、打つ前に予想できる
- [ ] worker が仕事に失敗したとき、api の答えではなく worker のログで気づける

**残った問い**: サムネイルは倉庫の `/app/media/thumbs/1.jpg` にできた。でも、倉庫の中のファイルは**ブラウザからは見えない**（窓口が無い）。**画面（web）にサムネイルを出すには、どうすればいいのか？**

---
▶ **次**: P4-6g 画面にサムネイルを出す

---

## P4-6g: 画面にサムネイルを出す

**❓ この回の問い**: 前回（P4-6f）で、サムネイルは倉庫の `/app/media/thumbs/1.jpg` にできた。でも倉庫の中のファイルには、ブラウザからたどり着く道が無い。
→ **ブラウザ（Mac）は、どの道を通って、倉庫の中のサムネイルを取りに行けばいいのか？**

**作ること / 確かめること**: Django に `/media/...` の画像を配らせる。商品一覧 API に、サムネイルの住所（URL）を足す。web の箱（Vite）に、`/media` も api へ中継させる。http://localhost:5173 の商品一覧にサムネイルが出ることを確かめる
**重要度**: 🔴 毎日使う — 「ブラウザで動くコード」と「箱の中で動くコード」で、使える住所が違う。これを取り違えると、画像も API もつながらないから
**前ステップとの接続**: P4-6f で作ったサムネイルを、画面まで届ける。`compose.yaml` は変えない。変えるのは `config/settings.py`・`config/urls.py`・`config/api.py`・`apps/web/vite.config.js`

**P4-6 ぜんたいの地図での位置**: ⑤（画面にサムネイルを出す）

### 🔁 前回の思い出し

**問い**: P4-6f の 🧪 で、worker が失敗したのに、api は `{"status": "saved"}` と返しました。なぜでしたか？ 一言で。

<details><summary>答え</summary>

api は、受付箱に**メモを入れただけ**で、worker の仕事の結果を待っていないからです（非同期 / asynchronous）。失敗は **worker のログにしか出ません**。今日は、そうやって worker が作ったサムネイルを、画面に出します。

</details>

### 🛠️ 先に自分で決める

教材が答えを出す前に、**あなたが画像の住所を決めます。** このあとのチャンクは、あなたの選んだ方針の答え合わせとして進みます。

**困りごと**（P4-6f の残った問い）

- サムネイルは倉庫 `media` の `thumbs/1.jpg` にある。api と worker の箱からは見える
- でも、商品一覧の画面を描いている **React のコードは、Mac のブラウザの中で動いています**（web の箱が配った JavaScript を、ブラウザが受け取って動かす）
- `App.jsx` には、P4-5 のときから `<img src={p.thumbnail_url} />` の行が用意されている。この `src` に、どんな住所を入れればいいか

**🤔 どの住所を選びますか？** 1つ選んで、理由を一言で書いてください（「分からない」でも大丈夫です）。

| 案 | `<img src=...>` に入れる住所 | ブラウザが取りに行く先 |
| --- | --- | --- |
| A | `http://api:8000/media/thumbs/1.jpg` | サービス名 `api` の箱 |
| B | `http://localhost:8000/media/thumbs/1.jpg` | Mac の窓口 8000 番 → api の箱 |
| C | `/media/thumbs/1.jpg`（頭に何も付けない） | いま開いているページと同じ所（localhost:5173 → web の箱）→ web が api へ中継 |

<details><summary>ヒント</summary>

1. サービス名（`api`、`db` など）で呼び合えるのは、**どこにいるもの**どうしでしたか？（P4-6b の 🧪、`docs/02-system-map.md` の「② 道（ネットワーク）」）
2. いまの画面は、商品一覧を `fetch("/api/products")` で取りに行っています。この `/api/...` は、誰がどこへ中継していましたか？（P4-4、`vite.config.js` の `proxy`）

</details>

<details><summary>答え合わせ</summary>

この教材は **C** で進めます。

| 案 | 判定 | 理由 |
| --- | --- | --- |
| A | ✗ | ブラウザは **Mac の上**で動いています。Mac は Docker の道（front / back）にいないので、`api` という名前を知りません。画像は壊れて表示されます |
| B | △ 動く | この Mac では動きます（8000 番は公開されている）。でも、住所に「`localhost:8000`」と**場所を書き込んで**しまうので、別のパソコンや本番では使えません。画面と API で窓口も2つに分かれます |
| C | ◎ | いまの `/api` と同じ道です。ブラウザは「いま開いているページ（localhost:5173）」に頼むだけ。中継は、**Docker の道（front）の中にいる web の箱**がするので、`api` という名前が使えます。本番で入口を1つにまとめるとき（P6-1 の Nginx）も、この形のまま使えます |

A がだめなことは、Mac から実際に確かめられます。

```bash
curl -sS -I http://api:8000/media/thumbs/1.jpg
```

```text
curl: (6) Could not resolve host: api
```

✅ 検証済み: macOS / Docker Compose v5.5.1（2026-11-19）

`Could not resolve host` = 「`api` という名前の住所が分からない」。Mac のブラウザも同じです。

</details>

### 🐳 Docker の中の図

動く図のページ（`docs/visual/docker-inside.html`。ブラウザで `open docs/visual/docker-inside.html`）で、**「6f」と「6g」のボタンを交互に押して**比べてください。赤く光るのが今日変わる所です。ブラウザ → 窓口 5173 → web → api → 倉庫 media という、**画像が届くまでの線**が増えます。

### 🧭 全体の中のいま

`docs/02-system-map.md` の「1枚の地図」に、今日さわる所を ★ で示します。

```text
Mac の道具       窓口（④）              Docker の中

                                        【道 front】 web・api
ブラウザ      ── :5173 どこからでも ──▶ web ──▶ api（画面から API を呼ぶ）
                                        web ──▶ api の /media（画像も中継する）  ★ 今日
curl          ── :8000 どこからでも ──▶ api
                                        api が /media/... で倉庫の画像を返す    ★ 今日
Zed           ── :5678 Mac だけ     ──▶ api（デバッガ）

                                        【道 back】 api・worker・db・redis
                                        （今日は変わらない）
                                        api・worker ──▶ 倉庫 media（画像。消えない）
```

**見てほしいところ**: 今日も**新しい箱・道・倉庫・窓口は増えません。** P4-4 で作った「web が `/api` を api へ中継する」道に、**`/media` も乗せる**だけです。

### 🗺️ 今日の地図

```text
Mac のブラウザ（React の <img src="/media/thumbs/1.jpg">）
        │  localhost:5173（窓口）
        ▼
web の箱（Vite）  vite.config.js の proxy
  ③ /media で始まる頼みを、api:8000 へ中継する          … チャンク3（vite.config.js）
        │  道 front
        ▼
api の箱（Django）
  ① /media/... の頼みに、倉庫 media のファイルを返す    … チャンク1（settings.py と urls.py）
  ② 商品一覧に thumbnail_url（画像の住所）を入れる      … チャンク2（api.py）
        │
        ▼
倉庫 media の /app/media/thumbs/1.jpg（P4-6f で worker が作った）
```

**見てほしいところ**: 番号は**作る順**です（奥の api から作り、最後に入口の web をつなぐ）。画像が通る順は、**上から下**です。

### 6g-0. このステップの初出

**Django**: `MEDIA_URL`、`django.conf.urls.static.static()`、`ninja.Field(alias=...)`
**Docker**: なし（P4-4 の `proxy` と `up -d --build` を、もう一度使う）

---

### チャンク1: Django に画像を配らせる（`apps/api/src/config/settings.py` と `config/urls.py`）— 地図の①

**このチャンクの目的**: 倉庫の中のファイルを、**URL で取りに来られる**ようにする。まずは Mac の窓口 8000 番から、api に直接たずねて確かめる。

> 💡 このチャンクだけ、ファイルを**2つ**さわります。2つで1つの仕事（「`/media/` という住所」と「その住所への道」）なので、分けると片方だけでは何も確かめられないためです。書くのは合わせて4行です。

**🤔 先に考える**: いま（何も書く前に）、Mac で次を打つとどうなると思いますか？

```bash
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/media/thumbs/1.jpg
```

A. `200`（画像が返る）　B. `404`（見つからない）

理由も一言で（「分からない」でも大丈夫です）。ヒント: ファイルは倉庫にあります（P4-6f で `ls` で見た）。では、Django は `/media/...` という URL を知っているでしょうか？ `config/urls.py` には、何の道が書いてありましたか？

<details><summary>答え</summary>

**B（`404`）** です。

```text
404
```

✅ 検証済み: Django 5.2.18（2026-11-19）

ファイルは倉庫にあっても、Django の **URL の一覧**（`config/urls.py`）には `api/` の道しかありません。知らない URL には「見つからない」と返します。api のログにも出ます。

```text
Not Found: /media/thumbs/1.jpg
"GET /media/thumbs/1.jpg HTTP/1.1" 404 2228
```

</details>

**🎯 書くもの**:

1. `settings.py` の `MEDIA_ROOT` のすぐ下に、「画像の住所は `/media/` で始める」という1行を足す
2. `urls.py` で、`settings` と `static` を読み込む2行を足し、`urlpatterns` の**あと**に「`MEDIA_URL` の住所に来たら `MEDIA_ROOT` のファイルを返す」道を1行足す

**🔬 1行ずつ分解**（はじめて書く形なので、打つ前に読みます）:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `MEDIA_URL = "/media/"` | メディア ユーアールエル（**MEDIA_URL** 設定） | 倉庫の画像を、ブラウザから見るときの**住所の頭**。P4-6c で決めた `MEDIA_ROOT`（**置き場**）と対になる | 無いと、画像の住所が `/thumbs/1.jpg` のように頭なしになる。`static()` は空の頭を受け付けず `ImproperlyConfigured: Empty static prefix not permitted` |
| `from django.conf import settings` | — | `settings.py` の値を読む入口 | 無いと `NameError` |
| `from django.conf.urls.static import static` | スタティック（**`static()`** 関数） | 「ある住所の頭 → あるフォルダのファイル」という道を作る道具 | 無いと `NameError` |
| `urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` | プラス イコール | `/media/` で始まる URL が来たら、`/app/media`（倉庫）の下から同じ名前のファイルを探して返す道を、一覧の**最後に足す** | 無いと 🤔 のとおり `404` |

**✍️ 自分で書く**（はじめての形なので、下を見ながら**手で打ちます**。コピペはしません）

`apps/api/src/config/settings.py`（`MEDIA_ROOT` の行の下に1行）:

```python
MEDIA_ROOT = "/app/media"
MEDIA_URL = "/media/"
```

`apps/api/src/config/urls.py`（全体。打つのは上の2行と、いちばん下の1行）:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from config.api import api

urlpatterns = [
    path("api/", api.urls),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
 MEDIA_ROOT = "/app/media"
+MEDIA_URL = "/media/"
```

```diff
+from django.conf import settings
+from django.conf.urls.static import static
 from django.urls import path
 
```

```diff
     path("api/", api.urls),
 ]
+urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

</details>

**▶️ 確かめる**: 保存したら、🤔 と同じコマンドを打ちます。api（runserver）は**保存すると自分で読み直す**ので、起動し直しは要りません（worker とのちがい。P4-6e チャンク2 の ⚠️）。今度は `-I`（中身ではなく**見出し**だけ見る）を付けます。

```bash
curl -s -I localhost:8000/media/thumbs/1.jpg
```

```text
HTTP/1.1 200 OK
Server: WSGIServer/0.2 CPython/3.13.18
Content-Type: image/jpeg
Content-Length: 1096
```

✅ 検証済み: Django 5.2.18（2026-11-19。手元と同じファイルを別の場所に写し、プロジェクト名 `p46g-verify` で確認した）

`200` と `image/jpeg`（JPEG の画像）が返りました。`1096` は、P4-6f の `ls -l` で見たサムネイルの大きさ（バイト）と同じです。ブラウザで http://localhost:8000/media/thumbs/1.jpg を開くと、小さな薄茶色の四角が見えます。

> ⚠️ `thumbs/1.jpg` が無いときは、`docker compose exec api ls /app/media/thumbs/` で見えた名前に置きかえてください。

**🔎 答えの見つけ方**: 「Django がその URL をどう扱ったか」は、**api のログの最後の数字**を見る。

```bash
docker compose logs --since 1m api | grep media
```

```text
"GET /media/thumbs/1.jpg HTTP/1.1" 404 2228   ← 書く前（道が無い）
"HEAD /media/thumbs/1.jpg HTTP/1.1" 200 0     ← 書いた後（-I は HEAD という聞き方）
```

✅ 検証済み: 2026-11-19

`404` なら「その住所への道が無い」、`200` なら「返せた」。ファイルがあるのに `404` のときは、`urls.py` を疑います。

**📖 しくみ**

- **何をしているか**: `/media/` で始まる URL と、倉庫 `media` のフォルダを、1対1で結びました。
- **なぜ必要か**: 倉庫の中のファイルは、**箱の中のフォルダ**です。ブラウザが取りに来られるのは **URL** だけです。だから「この URL ならこのファイル」という対応表が要ります。
- **どういう原理で動くか**:
  1. **runserver** が `GET /media/thumbs/1.jpg` を受け取る
  2. **Django** が `urls.py` の一覧を上から見る。`api/` には合わない。最後の `static()` の道（`/media/` で始まる）に合う
  3. `/media/` を取り除いた残り `thumbs/1.jpg` を、`document_root`（`/app/media`）の下で探す
  4. `/app/media` は倉庫 `media` なので、worker が書いたファイルが見える（P4-6d）。見つかったら中身を返す

> 🔓 **教材用の簡略化**: `static()` の道は、**`DEBUG = True` のときだけ**作られます（Django のコードに `if not settings.DEBUG ... return []` と書いてある）。Django 自身が画像を配るのは開発中だけで、本番では入口の **Nginx** が倉庫から直接配ります（P6-1）。🧪 で確かめます。

> 📇 **MEDIA_URL** — 正式名称: Django の設定 **`MEDIA_URL`**
> かみくだくと: アップロードされたファイルを、**ブラウザから見るときの住所の頭**。
> 似た言葉との違い: `MEDIA_ROOT` = 箱の中の**置き場**（`/app/media`）。`MEDIA_URL` = 外から見たときの**住所**（`/media/`）。同じファイルを、2つの言葉で指している。
> この教材では: `/media/` に決め、`static()` と次のチャンクの `thumbnail_url` で使う。

---

### チャンク2: 商品一覧に画像の住所を入れる（`apps/api/src/config/api.py`）— 地図の②

**このチャンクの目的**: 画面（React）が「どの画像を出せばいいか」を知れるように、商品一覧の答えにサムネイルの住所を入れる。

**🤔 先に考える**: `apps/web/src/App.jsx` を開いて、`<img` の行を探してください。React は、商品のどの名前の値を、画像の住所として待っていますか？ 一言で。

<details><summary>答え</summary>

**`thumbnail_url`** です（`{p.thumbnail_url && (<img src={p.thumbnail_url} alt="" />)}`）。P4-5 のときから用意してあり、値が無いので何も出ていませんでした。いまの商品一覧の答えには、`id`・`name`・`price`・`description` しか入っていません。

```bash
curl -s localhost:8000/api/products
```

</details>

**🎯 書くもの**: `api.py` の `ProductOut` に、「`thumbnail_url` という名前で、商品の `thumbnail` 列の住所を出す」1行を足す。そのために `ninja` から `Field` も読み込む。

**🔬 1行ずつ分解**（はじめて書く形なので、打つ前に読みます）:

| 部品 | 読み方（正式名称） | 意味 | 無いと / 変えるとどうなる |
| --- | --- | --- | --- |
| `Field`（import に足す） | フィールド（Django Ninja の **`Field`**。中身は Pydantic の Field） | 答えの1項目に、細かい指定（初期値・別名）を付ける道具 | 無いと `NameError` |
| `thumbnail_url: str \| None` | 型の注釈 | 答えに `thumbnail_url` という項目を出す。中身は文字か、無いとき `null` | — |
| `= Field(None, alias="thumbnail")` | エイリアス（**alias**、別名） | 値は、商品の **`thumbnail` 列から取ってくる**。`None` は「無いときは null」 | `alias` が無いと、`thumbnail_url` という列を探して見つからず、いつも `null` |

`alias` は P4-5 の `Header(alias="X-Cart-Id")` でも使いました。あちらは「`X-Cart-Id` という見出しから取る」、こちらは「`thumbnail` という列から取る」です。

**✍️ 自分で書く**（下を見ながら**手で打ちます**）

```python
from ninja import Field, File, Header, ModelSchema, NinjaAPI, Schema, UploadedFile
```

```python
class ProductOut(ModelSchema):
    thumbnail_url: str | None = Field(None, alias="thumbnail")

    class Meta:
        model = Product
        fields = ["id", "name", "price", "description"]
```

（`import` の行は `Field, ` を足すだけ。`ProductOut` は、`class Meta:` の上に1行と空行を足すだけです）

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
 from django.shortcuts import get_object_or_404
-from ninja import File, Header, ModelSchema, NinjaAPI, Schema, UploadedFile
+from ninja import Field, File, Header, ModelSchema, NinjaAPI, Schema, UploadedFile
 
 from catalog.models import Product
```

```diff
 class ProductOut(ModelSchema):
+    thumbnail_url: str | None = Field(None, alias="thumbnail")
+
     class Meta:
         model = Product
```

</details>

**▶️ 確かめる**: 商品一覧を、api に直接たずねます（読みやすく並べるため、`python3 -m json.tool` に通します）。

```bash
curl -s localhost:8000/api/products | python3 -m json.tool --no-ensure-ascii
```

```text
[
    {
        "thumbnail_url": "/media/thumbs/1.jpg",
        "id": 1,
        "name": "木のマグカップ",
        ...
    },
    {
        "thumbnail_url": null,
        "id": 2,
        ...
```

✅ 検証済み: django-ninja 1.7.3（2026-11-19。あなたの手元では、P4-6f で何度も送っていれば `/media/thumbs/1_xxxxxxx.jpg` のような名前になる）

商品 1 には住所、サムネイルの無い商品 2 には `null` が入りました。

では、画面を開いてみます。http://localhost:5173 を開いてください。

**画像は出ません。** 住所は届いているのに、なぜでしょう。ブラウザが実際に取りに行った先を、Mac からたずねます。

```bash
curl -s -I localhost:5173/media/thumbs/1.jpg
```

```text
HTTP/1.1 200 OK
Content-Type: text/html
```

✅ 検証済み: Vite 8.3.6（2026-11-19）

`200` なのに、中身は `text/html`（**画像ではなく、ページの HTML**）です。`/media/thumbs/1.jpg` は「いま開いているページと同じ所」＝ **localhost:5173 の web の箱**に届きます。web の箱の Vite は、`/media` を**中継するように言われていない**ので、自分の画面の HTML を返してしまいました。ブラウザは HTML を画像として読めないので、何も出ません。これをチャンク3で直します。

**🔎 答えの見つけ方**: 画面に出ないときは、**住所を1つずつ直接たずねる**。

| たずねる先 | 何が分かるか |
| --- | --- |
| `curl -s localhost:8000/api/products` | API が住所を返しているか |
| `curl -s -I localhost:8000/media/...` | api の箱が画像を返せるか（チャンク1） |
| `curl -s -I localhost:5173/media/...` | ブラウザが**実際に**行く先で、画像が返るか（`Content-Type` を見る） |

ブラウザでは、開発者ツール（`Cmd + Option + I`）の **Network** タブで、`1.jpg` の行の Type や Status を見ても分かります。

**📖 しくみ**

- **何をしているか**: 商品一覧の答えに、`thumbnail` 列の住所を `thumbnail_url` という名前で入れました。
- **なぜ必要か**: db の `thumbnail` 列には `thumbs/1.jpg` という**置き場の中の名前**しか入っていません（P4-6f）。ブラウザに必要なのは、`MEDIA_URL` を頭に付けた**住所** `/media/thumbs/1.jpg` です。
- **どういう原理で動くか**:
  1. **Django Ninja** が、商品を1つずつ `ProductOut` の形に詰める
  2. `thumbnail_url` は `alias="thumbnail"` なので、商品の `thumbnail` を取りに行く。中身は Django の **FieldFile**（ファイルを指す値）
  3. Ninja は FieldFile を見つけると、**`.url`**（＝ `MEDIA_URL` ＋ 名前）に変えて答えに入れる。空なら `null`（Ninja のコード `ninja/schema.py` に `if isinstance(result, FieldFile): ... return result.url` と書いてある）

> 📇 **alias** — 正式名称: Pydantic / Django Ninja の **`Field(alias=...)`**
> かみくだくと: 答えの項目名と、**値を取ってくる元の名前**を別にする指定。
> 似た言葉との違い: `fields = [...]`（Meta）= 列の名前を**そのまま**出す。`alias` = **別の名前**で出す。
> この教材では: 列は `thumbnail`、React が待つ名前は `thumbnail_url`。そのずれを `alias` でつなぐ。

---

### チャンク3: web の箱に `/media` も中継させる（`apps/web/vite.config.js`）— 地図の③

**このチャンクの目的**: ブラウザ → web の箱 → api の箱、という `/api` と同じ道に、`/media` も乗せる（🛠️ の C）。

**🤔 先に考える**: `vite.config.js` を書き換えて**保存しただけ**で、web の箱の Vite に効くと思いますか？
A. 効く（api の runserver のように読み直す）　B. 効かない

理由も一言で（「分からない」でも大丈夫です）。ヒント: `compose.yaml` の web には、`volumes:`（Mac のフォルダを写す）がありますか？ `develop: watch:` で写しているのは、どのフォルダでしたか？ `apps/web/Dockerfile` の `COPY . .` は、いつ動きますか？

<details><summary>答え</summary>

**B（効かない）** です。

- web の箱には、Mac のフォルダを写す `volumes:` がありません。`vite.config.js` は、**イメージを作るとき**に `COPY . .` で箱の中へ**写し取られた**ものです（P4-4）
- `develop: watch:` で同期しているのは `./apps/web/src` だけです。`vite.config.js` は `src` の外にあります
- だから、Mac で保存しても、箱の中の `vite.config.js` は古いまま。**イメージを作り直す**必要があります

`docker compose restart web` でもだめです。restart は**同じイメージの同じ箱**を起動し直すだけで、イメージは作り直しません（✅ 検証済み: restart のあとも `502`／`text/html` のままだった。2026-11-19）。

</details>

**✍️ 自分で書く**（`proxy` は P4-4 に続いて2回目なので、**穴埋め**です）

`apps/web/vite.config.js` の `proxy` の中、`"/api"` の行の下に1行足します。`___` を埋めてください。

```js
        proxy: {
            // /api で始まるリクエストを、api サービスへ中継する
            "/api": "http://api:8000",
            "/media": "___",
        },
```

<details><summary>ヒント</summary>

1つ上の行と同じ相手です。中継するのは **web の箱の中の Vite** なので、Docker の道の中の名前が使えます。

</details>

<details><summary>答え合わせ（差分。前後2行つき）</summary>

```diff
             // /api で始まるリクエストを、api サービスへ中継する
             "/api": "http://api:8000",
+            "/media": "http://api:8000",
         },
     },
```

</details>

**▶️ 確かめる**: 保存したら、web のイメージを作り直して、箱を作り直します。コマンドは自分で思い出して打ちます（P4-4 で何度も使いました）。

<details><summary>ヒント: 作り直すコマンド</summary>

```bash
docker compose up -d --build web
```

</details>

そのあと、チャンク2 で `text/html` だったものを、もう一度たずねます。

```bash
curl -s -I localhost:5173/media/thumbs/1.jpg
```

```text
HTTP/1.1 200 OK
Vary: Origin
date: Thu, 19 Nov 2026 11:54:46 GMT
server: WSGIServer/0.2 CPython/3.13.18
```

✅ 検証済み: Vite 8.3.6 / Django 5.2.18（2026-11-19）

`server: WSGIServer`（Django の runserver）が返事をしています。**localhost:5173 にたずねたのに、答えたのは api** です。web の箱が中継した証拠です。api のログにも `"HEAD /media/thumbs/1.jpg HTTP/1.1" 200` が出ます。

最後に、http://localhost:5173 を開き直してください（`Cmd + Shift + R` で強めに読み直す）。**商品 1「木のマグカップ」の左に、サムネイルが出ます。** サムネイルの無い商品には、何も出ません。

✅ 検証済み: ブラウザ（Chromium）で開き、`<img>` の画像が `200 × 133` で読み込まれていることを確かめた（2026-11-19）

**📖 しくみ**

- **何をしているか**: web の箱の Vite に、「`/media` で始まる頼みも、`api:8000` へ送り直す」と教えました。
- **なぜ必要か**: ブラウザは Mac にいるので、Docker の道の中の `api` を知りません（🛠️ の A）。でも web の箱は **front の道**にいるので、`api` という名前で呼べます。だから、ブラウザが頼めるところ（窓口 5173）にいる web に、**中継役**をしてもらいます。
- **どういう原理で動くか**:
  1. **ブラウザ**が、`<img src="/media/thumbs/1.jpg">` を見て、いま開いているページと同じ `localhost:5173` に `GET /media/thumbs/1.jpg` を送る
  2. Mac の **窓口 5173** から、**web の箱**の Vite に届く
  3. **Vite** が `proxy` の一覧を見る。`/media` に合うので、front の道で `http://api:8000/media/thumbs/1.jpg` へ送り直す（`api` という名前は Docker が答える）
  4. **api の箱**の Django が、チャンク1 の道で倉庫のファイルを返す。Vite はそれを、そのままブラウザに返す

---

### 🧪 壊してみる

`DEBUG` を `False` にすると、どうなるでしょう（チャンク1 の 🔓 の答え合わせです）。

1. **予想**: `apps/api/src/config/settings.py` の `DEBUG = True` を **`DEBUG = False`** に変えて保存します（api は自分で読み直します）。そのあと、次の2つはどうなると思いますか？
   - `curl -s localhost:8000/api/products` の `thumbnail_url`
   - `curl -s -I localhost:8000/media/thumbs/1.jpg`
2. **実行**: 変えて保存し、2つを打ちます。

   ```bash
   curl -s localhost:8000/api/products
   curl -s -I localhost:8000/media/thumbs/1.jpg
   ```

3. **見る**:

   ```text
   [{"thumbnail_url": "/media/thumbs/1.jpg", "id": 1, ...
   ```

   ```text
   HTTP/1.1 404 Not Found
   ```

   ✅ 検証済み: Django 5.2.18（2026-11-19。localhost:5173 から頼んでも `404`。画面のサムネイルも消える）

   | 部品 | 意味 |
   | --- | --- |
   | `"thumbnail_url": "/media/thumbs/1.jpg"` | API は住所を**返し続ける**（db の列も `MEDIA_URL` も変わっていない） |
   | `404 Not Found` | でも、その住所に行くと**見つからない**。`static()` が `DEBUG = False` のとき道を作らないから（チャンク1 の 🔓） |
   | 404 のページが短い `Not Found` だけ | `DEBUG = False` だと、Django は「道の一覧」などの詳しい説明を出さない（本番で中身を見せないため） |

   ファイルは倉庫にあり、住所も正しいのに、**配る人がいない**状態です。本番（`DEBUG = False`）では、この「配る人」を Django ではなく **Nginx** にやらせます（P6-1）。

4. **元に戻す**: `DEBUG = True` に戻して保存し、`curl -s -I localhost:8000/media/thumbs/1.jpg` が `200` に戻ることを確かめます。

> ⚠️ `DEBUG = False` のまま放っておくと、エラーのときに詳しい説明が出なくなり、デバッグしにくくなります。必ず戻してください。

### 🐳 Docker の中の図（後）

動く図のページ（`docs/visual/docker-inside.html`）の **「6g」** のボタンを押し、**web の箱**をクリックしてみてください。右の説明に、今日 web がするようになったこと（`/media` も api へ中継する）が出ます。次に **ブラウザ** から倉庫までの赤い線を、指でたどってみます。

> 🗺️ 全体の地図（`docs/02-system-map.md`）の「1枚の地図」「🔎 調べ方の地図」「つまずきメモ」にも、今日の分を書き足しました。

### ✏️ 自分で地図を描く

冒頭の 🗺️ 今日の地図を**見ずに**、`＿＿＿` を埋めてみてください。各行の右に「なぜ」を一言ずつ書くのがポイントです。

```text
Mac の ＿＿＿＿＿（React の <img src="/media/thumbs/1.jpg">）
        │  localhost:＿＿＿＿（窓口）
        ▼
＿＿＿ の箱（Vite）  vite.config.js の proxy
  ③ /media で始まる頼みを、＿＿＿:8000 へ中継する
       なぜ: ブラウザは ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ から
       保存しただけで効かないのは: ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ から
        │  道 ＿＿＿＿＿
        ▼
api の箱（Django）
  ① /media/... の頼みに、倉庫 ＿＿＿＿ のファイルを返す（settings.py の ＿＿＿＿＿＿＿＿ と urls.py の static()）
       なぜ: ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
  ② 商品一覧に ＿＿＿＿＿＿＿＿＿＿＿＿ を入れる（alias で thumbnail 列から取る）
```

<details><summary>答え合わせ</summary>

```text
Mac の ブラウザ（React の <img src="/media/thumbs/1.jpg">）
        │  localhost:5173（窓口）
        ▼
web の箱（Vite）  vite.config.js の proxy
  ③ /media で始まる頼みを、api:8000 へ中継する
       なぜ: ブラウザは Mac にいて、Docker の道の中の api という名前を知らない から
       保存しただけで効かないのは: vite.config.js はイメージを作るときに写し取ったもので、watch も src しか同期しない から
        │  道 front
        ▼
api の箱（Django）
  ① /media/... の頼みに、倉庫 media のファイルを返す（settings.py の MEDIA_URL と urls.py の static()）
       なぜ: 倉庫のファイルは箱の中のフォルダで、ブラウザは URL でしか取りに来られないから
  ② 商品一覧に thumbnail_url を入れる（alias で thumbnail 列から取る）
```

「なぜ」は、言い方がちがっても、意味が合っていれば正解です。埋められなかった所があれば、そのチャンクの 📖 しくみ だけ読み返します。最後に、動く図のページの「6g」と見比べます。

</details>

### 📝 ひとこと

「〜だと思っていたけど、実は〜」を1行書きます。書いたものは `docs/notes.md` に貯めます。うまく書けなければ、書かずに先へ進んでも大丈夫です。

例: 「React のコードは web の箱の中で動いていると思っていたけど、実は Mac のブラウザの中で動いていた」

### ✅ できるようになったこと

- [ ] React の `<img src>` に `http://api:8000/...` が使えない理由を、「ブラウザはどこで動くか」で説明できる
- [ ] `vite.config.js` を変えたとき、保存・restart・`up -d --build` のどれが要るかを、打つ前に言える
- [ ] 画像が出ないとき、API・api の箱・web の箱の順に `curl` でたずねて、どこで止まっているかを見つけられる

**残った問い**: これで、画像を送ってから画面に出るまでが全部つながった。でも、worker がサムネイルを作っている**途中で** `docker compose stop` や作り直しをしたら、その仕事はどうなるのか？ 途中で切られたら、サムネイルは中途半端なまま残らないか？

---
▶ **次**: P4-6h worker を止めるとき、仕事が終わるまで待たせる（まだ作っていません。P4-6g が終わったら作ります）

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

| 操作    | メソッドとパス       |
| ------- | -------------------- |
| 一覧    | `GET /todos`         |
| 作成    | `POST /todos`        |
| 1件取得 | `GET /todos/{id}`    |
| 更新    | `PUT /todos/{id}`    |
| 削除    | `DELETE /todos/{id}` |

- データは MySQL に保存する
- API と MySQL を、`compose.yaml` 1つで起動する
- API は、この Mac の **3000 番**で受け付ける
- コンテナを止めて起動し直しても、Todo が残る
- 任意: コードを変えると、API が自動で再起動する
- 置き場所は `projects/multi-container-service/`

🔄 **素材からの変更**: Node.js + Express → Django + Django Ninja / MongoDB + Mongoose → MySQL + Django の ORM / nodemon → `runserver` の自動再読み込み / `docker-compose.yml` → `compose.yaml`。出典の Part 2（Terraform と Ansible）は扱いません。Part 3（CI/CD）とボーナス（Nginx）は P6〜P7 で扱います（`docs/00-plan.md` §6）。

### 2. このフェーズで学んだどれを使うか

| 使う                                          | ステップ      |
| --------------------------------------------- | ------------- |
| `Dockerfile`（`apt-get` を含む）              | P2 全体、P3-4 |
| `ENTRYPOINT` と `exec "$@"`                   | P2-5          |
| `services:` `ports:`                          | P4-1          |
| `volumes:`（名前付き）                        | P4-2          |
| `healthcheck` と `condition: service_healthy` | P4-3          |
| `build:` と `docker compose exec`             | P4-4          |
| `env_file:` と `docker compose config`        | P4-5          |
| bind mount（任意課題）                        | P3-2          |

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
