import argparse
import io
import json
import logging
import os
from pathlib import Path
import platform
import sys
import textwrap

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials

from datetime import datetime
from dateutil.relativedelta import relativedelta
now = datetime.now()

import probe_meta

def parse_args(arg_input=None):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''\
    Upload photos and videos to Google Photos. And, add to an album created by this API.

        To do: fix for when the number of Alums > 50

        Windows paths should be like this: 'z:/path/to/some/file_or_dir'
        No wildcards like 'z:/path/*' in Windows.
        Use quotes, to prevent Windows from mangling, in most cases

        Note: st_atime is updated, at the time of upload, to help with timestamp comparison.
        That is, when a file is uploaded, the access time will be updated.
        This will be used when exif not available, as google uses the st_atime for it's
        creation time when exif is not available.
        
        On NAS, even ro, seem to update st_atime, when uploading.  This program, will  update st_atime (and st_ctime)
        upon a successful upload and placement into an album, to help figure out with google if an item
        needs to be sync'd.

           ''')) 

    parser.add_argument('--auth ', metavar='auth_file', dest='auth_file',
                    help='Optional: used to store tokens and credentials, such as the refresh token')
    parser.add_argument('-c', '--credentials', required=True,
                    help='Path to client_id.json.')
    parser.add_argument('--album', metavar='album_name', dest='album_name', required=True,
                    help='Required.  Name of photo album to create (if it doesn\'t exist). Any uploaded photos will be added to this album.')
    parser.add_argument('--log', metavar='log_file', dest='log_file',
                    help='Name of output file for log messages')
    parser.add_argument('--tz', metavar='time_zone', dest='tz', default='Europe/London',
                    help='If you suspect your exif timestamp is lacking a time zone, you can give it here, e.g. America/New_York.  The default is Europe/London')
    parser.add_argument('--dry-run', action='store_true',
                help='Prints photo file list and exits')
    parser.add_argument('--test-stat-times', action='store_true', dest='stat_times',
                help='Prints photo file list and checks to see if files would be updated based on timestamp, so --min adjustments can be made')
    parser.add_argument('--debug', dest='log_level', action='store_true',
                help='turn on debug logging')
    parser.add_argument('--recurse', dest='recurse', default='once',
                 choices=['none', 'once', 'all'],
                 help='Default: once')
    parser.add_argument('-e', '--exclude', metavar='exclude',type=str, nargs='*',
            help='List of extensions to exclude.  Example: --exclude .db .iso')
    parser.add_argument('-m', '--min', metavar='minutes',type=int, dest='minutes',
            default=0,
            help='Number of minutes in timestamp (st_atime) difference to accept as a match. '
            'That is, if filename, album, mimetype match, but exif.datetime does not exist, or is not a match '
            'then compare st_atime. Default: 0')
    parser.add_argument('photos', metavar='photo',type=str, nargs='*',
            help='List of filenames or directories of photos and videos to upload. '
                "Quote Windows path, to be safe: 'z:/path/to/file'.  "
                "Note: Windows does not handle wildcards such as 'z:/path/to/*', use files or dirs for Windows")

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

def get_authorized_session(auth_token_file, credentials,
        scopes=['https://www.googleapis.com/auth/photoslibrary',
                'https://www.googleapis.com/auth/photoslibrary.sharing',
                'https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata']):

    logging.debug('scopes: {}'.format(scopes))

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

def upload_photos(session, photo_file_list, album_name, args):

    number_added = 0
    album_id = create_or_retrieve_album(session, album_name) if album_name else None

    # interrupt upload if an upload was requested but could not be created
    if album_name and not album_id:
        return

    session.headers["Content-type"] = "application/octet-stream"
    session.headers["X-Goog-Upload-Protocol"] = "raw"

    albums_for_loop = getAlbums(session,True)
    for photo_file_name in photo_file_list:

            try:
                photo_file = open(photo_file_name, mode='rb')
                photo_bytes = photo_file.read()
            except OSError as err:
                logging.error("Could not read file \'{0}\' -- {1}".format(photo_file_name, err))
                continue

            session.headers["X-Goog-Upload-File-Name"] = photo_file_name.name

            find_match = media_comparison(args, [photo_file_name,],
                    session, albums_for_loop)
            yes_match = find_match.get(photo_file_name, False)
            if yes_match:
                logging.info("Match, not uploading -- {}".format(photo_file_name))
            else:
                logging.info("Uploading -- {}".format(photo_file_name))

            if not yes_match:
                try:
                    upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', photo_bytes)
                except OverflowError as e:
                    logging.info('''OverflowError: {} Trying chunking'''.format(e))
                    upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', data=read_file(photo_file_name))
                except Exception as e:
                    logging.info('''Maybe a timout error: {} Trying chunking'''.format(e))
                    upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', data=read_file(photo_file_name))
                except Exception as e:
                    logging.error("Even after chunking, could not upload file {}: {}".format(photo_file_name, e))
                    continue

                if (upload_token.status_code == 200) and (upload_token.content):
    
                    create_body = json.dumps({"albumId":album_id, "newMediaItems":[{"description":"","simpleMediaItem":{"uploadToken":upload_token.content.decode()}}]}, indent=4)
    
                    resp = session.post('https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate', create_body).json()
    
                    logging.debug("Server response mediaItems:batchCreate: {}".format(resp))
    
                    if "newMediaItemResults" in resp:
                        status = resp["newMediaItemResults"][0]["status"]
                        if status.get("code") and (status.get("code") > 0):
                            logging.error("Could not add \'{0}\' to library -- {1}".format(photo_file_name.name, status["message"]))
                        else:
                            logging.info("Added \'{}\' to library and album \'{}\' ".format(photo_file_name.name, album_name))
                            number_added += 1
                            # Linux: Changed: st_atime and st_ctime, Unchanged: st_mtime
                            # Windows: Changed: st_atime, Unchanged: st_mtime and st_ctime
                            try:
                                fn_stat = os.stat(photo_file_name)
                                logging.debug('stat before {}'.format(fn_stat))
                                os.utime(photo_file_name, (datetime.now().timestamp(), fn_stat.st_mtime))
                                logging.debug('stat after {}'.format(os.stat(photo_file_name)))
                            except Exception as e:
                                logging.info('Setting access time error: {}'.format(e))
                            finally:
                                pass
                    else:
                        logging.error("Could not add \'{0}\' to library. Server Response -- {1}".format(photo_file_name.name, resp))
    
                else:
                    logging.error("Could not upload \'{0}\'. Server Response - {1}".format(photo_file_name.name, upload_token))

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
    logging.debug('args: {}'.format(args))
    logging.debug('p: {}'.format(p))
    if args.recurse == 'none':
        return photo_file_list
    if args.recurse == 'once':
        list_dir = list(p.glob('*'))
        logging.debug('list_dir: {}'.format(list_dir))
    if args.recurse == 'all':
        list_dir = list(p.glob('**/*'))

    photo_file_list.extend(
        [pp for pp in list_dir if pp.is_file() if pp not in photo_file_list])

    return photo_file_list 

def dry_run_msg(photo_file_list):

        msg = '''
