# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 18:00:49 2014

Implementation of common ETL (Extraction, Transformation and Loading)
processes with Wikipedia data:

    - Page-stub (metadata only)
    - Page-meta-history dumps (complete dumps with revision history text)
    - Logging (MediaWiki activity logs, administrative actions)
    - [Future types for links, categories, etc.]

@author: jfelipe
"""

from wikidat.sources.etl import PageRevisionETL
from download import RevHistDownloader
import multiprocessing as mp


class Task(object):
    """
    Abstract class defining common interface for all tasks
    """

    def __init__(self, lang, date=None):
        """
        Builder method of class RevisionHistoryRetrieval.
        Arguments:
            - language: code of the Wikipedia language to be processed
            - date: publication date of target dump files collection
        """
        self.lang = lang
        self.date = date
        self.down = None
        self.etl = None


class RevisionHistoryTask(Task):
    """
    A complete, multiprocessing parser of full revision history dump files
    """

    def __init__(self, lang='scowiki', date=None):
        """
        Builder method of class RevisionHistoryRetrieval.
        Arguments:
            - language: code of the Wikipedia language to be processed
            - date: publication date of target dump files collection
        """
        super(RevisionHistoryTask, self).__init__(lang=lang, date=date)

    def execute(self, page_fan, rev_fan, db_user, db_passw,
                mirror='http://dumps.wikimedia.your.org/'):
        """
        Run data retrieval and loading actions.
        Arguments:
            - page_fan = Number of workers to fan out page elements parsing
            - rev_fan = Number of workers to fan out rev elements parsing
            - db_user = User name to connect to local database
            - db_passw = Password for database user
            - mirror = Base URL of site hosting XML dumps
        """
        # TODO: Use proper logging module to track execution progress
        # Choose corresponding file downloader and etl wrapper
        print "Downloading new dump files from %s, for language %s" % (
              mirror, self.lang)
        self.down = RevHistDownloader(mirror, self.lang)
        # Donwload latest set of dump files
        self.paths, self.date = self.down.download(self.date)
        print "Downloaded files for lang %s, date: %s" % (self.lang, self.date)

        db_name = self.lang + '_' + self.date.strip('/')
        print "paths: " + unicode(self.paths)

        # TODO: Retrieve information about available CPU cores and
        # Number of parallel ETL processes to be started to maximize
        # system's throughput

        if len(self.paths) > 1:
            # Case of multiple paths
            paths1 = self.paths[0:len(self.paths)/2]
            paths2 = self.paths[len(self.paths)/2:]
            self.etl1 = PageRevisionETL(paths=paths1, lang=self.lang,
                                        page_fan=page_fan, rev_fan=rev_fan,
                                        db_name=db_name,
                                        db_user=db_user, db_passw=db_passw)
            self.etl2 = PageRevisionETL(paths=paths2, lang=self.lang,
                                        page_fan=page_fan, rev_fan=rev_fan,
                                        db_name=db_name,
                                        db_user=db_user, db_passw=db_passw)
            proc_etl1 = mp.Process(target=self.etl1.run())
            proc_etl1.start()
            proc_etl2 = mp.Process(target=self.etl2.run())
            proc_etl2.start()
            proc_etl1.join()
            proc_etl2.join()

        else:
            # Case of single path
            self.etl = PageRevisionETL(paths=self.paths, lang=self.lang,
                                       page_fan=page_fan, rev_fan=rev_fan,
                                       db_name=db_name,
                                       db_user=db_user, db_passw=db_passw)
        print "ETL process for page and revision history defined OK."
        print "Proceeding with ETL workflow. This may take time..."
        # Extract, process and load information in local DB
        self.etl.run()

        # TODO: logger; ETL step completed, proceeding with data
        # analysis and visualization
        print "ETL process finished for language %s and date %s" % (
              self.lang, self.date)
