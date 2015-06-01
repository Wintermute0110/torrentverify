#!/usr/bin/python3
# Torrentverify

# Copyright (c) 2015 Wintermute0110 <wintermute0110@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import io
import sys
import os
import hashlib
import argparse
import bencodepy

# --- Global variables
__software_version = '0.1.0';

# --- Program options (from command line)
__prog_options_deleteWrongSizeFiles = 0
__prog_options_chopWrongSizeFiles = 0

# Unified torrent information object. Works for torrent files with 1 or several
# files.
class Torrent:
  torrent_file = None
  dir_name = None
  piece_length = 0
  num_pieces = 0
  num_files = 0
  file_name_list = []
  file_length_list = []
  pieces_hash_list = []

# --- Functions ---------------------------------------------------------------
# Convert a list of bytes into a path
def join_file_byte_list(file_list_bytes):
  file_list_string = []
  for i in range(len(file_list_bytes)):
    file_list_string.append(file_list_bytes[i].decode("utf-8"))

  return '/'.join(file_list_string)

# Returns a Torrent object
__debug_torrent_extract_metadata = 0
def extract_torrent_metadata(filename):
  torrent = Torrent
  torrent.torrent_file = filename
  
  # print('Opening torrent file {0}'.format(torrentFileName))
  torrent_file = open(torrentFileName, "rb")

  sys.stdout.write('Bdecoding torrent file {0}... '.format(torrentFileName))
  sys.stdout.flush()
  torr_ordered_dict = bencodepy.decode(torrent_file.read())
  info_ordered_dict = torr_ordered_dict[b'info']
  sys.stdout.write('done\n')

  if __debug_torrent_extract_metadata:
    print('=== Dumping torrent root ===')
    for key in torr_ordered_dict:
      print(' key {0} value {1}'.format(key, torr_ordered_dict[key]))

    print('=== Dumping torrent info ===')
    for key in info_ordered_dict:
      print(' key {0} value {1}'.format(key, info_ordered_dict[key]))

  # If torrent info has files field then torrent has several files
  if b'files' in info_ordered_dict:
    t_name = info_ordered_dict[b'name'] # Directory name to store torrent
    t_piece_length = info_ordered_dict[b'piece length']
    t_files_list = info_ordered_dict[b'files']
    
    # --- Converts the string into a file-like object
    t_pieces = info_ordered_dict[b'pieces']
    pieces = io.BytesIO(t_pieces)
    # --- Ensure num_pieces is integer
    num_pieces = len(t_pieces) / 20
    if not num_pieces.is_integer():
      print('num_pieces {0} is not integer!'.format(num_pieces))
      sys.exit(1)
    num_pieces = int(num_pieces)

    # --- Fill torrent object
    torrent.dir_name = t_name.decode("utf-8")
    torrent.piece_length = t_piece_length
    torrent.num_pieces = num_pieces
    torrent.num_files = len(t_files_list)
    for i in range(num_pieces):
      hash = pieces.read(20)
      torrent.pieces_hash_list.append(hash)
    torrent.total_bytes = 0
    for t_file in t_files_list:
      torrent.file_name_list.append(join_file_byte_list(t_file[b'path']))
      # print(type(t_file[b'length'])) # type is <class 'int'>
      torrent.file_length_list.append(t_file[b'length'])
      torrent.total_bytes += t_file[b'length']

    # DEBUG
    if __debug_torrent_extract_metadata:
      print(' Directory {0}'.format(t_name))
      print(' Piece length {0}'.format(t_piece_length))
      print(' Number of pieces {0}'.format(num_pieces))
      print(' Number of files {0}'.format(len(t_files_list)))
      print(' len(t_pieces) =  {0}'.format(len(t_pieces)))
      print(' num_pieces * piece_length = {0}'.format(num_pieces * t_piece_length))
      print(' len(torrent.pieces_hash_list) = {0}'.format(len(torrent.pieces_hash_list)))
      # print('File list')
      # for t_file in t_files_list:
      #   print(' path {0} length {1}'.format(t_file[b'path'], t_file[b'length']))
      
  # Single file torrent
  else:
    t_name = info_ordered_dict[b'name'] # File name11
    t_piece_length = info_ordered_dict[b'piece length']
    t_length = info_ordered_dict[b'length']
    
    # --- Converts the string into a file-like object
    t_pieces = info_ordered_dict[b'pieces']
    pieces = io.BytesIO(t_pieces)
    # --- Ensure num_pieces is integer
    num_pieces = len(t_pieces) / 20
    if not num_pieces.is_integer():
      print('num_pieces {0} is not integer!'.format(num_pieces))
      sys.exit(1)
    num_pieces = int(num_pieces)

    # --- Fill torrent object
    torrent.piece_length = t_piece_length
    torrent.num_pieces = num_pieces
    torrent.num_files = 1
    torrent.file_name_list.append(t_name)
    torrent.file_length_list.append(t_length)
    for i in range(num_pieces):
      hash = pieces.read(20)
      torrent.pieces_hash_list.append(hash)
    torrent.total_bytes = t_length

    # DEBUG
    if __debug_torrent_extract_metadata:
      print(' Filename {0}'.format(t_name))
      print(' Size {0}'.format(t_length))
      print(' Piece length {0}'.format(t_piece_length))
      print(' Number of pieces {0}'.format(num_pieces))
      print(' Number of files {0}'.format(1))
      print(' len(t_pieces) =  {0}'.format(len(t_pieces)))
      print(' num_pieces * piece_length = {0}'.format(num_pieces * t_piece_length))
      print(' len(torrent.pieces_hash_list) = {0}'.format(len(torrent.pieces_hash_list)))

  return torrent

