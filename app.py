from ytmusicapi import YTMusic
from ytmusicapi.parsers._utils import (nav, NAVIGATION_BROWSE_ID, SECTION_LIST, SINGLE_COLUMN_TAB, TITLE_TEXT)
from flask import Flask, jsonify, make_response, request,send_from_directory
import requests
import json
import time
import re
import os
from flask_restful import Resource, Api
from pytube import YouTube
# import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import billboard
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

ytmusic = YTMusic()

app = Flask(__name__)
#Spotify Config
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(
    client_id='721d6f670f074b1497e74fc59125a6f3', client_secret='efddc083fa974d39bc6369a892c07ced',))

def convert_to_json(data: list[dict]):
    with open("myjson.json", "w") as f:
        json.dump(data, f, indent= 4)
    return send_from_directory('', 'myjson.json')

def find_track_id(search_query):
    results = spotify.search(q='track:' + search_query, type='track')
    track_id = results['tracks']['items'][0]['id']
    return track_id

@app.route('/', methods=['GET'])
def info():
    return """YTMusic API from maxrave
    Thanks to @ytmusicapi, @spotipy, @billboard.py, @pytube"""

#SEARCH
@app.route('/search/', methods=['GET'])
#q = query, f = filter
def search():
    query = request.args.get('q')
    filter = request.args.get('f')
    if (filter != None):
        result = ytmusic.search(query, filter, limit=20)
        print (len(result))
        a = convert_to_json(result)
        return a
    else:
        result = ytmusic.search(query, limit=20)
        print (len(result))
        a = convert_to_json(result)
        return a
@app.route("/query/", methods=['GET'])
def query():
    query = request.args.get('q')
    url = "http://suggestqueries.google.com/complete/search"
    PARAMS = {'client': 'firefox', 'ds': 'yt', 'q': query}
    r = requests.get(url=url, params=PARAMS)
    result = r.json()
    return result[1]

@app.route('/home')
def get_home():
    data = ytmusic.get_home(limit=20)
    return convert_to_json(data)

@app.route('/browse/artists/')
def browse_artists():
    channelId = request.args.get('channelId')
    params = request.args.get('params')
    if params == None:
        data = ytmusic.get_artist(channelId)
        return convert_to_json(data)
    else:
        data = ytmusic.get_artist_albums(channelId, params)
        return convert_to_json(data)
    
@app.route('/browse/albums/')
def get_albums():
    browseId = request.args.get('browseId')
    audioPlaylistId = request.args.get('audioPlaylistId')
    if audioPlaylistId == None:
        data = ytmusic.get_album(browseId)
        return convert_to_json(data)
    if browseId == None:
        data = ytmusic.get_album_browse_id(audioPlaylistId)
        return convert_to_json(data)

@app.route('/user/')
def get_user():
    channelId = request.args.get('channelId')
    params = request.args.get('params')
    if params == None:
        return ytmusic.get_user(channelId)
    else:
        return ytmusic.get_user_playlists(channelId, params)

@app.route('/songs/metadata/')
def get_song_metadata():
    videoId = request.args.get('videoId')
    pytube = YouTube("https://www.youtube.com/watch?v=" + videoId)
    def stream(videoId):
        audio_stream = pytube.streams.filter(only_audio=True).order_by('abr').desc().first()
        return str(audio_stream.url)
    result = ytmusic.search(videoId, "songs", limit=1)
    result_clone = json.dumps(result, indent=4)
    parse_json = json.loads(result_clone)
    song_detail = parse_json[0]
    print(song_detail)
    song_name = song_detail['title']
    song_artists = song_detail['artists']
    song_album = song_detail["album"]
    search_keyword_for_spotify_id = song_name + " " + song_artists[0]['name']
    search_keyword_for_spotify_id = re.sub(r'[^\w\s]', '', search_keyword_for_spotify_id)
    print(search_keyword_for_spotify_id)
    def lyrics(search_keyword_for_spotify_id):
        url = "https://spotify-lyric-api.herokuapp.com/?trackid=" + find_track_id(search_keyword_for_spotify_id)
        request = requests.get(url)
        return request.json()
    result.append({"streamAudio": stream(videoId), "lyrics": lyrics(search_keyword_for_spotify_id)})
    return convert_to_json(result)
