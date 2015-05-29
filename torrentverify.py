#!/usr/bin/python3
#
import io
import sys
import os
from bencodepy import decode

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
  torr_ordered_dict = decode(torrent_file.read())
  info_ordered_dict = torr_ordered_dict[b'info']
  sys.stdout.write('done\n\n')

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
  # --- Print list of files
  print('    F#            Bytes  File name')
  print('------ ----------------  --------------')
  for i in range(len(torrent_obj.file_name_list)):
    print('{0:6} {1:16,}  {2}'.format(i+1, torrent_obj.file_length_list[i], torrent_obj.file_name_list[i]))

  # --- Print torrent metadata
  print('')
  print('Torrent file      : {0}'.format(torrent_obj.torrent_file))
  print('Torrent directory : {0}'.format(torrent_obj.dir_name))
  print('Pieces info       : {0:10,} pieces, {1:16,} bytes/piece'.format(torrent_obj.num_pieces, torrent_obj.piece_length))
  print('Files info        : {0:10,} files,  {1:16,} total bytes'.format(torrent_obj.num_files, torrent_obj.total_bytes))
  # print('Torrent comment  : {0}'.format(torrent.comment))

# Checks that files listed in the torrent file exist, and that file size
# is correct
# Status can be: OK, MISSING, BAD_SIZE
def check_torrent_files_only(data_directory, torrent_obj):
  num_files_OK = 0
  num_files_bad_size = 0
  num_files_missing = 0
  print('Checking torrent files and sizes (NOT hash)')
  print('    F#   Status            Bytes  File name')
  print('------ -------- ----------------  --------------')
  for i in range(len(torrent_obj.file_name_list)):
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
    print('{0:6} {1:>8} {2:16,} {3}'.format(i+1, status, torrent_obj.file_length_list[i], torrent_obj.file_name_list[i]))  

  # --- Print torrent metadata
  print('')
  print('Torrent file      : {0}'.format(torrent_obj.torrent_file))
  print('Torrent directory : {0}'.format(torrent_obj.dir_name))
  print('Pieces info       : {0:10,} pieces, {1:16,} bytes/piece'.format(torrent_obj.num_pieces, torrent_obj.piece_length))
  print('Files info        : {0:10,} files,  {1:16,} total bytes'.format(torrent_obj.num_files, torrent_obj.total_bytes))
  print('Data directory    : {0}'.format(data_directory))
  print('Files OK          : {0:,}'.format(num_files_OK))
  print('Files bad size    : {0:,}'.format(num_files_bad_size))
  print('Files missing     : {0:,}'.format(num_files_missing))

# Lists torrent unneeded files
def list_torrent_unneeded_files(data_directory, torrent_obj):
  pass

# Removes unneeded files from torrent download directory
def delete_torrent_unneeded_files(data_directory, torrent_obj):
  pass

# Checks torrent files against SHA1 hash for integrity
def check_torrent_files_hash(data_directory, torrent_obj):
  pass

# --- Main --------------------------------------------------------------------
data_directory = '/home/mendi/Data/temp-KTorrent/'

# torrentFileName = 'MAME Guide V1.torrent'
# torrentFileName = 'Sega 32X Manuals (DMC-v2014-08-16).torrent'
torrentFileName = 'MAME 0.162 Software List ROMs (TZ-Split).torrent'
# torrentFileName = 'No Intro (2015-02-16).torrent'
# torrentFileName = 'Vogt, A. E. van -  El viaje.torrent'

# --- Extrant torrent metadata
torrent_obj = extract_torrent_metadata(torrentFileName)

# --- Print info
# list_torrent_contents(torrent_obj)

check_torrent_files_only(data_directory, torrent_obj)

list_torrent_unneeded_files(data_directory, torrent_obj)

# delete_torrent_unneeded_files(data_directory, torrent_obj)

# check_torrent_files_hash(data_directory, torrent_obj)
