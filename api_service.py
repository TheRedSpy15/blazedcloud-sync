import logging
import os
from mimetypes import MimeTypes

import httpx
import requests

from configs import getBackendUrl
from models.fileObject import FileObject

client = httpx.Client(http2=True)


def checkHealth():
    reponse = client.get(
        "https://pb.blazedcloud.com/api/health",
        follow_redirects=True,
        headers={"User-Agent": "blazedcloud-sync"},
    )
    logging.info(reponse.json().get("message"))


def getUsage(token: str, uid: str):
    logging.info(f"Getting usage for {token}")
    backendUrl = getBackendUrl()
    url = backendUrl + "data/usage/" + uid
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "blazedcloud-sync"}
    response = client.get(url, headers=headers)
    return response.text


def getFileList(token: str, uid: str) -> list[FileObject]:
    logging.info(f"Getting file list for {uid}")
    backendUrl = getBackendUrl()
    url = backendUrl + "data/listall/" + uid
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "blazedcloud-sync"}
    response = client.get(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Failed to get file list: {response.text}")
        return []

    # convert to array of FileObject
    fileObjects: FileObject = []
    try:
        for file in response.json():
            object = FileObject.from_dict(file)

            # remove string before first / and the slash itself
            object.Key = object.Key[object.Key.find("/") + 1 :]

            # if on windows, replace / with \
            if "\\" not in object.Key:
                object.Key = object.Key.replace("/", "\\")

            # ensure no whitespace between slashes
            object.Key = object.Key.replace(" \\", "\\")
            object.Key = object.Key.replace("\\ ", "\\")

            fileObjects.append(object)
    except Exception as e:
        logging.error(f"Failed to convert file list to FileObject: {e}")
        return []

    return fileObjects


def getDownloadUrl(token: str, uid: str, key: str):
    """
    this function will always replace \ with / in the key
    """

    # replace \ with /
    key = key.replace("\\", "/")

    logging.info(f"Getting download url for {key}")
    backendUrl = getBackendUrl()
    url = backendUrl + "data/down/" + uid
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "blazedcloud-sync"}
    payload = {"filename": key, "useShlink": False}
    response = client.post(url, headers=headers, data=payload)
    return response.text


def downloadFromUrl(url, headers, directory):
    logging.info(f"Downloading from {url}")
    response = client.get(url, headers=headers)
    with open(directory, "wb") as f:
        f.write(response.content)
    return response


def getUploadUrl(filePath: str, token: str, uid: str):
    backendUrl = getBackendUrl()
    filename = os.path.basename(filePath)
    url = backendUrl + "data/up/" + uid
    mime = MimeTypes().guess_type(filename)[0]
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "blazedcloud-sync"}
    payload = {"filename": filePath, "contentType": mime}
    logging.info(f"Getting upload url for {payload}")

    response = client.post(url, headers=headers, data=payload)
    return response.text


def uploadToUrl(url, file):
    # check if file exists
    if not os.path.exists(file):
        logging.error(f"File {file} does not exist")
        return None

    # multipart upload
    logging.info(f"Uploading to {url}")
    with open(file, "rb") as f:
        filename = os.path.basename(file)
        mime = MimeTypes().guess_type(filename)[0]
        headers = {"Content-Type": mime, "User-Agent": "blazedcloud-sync"}
        logging.info(f"Uploading {file}")
        files = {"file": (filename, f, mime)}
        response = client.put(url=url, headers=headers, files=files)
    return response


async def get_latest_version():
    url = "https://api.github.com/repos/TheRedSpy15/blazedcloud-sync/releases/latest"
    response = requests.get(url)

    if response.status_code == 200:
        latest_version = response.json()["tag_name"]
        return latest_version
    else:
        logging.error(
            f"Failed to fetch latest version. Status code: {response.status_code}"
        )
        return None
