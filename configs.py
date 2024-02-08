import logging

from tinydb import Query, TinyDB

from constants import DEFAULT_BACKEND_URL
from models.syncSettings import SyncSettings
from utils import promptUserForOfflineFolder

db = TinyDB("db.json", sort_keys=True)


def getBackendUrl() -> str:
    query = Query()
    url = db.search(query.backendUrl.exists())

    if url is None or len(url) == 0:
        db.insert({"backendUrl": DEFAULT_BACKEND_URL})
        return DEFAULT_BACKEND_URL

    extractedUrl = url[0].get("backendUrl")
    logging.info(f"Backend URL: {extractedUrl}")
    return extractedUrl


def updateOfflineFolder() -> str:
    """
    Prompts the user for a folder to keep synced and saves it to the database
    """

    folder = promptUserForOfflineFolder()
    logging.info(f"Updating offline folder to {folder}")

    query = Query()
    db.upsert({"offlineFolder": folder}, query.offlineFolder.exists())
    logging.info(f"Updated offline folder to {folder}")

    return folder


def getOfflineFolder() -> str | None:
    query = Query()
    folder = db.search(query.offlineFolder.exists())

    if folder is None or len(folder) == 0:
        return None

    extractedFolder = folder[0].get("offlineFolder")
    if extractedFolder is None or len(extractedFolder) == 0:
        return None

    logging.info(f"Offline folder: {extractedFolder}")

    # if windows, replace / with \
    if "\\" not in extractedFolder:
        extractedFolder = extractedFolder.replace("/", "\\")

    return extractedFolder


def getSyncSettings() -> SyncSettings | None:
    query = Query()
    settings = db.search(query.syncSettings.exists())

    if settings is None or len(settings) == 0:
        return SyncSettings()

    extractedSettings = settings[0].get("syncSettings")  # type: SyncSettings
    logging.info(f"Sync settings: {extractedSettings}")

    return extractedSettings


def updateSyncSettings(settings):
    query = Query()
    db.upsert({"syncSettings": settings}, query.syncSettings.exists())
    logging.info(f"Updated sync settings to {settings}")


def clearSavedData():
    db.truncate()
    logging.info("Cleared saved data")


def updateLastSync():
    query = Query()
    db.upsert({"lastSync": "10/10/2021 10:00 AM"}, query.lastSync.exists())
    logging.info("Updated last sync")


def getLastSync() -> str:
    query = Query()
    lastSync = db.search(query.lastSync.exists())

    if lastSync is None or len(lastSync) == 0:
        return "Never"

    extractedLastSync = lastSync[0].get("lastSync")
    logging.info(f"Last sync: {extractedLastSync}")

    return extractedLastSync
