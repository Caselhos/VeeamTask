import datetime
import filecmp
import shutil
import sys
import os
import sched
import time
import pathlib


def context_cracking():
    if sys.platform != 'win32':
        print('WARNING - This script was designed and tested only on Windows')
    if sys.version_info.major != 3 and sys.version_info.minor != 12:
        print('WARNING - This script was designed and tested only on Python 3.12')


def command_line_parsing_safety():
    if len(sys.argv) < 5:
        sys.exit('number of arguments insufficient')
    if os.path.isdir(sys.argv[1]) and os.path.isabs(sys.argv[1]):
        print('SOURCE PATH IS A DIRECTORY AND ITS ABSOLUTE')  # main folder path
    else:
        sys.exit('SOURCE PATH NOT UP TO REQS')
    if os.path.isdir(sys.argv[2]) and os.path.isabs(sys.argv[2]):
        print('REPLICA PATH IS A DIRECTORY AND ITS ABSOLUTE')  # replica folder path
    else:
        sys.exit('REPLICA PATH NOT UP TO REQS')
    try:
        int(sys.argv[3])  # this is limited by 4300 digits the default
    except ValueError as e:
        print(e)
        sys.exit('INTERVAL DEFINITION NOT UP TO REQS')
    if os.path.isfile(sys.argv[4]) and os.path.isabs(sys.argv[4]):
        print('LOG FILE PATH IS A FILE AND ITS ABSOLUTE')  # log file path
    else:
        sys.exit('LOG FILE PATH NOT UP TO REQS')
    try:
        open(sys.argv[4], 'a')  # check if file is possible to open in write mode
        print('FILE IS WRITABLE')
    except PermissionError:
        sys.exit('YOU DO NOT HAVE PERMISSION TO WRITE FILE')


def logs_manager(s):
    print(s)  # log to stdout
    with open(sys.argv[4], 'a') as f:
        f.write(str(s + '\n'))  # log to log file


def directory_comparison_main_only(dircmp):
    for name in dircmp.left_only:
        fullpathMain = os.path.join(sys.argv[1], dircmp.left, name)
        fullpathReplica = os.path.join(sys.argv[2], dircmp.right, name)
        if os.path.isdir(fullpathMain):
            shutil.copytree(fullpathMain, fullpathReplica)
            logLine = "{} INFO - COPIED DIR {} FROM {} TO {}".format(datetime.datetime.now(), name, fullpathMain,
                                                                     fullpathReplica)
        else:
            shutil.copy2(fullpathMain, fullpathReplica)
            logLine = "{} INFO - COPIED FILE {} FROM {} TO {}".format(datetime.datetime.now(), name, fullpathMain,
                                                                      fullpathReplica)
        logs_manager(logLine)
    for sub in dircmp.subdirs.values():
        directory_comparison_main_only(sub)


def directory_comparison_replica_only(dircmp):
    for name in dircmp.right_only:
        fullpathReplica = os.path.join(sys.argv[2], dircmp.right, name)
        if os.path.isdir(fullpathReplica):
            shutil.rmtree(fullpathReplica)
            logLine = "{} INFO - DELETED DIR {} FROM {}".format(datetime.datetime.now(), name, fullpathReplica)
        else:
            pathlib.Path(fullpathReplica).unlink()
            logLine = "{} INFO - DELETED FILE {} FROM {}".format(datetime.datetime.now(), name, fullpathReplica)
        logs_manager(logLine)
    for sub in dircmp.subdirs.values():
        directory_comparison_replica_only(sub)


def directory_comparison_both(dircmp):
    # todo compare files that have similar structures but different content

    for name in dircmp.common_files:
        fullpathMain = os.path.join(sys.argv[1], dircmp.left, name)
        fullpathReplica = os.path.join(sys.argv[2], dircmp.right, name)

        if not filecmp.cmp(fullpathMain, fullpathReplica, shallow=False):
            shutil.copy2(fullpathMain, fullpathReplica)
            logLine = "{} INFO - UPDATED EXISTENT FILE {} FROM {} TO {}".format(datetime.datetime.now(), name,
                                                                                fullpathMain, fullpathReplica)
            logs_manager(logLine)
    for sub in dircmp.subdirs.values():
        directory_comparison_both(sub)


def job():
    logLine = "{} INFO - NEW SYNCHRONIZATION".format(datetime.datetime.now())
    logs_manager(logLine)
    filecmp.clear_cache()
    fc = filecmp.dircmp(sys.argv[1], sys.argv[2])
    directory_comparison_main_only(fc)  # FILES THAT ARE ONLY ON THE MAIN FOLDER GET SENT WITHOUT ANY TYPE OF CHECK
    directory_comparison_replica_only(fc)  # FILES THAT ARE ONLY ON THE REPLICA FOLDER SHOULD GET DELETED
    directory_comparison_both(fc)  # FILES THAT ARE IN BOTH FOLDERS NEED EXTENSIVE CHECK TO SEE IF THEY ARE SIMILAR
    scheduler.enter(int(sys.argv[3]), 1, job, ())

# CURRENT PROGRAM LIMITATIONS
# BOTH MAIN AND REPLICA FOLDER DIRECTORIES MUST EXIST (CREATED BEFORE RUNNING SCRIPT)
# LOG FILE NEEDS TO ALREADY HAVE BEEN CREATED (CREATED BEFORE RUNNING SCRIPT)
# ALL PATHS GIVEN TO COMMAND LINE MUST BE ABSOLUTE PATHS (IS THIS PLATFORM DEPENDENT?)
# INTERVAL TIME NEEDS TO BE IN SECONDS AND A INTEGER


if __name__ == '__main__':

    context_cracking()
    command_line_parsing_safety()
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(int(sys.argv[3]), 1, job, ())
    scheduler.run()  # this is an infinite loop
