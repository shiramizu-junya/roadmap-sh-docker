# 00. 学習計画（M0）

**モード**: M0 学習計画 / 生成日: 2026-11-01 / **状態: 承認済み（2026-11-01）**
**素材**: `docs/_roadmap-docker-source.md`（roadmap.sh/docker 全56トピック）
**生成ルール**: `docs/_prompt.md`

本編は1フェーズずつ生成し、フェーズごとに確認を受ける。

---

## 1. 到達点の確認

| # | 到達点 | 満たすフェーズ | 検証の形 |
| --- | --- | --- | --- |
| 1 | 任意のアプリを Dockerfile でイメージ化できる | P2（PJ1） | 自分で書いた Dockerfile で `docker build` が通り、`curl` に応答する |
| 2 | 複数コンテナを Compose で連携させ、データを永続化できる | P3 → P4（PJ2） | `docker compose up` 1回で EC が動き、`down` → `up` 後も商品が残る |
| 3 | イメージのサイズとビルド時間を意図して削減できる | P5 | 変更ごとの差を数値で示し、理由を説明できる |
| 4 | 本番向けに安全な構成へ変えられる | P6（PJ3） | 非 root で動き、パスワードが `docker inspect` と `docker history` に出ない |
| 5 | イメージの配布と CI/CD の流れを説明し、構築できる | P7（PJ4） | push のたびに CI がテストとビルドを行い、レジストリに公開される。デプロイは読むだけでも流れを説明できる |
| 6 | 落ちた・繋がらないときに原因の層を特定できる | P1 から全フェーズ | 「ホスト / デーモン / イメージ / プロセス / ネットワーク」のどの層かを、コマンド出力を根拠に言える |

---

## 2. 前提知識・環境

✅ 検証済み: **Docker Desktop / Docker Engine 29.8.0 / containerd v2.3.5 / runc 1.5.1 / Docker Compose v5.5.1 / buildx v0.37.1 / macOS 26.6.2（arm64）**

| 種類 | 使うもの | 確認した版 | 選んだ理由 |
| --- | --- | --- | --- |
| API 実行環境 | `python:3.13-slim` | Python 3.13.18 | 公式イメージ。Debian 系で `apt` も学べる |
| Web フレームワーク | Django / Django Ninja | 5.2.18（LTS）/ 1.7.3 | 指定どおり。Django は LTS 系を採用 |
| DB | `mysql:8.4` | 8.4.13（LTS） | 指定どおり。Django 5.2 の要件は MySQL 8.0.11 以上 |
| DB ドライバ | mysqlclient | 2.3.0 | Django が推奨するドライバ |
| キャッシュ / キュー | `redis:8-alpine` | 8.10.3 | カートと Celery のブローカーを兼ねる |
| 非同期処理 | Celery | 5.6.3 | Django で広く使われるタスクキュー |
| アプリサーバ | gunicorn | 26.2.0 | Django の本番用 WSGI サーバ |
| フロント | `node:24-alpine` / Vite / React | Node 24.22.2 / 8.3.5 / 19.3.1 | Node は LTS 系 |
| 入口 | `nginx:1.30-alpine` | 1.30.6 | 静的配信とリバースプロキシ |
| Python 依存管理 | uv | 0.13.6 | ロックファイルで再現性を確保できる |

✅ 検証済み: `python:3.13-slim` 上に上記の Python パッケージを入れ、`mysql:8.4` に Django 5.2 のマイグレーションが通ることを確認した。

> 💡補足: `mysqlclient` は `python:3.13-slim` のままではインストールできず、`gcc` などのビルド用パッケージが必要だった。実測ではビルド用パッケージ入りのイメージが 739MB になった。これは P3-4 でつまずきとして体験し、P5-4 でマルチステージビルドの題材にする。

### 環境準備

| # | コマンド | 役割 |
| --- | --- | --- |
| 1 | `docker version` | クライアントとデーモンの両方が応答するか確認する |
| 2 | `docker context ls` | どのデーモンにつないでいるか確認する |
| 3 | `docker info` | デーモン側の構成を確認する |
| 4 | `docker compose version` | Compose が使えるか確認する |
| 5 | `docker run --rm hello-world` | pull から実行までの通し確認 |

**ホストの Mac に Python と Node.js は要らない。** 依存のインストールも実行もコンテナの中で行う。

---

## 3. リポジトリ構成（完成時）

モノレポにする。現時点で存在するのは `docs/` だけで、`apps/` 以下は読者が教材を見ながら自分で作る。

