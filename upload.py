from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
import json
import os.path
import argparse
import logging
from pathlib import Path
import sys
import platform
import io

from datetime import datetime
from dateutil.relativedelta import relativedelta
now = datetime.now()

LOG_LEVEL = logging.INFO

def parse_args(arg_input=None):
    parser = argparse.ArgumentParser(description='Upload photos to Google Photos.')
    parser.add_argument('--auth ', metavar='auth_file', dest='auth_file',
                    help='Optional: used to storing refresh tokens, and ...')
    parser.add_argument('-c', '--credentials', required=True,
                    help='Path to client_id.json. Examples - Linux: ~/path/file, Windows: c:/path/file')
    parser.add_argument('--album', metavar='album_name', dest='album_name',
                    help='Name of photo album to create (if it doesn\'t exist). Any uploaded photos will be added to this album.')
    parser.add_argument('--log', metavar='log_file', dest='log_file',
                    help='Name of output file for log messages')
    parser.add_argument('--dry-run', action='store_true',
                help='Prints photo file list and exits')
    parser.add_argument('--recurse', dest='recurse', default='once',
                 choices=['none', 'once', 'all'],
                 help='Default: once')
    parser.add_argument('-e', '--exclude', metavar='exclude',type=str, nargs='*',
            help='List of extensions to exclude.  Example: --exclude .db .iso')
    parser.add_argument('photos', metavar='photo',type=str, nargs='*',
            help='List of filenames or directories of photos/videos to upload. Remember, Windows handle such things as /*')
    return parser.parse_args(arg_input)


def auth(scopes, credentials):
    flow = InstalledAppFlow.from_client_secrets_file(
        credentials,
        scopes=scopes)

    logging.debug('Starting local web server')
    credentials = flow.run_local_server(host='localhost',
                                        port=8080,
                                        authorization_prompt_message="",
                                        success_message='The auth flow is complete; you may close this window.',
                                        open_browser=True)

    logging.debug('Shuting down local web server')

    return credentials

def get_authorized_session(auth_token_file, credentials):

    scopes=['https://www.googleapis.com/auth/photoslibrary',
            'https://www.googleapis.com/auth/photoslibrary.sharing']

    logging.debug('entering def get_auth')
    cred = None

    if auth_token_file:
        logging.debug('is auth token file')
        try:
            cred = Credentials.from_authorized_user_file(auth_token_file, scopes)
        except OSError as err:
            logging.debug("Error opening auth token file - {0}".format(err))
        except ValueError:
            logging.debug("Error loading auth tokens - Incorrect format")


    logging.debug('line 53')
    if not cred:
        logging.debug("cred: looking")
        cred = auth(scopes, credentials)
        logging.debug("cred: {}".format(cred))

    logging.debug('line 56')
    session = AuthorizedSession(cred)

    if auth_token_file:
        try:
            save_cred(cred, auth_token_file)
        except OSError as err:
            logging.debug("Could not save auth tokens - {0}".format(err))

    return session


def save_cred(cred, auth_file):

    cred_dict = {
        'token': cred.token,
        'refresh_token': cred.refresh_token,
        'id_token': cred.id_token,
        'scopes': cred.scopes,
        'token_uri': cred.token_uri,
        'client_id': cred.client_id,
        'client_secret': cred.client_secret
    }

    with open(auth_file, 'w') as f:
        print(json.dumps(cred_dict), file=f)

# Generator to loop through all albums

def getAlbums(session, appCreatedOnly=False):

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

def create_or_retrieve_album(session, album_title):

# Find albums created by this app to see if one matches album_title

    for a in getAlbums(session, True):
        if a["title"].lower() == album_title.lower():
            album_id = a["id"]
            logging.info("Uploading into EXISTING photo album -- \'{0}\'".format(album_title))
            return album_id

# No matches, create new album

    create_album_body = json.dumps({"album":{"title": album_title}})
    #print(create_album_body)
    resp = session.post('https://photoslibrary.googleapis.com/v1/albums', create_album_body).json()

    logging.debug("Server response: {}".format(resp))

    if "id" in resp:
        logging.info("Uploading into NEW photo album -- \'{0}\'".format(album_title))
        return resp['id']
    else:
        logging.error("Could not find or create photo album '\{0}\'. Server Response: {1}".format(album_title, resp))
        return None

def read_file(path, block_size=io.DEFAULT_BUFFER_SIZE):
    '''
    https://stackoverflow.com/questions/519633/lazy-method-for-reading-big-file-in-python
    https://docs.python.org/3/library/functions.html?#iter
    '''

    with open(path, 'rb') as f:
        while True:
            piece = f.read(block_size)
            if piece:
                yield piece
            else:
                return

