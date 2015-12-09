#!/usr/bin/python3

from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TPE2, COMM, USLT, TCOM, TCON, TDRC
import os
import sys
import subprocess

filename = os.path.expanduser("~") + "/Documents/Tristam - The Vine - 1 The Vine.wav"

to = ["FLAC", "MP3_320"]


def main():
    print("hi")
    try:
        tags = ID3(filename)
    except ID3NoHeaderError:
        print("Adding ID3 header;")
        tags = ID3()

    print(tags)
    convert(filename, to)
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

if __name__ == '__main__':
    # if len(sys.argv) > 1:
    #     filename = sys.argv[1]
    # else:
    #     exit("Please enter your filename as program argument!")
    main()
