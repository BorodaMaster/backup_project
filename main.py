#!/usr/bin/env python3

import json
import click
import os.path
import requests

from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly", "https://www.googleapis.com/auth/drive.file"]


def save_result(result):
    json_object = json.dumps(result, indent=2)

    with open("result.json", "w") as outfile:
        outfile.write(json_object)


def connect_to_google_api():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def list_files(service, folder_id):
    try:
        items = []
        page_token = None

        while True:
            results = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents",
                    spaces="drive",
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token)
                .execute()
            )
            items.extend(results.get("files", []))
            page_token = results.get("nextPageToken", None)
            if page_token is None:
                break

    except HttpError as error:
        print(f"An error occurred: {error}")
        items = None

    return items


def upload_file_google(service, name, folder_id):
    file_metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(f"tmp/{name}", mimetype="image/jpeg")

    try:
        results = service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        item_id = results.get("id")

        return item_id

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def create_folder_google(service, name):
    file_metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}

    try:
        results = service.files().create(body=file_metadata, fields="id").execute()

        item_id = results.get("id")

        return item_id

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


class VK:
    API_BASE_URL = 'https://api.vk.com/method'
    now = datetime.now()

    def __init__(self, vk_token, vk_id, target_endpoint, deep, ttype):
        self.vk_id = vk_id
        self.vk_token = vk_token
        self.target_endpoint = target_endpoint
        self.version = '5.199'
        self.params = {'access_token': self.vk_token, 'user_ids': self.vk_id, 'v': self.version}

        self.deep = deep
        self.ttype = ttype
        self.target_folder = self.now.strftime("%Y-%m-%d-%H%M%S")
        self.folder_id = ""

    def users_info(self):
        url = f'{self.API_BASE_URL}/users.get'
        response = requests.get(url, params={**self.params})

        return response.json()

    def get_status(self):
        url = f'{self.API_BASE_URL}/status.get'
        response = requests.get(url, params={**self.params})

        return response.json()

    def get_albums(self):
        url = f'{self.API_BASE_URL}/photos.getAlbums'
        response = requests.get(url, params={**self.params})

        return response.json()

    def get_photos(self):
        url = f'{self.API_BASE_URL}/photos.get'
        params = {'album_id': self.ttype, 'extended': "1"}
        response = requests.get(url, params={**self.params, **params})

        return response.json()

    # Save photos to local or Google disk
    def download_photo(self, url, filename):
        response = requests.get(url, params={**self.params})

        # if local of Google_disk
        if self.target_endpoint == "local":
            is_exist = os.path.exists(self.target_folder)
            if not is_exist:
                os.makedirs(self.target_folder)
            with open(f"{self.target_folder}/{filename}", mode="wb") as file:
                file.write(response.content)
        elif self.target_endpoint == "google":
            creds = connect_to_google_api()

            try:
                service = build("drive", "v3", credentials=creds)
                if not self.folder_id:
                    folder_id = create_folder_google(service, self.target_folder)
                    self.folder_id = folder_id

                # download file to tmp folder
                is_exist = os.path.exists("tmp")
                if not is_exist:
                    os.makedirs("tmp")
                with open(f"tmp/{filename}", mode="wb") as file:
                    file.write(response.content)

                upload_file_google(service, filename, self.folder_id)
            except HttpError as error:
                print(f"An error occurred: {error}")

    def list_photo_google(self):
        creds = connect_to_google_api()

        try:
            service = build("drive", "v3", credentials=creds)
            items = list_files(service, self.folder_id)
            if not items:
                print("No files found.")
                return

            print("Files:")
            for item in items:
                print(f"{item['name']} ({item['id']})")
        except HttpError as error:
            print(f"An error occurred: {error}")


@click.command(help='Backup photo to local or Google disk')
@click.option("--vk-id", required=True, help='VK user ID.')
@click.option("--vk-token", required=True, help='VK token.')
@click.option("--target_endpoint", required=False, default='local', help='Save photos to local or Google disk')
@click.option("--deep", required=True, default=5, help='Count last photos.')
@click.option("--ttype", required=True, default='profile', help='Backup type wall, profile or album photos.')
def backup_photo(vk_id: str, vk_token: str, target_endpoint: str, deep: int, ttype: str):
    vk = VK(vk_token, vk_id, target_endpoint, deep, ttype)

    photos = vk.get_photos()

    photo_size = ''
    result_output, all_photos, all_photos_sorted = [], [], []

    if photos.get('error'):
        print(photos.get('error', {}).get("error_msg"))
    elif photos:
        for photo in photos['response']['items']:
            sizes = [size['type'] for size in photo['sizes']]

            if sizes.count('z') == 1:
                photo_size = 'z'
            elif sizes.count('y') == 1:
                photo_size = 'y'
            else:
                print("Not supported size ...")

            if photo_size == 'z' or photo_size == 'y':
                metadata = [size for size in photo['sizes'] if size['type'] == photo_size][0]
                metadata.update({'date': photo['date'], 'likes': photo['likes']['count']})

                all_photos.append(metadata)

        all_photos_sorted = sorted(all_photos, key=lambda x: x['date'], reverse=True)

    if all_photos_sorted:
        for item in all_photos_sorted[:deep]:
            url = item['url']
            filename = f"{item['date']}_{item['likes']}.jpg"

            vk.download_photo(url, filename)
            file_inf = {"file_name": filename, "size": photo_size}
            result_output.append(file_inf)

    if result_output:
        save_result(result_output)

    vk.list_photo_google()


if __name__ == '__main__':
    backup_photo()
