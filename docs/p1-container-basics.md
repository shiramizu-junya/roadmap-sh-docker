# P1: コンテナ操作 / 隔離の仕組み

このフェーズの問いは1つです。**「コンテナの正体は何か」**

全5ステップと、フェーズ末パックです。EC はまだ作りません。既存の nginx イメージで、コンテナそのものを観察します。

> 検証環境: Docker Desktop / Docker Engine 29.8.0 / macOS 26.6.2（Apple シリコン）
> 使うイメージ: `nginx:1.30-alpine`
> このフェーズでは、ポート `8080` を使います。使用中なら `8081:80` のように左の数字を変えてください。

---

## P1-1: 既存イメージを動かす

**❓ この回の問い**: P0 の答えは「`docker run` すると runc がコンテナを作る」だった。hello-world はすぐに終わった。
→ **Web サーバのように動き続けるものは、どう動かし、どう外からつなぐのか？**

**作るもの / 確かめること**: nginx を起動して、ブラウザで見る
**重要度**: 🔴 毎日使う — コンテナの起動と確認は、Docker を使うたびに必ず行うから
**前ステップとの接続**: P0-3 の `docker run` に `-d` と `-p` を足す

### 1-0. このステップの初出トークン

**Docker**: `-d` `-p` `docker ps`
**補助**: `--name` `docker stop`
**Linux**: なし
**その他**: ポート

### 1-1. 実践

**実行場所**: どこでもよい（ターミナル）

```bash
docker run -d -p 8080:80 --name web nginx:1.30-alpine
```

ブラウザで http://localhost:8080 を開きます。`Welcome to nginx!` と出れば成功です。

動いているコンテナを一覧します。

```bash
docker ps
```

```text
IMAGE               STATUS         PORTS                                     NAMES
nginx:1.30-alpine   Up 5 seconds   0.0.0.0:8080->80/tcp, [::]:8080->80/tcp   web
```

ターミナルからも確かめます。

```bash
curl -sI localhost:8080 | head -2
```

```text
HTTP/1.1 200 OK
Server: nginx/1.30.6
```

止めて、状態を確かめます。

```bash
docker stop web
docker ps
docker ps -a
```

```text
NAMES     STATUS
web       Exited (0) 2 seconds ago
```

`docker ps` は動いているものだけを出すので、`web` は出ません。`-a` は止まったものも出します。上の表は `docker ps -a` の結果から、関係する列だけを選びました。

✅ 検証済み: Docker Engine 29.8.0。表は `--format` で列を絞って取得した。

### 1-2. 🔬 仕組み解剖

#### `docker run -d -p 8080:80 --name web nginx:1.30-alpine`

| 部品 | 正式名称 | 実行時に何が起きるか |
| --- | --- | --- |
| `-d` | detached（切り離し）モード | コンテナを裏で動かし、ターミナルをすぐ返す |
| `-p 8080:80` | ポートの公開（publish） | `ホスト側:コンテナ側` の転送を作る |
| `--name web` | コンテナ名 | 人が読める名前を付ける。無ければ自動で付く |
| `nginx:1.30-alpine` | イメージ名:タグ | `:` の右がタグ。版と種類を選ぶ |

> 🧒 **かみくだくと**: ポート = 建物の部屋番号。同じ住所でも、番号で届け先を分けます。タグ = 箱に貼るラベルです。

通信の道のりはこうなります。

```text
ブラウザ（この Mac）
   │ localhost:8080
   ▼
Docker Desktop の転送
   │
   ▼
ホスト（Linux VM）の 8080
   │ -p 8080:80
   ▼
コンテナの 80 番（nginx）
```

**見てほしいところ**: コンテナの中の nginx は 80 番で待っているだけです。外の 8080 番を知りません。

なぜを下っていきます。

