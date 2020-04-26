#!/usr/bin/python
try:
    from os.path import isfile, join, isdir, exists, dirname
    from stat import ST_MTIME
    from os import stat, listdir, makedirs, rename
    from time import asctime, localtime
    from sys import argv
    # from face_recognition import load_image_file, face_locations
    import rawpy
    from pathlib import Path
except ImportError as err:
    exit(err)


def are_there_faces(image, verbose=False):
    """
    Returns true if there is at least one face in the image.
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

    if verbose:
        print("I found {} face(s) in this photograph.".format(len(face_locs)))

        for face_location in face_locs:
            # Print the location of each face in this image
            top, right, bottom, left = face_location

            print("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))

    return len(face_locs) > 0


def retrieve_creation_time_of_file(path, file):
    """
    A simple way to retrieve the creation time of a file.
    
    path : path in which the file is supposed to be\n
    file : the file for which we have to retrieve the creation time
    """
    info = stat(join(path, file))
    time_of_file = asctime(localtime(info[ST_MTIME]))
    return time_of_file


def is_directory_automatically_created(folder):
    """
    Verifies the name of the directory -> if it contains a month it returns True, otherwise False.
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
    return any(month in folder for month in months)


def retrieve_all_files(path, elements, alltime, files_to_move, is_in_dir):
    """
    Retrieves recursively all of the files in a specific directory.
    It returns the files which are in a directory and that are going 
    to be moved.

    path          : the path in which all the files and directories are\n
    elements      : the files\n
    allTime       : the time\n
    files_to_move : potential files to move from a directory to the path
    """
    all_files = [f for f in listdir(path)]
    for e in all_files:
        if isdir(join(path, e)):
            if not is_directory_automatically_created(e):
                files_to_move = retrieve_all_files(path + e + "/", elements, alltime, files_to_move, True)
            else:
                print("Can't move files which are in the directory '{}'.".format(e))
        elif isfile(join(path, e)):
            if is_in_dir:
                files_to_move.append(join(path, e))
            elements.append(e)
            alltime.append(retrieve_creation_time_of_file(path, e))
    
    return files_to_move


def move_files_to_correct_path(path, alltime, files_to_move):
    """
    Moves files from their path to an other path.

    path          : the path where all files will be after the execution\n
    alltime       : needed to not process some files\n
    files_to_move : files which are going to be moved
    """
    for f in files_to_move:
        is_already_moved = False
        for time in alltime:
            if transform_time_to_date(time) in f:
                is_already_moved = True
                break
        # If a time pattern has not been found in the path of the file
        # then we can move this one
        if not is_already_moved:
            # Old path of the file
            old_path = f
            # Retrieve file name
            split_file_path = f.split("/")
            file_name = split_file_path[len(split_file_path)-1]
            new_path = join(path, file_name)
            # Now move the file
            rename(old_path, new_path)


def switch_month(month):
    """
    Translates an english month to a french one. For example: 'Jan' becomes '(01)Janvier'.

    month : the month that will be translated
    """
    return {
        'Jan': '(01)Janvier',
        'Feb': '(02)Fevrier',
        'Mar': '(03)Mars',
        'Apr': '(04)Avril',
        'May': '(05)Mai',
        'Jun': '(06)Juin',
        'Jul': '(07)Juillet',
        'Aug': '(08)Aout',
        'Sep': '(09)Septembre',
        'Oct': '(10)Octobre',
        'Nov': '(11)Novembre',
        'Dec': '(12)Decembre',
    }[month]


def transform_to_path(path, date):
    """
    Concatenates the path and the date to create an absolute path.
    
    path : absolute path\n
    date : date (format: Month-Year)
    """
    return join(path, date + "/")


def transform_time_to_date(time):
    """
    Concatenates the month and the year.
    
    time : the time to transform
    """
    split_time = time.split()
    return split_time[4] + "_" + switch_month(split_time[1])  # [4]=year and [1]=month


def create_directories(path, alltime):
    """
    Creates new directories thanks to the date of creation of some files.
    
    path        : absolute path of the directories\n
    alltime     : these times will be used to create directories
    """
    directories = list()
    for time in alltime:
        # Concatenate the month and the year
        date = transform_time_to_date(time)
        # If this date is not in the directories, add it
        if date not in directories:
            directories.append(date)
            # Concatenate the path and the date to create an absolute path
            path_of_dir = transform_to_path(path, date)
            new_directory = dirname(path_of_dir)
            # We need to create a directory if it doesn't exist
            if not exists(new_directory):
                makedirs(new_directory)


def move_files(path, elements, alltime):
    """
    Move a file from an old path to a new one.
    
    path     : absolute path of the file\n
    elements : files that will be moved\n
    alltime  : we use the time to create the new path of the file
    """
    for i in range(0, len(elements)):
        date = transform_time_to_date(alltime[i])
        # Create the new path
        newpath = transform_to_path(path, date)
        # Add the name of the element to the new path
        newpath += elements[i]
        # We need the old file path to move it
        oldpath = join(path, elements[i])
        # Move file
        if not isfile(newpath):
            rename(oldpath, newpath)
        else:
            print(newpath + " already exists.")
