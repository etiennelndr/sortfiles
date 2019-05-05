#!/usr/bin/python
try:
    from os.path import isfile, join, isdir, exists, dirname
    from stat import ST_MTIME
    from os import stat, listdir, makedirs, rename
    from time import asctime, localtime
    from sys import argv
    from face_recognition import load_image_file, face_locations
    import rawpy
    from pathlib import Path
except ImportError as err:
    exit(err)

def areThereFaces(image):
    """
    Return true if there is at least one face on the image.
    """
    # Load the jpg file into a numpy array
    if Path(image).suffix[1:] == "NEF":
        raw = rawpy.imread(image)
        img = raw.postprocess()
    else:
        img = load_image_file(image)

    print(type(img))

    # Find all the faces in the image using a pre-trained convolutional neural network.
    # This method is more accurate than the default HOG model, but it's slower
    # unless you have an nvidia GPU and dlib compiled with CUDA extensions. But if you do,
    # this will use GPU acceleration and perform well.
    # See also: find_faces_in_picture.py
    face_locs = face_locations(img, number_of_times_to_upsample=0, model="cnn")

    print("I found {} face(s) in this photograph.".format(len(face_locs)))

    for face_location in face_locs:
        # Print the location of each face in this image
        top, right, bottom, left = face_location

        print("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))

    return len(face_locs) > 0

def retrieveCreationTimeOfFile(path, file):
    """
    A simple way to retrieve the creation time of a file.
    
    path : path in which the file is supposed to be\n
    file : the file for which we have to retrieve the creation time
    """
    infos = stat(join(path, file))
    timeOfFile = asctime(localtime(infos[ST_MTIME]))
    return timeOfFile

def isDirectoryAutomaticallyCreated(dir):
    """
    Verify the name of the directory -> if it contains a month it returns True, otherwise False.
    """
    months = [
        '(01)Janvier',
        '(02)Fevrier',
        '(03)Mars',
        '(04)Avril',
        '(05)Mai',
        '(06)Juin',
        '(07)Juillet',
        '(08)Aout',
        '(09)Septembre',
        '(10)Octobre',
        '(11)Novembre',
        '(12)Decembre'
    ]
    return any(month in dir for month in months)

def retrieveAll(path, elements, alltime, filesToMove, isInDir):
    """
    Retrieve recursively all of the files in a specific directory.
    It returns the files which are in a directory and that are going 
    to be moved.

    path        : the path in which all the files and directories are\n
    elements    : the files\n
    allTime     : the time\n
    filesToMove : potential files to move from a directory to the path
    """
    all = [f for f in listdir(path)]
    for e in all:
        if isdir(join(path, e)):
            if not isDirectoryAutomaticallyCreated(e):
                filesToMove = retrieveAll(path + e + "/", elements, alltime, filesToMove, True)
            else:
                print("Can't move files which are in the directory '{}'.".format(e))
        elif isfile(join(path, e)):
            if isInDir:
                filesToMove.append(join(path, e))
            elements.append(e)
            alltime.append(retrieveCreationTimeOfFile(path, e))
    
    return filesToMove

def moveFilesToCorrectPath(path, alltime, filesToMove):
    """
    Move files from their path to an other path.

    path        : the path where all files will be after the execution\n
    alltime     : needed to not process some files\n
    filesToMove : files which are going to be moved
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
            newpath = join(path, fileName)
            # Now move the file
            rename(oldpath, newpath)

def show(path, allFiles, allCreationTime):
    print("Files are from " + path)
    print("")
    for i in range (0,len(allFiles)):
        print(allFiles[i] + " : " + allCreationTime[i])

def switchMonth(month):
    """
    Translate an english month to a french one. For example: 'Jan' becomes '(01)Janvier'.

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
    return join(path, date + "/")

def transformTimeToDate(time):
    """
    Concatenate the month and the year.
    
    time : the time to transform
    """
    splittime = time.split()
    return  splittime[4] + "_" + switchMonth(splittime[1]) # [4]=year and [1]=month
    
def createDirectories(path, alltime):
    """
    Create new directories thanks to the date of creation of some files.
    
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
            path_of_dir = transformToPath(path, date)
            new_directory = dirname(path_of_dir)
            # We need to create a directory if it doesn't exist
            if not exists(new_directory):
                makedirs(new_directory)

def moveFiles(path, elements, alltime):
    """
    Move a file from an old path to a new one.
    
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
        oldpath = join(path, elements[i])
        # Move file
        if not isfile(newpath):
            rename(oldpath, newpath)
        else:
            print(newpath + " already exists.")

def main():
    """
    Main method.
    """
    if len(argv[1:]) == 0:
        exit("Error: you must start the program this way -> python sortfiles.py [path]")

    # Create the path
    path = argv[1]

    # Verify if the directory exists
    if not isdir(path):
        exit("Error: this directory doesn't exist. Please create it or verify if you haven't made a mistake in the path.")

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
    #main()
    ret = areThereFaces("D:\Images\photo_profil.jpg")
    print(ret)
    ret = areThereFaces("D:\Images\Identité.jpg")
    print(ret)
    ret = areThereFaces("D:\Images\Photos\2019_(02)Fevrier\DSC_8529.NEF")
    print(ret)
    