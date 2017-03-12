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
import time
import urllib
from findInLibrary import MediaLibrary
from subprocess import Popen, PIPE, STDOUT, DEVNULL, check_output
from http.server import BaseHTTPRequestHandler
from apiclient.discovery import build
import random
import socket
import configparser
import webbrowser
        
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
        pause()
    elif "resume" in args:
        pause()
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
        print("volume.GetMute(): %s" % volume.GetMute())
        setWindowsVolume(float(args["windowsVolume"][0]))
    elif "windowsVolumeUp" in args:
        setWindowsVolume(float(args["windowsVolumeUp"][0]), False)
    elif "windowsVolumeDown" in args:
        setWindowsVolume(-1 * float(args["windowsVolumeDown"][0]), False)
    elif "sleep" in args:
        windowsCMD("%windir%/System32/rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    elif "hibernate" in args:
        windowsCMD("%windir%/System32/rundll32.exe powrprof.dll,SetSuspendState Hibernate")
    elif "search" in args:
        query =  args["search"][0]
        print("googling %s\n" % query)
        #googleSearch(query) # this is to get a string of results from google api
        webbrowser.open('https://www.google.com/search?q=%s' % query) # this opens google search in default browser
    elif "imageSearch" in args:
        query =  args["imageSearch"][0]
        print("searching google images for %s\n" % query)
        webbrowser.open('https://www.google.com/images?q=%s' % query) # this opens google search in default browser
    
def windowsCMD(cmd):
    print(check_output(cmd, shell=True).decode())

def setWindowsVolume(vol, absolute=True):
    if not absolute:
        newVol = float(volume.GetMasterVolumeLevelScalar()) + vol
    else:
        newVol = vol
    print("volume.GetMasterVolumeLevelScalar(): %s" % volume.GetMasterVolumeLevelScalar())
    volume.SetMasterVolumeLevelScalar(newVol, None)
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

def pause():
    vlcSockSend("pause\n")
    
def getTime():
    time = -1
    pause()
    pause()
    vlcSockSend("get_time\n", False)
    result = vlcSockRecv(100)
    
    # keep trying to receive output until we get the time
    while 1:
        if result != "":
            # output may have multiple lines - split the string into lines
            lines = result.split("\n")
            for line in lines:
                # get rid of the white space at the start and end of line
                line = line.strip()
                # if it is a time, it should be between 1 and 5 characters
                if len(line) > 0 and len(line) <= 5:
                    try:
                        # check if the value is an integer by trying to cast
                        time = int(line)
                        # if we get here, the conversion succeeded, break out of for loop
                        break
                    except Exception:
                        # exception thrown during conversion - not an int, try to
                        # receive output again
                        pass
            if time != -1:
                # got the time value, break out of while 1 loop
                break
                
        # still haven't broken out of while 1 loop, try to receive output again
        result = vlcSockRecv(100)
        
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
    try:
        vlc_sock.close()
    except Exception:
        pass
        
    vlc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    vlc_sock.connect((config["VLC"]["host"], int(config["VLC"]["port"])))
    vlc_sock.setblocking(0)
    
def googleSearch(query):
    res = customSearch.cse().list(
      q=query,
      cx=config["GOOGLE"]["search_engine_id"],
      num=1,
      safe='off',
    ).execute()
    print(res)

def openVLC():
    global vlc_sock
    
    retries = 3
    try:
        vlc_sock.close()
    except Exception:
        pass
        
    # open VLC
    host_port = "%s:%s" % (config["VLC"]["host"], config["VLC"]["port"])
    vlc = Popen([config["VLC"]["path"], "-I", "qt", "--extraintf", "rc", "--rc-host", host_port, "--rc-quiet"], stdout=DEVNULL, stderr=STDOUT)

    while retries > 0:
        try:
            connectVLC()
            break
        except Exception as e:
            retries -= 1
            if retries > 0:
                time.sleep(1)
            else:
                print("Could not connect to VLC (%s).  Try again later with connect command.\n" % e)
    
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

# init google apis
youtube = build("youtube", "v3", developerKey = config["GOOGLE"]["developer_key"])
#customSearch = build("customsearch", "v1", developerKey = config["GOOGLE"]["developer_key"])

# init library
pathPrefix = [config["LIBRARY"]["path1"],config["LIBRARY"]["path2"]]
library = MediaLibrary(pathPrefix)

# init windows volume interface
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
        
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
