import os
import json

import jwt
from datetime import datetime
import urllib
import requests

BASE_API_URL = "https://www.worksapis.com/v1.0"
BASE_AUTH_URL = "https://auth.worksmobile.com/oauth2/v2.0"


def get_jwt(client_id, service_account_id, privatekey):
    """アクセストークンのためのJWT取得
    """
    current_time = datetime.now().timestamp()
    iss = client_id
    sub = service_account_id
    iat = current_time
    exp = current_time + (60 * 60) # 1時間

    jws = jwt.encode(
        {
            "iss": iss,
            "sub": sub,
            "iat": iat,
            "exp": exp
        }, privatekey, algorithm="RS256")

    return jws


def get_access_token(client_id, client_secret, scope, jws):
    """アクセストークン取得"""
    url = '{}/token'.format(BASE_AUTH_URL)

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    params = {
        "assertion": jws,
        "grant_type": urllib.parse.quote("urn:ietf:params:oauth:grant-type:jwt-bearer"),
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
    }

    form_data = params

    r = requests.post(url=url, data=form_data, headers=headers)

    body = json.loads(r.text)

    return body


def refresh_access_token(client_id, client_secret, refresh_token):
    """アクセストークン更新"""
    url = '{}/token'.format(BASE_AUTH_URL)

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    params = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    form_data = params

    r = requests.post(url=url, data=form_data, headers=headers)

    body = json.loads(r.text)

    return body


def send_message(content, bot_id, user_id, access_token):
    """メッセージ送信"""
    url = "{}/bots/{}/users/{}/messages".format(BASE_API_URL, bot_id, user_id)

    headers = {
          'Content-Type' : 'application/json',
          'Authorization' : "Bearer {}".format(access_token)
        }

    params = content
    form_data = json.dumps(params)

    r = requests.post(url=url, data=form_data, headers=headers)

    r.raise_for_status()


def main():
    client_id = os.environ.get("ceUD6hrra7u8LE0yeVd9")
    client_secret = os.environ.get("HfJ93E6PrU")
    service_account_id = os.environ.get("hy8w3.serviceaccount@sunlife-1979")
    privatekey = os.environ.get("-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQChspaMokqhYOR+
L0jefo9EzigkwdX19nMTBAVaFh44YNaIQDRx7toidwABIde6QIriVbrp/kDjpNBd
oTVJq33QZD52JBDkIzotHU0fdvEPSnGsLvtu794iFKrDtcVTVPzAPCu2S8M5pR7i
5KOtkG4eZ9uiF8qR2fnKnuGuH16HIasTyJv/nJgFWFSHinQOC/e89gZKrYMeFRUx
/qnUHCChQi1pl0UzIkH1oAXuOzHZq9Q7AjbSCf6dJ8CiqCqsOXs74Gs86w6qm7iQ
6LvGyOtwBvAKv5rdHHpDrO1fBCb3s62AB8STOTUbkyM44nb0o1ZgZKzbV+eli3O6
WbayzXTDAgMBAAECggEAAI+G198ML1CXGjqNCXvAYpiDOGoc0WU2typ1Kv+tsWGl
C9dOj7dGl6SWkwEE3A6kLKMzG1wBj5eQLHLvhyEZgTmHwXE6dB4q6njGxb1VTuA0
rJOiEVA6TuMeolb3xYnnInLLbpgWL2EKqKsXz17IERTsKlOJu5+c3CukCQjRC56L
QvY8Aq2hJ/TBcyl5IuX2mQCMyO5z7hkdybC664jFRqjdwSTHXxGYbeUDCABCLFCV
Dpo2N2yElqXOWlAyjl6aFyJuTjnKj+O4HLM7Z1pSHKx1hNxcsgoZ8jGVUscaNH7u
OTMflAEPmCo0QYdjuFaB5upZeQoD1Klvmet7IKg9AQKBgQC6tRAc7MzEJcX60vFq
nIXOfpcZ8ZurpD6XzuEXiqppdvTb+DOY0mNZV3ItRKIFZrDD0OQoTixlaslK7fVW
I9rYD/f0FwtuEPCiwU7lp9nkOYpiwkZvyhVoEwjQsIrzekAZ9Bq7wr2+YjP/Jq0K
SLdATsySneHuY3G/AUIRmVbsQwKBgQDdtV92BtMx+rWL1PU2nle+Y7aSrDxHHbyj
+aB+1kjXjOI5PkqBzkLBKl9u8qHshAXHT06BTp5t71LLuNmc0uCrr5hhM65c5p84
mBOn3ky9df4GVDRZm3DalrJOxbfpY6b8keWp56+KSM66mv2+F8B5udWxj1nSuNIJ
epLabGsNgQKBgQCRFFMB9uuiWyu9HJ7lVd0PuQRW74wkUsskkWgNL/39V6crKnGF
ha4XZUDedh9kDQi8EBzKSPxsjg7+P2vNVK0gCUCGFkYWb+lcvtM81zIUCrZCyW2M
Pj5mEaxe5WADk/IteKYxUkC4qHx4/qelfx2ORezm3PILmJBxeFvLaxjFGwKBgQCg
ZHpvNHjNi4aTZrkPjnYD8rc+XQQunsC+D/WgTP3dkrqGlx3n0oRQoorwBPBH3ysf
CazNt0a+WYkYgN5NqfGHwz0F9RGLe/xsQPjXVOdHmXjwszI8MUvvl13fxwJKAiHo
TtRLmqVP8WQ9c6tmPmCsr1h9YCunWrX4zYg4JH8+AQKBgQCIDG1vxFoNfQxP4+bM
AdKD9guOno+G4N+6x6z1AkFfWTigftQqD0PXK4D3CGV3uPf/1XoqCuXFBb6QHtlg
2oCJi+3O0ghjYwp2VOdRHpCfMmVsD1ccpBOnJXuM+tN33HEksO4mqdaKcmfTWQ4S
L3dIa1dexwhQ5FXSDs3yryKBUw==
-----END PRIVATE KEY-----")
    bot_id = os.environ.get("12419749")
    user_id = os.environ.get("su.37308@sunlife-1979")

    scope = "bot"

    # JWT生成
    jwttoken = get_jwt(client_id, service_account_id, privatekey)

    # アクセストークン取得
    res = get_access_token(client_id, client_secret, scope, jwttoken)

    access_token = res["access_token"]

    # APIリクエスト (メッセージ送信)
    content = {
        "content": {
            "type": "text",
            "text": "Hello"
        }
    }
    content = {
        "content": {
            "type": "flex",
            "altText": "this is a flexible template",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "hello"
                        },
                        {
                            "type": "text",
                            "text": "world"
                        }
                    ]
                }
            }
        }
    }
    res = send_message(content, bot_id, user_id, access_token)

    return


if __name__ == "__main__":
    main()