```text
roadmap-sh-docker/
├── README.md
├── compose.yaml            開発用（P4）
├── compose.prod.yaml       本番用の差分（P6）
├── apps/
│   ├── api/                Django + Django Ninja（P2 から）
│   │   ├── Dockerfile
│   │   ├── .dockerignore
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   └── src/
│   └── web/                React + Vite（P4 から）
│       ├── Dockerfile
│       ├── .dockerignore
│       ├── package.json
│       └── src/
├── infra/
│   └── nginx/              Nginx の設定（P6）
├── .github/workflows/      CI/CD（P7）
├── docs/
│   ├── _prompt.md
│   ├── _roadmap-docker-source.md
│   ├── 00-plan.md
│   ├── 01-glossary.md      用語の逆引き
│   ├── p0-foundations.md
│   ├── p1-container-basics.md
│   ├── p2-dockerfile.md
│   ├── p3-storage-network.md
│   ├── p4-compose.md
│   ├── p5-optimize.md
│   ├── p6-production.md
│   ├── p7-delivery.md
│   └── 99-uncovered.md     M3 の出力
└── projects/               EC に含まれない roadmap.sh の提出物
    ├── basic-dockerfile/
    ├── multi-container-service/
    └── dockerized-service-deployment/
```

---

## 4. 題材アプリの育ち方

機能は Docker の概念を学ぶために足す。アプリの解説は最小限にする。

```text
P2  api                                   /api/health
P3  api + db                              商品一覧・詳細
P4  web + api + db + redis + worker       画面・商品画像・カート・サムネイル
P6  nginx + web成果物 + api + db + redis + worker   本番構成
```

| 機能 | 導入 | 引き出す Docker の概念 |
| --- | --- | --- |
| ヘルスチェック API | P2 | Dockerfile、レイヤ、ポート公開 |
| 商品一覧・詳細 | P3 | volume、network、環境変数、DB の初期化 |
| 商品画面 | P4 | Compose へのサービス追加、開発時の同期 |
| カート | P4 | Redis の追加、サービス名での名前解決 |
| 商品画像・サムネイル | P4 | ワーカー、同じイメージの別コマンド起動、volume の共有 |
| 本番配信 | P6 | マルチステージの成果物、リバースプロキシ |

---

## 5. ステップ一覧

合計 **35ステップ**（P0 3 / P1 5 / P2 5 / P3 4 / P4 6 / P5 4 / P6 4 / P7 4）。
1ステップの Docker 側の初出は最大3つ。全体が15ステップを超えるため、テンプレに従って8フェーズに分割した。

### P0 — なぜコンテナか / Docker の構造（プロジェクト・M2 なし）

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P0-1 | 「動かない」はどこで起きるのか | アプリの下にある層を実機で確かめる | `コンテナ` `イメージ` | ⚪ |
| P0-2 | ベアメタル・VM・コンテナ | Mac と Docker の2つのカーネルを並べて見る | `カーネル` `VM` `ホスト` | ⚪ |
| P0-3 | `docker` と打つと何が起きるか | イベントを流しながら hello-world を実行する | `docker run` `docker system events` `OCI` | ⚪ |

### P1 — コンテナ操作 / 隔離の仕組み

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P1-1 | 既存イメージを動かす | nginx を起動してブラウザで見る | `-d` `-p` `docker ps` | 🔴 |
| P1-2 | イメージとコンテナは別物 | 1つのイメージから2つのコンテナを作る | `docker pull` `docker image ls` `docker rm` | 🔴 |
| P1-3 | 動いているコンテナを調べる | ログ・シェル・設定の3方向から調べる | `docker logs` `docker exec` `docker inspect` | 🔴 |
| P1-4 | 隔離の正体 | PID のずれとメモリ制限を確認する | `namespace` `cgroup` `--memory` | ⚪ |
| P1-5 | 書き込みはどこへ消えるか | `stop` と `rm` で結果の違いを見る | `docker start` `docker diff` `overlay` | 🟡 |
| **M2** | フェーズ末パック | ブランクページ再現 + 宿題 Lv1〜3 | — | — |

### P2 — Dockerfile で API をイメージ化する

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P2-1 | 最小の Dockerfile | Python を実行するだけのイメージを作る | `FROM` `CMD` `docker build` | 🔴 |
| P2-2 | コードをイメージに入れる | Django のコードを置き、配置を確かめる | `COPY` `WORKDIR` `.dockerignore` | 🔴 |
| P2-3 | 依存を入れて API を動かす | uv で依存を入れ、レイヤの増加を見る | `RUN` `docker history` `uv sync` | 🔴 |
| P2-4 | ビルドキャッシュを効かせる | 命令の順序で再ビルド時間を比べる | `--no-cache` `docker builder prune` `build context` | 🔴 |
| P2-5 | 起動とポート / 止まらないコンテナ | `docker stop` が10秒かかる状態を直す | `EXPOSE` `ENTRYPOINT` `PID 1` | 🔴 |
| **PJ1** | Basic Dockerfile | 提出用に小さな Dockerfile を書く | — | — |
| **M2** | フェーズ末パック | ブランクページ再現 + 宿題 Lv1・Lv2 | — | — |

