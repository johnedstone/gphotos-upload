import io
import json
import logging
import os
from pathlib import Path
import platform
import sys

from datetime import datetime
from dateutil.relativedelta import relativedelta
now = datetime.now()

import probe_meta
from utils import album_contents, setup
def create_or_retrieve_album(session, album_title):

# Find albums created by this app to see if one matches album_title

    for a in album_contents.get_albums(session, True):
        if a["title"].lower() == album_title.lower():
            album_id = a["id"]
            logging.info("| Uploading into EXISTING photo album -- \'{0}\'".format(album_title))
            return album_id

# No matches, create new album

    create_album_body = json.dumps({"album":{"title": album_title}})
    #print(create_album_body)
    resp = session.post('https://photoslibrary.googleapis.com/v1/albums', create_album_body).json()

    logging.debug("Server response: {}".format(resp))

    if "id" in resp:
        logging.info("| Uploading into NEW photo album -- \'{0}\'".format(album_title))
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

def upload_photos(session, photo_file_list, args):

    number_added = 0
    number_passed_on_ts = 0
    album_id = create_or_retrieve_album(session, args.album_name)

    # interrupt upload if an upload was requested but could not be created
    if not album_id:
        return number_added, number_passed_on_ts

    album_exists, album_content_details = get_album_and_contents(session, args)

    session.headers["Content-type"] = "application/octet-stream"
    session.headers["X-Goog-Upload-Protocol"] = "raw"

    for photo_file_name in photo_file_list:

            try:
                photo_file = open(photo_file_name, mode='rb')
                photo_bytes = photo_file.read()
            except OSError as err:
                logging.error("Could not read file \'{0}\' -- {1}".format(photo_file_name, err))
                continue

            if not args.skip_compare:
                result = media_comparison(args, [photo_file_name,],
                        album_content_details)

                if result.get(photo_file_name, None):
                    if result[photo_file_name].get('media_match', None):
                        logging.info('| {:<7} | {:<7} {:<4} | {:<15} {:<4} | {:<5} {}'.format(
                        'Pass',
                        'In album:', str(result[photo_file_name]['media_exists_in_album']),
                        'Timestamp Match:', str(result[photo_file_name]['media_match']),
                        'Path:', photo_file_name))
    
                        number_passed_on_ts += 1 
                        continue
                    else:
                        logging.info('| {:<7} | {:<7} {:<4} | {:<15} {:<4} | {:<5} {}'.format(
                        'Upload',
                        'In album:', str(result[photo_file_name]['media_exists_in_album']),
                        'Timestamp Match:', str(result[photo_file_name]['media_match']),
                        'Path:', photo_file_name))
                else:
                    logging.error('Something odd here, skipping {}'.format(photo_file_name))
                    continue

            session.headers["X-Goog-Upload-File-Name"] = photo_file_name.name
            try:
                upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', data=read_file(photo_file_name))
                # Keep this for historical purposes
                #upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', photo_bytes)
                #except OverflowError as e:
                #except Exception as e:
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
                        logging.info('''| {:<7} | '{}' to library and album '{}' '''.format('Added', photo_file_name.name, args.album_name))
                        number_added += 1
                        # Linux: Changed: st_atime and st_ctime, Unchanged: st_mtime
                        # Windows: Changed: st_atime, Unchanged: st_mtime and st_ctime
                        try:
                            fn_stat = os.stat(photo_file_name)
                            logging.debug('stat before {}'.format(fn_stat))
                            os.utime(photo_file_name, (datetime.now().timestamp(), fn_stat.st_mtime))
                            logging.debug('stat after {}'.format(os.stat(photo_file_name)))
                        except Exception as e:
                            logging.info('|Setting access time: {} | Not critical, used for comparing access times'.format(e))
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

    return number_added, number_passed_on_ts

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
    #logging.debug('recurse: {}'.format(args.recurse))
    #logging.debug('args: {}'.format(args))
    #logging.debug('p: {}'.format(p))
    if args.recurse == 'none':
        return photo_file_list
    if args.recurse == 'once':
        list_dir = list(p.glob('*'))
        #logging.debug('list_dir: {}'.format(list_dir))
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

