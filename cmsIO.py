#!/usr/bin/env python
"""
_cmsStage_

Get files in and out of CASTOR using various LFNs

"""

import sys
import os
import subprocess
import shutil
#from ProdCommon.TrivialFileCatalog.TrivialFileCatalog import TrivialFileCatalog
from PhysicsTools.HeppyCore.utils.ProdCommon.TrivialFileCatalog.TrivialFileCatalog import TrivialFileCatalog

class cmsFileManip:
    """A class to interact with files/directories"""
    def runCommand( self, cmd ):
        myCommand = subprocess.Popen( cmd,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE )
        ( out, err ) = myCommand.communicate()
        if myCommand.returncode != 0:
            print >> sys.stderr, "Command (%s) failed with return code: %d" % ( cmd, myCommand.returncode )
            print >> sys.stderr, err

        return out,err,myCommand.returncode


class localFileManip(cmsFileManip):
    def resetCache( self ):
        pass
    def stat( self, file ):
        return os.stat( file.pfn )
    def size( self, file ):
        return os.stat( file.pfn ).st_size
    def isdir( self, file ):
        return os.path.isdir( file.pfn )
    def isfile( self, file ):
        return os.path.isfile( file.pfn )
    def rm( self, file, args ):
        retc = 0
        if "-r" in args and file.isdir():
            shutil.rmtree( file.path )
        else:
            try:
                os.remove( file.path )
            except OSError:
                retc = 1
        return retc
    def mkdir( self, file, args ):
        if "-p" in args:
            os.makedirs( file.path )
        else:
            os.mkdir( file.path )
        return 0
    def rmdir( self, file, args ):
        if "-p" in args:
            shutil.removedirs( file.path )
        else:
            os.rmdir( file.path )
        return 0
    def ls( self, file, args ):
        command = [ "ls" ]
        command += args
        command.append( file.path )
        (out,err,rtc) = self.runCommand( command )
        if err:
            print err
        return out

class xrdFileManip(cmsFileManip):
    """A root specific version"""
    def __init__( self ):
        self.isFile = None
        self.isFileSet = False
        self.isDir = None
        self.isDirSet = False
        self.statCache = ''

    def resetCache( self ):
        self.__init__()

    def size( self, file ):
        return int( self.stat( file ).split()[3] )

    def stat( self, file ):
        if self.statCache == '':
            command = [ 'xrd',
                        file.host,
                        'stat',
                        file.path + file.opaque ]

            # give the first line only
            self.statCache = self.runCommand( command )[0].split('\n')[0]
        return self.statCache

    def isdir( self, file ):
        if not self.isDirSet:
            self.isDirSet = True
            command = [ 'xrd',
                        file.host,
                        'existdir',
                        file.path + file.opaque ]
            out,err,retcd = self.runCommand( command )
            if retcd == 0 and out.startswith( 'The directory exists.' ):
                self.isDir = True
            else:
                self.isDir = False
        return self.isDir

    def isfile( self, file ):
        if not self.isFileSet:
            self.isFileSet = True
            command = [ 'xrd',
                        file.host,
                        'existfile',
                        file.path + file.opaque ]
            out,err,retcd = self.runCommand( command )
            if ( retcd == 0 and out.startswith( 'The file exists.' ) ):
                self.isFile = True
            else:
                self.isFile = False
        return self.isFile

    def rm( self, file, args ):
        if '-r' in args:
            print "warning: cmsRm -r not supported with xrootd. Trying eos command."
            command = [ '/afs/cern.ch/project/eos/installation/pro/bin/eos.select',
                        'root://%s/' % file.host,
                        "rm",
                        "-r",
                        file.path ]
        else:
            command = [ 'xrd',
                        file.host,
                        "rm" ,
                        file.path + file.opaque ]
        out,err,retcd = self.runCommand( command )
        if out:
            print out
        if err:
            print err
        return retcd

    def rmdir( self, file, args ):
        if '-p' in args:
            print "cmsRmdir -p not supported with xrootd."
            sys.exit( 3 )
        command = [ 'xrd',
                    file.host,
                    "rmdir",
                    file.path + file.opaque ]
        out,err,retcd = self.runCommand( command )
        if out:
            print out
        if err:
            print err
        return retcd

    def mkdir( self, file, args ):
        if '-p' in args:
            print "cmsMkdir -p not supported with xrootd."
            sys.exit( 3 )
        command = [ 'xrd',
                    file.host,
                    "mkdir",
                    file.path + file.opaque ]
        out,err,retcd = self.runCommand( command )
        if out:
            print out
        if err:
            print err
        return retcd

    def ls( self, file, args ):
        if '-R' in args:
            xrdComm = "dirlistrec"
        else:
            xrdComm = "dirlist"
        if file.isdir():
            pathToLS = file.path
        elif file.isfile():
            pathToLS = os.path.dirname( file.path )
        else:
            file.exitcode = 2
            return "No such file or directory: %s" % file.lfn
        # FIXME we perhaps need opaque information, but not with file name
        # as that breaks this
        command = [ 'xrd',
                    file.host,
                    xrdComm,
                    pathToLS ]
        out,err,retcd = self.runCommand( command )
        if err:
            print err

        result = ""
        if file.isfile():
            # we only want the output for one file in this case
            for line in out.split('\n'):
                if line.endswith( '/%s' % os.path.basename( file.path ) ):
                    result = line
                    break
        else:
            result = out
        return result.replace( file.prefix, '' )