```text
なぜ、-p が無いとつながらないのか
  → コンテナのネットワークは、ホストと分かれているから
      → なぜ、分かれているのか
          → 複数のコンテナが同じ 80 番を使っても、ぶつからないようにするため
              → どう分けているのか
                  → P1-4 で明かす
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | Vite の `server.port` は、アプリ自身が待つ番号を変える。`-p` はアプリを変えず、外との対応だけを作る |
| **なぜこの設計か** | アプリの設定を変えずに、外から見える番号を自由に決められる |
| **ビルド時かランタイム時か** | ランタイム。`docker run` のたびに指定する |
| **ホストからの見え方** | `docker ps` の `PORTS` 列に転送が出る |
| **失敗時の挙動** | 同じ名前のコンテナがあると、下のエラーになる |

止まった `web` を残したまま、もう一度起動するとこうなります。

```text
docker: Error response from daemon: Conflict. The container name "/web" is already in use by container "89c07d3a1ddb...". You have to remove (or rename) that container to be able to reuse that name.
```

✅ 検証済み: Docker Engine 29.8.0。コンテナ ID は省略した。

**`docker stop` のあとのコンテナは消えていません。** 消し方は P1-2 で扱います。ここでは名前を変えるか、次の1行で片付けます。

```bash
docker rm web
```

### 1-3. 🐧 Linux注

このステップに Linux の前提知識はありません。

### 1-4. 解説 — なぜこうするか

`-d` を付けないと、コンテナのログがターミナルに流れ続け、次のコマンドを打てなくなります。

✅ 検証済み: Docker Engine 29.8.0。`-d` なしで起動すると、起動ログが流れ続けることを確認した。

hello-world が終わり、nginx が動き続ける理由は、動いているプログラムの違いです。nginx は要求を待ち続けます。hello-world は文字を出して終わります。

🧠 **Docker の考え方**: コンテナの寿命は、中のメインのプログラムの寿命と同じ。

### 1-5. 🏢 実務メモ

> 🏢 **実務メモ**: `-p 8080:80` は既定で、ホストのすべてのネットワークに公開します。自分のパソコンだけで使うなら、`-p 127.0.0.1:8080:80` と書けます。
> 根拠: https://docs.docker.com/engine/network/port-publishing/

### 1-6. 🔮 予測 → 動作確認

**問い**: nginx を止めたら、ブラウザはどうなるでしょうか。もう一度起動するときに、`-p 8081:80` にしたらどうなるでしょうか。

```bash
docker run -d -p 8081:80 --name web nginx:1.30-alpine
curl -sI localhost:8081 | head -1
curl -s -o /dev/null -m 3 localhost:8080; echo "curl の終了コード: $?"
docker stop web
docker rm web
```

```text
HTTP/1.1 200 OK
curl の終了コード: 7
```

`8081` は応答します。`8080` は接続できません。終了コード `7` は、curl がつなげなかったことを示します。

✅ 検証済み: Docker Engine 29.8.0

### 1-7. ✅ 想起チェック

1. `-p 8080:80` の左と右は、それぞれどこの番号ですか
2. `docker ps` と `docker ps -a` の違いは何ですか
3. コンテナが動き続ける条件は何ですか

<details><summary>答え</summary>

1. 左がホスト側、右がコンテナ側
2. `docker ps` は動いているものだけ。`-a` は止まったものも含む
3. コンテナの中のメインのプログラムが動いていること

</details>

### 1-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `-d` | 1-2 で解剖 |
| `-p` | 1-2 で解剖 |
| `docker ps` | 1-1 で実践 |
| `--name` | 1-2 で解剖 |
| `docker stop` | 1-1 で実践。⏭️ 止まる仕組みは P2-5 で回収 |
| ポート | 1-2 で解説 |

### 📇 まとめカード

> **`-p ホスト:コンテナ` で、隔離された中へ道を通す。**

**残った問い**: `docker stop` のあとも `web` は残っていた。イメージとコンテナは、どう違うのか。

---
▶ **次**: P1-2 イメージとコンテナは別物

---

## P1-2: イメージとコンテナは別物

**❓ この回の問い**: 前回、止めたコンテナが残っていた。同じ名前で作り直すこともできなかった。
→ **イメージとコンテナは、それぞれ何で、どう消すのか？**

**作るもの / 確かめること**: 1つのイメージから2つのコンテナを作る
**重要度**: 🔴 毎日使う — 「イメージを直すのか、コンテナを作り直すのか」の判断に毎回使うから
**前ステップとの接続**: P1-1 の `docker run` を2回行い、結果を比べる

### 2-0. このステップの初出トークン

**Docker**: `docker pull` `docker image ls` `docker rm`
**補助**: `docker image rm` `docker rm -f`
**Linux**: なし
**その他**: Docker Hub

### 2-1. 実践

イメージを取得して、一覧します。

```bash
docker pull nginx:1.30-alpine
docker image ls nginx:1.30-alpine
```

```text
IMAGE               ID             DISK USAGE   CONTENT SIZE   EXTRA
nginx:1.30-alpine   0e52bd054126       93.1MB         26.9MB
```

✅ 検証済み: Docker Engine 29.8.0。ID とサイズは取得した時期で変わる。

| 列 | 意味 |
| --- | --- |
| `DISK USAGE` | 手元のディスクで使っている量 |
| `CONTENT SIZE` | 圧縮された、転送される量 |

同じイメージから2つのコンテナを作ります。

```bash
docker run -d --name web1 nginx:1.30-alpine
docker run -d --name web2 nginx:1.30-alpine
docker ps
```

```text
CONTAINER ID   IMAGE               NAMES
8733abb0b249   nginx:1.30-alpine   web2
23e9aa77804c   nginx:1.30-alpine   web1
```

✅ 検証済み: Docker Engine 29.8.0。表は列を絞って載せた。

**🔮 予測**: `web1` の中にファイルを作ります。`web2` から見えるでしょうか。

```bash
docker exec web1 sh -c 'echo only-web1 > /tmp/x'
docker exec web1 cat /tmp/x
docker exec web2 cat /tmp/x
```

```text
only-web1
cat: can't open '/tmp/x': No such file or directory
```

✅ 検証済み: Docker Engine 29.8.0

**見えません。** 2つのコンテナは同じイメージから作られましたが、書き込む先は別です。`docker exec` は次の P1-3 で解剖します。今は「動いているコンテナの中でコマンドを実行する」とだけ理解します。

消す順番を確かめます。まず、動いている `web1` を消そうとします。

```bash
docker rm web1
```

```text
Error response from daemon: cannot remove container "web1": container is running: stop the container before removing or force remove
```

止めてから消します。

```bash
docker stop web1
docker rm web1
```

次に、コンテナが残っているイメージを消そうとします。

```bash
docker image rm nginx:1.30-alpine
```

```text
Error response from daemon: conflict: unable to delete nginx:1.30-alpine (must be forced) - container 8733abb0b249 is using its referenced image 0e52bd054126
```

✅ 検証済み: Docker Engine 29.8.0

コンテナが**止まっていても**同じエラーになります。残っている限り、そのコンテナはイメージを使っているからです。

`web2` を片付けます。`-f` は動いていても強制的に消します。

```bash
docker rm -f web2
```

### 2-2. 🔬 仕組み解剖

```text
レジストリ（Docker Hub）
   │ docker pull
   ▼
イメージ（読み取り専用）
   │ docker run
   ├──────────────┐
   ▼              ▼
コンテナ web1    コンテナ web2
（書き込み層）   （書き込み層）
```

**見てほしいところ**: イメージは1つで、コンテナごとに書き込み層が付きます。書き込み層の実体は P1-5 で確かめます。

| | イメージ | コンテナ |
| --- | --- | --- |
| 中身 | 動かす前の、読み取り専用の材料 | 材料から起動した実行中のプロセスと書き込み層 |
| たとえ | 封をした段ボール | 箱を開けて生活を始めた部屋 |
| 数 | 1つから何個でも作れる | 作るたびに増える |
| 作るコマンド | `docker pull` / `docker build` | `docker run` |
| 消すコマンド | `docker image rm` | `docker rm` |

> 🧒 **かみくだくと**: Docker Hub = Docker 社が運営するレジストリ。公式のイメージが置かれている、大きな配送センターです。

なぜを下っていきます。

```text
なぜ、イメージを読み取り専用にするのか
  → 同じ箱から、同じ状態を何度でも作るため
      → なぜ、それが大事なのか
          → コンテナが壊れても、消して作り直せば元に戻るから
              → なぜ、イメージは消せなかったのか
                  → 残っているコンテナが材料として使っているから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | クラスとインスタンスの関係に近い。ただし、イメージは実行できるファイルの集まりで、メモリ上の型ではない |
