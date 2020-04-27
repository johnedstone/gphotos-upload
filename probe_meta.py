'''Retrieve google photos/videos metatdata'''

from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging
import mimetypes
from pathlib import Path
import sys

import arrow
from PIL import Image
from PIL.ExifTags import TAGS
import upload

now = datetime.now()

LOG_LEVEL = logging.INFO

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

    def exif_ts(self, tz='Europe/London'):
        r = None
        if self.exif_datetime:
            d = arrow.get('{} {}'.format(self.exif_datetime, tz), 'YYYY:MM:DD HH:mm:ss ZZZ')
            r = d.datetime

        return r
        
def get_labeled_exif(exif):
    labeled = {}
    for (key, val) in exif.items():
        labeled[TAGS.get(key)] = val

    return labeled

def get_exif(filename):
    exif = None
    try:
        image = Image.open(filename)
        image.verify()
        exif = image._getexif()
    except Exception as e:
        logging.debug('''Problem getting exif. That's okay, moving on: {}'''.format(e))

    return exif

def get_album_contents(session, album):

    media_items = []
    session.headers["Content-type"] = "application/json"

    try:
        data = json.dumps({"albumId":album['id'], "pageSize":"100"}, indent=4)
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

def compare_media(args, posix_path=None, session=None, albums=None):
    media_match = False
    try:
        media_on_disk = MediaOnDisk(posix_path)

        logging.debug('Path of media on disk: {}'.format(media_on_disk.path_obj))

        mime, encoding = mimetypes.guess_type('{}'.format(media_on_disk.path_obj))
        logging.debug(mime)
        media_on_disk.mime_type = mime

        # Google registers webm as mp4, adjusting here
        if media_on_disk.mime_type == 'video/webm':
            media_on_disk.mime_type = 'video/mp4'

        logging.debug(media_on_disk.mime_type)

        exif = get_exif(media_on_disk.path_obj)
        logging.debug('exif: {}'.format(exif))
        if exif:
            labeled = get_labeled_exif(exif)
            media_on_disk.exif_datetime = labeled.get('DateTime', '')
            logging.debug(media_on_disk.exif_datetime)


        logging.debug('media_on_disk:{}, exif_datetime:{}, st_ctime:{}'.format(media_on_disk, media_on_disk.exif_datetime, media_on_disk.st_ctime))

        logging.debug('Response: {}'.format(albums))
        album_exists = False
        for a in albums:
            if a["title"].lower() == args.album_name.lower():
                album_exists =True
                media_items = get_album_contents(session, a)
                logging.debug('Album contents: {}'.format([(x.filename, x.mimetype, x.media_metadata_creation_time) for x in media_items]))
            
                for mi in media_items:
                    if mi.filename == media_on_disk.path_obj.name:
                        logging.debug('1: Found name match {}'.format(media_on_disk))
                        logging.debug("media mime on disk: {}, media mime in cloud: {}".format(media_on_disk.mime_type, mi.mimetype))
                        if media_on_disk.mime_type == mi.mimetype:
                            logging.debug('2: Found mimetype (media on disk) match: {}'.format(media_on_disk.mime_type))
                            if mi.creation_ts == media_on_disk.exif_ts(args.tz):
                                logging.debug('3: timestamps match {}: {}'.format(mi.media_metadata_creation_time, media_on_disk.exif_datetime))
                                media_match = True

                                logging.debug('Yes match, no upload: album, filename, mime, timestamp: {}'.format(args.photos[0]))
                                # Used for debugging
                                logging.debug('str: Timestamp from google: {}'.format(mi.media_metadata_creation_time))
                                logging.debug('Timestamp, reformatted, from google: {}'.format(mi.creation_ts))
                                logging.debug('str: Timestamp (exif) from media on disk: {}'.format(media_on_disk.exif_datetime))
                                logging.debug('Timestamp (exif), reformatted, from media on disk: {}'.format(media_on_disk.exif_ts(args.tz)))
                                logging.debug('str: Timestamp st_ctime from media on disk: {}'.format(media_on_disk.st_ctime))
                                logging.debug('str: Timestamp st_atime from media on disk: {}'.format(media_on_disk.st_atime))
                                logging.debug('str: Timestamp st_mtime from media on disk: {}'.format(media_on_disk.st_mtime))
                                logging.debug('Timestamp st_atime from media on disk: {}'.format(media_on_disk.st_atime_ts))
                            elif args.minutes != 0:
                                logging.debug('--min  {}'.format(args.minutes))
                                if not media_on_disk.exif_ts(args.tz):
                                    min_delta = timedelta(minutes=args.minutes)
                                    logging.debug('min_delta: {}'.format(min_delta))
                                    logging.debug('time delta: {}'.format(media_on_disk.st_atime_ts - mi.creation_ts))
                                    ts_diff =media_on_disk.st_atime_ts - mi.creation_ts
                                    if ts_diff < min_delta:
                                        logging.debug('Woo! Hoo!')
                                        logging.debug('Yes match, upload not needed: album, filename, mime are ok, st_atime within range '
                                            '[{} < {} min] [{} {}]'.format(
                                                ts_diff, args.minutes, media_on_disk.st_atime_ts, mi.creation_ts))
                                        media_match = True
                                    else:
                                        pass
                                        logging.debug('No match, upload needed: album, filename, mime are ok, '
                                            'but [{} > {} min] [{} {}]'.format(
                                                ts_diff, args.minutes, media_on_disk.st_atime_ts, mi.creation_ts))
                                else:
                                    logging.debug("There was media_on_disk.exif_ts but it doesn't match Google's. So you'd better upload again, or adjust the tz")
                                    logging.debug('str: Timestamp from google: {}'.format(mi.media_metadata_creation_time))
                                    logging.debug('Timestamp, reformatted, from google: {}'.format(mi.creation_ts))
                                    logging.debug('str: Timestamp (exif) from media on disk: {}'.format(media_on_disk.exif_datetime))
                                    logging.debug('Timestamp (exif), reformatted from media on disk: {}'.format(media_on_disk.exif_ts(args.tz)))

                            else:
                                logging.debug('No match, upload: filename:ok, mimetype:ok, timestamp:not_okay: {}'.format(args.photos[0]))

                                # Used for debugging
                                logging.debug('Timestamp from google: {}'.format(mi.media_metadata_creation_time))
                                logging.debug('Timestamp (exif) from media on disk: {}'.format(media_on_disk.exif_datetime))
                                logging.debug('Timestamp st_ctime from media on disk: {}'.format(media_on_disk.st_ctime))
                                logging.debug('Timestamp st_atime from media on disk: {}'.format(media_on_disk.st_atime))
                                logging.debug('Timestamp st_mtime from media on disk: {}'.format(media_on_disk.st_mtime))

            break # Found an album match

        if not album_exists:
                logging.error('Match not possible.  Album name {} not found'.format(args.album_name))

    except Exception as e:
        logging.error('There was an error trying to do a match {}'.format(e))
    finally:
        logging.debug('media match: {}'.format(media_match))
        return media_match

def main():

    args = upload.parse_args()

    LOG_LEVEL = logging.INFO
    if args.log_level:
        LOG_LEVEL = logging.DEBUG


    logging.basicConfig(format='%(asctime)s %(module)s.%(funcName)s:%(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I_%M_%S %p',
                    filename=args.log_file,
                    level=LOG_LEVEL)

    if args.dry_run:
        logging.debug(args)
        if args.photos:
            logging.info('''

Path: {}
Exiting, --dry-run '''.format(args.photos[0]))
        else:
            logging.info('''
            No path provided 
            Exiting, --dry-run
                        ''')

    else:
        if args.photos:
            try:
                session = upload.get_authorized_session(args.auth_file, Path(args.credentials))
            except Exception as e:
                logging.error('{}'.format(e))
                sys.exit('''
                Exiting ....
                ''')

            posix_path = Path(args.photos[0])

            result = compare_media(args, posix_path=posix_path,
                    session=session, albums=upload.getAlbums(session, True))
            logging.info('Was there a match? {}'.format(result))

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
