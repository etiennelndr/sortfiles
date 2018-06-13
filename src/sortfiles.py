try:
    from os import listdir
    from os.path import isfile, join, isdir
    from os import stat
    from stat import ST_MTIME
    import time
except ImportError as err:
    exit(err)

def retrieveCreationTimeOfFile(path, file):
    infos = stat(path + file)
    timeOfFile = time.asctime(time.localtime(infos[ST_MTIME]))
    return timeOfFile

def retrieveAll(path, alltime, elements):
    all = [f for f in listdir(path)]
    for e in all:
        if isdir(join(path, e)):
            retrieveAll(path+e+"/", alltime, elements)
        elif isfile(join(path, e)):
            elements.append(e)
            alltime.append(retrieveCreationTimeOfFile(path, e))

def show(path, allFiles, allCreationTime):
    print("Files are from " + path)
    print("")
    for i in range (0,len(allFiles)):
        print(allFiles[i] + " : " + allCreationTime[i])

def main():
    # Create the path
    path = "/home/landure/go/src/github.com/etiennelndr/archiveservice/"
    # Create a variable for all the elements
    elements = list()
    # Create a variable for all the time
    alltime = list()

    # Retrieve all the files from a path
    retrieveAll(path, elements, alltime)

    # Finally, show the results
    show(path, elements, alltime)

if __name__=="__main__":
    main()