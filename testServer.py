"""
Get and set access to master volume example.
"""
from __future__ import print_function
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, ISimpleAudioVolume

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


def vlcSockSend(command, recv=True):
    global vlc_sock
    print("sending vlc command %s" % command)
    vlc_sock.sendall(command.encode())
    if recv:
        vlcSockRecv(2048)
    
def vlcSockRecv(bytes):
    global vlc_sock
    try:
        value = vlc_sock.recv(bytes)
        value = value.decode()
    except Exception:
        value = ""
        
    return value

def handleCommand(args):
    if "youtube" in args:
        print("play youtube vid\n")
        playFromYoutube(args["youtube"][0])
    elif "youtubePlaylist" in args:
        playFromYoutube(args["youtubePlaylist"][0], queryType = "playlist")
    elif "stop" in args:
        vlcSockSend("pause\n")
    elif "resume" in args:
        vlcSockSend("pause\n")
    elif "fullscreen" in args:
        vlcSockSend("f\n")
    elif "next" in args:
        vlcSockSend("next\n")
    elif "prev" in args:
        vlcSockSend("prev\n")
    elif "volume" in args:
        vlcSockSend("volume %s\n" % args["volume"][0])
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
    elif "forwardSecs" in args:
        fastForward(int(args["forwardSecs"][0]))
    elif "rewindSecs" in args:
        rewind(int(args["rewindSecs"][0]))
    elif "volumeUp" in args:
        vlcSockSend("volup %s\n" % args["volumeUp"][0])
    elif "volumeDown" in args:
        vlcSockSend("voldown %s\n" % args["volumeDown"][0])
    elif "open" in args:
        openVLC()
    elif "close" in args:
        closeVLC()
    elif "connect" in args:
        connectVLC()
    elif "windowsVolume" in args:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        print("volume.GetMute(): %s" % volume.GetMute())
        print("volume.GetMasterVolumeLevelScalar(): %s" % volume.GetMasterVolumeLevelScalar())
        volume.SetMasterVolumeLevelScalar(float(args["windowsVolume"][0]), None)
        print("volume.GetMasterVolumeLevelScalar(): %s" % volume.GetMasterVolumeLevelScalar())
    elif "windowsVolumeUp" in args:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        print("volume.GetMasterVolumeLevelScalar(): %s" % volume.GetMasterVolumeLevelScalar())
        volume.SetMasterVolumeLevelScalar(float(volume.GetMasterVolumeLevelScalar()) + float(args["windowsVolumeUp"][0]), None)
        print("volume.GetMasterVolumeLevelScalar(): %s" % volume.GetMasterVolumeLevelScalar())
    elif "windowsVolumeDown" in args:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        print("volume.GetMasterVolumeLevelScalar(): %s" % volume.GetMasterVolumeLevelScalar())
        volume.SetMasterVolumeLevelScalar(float(volume.GetMasterVolumeLevelScalar()) - float(args["windowsVolumeDown"][0]), None)
        print("volume.GetMasterVolumeLevelScalar(): %s" % volume.GetMasterVolumeLevelScalar())
    
        
def playLatest(showName):
    show = library.find_show(showName)
    episodeList = library.list_episode_paths(show)
    if not len(episodeList) == 0:
        vlcSockSend("clear\nrandom off\n")
        for mediaPath in episodeList:
            vlcSockSend("add %s\n" % mediaPath)

def playMovie(movieQuery):
    """
    Play a movie from the local library
    :param movieQuery:
    :return: None
    """
    movie = library.find_movie_path(movieQuery)
    if movie is not None:
        vlcSockSend("clear\nrandom off\n")
        vlcSockSend("add %s\n" % movie)

def getTime():
    vlcSockSend("get_time\n", False)
    result = vlcSockRecv(100)
    
    while len(result) == 0 or len(result) > 5:
        result = vlcSockRecv(100)
    
    try:
        time = int(result)
    except Exception:
        time = 0
        
    return time
    
