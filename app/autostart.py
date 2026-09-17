"""Windowsのスタートアップフォルダへのショートカット登録。

オンボーディング画面で「スタートアップに登録する」を選んだ場合に、`shell:startup`
フォルダにこのアプリを起動するショートカット(.lnk)を作成する。ショートカット作成には
`win32com.client`(`WMI`パッケージ経由で既にインストールされている`pywin32`)を使い、
新規依存の追加はしていない。

配布用exe(PyInstallerでfrozen化されたもの)と、ソースから`pythonw run.py`で起動する
開発環境の両方に対応する(判定は`app/config.py`の`PROJECT_ROOT`と同じ`sys.frozen`基準)。
"""
import os
import sys

SHORTCUT_NAME = "TypingActivityTracker.lnk"


def _startup_folder():
    return os.path.join(
        os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )


def shortcut_path():
    return os.path.join(_startup_folder(), SHORTCUT_NAME)


def is_registered():
    return os.path.exists(shortcut_path())


def _launch_target():
    """(target, arguments, working_dir)を返す。"""
    if getattr(sys, "frozen", False):
        exe = sys.executable
        return exe, "", os.path.dirname(exe)

    # ソースから起動している開発環境: コンソールが出ないpythonw.exeでrun.pyを起動する。
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    run_py = os.path.join(project_root, "run.py")
    return pythonw, f'"{run_py}"', project_root


def register():
    """スタートアップフォルダにショートカットを作成する(既にあれば上書き)。"""
    import win32com.client  # Windows専用・pywin32依存のためここでimportする

    # 通常のWindows環境では常に存在するフォルダだが、WshShortcut.Saveは親フォルダが
    # 無いと失敗する(例外メッセージが分かりにくい)ため、念のため作成しておく。
    os.makedirs(_startup_folder(), exist_ok=True)

    target, arguments, working_dir = _launch_target()
    shell = win32com.client.DispatchEx("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path())
    shortcut.TargetPath = target
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = working_dir
    shortcut.WindowStyle = 7  # 最小化状態で起動
    shortcut.Save()


def unregister():
    path = shortcut_path()
    if os.path.exists(path):
        os.remove(path)
