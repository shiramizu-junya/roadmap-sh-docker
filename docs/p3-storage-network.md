# P3: データとネットワーク：API を MySQL につなぐ

このフェーズの問いは1つです。**「消える箱の外に、データとつながりをどう持つのか」**

全4ステップと、フェーズ末パックです。P2 で作った API を MySQL につなぎ、商品一覧を返します。

> 検証環境: Docker Desktop / Docker Engine 29.8.0 / macOS 26.6.2（Apple シリコン）
> 使うイメージ: `mysql:8.4`（8.4.13）/ `python:3.13-slim` / `alpine` / P2 で作った `ec-api:step5`
> 作業場所: リポジトリの `apps/api/`。特に断りがなければ、コマンドはすべてここで実行します。
> 使う名前: コンテナ `ec-db` `ec-api` / volume `ec-db-data` / ネットワーク `ec-net`

---

## P3-1: volume でデータを残す

**❓ この回の問い**: P1-5 の答えは「書き込み層は `rm` で消える」だった。P2 の最後に「DB はどうするのか」という問いが残った。
→ **コンテナを消しても残る場所は、どこに作るのか？**

**作るもの / 確かめること**: MySQL のコンテナを消して作り直しても、データが残ることを確かめる
**重要度**: 🔴 毎日使う — DB をコンテナで動かすなら、必ず volume を使うから
**前ステップとの接続**: P1-5 の書き込み層の代わりに、volume へ書かせる

### 1-0. このステップの初出トークン

**Docker**: `docker volume` `-v` `マウント`
**補助**: `-e`
**Linux**: `/var/lib/mysql`
**その他**: なし

### 1-1. 実践

まず volume を作ります。

```bash
docker volume create ec-db-data
docker volume ls --filter name=ec-db-data
```

```text
ec-db-data
DRIVER    VOLUME NAME
local     ec-db-data
```

MySQL を起動します。`-e` は環境変数を渡す指定です。詳しくは P3-4 で解剖します。

```bash
docker run -d --name ec-db \
  -v ec-db-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=root-pass \
  -e MYSQL_DATABASE=ec \
  -e MYSQL_USER=ec \
  -e MYSQL_PASSWORD=ec-pass \
  mysql:8.4
```

起動の完了を待ちます。初回は初期化があるので、数秒かかります。

```bash
until docker logs ec-db 2>&1 | grep -q 'port: 3306'; do sleep 1; done; echo ready
```

```text
ready
```

> 🐧 **Linux注**: `until A; do B; done` は、A が成功するまで B を繰り返します。`\` は、長いコマンドを次の行へ続ける印です。

表を作り、1行入れます。

```bash
docker exec ec-db mysql -uec -pec-pass ec -e "CREATE TABLE memo (body VARCHAR(50)); INSERT INTO memo VALUES ('keep-me');"
docker exec ec-db mysql -uec -pec-pass ec -e "SELECT * FROM memo;"
```

```text
mysql: [Warning] Using a password on the command line interface can be insecure.
body
keep-me
```

1行目は「パスワードをコマンドに書くのは安全ではない」という警告です。動作には影響しません。

**🔮 予測**: コンテナを消して、同じ volume で作り直すと、`keep-me` は残るでしょうか。

```bash
docker rm -f ec-db
docker run -d --name ec-db \
  -v ec-db-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=root-pass \
  -e MYSQL_DATABASE=ec \
  -e MYSQL_USER=ec \
  -e MYSQL_PASSWORD=ec-pass \
  mysql:8.4
until docker logs ec-db 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker exec ec-db mysql -uec -pec-pass ec -e "SELECT * FROM memo;"
```

```text
body
keep-me
```

✅ 検証済み: Docker Engine 29.8.0 / MySQL 8.4.13。警告の行は省略した。

**残りました。** 2回目の起動は約2秒でした。初期化が済んだデータを使うからです。

### 1-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `docker volume create` | volume の作成 | Docker が管理する保存場所を、ホスト（Linux VM）に作る |
| `-v ec-db-data:/var/lib/mysql` | volume のマウント | **ランタイム**に、volume をコンテナの `/var/lib/mysql` に接続する |
| `マウント` | mount | ある保存場所を、ディレクトリツリーの1か所につなぐこと |

> 🧒 **かみくだくと**: volume = 建物の外にある貸し倉庫。部屋（コンテナ）を引き払っても、倉庫の中身は残ります。マウント = 部屋の中の扉を、倉庫につなぐ工事です。

```text
コンテナ ec-db の / （overlay）
├── /etc、/usr …   書き込み層。rm で消える
└── /var/lib/mysql ─────┐ マウント
                        ▼
              volume ec-db-data
              ホスト（Linux VM）の
              /var/lib/docker/volumes/ec-db-data/_data
```

**見てほしいところ**: `/var/lib/mysql` だけは、書き込み層ではなく volume に書かれます。P1-5 の overlay を通りません。

ホスト側の場所と、つなぎ方を見ます。

```bash
docker volume inspect ec-db-data --format '{{.Driver}} {{.Mountpoint}}'
docker exec ec-db sh -c 'grep " /var/lib/mysql " /proc/mounts'
```

```text
local /var/lib/docker/volumes/ec-db-data/_data
/dev/vda1 /var/lib/mysql ext4 rw,relatime,discard 0 0
```

✅ 検証済み: Docker Engine 29.8.0 / Docker Desktop

`/` は `overlay` でしたが、`/var/lib/mysql` は `ext4` です。**別の保存場所が、そこだけつながっています。** パスはホストである Linux VM の中のもので、この Mac の Finder では見えません。

なぜを下っていきます。

```text
なぜ、rm してもデータが残るのか
  → データが書き込み層ではなく volume にあるから
      → なぜ、volume はコンテナと一緒に消えないのか
          → コンテナとは別に、Docker が管理しているから
              → なぜ、コンテナの中から見えるのか
                  → MNT namespace の中の1か所に、マウントでつないでいるから（P1-4）
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | 対応物なし。アプリのプロセスが終わってもファイルは残るのが普通だが、コンテナは中のファイルごと捨てるので、残す場所を外に指定する必要がある |
| **なぜこの設計か** | コンテナは作り直す前提なので、残すデータの置き場所を分ける |
| **ビルド時かランタイム時か** | ランタイム。`docker run` のたびに `-v` で指定する |
| **ホストからの見え方** | `docker volume ls` と `docker volume inspect` |
| **失敗時の挙動** | 使用中の volume は消せない。下のエラーになる |