### P3 — データとネットワーク：API を MySQL につなぐ

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P3-1 | volume でデータを残す | コンテナを消しても DB が残ることを確かめる | `docker volume` `-v` `マウント` | 🔴 |
| P3-2 | bind mount で開発する | コードの変更が即反映されることと所有者を確かめる | `--mount type=bind` `--user` `UID/GID` | 🔴 |
| P3-3 | コンテナ同士をつなぐ | コンテナ名で通信できることを確かめる | `docker network` `--network` `bridge` | 🔴 |
| P3-4 | 商品 API を MySQL につなぐ | ビルド失敗を直し、商品一覧を返す | `-e` `--env-file` `apt-get` | 🔴 |
| **M2** | フェーズ末パック | ブランクページ再現 + 宿題 Lv1〜3 | — | — |

### P4 — Compose で EC を組み上げる

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P4-1 | 長いコマンドを compose.yaml にする | api と db を1コマンドで起動する | `services:` `docker compose up` `docker compose down` | 🔴 |
| P4-2 | volume と network を宣言する | `down` と `down -v` の差を確かめる | `volumes:` `networks:` `docker compose ps` | 🔴 |
| P4-3 | 「起動した」の定義 | DB の起動待ちで落ちる状態を作って直す | `healthcheck` `depends_on` `condition` | 🔴 |
| P4-4 | React の画面を足す | 開発サーバを動かし、変更を同期する | `build:` `docker compose exec` `docker compose watch` | 🔴 |
| P4-5 | Redis でカートを作る | サービスを足し、設定を外に出す | `environment:` `env_file:` `docker compose config` | 🔴 |
| P4-6 | ワーカーでサムネイルを作る | 同じイメージを別コマンドで動かし、画像を共有する | `command:` `docker compose logs -f` `stop_grace_period` | 🔴 |
| **PJ2** | Multi-Container Application | Todo API を自力で組む | — | — |
| **M2** | フェーズ末パック | ブランクページ再現 + 宿題 Lv1・Lv2 | — | — |

### P5 — サイズ削減とマルチステージ

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P5-1 | 今のイメージを測る | サイズと既知の脆弱性を数値にする | `docker system df` `docker image inspect` `docker scout cves` | 🟡 |
| P5-2 | ベースイメージを選ぶ | slim / alpine を同条件で比べる | `ARG` `ENV` `--platform` | 🟡 |
| P5-3 | フロントのマルチステージ | Node を最終イメージから追い出す | `AS` `COPY --from` `--target` | 🔴 |
| P5-4 | API のマルチステージ | `gcc` を追い出し、gunicorn で起動する | `gunicorn` `--no-dev` `.venv の移送` | 🔴 |
| **M2** | フェーズ末パック | ブランクページ再現 + 宿題 Lv1〜3 | — | — |

### P6 — 本番構成 / セキュリティ / 運用設定

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P6-1 | Nginx を入口にする | 静的配信と API の中継を1つの入口にまとめる | `proxy_pass` `docker compose -f` `expose:` | 🔴 |
| P6-2 | root で動かさない | 非 root で起動し、volume の所有者問題を直す | `USER` `read_only:` `cap_drop:` | 🔴 |
| P6-3 | パスワードを外に出す | `inspect` と `history` に出ないことを確かめる | `secrets:` `/run/secrets/` `--secret` | 🔴 |
| P6-4 | 落ちても戻る / ログを溢れさせない | 再起動方針とログの上限を設定する | `restart:` `logging:` `max-size` | 🟡 |
| **PJ3** | Multi-Service Application | EC 全体を要件と照合して提出する | — | — |
| **M2** | フェーズ末パック | ブランクページ再現 + 宿題 Lv1・Lv2 | — | — |

### P7 — レジストリ / CI/CD / デプロイ