def list_torrent_contents(torrent_obj):
  print('Printing torrent file contents...')

  # --- Print list of files
  print('    F#            Bytes  File name')
  print('------ ----------------  --------------')
  for i in range(len(torrent_obj.file_name_list)):
    print('{0:6} {1:16,}  {2}'
      .format(i+1, torrent_obj.file_length_list[i], torrent_obj.file_name_list[i]))

  # --- Print torrent metadata
  print('')
  print('Torrent file      : {0}'.format(torrent_obj.torrent_file))
  print('Torrent directory : {0}'.format(torrent_obj.dir_name))
  print('Pieces info       : {0:10,} pieces, {1:16,} bytes/piece'
    .format(torrent_obj.num_pieces, torrent_obj.piece_length))
  print('Files info        : {0:10,} files,  {1:16,} total bytes'
    .format(torrent_obj.num_files, torrent_obj.total_bytes))
  # print('Torrent comment  : {0}'.format(torrent.comment))

# Checks that files listed in the torrent file exist, and that file size
# is correct
# Status can be: OK, MISSING, BAD_SIZE
def check_torrent_files_only(data_directory, torrent_obj):
  print('Checking torrent files and sizes (NOT hash)')
  num_files_OK = 0
  num_files_bad_size = 0
  num_files_missing = 0
  print('    F#   Status     Actual Bytes    Torrent Bytes  File name')
  print('------ -------- ---------------- ----------------  --------------')
  for i in range(len(torrent_obj.file_name_list)):
    file_size = -1
    filename_path = os.path.join(data_directory, torrent_obj.dir_name, torrent_obj.file_name_list[i])
    # print(filename_path)
    file_exists = os.path.isfile(filename_path)
    if file_exists:
      file_size = os.path.getsize(filename_path)
      if file_size == torrent_obj.file_length_list[i]:
        status = 'OK'
        num_files_OK += 1
      else:
        status = 'BAD_SIZE'
        num_files_bad_size += 1
    else:
      status = 'MISSING'
      num_files_missing += 1
    print('{0:6} {1:>8} {2:16,} {3:16,}  {4}'
      .format(i+1, status, file_size, torrent_obj.file_length_list[i], torrent_obj.file_name_list[i]))
    
    # Delete files with bad size... to they can be downloaded again
    # WARNING may deleted useful files that can be recovered by truncating them to
    #         the correct size.
    # if status == 'BAD_SIZE':
    #   os.unlink(filename_path)

  # --- Print torrent metadata
  print('')
  print('Torrent file      : {0}'.format(torrent_obj.torrent_file))
  print('Pieces info       : {0:10,} pieces, {1:16,} bytes/piece'.format(torrent_obj.num_pieces, torrent_obj.piece_length))
  print('Files info        : {0:10,} files,  {1:16,} total bytes'.format(torrent_obj.num_files, torrent_obj.total_bytes))
  print('Torrent directory : {0}'.format(torrent_obj.dir_name))
  print('Data directory    : {0}'.format(data_directory))
  print('Files OK          : {0:,}'.format(num_files_OK))
  print('Files bad size    : {0:,}'.format(num_files_bad_size))
  print('Files missing     : {0:,}'.format(num_files_missing))

