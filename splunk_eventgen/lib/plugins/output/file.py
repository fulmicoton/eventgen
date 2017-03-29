# Note as implemented this plugin is not threadsafe, file should only be used with one output worker

from __future__ import division
from splunk_eventgen.lib.outputplugin import OutputPlugin
import os


class FileOutputPlugin(OutputPlugin):
    name = 'file'
    MAXQUEUELENGTH = 10

    validSettings = [ 'fileMaxBytes', 'fileBackupFiles' ]
    intSettings = [ 'fileMaxBytes', 'fileBackupFiles' ]

    def __init__(self, sample):
        OutputPlugin.__init__(self, sample)

        from splunk_eventgen.lib.eventgenconfig import Config
        globals()['c'] = Config()

        if sample.fileName == None:
            self.logger.error('outputMode file but file not specified for sample %s' % self._sample.name)
            raise ValueError('outputMode file but file not specified for sample %s' % self._sample.name)
            
        self._file = sample.pathParser(sample.fileName)
        self._fileMaxBytes = sample.fileMaxBytes
        self._fileBackupFiles = sample.fileBackupFiles

        self._fileHandle = open(self._file, 'a')
        self._fileLength = os.stat(self._file).st_size
        self.logger.debug("Configured to log to '%s' with maxBytes '%s' with backupCount '%s'" % \
                        (self._file, self._fileMaxBytes, self._fileBackupFiles))

    def flush(self, q):
        if len(q) > 0:
            metamsg = q.popleft()
            msg = metamsg['_raw']

            self.logger.debug("Flushing output for sample '%s' in app '%s' for queue '%s'" % (self._sample.name, self._app, self._sample.source))

            try:
                while msg:
                    if msg[-1] != '\n':
                        msg += '\n'

                    self._fileHandle.write(msg)
                    self._fileLength += len(msg)

                    # If we're at the end of the max allowable size, shift all files
                    # up a number and create a new one
                    if self._fileLength > self._fileMaxBytes:
                        self._fileHandle.flush()
                        self._fileHandle.close()
                        if os.path.exists(self._file+'.'+str(self._fileBackupFiles)):
                            self.logger.debug('File Output: Removing file: %s' % self._file+'.'+str(self._fileBackupFiles))
                            os.unlink(self._file+'.'+str(self._fileBackupFiles))
                        for x in range(1, self._fileBackupFiles)[::-1]:
                            self.logger.debug('File Output: Checking for file: %s' % self._file+'.'+str(x))
                            if os.path.exists(self._file+'.'+str(x)):
                                self.logger.debug('File Output: Renaming file %s to %s' % (self._file+'.'+str(x), self._file+'.'+str(x+1)))
                                os.rename(self._file+'.'+str(x), self._file+'.'+str(x+1))
                        os.rename(self._file, self._file+'.1')
                        self._fileHandle = open(self._file, 'w')
                        self._fileLength = 0

                    msg = q.popleft()['_raw']

                    self.logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample.name))
            except IndexError:
                self.logger.debug("Queue for app '%s' sample '%s' written" % (self._app, self._sample.name))

            if not self._fileHandle.closed:
                self._fileHandle.flush()

def load():
    """Returns an instance of the plugin"""
    return FileOutputPlugin