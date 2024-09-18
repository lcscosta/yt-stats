import os
import json

import click
from dotenv import load_dotenv
import isodate
from googleapiclient.discovery import build
from tabulate import tabulate


def get_channel_videos(youtube, channel_id):
    # Obtém a lista de uploads do canal
    response = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    ).execute()
    
    playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # Lista todos os vídeos da playlist de uploads
    videos = []
    next_page_token = None
    while True:
        playlist_response = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        
        for item in playlist_response['items']:
            video_id = item['snippet']['resourceId']['videoId']
            videos.append(video_id)
        
        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break
    
    return videos


def get_video_details(youtube, video_ids):
    all_video_details = []
    batch_size = 50  # Maximum number of IDs per request
    
    # Process video IDs in batches
    for start in range(0, len(video_ids), batch_size):
        end = min(start + batch_size, len(video_ids))
        batch_ids = video_ids[start:end]
        
        response = youtube.videos().list(
            part='snippet,contentDetails',
            id=','.join(batch_ids)
        ).execute()
        
        # Collect video details from this batch
        for item in response['items']:
            video_id = item['id']
            video_title = item['snippet']['title']
            duration = item['contentDetails']['duration']
            # Parse ISO 8601 duration
            duration = isodate.parse_duration(duration)
            # Convert duration to total seconds
            duration_seconds = int(duration.total_seconds())
            all_video_details.append((video_id, video_title, duration_seconds))
    
    return all_video_details


def format_duration(seconds):
    # Format duration in a more readable format (HH:MM:SS)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02}h:{minutes:02}m:{seconds:02}s'


def get_channel_by_keyword(youtube, keyword):
    search_response = youtube.search().list(
        q=keyword,
        type='channel',
        part='snippet',
        maxResults=10
    ).execute()

    channels = []
    for item in search_response.get('items', []):
        channel_title = item['snippet']['title']
        channel_id = item['snippet']['channelId']
        channels.append([channel_title, channel_id])

    print(tabulate(channels, headers=['Channel Name', 'Channel ID'], showindex="always", tablefmt="fancy_grid"))


def get_all_channel_videos_duration(youtube, channel_id):
    total_duration = 0
    try:
        videos_id = get_channel_videos(youtube, channel_id)
        videos_details = get_video_details(youtube, videos_id)
        for video_id, video_title, duration_seconds in videos_details:
            total_duration += duration_seconds
    except ValueError as e:
        print(e)

    print(tabulate(videos_details[0:10], headers=['Video ID', 'Video Title', 'Duration (s)'], showindex="always", tablefmt="fancy_grid"))

    table = [
        ["Total Duration", format_duration(total_duration)], 
        ["Average Duration", format_duration(int(total_duration/len(videos_details)))]
    ] 
    

    print(tabulate(table, tablefmt="fancy_grid"))

@click.command()
@click.option('--search', '-s', help='Search a Channel ID')
@click.option('--channel-id', '-chid', help='Channel ID')
@click.option('--channel-all-videos-duration', '-chavd', help='Get All Videos Duration for a Channel', is_flag=True)
def main(search, channel_id, channel_all_videos_duration):
    load_dotenv()

    # Load environment variables
    
    API_KEY = os.environ.get("GOOGLE_API_KEY")
    if not API_KEY:
        raise Exception("API KEY not found. Please set GOOGLE_API_KEY environment variable")
    
    if not channel_id:
        try:
            channel_id = os.environ.get("CHANNEL_ID")
        except:
            pass

    youtube = build('youtube', 'v3', developerKey=API_KEY)

    if search:
        get_channel_by_keyword(youtube, search)
    
    if channel_all_videos_duration:
        if not channel_id:
            raise Exception("Channel ID is required")
        get_all_channel_videos_duration(youtube, channel_id)


if __name__ == '__main__':
    main()