@app.route('/thumbnails/', methods=['GET', 'POST'])
def get_thumbnails():
    songId = request.args.get('songId')
    print(str(songId))
    op = webdriver.ChromeOptions()
    op.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    opbin = os.environ.get("GOOGLE_CHROME_BIN")
    opdriver = os.environ.get("CHROMEDRIVER_PATH")
    op.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36')
    op.add_argument('--headless')
    op.add_argument('--disable-gpu')
    op.add_argument("--no-sandbox")
    # driver = webdriver.Chrome(service=Service(os.environ.get("CHROMEDRIVER_PATH")), options=op)
    driver = webdriver.Chrome(service=Service(os.environ.get("CHROMEDRIVER_PATH")), options=op)
    url = "https://music.youtube.com/watch?v="+songId
    driver.get(url)
    time.sleep(1)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    data_div = soup.find('div', attrs={'id': 'song-image'})
    print(data_div)
    link = data_div.find('img')['src']
    link1 = data_div.select_one('img')['src']
    error = False
    if link==None or link == "":
        link = ""
        error = True
    elif link.__contains__("https://") == False:
        error = True
    result = [{"thumbnails": link1, "error": error}]
    return convert_to_json(result)
        
#EXPLORE
@app.route('/explore/mood/title')
def get_explore_mood():
    response = ytmusic._send_request("browse", {"browseId": "FEmusic_moods_and_genres"})
    moods = {}
    genre = {}
    array = nav(response, SINGLE_COLUMN_TAB + SECTION_LIST)
    moodsmoment = nav(response, SINGLE_COLUMN_TAB + SECTION_LIST)[0]
    items_mood = nav(moodsmoment, ["gridRenderer", "items"])
    for item in items_mood:
        title = nav(item, ["musicNavigationButtonRenderer", "buttonText", "runs", 0, "text"]).strip()
        endpnt = nav(item, ["musicNavigationButtonRenderer", "clickCommand", "browseEndpoint", "browseId"])
        params = nav(item, ["musicNavigationButtonRenderer", "clickCommand", "browseEndpoint", "params"])
        moods[title] = {"params": params, "endpoint": endpnt}
    header_mood = nav(moodsmoment, ["gridRenderer", "header","gridHeaderRenderer", "title", "runs", 0, "text"])
    genres = nav(response, SINGLE_COLUMN_TAB + SECTION_LIST)[1]
    items_genres = nav(genres, ["gridRenderer", "items"])
    for item in items_genres:
        title = nav(item, ["musicNavigationButtonRenderer", "buttonText", "runs", 0, "text"]).strip()
        endpnt = nav(item, ["musicNavigationButtonRenderer", "clickCommand", "browseEndpoint", "browseId"])
        params = nav(item, ["musicNavigationButtonRenderer", "clickCommand", "browseEndpoint", "params"])
        genre[title] = {"params": params, "endpoint": endpnt}
    header_genres = nav(genres, ["gridRenderer", "header","gridHeaderRenderer", "title", "runs", 0, "text"])
    result = [{header_mood: [moods]}, {header_genres: [genre]}]
    return convert_to_json(result)
            # {
        #     'For you': [
        #         {
        #             'params': 'ggMPOg1uX1ZwN0pHT2NBT1Fk',
        #             'title': '1980s'
        #         },
        #         {
        #             'params': 'ggMPOg1uXzZQbDB5eThLRTQ3',
        #             'title': 'Feel Good'
        #         },
        #         ...
        #     ],
        #     'Genres': [
        #         {
        #             'params': 'ggMPOg1uXzVLbmZnaWI4STNs',
        #             'title': 'Dance & Electronic'
        #         },
        #         {
        #             'params': 'ggMPOg1uX3NjZllsNGVEMkZo',
        #             'title': 'Decades'
        #         },
        #         ...
        #     ],
        #     'Moods & moments': [
        #         {
        #             'params': 'ggMPOg1uXzVuc0dnZlhpV3Ba',
        #             'title': 'Chill'
        #         },
        #         {
        #             'params': 'ggMPOg1uX2ozUHlwbWM3ajNq',
        #             'title': 'Commute'
        #         },
        #         ...
        #     ],
        # }
