# gphotos-upload, forked
__Original gphotos-upload Readme is further down below. New features of fork are listed here__

## Current Issues
* 02-Apr-2020: these files are being uploaded at the original size (per API documentation), and
will be counted agains storage limits.  To remdiate, go to settings -> "recover storage" and choose compress storage, after uploading.

### To do
* Selenium: webbrowser_selenium.py *Notes: SSL errors - http://allselenium.info/selfsigned-certificates-python-selenium/*

## Fixed
* 02-Apr-2020: noted OverflowError on Linux, with 2.5GB mp4, but not on Windows.
Implemented chunked data for all uploads.

## Features of this fork:
* Using pathlib, upload.py is now compatible on Linux and Windows
* added --dry-run --credentials, --exclude, --recurse, --min, --test-stat-times, --tz, --skip-compare
* Can check exif or ts_atime to determine if file has been previous uploaded. st_atime is updated upon uploading.
* On Windows, upload.py has been tested with Anaconda Powershell Prompt
    * conda install git
    * conda install google-auth-oauthlib
    * conda install arrow
    * conda install -c conda-forge filetype
    * conda install filetype
    * conda install -c conda-forge ffmpeg
* Since path name expansion with wildcards is not available on Windows,
only filenames and/or a directories are acceptable, when using upload.py
on Windows.  An example would be `z:/path/to/file z:/path/to/dir`
* On Linux, upload.py will take filenames directly or with path name expansion, and/or directories.
An example would be `/path/to/file /path/to/* /path/to/dir`

## Usage, revised

```
usage: upload.py [-h] [--auth  auth_file] -c CREDENTIALS --album album_name [--log log_file] [--tz time_zone] [--dry-run] [--skip-compare] [--test-stat-times] [--debug] [--recurse {none,once,all}]
                 [-e [exclude [exclude ...]]] [-m minutes]
                 [photo [photo ...]]

Upload photos and videos to Google Photos. And, add to an album created by this API.

    Windows paths should be like this: 'z:/path/to/some/file_or_dir'
    No wildcards like 'z:/path/*' in Windows.
    Use quotes, to prevent Windows from mangling, in most cases

    Note: treating album names as case insensitive

    Note: Google's API only uploads to albums created by API

    Note: images exif timestamps do not have TZ.  Google assumes/uses UTC.
    --tz will help compare the exif if you know that the TZ is not UTC.
    Use this to compare if you need to upload image again.

    Note: st_atime is updated, at the time of upload, to help with timestamp comparison.
    That is, when a file is uploaded, the access time will be updated.
    This will be used when exif or ffmpeg creation time is not available,
    as google uses the st_atime for it's creation time when neither are available.

    Uploading from NAS: in some cases, permissions might not allow updating access time (st_atime),
    resulting in a non-critical error.  Non-critical, in that updating st_atime
    is only used for comparing timestamps later.

positional arguments:
  photo                 List of filenames or directories of photos and videos to upload. Quote Windows path, to be safe: 'z:/path/to/file'. Note: Windows does not handle wildcards such as
                        'z:/path/to/*', use files or dirs for Windows

optional arguments:
  -h, --help            show this help message and exit
  --auth  auth_file     Optional: used to store tokens and credentials, such as the refresh token
  -c CREDENTIALS, --credentials CREDENTIALS
                        Path to client_id.json.
  --album album_name    Required. Name of photo album to create (if it doesn't exist). Any uploaded photos will be added to this album.
  --log log_file        Name of output file for log messages
  --tz time_zone        If you suspect your exif timestamp is lacking a time zone, you can give it here, e.g. America/New_York. The default is Europe/London
  --dry-run             Prints photo file list and exits
  --skip-compare        Skip comparing filename, mime_time, exif and timestamp. Just upload
  --test-stat-times     Prints photo file list and checks to see if files would be updated based on timestamp, so --min adjustments can be made
  --debug               turn on debug logging
  --recurse {none,once,all}
                        Default: once
  -e [exclude [exclude ...]], --exclude [exclude [exclude ...]]
                        List of extensions to exclude. Example: --exclude .db .iso
  -m minutes, --min minutes
                        Number of minutes in timestamp (st_atime) difference to accept as a match. That is, if filename, album, mimetype match, but exif.datetime does not exist, or is not a match then
                        compare st_atime. Default: 0
```

# gphotos-upload, original
__From: https://github.com/eshmu/gphotos-upload.git__

Simple but flexible script to upload photos to Google Photos. Useful if you have photos in a directory structure that you want to reflect as Google Photos albums.

## Usage 

```
usage: upload.py [-h] [--auth  auth_file] [--album album_name]
                 [--log log_file]
                 [photo [photo ...]]

Upload photos to Google Photos.

positional arguments:
  photo               filename of a photo to upload

optional arguments:
  -h, --help          show this help message and exit
  --auth  auth_file   file for reading/storing user authentication tokens
  --album album_name  name of photo album to create (if it doesn't exist). Any
                      uploaded photos will be added to this album.
  --log log_file      name of output file for log messages
```


## Setup

### Obtaining a Google Photos API key

1. Obtain a Google Photos API key (Client ID and Client Secret) by following the instructions on [Getting started with Google Photos REST APIs](https://developers.google.com/photos/library/guides/get-started)

**NOTE** When selecting your application type in Step 4 of "Request an OAuth 2.0 client ID", please select "Other". There's also no need to carry out step 5 in that section.

2. Replace `YOUR_CLIENT_ID` in the client_id.json file with the provided Client ID. 
3. Replace `YOUR_CLIENT_SECRET` in the client_id.json file wiht the provided Client Secret.

### Installing dependencies and running the script

1. Make sure you have [Python 3.7](https://www.python.org/downloads/) installed on your system
2. If needed, install [pipenv](https://pypi.org/project/pipenv/) via `pip install pipenv`
3. Change to the directory where you installed this script
4. Run `pipenv install` to download and install all the dependencies
5. Run `pipenv shell` to open a shell with all the dependencies available (you'll need to do this every time you want to run the script)
6. Now run the script via `python upload.py` as desired. Use `python upload.py -h` to get help.

 
