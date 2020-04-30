import argparse
import json
import logging
import textwrap

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials

def parse_args(arg_input=None):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''\
    Upload photos and videos to Google Photos. And, add to an album created by this API.

        To do: fix for when the number of media_items in album > 50

        Windows paths should be like this: 'z:/path/to/some/file_or_dir'
        No wildcards like 'z:/path/*' in Windows.
        Use quotes, to prevent Windows from mangling, in most cases

        Note: treating album names as case insensitive

        Note: API only uploads to albums created by API

        Note: images exif timestamps do not have TZ.  Google assumes/uses UTC.
        --tz will help compare the exif if you know that the TZ is not UTC.
        Use this to compare if you need to upload image again.

        Note: st_atime is updated, at the time of upload, to help with timestamp comparison.
        That is, when a file is uploaded, the access time will be updated.
        This will be used when exif not available, as google uses the st_atime for it's
        creation time when exif is not available.
        
        Uploading from NAS: in some cases, permissions might not allow updating access time (st_atime),
        and a non-critical error is displayed.  Updating st_atime is only used for comparing timestamps.

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
    parser.add_argument('--skip-compare', action='store_true',
                help='Skip comparing filename, mime_time, exif and timestamp.  Just upload')
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

