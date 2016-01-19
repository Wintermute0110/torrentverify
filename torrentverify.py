#!/usr/bin/python3
#
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
#
# Bencoder code based on Bencodepy by Eric Weast (c) 2014
# Licensed under the GPL v2
# https://github.com/eweast/BencodePy/commits/master
import io
import sys
import os
import hashlib
import argparse
import shutil
from collections import OrderedDict

# --- Global variables
__software_version = '0.1.0';

# --- Program options (from command line)
__prog_options_override_torrent_dir = 0
__prog_options_deleteWrongSizeFiles = 0
__prog_options_truncateWrongSizeFiles = 0
__prog_options_deleteUnneeded = 0

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
  pieces_file_list = []

# --- Get size of terminal
# https://docs.python.org/3/library/shutil.html#querying-the-size-of-the-output-terminal
__cols, __lines = shutil.get_terminal_size()
# print('{0} cols and {1} lines'.format(__cols, __lines))

# --- Bdecoder ----------------------------------------------------------------
class DecodingError(Exception):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return repr(self.msg)

class Decoder:
  def __init__(self, data: bytes):
    self.data = data
    self.idx = 0

  def __read(self, i: int) -> bytes:
    """Returns a set number (i) of bytes from self.data."""
    b = self.data[self.idx: self.idx + i]
    self.idx += i
    if len(b) != i:
      raise DecodingError(
         "Incorrect byte length returned between indexes of {0} and {1}. Possible unexpected End of File."
         .format(str(self.idx), str(self.idx - i)))
    return b

  def __read_to(self, terminator: bytes) -> bytes:
    """Returns bytes from self.data starting at index (self.idx) until terminator character."""
    try:
      # noinspection PyTypeChecker
      i = self.data.index(terminator, self.idx)
      b = self.data[self.idx:i]
      self.idx = i + 1
      return b
    except ValueError:
      raise DecodingError(
          'Unable to locate terminator character "{0}" after index {1}.'.format(str(terminator), str(self.idx)))

  def __parse(self) -> object:
    """Selects the appropriate method to decode next bencode element and returns the result."""
    char = self.data[self.idx: self.idx + 1]
    if char in [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9', b'0']:
      str_len = int(self.__read_to(b':'))
      return self.__read(str_len)
    elif char == b'i':
      self.idx += 1
      return int(self.__read_to(b'e'))
    elif char == b'd':
      return self.__parse_dict()
    elif char == b'l':
      return self.__parse_list()
    elif char == b'':
      raise DecodingError('Unexpected End of File at index position of {0}.'.format(str(self.idx)))
    else:
      raise DecodingError('Invalid token character ({0}) at position {1}.'.format(str(char), str(self.idx)))

  def decode(self):
    """Start of decode process. Returns final results."""
    if self.data[0:1] not in (b'd', b'l'):
      return self.__wrap_with_tuple()
    return self.__parse()

  def __wrap_with_tuple(self) -> tuple:
    """Returns a tuple of all nested bencode elements."""
    l = list()
    length = len(self.data)
    while self.idx < length:
      l.append(self.__parse())
    return tuple(l)

  def __parse_dict(self) -> OrderedDict:
    """Returns an Ordered Dictionary of nested bencode elements."""
    self.idx += 1
    d = OrderedDict()
    key_name = None
    while self.data[self.idx: self.idx + 1] != b'e':
      if key_name is None:
        key_name = self.__parse()
      else:
        d[key_name] = self.__parse()
        key_name = None
    self.idx += 1
    return d

  def __parse_list(self) -> list:
    """Returns an list of nested bencode elements."""
    self.idx += 1
    l = []
    while self.data[self.idx: self.idx + 1] != b'e':
      l.append(self.__parse())
    self.idx += 1
    return l

# --- Functions ---------------------------------------------------------------
def query_yes_no_all(question, default="no"):
  """Ask a yes/no question via raw_input() and return their answer.

  "question" is a string that is presented to the user.
  "default" is the presumed answer if the user just hits <Enter>.
      It must be "yes" (the default), "no" or None (meaning
      an answer is required of the user).

  The "answer" return value is True for "yes" or False for "no".
  """
  valid = {"yes": 1,  "y": 1, "ye": 1,
           "no": 0,   "n": 0,
           "all": -1, "a": -1}
  if default is None:
    prompt = " [y/n/a] "
  elif default == "yes":
    prompt = " [Y/n/a] "
  elif default == "no":
    prompt = " [y/N/a] "
  elif default == "all":
    prompt = " [y/n/A] "
  else:
    raise ValueError("invalid default answer: '%s'" % default)

  while True:
    sys.stdout.write(question + prompt)
    choice = input().lower()
    if default is not None and choice == '':
      return valid[default]
    elif choice in valid:
      return valid[choice]
    else:
      sys.stdout.write("Please respond with 'yes', 'no' or 'all'"
                       " (or 'y' or 'n' or 'a').\n")

def confirm_file_action(action_str, result_str, force_delete):
  delete_file = 0
  if force_delete:
    delete_file = 1
  else:
    result = query_yes_no_all('{0} this file?'.format(action_str))
    if result == 1:
      delete_file = 1
      print('File {0}'.format(result_str))
    elif result == 0:
      delete_file = 0
      print('File not deleted')
    elif result == -1:
      delete_file = 1
      force_delete = True
      print('File {0}'.format(result_str))
    else:
      print('Logic error')

  return (delete_file, force_delete)

def limit_string_lentgh(string, max_length):
  if len(string) > max_length:
    string = (string[:max_length-1] + '*');
  else:
    string

  return string

# Convert a list of bytes into a path
def join_file_byte_list(file_list_bytes):
  file_list_string = []
  for i in range(len(file_list_bytes)):
    file_list_string.append(file_list_bytes[i].decode("utf-8"))

  return '/'.join(file_list_string)

# Returns a Torrent object with torrent metadata
__debug_torrent_extract_metadata = 0
def extract_torrent_metadata(filename):
  torrent = Torrent
  torrent.torrent_file = filename
  
  sys.stdout.write('Bdecoding torrent file {0}... '.format(torrentFileName))
  sys.stdout.flush()
  torrent_file = open(torrentFileName, "rb")
  # Use internal Bdecoder class
  decoder = Decoder(torrent_file.read())
  torr_ordered_dict = decoder.decode()
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

  # Make a list of files for each piece. Should include also the file offsets.
  # This is to find torrent that has padded files that must be trimmend.
  # Many Linux torrent clients have this bug in ext4 filesystems.
  # [ [{'file_idx': 0, 'start_offset': 1234, 'end_offset': 5678},
  #    { ... } ],
  #   [  ...   ],
  #   ...
  # ]
  piece_length = torrent.piece_length
  pieces_file_list = []
  piece_current_length = 0
  this_piece_files_list = []
  for i in range(torrent.num_files):
    file_dict = {}
    file_dict['file_idx'] = i
    file_dict['start_offset'] = 0
    file_size = file_current_size = torrent.file_length_list[i]
    while True:
      remaining_piece_bytes = piece_length - piece_current_length
      if file_current_size > remaining_piece_bytes:
        piece_current_length += remaining_piece_bytes
        file_current_size -= remaining_piece_bytes
      else:
        piece_current_length += file_current_size
        file_current_size = 0
      # Go for next file if no more bytes
      if file_current_size == 0:
        file_dict['end_offset'] = file_size
        this_piece_files_list.append(file_dict)
        break
      # Piece is ready, add to the list
      file_dict['end_offset'] = file_size - file_current_size
      this_piece_files_list.append(file_dict)
      pieces_file_list.append(this_piece_files_list)
      # Reset piece files list and size
      piece_current_length = 0
      this_piece_files_list = []
      # Add current file to piece files list
      file_dict = {}
      file_dict['file_idx'] = i
      file_dict['start_offset'] = file_size - file_current_size
  # Last piece
  if piece_current_length > 0:
    pieces_file_list.append(this_piece_files_list)
    
  # Put in torrent object
  torrent.pieces_file_list = pieces_file_list

  # DEBUG: print list of files per piece
  if __debug_torrent_extract_metadata:
    for piece_idx in range(len(pieces_file_list)):
      print('Piece {0:06d}'.format(piece_idx))
      this_piece_files_list = pieces_file_list[piece_idx]
      for file_idx in range(len(this_piece_files_list)):
        file_dict = this_piece_files_list[file_idx]
        print(' File {0:06d} start {1:8d} end {2:8d}'
          .format(file_dict['file_idx'], file_dict['start_offset'], file_dict['end_offset']))

  return torrent

def list_torrent_contents(torrent):
  print('Printing torrent file contents...')

  # --- Print list of files
  print('    F#            Bytes  File name')
  print('------ ----------------  --------------')
  for i in range(len(torrent.file_name_list)):
    print('{0:6} {1:16,}  {2}'
      .format(i+1, torrent.file_length_list[i], torrent.file_name_list[i]))

  # --- Print torrent metadata
  print('')
  print('Torrent file      : {0}'.format(torrent.torrent_file))
  print('Pieces info       : {0:10,} pieces, {1:16,} bytes/piece'
    .format(torrent.num_pieces, torrent.piece_length))
  print('Files info        : {0:10,} files,  {1:16,} total bytes'
    .format(torrent.num_files, torrent.total_bytes))
  if torrent.num_files > 1:
    print('Torrent directory : {0}'.format(torrent.dir_name))

# Checks that files listed in the torrent file exist, and that file size
# is correct
# Status can be: OK, MISSING, BAD_SIZE
def check_torrent_files_only(torrent):
  print('Checking torrent files and sizes (NOT hash)')
  ret_value = 0
  num_files_OK = 0
  num_files_bigger_size = 0
  num_files_smaller_size = 0
  num_files_missing = 0
  force_delete = False
  force_truncate = False
  num_deleted_files = 0
  num_truncated_files = 0
  print('    F#   Status     Actual Bytes    Torrent Bytes  File name')
  print('------ -------- ---------------- ----------------  --------------')
  for i in range(len(torrent.file_name_list)):
    file_size = -1
    filename_path = os.path.join(torrent.dir_data, torrent.file_name_list[i])
    # print(filename_path)
    file_exists = os.path.isfile(filename_path)
    if file_exists:
      file_size = os.path.getsize(filename_path)
      if file_size == torrent.file_length_list[i]:
        status = 'OK'
        num_files_OK += 1
      else:
        ret_value = 1
        status = 'BAD_SIZE'
        if file_size > torrent.file_length_list[i]:
          num_files_bigger_size += 1
        else:
          num_files_smaller_size += 1
    else:
      ret_value = 1
      status = 'MISSING'
      num_files_missing += 1

    # --- Print file info
    text_size = 7+9+17+17+1
    print('{0:6} {1:>8} {2:16,} {3:16,}  {4}'
      .format(i+1, status, file_size, torrent.file_length_list[i],
              limit_string_lentgh(torrent.file_name_list[i], __cols -text_size)))

    # --- Delete wrong size files (mutually exclusive with truncate)
    if status == 'BAD_SIZE' and file_size != torrent.file_length_list[i]:
      if __prog_options_deleteWrongSizeFiles:
        print('RM  {0}'.format(filename_path))
        # This option is very dangerous if user writes the wrong directory
        # Always confirm with user
        delete_file, force_delete = confirm_file_action('Delete', 'deleted', force_delete)
        if delete_file:
          os.unlink(torrent.file_length_list[i])
          num_deleted_files += 1

    # --- Truncate bigger size files
    if status == 'BAD_SIZE' and file_size > torrent.file_length_list[i]:
      if __prog_options_truncateWrongSizeFiles:
        print('TRUNCATE  {0}'.format(filename_path))
        # This option is very dangerous if user writes the wrong directory
        # Always confirm with user
        truncate_file, force_truncate = confirm_file_action('Truncate', 'truncated', force_truncate)
        if truncate_file:
          # w+ mode truncates the file, but the file if filled with zeros!
          # According to Python docs, r+ is for both read and writing, should work.
          fo = open(filename_path, "r+b")
          fo.truncate(torrent.file_length_list[i])
          fo.close()
          num_truncated_files += 1

  # --- Print torrent metadata
  print('')
  print('Torrent file       : {0}'.format(torrent.torrent_file))
  print('Pieces info        : {0:10,} pieces, {1:16,} bytes/piece'.format(torrent.num_pieces, torrent.piece_length))
  print('Files info         : {0:10,} files,  {1:16,} total bytes'.format(torrent.num_files, torrent.total_bytes))
  print('Torrent directory  : {0}'.format(torrent.dir_name))
  print('Download directory : {0}'.format(torrent.dir_download))
  print('Data directory     : {0}'.format(torrent.dir_data))
  print('Files OK           : {0:,}'.format(num_files_OK))
  print('Files w big size   : {0:,}'.format(num_files_bigger_size))
  print('Files w small size : {0:,}'.format(num_files_smaller_size))
  print('Files missing      : {0:,}'.format(num_files_missing))
  if __prog_options_deleteWrongSizeFiles:
    print('Deleted files      : {0:,}'.format(num_deleted_files))
  if __prog_options_truncateWrongSizeFiles:
    print('Truncated files    : {0:,}'.format(num_truncated_files))

  if num_files_bigger_size > 0 and (num_files_smaller_size == 0 or num_files_missing == 0):
    print("""WARNING
 Found files with bigger size than it should be.
 Run torrentverify with --check and --truncateWrongSizeFiles parameters
 to correct the problems.""")

  elif num_files_smaller_size > 0 or num_files_missing > 0:
    print("""WARNING
 Found files with smaller size than it should be or there are missing files.
 It is likely there is some problem with this Torrent. Check with your Torrent
 client and download the torrent again.""")

  return ret_value

# Lists torrent unneeded files
def check_torrent_unneeded_files(torrent):
  print('Checking torrent unneeded files')
  ret_value = 0

  # --- Make a recursive list of files in torrent data directory
  torrent_directory = os.path.join(torrent.dir_data)
  file_list = []
  for root, dirs, files in os.walk(torrent_directory, topdown=False):
    for name in files:
      file_list.append(os.path.join(root, name))

  # --- Make a set of files in the list of torrent metadata files
  print('  Status                                File name')
  print('--------  ---------------------------------------')
  torrent_file_list = []
  for i in range(len(torrent.file_name_list)):
    filename_path = os.path.join(torrent.dir_data, torrent.file_name_list[i])
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
  num_deleted_files = 0
  force_delete = False
  for i in range(len(file_list)):
    if file_list[i] not in torrent_file_set:
      print('UNNEEDED  {0}'.format(file_list[i]))
      ret_value = 1
      num_redundant += 1
      
      # --- Deleted unneeded file
      if __prog_options_deleteUnneeded:
        print('      RM  {0}'.format(file_list[i]))
        # This option is very dangerous if user writes the wrong directory
        # Always confirm with user
        delete_file, force_delete = confirm_file_action('Delete', 'deleted', force_delete)
        if delete_file:
          os.unlink(file_list[i])
          num_deleted_files += 1
    else:
      print('      OK  {0}'.format(file_list[i]))
      num_needed += 1
 
  # --- Print torrent metadata
  print('')
  print('Torrent file            : {0}'.format(torrent.torrent_file))
  print('Pieces info             : {0:10,} pieces, {1:16,} bytes/piece'.format(torrent.num_pieces, torrent.piece_length))
  print('Files info              : {0:10,} files,  {1:16,} total bytes'.format(torrent.num_files, torrent.total_bytes))
  print('Torrent directory       : {0}'.format(torrent.dir_name))
  print('Download directory      : {0}'.format(torrent.dir_download))
  print('Data directory          : {0}'.format(torrent.dir_data))
  print('Files in data directory : {0:,}'.format(len(file_list)))
  print('Needed files            : {0:,}'.format(num_needed))
  print('Unneeded files          : {0:,}'.format(num_redundant))
  if __prog_options_deleteUnneeded:
    print('Deleted files           : {0:,}'.format(num_deleted_files))
  
  if num_redundant > 0:
    print("""WARNING
 Found unneeded files in the torrent download directory.
 Run torrentverify with --checkUnneeded and --deleteUnneeded parameters
 to correct the problems.""")

  return ret_value

# This naive piece generator only works if files have correct size and exist
# on filesystem
def pieces_generator_naive(torrent):
  """Yield pieces from download file(s)."""
  piece_length = torrent.piece_length
  
  # yield pieces from a multi-file torrent
  # Iterator finishes when function exits but not with the yield keyword
  if torrent.num_files > 1:
    piece = b''
    file_idx_list = []
    # --- Iterate through all files
    # print('{0:6d}'.format(pieces_counter))
    for i in range(len(torrent.file_name_list)):
      path = os.path.join(torrent.dir_data, torrent.file_name_list[i])

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

# This piece generator returns zeros if file does not exists. Also,
# if files are padded at the end does not return that padding. This is to
# mimic KTorrent behaviour: files will pass the SHA checksum of the torrent
# but some files will have bigger sizes that need to be truncated.
def pieces_generator(torrent, pieces_list=None):
  piece_length = torrent.piece_length
  pieces_range = range(torrent.num_pieces)
  if pieces_list != None:
    pieces_range = pieces_list
  for piece_idx in pieces_range:
    # Get list of files for this piece
    this_piece_files_list = torrent.pieces_file_list[piece_idx]
    # Iterate through files and make piece
    piece = b''
    file_idx_list = []
    for file_idx in range(len(this_piece_files_list)):
      # Get file info
      file_dict = this_piece_files_list[file_idx]
      file_name = torrent.file_name_list[file_dict['file_idx']]
      file_start = file_dict['start_offset']
      file_end = file_dict['end_offset']
      file_correct_size = torrent.file_length_list[file_dict['file_idx']]
      file_idx_list.append(file_dict['file_idx'])
      # Read file
      path = os.path.join(torrent.dir_data, file_name)
      file_exists = os.path.isfile(path)
      if file_exists:
        file_size = os.path.getsize(path)
        if file_size == file_correct_size:
          # If downloaded file has correct size then read whithin the file
          # limits. Maybe the whole file if file is smaller than the piece size
          sfile = open(path, "rb")
          sfile.seek(file_start)
          piece += sfile.read(file_end - file_start)
          sfile.close()
        elif file_size < file_correct_size:
          # If downloaded file has less size then pad with zeros.
          # To simplify things, treat file as if it doesn't exist.
          # Consequently, SHA1 check will fail.
          piece += bytearray(file_end - file_start)
        else:
          # If downloaded file has more size then truncate file read. Note that 
          # SHA1 check may succed, but file will have an incorrect bigger size 
          # that must be truncated later.
          sfile = open(path, "rb")
          sfile.seek(file_start)
          piece += sfile.read(file_end - file_start)
          sfile.close()         
      else:
        # If file does not exists at all, just pad with zeros
        piece += bytearray(file_end - file_start)
    # Yield piece
    yield (piece, file_idx_list, piece_idx)

# Checks torrent files against SHA1 hash for integrity
def check_torrent_files_hash(torrent):
  ret_value = 0
  print('piece#  file#  HStatus  FStatus     Actual Bytes    Torrent Bytes  File name')
  print('------ ------ -------- -------- ---------------- ----------------  --------------')
  num_files_OK_list = []
  num_files_bigger_size_list = []
  num_files_smaller_size_list = []
  num_files_missing_list = []
  piece_counter = 0
  good_pieces = 0
  bad_pieces = 0
  for piece, file_idx_list, piece_index in pieces_generator(torrent):
    # --- Compare piece hash with expected hash
    piece_hash = hashlib.sha1(piece).digest()
    if piece_hash != torrent.pieces_hash_list[piece_index]:
      hash_status = 'BAD_SHA'
      bad_pieces += 1
      ret_value = 1
    else:
      hash_status = 'GOOD_SHA'
      good_pieces += 1

    # --- Print information
    for i in range(len(file_idx_list)):
      file_idx = file_idx_list[i]
      path = os.path.join(torrent.dir_data, torrent.file_name_list[file_idx])
      file_exists = os.path.isfile(path)
      if file_exists:
        file_size = os.path.getsize(path)
        if file_size == torrent.file_length_list[file_idx]:
          file_status = 'OK'
          num_files_OK_list.append(file_idx)
        else:
          file_status = 'BAD_SIZE'
          ret_value = 1
          if file_size > torrent.file_length_list[file_idx]:
            num_files_bigger_size_list.append(file_idx)
          else:
            num_files_smaller_size_list.append(file_idx)
      else:
        file_size = -1
        file_status = 'MISSING'
        ret_value = 1
        num_files_missing_list.append(file_idx)
      # --- Print odd/even pieces with different colors
      text_size = 7+7+9+9+17+17+1
      if piece_index % 2:
        print('{0:06d} {1:6} {2:>8} {3:>8} {4:16,} {5:16,}  {6}'
          .format(piece_index+1, file_idx+1, hash_status, file_status, 
                  file_size, torrent.file_length_list[file_idx], 
                  limit_string_lentgh(torrent.file_name_list[file_idx], __cols -text_size)))
      else:
        print('\033[0;97m{0:06d} {1:6} {2:>8} {3:>8} {4:16,} {5:16,}  {6}\033[0m'
          .format(piece_index+1, file_idx+1, hash_status, file_status, 
                  file_size, torrent.file_length_list[file_idx], 
                  limit_string_lentgh(torrent.file_name_list[file_idx], __cols -text_size)))
    # --- Increment piece counter
    piece_counter += 1

  # --- Make lists set to avoid duplicates
  num_files_OK_set           = set(num_files_OK_list)
  num_files_bigger_size_set  = set(num_files_bigger_size_list)
  num_files_smaller_size_set = set(num_files_smaller_size_list)
  num_files_missing_set      = set(num_files_missing_list)

  # --- Print torrent metadata
  print('')
  print('Torrent file        : {0}'.format(torrent.torrent_file))
  print('Pieces info         : {0:10,} pieces, {1:16,} bytes/piece'.format(torrent.num_pieces, torrent.piece_length))
  print('Files info          : {0:10,} files,  {1:16,} total bytes'.format(torrent.num_files, torrent.total_bytes))
  print('Torrent directory   : {0}'.format(torrent.dir_name))
  print('Download directory  : {0}'.format(torrent.dir_download))
  print('Data directory      : {0}'.format(torrent.dir_data))
  print('Files OK            : {0:12,}'.format(len(num_files_OK_set)))
  print('Files w big size    : {0:12,}'.format(len(num_files_bigger_size_set)))
  print('Files w small size  : {0:12,}'.format(len(num_files_smaller_size_set)))
  print('Files missing       : {0:12,}'.format(len(num_files_missing_set)))
  print('# of pieces checked : {0:12,}'.format(piece_counter))
  print('Good pieces         : {0:12,}'.format(good_pieces))
  print('Bad pieces          : {0:12,}'.format(bad_pieces))

  if bad_pieces == 0 and len(num_files_bigger_size_set):
    print("""WARNING
 Downloaded files pass SHA check but some files are bigger than they should be.
 Run torrentverify with --check and --truncateWrongSizeFiles parameters to correct the 
 problems and then run torrentverify with --checkHash parameter only to make sure 
 problems are solved.""")

  return ret_value

# Checks single file against SHA1 hash for integrity
__debug_file_location_in_torrent = 0
def check_torrent_files_single_hash(torrent, fileName):
  ret_value = 0

  # Remove torrent download directory from path
  dir_data = torrent.dir_data
  fileName_search = fileName.replace(dir_data, '');
  fileName_search = fileName_search.strip('/')
  
  if __debug_file_location_in_torrent:
    print('dir_data         {0}'.format(dir_data))
    print('fileName         {0}'.format(fileName))
    print('fileName_search  {0}'.format(fileName_search))

  # Locate which pieces of the torrent this file spans
  pieces_list = []
  for piece_idx in range(torrent.num_pieces):
    if __debug_file_location_in_torrent:
      print('Piece {0:6}'.format(piece_idx))
    this_piece_files_list = torrent.pieces_file_list[piece_idx]
    for file_idx in range(len(this_piece_files_list)):
      # Get file info
      cfile_dict = this_piece_files_list[file_idx]
      file_name = torrent.file_name_list[cfile_dict['file_idx']]
      if file_name == fileName_search:
        if __debug_file_location_in_torrent:
          print('  MATCHED  {0}'.format(file_name))
        pieces_list.append(piece_idx)
      else:
        if __debug_file_location_in_torrent:
          print('UNMATCHED  {0}'.format(file_name))

  # DEBUG info
  print('File           {0}'.format(fileName))
  print('Internal name  {0}'.format(fileName_search))
  print('File spans {0} pieces'.format(len(pieces_list)))
  if __debug_file_location_in_torrent:
    print('List of pieces')
    for i in range(len(pieces_list)):
      print(' #{0:6}'.format(pieces_list[i]))

  if len(pieces_list) < 1:
    print('ERROR File not found in torrent list of files. Exiting.')
    sys.exit(1)

  # --- Check pieces in list only
  print('piece#  file# HStatus  FStatus     Actual Bytes    Torrent Bytes  File name')
  print('------ ------ -------- -------- ---------------- ----------------  --------------')
  piece_counter = 0
  good_pieces = 0
  bad_pieces = 0
  for piece, file_idx_list, piece_index in pieces_generator(torrent, pieces_list):
    # --- Compare piece hash with expected hash
    piece_hash = hashlib.sha1(piece).digest()
    if piece_hash != torrent.pieces_hash_list[piece_index]:
      hash_status = 'BAD_SHA'
      bad_pieces += 1
      ret_value = 1
    else:
      hash_status = 'GOOD_SHA'
      good_pieces += 1

    # --- Print information
    for i in range(len(file_idx_list)):
      file_idx = file_idx_list[i]
      path = os.path.join(torrent.dir_data, torrent.file_name_list[file_idx])
      file_exists = os.path.isfile(path)
      if file_exists:
        file_size = os.path.getsize(path)
        if file_size == torrent.file_length_list[file_idx]:
          file_status = 'OK'
        else:
          file_status = 'BAD_SIZE'
          ret_value = 1
      else:
        file_size = -1
        file_status = 'MISSING'
        ret_value = 1
      # --- Print odd/even pieces with different colors
      text_size = 7+7+9+9+17+17+1
      if piece_index % 2:
        print('{0:06d} {1:6} {2:>8} {3:>8} {4:16,} {5:16,}  {6}'
          .format(piece_index+1, file_idx+1, hash_status, file_status, 
                  file_size, torrent.file_length_list[file_idx], 
                  limit_string_lentgh(torrent.file_name_list[file_idx], __cols -text_size)))
      else:
        print('\033[0;97m{0:06d} {1:6} {2:>8} {3:>8} {4:16,} {5:16,}  {6}\033[0m'
          .format(piece_index+1, file_idx+1, hash_status, file_status, 
                  file_size, torrent.file_length_list[file_idx], 
                  limit_string_lentgh(torrent.file_name_list[file_idx], __cols -text_size)))
    # --- Increment piece counter
    piece_counter += 1

  # --- Print torrent metadata
  print('')
  print('Torrent file        : {0}'.format(torrent.torrent_file))
  print('Pieces info         : {0:10,} pieces, {1:16,} bytes/piece'.format(torrent.num_pieces, torrent.piece_length))
  print('Files info          : {0:10,} files,  {1:16,} total bytes'.format(torrent.num_files, torrent.total_bytes))
  print('Torrent directory   : {0}'.format(torrent.dir_name))
  print('Download directory  : {0}'.format(torrent.dir_download))
  print('Data directory      : {0}'.format(torrent.dir_data))
  print('# of pieces checked : {0:12,}'.format(piece_counter))
  print('Good pieces         : {0:12,}'.format(good_pieces))
  print('Bad pieces          : {0:12,}'.format(bad_pieces))

  return ret_value

def do_printHelp():
  print("""\033[32mUsage: torrentverify.py -t file.torrent [-d /download_dir/] [options]\033[0m
   A small utility written in Python that lists contents of torrent files, deletes
unneeded files in the torrent downloaded data directory, and checks the torrent 
downloaded files for errors (either a fast test for file existence and size or a slower, 
comprehensive test using the SHA1 hash) optionally deleting or truncating wrong size files.

   If only the torrent file is input with -t file.torrent then torrent file contents are 
listed but no other action is performed.

\033[32mOptions:
 \033[35m-t\033[0m \033[31mfile.torrent\033[0m
   Torrent filename.

 \033[35m-d\033[0m \033[31m/download_dir/\033[0m
   Directory where torrent is downloaded. Data directory will be the concatenation
   of this directory with the torrent internally reported download directory.

 \033[35m--otd\033[0m
   Override torrent data directory. Data directory will be the directory specified 
   with -d option and torrent internally reported directory will be ignored.
 
 \033[35m--check\033[0m
   Checks that all the files listed in the torrent file are in the download directory
   and that their size is correct. This test is very fast but files having wrong checksum
   are not detected.

 \033[35m--deleteWrongSizeFiles\033[0m
   Delete files in the torrent download directory whose size is incorrect. Then, you can
   use your favourite torrent client to recreate (download) them again. Use this option
   in conjuction with --check.
 
 \033[35m--truncateWrongSizeFiles\033[0m
   Truncate files whose size is bigger than it should be. This may solve bugs with some
   torrent clients, specially when older version of the downloaded files are used as
   starting point to download a new torrent. Use this option in conjuction with --check.
   After using this option it is recommended you check the SHA1 with --checkHash to make
   sure everything is OK with your downloaded files.

 \033[35m--checkUnneeded\033[0m
   Checks the torrent downloaded files and finds files there not belonging to the torrent.

 \033[35m--deleteUnneeded\033[0m
   Deletes unneeded files in the torrent directory. Use this option in conjuction with
   --checkUnneeded. You will be asked wheter to delete the uneeded files or not for security.
   WARNING: this option is dangerous! If you specify the wrong directory you may
   potentially delete all files in you computer!

 \033[35m--checkHash\033[0m
   Checks torrent downloaded files against the SHA1 checksum. This test is slow but reliable. 
   If some files are padded (have extra bytes at the end of the file) SHA1 will pass
   but files may be incorrect (see --truncateWrongSizeFiles option).

 \033[35m--checkFile\033[0m \033[31mfilename\033[0m
   Checks a single downloaded file against the SHA1 checksum. You must also specify the
   torrent download directory with -d and optionally you can use --otd.""")

# -----------------------------------------------------------------------------
# main function
#
# Program returns
# 0 everything OK
# 1 error found with torrent files
# 2 error in program arguments or no arguments given
# 3 torrent file does not found
# 4 data directory not found
# -----------------------------------------------------------------------------
print('\033[36mTorrentVerify\033[0m' + ' version ' + __software_version)

# --- Command line parser
p = argparse.ArgumentParser()
p.add_argument('-t', help="Torrent file", nargs = 1)
p.add_argument("-d", help="Data directory", nargs = 1)
p.add_argument("--otd", help="Override torrent directory", action="store_true")
g = p.add_mutually_exclusive_group()
g.add_argument("--check", help="Do a basic torrent check: files there or not and size", action="store_true")
g.add_argument("--checkUnneeded", help="Write me", action="store_true")
g.add_argument("--checkHash", help="Full check with SHA1 hash", action="store_true")
g.add_argument("--checkFile", help="Check single file with SHA1 hash", nargs = 1)
d = p.add_mutually_exclusive_group()
d.add_argument("--deleteWrongSizeFiles", help="Delete files having wrong size", action="store_true")
d.add_argument("--truncateWrongSizeFiles", help="Chop files with incorrect size to right one", action="store_true")
p.add_argument("--deleteUnneeded", help="Write me", action="store_true")
args = p.parse_args();

# --- Read arguments
torrentFileName = data_directory = None
check = checkUnneeded = checkHash = 0

if args.t:
  torrentFileName = args.t[0];
if args.d:
  data_directory = args.d[0];
  
# Optional arguments
if args.otd:
  __prog_options_override_torrent_dir = 1

if args.deleteWrongSizeFiles:
  __prog_options_deleteWrongSizeFiles = 1

if args.truncateWrongSizeFiles:
  __prog_options_truncateWrongSizeFiles = 1

if args.deleteUnneeded:
  __prog_options_deleteUnneeded = 1

# --- Extrant torrent metadata
if not torrentFileName:
  do_printHelp()
  sys.exit(2)

if (args.check or args.checkUnneeded or args.checkHash or args.checkFile) \
    and data_directory == None:
  do_printHelp()
  sys.exit(2)

# --- Check for torrent file existence
if not os.path.isfile(torrentFileName):
  print('Torrent file not found : {0}'.format(torrentFileName))
  sys.exit(3)

# --- Read torrent file metadata  
torrent_obj = extract_torrent_metadata(torrentFileName)

# --- Get torrent data directory and check it exists
if data_directory != None:
  torrent_obj.dir_download = data_directory
  # User wants to override torrent data directory
  if __prog_options_override_torrent_dir:
    torrent_obj.dir_data = torrent_obj.dir_download
  # Normal mode of operation
  else:
    torrent_obj.dir_data = os.path.join(data_directory, torrent_obj.dir_name)
  # Check that data directory exists
  if not os.path.isdir(torrent_obj.dir_data):
    print('Data directory not found : {0}'.format(torrent_obj.dir_data))
    exit(4)

# --- Decide what to do based on arguments
ret_value = 0
if args.check:
  ret_value = check_torrent_files_only(torrent_obj)
elif args.checkUnneeded:
  ret_value = check_torrent_unneeded_files(torrent_obj)
elif args.checkHash:
  ret_value = check_torrent_files_hash(torrent_obj)
elif args.checkFile:
  ret_value = check_torrent_files_single_hash(torrent_obj, args.checkFile[0])
else:
  ret_value = list_torrent_contents(torrent_obj)
sys.exit(ret_value)