def media_comparison(args, photo_file_list, album_content_detail):
    results = {}
    for ea in photo_file_list:
        media_match, media_exists_in_album = probe_meta.compare_media(args, ea, album_content_detail)

        results[ea] = {'media_match': media_match,
                       'media_exists_in_album': media_exists_in_album}

    return results

def get_album_and_contents(session, args):
    album_exists = False
    album_itself = None
    album_content_details = None

    album_list = album_contents.get_albums(session, True)

    for a in album_list:
        if a['title'].lower() == args.album_name.lower():
            album_exists = True
            album_itself = a
            break

    if album_exists:
        album_content_generator = album_contents.get_album_contents(
                session, album_itself)
        album_content_details = album_contents.parse_media_items(album_content_generator)

    return album_exists, album_content_details

    
def main():
    existing_album = None
    args = setup.parse_args()

    LOG_LEVEL = logging.INFO
    if args.log_level:
        LOG_LEVEL = logging.DEBUG

        logging.basicConfig(format='%(asctime)s %(module)s.%(funcName)s:%(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %I_%M_%S %p',
                    filename=args.log_file,
                    level=LOG_LEVEL)
    else:
        logging.basicConfig(filename=args.log_file, level=LOG_LEVEL)

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
        
    #logging.debug('photo_file_list: {}:'.format(photo_file_list))

    session = setup.get_authorized_session(args.auth_file, Path(args.credentials))
    logging.debug("Session set up, now uploading ... ")


    if args.stat_times:
        album_exists, album_content_details = get_album_and_contents(session, args)
        if album_exists:
            result = media_comparison(args, photo_file_list,
                    album_content_details)
            if result:
                #logging.debug('{}'.format(result))
                for ea in result.keys():
                    logging.info('|{:<16} {:<5} | {:<16} {:<5} | {:<5} {}'.format(
                    'Exists in album:', str(result[ea]['media_exists_in_album']),
                    'Timestamp Match:', str(result[ea]['media_match']),
                    'Path:', ea))

            sys.exit()
        else:
            logging.info('''
Album "{}" does not exist, so no comparison is possible!
Exiting ...'''.format(args.album_name))

        sys.exit()

    # Okay, let's get to work
    number_added, number_passed_on_ts = upload_photos(session, photo_file_list, args)

    # As a quick status check, dump the albums and their key attributes

    logging.info("|{:<50} | {:>8} | {} ".format("PHOTO ALBUM","# PHOTOS", "IS WRITEABLE?"))

    for a in album_contents.get_albums(session):
        print("{:<50} | {:>8} | {} ".format(a["title"],a.get("mediaItemsCount", "0"), str(a.get("isWriteable", False))))

    return photo_file_list, number_added, number_passed_on_ts

if __name__ == '__main__':
    photo_file_list = []
    number_added = 0
    number_passed_on_ts = 0
    print_times = False
  
    try:
        photo_file_list, number_added, number_passed_on_ts = main()
        print_times = True
    except KeyboardInterrupt:
        logging.error('''
  
          Keyboard interrupt : ) exiting
  
          ''')
  
    finally:
  
        if print_times:
            end = datetime.now()
            elapsed = relativedelta(end, now)
            print('')
            print('{:<50} | {}'.format('Number of files added', number_added))
            print('{:<50} | {}'.format('Number of files, not added, based on timestamp', number_passed_on_ts))
            print('{:<50} | {}'.format('Number of files attempted', len(photo_file_list)))
            print('{:<50} | {} hours, {} minutes, {} seconds'.format('Time elapsed', elapsed.hours, elapsed.minutes, elapsed.seconds))
  
# vim: ai et ts=4 sw=4 sts=4 nu