```bash
docker volume rm ec-db-data
```

```text
Error response from daemon: remove ec-db-data: volume is in use - [902a967b8325...]
```

✅ 検証済み: Docker Engine 29.8.0。ID は省略した。

#### `-v` を書き忘れたら

`mysql:8.4` のイメージには、「`/var/lib/mysql` は volume にする」という指定が入っています。

```bash
docker image inspect mysql:8.4 --format '{{json .Config.Volumes}}'
```

```text
{"/var/lib/mysql":{}}
```

✅ 検証済み: Docker Engine 29.8.0

だから `-v` を書き忘れても、Docker が**名前の無い volume** を自動で作ります。名前が長い英数字なので、次に作り直したコンテナはそれを使えません。`docker rm -f` では、この volume は消えずに残ります。

✅ 検証済み: Docker Engine 29.8.0。`-v` なしで起動して `docker rm -f` すると、`docker volume ls` が1つ増えたままになることを確認した。`--rm` 付きで起動した場合は、止めると一緒に消えた。

### 1-3. 🐧 Linux注

> 🐧 **Linux注**: `/var/lib/mysql` は、MySQL がデータを置くディレクトリです。`/var` は、動作中に増える可変のデータを置く場所です。

### 1-4. 解説 — なぜこうするか

volume に名前を付けるのは、作り直したコンテナに同じ倉庫をつなぐためです。名前が無いと、どの倉庫が自分のデータか分かりません。

`docker volume ls` に長い英数字の名前が並んでいたら、名前の無い volume です。消すと中のデータは戻りません。中身を確かめてから消します。

🧠 **Docker の考え方**: コンテナは使い捨て、volume は残すもの。寿命の違うものを分けて持つ。

### 1-5. 🏢 実務メモ

> 🏢 **実務メモ**: DB のデータのように残す必要があり、書き込みの多いデータには volume を使います。volume はコンテナと別に管理され、コンテナを消しても残ります。
> 根拠: https://docs.docker.com/engine/storage/volumes/

### 1-6. 🔮 予測 → 動作確認

**問い**: `-v` を付けずに MySQL を作り直したら、`memo` 表は見えるでしょうか。

```bash
docker run -d --name ec-db-tmp -e MYSQL_ROOT_PASSWORD=root-pass -e MYSQL_DATABASE=ec mysql:8.4
until docker logs ec-db-tmp 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker exec ec-db-tmp mysql -uroot -proot-pass ec -e "SELECT * FROM memo;" 2>&1 | tail -1
docker rm -f -v ec-db-tmp
```

```text
ERROR 1146 (42S02) at line 1: Table 'ec.memo' doesn't exist
```

✅ 検証済み: Docker Engine 29.8.0

見えません。新しい名前の無い volume で、空の DB が作られたからです。`docker rm -v` の `-v` は、名前の無い volume も一緒に消す指定です。

### 1-7. ✅ 想起チェック

1. `-v ec-db-data:/var/lib/mysql` の左と右は、それぞれ何ですか
2. コンテナを消しても DB のデータが残るのは、なぜですか
3. `docker volume ls` に長い英数字の名前があります。これは何ですか

<details><summary>答え</summary>

1. 左が volume の名前、右がコンテナの中のマウント先
2. データが書き込み層ではなく、コンテナと別に管理される volume にあるから
3. 名前の無い volume。`-v` を書き忘れたときなどに自動で作られる

</details>

### 1-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `docker volume` | 1-1 で実践、1-2 で解剖 |
| `-v` | 1-2 で解剖 |
| `マウント` | 1-2 で解剖 |
| `-e` | 1-1 で実践。⏭️ P3-4 で回収 |
| `/var/lib/mysql` | 1-3 で解説 |

### 📇 まとめカード

> **残すデータは volume へ。コンテナを消しても、名前の付いた倉庫は残る。**

**残った問い**: volume は Docker が管理する場所だった。この Mac のフォルダを、そのままつなぐことはできないのか。

---
▶ **次**: P3-2 bind mount で開発する

---

## P3-2: bind mount で開発する

**❓ この回の問い**: 前回の答えは「volume をマウントすると、データが残る」だった。P2-2 では、コードを1行変えるたびにビルドが要った。
→ **この Mac のフォルダを直接つなげば、ビルドせずに済むのか。そのとき、ファイルの持ち主は誰になるのか？**

**作るもの / 確かめること**: コードの変更がすぐ反映されることと、ファイルの所有者を確かめる
**重要度**: 🔴 毎日使う — 開発中の同期と、所有者の問題の両方で毎回使うから
**前ステップとの接続**: P3-1 の volume の代わりに、この Mac の `src/` をつなぐ

### 2-0. このステップの初出トークン

**Docker**: `--mount type=bind` `--user` `UID/GID`
**Linux**: パーミッション
**その他**: なし

### 2-1. 実践

P2 で作った `ec-api:step5` を、`src/` をつないで起動します。

**実行場所**: `apps/api/`

```bash
docker run -d --name ec-api -p 8000:8000 \
  --mount type=bind,src="$(pwd)/src",dst=/app/src \
  ec-api:step5
sleep 3
curl -s localhost:8000/api/health
```

```text
{"status": "ok"}
```

**🔮 予測**: この Mac で `src/config/api.py` を書き換えると、ビルドせずに応答は変わるでしょうか。

`{"status": "ok"}` を `{"status": "ok", "mode": "bind"}` に変えて保存し、数秒待ちます。

```bash
curl -s localhost:8000/api/health
docker logs ec-api 2>&1 | grep -E 'changed|Watching' | tail -2
```

```text
{"status": "ok", "mode": "bind"}
/app/src/config/api.py changed, reloading.
Watching for file changes with StatReloader
```

✅ 検証済み: Docker Engine 29.8.0 / Docker Desktop

**ビルドせずに変わりました。** `runserver` がファイルの変更に気づき、自分で読み込み直しています。確かめたら `, "mode": "bind"` を消して戻します。