# Lists torrent unneeded files
def list_torrent_unneeded_files(data_directory, torrent_obj):
  print('Listing torrent unneeded files')

  # --- Make a recursive list of files in torrent data directory
  torrent_directory = os.path.join(data_directory, torrent_obj.dir_name)
  file_list = []
  for root, dirs, files in os.walk(torrent_directory, topdown=False):
    for name in files:
      file_list.append(os.path.join(root, name))
      # print(name)
    # for name in dirs:
      # print(os.path.join(root, name))
      # print(name)
      
  # --- Make a set of files in the list of torrent metadata files
  torrent_file_list = []
  for i in range(len(torrent_obj.file_name_list)):
    filename_path = os.path.join(data_directory, torrent_obj.dir_name, torrent_obj.file_name_list[i])
    # print(filename_path)
    torrent_file_list.append(filename_path);
  torrent_file_set = set(torrent_file_list)

  # Check number of elements in list and set are the same. This means there are no
  # duplicate files in the list
  if len(torrent_file_list) != len(torrent_file_set):
    print('len(torrent_file_list) != len(torrent_file_set)')
    exit(1)

  # --- Check if files in the torrent directory are on the metadata file set
  num_needed = 0
  num_redundant = 0
  for i in range(len(file_list)):
    if file_list[i] not in torrent_file_set:
      print('UNNEEDED  {0}'.format(file_list[i]))
      num_redundant += 1
    else:
      print('      OK  {0}'.format(file_list[i]))
      num_needed += 1
    
  print('Files in torrent data directory : {0:,}'.format(len(file_list)))
  print('Files in torrent                : {0:,}'.format(len(torrent_file_list)))
  print('Needed                          : {0:,}'.format(num_needed))
  print('Unneeded                        : {0:,}'.format(num_redundant))

# Removes unneeded files from torrent download directory
def delete_torrent_unneeded_files(data_directory, torrent_obj):
  print('Removing torrent unneeded files')

  # --- Make a recursive list of files in torrent data directory
  torrent_directory = os.path.join(data_directory, torrent_obj.dir_name)
  file_list = []
  for root, dirs, files in os.walk(torrent_directory, topdown=False):
    for name in files:
      file_list.append(os.path.join(root, name))
      
  # --- Make a set of files in the list of torrent metadata files
  torrent_file_list = []
  for i in range(len(torrent_obj.file_name_list)):
    filename_path = os.path.join(data_directory, torrent_obj.dir_name, torrent_obj.file_name_list[i])
    torrent_file_list.append(filename_path);
  torrent_file_set = set(torrent_file_list)
  # Check number of elements in list and set are the same. This means there are no
  # duplicate files in the list
  if len(torrent_file_list) != len(torrent_file_set):
    print('len(torrent_file_list) != len(torrent_file_set)')
    exit(1)

  # --- Check if files in the torrent directory are on the metadata file set
  num_needed = 0
  num_redundant = 0
  for i in range(len(file_list)):
    if file_list[i] not in torrent_file_set:
      print('UNNEEDED  {0}'.format(file_list[i]))
      num_redundant += 1
      # Delete unneeded file
      print('      RM  {0}'.format(file_list[i]))
      os.unlink(file_list[i])
    else:
      # Do not list needed files
      num_needed += 1
    
  print('Files in torrent data directory : {0:,}'.format(len(file_list)))
  print('Files in torrent                : {0:,}'.format(len(torrent_file_list)))
  print('Needed                          : {0:,}'.format(num_needed))
  print('Unneeded                        : {0:,}'.format(num_redundant))

