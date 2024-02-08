import logging

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from api_service import getDownloadUrl, getFileList
from auth import getAuth
from configs import getOfflineFolder, getSyncSettings, updateLastSync
from models.fileObject import FileObject
from utils import (
    downloadUrlToFile,
    formatBytesToString,
    getAllFilesFromFolder,
    isLocalNewer,
)

sync_status = "Folder not selected"
is_syncing = False


def getSyncStatus():
    global sync_status
    return sync_status


def Sync():
    global is_syncing
    global sync_status
    if getOfflineFolder() is None or len(getOfflineFolder()) == 0:
        logging.error("Invalid folder for sync: " + getOfflineFolder())
        return
    if is_syncing:
        return
    is_syncing = True
    sync_status = "Syncing"
    logging.info("Syncing...")

    console = Console()

    auth = getAuth()
    if auth is None:
        logging.error("Auth not saved for sync")
        return

    token = auth[0]
    uid = auth[1].get("id")
    syncSettings = getSyncSettings()

    # get server file list
    server_files: list[FileObject] = getFileList(token, uid)
    if server_files is None:
        logging.error("No server files found")
        return

    logging.debug(server_files)
    server_keys: list[str] = []
    logging.debug("---------- Loading Server files ----------")
    for server_file in server_files:
        logging.debug(server_file.Key)
        server_keys.append(server_file.Key)

    # get local file list
    local_files, local_files_abs = getAllFilesFromFolder(getOfflineFolder())
    logging.debug("---------- Loading Local files ----------")
    for local_file in local_files:
        logging.debug(local_file)

    # compare
    totalNotDownloaded = 0
    totalNotUploaded = 0

    missingTable = Table(title="Files not downloaded")
    missingTable.add_column("File", style="cyan", no_wrap=True)
    missingTable.add_column("Size", style="magenta")
    logging.debug("---------- Finding missing files (not downloaded) ----------")
    missing_keys: list[FileObject] = []
    for object in server_files:
        if object.Key not in local_files and ".blazed-placeholder" not in object.Key:
            logging.debug(object.Key)
            missing_keys.append(object.Key)
            missingTable.add_row(object.Key, str(object.Size or "0") + " B")
            totalNotDownloaded += object.Size or 0
    missingTable.add_row("Total", formatBytesToString(totalNotDownloaded))
    console.print(missingTable, justify="center")

    import os

    unsyncedTable = Table(title="Files not uploaded or updated")
    unsyncedTable.add_column("File", style="yellow", no_wrap=True)
    unsyncedTable.add_column("Size", style="magenta")
    logging.debug(
        "---------- Finding unsynced files (not uploaded or updated) ----------"
    )
    unsynced_files: list[str] = []
    for i, local_file in enumerate(local_files):
        if local_file not in server_keys:
            logging.debug(local_file)
            unsynced_files.append(local_files_abs[i])
            unsyncedTable.add_row(
                local_file, str(os.path.getsize(local_files_abs[i])) + " B"
            )
            totalNotUploaded += os.path.getsize(local_files_abs[i])
        elif local_file in server_keys:
            if isLocalNewer(
                local_files_abs[i],
                server_files[server_keys.index(local_file)],
            ):
                logging.debug("SERVER outdated", local_file)
                unsynced_files.append(local_files_abs[i])
                unsyncedTable.add_row(
                    local_file, str(os.path.getsize(local_files_abs[i])) + " B"
                )
                totalNotUploaded += os.path.getsize(local_files_abs[i])
    unsyncedTable.add_row("Total", formatBytesToString(totalNotUploaded))
    console.print(unsyncedTable, justify="center")

    # download missing
    confirmDownload = Confirm.ask(
        "Download missing " + formatBytesToString(totalNotDownloaded) + "? y/n"
    )

    if syncSettings.downloadMissingFiles and confirmDownload:
        logging.debug("---------- Downloading missing files ----------")
        for missing_file in missing_keys:
            logging.debug(missing_file)
            down_url = getDownloadUrl(token, uid, missing_file)
            logging.debug(down_url)

            # download file
            downloadUrlToFile(
                down_url,
                missing_file,
                getOfflineFolder(),
                server_files[server_keys.index(missing_file)],
            )

    console.print("Uploaded is not supported currently", style="bold yellow")
    # upload unsynced
    # if syncSettings.uploadUnsyncedFiles:
    #    logging.debug("---------- Uploading unsynced files ----------")
    #    for unsynced_file in unsynced_files:
    #        # remove offline folder from path and first slash
    #        key = unsynced_file.replace(getOfflineFolder() + "\\", "")
    #
    #        # replace \\ with /
    #        key = key.replace("\\", "/")
    #
    #        logging.debug("UPLOADING unsynced", unsynced_file, unsynced_file)
    #        up_url = getUploadUrl(key, token, uid)
    #        uploadToUrl(up_url, unsynced_file)

    is_syncing = False
    sync_status = "Synced"
    console.print("Synced", style="bold green")
    updateLastSync()