| **なぜこの設計か** | 実行の状態と材料を分けると、同じものを何度でも再現できる |
| **ビルド時かランタイム時か** | イメージはビルドの成果物、コンテナはランタイムの実体 |
| **ホストからの見え方** | イメージは `docker image ls`、コンテナは `docker ps -a` |
| **失敗時の挙動** | 2-1 の2つのエラーが、消す順番の間違いを教えてくれる |

### 2-3. 🐧 Linux注

> 🐧 **Linux注**: `sh -c '...'` は文字列をシェルに渡します。`>` はコマンドの出力をファイルへ書き込みます。`cat` はファイルの中身を表示します。

### 2-4. 解説 — なぜこうするか

**不具合が起きたら、コンテナの中を直すのではなく作り直す。** これが Docker の基本の動きです。中で直しても、次に作り直せば消えるからです。

`docker run` は、手元にイメージが無ければ自動で pull します。`docker pull` を先に打つのは、タグの指す中身を更新したいときなどです。

🧠 **Docker の考え方**: イメージは変えない。変えたいときは作り直す。

### 2-5. 🏢 実務メモ

> 🏢 **実務メモ**: `latest` のようなタグは指す中身が変わることがあります。本教材の `1.30-alpine` のように、版を指定します。実務では、より厳密に固定するためにダイジェストも使います（P7-1）。
> 根拠: https://docs.docker.com/build/building/best-practices/

### 2-6. 🔮 予測 → 動作確認

**問い**: 止まったコンテナだけが残っている状態で、`docker image rm` は成功するでしょうか。

```bash
docker run -d --name stoponce nginx:1.30-alpine
docker stop stoponce
docker image rm nginx:1.30-alpine
docker rm stoponce
```

期待される結果は、`docker image rm` の `conflict` エラーです。最後の `docker rm stoponce` は成功します。

✅ 検証済み: Docker Engine 29.8.0

### 2-7. ✅ 想起チェック

1. 1つのイメージから2つのコンテナを作ると、ファイルの変更は共有されますか
2. イメージを消す前に、何をしますか
3. コンテナの調子が悪いとき、基本はどうしますか

<details><summary>答え</summary>

1. 共有されない。書き込み先はコンテナごとに別
2. そのイメージを使うコンテナを、止まったものも含めて消す
3. 消して作り直す

</details>

### 2-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `docker pull` | 2-1 で実践、2-2 で解説 |
| `docker image ls` | 2-1 で実践 |
| `docker rm` | 2-1 で実践、2-2 で解説 |
| `docker image rm` | 2-1 で実践。P0-3 の宣言を回収 |
| `docker rm -f` | 2-1 で解説 |
| Docker Hub | 2-2 で解説 |

### 📇 まとめカード

> **イメージは読み取り専用の材料。コンテナは材料から起動した実体。**

**残った問い**: 動いているコンテナの中は、どう調べるのか。

---
▶ **次**: P1-3 動いているコンテナを調べる

---

## P1-3: 動いているコンテナを調べる

**❓ この回の問い**: 前回の答えは「コンテナは消して作り直せる」だった。でも、消す前に原因を知りたい。
→ **動いているコンテナの中は、どう調べるのか？**

**作るもの / 確かめること**: ログ・シェル・設定の3方向から、同じコンテナを調べる
**重要度**: 🔴 毎日使う — 不具合の調査は、ほぼこの3つから始まるから
**前ステップとの接続**: P1-1 の `web` を調べる

### 3-0. このステップの初出トークン

**Docker**: `docker logs` `docker exec` `docker inspect`
**Linux**: `/usr/share/nginx/html`
**その他**: なし

### 3-1. 実践

準備します。わざと存在しないページも開きます。

```bash
docker run -d -p 8080:80 --name web nginx:1.30-alpine
curl -s -o /dev/null localhost:8080
curl -s -o /dev/null localhost:8080/nothing
```

#### 方向1: ログを見る

```bash
docker logs web --tail 3
```

```text
192.168.65.1 - - [02/Nov/2026:13:46:25 +0000] "GET / HTTP/1.1" 200 896 "-" "curl/8.7.1" "-"
192.168.65.1 - - [02/Nov/2026:13:46:25 +0000] "GET /nothing HTTP/1.1" 404 153 "-" "curl/8.7.1" "-"
2026/11/02 13:46:25 [error] 31#31: *2 open() "/usr/share/nginx/html/nothing" failed (2: No such file or directory), client: 192.168.65.1, server: localhost, request: "GET /nothing HTTP/1.1", host: "localhost:8080"
```

✅ 検証済み: Docker Engine 29.8.0。行の順番は実行のたびに前後することがある。

アクセスが記録されています。`404` の原因が、探したファイルのパスまで出ています。

#### 方向2: 中に入る

```bash
docker exec web sh -c 'grep -E "listen|root" /etc/nginx/conf.d/default.conf | head -3; ls /usr/share/nginx/html'
```

```text
    listen       80;
    listen  [::]:80;
        root   /usr/share/nginx/html;
50x.html
index.html
```

✅ 検証済み: Docker Engine 29.8.0

中で対話したいときは、次のように入ります。

```bash
docker exec -it web sh
```

`hostname` などを試して、`exit` で出ます。

⚠️ 未実行: `-it` の対話操作は、ターミナルが無い検証環境では実行していない。検証手順: 上のコマンドで `/ #` と表示され、`hostname` の結果が `docker ps` の CONTAINER ID と同じになることを確かめる。

