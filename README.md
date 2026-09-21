# roadmap-sh-docker

Docker の学習リポジトリ。**1リポジトリで完結させる** — 教材は `docs/`、題材アプリは `app/`、プロジェクト成果物は `projects/`。

## 到達点

1. 任意のアプリを Dockerfile でイメージ化できる
2. 複数コンテナを compose で連携させ、データを永続化できる
3. イメージサイズと起動時間を意図して削減できる
4. コンテナが落ちた・繋がらないときに、ログとプロセスから原因の層を特定できる

## 使い方

教材はモード制で1回に1つずつ生成する。詳細は `docs/_prompt.md` §1。

**次に呼ぶもの**:

```
M1: P0 ステップ1
```

学習計画（M0）は生成済み。全体像は [`docs/00-plan.md`](docs/00-plan.md) を見る。

## 進捗

**M0 学習計画: ✅ 完了（2026-09-20 / 改訂 2026-09-21）** → [`docs/00-plan.md`](docs/00-plan.md)
全36ステップ + プロジェクト4本（P6 を除くと31ステップ + 3本）。

| Ph | 内容 | ステップ | 状態 | プロジェクト | 出力先 |
|---|---|---|---|---|---|
| P0 | 基礎 / アーキテクチャ / 用語 | 6 | 進行中 **2/6** | — | `docs/p0-foundations.md` |
| P1 | コンテナとは / CLI 基礎 | 5 | 未着手 0/5 | — | `docs/p1-container-basics.md` |
| P2 | Dockerfile / レイヤ | 5 | 未着手 0/5 | PJ1 | `docs/p2-dockerfile.md` |
| P3 | 永続化 / ネットワーク | 4 | 未着手 0/4 | — | `docs/p3-storage-network.md` |
| P4 | Docker Compose | 6 | 未着手 0/6 | PJ2 | `docs/p4-compose.md` |
| P5 | 最適化 / セキュリティ | 5 | 未着手 0/5 | PJ3 | `docs/p5-optimize.md` |
| P6 | レジストリ / CI/CD（任意） | 5 | 未着手 0/5 | PJ4 | `docs/p6-cicd.md` |

各フェーズは「M1 × ステップ数 → MP（あれば）→ M2 フェーズ末パック」の順に進める。
P0 だけは M2 を付けない（再現すべき設定ファイルがまだ無いため）。
最後に M3 で `docs/99-uncovered.md` を作る。

用語は [`docs/01-glossary.md`](docs/01-glossary.md) に集約する。P0-3 で骨格を作り、以降のステップで初出トークンを1行ずつ追記していく。

### プロジェクト

出典を読んだうえで、**前提知識が揃う地点**から実施タイミングを確定済み（[`docs/00-plan.md`](docs/00-plan.md) §6.1）。
各プロジェクトは**教材側から「▶ ここで PJ1 に取り組む」と前提チェック付きで指示が出る**ので、タイミングを自分で判断する必要はない。

| PJ | 名前 | いつ | 前提が揃う理由 | 状態 |
|---|---|---|---|---|
| PJ1 | Basic Dockerfile | P2-5 の直後 | 任意課題に `ENTRYPOINT`+`CMD` が要る | 未着手 |
| PJ2 | Multi-Container Application | P4-6 の直後 | volume・network（P3）+ compose（P4）が要る | 未着手 |
| PJ3 | Multi-Service Application | P5-5 の直後 | マルチステージ・非root・secrets・healthcheck が要る | 未着手 |
| PJ4 | Dockerized Service Deployment | P6-5 の直後（任意） | push・CI・リモート実行が要る | 未着手 |

出典の要件は一部を取捨している（PJ2 の Terraform / Ansible は PJ4 へ、PJ3 の React は省略 など）。詳細は §6.1。

## 実行順

```
M1: P0 ステップ1 〜 6
M1: P1 ステップ1 〜 5   →  M2: P1
M1: P2 ステップ1 〜 5   →  MP: PJ1  →  M2: P2
M1: P3 ステップ1 〜 4   →  M2: P3
M1: P4 ステップ1 〜 6   →  MP: PJ2  →  M2: P4
M1: P5 ステップ1 〜 5   →  MP: PJ3  →  M2: P5
M1: P6 ステップ1 〜 5   →  MP: PJ4  →  M2: P6   （任意）
M3
```

各ステップの末尾に `▶ 次: ...` が出るので、それに従えばよい。全体表は [`docs/00-plan.md`](docs/00-plan.md) §8。

## 題材アプリ

`app/` に**最小の FastAPI アプリを新規に作る**（P2-2 で `/health` のみ → P3-4 で MySQL 接続を追加）。
別リポジトリのアプリは持ち込まない。理由と方針は [`docs/00-plan.md`](docs/00-plan.md) §3.1。

`Dockerfile` / `compose.yaml` はリポジトリのルートに実ファイルとして置き、同じ内容を教材にも全文掲載する。

## 環境

✅ 検証済み（2026-09-20）: Docker Desktop 4.81.0 / Docker Engine 29.6.1 / Docker Compose v5.2.0 / macOS (darwin/arm64)

## メモ

- 各ステップの末尾に `📇 まとめカード` がある。**翌日はそれだけ見返す**
- 1回で覚えることは1つだけ。新しい言葉は4つまで（`docs/00-plan.md` §4 の P0 設計メモ）
- プロジェクトは**先に自力で組む**。解答例は `<details>` に隠れているので、開く前に判定基準で自己採点する
- ブランクページ再現は**翌日**にやる
- ステップごとにコミットする（どこで壊れたか追えるように）
- 詰まったら `projects/*/README.md` の「詰まった記録」に残す（到達点4の素材になる）
- Engine 29.x の `docker images` に `SIZE` 列は無い。`DISK USAGE` / `CONTENT SIZE` で読む