def pieces_generator(data_directory, torrent):
  """Yield pieces from download file(s)."""
  piece_length = torrent.piece_length
  
  # yield pieces from a multi-file torrent
  # Iterator finishes when function exits but not with the yield keyword
  if torrent.num_files > 1:
    piece = b''
    file_idx_list = []
    # --- Iterate through all files
    # print('{0:6d}'.format(pieces_counter))
    for i in range(len(torrent_obj.file_name_list)):
      path = os.path.join(data_directory, torrent_obj.dir_name, torrent_obj.file_name_list[i])

      # CHECK file
      # If file does not exist then bogus should be created for checksum calculation. Otherwise,
      # all files after a non-existant file will have bad checksum
      # Same situation when file size is not correct

      # --- Read file
      sfile = open(path, "rb")
      file_idx_list.append(i)
      while True:
        piece += sfile.read(piece_length-len(piece))
        if len(piece) != piece_length:
          sfile.close()
          break
        yield (piece, file_idx_list)
        # --- Go for another piece
        piece = b''
        file_idx_list = []
        file_idx_list.append(i)
    if piece != b'':
      # print('yielding (last?) piece')
      yield (piece, file_idx_list)

  # yield pieces from a single file torrent
  else:
    path = info['name']
    print(path)
    sfile = open(path.decode('UTF-8'), "rb")
    while True:
      piece = sfile.read(piece_length)
      if not piece:
        sfile.close()
        return
      yield piece

# Checks torrent files against SHA1 hash for integrity
def check_torrent_files_hash(data_directory, torrent_obj):
  print('    P#     F#  HStatus  FStatus     Actual Bytes    Torrent Bytes  File name')
  print('------ ------ -------- -------- ---------------- ----------------  --------------')
  
  # --- Iterate through pieces
  piece_index = 0
  good_pieces = 0
  bad_pieces = 0
  for piece, file_idx_list in pieces_generator(data_directory, torrent_obj):
    # --- Compare piece hash with expected hash
    piece_hash = hashlib.sha1(piece).digest()
    if piece_hash != torrent_obj.pieces_hash_list[piece_index]:
      piece_sha1_OK = 0
      bad_pieces += 1
    else:
      piece_sha1_OK = 1
      good_pieces += 1

    # --- Print information
    for i in range(len(file_idx_list)):
      if piece_sha1_OK:
        hash_status = 'SHA1 OK'
      else:
        hash_status = 'SHA1 BAD'
      file_idx = file_idx_list[i]
      path = os.path.join(data_directory, torrent_obj.dir_name, torrent_obj.file_name_list[file_idx])
      file_exists = os.path.isfile(path)
      if file_exists:
        file_size = os.path.getsize(path)
        if file_size == torrent_obj.file_length_list[file_idx]:
          file_status = 'OK'
        else:
          file_status = 'BAD_SIZE'
      else:
        file_status = 'MISSING'
      print('{0:6d} {1:6} {2:>8} {3:>8} {4:16,} {5:16,}  {6}'
        .format(piece_index+1, file_idx+1, hash_status, file_status, file_size,
                torrent_obj.file_length_list[file_idx], torrent_obj.file_name_list[file_idx]))
    # stop for DEBUG
    # if not piece_sha1_OK:
    #   print('Errors found. Exiting.')
    #   exit(1)

    # Increment piece counter
    piece_index += 1

  # ensure we've read all pieces
  print('Checked {0} pieces out of {1}'.format(piece_index, torrent_obj.num_pieces))
  print('Good pieces {0} / Bad pieces {1}'.format(good_pieces, bad_pieces))