#### 方向3: 設定を見る

```bash
docker inspect web --format '{{.State.Status}} {{.NetworkSettings.Networks.bridge.IPAddress}} {{json .Config.Cmd}}'
```

```text
running 172.17.0.2 ["nginx","-g","daemon off;"]
```

✅ 検証済み: Docker Engine 29.8.0

`docker inspect` は、本来は大きな JSON を出します。`--format` で必要な項目だけを取り出します。

### 3-2. 🔬 仕組み解剖

| コマンド | 調べるもの | 仕組み | 使う場面 |
| --- | --- | --- | --- |
| `docker logs` | プログラムの出力 | Docker が標準出力と標準エラーを保存している | 最初に見る。エラーの理由を探す |
| `docker exec` | 中の実際の状態 | 動いているコンテナに新しいプロセスを追加する | 設定やファイルを確かめる |
| `docker inspect` | Docker が持つ設定 | デーモンの記録を JSON で返す | ポート、環境変数、状態を確かめる |

`-it` は2つのオプションの組み合わせです。

| 部品 | 正式名称 | 意味 |
| --- | --- | --- |
| `-i` | interactive | キーボードの入力をコンテナに渡す |
| `-t` | tty | 端末のように表示する |

> 🧒 **かみくだくと**: 標準出力 = プログラムが画面に向けて出す文字。`print()` や `console.log()` の行き先です。

なぜを下っていきます。

```text
なぜ、docker logs で nginx のログが読めるのか
  → nginx の出力を Docker が受け取っているから
      → なぜ、ファイルではなく出力に書くのか
          → コンテナを消すと、中のファイルは消えるから
              → なぜ、それで困らないのか
                  → 出力を Docker が受け取れば、外から集められるから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | `docker logs` はサーバのコンソール出力に近い。`docker exec` は対応物なし。理由は、動いている隔離環境に後からプロセスを足す仕組みが Node.js や Python に無いから |
| **なぜこの設計か** | ログと中の状態と Docker の設定は別物なので、調べる手段も3つに分かれている |
| **ビルド時かランタイム時か** | すべてランタイム |
| **ホストからの見え方** | `docker exec` で足したプロセスも、P1-4 の `docker top` に出る |
| **失敗時の挙動** | 中に無いコマンドを打つと、下のエラーになる |

```text
OCI runtime exec failed: exec failed: unable to start container process: exec: "bash": executable file not found in $PATH
```

✅ 検証済み: Docker Engine 29.8.0

このエラーは、イメージの中に `bash` が無いことを示します。Alpine 系のイメージには `sh` を使います。**箱に入っていないコマンドは、中で打てません。** P0-1 の「下の層」の話と同じです。

### 3-3. 🐧 Linux注

> 🐧 **Linux注**: `/usr/share/nginx/html` は、nginx が配るファイルの置き場所です。Linux のパスは `/` から始まり、macOS と同じ形で書きます。
> 🐧 **Linux注**: `grep -E "listen|root"` は、`listen` か `root` を含む行を取り出します。

### 3-4. 解説 — なぜこうするか

不具合を調べる順番を決めておくと、迷いません。

```text
1. docker ps -a     動いているか。止まった理由のコードは何か
2. docker logs      プログラムは何と言っているか
3. docker inspect   Docker の設定は意図どおりか
4. docker exec      中の実際の状態はどうか
```

**見てほしいところ**: 外から内へ進みます。コンテナが止まっていると `docker exec` は使えませんが、`docker logs` と `docker inspect` は使えます。

片付けます。

```bash
docker rm -f web
```

🧠 **Docker の考え方**: コンテナは使い捨て。だから、出力は外に流し、調べる手段も外に持つ。

### 3-5. 🏢 実務メモ

> 🏢 **実務メモ**: `docker logs` は、コンテナの標準出力と標準エラーを表示します。アプリのログをファイルに書くと、`docker logs` には出ません。
> 根拠: https://docs.docker.com/engine/logging/

### 3-6. 🔮 予測 → 動作確認

**問い**: `docker exec` で `index.html` を書き換えると、ブラウザの表示は変わるでしょうか。

```bash
docker run -d -p 8080:80 --name web nginx:1.30-alpine
docker exec web sh -c 'echo "<h1>hello from exec</h1>" > /usr/share/nginx/html/index.html'
curl -s localhost:8080
docker rm -f web
```

```text
<h1>hello from exec</h1>
```

✅ 検証済み: Docker Engine 29.8.0

表示は変わります。動いている nginx が、同じファイルを読むからです。この変更がどこに書かれて、いつ消えるかは P1-5 で確かめます。

### 3-7. ✅ 想起チェック

1. コンテナの不具合を調べる順番を言えますか
2. `docker exec web bash` が失敗する理由は何ですか
3. 止まったコンテナで使えるのは、`logs`、`exec`、`inspect` のどれですか

<details><summary>答え</summary>

1. `docker ps -a` → `docker logs` → `docker inspect` → `docker exec`
2. そのイメージに `bash` が入っていないから
3. `logs` と `inspect`

</details>

### 3-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `docker logs` | 3-2 で解剖 |
| `docker exec` | 3-2 で解剖 |
| `docker inspect` | 3-2 で解剖 |
| `/usr/share/nginx/html` | 3-3 で解説 |

### 📇 まとめカード

> **調べる順番は `ps -a` → `logs` → `inspect` → `exec`。外から内へ。**

**残った問い**: `exec` で入ると、別の世界のように見えた。何が隔離されているのか。

---
▶ **次**: P1-4 隔離の正体

---

## P1-4: 隔離の正体

**❓ この回の問い**: 前回、コンテナの中に入ると別の環境のように見えた。P1-1 では「どう分けているかは後で明かす」と書いた。
→ **コンテナは、どうやって隔離されているのか？**

**作るもの / 確かめること**: PID のずれとメモリ制限を確かめる
**重要度**: ⚪ 背景知識 — 普段は打たないが、停止やメモリ不足の原因を読むために要るから
**前ステップとの接続**: P1-3 の `web` を、外側と内側から比べる

### 4-0. このステップの初出トークン

**Docker**: `namespace` `cgroup` `--memory`
**補助**: `docker top` `docker stats`
**Linux**: `PID` / `UID`
**その他**: OOM Kill

### 4-1. 実践

#### 同じプロセスを、2つの視点で見る

**🔮 予測**: nginx の親玉のプロセスは、内側と外側で同じ番号でしょうか。

```bash
docker run -d --name web nginx:1.30-alpine