@app.route('/explore/genre')
def get_explore_playlist():
    params = request.args.get('p')
    endpoint = request.args.get('ep')
    response_1 = ytmusic._send_request("browse", {"browseId": endpoint, "params": params})
    header = nav(response_1, ["header","musicHeaderRenderer", "title", "runs", 0, "text"])
    items = nav(response_1, ["contents", "singleColumnBrowseResultsRenderer", "tabs", 0, "tabRenderer", "content", "sectionListRenderer", "contents"])
    result = {}
    for item in items:
        #Today's Dance Hits
        key = []
        key_content = []
        key_header = ""
        if ("musicCarouselShelfRenderer" in item):
            key = ["musicCarouselShelfRenderer"]
            key_content = ["contents"]
            key_header = "musicCarouselShelfBasicHeaderRenderer"
        elif ("gridRenderer" in item):
            key = ["gridRenderer"]
            key_content = ["items"]
            key_header = "gridHeaderRenderer"
        elif ("musicImmersiveCarouselShelfRenderer" in item):
            key = ["musicImmersiveCarouselShelfRenderer"]
            key_content = ["contents"]
            key_header = "musicImmersiveCarouselShelfHeaderRenderer"
        mCSR = nav(item, key)
        item_header = nav(mCSR,["header", key_header,"title", "runs", 0, "text"])
        item_contents = nav(mCSR, key_content)
        item_contents_list = []
        for item_content in item_contents:
            #Chroma: Today's Dance 
            item_content_title = nav(item_content, ["musicTwoRowItemRenderer", "title", "runs", 0, "text"])
            thumbnail = nav(item_content, ["musicTwoRowItemRenderer", "thumbnailRenderer", "musicThumbnailRenderer", "thumbnail", "thumbnails"])
            subtitle = nav(item_content, ["musicTwoRowItemRenderer", "subtitle", "runs", 0, "text"]) + nav(item_content, ["musicTwoRowItemRenderer", "subtitle", "runs", 1, "text"]) + nav(item_content, ["musicTwoRowItemRenderer", "subtitle", "runs", 2, "text"])
            playlistBrowseId = nav(item_content, ["musicTwoRowItemRenderer", "navigationEndpoint", "browseEndpoint", "browseId"])
            item_content_dict = {"title": item_content_title, "subtitle": subtitle, "thumbnail": thumbnail, "playlistBrowseId": playlistBrowseId}
            item_contents_list.append(item_content_dict)
        item_dict = {"header": item_header, "browseId": item_browse_id, "params": item_params, "contents": item_contents_list}
    result = {"header": header, "items": item_dict}
    return convert_to_json(result)