| # | タイトル | 作るもの / 確かめること | 初出トークン | 重要度 |
| --- | --- | --- | --- | --- |
| P7-1 | レジストリへ push する | タグとダイジェストの違いを確かめる | `docker tag` `docker push` `@sha256:` | 🔴 |
| P7-2 | GitHub Actions でテストと公開 | コンテナ内テスト、スキャン、push を自動化する | `docker/build-push-action` `docker compose run` `GHCR` | 🔴 |
| P7-3 | マルチアーキテクチャ | arm64 と amd64 を1つのタグで配る | `docker buildx build --platform` `manifest` `imagetools inspect` | ⚪ |
| P7-4 | サーバへデプロイする | 別ホストで起動し、更新と切り戻しをする | `docker context` `ssh://` `docker compose pull` | 🟡 |
| **PJ4** | Dockerized Service Deployment（任意） | CI からサーバ公開までを通す | — | — |
| **M2** | フェーズ末パック | ブランクページ再現 + 宿題 Lv1・Lv2 | — | — |

**最後に M3** で `docs/99-uncovered.md` を作る。

---

## 6. roadmap.sh のプロジェクト

出典は 2026-11-01 に確認した。

| PJ | 実施 | 置き場 | 要件の扱い |
| --- | --- | --- | --- |
| **PJ1** Basic Dockerfile | P2 末 | `projects/basic-dockerfile/` | `alpine:latest` で文字列を出す。任意課題の引数も行う |
| **PJ2** Multi-Container Application | P4 末 | `projects/multi-container-service/` | Part 1 を Django Ninja + MySQL の Todo API で作る |
| **PJ3** Multi-Service Application | P6 末 | リポジトリのルート | EC 全体で満たす。API のカスタムベース、全サービスのヘルスチェックとログローテーションも含める |
| **PJ4** Dockerized Service Deployment | P7 末（任意） | `projects/dockerized-service-deployment/` | Node.js を Django Ninja に置き換える。サーバが要るので任意 |

| 出典の項目 | 扱い | 理由 |
| --- | --- | --- |
| PJ2 の Terraform / Ansible | 扱わない | Docker と別の学習対象になる。M3 に載せる |
| PJ2 の Part 3（CI/CD デプロイ） | P7 と PJ4 で扱う | 内容が重複するため |
| PJ2 の Nginx（ボーナス） | P6-1 で扱う | PJ3 の要件と重複するため |
| `nodejs-service-deployment` | 扱わない | Docker を使わない課題のため |
| `stans-navigation-deployment` | 扱わない | PJ4 と学習内容が重複するため |

🔄 **素材からの変更**: Node.js + Express → Django + Django Ninja / MongoDB → MySQL / nodemon → `runserver` / `docker-compose.yml` → `compose.yaml`。

---

## 7. デプロイの扱い（VPS を借りなくても理解できる形）

P7-4 と PJ4 は2本立てにする。

| 読み方 | 内容 | 費用 |
| --- | --- | --- |
| **読むだけ** | 手順と実際の出力を載せる。出力を見れば流れが分かるように書く | 0円 |
| **手元で試す** | Linux コンテナを「疑似サーバ」として SSH で接続し、`docker context` とデプロイを体験する | 0円 |
| **VPS で試す** | 同じ手順を実サーバで行う | VPS 費用 |

疑似サーバで確認した箇所は `✅ 検証済み（疑似サーバ）` と書く。実 VPS 固有の手順は `⚠️ 未実行` として検証手順を併記する。

---

## 8. 単元との対応表（全56トピック）