次に、所有者を見ます。コンテナの中で作ったファイルは、この Mac では誰のものになるでしょうか。

```bash
docker exec ec-api sh -c 'id; touch /app/src/from-container.txt'
ls -ln src/from-container.txt
id -u
```

```text
uid=0(root) gid=0(root) groups=0(root)
-rw-r--r--  1 501  0  0 11月  5 08:30 src/from-container.txt
501
```

✅ 検証済み: Docker Engine 29.8.0 / Docker Desktop。`501` は検証環境の Mac のユーザ番号で、あなたの環境では違うことがある。

コンテナの中は root（UID 0）です。でも、この Mac では**自分（501）のファイル**になっています。

```bash
rm src/from-container.txt
docker rm -f ec-api
```

#### 本来の Linux では所有者がそのまま残る

Docker Desktop は、この Mac とのあいだで所有者を読み替えています。**本来の Linux では読み替えません。** volume を使うと、本来の動きを確かめられます。

```bash
docker volume create perm-test
docker run --rm -v perm-test:/data alpine sh -c 'echo root > /data/by-root.txt; ls -ln /data'
docker run --rm --user 1000:1000 -v perm-test:/data alpine sh -c 'id; echo x >> /data/by-root.txt'
```

```text
-rw-r--r--    1 0        0                5 Nov  4 23:30 by-root.txt
uid=1000 gid=1000 groups=1000
sh: can't create /data/by-root.txt: Permission denied
```

✅ 検証済み: Docker Engine 29.8.0。`ls -ln` の1行目の `total` は省略した。

root が作ったファイルに、UID 1000 は書き込めません。持ち主を変えると書き込めます。

```bash
docker run --rm -v perm-test:/data alpine chown -R 1000:1000 /data
docker run --rm --user 1000:1000 -v perm-test:/data alpine sh -c 'echo x >> /data/by-root.txt && echo 書けた'
docker volume rm perm-test
```

```text
書けた
```

✅ 検証済み: Docker Engine 29.8.0

### 2-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `--mount type=bind` | bind mount | **ランタイム**に、ホストのディレクトリをコンテナの中へ直接つなぐ |
| `src="$(pwd)/src"` | つなぐ元 | 絶対パスで書く。`$(pwd)` は今いる場所の絶対パスに置き換わる |
| `dst=/app/src` | つなぐ先 | コンテナの中のパス。イメージの `/app/src` は隠れて見えなくなる |
| `--user 1000:1000` | 実行ユーザの指定 | コンテナのプロセスを `UID:GID` で動かす |

> 🧒 **かみくだくと**: bind mount = 部屋の中の扉を、この Mac のフォルダに直結する工事。UID/GID = ユーザとグループの番号です。Linux はファイルの持ち主を、名前ではなく番号で覚えています（P1-4）。

```text
この Mac の apps/api/src/
        │ Docker Desktop のファイル共有（virtiofs）
        ▼
ホスト（Linux VM）
        │ bind mount
        ▼
コンテナ ec-api の /app/src
（イメージの /app/src は上から隠れる）
```

**見てほしいところ**: この Mac の場合は、Docker Desktop のファイル共有を通ります。所有者の読み替えは、ここで起きています。

```bash
docker run --rm --mount type=bind,src="$(pwd)/src",dst=/app/src alpine sh -c 'grep " /app/src " /proc/mounts'
```

```text
virtiofs2 /app/src virtiofs rw,nosuid,nodev,relatime,ignore_atime,no_xattr 0 0
```

✅ 検証済み: Docker Engine 29.8.0 / Docker Desktop

| | volume | bind mount |
| --- | --- | --- |
| 置き場所 | Docker が管理する場所 | 自分で指定したホストのディレクトリ |
| 主な用途 | DB などの残すデータ | 開発中のコードの同期 |
| この Mac から | 直接は見えない | Finder やエディタで見える |
| 元が無いとき | 作られる | `--mount` はエラー（下） |

```text
docker: Error response from daemon: invalid mount config for type "bind": bind source path does not exist: /host_mnt/private/tmp/p3v-nope
```

✅ 検証済み: Docker Engine 29.8.0。`-v` で bind mount を書くと、元が無ければ空のディレクトリが作られた。名前を打ち間違えても気づけないので、本教材は `--mount` を使う。

なぜを下っていきます。