@app.route('/explore/mood')
def get_explore_mood_playlist():
    params = request.args.get('p')
    endpoint = request.args.get('ep')
    response = ytmusic._send_request("browse", {"browseId": endpoint, "params": params})
    header = nav(response, ["header","musicHeaderRenderer", "title", "runs", 0, "text"])
    items = nav(response, ["contents", "singleColumnBrowseResultsRenderer", "tabs", 0, "tabRenderer", "content", "sectionListRenderer", "contents"])
    item_list = []
    for item in items:
        key = []
        key_content = []
        if ("musicCarouselShelfRenderer" in item):
            key = ["musicCarouselShelfRenderer"]
            key_content = ["contents"]
        elif ("gridRenderer" in item):
            key = ["gridRenderer"]
            key_content = ["items"]
        elif ("musicImmersiveCarouselShelfRenderer" in item):
            key = ["musicImmersiveCarouselShelfRenderer"]
            key_content = ["contents"]
        mCSR = nav(item, key)
        header = nav(mCSR, ["header", key[0],"title", "runs", 0, "text"])
        contents = nav(mCSR, key_content)
        content_dict = []
        for content in contents:
            mTRIR = nav(content, ["musicTwoRowItemRenderer"])
            thumbnails = nav(mTRIR, ["thumbnailRenderer", "musicThumbnailRenderer", "thumbnail", "thumbnails"])
            title = nav(mTRIR, ["title", "runs", 0, "text"])
            subtitle = nav(mTRIR, ["subtitle", "runs", 0, "text"]) + nav(mTRIR, ["subtitle", "runs", 1, "text"]) + nav(mTRIR, ["subtitle", "runs", 2, "text"])
            playlistBrowseId = nav(mTRIR, ["navigationEndpoint", "browseEndpoint", "browseId"])
            ctd = {"title": title, "subtitle": subtitle, "thumbnails": thumbnails, "playlistBrowseId": playlistBrowseId}
            content_dict.append(ctd)
        item_dict = {"header": header, "contents": content_dict}
        item_list.append(item_dict)
    result = {"header": header, "params": params, "endpoint": endpoint, "items": item_list}
    return convert_to_json(result)
@app.route('/explore/charts')
def get_explore_charts():
    countryCode = request.args.get('cc')
    data = ytmusic.get_charts(countryCode)
    return convert_to_json(data)
    #     {
    #     "countries": {
    #         "selected": {
    #             "text": "United States"
    #         },
    #         "options": ["DE",
    #             "ZZ",
    #             "ZW"]
    #     },
    #     "songs": {
    #         "playlist": "VLPL4fGSI1pDJn6O1LS0XSdF3RyO0Rq_LDeI",
    #         "items": [
    #             {
    #                 "title": "Outside (Better Days)",
    #                 "videoId": "oT79YlRtXDg",
    #                 "artists": [
    #                     {
    #                         "name": "MO3",
    #                         "id": "UCdFt4Cvhr7Okaxo6hZg5K8g"
    #                     },
    #                     {
    #                         "name": "OG Bobby Billions",
    #                         "id": "UCLusb4T2tW3gOpJS1fJ-A9g"
    #                     }
    #                 ],
    #                 "thumbnails": [...],
    #                 "isExplicit": true,
    #                 "album": {
    #                     "name": "Outside (Better Days)",
    #                     "id": "MPREb_fX4Yv8frUNv"
    #                 },
    #                 "rank": "1",
    #                 "trend": "up"
    #             }
    #         ]
    #     },
    #     "videos": {
    #         "playlist": "VLPL4fGSI1pDJn69On1f-8NAvX_CYlx7QyZc",
    #         "items": [
    #             {
    #                 "title": "EVERY CHANCE I GET (Official Music Video) (feat. Lil Baby & Lil Durk)",
    #                 "videoId": "BTivsHlVcGU",
    #                 "playlistId": "PL4fGSI1pDJn69On1f-8NAvX_CYlx7QyZc",
    #                 "thumbnails": [],
    #                 "views": "46M"
    #             }
    #         ]
    #     },
    #     "artists": {
    #         "playlist": null,
    #         "items": [
    #             {
    #                 "title": "YoungBoy Never Broke Again",
    #                 "browseId": "UCR28YDxjDE3ogQROaNdnRbQ",
    #                 "subscribers": "9.62M",
    #                 "thumbnails": [],
    #                 "rank": "1",
    #                 "trend": "neutral"
    #             }
    #         ]
    #     },
    #     "genres": [
    #         {
    #             "title": "Top 50 Pop Music Videos United States",
    #             "playlistId": "PL4fGSI1pDJn77aK7sAW2AT0oOzo5inWY8",
    #             "thumbnails": []
    #         }
    #     ],
    #     "trending": {
    #         "playlist": "VLPLrEnWoR732-DtKgaDdnPkezM_nDidBU9H",
    #         "items": [
    #             {
    #                 "title": "Permission to Dance",
    #                 "videoId": "CuklIb9d3fI",
    #                 "playlistId": "PLrEnWoR732-DtKgaDdnPkezM_nDidBU9H",
    #                 "artists": [
    #                     {
    #                         "name": "BTS",
    #                         "id": "UC9vrvNSL3xcWGSkV86REBSg"
    #                     }
    #                 ],
    #                 "thumbnails": [],
    #                 "views": "108M"
    #             }
    #         ]
    #     }
    # }

