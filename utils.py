import asyncio
import datetime
import logging
import os
import sys
import zipfile
from io import BytesIO
from tkinter.filedialog import askdirectory

import requests
from rich.console import Console
from rich.panel import Panel

from constants import TOOL_VERSION
from models.fileObject import FileObject

console = Console()

isUpdateAvailable = False


def promptUserForOfflineFolder():
    """
    Simply gets a user selected folder and returns it.

    Use updateOfflineFolder() to call this function and save the result to the database
    """

    logging.info("Prompting user for offline folder...")
    return askdirectory(
        mustexist=True
    )  # show an "Open" dialog box and return the path to the selected file


def checkIfUpdateAvailable():
    """
    Display a message if there is an update available
    """
    from api_service import get_latest_version

    global isUpdateAvailable

    try:
        loop = asyncio.get_event_loop()
        latest = loop.run_until_complete(get_latest_version())
        if latest is None:
            return
    except Exception as e:
        logging.error(f"Failed to check for update: {e}")
        return

    # replace "." with "" to get the version number as an int
    latestCode = latest.replace(".", "")
    currentCode = TOOL_VERSION.replace(".", "")

    if int(latestCode) > int(currentCode):
        console.print(
            Panel.fit(
                f"Current version: {TOOL_VERSION}\nLatest version: {latest}",
                title="Update Available",
            )
        )
        isUpdateAvailable = True


def runUpdate():
    if not isUpdateAvailable:
        console.print("[red]No update available")
        return

    latest = None
    try:
        from api_service import get_latest_version

        loop = asyncio.get_event_loop()
        latest = loop.run_until_complete(get_latest_version())
        if latest is None:
            return
    except Exception as e:
        logging.error(f"Failed to check for update: {e}")
        return

    if latest is None:
        logging.error("Failed to update")
        return

    # GitHub API endpoint for releases
    releases_url = (
        "https://api.github.com/repos/TheRedSpy15/blazedcloud-sync/releases/latest"
    )
    print(releases_url)

    # Make a request to get the latest release information
    response = requests.get(releases_url)
    release_data = response.json()
    print(release_data)

    # Get the download URL for the latest release
    download_url = release_data["assets"][0]["browser_download_url"]
    print(download_url)

    # Download the ZIP file containing the executable
    zip_content = requests.get(download_url).content

    # Extract the contents of the ZIP file
    print("Extracting release to", os.getcwd())
    with zipfile.ZipFile(BytesIO(zip_content), "r") as zip_ref:
        zip_ref.extractall()

    os.system(f"start blazedcloud-sync-{latest}.exe")
    sys.exit()


def convertUsageToString(bytes, isTerabyteActive):
    capacity = 5

    if isTerabyteActive:
        capacity = 1000

    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024**2:
        return f"{round(bytes / 1024, capacity)} KB"
    elif bytes < 1024**3:
        return f"{round(bytes / 1024 ** 2, capacity)} MB"
    elif bytes < 1024**4:
        return f"{round(bytes / 1024 ** 3, capacity)} GB"

    return f"{round(bytes / 1024 ** 4, capacity)} TB"


def formatBytesToString(bytes):
    capacity = 5

    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024**2:
        return f"{round(bytes / 1024, capacity)} KB"
    elif bytes < 1024**3:
        return f"{round(bytes / 1024 ** 2, capacity)} MB"
    elif bytes < 1024**4:
        return f"{round(bytes / 1024 ** 3, capacity)} GB"

    return f"{round(bytes / 1024 ** 4, capacity)} TB"


def deleteOtherReleaseExecutables():
    """
    Deletes all other release executables in the current directory
    """
    import os

    for file in os.listdir():
        if file.endswith(".exe") and file != f"blazedcloud-sync-{TOOL_VERSION}.exe":
            os.remove(file)


def getAllFilesFromFolder(folder):
    """
    Returns [0] the relative paths of all files in the folder, and [1] the absolute paths of all files in the folder
    """
    import os

    relativePaths: list[str] = []
    absolutePaths: list[str] = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            # if file ends with .tmp, delete it and move on
            if file.endswith(".tmp"):
                os.remove(os.path.join(root, file))
                continue

            absolutePaths.append(os.path.join(root, file))

            # remove offline folder from path and first slash
            file = os.path.join(root, file)
            file = file.replace(folder, "")
            if file.startswith("\\"):
                file = file[1:]

            relativePaths.append(file)
    return relativePaths, absolutePaths


