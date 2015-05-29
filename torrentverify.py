#!/usr/bin/python3
#

import bencode
from bencodepy import decode

# torrentFileName = 'MAME Guide V1.torrent'
# torrentFileName = 'Sega 32X Manuals (DMC-v2014-08-16).torrent'
torrentFileName = 'No Intro (2015-02-16).torrent'

print('Opening torrent file {0}'.format(torrentFileName))
torrent_file = open(torrentFileName, "rb")

print('Bdecoding torrent file {0}'.format(torrentFileName))
torr_ordered_dict = decode(torrent_file.read())

# for key in torr_ordered_dict:
#   print('key {0} value {1}'.format(key, torr_ordered_dict[key]))

info_ordered_dict = torr_ordered_dict[b'info']
# for key in info_ordered_dict:
#   print('key {0} value {1}'.format(key, info_ordered_dict[key]))

# Directory name to store torrent
t_name = info_ordered_dict[b'name']
t_pLength = info_ordered_dict[b'piece length']
t_files_list = info_ordered_dict[b'files']
t_pieces = info_ordered_dict[b'pieces']

print('Directory {0}'.format(t_name))
print('Piece length {0}'.format(t_pLength))
print('File list')
for t_file in t_files_list:
  print(' path {0} length {1}'.format(t_file[b'path'], t_file[b'length']))
  