#PLAYLISTS
@app.route('/playlists')
def get_playlist():
    playlistId = request.args.get('id')
    data = ytmusic.get_playlist(playlistId)
    return convert_to_json(data)
    # {
    #   "id": "PLQwVIlKxHM6qv-o99iX9R85og7IzF9YS_",
    #   "privacy": "PUBLIC",
    #   "title": "New EDM This Week 03/13/2020",
    #   "thumbnails": [...]
    #   "description": "Weekly r/EDM new release roundup. Created with github.com/sigma67/spotifyplaylist_to_gmusic",
    #   "author": "sigmatics",
    #   "year": "2020",
    #   "duration": "6+ hours",
    #   "duration_seconds": 52651,
    #   "trackCount": 237,
    #   "suggestions": [
    #       {
    #         "videoId": "HLCsfOykA94",
    #         "title": "Mambo (GATTÜSO Remix)",
    #         "artists": [{
    #             "name": "Nikki Vianna",
    #             "id": "UCMW5eSIO1moVlIBLQzq4PnQ"
    #           }],
    #         "album": {
    #           "name": "Mambo (GATTÜSO Remix)",
    #           "id": "MPREb_jLeQJsd7U9w"
    #         },
    #         "likeStatus": "LIKE",
    #         "thumbnails": [...],
    #         "isAvailable": true,
    #         "isExplicit": false,
    #         "duration": "3:32",
    #         "duration_seconds": 212,
    #         "setVideoId": "to_be_updated_by_client"
    #       }
    #   ],
    #   "related": [
    #       {
    #         "title": "Presenting MYRNE",
    #         "playlistId": "RDCLAK5uy_mbdO3_xdD4NtU1rWI0OmvRSRZ8NH4uJCM",
    #         "thumbnails": [...],
    #         "description": "Playlist • YouTube Music"
    #       }
    #   ],
    #   "tracks": [
    #     {
    #       "videoId": "bjGppZKiuFE",
    #       "title": "Lost",
    #       "artists": [
    #         {
    #           "name": "Guest Who",
    #           "id": "UCkgCRdnnqWnUeIH7EIc3dBg"
    #         },
    #         {
    #           "name": "Kate Wild",
    #           "id": "UCwR2l3JfJbvB6aq0RnnJfWg"
    #         }
    #       ],
    #       "album": {
    #         "name": "Lost",
    #         "id": "MPREb_PxmzvDuqOnC"
    #       },
    #       "duration": "2:58",
    #       "likeStatus": "INDIFFERENT",
    #       "thumbnails": [...],
    #       "isAvailable": True,
    #       "isExplicit": False,
    #       "videoType": "MUSIC_VIDEO_TYPE_OMV",
    #       "feedbackTokens": {
    #         "add": "AB9zfpJxtvrU...",
    #         "remove": "AB9zfpKTyZ..."
    #     }
    #   ]
    # }

#Billboard
#Some ID 
    #hot-100
    #billboard-200
    #artist-100
    #billboard-global-200
    #dance-electronic-songs
    #r-and-b-songs
    #billboard-vietnam-hot-100
@app.route('/billboard')
def get_billboard():
    chartId = request.args.get('id')
    charts = billboard.ChartData(chartId)
    json_dict = []
    for i in charts:
        json_dict.append(i.__dict__)
    return convert_to_json(json_dict)

if __name__ == '__main__':
    app.run()