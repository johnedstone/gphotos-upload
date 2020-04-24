# gphotos-upload, forked
__Original gphotos-upload Readme is further down below. New features of fork are listed here__

## Current Issues
* 02-Apr-2020: these files are being uploaded at the original size (per API documentation), and
will be counted agains storage limits.  To remdiate, go to settings -> "recover storage" and choose compress storage, after uploading.

### To do

* Check if file exists, so time is not lost uploading. This may be hard to do,
as Google does not return any checksum to you of the original photo.

* Selenium: webbrowser_selenium.py *Notes: SSL errors - http://allselenium.info/selfsigned-certificates-python-selenium/*

## Fixed
* 02-Apr-2020: noted OverflowError on Linux, with 2.5GB mp4, but not on Windows.
Implemented chunked data for requests.post()

## Features of this fork:
* Using pathlib, upload.py is now compatible on Linux and Windows
* added --dry-run --credentials, --exclude, --recurse, --min, --dry-run-plus
* On Windows, upload.py has been tested with Anaconda Powershell Prompt
    * conda install git
    * conda install google-auth-oauthlib
    * conda install arrow
    * conda install -c conda-forge filetype
    * conda install filetype
* Since path name expansion with wildcards is not available on Windows,
only filenames and/or a directories are acceptable, when using upload.py
on Windows.  An example would be `z:/path/to/file z:/path/to/dir`
* On Linux, upload.py will take filenames directly or with path name expansion, and/or directories.
An example would be `/path/to/file /path/to/* /path/to/dir`

## Usage, revised

```
usage: upload.py [-h] [--auth  auth_file] -c CREDENTIALS [--album album_name] [--log log_file] [--dry-run] [--dry-run-plus] [--debug] [--recurse {none,once,all}] [-e [exclude [exclude ...]]]
                 [-m minutes]
                 [photo [photo ...]]

Upload photos and videos to Google Photos. And, add to an album created by this API.

    Windows paths should be like this: 'z:/path/to/some/file_or_dir'
    No wildcards like 'z:/path/*' in Windows.
    Use quotes, to prevent Windows from mangling, in most cases

    Working on updating st_atime, at time of upload, to help with timestamp comparison.
    That is, when a file is uploaded, the access time will be updated.
    This will be used when exif not available, as google uses the st_atime for it's
    creation time when exif is not available.

    On NAS, even ro, seem to update st_atime, when uploading.  This program, will  update st_atime (and st_ctime)
    upon a successful upload and placement into an album, to help figure out with google if an item
    needs to be sync'd.

positional arguments:
  photo                 List of filenames or directories of photos and videos to upload. Quote Windows path, to be safe: 'z:/path/to/file'. Note: Windows does not handle wildcards such as
                        'z:/path/to/*', use files or dirs for Windows

optional arguments:
  -h, --help            show this help message and exit
  --auth  auth_file     Optional: used to store tokens and credentials, such as the refresh token
  -c CREDENTIALS, --credentials CREDENTIALS
                        Path to client_id.json.
  --album album_name    Name of photo album to create (if it doesn't exist). Any uploaded photos will be added to this album.
  --log log_file        Name of output file for log messages
  --dry-run             Prints photo file list and exits
  --dry-run-plus        Not implemented, yet. Prints photo file list and checks to see if files would be updated, so --min adjustments can be made
  --debug               turn on debug logging
  --recurse {none,once,all}
                        Default: once
  -e [exclude [exclude ...]], --exclude [exclude [exclude ...]]
                        List of extensions to exclude. Example: --exclude .db .iso
  -m minutes, --min minutes
                        Not completely implemented yet. Developing. Number of minutes in timestamp (st_atime) difference to accept, if filename, album, mimetype match, but exif.datetime does not exist,
                        when deciding to upload again. Default: 0
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

 
