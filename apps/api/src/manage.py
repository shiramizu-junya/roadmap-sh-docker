import os
import sys


def start_debugpy_if_requested() -> None:
    """DEBUGPY=1 のときだけ、デバッガ（Zed など）の接続を 5678 番で待つ。"""
    if os.environ.get("DEBUGPY") != "1":
        return
    # runserver は自動再起動のために親子2つのプロセスで動く。
    # リクエストを処理するのは子（RUN_MAIN=true）なので、そちらでだけ待つ
    if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
        return
    # Python 本体の一部（frozen modules）について出る警告を止める。自分のコードの停止には影響しない
    os.environ.setdefault("PYDEVD_DISABLE_FILE_VALIDATION", "1")
    import debugpy

    port = int(os.environ.get("DEBUGPY_PORT", "5678"))
    # コンテナの中なので 0.0.0.0 で待つ（127.0.0.1 だとホストから届かない）。
    # ホスト側は compose.yaml で 127.0.0.1 にだけ公開しているので、外からは繋がらない
    # in_process_debug_adapter=True: 保存で再起動したときに古い部品がポートを握ったまま残らないようにする
    debugpy.listen(("0.0.0.0", port), in_process_debug_adapter=True)
    print(f"debugpy: {port} 番で接続を待っています", file=sys.stderr)


if __name__ == "__main__":
    start_debugpy_if_requested()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