| # | トピック | 扱う場所 |
| --- | --- | --- |
| 1 | application-architecture | P4 / P6-1 |
| 2 | bare-metal-vs-vms-vs-containers | P0-2 |
| 3 | basics-of-docker | P0-3 / P1 全体 |
| 4 | bind-mounts | P3-2 |
| 5 | building-container-images | P2 全体 |
| 6 | cgroups | P1-4 |
| 7 | command-line-utilities | P1-3 |
| 8 | container-registries | P7-1 |
| 9 | container-security | P6-2 / P6-3 |
| 10 | containers | P1 全体 |
| 11 | continuous-integration | P7-2 |
| 12 | data-persistence | P3-1 |
| 13 | databases | P3-1 / P3-4 |
| 14 | debuggers | **扱わない**（M3）。言語と IDE に依存し、Docker の仕組みの学習から離れるため |
| 15 | deploying-containers | P7-4 |
| 16 | developer-experience | P4-4 |
| 17 | docker-and-oci | P0-3 |
| 18 | docker-cli | P1 全体 |
| 19 | docker-compose | P4 全体 |
| 20 | docker-desktop-winmaclinux | 本ファイル §2 / P0-2 |
| 21 | docker-engine--linux | P0-3 |
| 22 | docker-run | P1-1 |
| 23 | docker-swarm | **扱わない**（M3）。複数ホストの運用は本教材の到達点の外 |
| 24 | dockerfiles | P2 全体 |
| 25 | dockerhub | P1-2 / P7-1 |
| 26 | efficient-layer-caching | P2-4 |
| 27 | ephemeral-container-filesystem | P1-5 |
| 28 | hot-reloading | P3-2 / P4-4 |
| 29 | image-security | P5-1 / P7-2 |
| 30 | image-size-and-security | P5 全体 |
| 31 | image-tagging-best-practices | P7-1 |
| 32 | images | P1-2 |
| 33 | installation--setup | 本ファイル §2 |
| 34 | introduction | P0-1 |
| 35 | kubernetes | **扱わない**（M3）。同上 |
| 36 | namespaces | P1-4 |
| 37 | networks | P3-3 |
| 38 | nomad | **扱わない**（M3）。同上 |
| 39 | others-ghcr-ecr-gcr-acr-etc | P7-1 / P7-2 |
| 40 | paas-options | **扱わない**（M3）。各社の操作手順で、Docker の仕組みから離れるため |
| 41 | package-managers | P3-4 / P5-2 |
| 42 | programming-languages | 前提として充足 |
| 43 | running-containers | P1-1 |
| 44 | runtime-configuration-options | P1-4 / P3-4 / P6-2 / P6-4 |
| 45 | runtime-security | P6-2 |
| 46 | shell-commands | 単元にせず、🐧 Linux注で必要な分だけ扱う |
| 47 | shell-scripting | P2-5（`ENTRYPOINT` の範囲） |
| 48 | tests | P7-2 |
| 49 | underlying-technologies | P1-4 / P1-5 |
| 50 | union-filesystems | P1-5 / P2-3 |
| 51 | users--groups-permissions | P3-2 / P6-2 |
| 52 | using-3rd-party-container-images | P1-1 / P5-2 |
| 53 | volume-mounts | P3-1 |
| 54 | volumes | P3-1 |
| 55 | what-are-containers | P0-1 |
| 56 | why-do-we-need-containers | P0-1 |

**扱わない6件**: debuggers / docker-swarm / kubernetes / nomad / paas-options / programming-languages（前提として充足）。
programming-languages 以外の5件は M3 に一次情報付きで載せる。

---

## 9. 範囲外の予告

詳細は M3 の `docs/99-uncovered.md` で確定する。

| 項目 | 扱わない理由 | 一次情報 |
| --- | --- | --- |
| Kubernetes | 複数ホストのオーケストレーションは到達点の外 | https://kubernetes.io/docs/ |
| Docker Swarm | 同上 | https://docs.docker.com/engine/swarm/ |
| Nomad | 同上 | https://developer.hashicorp.com/nomad/docs |
| PaaS 各社の手順 | Docker の仕組みから離れる | https://docs.docker.com/guides/ |
| Terraform / Ansible | Docker と別の学習対象 | https://developer.hashicorp.com/terraform/docs |
| デバッガ接続 | 言語と IDE に依存する | https://docs.docker.com/reference/cli/docker/buildx/debug/ |
| rootless モード | Docker Desktop では前提が変わる | https://docs.docker.com/engine/security/rootless/ |
| イメージ署名 | 配布の信頼性という別の層の話 | https://docs.docker.com/engine/security/trust/ |
| overlay / macvlan ネットワーク | 複数ホストや特殊な環境が前提 | https://docs.docker.com/engine/network/drivers/ |
| Windows コンテナ | macOS では検証できない | https://learn.microsoft.com/virtualization/windowscontainers/ |
| 実行時の脅威検知 | 運用フェーズの別分野 | https://falco.org/docs/ |

---

## 10. 実行順

```text
P0 （3ステップ）                 確認
P1 （5ステップ）→ M2             確認
P2 （5ステップ）→ PJ1 → M2       確認
P3 （4ステップ）→ M2             確認
P4 （6ステップ）→ PJ2 → M2       確認
P5 （4ステップ）→ M2             確認
P6 （4ステップ）→ PJ3 → M2       確認
P7 （4ステップ）→ PJ4 → M2       確認
M3
```

AI はコードを読者のリポジトリへ置かず、作業用の場所で教材どおりに打って検証する。

---

## 11. 確定した判断（2026-11-01）

| 項目 | 決定 |
| --- | --- |
| Django の経験 | 触ったことがある。Django はファイルの役割を短く説明し、Docker の説明に分量を回す |
| Django のバージョン | 5.2 LTS |
| デプロイ | 疑似サーバで手を動かせるようにし、VPS がなくても読んで理解できる形にする |
| リポジトリ構成 | §3 のモノレポ。PJ3 は EC 全体で提出し、ほかは `projects/` に置く |
