'''Retrieve google photos/videos metatdata'''

from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging
from pathlib import Path

import arrow
from exif import Image
import filetype
from upload import parse_args, get_authorized_session

now = datetime.now()

LOG_LEVEL = logging.INFO

# https://awesomeopensource.com/project/h2non/filetype.py
VIDEO_MIMES = [
    'video/mp4',
    'video/x-m4v',
    'video/x-matroska', # mkv
    'video/webm',
    'video/quicktime', # mov
    'video/x-msvideo', # avi
    'video/x-ms-wmv',
    'video/mpeg',
    'video/x-flv',
]


class Album:
    def __init__(self, id, title):
        self.id = id
        self.title = title

    def __repr__(self):
        return '{}'.format(self.title)

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
        d = arrow.get(self.media_metadata_creation_time)
        return d.datetime

class MediaOnDisk:
    '''
    It would appear that on the image, if it has exif.datetime, google uses this for creation time.
    Othewise, google uses the time of uploading for creation time.
    Google is storing the timestamp as GMT time in google, but somehow being transposed - not sure 
    '''

    def __init__(self, path_obj):
        self.path_obj = path_obj 
        self.exif_datetime = ''
        self.mime_type = ''
        self.stat = path_obj.stat() 

    def __repr__(self):
        return '{}'.format(self.path_obj.name)

    @property
    def st_ctime(self):
        return datetime.fromtimestamp(self.stat.st_ctime, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def st_atime(self):
        return datetime.fromtimestamp(self.stat.st_atime, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def st_atime_ts(self):
        return datetime.fromtimestamp(self.stat.st_atime, timezone.utc)

    @property
    def st_mtime(self):
        return datetime.fromtimestamp(self.stat.st_mtime, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def exif_ts(self):
        r = None
        if self.exif_datetime:
            d = arrow.get(self.exif_datetime, 'YYYY:MM:DD HH:mm:ss')
            r = d.datetime

        return r
        


def get_albums(session):
    '''Need to fix this, and just get the album needed'''

    albums = [] 
    session.headers["Content-type"] = "application/json"

    try:
        resp = session.get('https://photoslibrary.googleapis.com/v1/albums').json()
        if 'albums' in resp.keys():
            for ea in resp['albums']:
                logging.debug('{} {}'.format(ea['title'], ea['id']))
                albums.append(Album(ea['id'], ea['title']))

    except Exception as e:
        logging.error('get album id: {}'.format(e))
        sys.exit()
    finally:
        return albums

def get_album_contents(session, album):

    media_items = []
    session.headers["Content-type"] = "application/json"

    try:
        data = json.dumps({"albumId":album.id, "pageSize":"100"}, indent=4)
        r = session.post('https://photoslibrary.googleapis.com/v1/mediaItems:search', data).json()
        if 'mediaItems' in r.keys():
            for ea in r['mediaItems']:
                media = Media(ea['mimeType'], ea['filename'])
                if 'mediaMetadata' in ea.keys():
                        media.media_metadata_creation_time = ea['mediaMetadata'].get('creationTime', '')
                media_items.append(media)

    except Exception as e:
        logging.error('{}'.format(e))
        sys.exit()
    finally:
        return media_items

def compare_media(args):

    if not args.album_name:
        logging.info('An album name is needed to do this comparison')
        return

    media_match = False

    try:
        media_on_disk = MediaOnDisk(Path(args.photos[0]))
        logging.debug('Path of media on disk: {}'.format(media_on_disk.path_obj))

        kind = filetype.guess('{}'.format(media_on_disk.path_obj))
        logging.debug(kind.mime)
        media_on_disk.mime_type = kind.mime
        logging.debug(media_on_disk.mime_type)

        if media_on_disk.mime_type.lower() not in VIDEO_MIMES:
            with open(media_on_disk.path_obj, 'rb') as fh:
                image = Image(fh)
        
            # Deal with image on disk
            if image.has_exif:
                media_on_disk.exif_datetime = image.get('datetime', '')
                logging.debug(media_on_disk.exif_datetime)


        logging.debug('media_on_disk:{}, exif_datetime:{}, st_ctime:{}'.format(media_on_disk, media_on_disk.exif_datetime, media_on_disk.st_ctime))

        # Deal with image on google photos
        session = get_authorized_session(args.auth_file, Path(args.credentials))
                #scopes=['https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata'])

        albums = get_albums(session)
        logging.debug('Response: {}'.format(albums))
        album_exists = False
        for ea in albums:
            if ea.title == args.album_name:
                album_exists = True
                media_items = get_album_contents(session, ea)
                logging.debug('{}'.format([(x.filename, x.mimetype, x.media_metadata_creation_time) for x in media_items]))
            
                for mi in media_items:
                    if mi.filename == media_on_disk.path_obj.name:
                        logging.debug('1: Found name match {}'.format(media_on_disk))
                        if media_on_disk.mime_type == mi.mimetype:
                            logging.debug('2: Found mimetype (media on disk) match: {}'.format(media_on_disk.mime_type))
                            if mi.creation_ts == media_on_disk.exif_ts:
                                logging.debug('3: timestamps match {}: {}'.format(mi.media_metadata_creation_time, media_on_disk.exif_datetime))
                                media_match = True

                                logging.info('Yes match, no upload: album, filename, mime, timestamp: {}'.format(args.photos[0]))
                                # Used for debugging
                                logging.debug('str: Timestamp from google: {}'.format(mi.media_metadata_creation_time))
                                logging.debug('Timestamp from google: {}'.format(mi.creation_ts))
                                logging.debug('str: Timestamp (exif) from media on disk: {}'.format(media_on_disk.exif_datetime))
                                logging.debug('Timestamp (exif) from media on disk: {}'.format(media_on_disk.exif_ts))
                                logging.debug('str: Timestamp st_ctime from media on disk: {}'.format(media_on_disk.st_ctime))
                                logging.debug('str: Timestamp st_atime from media on disk: {}'.format(media_on_disk.st_atime))
                                logging.debug('str: Timestamp st_mtime from media on disk: {}'.format(media_on_disk.st_mtime))
                                logging.debug('Timestamp st_atime from media on disk: {}'.format(media_on_disk.st_atime_ts))
                            elif args.minutes != 0:
                                logging.debug('--min  {}'.format(args.minutes))
                                if not media_on_disk.exif_ts:
                                    min_delta = timedelta(minutes=args.minutes)
                                    logging.debug('min_delta: {}'.format(min_delta))
                                    logging.debug('time delta: {}'.format(media_on_disk.st_atime_ts - mi.creation_ts))
                                    if (media_on_disk.st_atime_ts - mi.creation_ts) < min_delta:
                                        logging.debug('Woo! Hoo!')
                                        logging.info('Yes match, no upload: album, filename, mime are ok, and st_atime - '
                                            'google timestamp < {} min [{} {}]'.format(args.minutes, 
                                             media_on_disk.st_atime_ts, mi.creation_ts))
                                        media_match = True
                                    else:
                                        pass
                                        logging.info('No match, upload: album, filename, mime are ok, but st_atime - '
                                            'google timestamp > {} min [{} {}]'.format(args.minutes, 
                                             media_on_disk.st_atime_ts, mi.creation_ts))

                            else:
                                logging.info('No match, upload: filename:ok, mimetype:ok, timestamp:not_okay: {}'.format(args.photos[0]))

                                # Used for debugging
                                logging.info('Timestamp from google: {}'.format(mi.media_metadata_creation_time))
                                logging.info('Timestamp (exif) from media on disk: {}'.format(media_on_disk.exif_datetime))
                                logging.info('Timestamp st_ctime from media on disk: {}'.format(media_on_disk.st_ctime))
                                logging.info('Timestamp st_atime from media on disk: {}'.format(media_on_disk.st_atime))
                                logging.info('Timestamp st_mtime from media on disk: {}'.format(media_on_disk.st_mtime))


    except Exception as e:
        logging.error('{}'.format(e))
    finally:
        if not album_exists:
                logging.info('album name {} not found'.format(args.album_name))
        return media_match

def main():

    args = parse_args()

    logging.basicConfig(format='%(asctime)s %(module)s.%(funcName)s:%(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I_%M_%S %p',
                    filename=args.log_file,
                    level=LOG_LEVEL)

    if args.dry_run:
        logging.debug(args)
        if args.photos:
            logging.info('''
            Path: {}
            Exiting, --dry-run
                        '''.format(args.photos[0]))
        else:
            logging.info('''
            No path provided 
            Exiting, --dry-run
                        ''')

    else:
        if args.photos:
            compare_media(args)

        else:
            logging.error('No photo or video path provided')

if __name__ == '__main__':
  
    try:
        main()

    except KeyboardInterrupt:
        logging.error('''
  
          Keyboard interrupt : ) exiting
  
          ''')
  
    finally:
  
        end = datetime.now()
        elapsed = relativedelta(end, now)
        print("""
Time elapsed: {} hours, {} minutes, {} seconds
""".format(elapsed.hours, elapsed.minutes, elapsed.seconds))
  
# vim: ai et ts=4 sw=4 sts=4 nu