# ホストから見たプロセス
docker top web

# コンテナの中から見たプロセス
docker exec web ps

# Docker が記録しているホスト側の番号
docker inspect web --format '{{.State.Pid}}'
```

```text
UID     PID     PPID    CMD
root    6219    6195    nginx: master process nginx -g daemon off;
statd   6255    6219    nginx: worker process
（省略）

PID   USER     TIME  COMMAND
    1 root      0:00 nginx: master process nginx -g daemon off;
   30 nginx     0:00 nginx: worker process
（省略）
   42 root      0:00 ps

6219
```

✅ 検証済み: Docker Engine 29.8.0。`docker top` は列と行を省略した。

**同じプロセスなのに、番号が違います。** 外では `6219`、中では `1` です。

> 🧒 **かみくだくと**: PID = プロセスに付く番号。動いているプログラムの出席番号です。

#### 別のコンテナからは見えるのか

**🔮 予測**: 普通のコンテナで `ps` を実行すると、`web` の nginx は見えるでしょうか。

```bash
# 普通のコンテナ
docker run --rm alpine ps

# PID の隔離を外したコンテナ
docker run --rm --pid=host alpine sh -c 'ps | grep -m1 "nginx: master"'
```

```text
PID   USER     TIME  COMMAND
    1 root      0:00 ps
 8204 root      0:00 nginx: master process nginx -g daemon off;
```

✅ 検証済み: Docker Engine 29.8.0。番号はコンテナを作り直すと変わる。

普通のコンテナには、自分の `ps` しか見えません。隔離を外すと、`web` の nginx がホスト側の番号で見えます。**つまり、nginx はホストの上の普通のプロセスです。** 周りが見えないようにされているだけです。

> 🔓 **教材用の簡略化**: `--pid=host` は観察のためだけに使います。**本番では**使いません。隔離が弱くなるためです。
> 根拠: https://docs.docker.com/reference/cli/docker/container/run/

#### 使える量を制限する

現在の使用量を見ます。

```bash
docker stats --no-stream web
docker rm -f web
```

```text
NAME      MEM USAGE / LIMIT     CPU %     PIDS
web       10.12MiB / 7.748GiB   0.00%     13
```

✅ 検証済み: Docker Engine 29.8.0。表は列を絞って載せた。

次に、メモリを制限します。Python で約 200MB を使います。

**🔮 予測**: 64MB に制限すると、どうなるでしょうか。

```bash
docker run --name oom --memory 64m --memory-swap 64m python:3.13-slim python -c 'x = b"x" * 200_000_000; print("ok", len(x))'
echo "終了コード: $?"
docker inspect oom --format 'OOMKilled={{.State.OOMKilled}}'
docker rm oom
```

```text
終了コード: 137
OOMKilled=true
```

Python の `ok` は出ません。プログラムは、何も言わずに強制終了されました。

512MB に増やすと動きます。

```bash
docker run --rm --memory 512m python:3.13-slim python -c 'x = b"x" * 200_000_000; print("ok", len(x))'
```

```text
ok 200000000
```

✅ 検証済み: Docker Engine 29.8.0

> 🧒 **かみくだくと**: OOM Kill = メモリが足りなくなったとき、カーネルがプロセスを強制終了すること。OOM は Out Of Memory（メモリ切れ）の略です。

### 4-2. 🔬 仕組み解剖

コンテナの隔離は、Linux カーネルの2つの機能でできています。

```text
         ホスト（Linux VM）の カーネル
┌──────────────────────────────────────┐
│ namespace = 何が見えるか             │
│ cgroup    = どれだけ使えるか         │
│                                      │
│   ┌──────────┐      ┌──────────┐     │
│   │ web      │      │ 別の箱   │     │
│   │ nginx    │      │ ps       │     │
│   └──────────┘      └──────────┘     │
└──────────────────────────────────────┘
```

**見てほしいところ**: 箱の中のプログラムは、ホストの上の普通のプロセスです。箱の正体は、カーネルが付けた2つの設定です。

| 機能 | 正式名称 | 役割 | たとえ |
| --- | --- | --- | --- |
| `namespace` | Linux namespace（名前空間） | プロセスごとに見える範囲を分ける | 部屋の壁 |
| `cgroup` | control group | CPU やメモリの使用量を制限する | 部屋ごとの電気の上限 |

Docker が使う主な namespace です。

| 種類 | 分けるもの | 確かめたこと |
| --- | --- | --- |
| PID | プロセスの番号と一覧 | `ps` で他のコンテナが見えない |
| NET | ネットワーク | 同じ 80 番がぶつからない（P1-1） |
| MNT | ファイルシステムの見え方 | 中の `/` がホストと違う |
| UTS | ホスト名 | `hostname` が CONTAINER ID になる |
| IPC | プロセス間の通信 | 通常は意識しない |
| USER | ユーザの番号 | Docker の既定では使わない |

namespace が違うことは、番号でも確かめられます。

```bash
docker run -d --name web nginx:1.30-alpine
docker exec web readlink /proc/1/ns/pid
docker run --rm alpine readlink /proc/1/ns/pid
docker exec web hostname
docker ps --filter name=^web$ --format '{{.ID}}'
docker rm -f web
```

```text
pid:[4026532693]
pid:[4026532829]
fdc0f227b836
fdc0f227b836
```

✅ 検証済み: Docker Engine 29.8.0。番号は環境で変わる。比べるのは、2つの番号が違うこと。

cgroup の制限は、ファイルとして見えます。

```bash
docker run --rm alpine cat /sys/fs/cgroup/memory.max
docker run --rm --memory 64m alpine cat /sys/fs/cgroup/memory.max
```

```text
max
67108864
```

✅ 検証済み: Docker Engine 29.8.0。`67108864` は 64MiB をバイトで表した数。

なぜを下っていきます。

```text
なぜ、中のプログラムは自分が PID 1 だと思うのか
  → カーネルが namespace の中の番号を見せているから
      → なぜ、番号を分けられるのか
          → カーネルが1つのプロセスに、複数の番号を持たせられるから
              → なぜ、終了コードは 137 なのか
                  → 128 + シグナル番号 9（SIGKILL）で、カーネルに強制終了されたから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | 対応物なし。React のコンポーネントのスコープはプログラムの中の決まりで、namespace はカーネルが強制する仕切りだから |
