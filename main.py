import logging

from rich.columns import Columns
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from auth import clearSavedAuth, initAuth
from configs import getLastSync, updateOfflineFolder
from sync import Sync, getOfflineFolder
from utils import (
    checkIfUpdateAvailable,
    deleteOtherReleaseExecutables,
    runUpdate,
)

banner = """
▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
██░▄▄▀█░██░▄▄▀█▄▄░█░▄▄█░▄▀████░▄▄▀█░██▀▄▄▀█░██░█░▄▀██
██░▄▄▀█░██░▀▀░█▀▄██░▄▄█░█░████░████░██░██░█░██░█░█░██
██░▀▀░█▄▄█▄██▄█▄▄▄█▄▄▄█▄▄█████░▀▀▄█▄▄██▄▄███▄▄▄█▄▄███
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
"""
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.FileHandler("log.txt"), RichHandler()],
)


def showMenu():
    optionTable = Table(
        title="BlazedCloud Sync",
        header_style="bold magenta",
        highlight=True,
        expand=True,
        show_header=False,
    )

    statusTable = Table(
        title="Status",
        header_style="bold magenta",
        highlight=True,
        expand=True,
        show_header=False,
    )
    statusData = [
        "Last Sync: " + getLastSync(),
        "Offline Folder:",
        "[yellow]" + getOfflineFolder()
        if getOfflineFolder() is not None
        else "[red]Not Set",
    ]
    import utils

    if utils.isUpdateAvailable:
        statusData.append("[yellow]Update Available")

    for statusData in statusData:
        statusTable.add_row(statusData)

    options = [
        "(1) Sync",
        "(2) Set Offline Folder",
        "(3) Update",
        "(4) Sign out",
        "(5) Exit",
    ]
    for option in options:
        optionTable.add_row(option)

    columns = Columns([optionTable, statusTable], expand=True)

    console.print(Panel(columns, title="Menu", style="bold green", expand=False))
    choice = Prompt.ask("Action Select")

    if choice == "1":
        if getOfflineFolder() is None or len(getOfflineFolder()) == 0:
            console.print("[red]Offline folder not set")
        else:
            console.print("[green]Syncing")
            Sync()
    elif choice == "2":
        console.print("[green]Setting Offline Folder")
        updateOfflineFolder()
    elif choice == "3":
        console.print("[green]Launching Update Script")
        runUpdate()
    elif choice == "4":
        console.print("[green]Signing Out")
        clearSavedAuth()
        return
    elif choice == "5":
        console.print("[green]Exiting")
        return
    else:
        console.print("[red]Invalid Option")

    console.print(banner, style="bold red", justify="center")
    showMenu()


if __name__ == "__main__":
    try:
        deleteOtherReleaseExecutables()
    except Exception as e:
        logging.error("Failed to delete other release executables: " + str(e))
    console.print(banner, style="bold red", justify="center")

    try:
        checkIfUpdateAvailable()
    except Exception as e:
        logging.error("Failed to check for updates: " + str(e))

    if initAuth():
        showMenu()
