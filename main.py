#!/usr/bin/env python3

import json
import click
import requests

from datetime import datetime

def save_result(result):
    json_object = json.dumps(result, indent=2)

    with open("result.json", "w") as outfile:
        outfile.write(json_object)


class VK:
    API_BASE_URL = 'https://api.vk.com/method'
    now = datetime.now()

    def __init__(self, vk_token, vk_id, yandex_token, deep, ttype):
        self.vk_id = vk_id
        self.vk_token = vk_token
        self.yandex_token = yandex_token
        self.version = '5.199'
        self.params = {'access_token': self.vk_token, 'user_ids': self.vk_id, 'v': self.version}

        self.deep = deep
        self.ttype = ttype
        self.yandex_folder = self.now.strftime("%Y-%m-%d-%H%M%S")

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

    def download_photo(self, url, filename):
        response = requests.get(url, params={**self.params})

        with open(filename, mode="wb") as file:
            file.write(response.content)


@click.command(help='Backup photo to Yandex disk')
@click.option("--vk-id", required=True, help='VK user ID.')
@click.option("--vk-token", required=True, help='VK token.')
@click.option("--yandex-token", required=False, default='', help='Yandex token.')
@click.option("--deep", required=True, default=5, help='Count last photos.')
@click.option("--ttype", required=True, default='profile', help='Backup type wall, profile or album photos.')

def backup_photo(vk_id: str, vk_token: str, yandex_token: str, deep: int, ttype: str):
    vk = VK(vk_token, vk_id, yandex_token, deep, ttype)

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


if __name__ == '__main__':
    backup_photo()
