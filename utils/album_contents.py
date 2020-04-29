import json
import logging

import arrow

class Media:
    ''' Media on Google Cloud'''

    def __init__(self, mimetype, filename):
        self.filename = filename
        self.mimetype = mimetype
        self.media_metadata_creation_time = ''

    def __repr__(self):
        return '{}'.format(self.filename)

    @property
    def creation_ts(self):
        ''' reformatting, removing Z, etc '''
        d = arrow.get(self.media_metadata_creation_time)
        return d.datetime

def get_album_contents(session, album):
    ''' returns generator '''

    session.headers["Content-type"] = "application/json"
    data_dict = {
        'albumId':album['id'],
        'pageSize':'100',
    }
    while True:
        data = json.dumps(data_dict, indent=4)
        resp = session.post('https://photoslibrary.googleapis.com/v1/mediaItems:search', data).json()
        if 'mediaItems' in resp: 
            for mi in resp['mediaItems']: 
                yield mi

            if 'nextPageToken' in resp:
                data_dict['pageToken'] = resp['nextPageToken']
            else:
                return
        else:
            return

def parse_media_items(album_content_generator):
    media_items = []

    for ea in album_content_generator:
        media = Media(ea['mimeType'], ea['filename'])
        if 'mediaMetadata' in ea.keys():
            media.media_metadata_creation_time = ea['mediaMetadata'].get('creationTime', '')
            media_items.append(media)

    return media_items


def get_albums(session, appCreatedOnly=False):

    params = {
            'excludeNonAppCreatedData': appCreatedOnly
    }

    while True:

        albums = session.get('https://photoslibrary.googleapis.com/v1/albums', params=params).json()

        logging.debug("Server response: {}".format(albums))

        if 'albums' in albums:

            for a in albums["albums"]:
                yield a

            if 'nextPageToken' in albums:
                params["pageToken"] = albums["nextPageToken"]
            else:
                return

        else:
            return
  
# vim: ai et ts=4 sw=4 sts=4 nu