```text
なぜ、ビルドせずに変更が届くのか
  → コンテナの /app/src が、この Mac のフォルダそのものだから
      → なぜ、UID 1000 は書き込めなかったのか
          → Linux は持ち主を番号で比べ、0 と 1000 は別人だから
              → なぜ、この Mac では自分のファイルに見えたのか
                  → Docker Desktop が、Mac との間で持ち主を読み替えるから
                      → なぜ、それを知っておくのか
                          → 本番の Linux では読み替えがなく、同じ設定で詰まるから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | Vite の HMR に体験は近い。ただし bind mount はファイルを共有するだけで、読み込み直すのはアプリ側（ここでは `runserver`） |
| **なぜこの設計か** | 開発中だけはイメージを作り直さず、手元の変更を即座に試したいから |
| **ビルド時かランタイム時か** | ランタイム。イメージには入らない |
| **ホストからの見え方** | `docker inspect ec-api --format '{{json .Mounts}}'` に `"Type":"bind"` が出る |
| **失敗時の挙動** | 所有者が合わないと `Permission denied`。元のパスが無いと、上の `bind source path does not exist` |

### 2-3. 🐧 Linux注

> 🐧 **Linux注**: パーミッションは、`ls -l` の `-rw-r--r--` の部分です。持ち主・グループ・その他の順に、読む・書く・実行の可否を示します。
> 🐧 **Linux注**: `ls -ln` の `-n` は、持ち主を名前ではなく番号で表示します。`chown 1000:1000` は持ち主の番号を変えます。

### 2-4. 解説 — なぜこうするか

`--user` を付けると、イメージの中に無いユーザでも動けます。名前は無く、番号だけです。

```bash
docker run --rm --user 501:20 --entrypoint sh ec-api:step5 -c 'id; whoami'
```

```text
uid=501 gid=20(dialout) groups=20(dialout)
whoami: cannot find name for user ID 501
```

✅ 検証済み: Docker Engine 29.8.0

`dialout` は、コンテナの中でたまたま番号 20 に付いていた名前です。**番号が同じなら同じ人、という扱いです。** 名前は表示のための読み替えです。root で動かさない設定は P6-2 で行います。

🧠 **Docker の考え方**: 持ち主は番号で決まる。名前は飾り。

### 2-5. ⚠️ アンチパターン

> ⚠️ **アンチパターン**: 開発用の bind mount を本番でも使うと、ホストのファイルの状態に依存します。本番では、コードをイメージに入れて配ります。
> 根拠: https://docs.docker.com/engine/storage/bind-mounts/

### 2-6. 🔮 予測 → 動作確認

**問い**: 読み取り専用で bind mount すると、コンテナの中から書き込めるでしょうか。

```bash
docker run --rm --mount type=bind,src="$(pwd)/src",dst=/app/src,readonly alpine touch /app/src/x
```

```text
touch: /app/src/x: Read-only file system
```

✅ 検証済み: Docker Engine 29.8.0

書き込めません。`readonly` を付けると、コンテナが手元のファイルを壊さなくなります。

### 2-7. ✅ 想起チェック

1. volume と bind mount の違いを、置き場所で説明できますか
2. bind mount すると、イメージの中の同じパスのファイルはどうなりますか
3. UID 0 が作ったファイルに UID 1000 が書けないのは、なぜですか

<details><summary>答え</summary>

1. volume は Docker が管理する場所。bind mount は自分で指定したホストのディレクトリ
2. 上から隠れて見えなくなる。消えてはいない
3. Linux は持ち主を番号で比べ、パーミッションが持ち主以外の書き込みを許していないから

</details>

### 2-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `--mount type=bind` | 2-1 で実践、2-2 で解剖 |
| `--user` | 2-1 で実践、2-4 で解説。⏭️ 非 root の設定は P6-2 で回収 |
| `UID/GID` | 2-2 で解剖。P1-4 の宣言を回収 |
| パーミッション | 2-3 で解説 |

### 📇 まとめカード

> **bind mount は手元のフォルダを直結する。持ち主は番号で比べられる。**

**残った問い**: データはつなげた。では、API のコンテナから DB のコンテナへは、どうつなぐのか。

---
▶ **次**: P3-3 コンテナ同士をつなぐ

---

## P3-3: コンテナ同士をつなぐ

**❓ この回の問い**: 前回までで、データは外に置けた。P1-4 では、コンテナごとにネットワークが分かれていた。
→ **分かれたコンテナ同士は、どうやって相手を見つけるのか？**

**作るもの / 確かめること**: コンテナ名で通信できる条件を確かめる
**重要度**: 🔴 毎日使う — API から DB へつなぐ設定は、必ず書くから
**前ステップとの接続**: P3-1 の `ec-db` に、別のコンテナから話しかける

### 3-0. このステップの初出トークン

**Docker**: `docker network` `--network` `bridge`
**Linux**: IP アドレス / DNS
**その他**: なし

### 3-1. 実践

P3-1 の `ec-db` は、何も指定せずに動いています。別のコンテナから名前で探します。

```bash
docker run --rm python:3.13-slim getent hosts ec-db; echo "終了コード: $?"
```

```text
終了コード: 2
```

**名前が見つかりません。** 次に、番号（IP アドレス）で探します。

```bash
docker inspect ec-db --format '{{.NetworkSettings.Networks.bridge.IPAddress}}'
```

```text
172.17.0.2
```

```bash
docker run --rm python:3.13-slim python -c "import socket; socket.create_connection(('172.17.0.2', 3306), timeout=3); print('つながった')"
```

```text
つながった
```

✅ 検証済み: Docker Engine 29.8.0。IP アドレスは環境で変わる。表示された番号に置き換えて打つ。

番号ならつながります。でも、番号は作り直すたびに変わることがあります。名前で探せるネットワークを作ります。

```bash
docker network create ec-net
docker rm -f ec-db
docker run -d --name ec-db --network ec-net \
  -v ec-db-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=root-pass \
  -e MYSQL_DATABASE=ec \
  -e MYSQL_USER=ec \
  -e MYSQL_PASSWORD=ec-pass \
  mysql:8.4
until docker logs ec-db 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker run --rm --network ec-net python:3.13-slim getent hosts ec-db
```

```text
172.19.0.2      ec-db
```

✅ 検証済み: Docker Engine 29.8.0。番号は環境で変わる。

**同じネットワークにいると、名前で見つかります。** volume が同じなので、P3-1 の `memo` 表も残っています。

### 3-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `docker network create ec-net` | ユーザ定義ネットワーク | 新しい `bridge` ネットワークと、そこだけの名前解決を作る |
| `--network ec-net` | ネットワークへの接続 | **ランタイム**に、コンテナをそのネットワークにつなぐ |
| `bridge` | bridge ドライバ | ホストの中に仮想の配線をつくり、同じ配線のコンテナ同士をつなぐ |

> 🧒 **かみくだくと**: ネットワーク = 建物の中の内線。同じ内線につながった部屋同士は、部屋の名前で呼び出せます。IP アドレス = 内線番号、DNS = 名前から番号を調べる電話帳です。

```text
ホスト（Linux VM）
┌─────────────────────────────────────┐
│ bridge（既定）       ec-net（自作） │
│ 172.17.0.0/16        172.19.0.0/16  │
│ 名前で探せない       名前で探せる   │
│                                     │
│                      ┌───────┐      │
│                      │ ec-db │      │
│                      └───────┘      │
│                      ┌────────┐     │
│                      │ ec-api │     │
│                      └────────┘     │
└─────────────────────────────────────┘
```

**見てほしいところ**: 既定の `bridge` と `ec-net` は、どちらも bridge ドライバです。違いは、名前で探せるかどうかです。`ec-api` は P3-4 でつなぎます。

名前を調べる係の場所を見ます。

```bash
docker run --rm python:3.13-slim grep nameserver /etc/resolv.conf
docker run --rm --network ec-net python:3.13-slim grep nameserver /etc/resolv.conf
docker network inspect ec-net --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{end}}'
```

```text
nameserver 192.168.65.7
nameserver 127.0.0.11
ec-db 172.19.0.2/16
```

✅ 検証済み: Docker Engine 29.8.0 / Docker Desktop

自作のネットワークでは、`127.0.0.11` が電話帳の係です。Docker がコンテナの名前を答えます。

なぜを下っていきます。

```text
なぜ、既定の bridge では名前で探せないのか
  → 名前解決の仕組みが、自作のネットワークにだけ付くから
      → なぜ、自作のネットワークでは探せるのか
          → Docker の DNS（127.0.0.11）が、コンテナ名を答えるから
              → なぜ、名前で探したいのか
                  → IP アドレスは作り直すと変わるが、名前は変わらないから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | `localhost:3306` で DB に接続する感覚とは違う。コンテナの `localhost` は自分自身なので、相手は名前で指す |