def upload_photos(session, photo_file_list, album_name):

    number_added = 0
    album_id = create_or_retrieve_album(session, album_name) if album_name else None

    # interrupt upload if an upload was requested but could not be created
    if album_name and not album_id:
        return

    session.headers["Content-type"] = "application/octet-stream"
    session.headers["X-Goog-Upload-Protocol"] = "raw"

    for photo_file_name in photo_file_list:

            try:
                photo_file = open(photo_file_name, mode='rb')
                photo_bytes = photo_file.read()
            except OSError as err:
                logging.error("Could not read file \'{0}\' -- {1}".format(photo_file_name, err))
                continue

            session.headers["X-Goog-Upload-File-Name"] = os.path.basename(photo_file_name)

            logging.info("Uploading photo -- \'{}\'".format(photo_file_name))

            try:
                upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', photo_bytes)
            except OverflowError as e:
                logging.info('''OverflowError: {} Trying chunking'''.format(e))
                upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', data=read_file(photo_file_name))
            except Exception as e:
                logging.error("Even after chunking, could not upload file \'{0}\' -- {1}".format(photo_file_name, e))
                continue

            if (upload_token.status_code == 200) and (upload_token.content):

                create_body = json.dumps({"albumId":album_id, "newMediaItems":[{"description":"","simpleMediaItem":{"uploadToken":upload_token.content.decode()}}]}, indent=4)

                resp = session.post('https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate', create_body).json()

                logging.debug("Server response: {}".format(resp))

                if "newMediaItemResults" in resp:
                    status = resp["newMediaItemResults"][0]["status"]
                    if status.get("code") and (status.get("code") > 0):
                        logging.error("Could not add \'{0}\' to library -- {1}".format(os.path.basename(photo_file_name), status["message"]))
                    else:
                        logging.info("Added \'{}\' to library and album \'{}\' ".format(os.path.basename(photo_file_name), album_name))
                        number_added += 1
                else:
                    logging.error("Could not add \'{0}\' to library. Server Response -- {1}".format(os.path.basename(photo_file_name), resp))

            else:
                logging.error("Could not upload \'{0}\'. Server Response - {1}".format(os.path.basename(photo_file_name), upload_token))

    try:
        del(session.headers["Content-type"])
        del(session.headers["X-Goog-Upload-Protocol"])
        del(session.headers["X-Goog-Upload-File-Name"])
    except KeyError:
        pass

    return number_added

def clean_file_list(photo_file_list, args):
    if not args.exclude:
        return list(filter(None, photo_file_list))

    photo_file_list_clean = []
    for p in photo_file_list:
        add_to_clean = True
        for ea in args.exclude:
            if p.name.lower().endswith(ea.lower()):
                add_to_clean = False
                break

        if add_to_clean:
            photo_file_list_clean.append(p)

    return list(filter(None, photo_file_list_clean))

def format_file_list(file_list):
        s = '' 
        for ea in file_list:
            s += '{}\n'.format(ea)

        return s.strip()

def recurse_dirs(p, args, photo_file_list=[]):
    logging.debug('recurse: {}'.format(args.recurse))
    if args.recurse == 'none':
        return photo_file_list
    if args.recurse == 'once':
        list_dir = list(p.glob('*/*'))
    if args.recurse == 'all':
        list_dir = list(p.glob('**/*'))

    photo_file_list.extend(
        [pp for pp in list_dir if pp.is_file() if pp not in photo_file_list])

    return photo_file_list 

def main():

    args = parse_args()

    logging.basicConfig(format='%(asctime)s %(module)s.%(funcName)s:%(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I_%M_%S %p',
                    filename=args.log_file,
                    level=LOG_LEVEL)

    logging.debug('args: {}'.format(args))
    photo_file_list = []
    photo_list = [Path(p) for p in args.photos]
    try:
        for p in photo_list:
            if p.is_file():
                if p not in photo_file_list:
                    photo_file_list.append(p)
            elif p.is_dir():
                photo_file_list = recurse_dirs(p, args, photo_file_list)
                #photo_file_list.extend(recursed_list)
                #if not args.recurse:
                #    photo_file_list.extend(
                #        [pp for pp in list(p.glob('*')) if pp.is_file() if pp not in photo_file_list])
            else:
               logging.error('''

This item is NOT a file or directory: {}
Exiting ...
'''.format(p,))
               sys.exit()
    except OSError as e:
         logging.error('{}'.format(e))
         logging.error('Exiting ...')
         sys.exit()

    photo_file_list = clean_file_list(photo_file_list, args)

    if args.dry_run:
        print('''
File list:
{}

Number of files: {}        
Exiting, dry-run'''.format(format_file_list(photo_file_list), len(photo_file_list)))
        sys.exit()
        
    logging.debug('photo_file_list: {}:'.format(photo_file_list))

    session = get_authorized_session(args.auth_file, Path(args.credentials))
    logging.debug("Session set up, now uploading ... ")

    number_added = upload_photos(session, photo_file_list, args.album_name)

    # As a quick status check, dump the albums and their key attributes

    print("{:<50} | {:>8} | {} ".format("PHOTO ALBUM","# PHOTOS", "IS WRITEABLE?"))

    for a in getAlbums(session):
        print("{:<50} | {:>8} | {} ".format(a["title"],a.get("mediaItemsCount", "0"), str(a.get("isWriteable", False))))

    return photo_file_list, number_added

if __name__ == '__main__':
    photo_file_list = []
    number_added = 0
  
    try:
        photo_file_list, number_added = main()
    except KeyboardInterrupt:
        logging.error('''
  
          Keyboard interrupt : ) exiting
  
          ''')
  
    finally:
  
        end = datetime.now()
        elapsed = relativedelta(end, now)
        print("""
Number of files added: {}
Number of files attempted: {}
Time elapsed: {} hours, {} minutes, {} seconds
""".format(number_added, len(photo_file_list), elapsed.hours, elapsed.minutes, elapsed.seconds))
  
# vim: ai et ts=4 sw=4 sts=4 nu
