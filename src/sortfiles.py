#!/usr/bin/python
try:
    from os.path import isfile, join, isdir
    import stat
    import os
    import time
except ImportError as err:
    exit(err)

def retrieveCreationTimeOfFile(path, file):
    """
    A simple way to retrieve the creation time of a file
    
    path : path in which the file is supposed to be\n
    file : the file for which we have to retrieve the creation time\n
    """
    infos = os.stat(path + file)
    timeOfFile = time.asctime(time.localtime(infos[stat.ST_MTIME]))
    return timeOfFile

def retrieveAll(path, elements, alltime, filesToMove, isInDir):
    """
    Retrieve recursively all of the files in a specific directory.
    It returns the files which are in a directory and that will be moved (ot not).

    path        : the path in which all the files and directories are\n
    elements    : the files\n
    allTime     : the time\n
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
    """
    Move files from their path to an other path.

    path        : the path where all files will be after the execution\n
    alltime     : needed to not process some files\n
    filesToMove : files which will be moved
    """
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
    """
    Translate an english month to a french one. For example: 'Jan' becomes 'Janvier'.

    month : the month that will be translated
    """
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
    """
    Concatenate the path and the date to create an absolute path.
    
    path : absolute path\n
    date : date (format: Month-Year)
    """
    return path + date + "/"

def transformTimeToDate(time):
    """
    Concatenate the month and the year.
    
    time : the time to transform
    """
    splittime = time.split()
    return  splittime[4] + "_" + switchMonth(splittime[1]) # [4]=year and [1]=month
    
def createDirectories(path, alltime):
    """
    Create new directories thanks to the date of creation of some files
    
    path        : absolute path of the directories\n
    alltime     : these times will be used to create directories
    """
    directories = list()
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
    """
    Move a file from an old path to a new one
    
    path     : absolute path of the file\n
    elements : files that will be moved\n
    alltime  : we use the time to create the new path of the file
    """
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

    # Create the directories
    createDirectories(path, alltime)

    # Now, move the files
    moveFiles(path, elements, alltime)

if __name__== "__main__":
    # Start the program
    main()