def downloadUrlToFile(
    url: str, file: str, offlineFolder: str, object: FileObject
):  # example file: "vcx33oy8b86eg02/folder1/unnamed.jpg"
    """
    Downloads a file from a url to a file path

    remote object is need to set the modified date to match the server
    """

    # create folder for each string before the last /
    import os

    import httpx
    import rich.progress

    # create folder
    folder = os.path.join(offlineFolder, os.path.dirname(file))
    os.makedirs(folder, exist_ok=True)

    # file path
    filePath = os.path.join(offlineFolder, file + ".tmp")

    # Create the parent folder if it doesn't exist
    parent_folder = os.path.dirname(filePath)
    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)

    # download file
    with open(filePath, "wb") as out_file:
        with httpx.stream("GET", url) as response:
            total = int(response.headers["Content-Length"])
            if response.status_code != 200:
                logging.error(f"Failed to download file: {response.reason_phrase}")
                return

            with rich.progress.Progress(
                "[progress.percentage]{task.percentage:>3.0f}%",
                rich.progress.BarColumn(bar_width=None),
                rich.progress.DownloadColumn(),
                rich.progress.TransferSpeedColumn(),
            ) as progress:
                download_task = progress.add_task("Download", total=total)
                for chunk in response.iter_bytes():
                    out_file.write(chunk)
                    progress.update(
                        download_task, completed=response.num_bytes_downloaded
                    )

    # rename file
    try:
        os.rename(
            os.path.join(offlineFolder, file + ".tmp"),
            os.path.join(offlineFolder, file),
        )
    except Exception as e:
        logging.error("failed to rename file: " + str(e))
        if os.path.exists(os.path.join(offlineFolder, file + ".tmp")):
            os.remove(os.path.join(offlineFolder, file + ".tmp"))

    # set modified date
    remote_timestamp = datetime.datetime.strptime(
        object.LastModified, "%Y-%m-%dT%H:%M:%S.%fZ"
    ).timestamp()
    os.utime(os.path.join(offlineFolder, file), (remote_timestamp, remote_timestamp))

    del response
    del out_file


def isLocalSame(filepath, object):
    """
    Checks if the local file is the same as the server file by checking the size

    Returns True if the file is the same, False if not
    """
    import os

    # get local file info
    file_stats = os.stat(filepath)
    file_size = file_stats.st_size

    # compare
    if file_size == object.Size:
        return True
    return False


def isLocalNewer(filepath: str, object: FileObject):
    """
    Checks if the local file is newer than the server file by checking the last modified date

    Returns True if the local file is newer, False if not
    """
    import datetime
    import os

    # get local file info
    local_timestamp = os.path.getmtime(filepath)  # unix timestamp
    remote_timestamp = datetime.datetime.strptime(
        object.LastModified, "%Y-%m-%dT%H:%M:%S.%fZ"
    ).timestamp()

    # compare
    if local_timestamp > remote_timestamp:
        return True

    return False


def checkIfInStartFolder():
    """
    Checks if a shortcut is in the start folder
    """
    import getpass
    import os

    USER_NAME = getpass.getuser()

    bat_path = (
        r"C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
        % USER_NAME
    )
    return os.path.exists(bat_path + "\\" + "blazedcloud.lnk")


def createShortcutToApp():
    """
    Creates a shortcut to the application itself in the start folder
    """
    import getpass
    import os

    USER_NAME = getpass.getuser()

    file_path = os.path.abspath(__file__)
    app_name = "Blazed Sync"

    shortcut_path = (
        r"C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\%s.lnk"
        % (USER_NAME, app_name)
    )

    try:
        import os
        import sys

        import pythoncom
        from win32comext.shell import shell

        shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )
        shortcut.SetPath(shortcut_path)
        shortcut.SetDescription(app_name)
        shortcut.SetIconLocation(sys.executable, 0)
    except Exception as e:
        logging.error(f"Error creating shortcut: {e}")


def deleteShortcutInStartFolder():
    """
    Deletes the shortcut in the start folder
    """
    import getpass
    import os

    USER_NAME = getpass.getuser()

    bat_path = (
        r"C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
        % USER_NAME
    )
    os.remove(bat_path + "\\" + "blazedcloud.lnk")
