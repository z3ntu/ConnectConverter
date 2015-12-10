#!/usr/bin/python3

import http.cookiejar
import http.cookiejar
import json
import os
import subprocess
import sys
import re
import zipfile

import requests
from mutagen.id3 import ID3
from mutagen.id3 import ID3NoHeaderError

import config

DATA_PATH = os.path.expanduser('~/.monstercatconnect/')
COOKIE_FILE = DATA_PATH + "connect.cookies"
TMP_PATH = DATA_PATH + "tmp/"
EXTRACT_PATH = TMP_PATH + "extracted/"
DOWNLOAD_PATH = TMP_PATH + "downloads/"
SIGNIN_URL = "https://connect.monstercat.com/signin"
COVER_ART = "https://connect.monstercat.com/img/labels/monstercat/albums/{0}"
DOWNLOAD_URL = "https://connect.monstercat.com/album/{0}/download{1}"
ALBUM_INFO_URL = "https://connect.monstercat.com/album/{0}"

# filename = os.path.expanduser("~") + "/Documents/Tristam - The Vine - 1 The Vine.wav"

to = ["FLAC", "MP3_320"]


def main():
    album_id = input("Please enter the album ID: ")

    create_directories()

    session = requests.Session()
    cj, successful = load_cookies(COOKIE_FILE)
    session.cookies = cj
    session.headers = {'user-agent': 'github.com/z3ntu/MonstercatConnectNotifier'}
    if not successful:
        # SIGN IN
        print("Logging in.")
        sign_in(session)
        save_cookies(session.cookies, COOKIE_FILE)

    ret = get_album_info(album_id, session)
    if ret.get("error", ".") != ".":
        print(ret.get("message", "Unknown error."))
        exit("Ending the program.")
    if ret['type'] == "Single":
        print("single")
        title = ret['title']
        artist = ret['renderedArtists']
        cover = ret['coverArt']
        catalog = ret['catalogId']
    answer = input("We will now download '" + title + "' by '" + artist + "'. Ok? [Y/n]")
    if answer in ['N', 'n']:
        exit("Bye.")

    download_album_zip(album_id, DOWNLOAD_PATH, session)


    # try:
    #     tags = ID3(filename)
    # except ID3NoHeaderError:
    #     print("Adding ID3 header;")
    #     tags = ID3()

    # print(tags)
    # convert(filename, to)
    # tags.save(fname)


def convert(filename, to):
    """
    converts an audio file into the specified qualities
    :param filename: the filename to convert
    :param to: array of needed quality
    :return: list of new file names
    """
    if "MP3_320" in to:
        print("Converting to MP3 with LAME...")
        if subprocess.call("lame --silent -h -b 320 \"" + filename + "\"", shell=True) != 0:
            print("ERROR!")
            exit(1)
    if "FLAC" in to:
        print("Converting to FLAC with FLAC...")
        if subprocess.call("flac --totally-silent --best \"" + filename + "\"", shell=True) != 0:
            print("ERROR!")
            exit(1)


def get_album_info(album_id, session):
    # GET ALBUM LIST
    print("Getting album info...")
    album_info_raw = session.get(ALBUM_INFO_URL.format(album_id))

    # PARSE RESPONSE INTO JSON
    album_info = json.loads(album_info_raw.text)
    # try:
    #     if albums['error']:
    #         global REMOVED_COOKIE_FILE
    #         if not REMOVED_COOKIE_FILE:
    #             print("Fatal error! Maybe because of expired cookies, deleting cookie file and retrying.")
    #             os.remove(COOKIE_FILE)
    #             REMOVED_COOKIE_FILE = True
    #             main()
    #             sys.exit(0)
    #         else:
    #             raise Exception("FATAL ERRROR! : " + str(albums))
    # except TypeError:
    #     pass
    return album_info


def save_cookies(cj, filename):
    print("Saving cookies")
    cj.save(filename=filename)


def load_cookies(filename):
    print("Loading cookies")
    cj = http.cookiejar.MozillaCookieJar()
    if not os.path.isfile(filename):
        return cj, False
    cj.load(filename=filename)
    return cj, True


def extract_zip(file, extractpath):
    with zipfile.ZipFile(file, "r") as z:
        z.extractall(path=extractpath)


def download_album_zip(albumid, path, session):
    count = 0
    chunksize = 8192
    lastvalue = 0

    r = session.get(DOWNLOAD_URL.format(albumid, "?format=wav"), stream=True)
    filename = str.replace(re.findall("filename=(.+)", r.headers['content-disposition'])[0], "\"", "")
    fullpath = path + filename
    print("Downloading " + filename + " ... Total size: " + str(int(r.headers['Content-Length'])/1000000) + "MB")
    diff = (40 / int(r.headers['Content-Length']))  # 40 was 100 for percent

    # stdout progressbar
    toolbar_width = 40
    sys.stdout.write("[{0}]".format(" " * toolbar_width))
    sys.stdout.flush()
    sys.stdout.write("\b" * (toolbar_width+1))  # return to start of line, after '['

    with open(fullpath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=chunksize):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                percentvalue = round(count * chunksize * diff, 0)
                # print(percentvalue)
                if percentvalue != lastvalue:
                    sys.stdout.write("-")
                    sys.stdout.flush()
                    lastvalue = percentvalue
                count += 1
    return fullpath


def sign_in(session):
    print("Signing in...")
    payload = {"email": config.connect['email'], "password": config.connect['password']}
    response_raw = session.post(SIGNIN_URL, data=payload)
    response = json.loads(response_raw.text)
    if len(response) > 0:
        print("Sign in failed")
        raise Exception("Sign-In Error: " + response.get("message", "Unknown error"))


def create_directories():
    os.makedirs(DATA_PATH, exist_ok=True)
    os.makedirs(TMP_PATH, exist_ok=True)
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    os.makedirs(EXTRACT_PATH, exist_ok=True)

if __name__ == '__main__':
    # if len(sys.argv) > 1:
    #     filename = sys.argv[1]
    # else:
    #     exit("Please enter your filename as program argument!")
    main()