| **なぜこの設計か** | VM を起動せずに、普通のプロセスを隔離できる。起動が速い代わりに、カーネルは共有する |
| **ビルド時かランタイム時か** | ランタイム。`docker run` のたびに設定される |
| **ホストからの見え方** | `docker top` にホスト側の PID が出る |
| **失敗時の挙動** | メモリ超過は終了コード `137` と `OOMKilled=true` で分かる。アプリのログには何も残らないことがある |

> 🐧 **UID**: `docker top` では `statd`、`docker exec web ps` では `nginx` と出ました。別のユーザに見えますが、実体は同じ番号 `101` です。Linux はユーザを名前ではなく番号で管理します。名前は、見る側の一覧で読み替えているだけです。詳しくは P3-2 で扱います。

✅ 検証済み: コンテナの中で `id nginx` が `uid=101` を返すことと、`docker top web -eo pid,uid,comm` が worker に UID 101 を示すことを確認した。

### 4-3. 🐧 Linux注

> 🐧 **Linux注**: `/proc` はカーネルの情報をファイルとして見せる場所です。`/sys/fs/cgroup` は cgroup の設定を見せる場所です。

### 4-4. 解説 — なぜこうするか

ここで、P0 からの答えがつながります。

**コンテナは、namespace と cgroup で囲まれた、ホスト上の普通のプロセスです。** だから起動が速く、カーネルを共有し、メインのプロセスが終わると終わります。

🧠 **Docker の考え方**: コンテナは小さなコンピュータではない。見える範囲と使える量を制限されたプロセス。

### 4-5. 🏢 実務メモ

> 🏢 **実務メモ**: 既定ではコンテナのメモリに上限はありません。メモリの使いすぎが他のプロセスに影響しないよう、必要に応じて `--memory` で制限します。
> 根拠: https://docs.docker.com/engine/containers/resource_constraints/

### 4-6. 🔮 予測 → 動作確認

**問い**: コンテナが何の前触れもなく止まり、ログが空でした。何を確かめますか。

```bash
docker run --name oom --memory 64m --memory-swap 64m python:3.13-slim python -c 'x = b"x" * 200_000_000'
docker ps -a --filter name=^oom$ --format '{{.Status}}'
docker logs oom
docker inspect oom --format '{{.State.OOMKilled}}'
docker rm oom
```

期待される結果は、`Exited (137)` と空のログと `true` です。

✅ 検証済み: Docker Engine 29.8.0

### 4-7. ✅ 想起チェック

1. namespace と cgroup の役割を、それぞれ一言で言えますか
2. コンテナの中の PID 1 は、ホストでも PID 1 ですか
3. 終了コード 137 を見たら、何を疑いますか

<details><summary>答え</summary>

1. namespace は何が見えるか。cgroup はどれだけ使えるか
2. 違う。ホスト側では別の番号を持つ
3. SIGKILL による強制終了。`OOMKilled` を確かめる

</details>

### 4-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `namespace` | 4-2 で解剖。P1-1 の宣言を回収 |
| `cgroup` | 4-2 で解剖 |
| `--memory` | 4-1 で実践、4-2 で解剖 |
| `docker top` | 4-1 で実践 |
| `docker stats` | 4-1 で実践 |
| `PID` | 4-1 で解説。⏭️ PID 1 の特別さは P2-5 で回収 |
| `UID` | 4-2 で解説。⏭️ P3-2 で回収 |
| OOM Kill | 4-1 で解説 |

### 📇 まとめカード

> **コンテナの正体は、namespace と cgroup で囲まれたホスト上のプロセス。**

**残った問い**: `/` が別に見えるのは MNT namespace のおかげだった。では、書き込んだファイルの実体はどこにあるのか。

---
▶ **次**: P1-5 書き込みはどこへ消えるか

---

## P1-5: 書き込みはどこへ消えるか

**❓ この回の問い**: 前回の答えは「コンテナは囲まれたプロセス」だった。P1-3 では `index.html` を書き換えられたが、イメージは読み取り専用のはずだ。
→ **書き込みはどこに入り、いつ消えるのか？**

**作るもの / 確かめること**: `stop` と `rm` で、書き込みの結果がどう違うかを見る
**重要度**: 🟡 読めればよい — 直接操作は少ないが、データが消える理由を説明するために要るから
**前ステップとの接続**: P1-3 の書き換えの行方を確かめる

### 5-0. このステップの初出トークン

**Docker**: `docker start` `docker diff` `overlay`
**Linux**: なし
**その他**: 書き込み層

### 5-1. 実践

ファイルの作成、変更、削除を1つずつ行います。

```bash
docker run -d --name web nginx:1.30-alpine
docker exec web sh -c 'echo memo > /tmp/memo.txt; rm /usr/share/nginx/html/50x.html; echo x >> /usr/share/nginx/html/index.html'
docker diff web
```

抜き出した出力です。

```text
C /tmp
A /tmp/memo.txt
C /usr/share/nginx/html
C /usr/share/nginx/html/index.html
D /usr/share/nginx/html/50x.html
```

✅ 検証済み: Docker Engine 29.8.0。実際の出力には、nginx の起動処理が作った行も含まれる（`/run/nginx.pid` など）。