class nsFileManip(cmsFileManip):
    """CASTOR ns specific version"""
    def __init__( self ):
        self.statCache = ''

    def resetCache( self ):
        self.__init__()

    def size( self, file):
        # size should be the fifth element
        return int( self.ls( file, ["-l"] ).split()[4] )
    def isdir( self, file ):
        if self.ls( file, ["-dl"] ).startswith( "d" ):
            return True
        else:
            return False
    def ls( self, file, args ):
        command = [ "nsls" ]
        command += args
        command.append( file.path )
        (out,err,rtc) = self.runCommand( command )
        if err:
            print err
        return out
    def rm( self, file, args ):
        command = [ "nsrm" ]
        command += args
        command.append( file.path )
        (out,err,rtc) = self.runCommand( command )
        if out:
            print out
        if err:
            print err
        return rtc
    def mkdir( self, file, args ):
        command = [ "nsmkdir" ]
        command += args
        command.append( file.path )
        (out,err,rtc) = self.runCommand( command )
        if out:
            print out
        if err:
            print err
        return rtc
    def rmdir( self, file, args ):
        command = [ "nsrmdir" ]
        command += args
        command.append( file.path )
        (out,err,rtc) = self.runCommand( command )
        if out:
            print out
        if err:
            print err
        return rtc
    def isfile( self, file ):
        if len( self.ls( file, [] ) ) == 0 or self.isdir( file ):
            return False
        else:
            return True
    def stat( self, file ):
        if self.statCache == '':
            command = [ "rfstat", file.path ]
            (self.statCache,err,rtc) = self.runCommand( command )
        return self.statCache


class cmsFile:
    """Represents a file"""
    def __init__( self, lfn, tfcProt ):
        self.exitcode = 0
        self.lfn = lfn
        if lfn.startswith( "/store/" ) or lfn.startswith( "/user/" ):
            self.pfn = getPFN( self.lfn, tfcProt )
            ( self.protocol,
              self.host,
              self.path,
              self.opaque ) = splitPFN( self.pfn )
        else:
            self.pfn = lfn
            self.protocol = "Local"
            self.host = "localhost"
            self.path = lfn
            self.opaque = ""
        self.prefix = self.path.replace( self.lfn, '' )

        if self.protocol == "root":
            self.manip = xrdFileManip()
        elif self.protocol == "rfio":
            self.manip = nsFileManip()
        elif self.protocol == "Local":
            self.manip = localFileManip()
        else:
            print >> sys.stderr, "Unexpected protocol returned from TFC, please open Savannah ticket"
            print >> sys.stderr, "protocol: %s" % self.protocol
            sys.exit( 1 )

    def size( self ):
        return self.manip.size( self )
    def isdir( self ):
        return self.manip.isdir( self )
    def isfile( self ):
        return self.manip.isfile( self )
    def stat( self ):
        return self.manip.stat( self )
    def ls( self, args ):
        return self.manip.ls( self, args )
    def mkdir( self, args ):
        return self.manip.mkdir( self, args )
    def rmdir( self, args ):
        return self.manip.rmdir( self, args )
    def rm( self, args ):
        return self.manip.rm( self, args )
    def resetCache( self ):
        self.manip.resetCache()

def getPFN( lfn, protocol = "rfio" ):
    """
    _getPFN_

    figure out PFN and command first
    """

    tfc = TrivialFileCatalog( os.path.expandvars( "trivialcatalog_file:${CMS_PATH}/SITECONF/local/PhEDEx/storage.xml?protocol=%s" % protocol ) )
    pfn = tfc.matchLFN( None, lfn )
    # need to hack some TURL as the TFC returns invalid ones at CERN
    if pfn.startswith( 'rfio:/castor' ):
        pfn = pfn.replace( 'rfio:/castor/', 'rfio://castorcms//castor/' )

    return pfn

def splitPFN( pfn ):
    """
    _splitPFN_

    Split the PFN in to { <protocol>, <host>, <path>, <opaque> }
    """

    protocol = pfn.split(':')[0]
    host = pfn.split('/')[2]
    thisList = pfn.replace( '%s://%s/' % ( protocol, host ),'' ).split( '?' )
    path = thisList[0]
    opaque = ""
    # If we have any opaque info keep it
    if len( thisList ) == 2:
        opaque = "?%s" % thisList[1]

    # check for the path to actually be in the opaque information
    if opaque.startswith( "?path=" ):
        elements = opaque.split( '&' )
        path = elements[0].replace('?path=','')
        buildingOpaque = '?'
        for element in elements[1:]:
            buildingOpaque += element
            buildingOpaque += '&'
        opaque = buildingOpaque.rstrip( '&' )
    elif opaque.find( "&path=" ) != -1:
        elements = opaque.split( '&' )
        buildingOpaque = elements[0]
        for element in elements[1:]:
            if element.startswith( 'path=' ):
                path = element.replace( 'path=','' )
            else:
                buildOpaque += '&' + element
        opaque = buildingOpaque

    return protocol, host, path, opaque

def getCommand( protocol, force ):
    """
    _getCommand_

    Return the command array for a certain PFN
    """

    command = []
    if protocol == "root":
        command = [ "xrdcp", "-np" ]
        if force == True:
            command.append( "-f" )
    elif protocol == "rfio":
        command = [ "rfcp" ]
    else:
        print >> sys.stderr, "Unexpected protocol returned from TFC, please open Savannah ticket"
        print >> sys.stderr, "protocol: %s" % protocol
        sys.exit( 1 )

    return command

def executeCommand( command, debug = False ):
    """
    _executeCommand_

    command execute
    """

    if debug:
        print command
    else:
        result = subprocess.Popen( command ).wait()
        if result != 0:
            print >> sys.stderr, "%s exited with error code %d, exiting with the same code." % ( command[0], result )
            sys.exit( result )