def fastForward(seconds):
    time = getTime()
    time += seconds
    vlcSockSend("seek %d\n" % time)
        
def rewind(seconds):
    time = getTime()
    time -= seconds
    vlcSockSend("seek %d\n" % time)               

def connectVLC():
    global vlc_sock
    # init socket to VLC
    vlc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    vlc_sock.connect((config["VLC"]["host"], int(config["VLC"]["port"])))
    vlc_sock.setblocking(0)
    
def openVLC():
    global vlc_sock
    try:
        vlc_sock.close()
    except Exception:
        pass
        
    # open VLC
    host_port = "%s:%s" % (config["VLC"]["host"], config["VLC"]["port"])
    vlc = Popen([config["VLC"]["path"], "-I", "qt", "--extraintf", "rc", "--rc-host", host_port], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    connectVLC()
    
def closeVLC():
    global vlc_sock
    try:
        vlcSockSend("quit\n")
        vlc_sock.close()
    except Exception as e:
        print(e)
    
def shuffleFromLibrary(showName):
    show = library.find_show(showName)
    episodeList = library.list_episode_paths(show)
    print(episodeList)
    if not len(episodeList) == 0:
        vlcSockSend("clear\nrandom on\n")
        random.shuffle(episodeList, random.random)
        for mediaPath in episodeList:
            vlcSockSend("add %s\n" % mediaPath)
        

def playFromLibrary(showName, seasonNum, episodeNum):
    show = library.find_show(showName)
    index, episodeList = library.index_search(show, int(seasonNum), int(episodeNum))
    print(index, episodeList)
    if not len(episodeList) == 0:
        vlcSockSend("clear \nrandom off\n")
        vlcSockSend("add %s\n")
        truncatedList = episodeList[index + 1:]
        for mediaPath in truncatedList:
            vlcSockSend("enqueue %s\n" % mediaPath)

def playFromYoutube(query, queryType = "video"):
    print(query, queryType)

    response = youtube.search().list(q=urllib.parse.unquote(query), part="id,snippet", maxResults=5, type=queryType).execute()

    results = response.get("items", [])

    if queryType == "video" and not len(results) == 0:
        playYoutubeVideos([results[0]["id"]["videoId"]])
    elif queryType == "playlist" and not len(results) == 0:
        playYoutubePlaylist(results[0]["id"]["playlistId"])


def playYoutubeVideos(videoIds):
    vlcSockSend("clear\nrandom off\n")

    if not len(videoIds) == 0:
        videoUrl = "http://youtube.com/watch?v=%s" % videoIds[0]
        vlcSockSend("add %s \n" % videoUrl)

    for videoId in videoIds[1:]:
        videoUrl = "http://youtube.com/watch?v=%s" % videoId
        vlcSockSend("enqueue %s \n" % videoUrl)

def playYoutubePlaylist(playlistId):
    response = youtube.playlistItems().list(part="id,snippet", playlistId=playlistId, maxResults = 50).execute()

    results = response.get("items", [])

    videoIds = map(lambda result: result["snippet"]["resourceId"]["videoId"], results)

    playYoutubeVideos(videoIds)

# MAIN
global vlc
global vlc_sock

# read config file
config = configparser.ConfigParser()
config.read("config")

# init youtube api
youtube = build("youtube", "v3", developerKey = config["GOOGLE"]["developer_key"])

# init library
pathPrefix = [config["LIBRARY"]["path1"],config["LIBRARY"]["path2"]]
library = MediaLibrary(pathPrefix)

# init server
httpd = socketserver.TCPServer(("", int(config["SERVER"]["port"])), MyHandler)
httpd.serve_forever()

# Lans' test interface (comment out init server lines)
#while 1:
#    cmd = input(">")
#    args = cmd.split(" ")
#    argdict = dict()
#    argdict[args[0]] = [args[1]]
#    handleCommand(argdict)
