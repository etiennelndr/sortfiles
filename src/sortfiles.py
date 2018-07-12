#!/usr/bin/python
try:
    from os.path import isfile, join, isdir
    import stat
    import os
    import time
except ImportError as err:
    exit(err)

def retrieveCreationTimeOfFile(path, file):
    """A simple way to retrieve the creation time of a file"""
    infos = os.stat(path + file)
    timeOfFile = time.asctime(time.localtime(infos[stat.ST_MTIME]))
    return timeOfFile

def retrieveAll(path, elements, alltime, filesToMove, isInDir):
    """
    Retrieve recursively all of the files in a specific directory.
    It returns the files which are in a directory and that will be moved (ot not).

    path : the path in which all the files and directories are
    elements : the files
    allTime : the time
    filesToMove : potential file to move from a directory to the path
    """
    all = [f for f in os.listdir(path)]
    for e in all:
        if isdir(join(path, e)):
            filesToMove = retrieveAll(path + e + "/", elements, alltime, filesToMove, True)
        elif isfile(join(path, e)):
            if isInDir:
                filesToMove.append(path + e)
            elements.append(e)
            alltime.append(retrieveCreationTimeOfFile(path, e))
    
    return filesToMove

def moveFilesToCorrectPath(path, alltime, filesToMove):
    for f in filesToMove:
        isAlreadyMoved = False
        for time in alltime:
            if f.find(transformTimeToDate(time)) != -1:
                isAlreadyMoved = True
                break
        # If a time pattern has not been found then we can move the file
        if not isAlreadyMoved:
            # Old path of the file
            oldpath = f
            # Retrieve file name
            splitFilePath = f.split("/")
            fileName = splitFilePath[len(splitFilePath)-1]
            newpath = path + fileName
            # Now move the file
            os.rename(oldpath, newpath)

def show(path, allFiles, allCreationTime):
    print("Files are from " + path)
    print("")
    for i in range (0,len(allFiles)):
        print(allFiles[i] + " : " + allCreationTime[i])

def switchMonth(month):
    return {
        'Jan' : '(01)Janvier',
        'Feb' : '(02)Fevrier',
        'Mar' : '(03)Mars',
        'Apr' : '(04)Avril',
        'May' : '(05)Mai',
        'Jun' : '(06)Juin',
        'Jul' : '(07)Juillet',
        'Aug' : '(08)Aout',
        'Sep' : '(09)Septembre',
        'Oct' : '(10)Octobre',
        'Nov' : '(11)Novembre',
        'Dec' : '(12)Decembre',
    }[month]

def transformToPath(path, date):
    """Concatenate the path and the date to create an absolute path"""
    return path + date + "/"

def transformTimeToDate(time):
    """Concatenate the month and the year"""
    splittime = time.split()
    return  splittime[4] + "_" + switchMonth(splittime[1]) # [4]=year and [1]=month
    
def createDirectories(path, alltime, directories):
    """Create new directories thanks to the date of creation of some files"""
    for time in alltime:
        # Concatenate the month and the year
        date = transformTimeToDate(time)
        # If this date is not in the directories, add it
        if date not in directories:
            directories.append(date)
            # Concatenate the path and the date to create an absolute path
            pathofdir = transformToPath(path, date)
            newdirectory = os.path.dirname(pathofdir)
            # We need to create a directory if it doesn't exist
            if not os.path.exists(newdirectory):
                os.makedirs(newdirectory)

def moveFiles(path, elements, alltime):
    """Move a file from an old path to a new one"""
    for i in range(0, len(elements)):
        date = transformTimeToDate(alltime[i])
        # Create the new path
        newpath = transformToPath(path, date)
        # Add the name of the element to the new path
        newpath += elements[i]
        # We need the old file path to move it
        oldpath = path + elements[i]
        # Move file
        if not isfile(newpath):
            os.rename(oldpath, newpath)
        else:
            print(newpath + " already exists.")

def main():
    # Create the path
    path = "/home/etienne/Images/Photos/"
    # Create a variable for all the elements
    elements = list()
    # Create a variable for all the time
    alltime = list()

    # Retrieve all the files from a path
    filesToMove = retrieveAll(path, elements, alltime, [], False)

    # Move files that are not directly in the path
    moveFilesToCorrectPath(path, alltime, filesToMove)

    # Finally, show the results
    #show(path, elements, alltime)

    # Create a variable for all the future directories
    directories = list()

    # Create the directories
    createDirectories(path, alltime, directories)

    # Now, move the files
    moveFiles(path, elements, alltime)

if __name__== "__main__":
    main()