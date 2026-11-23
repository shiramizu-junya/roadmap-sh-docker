# Multi-Container Application（Todo API）

roadmap.sh の Docker プロジェクト「Multi-Container Application」の解答です。

- プロジェクト URL: https://roadmap.sh/projects/multi-container-service

Todo を作る・見る・直す・消す API と、データをしまう MySQL を、`compose.yaml` 1つで起動します。

## 課題との対応

課題の Part 1（ローカルで、API と DB を Docker Compose で動かす）に取り組みました。

| 課題の指定 | この解答 |
| --- | --- |
| Node.js + Express の API | Django + Django Ninja の API |
| MongoDB + Mongoose | MySQL 8.4 + Django の ORM |
| `docker-compose.yml` | `compose.yaml` |
| コンテナを止めてもデータが残る | 名前付き volume `db-data` に保存する |
| コードを変えると API が再起動する（nodemon） | `src/` を bind mount し、`runserver` の自動再読み込みを使う |

Part 2（Terraform と Ansible でのデプロイ）、Part 3（CI/CD）、ボーナス（Nginx）は、まだ取り組んでいません。

## 構成

```
Mac（localhost:3000）
   │
   ▼
┌──────────────────────────────┐            ┌──────────────────────────────┐
│ api                          │  db:3306   │ db                           │
│ Django + Django Ninja        │───────────▶│ MySQL 8.4                    │
│ 起動時に migrate してから    │            │ healthcheck で準備を確かめる │
│ runserver を動かす           │            │                              │
└──────────────────────────────┘            └──────────────┬───────────────┘
   ▲                                                        │
   │ ./src を bind mount                                    ▼
   │（保存するとすぐ反映）                      volume db-data（データを残す）
```

- api は、db の healthcheck が通るまで起動を待ちます（`depends_on` の `condition: service_healthy`）
- api は、起動のたびに `entrypoint.sh` で `migrate` を動かします。からっぽの DB でも、表が自動で作られます

## ファイル

```
projects/multi-container-service/
├── compose.yaml        api と db、volume db-data
├── Dockerfile          api のイメージ（python:3.13-slim + uv）
├── entrypoint.sh       migrate のあと、CMD の runserver に入れ替わる
├── api.env             api が db につなぐための設定
├── db.env              MySQL の初期設定（DB 名・ユーザー・パスワード）
├── pyproject.toml
├── uv.lock
└── src/
    ├── manage.py
    ├── config/         settings.py / urls.py / api.py（API の本体）
    └── todos/          Todo モデルと migration
```

## 動かし方

必要なもの: Docker（Docker Compose v2 以上）

```bash
cd projects/multi-container-service
docker compose up -d --build
docker compose ps
```

api が `Up`、db が `Up (healthy)` になれば起動しています。API は `http://localhost:3000` で受け付けます。

## API

| やり方 | 住所 | 内容 | 成功したときの番号 |
| --- | --- | --- | --- |
| GET | `/todos` | 一覧を見る | 200 |
| POST | `/todos` | 作る | 201 |
| GET | `/todos/{id}` | 1つ見る | 200 |
| PUT | `/todos/{id}` | 直す（`title` と `completed` をまるごと） | 200 |
| DELETE | `/todos/{id}` | 消す | 204 |

送る中身（POST / PUT）:

```json
{"title": "Buy milk", "completed": false}
```

- `title` は必ず書きます（200字まで）。ないときは 422 を返します
- `completed` は省略できます。省略すると `false` です
- ない番号を指定すると 404 を返します

API の仕様（OpenAPI、自動生成）: http://localhost:3000/openapi.json

## 動作の確かめ方

```bash
B=localhost:3000/todos
curl -s -X POST $B -H 'Content-Type: application/json' -d '{"title": "test"}' -w ' %{http_code}\n'
curl -s -X PUT $B/1 -H 'Content-Type: application/json' -d '{"title": "test", "completed": true}' -w ' %{http_code}\n'
curl -s $B/1 -w ' %{http_code}\n'
curl -s -X POST $B -H 'Content-Type: application/json' -d '{"title": "delete me"}' -w ' %{http_code}\n'
curl -s -X DELETE $B/2 -w '%{http_code}\n'
curl -s -o /dev/null $B/2 -w '%{http_code}\n'
```

```
{"id": 1, "title": "test", "completed": false} 201
{"id": 1, "title": "test", "completed": true} 200
{"id": 1, "title": "test", "completed": true} 200
{"id": 2, "title": "delete me", "completed": false} 201
204
404
```

止めて起動し直しても、データが残ることを確かめます。

```bash
docker compose down
docker compose up -d
curl -s $B -w ' %{http_code}\n'
```

```
[{"id": 1, "title": "test", "completed": true}] 200
```

`up -d` の直後は、api の起動が間に合わず返事が来ないことがあります。数秒待ってから打ち直してください。

## 片付け

```bash
docker compose down -v --rmi local
```

`-v` で volume `db-data` も消すので、データも消えます。`--rmi local` で、`build` で作ったイメージも消します。

## 注意

- `db.env` と `api.env` にパスワードを書き、リポジトリに入れています。学習用の簡略化です。本番では secrets などを使い、リポジトリに入れません
- API は Django の開発用サーバー（`runserver`）で動かしています。本番向けの構成ではありません
