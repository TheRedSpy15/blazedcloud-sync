import logging

import keyring as kr
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from tinydb import Query

from api_service import client
from configs import db, getBackendUrl

userTable = db.table("user", cache_size=30)
console = Console()


def initAuth():
    logging.info("Initializing auth")
    if getAuth() is None:
        logging.info("No auth record found, prompting user for email/password")
        loginInfo = promptForEmailPassword()
        email = loginInfo[0]
        password = loginInfo[1]
        auth = authenticatePassword(email, password)
        if auth is None:
            logging.error("Failed to authenticate with email/password")
            promptAuthFailed()
        else:
            logging.info("Successfully authenticated with email/password")
            token = auth[0]
            saveAuth(auth[1], token)
            return True
    else:
        logging.info("Found auth record")
        auth = refreshAuth(getAuth()[0])
        if auth is None:
            clearSavedAuth()
            logging.error("Failed to refresh token")
            promptAuthFailed()
        token = auth[0]
        return True


def saveAuth(authModel, token):
    uid = authModel.get("id")

    query = Query()
    userTable.upsert(authModel, query.id == uid)
    logging.info("Saved auth record")

    # save email/password to keyring
    kr.set_password("blazedcloud", uid, token)
    logging.info("Saved keyring")


def authenticatePassword(email, password):
    if email is None or password is None:
        logging.error("No email/password provided")
        return None

    logging.info("Authenticating with email/password")

    backendUrl = getBackendUrl()
    url = backendUrl + "api/collections/users/auth-with-password"

    payload = {"identity": email, "password": password}

    response = client.post(
        url, data=payload, headers={"User-Agent": "blazedcloud-sync"}
    )

    if response.status_code != 200:
        logging.error("Failed to authenticate with email/password")
        token = None
        return None
    token = response.json().get("token")

    return token, response.json().get("record")


def refreshAuth(token):
    logging.info("Authenticating with email/password")
    backendUrl = getBackendUrl()
    url = backendUrl + "api/collections/users/auth-refresh"
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "blazedcloud-sync"}
    response = client.post(url, headers=headers)

    if response.status_code != 200:
        logging.error(f"Failed to refresh token {response.text}")
        token = None
        return None
    token = response.json().get("token")

    return token, response.json().get("record")


def getAuth():
    """
    Returns a tuple of (token, user record) from the database
    """

    logging.info("Getting user")

    query = Query()
    user = userTable.search(query.id.exists())

    if user is None or len(user) == 0:
        logging.warning("No auth record found")
        return None

    token = getSavedToken(user[0].get("id"))

    if token is None:
        logging.warning("No token found")
        return None

    return token, user[0]


def getSavedToken(uid):
    logging.info("Getting keyring")
    return kr.get_password("blazedcloud", uid)


def promptForEmailPassword():
    logging.debug("Prompting for email/password")

    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    return email, password


def promptAuthFailed():
    console.print(
        Panel.fit(
            "Failed to authenticate with email/password. Please try again.",
            title="Authentication Failed",
            style="bold red",
        )
    )


def clearSavedAuth():
    uid = getAuth()[1].get("id")

    logging.info("Clearing saved auth")
    userTable.truncate()
    logging.info("Cleared saved auth")

    # clear keyring
    kr.delete_password("blazedcloud", uid)
    logging.info("Cleared keyring")