| **なぜこの設計か** | 関係するコンテナだけを同じネットワークに入れ、ほかから隔離できる |
| **ビルド時かランタイム時か** | ランタイム |
| **ホストからの見え方** | `docker network ls` と `docker network inspect` |
| **失敗時の挙動** | 名前が見つからないと、アプリは `Unknown server host` などで失敗する（P3-4） |

`ec-api` の中から `localhost:3306` につなぐと、こうなります。

```text
ConnectionRefusedError: [Errno 111] Connection refused
```

✅ 検証済み: Docker Engine 29.8.0

コンテナの `localhost` は自分自身なので、そこに MySQL はいません（P2-3）。

### 3-3. 🐧 Linux注

> 🐧 **Linux注**: `/etc/resolv.conf` は、名前を問い合わせる先を書いたファイルです。`getent hosts 名前` は、その名前の IP アドレスを調べます。

### 3-4. 解説 — なぜこうするか

`ec-db` には `-p` を付けていません。**コンテナ同士の通信に `-p` は要りません。** `-p` は、ホストの外からの入口です。

```bash
docker inspect ec-db --format '{{json .NetworkSettings.Ports}}'
```

```text
{"3306/tcp":null,"33060/tcp":null}
```

✅ 検証済み: Docker Engine 29.8.0

`null` は、ホストに公開していないことを示します。この Mac から DB に直接つなげないので、安全です。

🧠 **Docker の考え方**: コンテナ同士は名前で呼ぶ。外に開けるのは入口だけ。

### 3-5. 🏢 実務メモ

> 🏢 **実務メモ**: 既定の bridge ではなく、ユーザ定義の bridge を使います。コンテナ間で名前による自動の名前解決ができるためです。
> 根拠: https://docs.docker.com/engine/network/drivers/bridge/

### 3-6. 🔮 予測 → 動作確認

**問い**: 使っているコンテナがいる状態で、ネットワークは消せるでしょうか。

```bash
docker network rm ec-net
```

```text
Error response from daemon: error while removing network: network ec-net has active endpoints (name:"ec-db" id:"bd10bbf1aeef")
```

✅ 検証済み: Docker Engine 29.8.0。ID は環境で変わる。

消せません。volume と同じで、使っているものがあると消せません。

### 3-7. ✅ 想起チェック

1. 既定の bridge と、自作のネットワークの違いは何ですか
2. API のコンテナから DB を `localhost` で指すと、なぜつながらないのですか
3. DB のコンテナに `-p` が要らないのはなぜですか

<details><summary>答え</summary>

1. 自作のネットワークだけ、コンテナ名で相手を探せる
2. コンテナの `localhost` は自分自身で、DB は別のコンテナだから
3. `-p` はホストの外からの入口で、コンテナ同士の通信には使わないから

</details>

### 3-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `docker network` | 3-1 で実践、3-2 で解剖 |
| `--network` | 3-2 で解剖 |
| `bridge` | 3-2 で解剖 |
| IP アドレス / DNS | 3-2 で解説 |

### 📇 まとめカード

> **自作のネットワークに入れると、コンテナ名で呼べる。`localhost` は自分自身。**

**残った問い**: 名前で DB に届くようになった。では、API にパスワードや接続先をどう渡すのか。

---
▶ **次**: P3-4 商品 API を MySQL につなぐ

---

## P3-4: 商品 API を MySQL につなぐ

**❓ この回の問い**: 前回の答えは「同じネットワークなら名前で呼べる」だった。でも、API はまだ DB を知らない。P3-1 では `-e` の説明を後回しにした。
→ **接続先とパスワードは、どうやって API に渡すのか？**

**作るもの / 確かめること**: ビルドの失敗を直し、商品一覧を MySQL から返す
**重要度**: 🔴 毎日使う — 設定を環境変数で渡すのは、コンテナの基本だから
**前ステップとの接続**: P3-3 の `ec-net` に、`ec-api` をつなぐ

### 4-0. このステップの初出トークン

**Docker**: `-e` `--env-file` `apt-get`
**Linux**: 環境変数 / パッケージ
**その他**: マイグレーション、fixture

### 4-1. 実践

#### MySQL のドライバを足す

`apps/api/pyproject.toml` の `dependencies` に1行足します。

**ファイル**: `apps/api/pyproject.toml`（差分）

```diff
 dependencies = [
     "django>=5.2,<5.3",
     "django-ninja>=1.7,<1.8",
+    "mysqlclient>=2.3,<2.4",
 ]
```

P2 の宿題 Lv2 と同じ方法で、`uv.lock` を更新します。

```bash
docker run --rm -i --entrypoint sh ec-api:step5 -c 'cat > pyproject.toml && uv lock -q && cat uv.lock' < pyproject.toml > uv.lock.new
mv uv.lock.new uv.lock
grep -A1 'name = "mysqlclient"$' uv.lock
```

```text
name = "mysqlclient"
version = "2.3.0"
```

ビルドします。

```bash
docker build -t ec-api:step6 .
```

```text
error: Failed to build `mysqlclient==2.3.0`
  cause: The build backend returned an error
         Trying pkg-config --exists mysqlclient
         /bin/sh: 1: pkg-config: not found
         Exception: Can not find valid pkg-config name.
```

✅ 検証済み: Docker Engine 29.8.0 / uv 0.13.6。行を抜き出した。

**箱の中に、部品を組み立てる道具がありません。** `mysqlclient` は C 言語で書かれた部品を含みます。組み立てには `gcc` などが要ります。

**ファイル**: `apps/api/Dockerfile`（全文を置き換え）

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

