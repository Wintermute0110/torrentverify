torrentverify
=============

A small utility written in Python that lists contents of torrent files, deletes
unneeded files in the torrent downloaded data directory, and checks the torrent 
downloaded files for errors (either a fast test for file existence and size or a slower, 
comprehensive test using the SHA1 hash) optionally deleting or truncating wrong size files.
