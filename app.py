from datetime import timedelta
from flask import Flask, render_template
import datetime
import isodate
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')
PLAYLIST_ID = os.getenv('PLAYLIST_ID')

URL1 = 'https://www.googleapis.com/youtube/v3/playlistItems?' \
       'part=contentDetails' \
       '&maxResults=50' \
       '&fields=items/contentDetails/videoId,nextPageToken' \
       '&key={}' \
       '&playlistId={}' \
       '&pageToken= '
URL2 = 'https://www.googleapis.com/youtube/v3/videos?&part=contentDetails&id={}&key={' \
       '}&fields=items/contentDetails/duration '


app = Flask(__name__, static_url_path='/static')
app._static_folder = '/static/'


@app.route("/", methods=['GET'])
def home():
    next_page = ''
    videos_counter = 0
    total_playlist_length = timedelta(0)
    display_text = []

    while True:
        vid_list, next_page_token, error = get_video_list(next_page)
        if error is not None:
            display_text = error
            break

        duration, error = calculate_duration(vid_list)
        if error is not None:
            display_text = error
            break

        total_playlist_length += duration
        videos_counter += len(vid_list)

        if is_last_page(next_page_token) and videos_counter < 500:
            next_page = next_page_token
        else:
            if videos_counter >= 500:
                display_text = ['No of videos limited to 500.']
            display_text += format_message(total_playlist_length, videos_counter)
            break

    return render_template("home.html", display_text=display_text)


def calculate_duration(vid_list):
    url_list = ','.join(vid_list)
    total_duration = timedelta(0)

    try:
        video_durations = json.loads(requests.get(URL2.format(url_list, API_KEY)).text)

        for video in video_durations['items']:
            total_duration += isodate.parse_duration(video['contentDetails']['duration'])

        return total_duration, None
    except KeyError:
        return None, [video_durations['error']['message']]


def get_video_list(next_page):
    vid_list = []

    try:
        results = json.loads(requests.get(URL1.format(API_KEY, PLAYLIST_ID) + next_page).text)

        for video in results['items']:
            vid_list.append(video['contentDetails']['videoId'])

        if 'nextPageToken' in results:
            return vid_list, results['nextPageToken'], None
        else:
            return vid_list, None, None

    except KeyError:
        return None, None, [results['error']['message']]


def parse_time(a):
    seconds, days = a.seconds, a.days
    hours, rest_hours = divmod(seconds, 3600)
    minutes, seconds = divmod(rest_hours, 60)
    formatted_string = ''
    if days:
        hours += days * 24
    if hours:
        formatted_string += ' {} hour{},'.format(hours, 's' if hours != 1 else '')
    if minutes:
        formatted_string += ' {} minute{},'.format(minutes, 's' if minutes != 1 else '')
    if seconds:
        formatted_string += ' {} second{}'.format(seconds, 's' if seconds != 1 else '')
    if formatted_string == '':
        formatted_string = '0 seconds'
    return formatted_string.strip().strip(',')


def is_last_page(next_page_token):
    return next_page_token is not None


def format_message(total_playlist_length, videos_counter):
    total_weeks_of_the_year = datetime.date(2021, 12, 31).isocalendar()[1]
    current_week_number = datetime.datetime.today().isocalendar()[1]
    weeks_to_end_the_year = total_weeks_of_the_year - current_week_number
    total_playlist_hours = total_playlist_length.days * 24 + total_playlist_length.seconds / 3600
    missing_challenge_hours = (100 - total_playlist_hours)

    return [
        'Número de vídeos: ' + str(videos_counter),
        'Tamaño total de la lista: ' + parse_time(total_playlist_length),
        'Esto significa que tenemos un {:.2f}% del reto conseguido'.format(total_playlist_hours),
        'Y que necesitamos hacer al menos {:.2f} horas a la semana para llegar a tiempo'.format(
            missing_challenge_hours / weeks_to_end_the_year),
    ]


if __name__ == "__main__":
    app.run(use_reloader=True, debug=False)