```bash
docker build -t ec-api:step6 .
docker image ls ec-api --format '{{.Tag}} {{.Size}}'
```

```text
step6 672MB
step5 380MB
（省略）
```

✅ 検証済み: Docker Engine 29.8.0。初回のビルドは約40秒かかった。

**通りました。でも、イメージは 380MB から 672MB に増えました。** この理由と減らし方は P5-4 で扱います。

#### 商品のコードを書く

Django の商品アプリ `catalog` を足します。

| ファイル | 役割 |
| --- | --- |
| `src/catalog/models.py` | 商品の表の定義 |
| `src/catalog/fixtures/products.json` | 最初に入れる商品3件 |
| `src/config/settings.py` | DB の接続先を環境変数から読む |
| `src/config/api.py` | 商品一覧と詳細の API |

```bash
mkdir -p src/catalog/fixtures
touch src/catalog/__init__.py
```

**ファイル**: `apps/api/src/catalog/models.py`（新規・全文）

```python
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
```

**ファイル**: `apps/api/src/catalog/fixtures/products.json`（新規・全文）

```json
[
  {"model": "catalog.product", "pk": 1, "fields": {"name": "木のマグカップ", "price": 2800, "description": "手彫りのマグカップ"}},
  {"model": "catalog.product", "pk": 2, "fields": {"name": "麻のトートバッグ", "price": 3500, "description": "丈夫な麻の生地"}},
  {"model": "catalog.product", "pk": 3, "fields": {"name": "陶器の小皿", "price": 1200, "description": "5枚セット"}}
]
```

**ファイル**: `apps/api/src/config/settings.py`（全文を置き換え）

```python
import os

SECRET_KEY = "dev-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = ["catalog"]
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

**ファイル**: `apps/api/src/config/api.py`（全文を置き換え）

```python
from django.shortcuts import get_object_or_404
from ninja import ModelSchema, NinjaAPI

from catalog.models import Product

api = NinjaAPI()


class ProductOut(ModelSchema):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "description"]


@api.get("/health")
def health(request):
    return {"status": "ok"}


@api.get("/products", response=list[ProductOut])
def list_products(request):
    return Product.objects.order_by("id")


@api.get("/products/{product_id}", response=ProductOut)
def get_product(request, product_id: int):
    return get_object_or_404(Product, id=product_id)
```

#### 接続先を渡して起動する

P2-2 で作った `.env` を、接続の設定に書き換えます。`.env` は `.dockerignore` で箱に入らないので、起動のときに渡します。

**ファイル**: `apps/api/.env`（全文を置き換え）

```text
DB_HOST=ec-db
DB_NAME=ec
DB_USER=ec
DB_PASSWORD=ec-pass
```

```bash
docker build -t ec-api:step6 .
docker run -d --name ec-api --network ec-net -p 8000:8000 \
  --env-file .env \
  --mount type=bind,src="$(pwd)/src",dst=/app/src \
  ec-api:step6
sleep 4
```

表を作り、商品を入れます。

```bash
docker exec ec-api .venv/bin/python src/manage.py makemigrations catalog
docker exec ec-api .venv/bin/python src/manage.py migrate
docker exec ec-api .venv/bin/python src/manage.py loaddata products
```

```text
Migrations for 'catalog':
  src/catalog/migrations/0001_initial.py
    + Create model Product
Operations to perform:
  Apply all migrations: catalog
Running migrations:
  Applying catalog.0001_initial... OK
