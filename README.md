# gphotos-upload, forked
__Original gphotos-upload Readme is further down below. New features of fork are listed here__

## Current Issues
* 02-Apr-2020: these files are being uploaded at the original size (per API documentation), and
will be counted agains storage limits.  Go to settings -> recover and choose compress storage.

## Fixed
* 02-Apr-2020: noted OverflowError on Linux, with 2.5GB mp4, but not on Windows.
Implemented chunked data for requests.post()

## Features of this fork:
* Using pathlib, upload.py is now compatible on Linux and Windows
* On Windows, upload.py has been tested with Anaconda Powershell Prompt
    * conda install git
    * conda install google-auth-oauthlib
* Since path name expansion with wildcards is not available on Windows,
only filenames and/or a directories are acceptable, when using upload.py
on Windows.
An example would be `z:/path/to/file z:/path/to/dir`
* On Linux, upload.py will take filenames directly or with path name expansion, and/or directories.
An example would be `/path/to/file /path/to/* /path/to/dir`
* upload.py does not recurse directories.
This can be done by listing multiple directories, on both Linux and Windows.

## Usage, revised

```
usage: upload.py [-h] [--auth  auth_file] -c CREDENTIALS [--album album_name] [--log log_file] [--dry-run] [photo [photo ...]]

Upload photos to Google Photos.

positional arguments:
  photo                 List of filename(s) or directory(s) of photo(s) to upload. Linux: /file /* /, Windows (no wildcards): z:/path/file z:/path/dir

optional arguments:
  -h, --help            show this help message and exit
  --auth  auth_file     file for reading/storing user authentication tokens (not used/tested for this fork)
  -c CREDENTIALS, --credentials CREDENTIALS
                        Path to client_id.json. Examples - Linux: ~/path/file, Windows: c:/path/file
  --album album_name    name of photo album to create (if it doesn't exist). Any uploaded photos will be added to this album.
  --log log_file        name of output file for log messages
  --dry-run             Prints photo file list and exits
```

### In progress

* Selenium: webbrowser_selenium.py

*Notes: SSL errors - http://allselenium.info/selfsigned-certificates-python-selenium/*

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

 
