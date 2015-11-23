# transcribe-md
Scripts for a digital collections transcription project.

This project uses Omeka with the Scripto plugin and MediaWiki to manage transcription files.  These scripts are designed to facilitate the migration of content (both images and metadata) from a Fedora repository into Omeka.

The main script is fedora2csv.py, which can be used to extract essential metadata from our Fedora 2 based repository.  It currently writes to a CSV, but could easily be modified to write to other data serialization formats (such as JSON, for example).

The script takes two parameters, an input file consisting of the PIDs for descriptive fedora 2 items (UMDM items).  It writes to files named according to a base name supplied as a second parameter.  For example:

  `$ python3 fedora2csv.py [infile] [outfilebase]`
  
will look up the PIDs specified in the first file, extract metadata and related files, and output the data to three csv files:
  * outfilebase-cols.csv
  * outfilebase-items.csv
  * outfilebase-files.csv