Installed 3 object(s) from 1 fixture(s)
```

> 🧒 **かみくだくと**: マイグレーション = 表の設計図を DB に反映する手順書。fixture = 最初に入れておくデータのファイルです。

`makemigrations` が作った `0001_initial.py` は、bind mount を通って**この Mac の `src/catalog/migrations/` に残ります。** リポジトリに入れるファイルです。

```bash
curl -s localhost:8000/api/products/2
curl -s localhost:8000/api/products | grep -o '"id"' | wc -l
```

```text
{"id": 2, "name": "麻のトートバッグ", "price": 3500, "description": "丈夫な麻の生地"}
3
```

✅ 検証済み: Docker Engine 29.8.0 / Django 5.2.18 / mysqlclient 2.3.0 / MySQL 8.4.13

`麻` は日本語の文字を番号で書いたものです。ブラウザで http://localhost:8000/api/products/2 を開くと読めます。DB の中も確かめます。

```bash
docker exec ec-db mysql --default-character-set=utf8mb4 -uec -pec-pass ec -e "SELECT id, name FROM catalog_product;"
```

```text
id	name
1	木のマグカップ
2	麻のトートバッグ
3	陶器の小皿
```

✅ 検証済み: MySQL 8.4.13。警告の行は省略した。`--default-character-set=utf8mb4` が無いと、表示だけ `???` になる。

### 4-2. 🔬 仕組み解剖

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `-e 名前=値` | 環境変数の設定 | **ランタイム**に、コンテナのプロセスへ環境変数を1つ渡す。P3-1 の宣言をここで回収する |
| `--env-file .env` | 環境変数ファイル | **ランタイム**に、ファイルの `名前=値` を1行ずつ環境変数として渡す |
| `apt-get install` | Debian のパッケージ管理 | **ビルド時**に、OS の上半分の部品を足す |
| `rm -rf /var/lib/apt/lists/*` | 一覧の削除 | `apt-get update` が取った部品の一覧を、**同じ `RUN` の中で**消す |

> 🧒 **かみくだくと**: 環境変数 = プロセスに貼る付箋。プログラムは起動したあとに付箋を読み、設定を知ります。パッケージ = OS に足す部品の箱。`apt-get` は Debian の部品の取り寄せ係です。

設定がどこから来るのかを並べます。

```text
.env（この Mac）
   │ --env-file .env（docker run のとき）
   ▼
コンテナ ec-api の環境変数
   │ os.environ["DB_HOST"]（起動したあと）
   ▼
Django の DATABASES
   │ ec-db（P3-3 の名前解決）
   ▼
コンテナ ec-db の 3306 番
```

**見てほしいところ**: イメージには `ec-db` もパスワードも入っていません。同じイメージに別の付箋を貼れば、別の DB につながります。

```bash
docker exec ec-api env | grep ^DB_
```

```text
DB_HOST=ec-db
DB_NAME=ec
DB_USER=ec
DB_PASSWORD=ec-pass
```

✅ 検証済み: Docker Engine 29.8.0

なぜを下っていきます。

```text
なぜ、設定をイメージに入れず環境変数で渡すのか
  → 同じイメージを、開発でも本番でも使いたいから
      → なぜ、同じイメージを使いたいのか
          → 確かめた箱と違う箱を本番に出すと、確かめた意味がなくなるから
              → なぜ、apt-get の一覧は同じ RUN の中で消すのか
                  → 別の RUN で消しても、前の層に残るから（P2-3）
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | `process.env` や `os.environ` と同じ仕組み。`.env` を読むのはアプリではなく Docker である点が違う |
| **なぜこの設計か** | 設定を箱の外に出すと、箱を作り直さずに設定だけを変えられる |
| **ビルド時かランタイム時か** | `-e` と `--env-file` はランタイム。`apt-get` はビルド時 |
| **ホストからの見え方** | `docker exec ... env` と `docker inspect` に出る |
| **失敗時の挙動** | 下の表 |

| 間違い | 出るエラー |
| --- | --- |
| `--env-file` を付け忘れた | `KeyError: 'DB_HOST'` |
| `--network ec-net` を付け忘れた | `OperationalError: (2005, "Unknown server host 'ec-db' (-2)")` |
| `.env` で `DB_PASSWORD="ec-pass"` と書いた | `OperationalError: (1045, "Access denied for user 'ec'@'...' (using password: YES)")` |

✅ 検証済み: Docker Engine 29.8.0。3つとも実際に起こした。

3つ目は気づきにくい間違いです。`--env-file` は引用符を外さず、`"ec-pass"` という引用符付きの文字列を渡します。

### 4-3. 🐧 Linux注

> 🐧 **Linux注**: `apt-get update` は部品の一覧を取り直し、`apt-get install -y` は確認なしで部品を入れます。`--no-install-recommends` は、おすすめの追加部品を入れない指定です。

### 4-4. 解説 — なぜこうするか

**MySQL の `MYSQL_USER` などは、volume が空のときにだけ使われます。** 初期化が済んだ volume に別のユーザ名を渡しても、ユーザは作られません。

✅ 検証済み: MySQL 8.4.13。初期化済みの `ec-db-data` に `MYSQL_USER=ec2` で起動すると、`ec2` は作られず、ログインは `Access denied` になった。
根拠: https://hub.docker.com/_/mysql

DB が止まると、API は 500 を返します。DB を起動し直すと、API を作り直さなくても戻ります。

✅ 検証済み: Docker Engine 29.8.0。`docker stop ec-db` で 500 になり、`docker start ec-db` で 200 に戻ることを確認した。

🧠 **Docker の考え方**: イメージは同じ、設定は外から。だから同じ箱を、どこでも動かせる。

### 4-5. 🔓 教材用の簡略化

> 🔓 **教材用の簡略化**: パスワードを `-e` と `.env` で渡しています。`docker inspect` で誰でも読めます。
> **本番では**: P6-3 で secrets を使い、`docker inspect` に出ないようにします。
> 根拠: https://docs.docker.com/compose/how-tos/use-secrets/

```bash
docker inspect ec-db --format '{{range .Config.Env}}{{println .}}{{end}}' | grep PASSWORD
```

```text
MYSQL_ROOT_PASSWORD=root-pass
MYSQL_PASSWORD=ec-pass
```

✅ 検証済み: Docker Engine 29.8.0

### 4-6. 🔮 予測 → 動作確認

**問い**: `ec-db` と `ec-api` を両方消して作り直すと、商品は何件になるでしょうか。

```bash
docker rm -f ec-api ec-db
docker run -d --name ec-db --network ec-net \
  -v ec-db-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=root-pass \
  -e MYSQL_DATABASE=ec \
  -e MYSQL_USER=ec \
  -e MYSQL_PASSWORD=ec-pass \
  mysql:8.4
until docker logs ec-db 2>&1 | grep -q 'port: 3306'; do sleep 1; done
docker run -d --name ec-api --network ec-net -p 8000:8000 \
  --env-file .env \
  --mount type=bind,src="$(pwd)/src",dst=/app/src \
  ec-api:step6
sleep 4
curl -s localhost:8000/api/products | grep -o '"id"' | wc -l
```

```text
3
```

✅ 検証済み: Docker Engine 29.8.0

3件のままです。データは volume、コードは bind mount、設定は `.env` にあります。どれもコンテナの外です。

### 4-7. ✅ 想起チェック

1. `-e` と `--env-file` は、ビルド時とランタイムのどちらで働きますか
2. `apt-get` の一覧を消すのは、なぜ同じ `RUN` の中なのですか
3. `KeyError: 'DB_HOST'` が出ました。何を疑いますか

<details><summary>答え</summary>

1. ランタイム
2. 別の `RUN` で消しても、前の層に残ってサイズが減らないから
3. `--env-file .env` の付け忘れ

</details>

### 4-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `-e` | 4-2 で解剖。P3-1 の宣言を回収 |
| `--env-file` | 4-1 で実践、4-2 で解剖 |
| `apt-get` | 4-1 で実践、4-2 で解剖 |
| 環境変数 / パッケージ | 4-2 で解説 |
| マイグレーション、fixture | 4-1 で解説 |

### 📇 まとめカード

> **設定は環境変数で外から渡す。データは volume、つながりはネットワーク。**

**残った問い**: 動いた。でも `docker run` の行がとても長い。毎回これを打つのか。

---

## P3 のなぜなぜの鎖

```text
消える箱の外に、データをどう残すのか
  → volume をマウントする
      ↓ 手元のフォルダを直接つなげないのか
  → bind mount でつなげる。持ち主は番号で比べられる
      ↓ コンテナ同士はどうつなぐのか
  → 自作のネットワークに入れて、名前で呼ぶ
      ↓ 接続先とパスワードはどう渡すのか
  → 環境変数で外から渡す
      ↓ では、この長いコマンドの束をどうまとめるのか
```

---

## P3 フェーズ末パック（M2）

### ブランクページ再現

> ✍️ **ブランクページ**: 教材を閉じて、次の3つを白紙から書いてください。
> 思い出せなかった箇所に印を付け、**その箇所の仕組み解剖だけ**読み返します。

1. `ec-net` と `ec-db-data` を作り、`ec-db` を起動するコマンド
2. `.env` と bind mount を使って、`ec-api` を起動するコマンド
3. `apps/api/Dockerfile` の `apt-get` の1行

**翌日に行うことをすすめます。** 直後は短期記憶で再現できてしまい、定着の負荷が足りません。

### 宿題

#### Lv1 基礎確認: 4件目の商品を残す

**課題**

- `ec-db` に4件目の商品を直接入れる。名前は `Notebook`、価格は `900`
- `ec-db` と `ec-api` を消して作り直す

**ヒント**: 表の名前は `catalog_product` です。作り直しのコマンドは 4-6 と同じです。

**判定基準**: 作り直したあと、`curl -s localhost:8000/api/products | grep -o '"id"' | wc -l` が `4` を返す。

<details><summary>解答例</summary>

```bash
docker exec ec-db mysql -uec -pec-pass ec -e "INSERT INTO catalog_product (name, price, description) VALUES ('Notebook', 900, '');"
docker rm -f ec-api ec-db
# 4-6 の docker run を2つ実行する
curl -s localhost:8000/api/products | grep -o '"id"' | wc -l
```

✅ 検証済み: Docker Engine 29.8.0

</details>

#### Lv2 応用: バックアップから戻す

**課題**

- `mysqldump` で DB の中身を、この Mac の `backup.sql` に書き出す
- `ec-db` と `ec-db-data` を消し、空の volume で作り直す
- `backup.sql` から戻し、商品が元の件数に戻ることを確かめる

**ヒント**: 書き出しは標準出力、戻しは標準入力を使います。P2 の宿題 Lv2 の `docker run -i` と同じで、`docker exec -i` も標準入力を渡せます。

**判定基準**: 作り直した直後は `curl` が 500 を返す。戻したあとは、商品の件数が消す前と同じになる。

<details><summary>解答例</summary>

```bash
docker exec ec-db mysqldump -uec -pec-pass --no-tablespaces ec > backup.sql
docker rm -f ec-db
docker volume rm ec-db-data
docker run -d --name ec-db --network ec-net \
  -v ec-db-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=root-pass \
  -e MYSQL_DATABASE=ec \
  -e MYSQL_USER=ec \
  -e MYSQL_PASSWORD=ec-pass \
  mysql:8.4
until docker logs ec-db 2>&1 | grep -q 'port: 3306'; do sleep 1; done
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/products
docker exec -i ec-db mysql -uec -pec-pass ec < backup.sql
curl -s localhost:8000/api/products | grep -o '"id"' | wc -l
rm backup.sql
```

`docker volume rm` は、新しい volume も同じ名前で自動に作られるので、作り直しの `docker run` で空の DB になります。`--no-tablespaces` は、`ec` ユーザに無い権限を求めないための指定です。

✅ 検証済み: Docker Engine 29.8.0 / MySQL 8.4.13

</details>

#### Lv3 発展: volume と bind mount を比べる

**課題**

- `alpine` で、volume `lv3-vol` と bind mount `$(pwd)/lv3-bind` の両方をつないだコンテナを使う
- root と `--user 1000:1000` のそれぞれで、両方にファイルを書く
- 次の3点を、コマンドの出力を根拠に表にする: 書けたか / コンテナの中で見た持ち主の番号 / コンテナを消したあとと volume を消したあとに残るか

**ヒント**: 書けたかどうかは `echo ... && echo OK` で分かります。この Mac 側は `ls -ln lv3-bind` で見ます。

**判定基準**: volume は UID 1000 で書けず、bind mount は書ける。コンテナを消しても両方残る。`docker volume rm` で volume だけ消え、`lv3-bind` はこの Mac に残る。

<details><summary>解答例</summary>

```bash
mkdir -p lv3-bind
docker volume create lv3-vol

docker run --rm -v lv3-vol:/vol --mount type=bind,src="$(pwd)/lv3-bind",dst=/bind alpine \
  sh -c 'echo a > /vol/root.txt && echo vol-root OK; echo a > /bind/root.txt && echo bind-root OK'
docker run --rm --user 1000:1000 -v lv3-vol:/vol --mount type=bind,src="$(pwd)/lv3-bind",dst=/bind alpine \
  sh -c 'echo b > /vol/u.txt && echo vol-1000 OK; echo b > /bind/u.txt && echo bind-1000 OK'
docker run --rm -v lv3-vol:/vol --mount type=bind,src="$(pwd)/lv3-bind",dst=/bind alpine ls -ln /vol /bind
ls -ln lv3-bind
```

```text
vol-root OK
bind-root OK
sh: can't create /vol/u.txt: Permission denied
bind-1000 OK
```

```bash
docker volume rm lv3-vol
docker volume ls --filter name=lv3-vol
ls lv3-bind
rm -r lv3-bind
```

| 項目 | volume | bind mount（Docker Desktop） |
| --- | --- | --- |
| root で書けたか | 書けた | 書けた |
| UID 1000 で書けたか | `Permission denied` | 書けた |
| コンテナの中の持ち主 | `0` | 見る側の番号（root から見ると `0`） |
| この Mac での持ち主 | 見えない | 自分の番号 |
| コンテナを消したあと | 残る | 残る |
| `docker volume rm` のあと | 消える | 残る |

✅ 検証済み: Docker Engine 29.8.0 / Docker Desktop

**本来の Linux なら**: bind mount も読み替えがなく、volume と同じく UID 1000 は書けません。

</details>

---

## ▶ 次は P4

P3 はここまでです。次のフェーズでは、長い `docker run` を `compose.yaml` にまとめます。

**片付け**（P4 の前に行う）

```bash
docker rm -f ec-api ec-db
docker network rm ec-net
```

`ec-db-data` は残します。P4 では作り直すので、消してもかまいません。

**前提チェック**

- [ ] volume を使う理由を、書き込み層から説明できる（P3-1）
- [ ] volume と bind mount の違いを説明できる（P3-2）
- [ ] UID が合わないと書けない理由を説明できる（P3-2）
- [ ] 自作のネットワークが要る理由を説明できる（P3-3）
- [ ] 設定を環境変数で渡す理由を説明できる（P3-4）
