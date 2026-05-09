# WebCrawlerProjectDSCI551
Web Crawler repo for DSCI project
Instructions here are the same as requirements.txt

Using Python 3.14.4. If this doesn't work on the python on your computer, please try updating to this version
Also require pip for package installation, please install this if you do not have it already
python -m pip install --upgrade pip

Windows is the intended OS to use this on
pip install psycopg2-binary requests beautifulsoup4 lxml
or whatever method is available to install necessary packages. This is required for Windows and Linux

Please install the latest version of PostgreSQL from their website or from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
The password for the local database needs to be changed in the config.py folder, if you are planning on running this locally, please change
LOCAL_DB to include the password you set up in the installer. 
Add PostgreSQL to the PATH 
The default is C:\Program Files\PostgreSQL\18\bin, and you will need to change 18 to whichever version of PostgreSQL you are running. 

Additionally, once postgres is installed, run the following two commands from the WebCrawlerProject folder
psql -U postgres -c "CREATE DATABASE stories;"
psql -U postgres -d stories -f schema.sql
This should set up the local database.

To run the application, run python ./app/gui.py from the WebCrawlerProject folder or navigate to the file to run it from there
To run the crawler, run python ./WebCrawler/main.py from the WebCrawlerProject folder or navigate to the file to run it from there
If you want to run the application locally, add --offline as a parameter, i.e. python ./app/gui.py --offline
Main.py accepts a numerical value for the amount of threads you want to crawl, i.e. python ./WebCrawler/main.py 2 to crawl two threads 
Default is 50 threads.
If you wish to run offline storage and a certain amount of threads, put --offline after the number i.e. python ./WebCrawler/main.py 2 --offline
To stop the crawler any keyboard interrupt should work

For the data, it is recommeneded to grab at least 50 threads with the crawler for the local database, which can be done with ./WebCrawler/main.py 50 --offline
This will take a few minutes, but shouldn't be too long.
Supabase instead already has a database with 1000+ threads, which should be available as is

If you are unable to connect to the Supabase server, please check https://status.supabase.com/
The servers may be down or some other issue preventing connection may be there. There have been issues as of 5/7/2026 where there appears to be some infrastructure problem with the servers. 
If this is the case, please try again later when the servers may be back up
If this is not the case, please send me an email at steveron@usc.edu, I can check to put the server back up myself, 
as the database server may be paused.
The Local mode does perform all functionality if it is required. 