| 記号 | 意味 |
| --- | --- |
| `A` | Added（追加） |
| `C` | Changed（変更） |
| `D` | Deleted（削除） |

**🔮 予測**: `docker stop` と `docker start` のあと、`memo.txt` は残るでしょうか。

```bash
docker stop web
docker start web
docker exec web cat /tmp/memo.txt
```

```text
memo
```

**残ります。** 次に、**消して作り直します**。

```bash
docker rm -f web
docker run -d --name web nginx:1.30-alpine
docker exec web cat /tmp/memo.txt
docker exec web ls /usr/share/nginx/html
docker rm -f web
```

```text
cat: can't open '/tmp/memo.txt': No such file or directory
50x.html
index.html
```

✅ 検証済み: Docker Engine 29.8.0

**消えました。** 削除した `50x.html` も戻っています。イメージは最初から変わっていなかったからです。

### 5-2. 🔬 仕組み解剖

```text
見えるファイル（マージされた結果）
        ▲
┌───────┴────────────────────┐
│ 書き込み層（upper）        │ コンテナごと。rm で消える
├────────────────────────────┤
│ イメージのレイヤ（lower）  │ 読み取り専用。共有される
│ イメージのレイヤ（lower）  │
└────────────────────────────┘
```

**見てほしいところ**: 下は変わりません。変更は、すべて一番上の層に入ります。

| 操作 | 実際に起きること |
| --- | --- |
| 読む | 上の層から順に探す |
| 新しく作る | 書き込み層に作る |
| 変更する | 下の層からコピーしてから書き込み層で変更する（Copy-on-Write） |
| 消す | 書き込み層に「消した」という印を置く。下の層は残る |

これが `overlay` の仕組みです。実物を見ます。

```bash
docker run --rm alpine sh -c 'grep " / " /proc/mounts' | tr ',' '\n' | cut -c1-40
```

```text
overlay / overlay rw
relatime
lowerdir=/var/lib/desktop-containerd/dae
upperdir=/var/lib/desktop-containerd/dae
workdir=/var/lib/desktop-containerd/daem
nouserxattr 0 0
```

✅ 検証済み: Docker Engine 29.8.0 / Docker Desktop。パスは環境で変わる。

`lowerdir` がイメージの層で、`upperdir` が書き込み層です。コンテナの `/` は、複数のディレクトリを重ねて1つに見せた結果です。

> 🧒 **かみくだくと**: 層を透明なフィルムの重なりとして考えます。下の絵は変えず、一番上のフィルムにだけ書き足します。上に白く塗れば、下の絵は隠れて見えます。

なぜを下っていきます。

```text
なぜ、rm で書き込みが消えるのか
  → 書き込み層はコンテナごとに作られ、コンテナと一緒に消えるから
      → なぜ、イメージは消えないのか
          → イメージの層は読み取り専用で、コンテナはそれを重ねているだけだから
              → なぜ、この設計なのか
                  → コンテナごとに全ファイルを写さず、速く作れるから
```

| 確認すること | 内容 |
| --- | --- |
| **既知スタックとの対応** | 対応物なし。Git の差分に形は似ているが、overlay は履歴ではなく、動いているファイルシステムの見え方を作るから |
| **なぜこの設計か** | 同じイメージの層を共有できるので、コンテナを増やしてもディスクと時間を節約できる |
| **ビルド時かランタイム時か** | ランタイムの話。ビルドで層が積まれる話は P2-3 で扱う |
| **ホストからの見え方** | `docker diff` と `/proc/mounts` で確かめられる |
| **失敗時の挙動** | エラーは出ない。`docker rm` すると、データが静かに消える |

### 5-3. 🐧 Linux注

> 🐧 **Linux注**: `/proc/mounts` は、いま接続されているファイルシステムの一覧です。`tr ',' '\n'` は、読みやすいように `,` を改行に変えています。

### 5-4. 解説 — なぜこうするか

| 操作 | プロセス | 書き込み層 | イメージ |
| --- | --- | --- | --- |
| `docker stop` | 止まる | 残る | 残る |
| `docker start` | 動き出す | 残る | 残る |
| `docker rm` | — | **消える** | 残る |
| `docker image rm` | — | — | 消える |

つまり、**コンテナの中に大事なデータを置いてはいけません。** DB をこのまま動かすと、`docker rm` でデータが消えます。解決策は P3-1 の volume です。

🧠 **Docker の考え方**: コンテナの中は使い捨て。残したいデータは外に出す。

### 5-5. 🏢 実務メモ

> 🏢 **実務メモ**: 書き込み層のデータは、コンテナを消すと失われます。残すデータには volume などを使います。書き込みの多い処理も、volume のほうが適しています。
> 根拠: https://docs.docker.com/engine/storage/

### 5-6. 🔮 予測 → 動作確認

**問い**: コンテナの中で作ったファイルは、`docker image ls` のサイズを増やすでしょうか。

```bash
docker image ls nginx:1.30-alpine --format '{{.Size}}'
docker run -d --name web nginx:1.30-alpine
docker exec web sh -c 'dd if=/dev/zero of=/tmp/big bs=1M count=50 2>/dev/null'
docker image ls nginx:1.30-alpine --format '{{.Size}}'
docker ps --size --filter name=^web$ --format '{{.Size}}'
docker rm -f web
```

```text
93.1MB
93.1MB
52.5MB (virtual 119MB)
```

イメージのサイズは変わりません。増えるのはコンテナの書き込み層だけです。3行目の `52.5MB` が書き込み層の大きさです。

✅ 検証済み: Docker Engine 29.8.0

### 5-7. ✅ 想起チェック

1. `docker stop` のあと、書き込んだファイルは残りますか。`docker rm` のあとはどうですか
2. 書き込み層と、イメージの層の違いは何ですか
3. `docker diff` の `A`、`C`、`D` の意味を言えますか

<details><summary>答え</summary>