File list:
{}

Number of files: {}        
Exiting, dry-run'''.format(format_file_list(photo_file_list), len(photo_file_list))

        return msg
def media_comparison(args, photo_file_list, session, albums):
    results = {}
    for ea in photo_file_list:
        logging.debug('Type of ea in photo_file_list: {}:'.format(type(ea)))
        match = probe_meta.compare_media(args, posix_path=ea,
                session=session, albums=albums)
        logging.info('File match: {} - {}'.format(match, ea))

        results[ea] = match 

    return results

def main():

    args = parse_args()

    LOG_LEVEL = logging.INFO
    if args.log_level:
        LOG_LEVEL = logging.DEBUG


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
        msg = dry_run_msg(photo_file_list)
        print(msg)

        sys.exit()
        
    logging.debug('photo_file_list: {}:'.format(photo_file_list))

    session = get_authorized_session(args.auth_file, Path(args.credentials))
    logging.debug("Session set up, now uploading ... ")

    if args.stat_times:
        msg = dry_run_msg(photo_file_list)
        print(msg)
        print('''Before exiting, lets see if the exif or st_atime timestamps match:''')
        files_needed_uploaded = media_comparison(args, photo_file_list,
                session, getAlbums(session, True))
        sys.exit()

    number_added = upload_photos(session, photo_file_list, args.album_name, args)

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
