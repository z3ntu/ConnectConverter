#!/usr/bin/python3

import glob
import http.cookiejar
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import zipfile
from subprocess import DEVNULL
# from mutagen

import requests

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

NAMING_FORMAT = "{0} - {1}{2}"  # 0=Artist, 1=Title, 2=File-Extension (should contain a dot);

to_default = ["FLAC", "MP3_320"]


def main():
    """
    Main method, executes everything
    :return: nothing
    """
    album_id = input("Please enter the album ID: ")
    if len(album_id) != 24:
        exit("Please enter a valid album ID!")
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

    if ret['type'] in ["Single", "EP", "Album"]:
        print("single")
        title = ret['title']
        artist = ret['renderedArtists']
        cover = ret['coverArt']
        catalog = ret['catalogId']
    else:
        exit("Unknown type (e.g. Single, EP). Ending the program.")

    answer = input("We will now download '" + title + "' by '" + artist + "'. Ok [Y/n]? ")
    if answer in ['N', 'n']:
        exit("Bye.")

    zipfilepath, success = download_album_zip(album_id, DOWNLOAD_PATH, session)
    if success is False:
        answer = input("Download was not successful. Do you still want to continue with extracting etc [Y/n]? ")
        if answer in ['y', 'Y']:
            print("Bye.")
            exit(0)
    extract_zip(zipfilepath, EXTRACT_PATH)
    dirnames = os.listdir(EXTRACT_PATH)
    if len(dirnames) != 1:
        print(dirnames)
        exit("Error while extracting...")
    files = glob.glob(EXTRACT_PATH + dirnames[0] + "/*.wav")
    for file in files:
        converted_list = convert(file, to_default)
        print(converted_list)
        for converted in converted_list:
            path, file = os.path.split(converted)

            # os.path.splitext on position 1 returns the file extension
            newfilename = path + "/" + NAMING_FORMAT.format(artist, title, os.path.splitext(converted)[1])
            os.rename(converted, newfilename)
            print("New file: " + newfilename)
            # TODO: Fill metatags

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
    converted = []
    base = os.path.splitext(filename)[0]
    if "MP3_320" in to:
        print("Converting to MP3 with LAME...")
        if subprocess.call("lame --silent -h -b 320 \"" + filename + "\"", shell=True, stdout=DEVNULL,
                           stderr=DEVNULL) != 0:  # return codes: 0=success | file exists;
            print("ERROR MP3!")
            exit(1)
        converted.append(base + ".mp3")
    if "FLAC" in to:
        print("Converting to FLAC with FLAC...")
        if subprocess.call("flac --totally-silent --best \"" + filename + "\"", shell=True, stdout=DEVNULL,
                           stderr=DEVNULL) != 0:  # return codes: 0=success; OTHER=file exists
            print("ERROR FLAC!")
            exit(1)
        converted.append(base + ".flac")
    return converted


def get_album_info(album_id, session):
    """
    Returns information about an album.
    :param album_id: release_id as int
    :param session: session reference
    :return: parsed json which contains information
    """
    # GET ALBUM LIST
    print("Getting infos about the album...")
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
    """
    Save cookies to a file
    :param cj: cookies you want to save, preferably a MozillaCookiesJar
    :param filename: where to save the cookies
    :return: nothing
    """
    print("Saving cookies")
    cj.save(filename=filename)


def load_cookies(filename):
    """
    Load cookies from a file
    :param filename: where to try to load the cookies from
    :return: a MozillaCookieJar & bool if successful
    """
    # print("Loading cookies")
    cj = http.cookiejar.MozillaCookieJar()
    if not os.path.isfile(filename):
        return cj, False
    cj.load(filename=filename)
    return cj, True


def extract_zip(file, extractpath):
    """
    Extracts all from a zip file into the specified directory
    :param file: the file to extract
    :param extractpath: where to extract
    :return: nothing
    """
    print("Extracting " + file + " into " + extractpath + " ...")
    with zipfile.ZipFile(file, "r") as z:
        z.extractall(path=extractpath)


def download_album_zip(release_id, path, session):
    """
    Downloads an album (the zip file)
    :param release_id: The ReleaseID to download
    :param path: path where to save
    :param session: session reference
    :return: the full path of the downloaded file & bool if success
    """
    count = 0
    chunksize = 8192
    lastvalue = 0

    r = session.get(DOWNLOAD_URL.format(release_id, "?format=wav"), stream=True)
    filename = str.replace(re.findall("filename=(.+)", r.headers['content-disposition'])[0], "\"", "")
    fullpath = path + filename
    if os.path.isfile(fullpath):
        answer = input("File " + fullpath + " already exists. Overwrite it [y/N]? ")
        if answer not in ['y', 'Y']:
            return fullpath, False
    print("Downloading " + filename + " ... Total size: " + str(
            round(int(r.headers['Content-Length']) / 1000000, 2)) + " MB")
    diff = (40 / int(r.headers['Content-Length']))  # 40 was 100 for percent

    # stdout progressbar
    toolbar_width = 40
    sys.stdout.write("[{0}]".format(" " * toolbar_width))
    sys.stdout.flush()
    sys.stdout.write("\b" * (toolbar_width + 1))  # return to start of line, after '['

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
    return fullpath, True


def sign_in(session):
    """
    Signs you into Monstercat Connect
    :param session: the session to use
    :return: nothing
    """
    print("Signing in...")
    payload = {"email": config.connect['email'], "password": config.connect['password']}
    response_raw = session.post(SIGNIN_URL, data=payload)
    response = json.loads(response_raw.text)
    if len(response) > 0:
        print("Sign in failed")
        raise Exception("Sign-In Error: " + response.get("message", "Unknown error"))


def create_directories():
    """
    Creates necessary directories.
    :return:
    """
    os.makedirs(DATA_PATH, exist_ok=True)
    os.makedirs(TMP_PATH, exist_ok=True)
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    os.makedirs(EXTRACT_PATH, exist_ok=True)


if __name__ == '__main__':
    main()