1. `stop` では残る。`rm` では消える
2. 書き込み層はコンテナごとで書き込める。イメージの層は読み取り専用で共有される
3. 追加、変更、削除

</details>

### 5-8. 初出トークンの回収確認

| トークン | 扱い |
| --- | --- |
| `docker start` | 5-1 で実践 |
| `docker diff` | 5-1 で実践 |
| `overlay` | 5-2 で解剖。⏭️ 層が積まれる話は P2-3 で回収 |
| 書き込み層 | 5-2 で解説 |

### 📇 まとめカード

> **変更は書き込み層に入る。`rm` すれば層ごと消える。**

---

## P1 のなぜなぜの鎖

```text
動き続けるものは、どう動かすのか
  → -d で裏で動かし、-p で道を通す
      ↓ 止めてもコンテナが残るのはなぜか
  → イメージとコンテナは別物だから
      ↓ 動いているコンテナはどう調べるのか
  → ps -a → logs → inspect → exec の順に調べる
      ↓ 中が別の世界に見えるのはなぜか
  → namespace で見える範囲、cgroup で使える量が決まるから
      ↓ 書いたファイルはどこへ行くのか
  → 書き込み層に入り、rm で消える
      ↓ では、自分のアプリの箱はどう作るのか
```

---

## P1 フェーズ末パック（M2）

### ブランクページ再現

> ✍️ **ブランクページ**: 教材を閉じて、次のコマンド列を白紙から書いてください。
> 思い出せなかった箇所に印を付け、**その箇所の仕組み解剖だけ**読み返します。

1. nginx を `web` という名前で、裏で動かし、8080 番で公開する
2. 動いていることを、一覧と `curl` で確かめる
3. ログを確かめる
4. コンテナの中でファイルを1つ作り、変更の一覧を見る
5. 止めて、消して、変更が消えたことを確かめる

**翌日に行うことをすすめます。** 直後は短期記憶で再現できてしまい、定着の負荷が足りません。

### 宿題

#### Lv1 基礎確認: 自分のページを出す

**課題**

- `nginx:1.30-alpine` を `shop` という名前で起動する
- ホスト側のポートは `8090` にする
- `docker exec` で `index.html` を `<h1>EC準備中</h1>` に書き換える

**ヒント**: P1-3 の 3-6 と同じ形です。ポートの左側だけを変えます。

**判定基準**: `curl -s localhost:8090` が `<h1>EC準備中</h1>` を返す。

<details><summary>解答例</summary>

```bash
docker run -d -p 8090:80 --name shop nginx:1.30-alpine
docker exec shop sh -c 'echo "<h1>EC準備中</h1>" > /usr/share/nginx/html/index.html'
curl -s localhost:8090
docker rm -f shop
```

✅ 検証済み: Docker Engine 29.8.0

</details>

#### Lv2 応用: 2台を別々のページにする

**課題**

- 同じイメージから `shop1`（8091）と `shop2`（8092）を起動する
- それぞれの `index.html` を `shop1` と `shop2` に書き換える
- `shop1` を消して作り直すと、`shop2` は変わらず、`shop1` だけ初期状態に戻ることを確かめる

**ヒント**: コンテナごとに書き込み層が別であることを使います。

**判定基準**: 作り直したあと、`curl -s localhost:8091` の結果に `Welcome to nginx!` が含まれ、`curl -s localhost:8092` が `shop2` を返す。

<details><summary>解答例</summary>

```bash
docker run -d -p 8091:80 --name shop1 nginx:1.30-alpine
docker run -d -p 8092:80 --name shop2 nginx:1.30-alpine
docker exec shop1 sh -c 'echo shop1 > /usr/share/nginx/html/index.html'
docker exec shop2 sh -c 'echo shop2 > /usr/share/nginx/html/index.html'
docker rm -f shop1
docker run -d -p 8091:80 --name shop1 nginx:1.30-alpine
curl -s localhost:8091 | grep -o 'Welcome to nginx!' | head -1
curl -s localhost:8092
docker rm -f shop1 shop2
```

✅ 検証済み: Docker Engine 29.8.0

</details>

#### Lv3 発展: 隔離されているものと共有されているものを列挙する

**課題**

- `alpine` のコンテナを2つ用意し、次の4項目を比べる: カーネルの版 / ホスト名 / PID namespace の番号 / メモリの上限
- 片方だけに `--memory 128m` を付ける
- 項目ごとに「共有」か「隔離」かを、コマンドの出力を根拠に表にする

**ヒント**: カーネルの版は P0-3、ホスト名と namespace は P1-4、メモリの上限は `/sys/fs/cgroup/memory.max` です。起動を続けるには `sleep 300` を使います。

**判定基準**: カーネルの版だけが2つのコンテナで一致し、ホスト名・PID namespace の番号・`memory.max` は一致しない。

<details><summary>解答例</summary>

```bash
docker run -d --name box1 alpine sleep 300
docker run -d --name box2 --memory 128m alpine sleep 300

for name in box1 box2; do
  echo "== $name"
  docker exec "$name" sh -c 'uname -r; hostname; readlink /proc/1/ns/pid; cat /sys/fs/cgroup/memory.max'
done

docker rm -f box1 box2
```

| 項目 | 結果 | 判定 |
| --- | --- | --- |
| カーネルの版 | 同じ | 共有 |
| ホスト名 | 違う | 隔離（UTS namespace） |
| PID namespace | 違う | 隔離（PID namespace） |
| `memory.max` | `max` と `134217728` | コンテナごとに別（cgroup） |

✅ 検証済み: Docker Engine 29.8.0

</details>

---

## ▶ 次は P2

P1 はここまでです。次のフェーズから、EC の API を自分でイメージにします。

**前提チェック**

- [ ] `-p` の左右の意味を説明できる（P1-1）
- [ ] イメージとコンテナの違いを説明できる（P1-2）
- [ ] 不具合を調べる順番を言える（P1-3）
- [ ] コンテナの正体を、namespace と cgroup で説明できる（P1-4）
- [ ] `stop` と `rm` で何が変わるか説明できる（P1-5）
