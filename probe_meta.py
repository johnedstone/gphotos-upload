'''Retrieve google photos/videos metatdata'''

from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import logging
from pathlib import Path

from exif import Image
import filetype
from upload import parse_args, get_authorized_session

now = datetime.now()

LOG_LEVEL = logging.INFO

class Album:
    def __init__(self, id, title):
        self.id = id
        self.title = title

    def __repr__(self):
        return '{}'.format(self.title)

class Media:
    def __init__(self, mimetype, filename):
        self.filename = filename
        self.mimetype = mimetype
        self.media_metadata_creation_time = ''

    def __repr__(self):
        return '{}'.format(self.filename)

def get_albums(session):
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
            

        #img_id = 'AAZ8HlfaSd0mG4NZmjVn2iUibV2G6dS2SG9_JU3s_TdbdSX_iQI6YN33wXSHQoIYPw3MZV-CR8XopAK-p-OZghLBb7Nf1caCOQ'
        #resp = session.get('https://photoslibrary.googleapis.com/v1/mediaItems/{}'.format(img_id)).json()

    except Exception as e:
        logging.error('{}'.format(e))
        sys.exit()
    finally:
        return media_items

def main():

    args = parse_args()

    logging.basicConfig(format='%(asctime)s %(module)s.%(funcName)s:%(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I_%M_%S %p',
                    filename=args.log_file,
                    level=LOG_LEVEL)

    if args.dry_run:
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
            p = Path(args.photos[0])
            logging.debug('{}'.format(p.name))
            try:
                with open(p, 'rb') as fh:
                    image = Image(fh)
                
                ts = image.get('datetime', '')
                logging.debug('ts {}: {}'.format(p, ts))
                kind = filetype.guess('{}'.format(p))
                logging.debug(kind.mime)

                session = get_authorized_session(args.auth_file, Path(args.credentials),
                        scopes=['https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata'])
        
                albums = get_albums(session)
                logging.debug('Response: {}'.format(albums))
                for ea in albums:
                    if ea.title == 'test_album':
                        media_items = get_album_contents(session, ea)
                        logging.debug('{}'.format([(x.filename, x.mimetype, x.media_metadata_creation_time) for x in media_items]))
                    
                        for mi in media_items:
                            if mi.filename == p.name:
                                logging.debug('1: Found {}'.format(p))
                                if kind.mime == mi.mimetype:
                                    logging.debug('2: Found {}'.format(p))
                                    if mi.media_metadata_creation_time.strip('Z').replace('-', ':').replace('T', ' ') == image.get('datetime', ''):
                                        logging.info('3: Found {} in album'.format(p))


            except Exception as e:
                logging.error('{}'.format(e))

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
