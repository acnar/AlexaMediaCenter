import socketserver
from urllib.parse import urlparse
import os
import urllib
from findInLibrary import MediaLibrary
from subprocess import Popen, PIPE, STDOUT
from http.server import BaseHTTPRequestHandler
from apiclient.discovery import build
import random
import socket
import subprocess
import configparser
        
class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("done", "utf-8"))
        args = urllib.parse.parse_qs(parsed.query)
        print(self.path)

        handleCommand(args)


def vlc_sock_send(command):
    print("sending vlc command %s" % command)
    vlc_sock.sendall(command.encode())

def handleCommand(args):
    if "youtube" in args:
        print("play youtube vid\n")
        playFromYoutube(args["youtube"][0])
    elif "youtubePlaylist" in args:
        playFromYoutube(args["youtubePlaylist"][0], queryType = "playlist")
    elif "stop" in args:
        vlc_sock_send("pause\n")
    elif "resume" in args:
        vlc_sock_send("pause\n")
    elif "fullscreen" in args:
        vlc_sock_send("f\n")
    elif "next" in args:
        vlc_sock_send("next\n")
    elif "prev" in args:
        vlc_sock_send("prev\n")
    elif "volume" in args:
        vlc_sock_send("volume %s\n" % args["volume"][0])
    elif "plex" in args:
        showName = args["plex"][0]
        seasonNum = args["seasonNum"][0]
        episodeNum = args["episodeNum"][0]
        playFromLibrary(showName, seasonNum, episodeNum)
    elif "plexShuffle" in args:
        showName = args["plexShuffle"][0]
        shuffleFromLibrary(showName)
    elif "plexLatest" in args:
        playLatest(args["plexLatest"][0])
    elif "movie" in args:
        playMovie(args["movie"][0])
    elif "sec" in args:
        fastForward(args["sec"][0])

def playLatest(showName):
    show = library.find_show(showName)
    episodeList = library.list_episode_paths(show)
    if not len(episodeList) == 0:
        vlc_sock_send("clear\nrandom off\n")
        for mediaPath in episodeList:
            vlc_sock_send("add %s\n" % mediaPath)

def playMovie(movieQuery):
    """
    Play a movie from the local library
    :param movieQuery:
    :return: None
    """
    movie = library.find_movie_path(movieQuery)
    if movie is not None:
        message = "clear\nrandom off\n"
        vlc_sock.sendall(message.encode())
        message = "add %s\n" % movie
        vlc_sock.sendall(message.encode())

def fastForward(seconds):
    if seconds is not None:
        vlc_sock_send("seek %d")

def shuffleFromLibrary(showName):
    show = library.find_show(showName)
    episodeList = library.list_episode_paths(show)
    print(episodeList)
    if not len(episodeList) == 0:
        vlc_sock_send("clear\nrandom on\n")
        random.shuffle(episodeList, random.random)
        for mediaPath in episodeList:
            vlc_sock_send("add %s\n" % mediaPath)
        

def playFromLibrary(showName, seasonNum, episodeNum):
    show = library.find_show(showName)
    index, episodeList = library.index_search(show, int(seasonNum), int(episodeNum))
    print(index, episodeList)
    if not len(episodeList) == 0:
        vlc_sock_send("clear \nrandom off\n")
        vlc_sock_send("add %s\n")
        truncatedList = episodeList[index + 1:]
        for mediaPath in truncatedList:
            vlc_sock_send("enqueue %s\n" % mediaPath)


def playFromYoutube(query, queryType = "video"):
    print(query, queryType)

    response = youtube.search().list(q=urllib.parse.unquote(query), part="id,snippet", maxResults=5, type=queryType).execute()

    results = response.get("items", [])

    if queryType == "video" and not len(results) == 0:
        playYoutubeVideos([results[0]["id"]["videoId"]])
    elif queryType == "playlist" and not len(results) == 0:
        playYoutubePlaylist(results[0]["id"]["playlistId"])


def playYoutubeVideos(videoIds):
    message = "clear\nrandom off\n"
    vlc_sock.sendall(message.encode())

    if not len(videoIds) == 0:
        videoUrl = "http://youtube.com/watch?v=%s" % videoIds[0]
        vlc_sock_send("add %s \n" % videoUrl)

    for videoId in videoIds[1:]:
        videoUrl = "http://youtube.com/watch?v=%s" % videoId
        vlc_sock_send("enqueue %s \n" % videoUrl)

def playYoutubePlaylist(playlistId):
    response = youtube.playlistItems().list(part="id,snippet", playlistId=playlistId, maxResults = 50).execute()

    results = response.get("items", [])

    videoIds = map(lambda result: result["snippet"]["resourceId"]["videoId"], results)

    playYoutubeVideos(videoIds)

# MAIN

# read config file
config = configparser.ConfigParser()
config.read("config")

# open VLC
print(config["VLC"]["path"])
host_port = "%s:%s" % (config["VLC"]["host"], config["VLC"]["port"])
print(host_port)

vlc = Popen([config["VLC"]["path"], "-I", "qt", "--extraintf", "rc", "--rc-host", host_port])

# init youtube api
youtube = build("youtube", "v3", developerKey = config["GOOGLE"]["developer_key"])

# init library
pathPrefix = [config["LIBRARY"]["path1"],config["LIBRARY"]["path2"]]
library = MediaLibrary(pathPrefix)

# init socket to VLC
vlc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
vlc_sock.connect((config["VLC"]["host"], int(config["VLC"]["port"])))

# init server
httpd = socketserver.TCPServer(("", int(config["SERVER"]["port"])), MyHandler)
httpd.serve_forever()