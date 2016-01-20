# torrentverify

A small utility written in Python that lists contents of torrent files, deletes
unneeded files in the torrent downloaded data directory, and checks the torrent 
downloaded files for errors (either a fast test for file existence and size or a slower, 
comprehensive test using the SHA1 hash) optionally deleting or truncating wrong size files.

## Usage and examples

To list the contents of a torrent file.

```
$ ./torrentverify.py -t my_file.torrent
```

To check if your downloaded files exist and have correct size.

```
$ ./torrentverify.py -t my_file.torrent -d /download_dir/ --check
```

where `/download_dir/` is the directory where your Torrent client downloads
the Torrent data. Notice that the actual data directory is `/download_dir/` plus
an internal directory inside the Torrent file. To ignore the Torrent file 
internal directory use.

```
$ ./torrentverify.py -t my_file.torrent -d /download_dir/ --check --odt
```

You can truncate files with sizer bigger than it should be in the data directory. 
In most cases, this solves most problems with the downloaded data.

```
$ ./torrentverify.py -t my_file.torrent -d /download_dir/ --check --truncateWrongSizeFiles
```

Alternatively, you can delete files having wrong size and then tell your
Torrent client to check and download the missing parts again.

```
$ ./torrentverify.py -t my_file.torrent -d /download_dir/ --check --deleteWrongSizeFiles
```

You can also check if there are unneeded files in the torrent data directory.

```
$ ./torrentverify.py -t my_file.torrent -d /download_dir/ --checkUnneeded
```

If unneeded files are found you may deleted them.


```
$ ./torrentverify.py -t my_file.torrent -d /download_dir/ --checkUnneeded --deleteUnneeded
```

For every unneeded file found you will be presented with a promt.

Finally, you can do a comprehensive (and slow) check of your torrent files.

```
$ ./torrentverify.py -t my_file.torrent -d /download_dir/ --checkHash
```

Note that `--checkHash` does not check for unneeded files.

## Command line reference

### Syntax

```
torrentverify.py -t file.torrent [-d /download_dir/] [options]
```

If only the torrent file is input with `-t file.torrent` then torrent file contents 
are listed but no other action is performed.

### Options
* `-t file.torrent`
   Torrent filename.

* `-d /download_dir/`

   Directory where torrent is downloaded. Data directory will be the concatenation
   of this directory with the torrent internally reported download directory.

* `--otd`

   Override torrent data directory. Data directory will be the directory specified 
   with -d option and torrent internally reported directory will be ignored.
 
 `--check`
   Checks that all the files listed in the torrent file are in the download directory
   and that their size is correct. This test is very fast but files having wrong checksum
   are not detected.

 `--truncateWrongSizeFiles`
   Truncate files whose size is bigger than it should be. This may solve bugs with some
   torrent clients, specially when older version of the downloaded files are used as
   starting point to download a new torrent. Use this option in conjuction with `--check`.
   After using this option it is recommended you check the SHA1 with `--checkHash` to make
   sure everything is OK with your downloaded files.

 `--deleteWrongSizeFiles`
   Delete files in the torrent download directory whose size is incorrect. Then, you can
   use your favourite torrent client to recreate (download) them again. Use this option
   in conjuction with `--check`.
 
 `--checkUnneeded`
   Checks the torrent downloaded files and finds files there not belonging to the torrent.

 `--deleteUnneeded`
   Deletes unneeded files in the torrent directory. Use this option in conjuction with
   `--checkUnneeded`. You will be asked wheter to delete the uneeded files or not for security.
   WARNING: this option is dangerous! If you specify the wrong directory you may
   potentially delete all files in you computer!

 `--checkHash`
   Checks torrent downloaded files against the SHA1 checksum. This test is slow but reliable. 
   If some files are padded (have extra bytes at the end of the file) SHA1 will pass
   but files may be incorrect (see `--truncateWrongSizeFiles` option).

 `--checkFile filename`
   Checks a single downloaded file against the SHA1 checksum. You must also specify the
   torrent download directory with -d and optionally you can use `--otd`.