def do_printHelp():
  print("""
\033[32mUsage: torrentverify.py -t file.torrent -d /dataDir/ <options>\033[0m
    If not options are specified...

\033[32mOptions:
  \033[35m-t\033[0m \033[31m[logName]\033[0m
    Torrent file.

  \033[35m-d\033[0m
    Directory where torrent is downloaded.
 
  \033[35m--check\033[0m
    Write me
 
  \033[35m--checkUnneeded\033[0m
    Write me

  \033[35m--checkHash\033[0m
    Write me

  \033[35m--deleteWrongSizeFiles\033[0m
    Write me
 
  \033[35m--chopWrongSizeFiles\033[0m
    Write me""")

# -----------------------------------------------------------------------------
# main function
# -----------------------------------------------------------------------------
print('\033[36mTorrentVerify\033[0m' + ' version ' + __software_version)

# --- Command line parser
parser = argparse.ArgumentParser()
parser.add_argument('-t', help="Torrent file", nargs = 1)
parser.add_argument("-d", help="Data directory", action="store_true")
parser.add_argument("--check", help="Do a basic torrent check: files there or not and size", action="store_true")
parser.add_argument("--checkUnneeded", help="Write me", action="store_true")
parser.add_argument("--checkHash", help="Full check with SHA1 hash", action="store_true")
parser.add_argument("--deleteWrongSizeFiles", help="Delete files having wrong size", action="store_true")
parser.add_argument("--chopWrongSizeFiles", help="Chop files with incorrect size to right one", action="store_true")
args = parser.parse_args();

# --- Read arguments
torrentFileName = data_directory = None
check = checkUnneeded = checkHash = 0

if args.t:
  torrentFileName = args.t[0];
if args.d:
  data_directory = args.d;
  
# Arguments that define behaviour
if args.check:
  check = 1
if args.checkUnneeded:
  checkUnneeded = 1  
if args.checkHash:
  checkHash = 1

# Optional arguments
if args.deleteWrongSizeFiles:
  __prog_options_deleteWrongSizeFiles = 1
if args.chopWrongSizeFiles:
  __prog_options_chopWrongSizeFiles = 1

# --- DEBUG
# data_directory = '/home/mendi/Data/temp-KTorrent/'

# torrentFileName = 'MAME Guide V1.torrent'
# torrentFileName = 'Sega 32X Manuals (DMC-v2014-08-16).torrent'
# torrentFileName = 'MAME 0.162 Software List ROMs (TZ-Split).torrent'
# torrentFileName = 'No Intro (2015-02-16).torrent'
# torrentFileName = 'MAME 0.162 ROMs (Torrentzipped-split).torrent'
# torrentFileName = 'Vogt, A. E. van -  El viaje.torrent'

# --- Extrant torrent metadata
if not torrentFileName:
  do_printHelp()
  exit(0)
torrent_obj = extract_torrent_metadata(torrentFileName)

# --- Decide what to do based on arguments
if check:
  check_torrent_files_only(data_directory, torrent_obj)
elif checkUnneeded:
  list_torrent_unneeded_files(data_directory, torrent_obj)
  # delete_torrent_unneeded_files(data_directory, torrent_obj)
elif checkHash:
  check_torrent_files_hash(data_directory, torrent_obj)
else:
  list_torrent_contents(torrent_obj)

exit(0)
