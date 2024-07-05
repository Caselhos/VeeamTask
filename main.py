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
    if len(sys.argv) != 5:
        sys.exit('NUMBER OF ARGUMENTS INCORRECT')
    if not os.path.isdir(sys.argv[1]) and not os.path.isabs(sys.argv[1]):
        sys.exit('SOURCE PATH NOT UP TO REQS')
    if not os.path.isdir(sys.argv[2]) and not os.path.isabs(sys.argv[2]):
        sys.exit('REPLICA PATH NOT UP TO REQS')
    try:
        int(sys.argv[3])  # This is limited by 4300 digits the default.
    except ValueError as e:
        print(e)
        sys.exit('INTERVAL DEFINITION NOT UP TO REQS')
    if not os.path.isfile(sys.argv[4]) and not os.path.isabs(sys.argv[4]):
        sys.exit('LOG FILE PATH NOT UP TO REQS')
    try:
        open(sys.argv[4], 'a')  # Check if file is possible to open in write mode.
    except PermissionError:
        sys.exit('YOU DO NOT HAVE PERMISSION TO WRITE FILE')


def logs_manager(s):
    print(s)  # log to stdout
    with open(sys.argv[4], 'a') as f:
        f.write(str(s + '\n'))  # log to log file


def directory_comparison_object_exists_on_source_only(dir_cmp):
    for name in dir_cmp.left_only:
        fullpathMain = os.path.join(sys.argv[1], dir_cmp.left, name)
        fullpathReplica = os.path.join(sys.argv[2], dir_cmp.right, name)
        if os.path.isdir(fullpathMain):
            shutil.copytree(fullpathMain, fullpathReplica)
            logLine = "{} INFO - COPIED DIR {} FROM {} TO {}".format(datetime.datetime.now(), name, fullpathMain,
                                                                     fullpathReplica)
        else:
            shutil.copy2(fullpathMain, fullpathReplica)
            logLine = "{} INFO - COPIED FILE {} FROM {} TO {}".format(datetime.datetime.now(), name, fullpathMain,
                                                                      fullpathReplica)
        logs_manager(logLine)
    for sub in dir_cmp.subdirs.values():
        directory_comparison_object_exists_on_source_only(sub)


def directory_comparison_object_exists_on_replica_only(dir_cmp):
    for name in dir_cmp.right_only:
        fullpathReplica = os.path.join(sys.argv[2], dir_cmp.right, name)
        if os.path.isdir(fullpathReplica):
            shutil.rmtree(fullpathReplica)
            logLine = "{} INFO - DELETED DIR {} FROM {}".format(datetime.datetime.now(), name, fullpathReplica)
        else:
            pathlib.Path(fullpathReplica).unlink()
            logLine = "{} INFO - DELETED FILE {} FROM {}".format(datetime.datetime.now(), name, fullpathReplica)
        logs_manager(logLine)
    for sub in dir_cmp.subdirs.values():
        directory_comparison_object_exists_on_replica_only(sub)


def directory_comparison_object_exists_on_both(dir_cmp):
    for name in dir_cmp.common_files:
        fullpathMain = os.path.join(sys.argv[1], dir_cmp.left, name)
        fullpathReplica = os.path.join(sys.argv[2], dir_cmp.right, name)

        if not filecmp.cmp(fullpathMain, fullpathReplica, shallow=False):
            shutil.copy2(fullpathMain, fullpathReplica)
            logLine = "{} INFO - UPDATED EXISTENT FILE {} FROM {} TO {}".format(datetime.datetime.now(), name,
                                                                                fullpathMain, fullpathReplica)
            logs_manager(logLine)
    for sub in dir_cmp.subdirs.values():
        directory_comparison_object_exists_on_both(sub)


def job():
    log_line = "{} INFO - NEW SYNCHRONIZATION".format(datetime.datetime.now())
    logs_manager(log_line)
    filecmp.clear_cache()
    fc = filecmp.dircmp(sys.argv[1], sys.argv[2])
    directory_comparison_object_exists_on_source_only(fc)  # Add files unique on source to replica.
    directory_comparison_object_exists_on_replica_only(fc)  # Delete files unique on replica.
    directory_comparison_object_exists_on_both(fc)  # Updates files that are similar but with different contents.
    scheduler.enter(int(sys.argv[3]), 1, job, ())


if __name__ == '__main__':
    print("STARTING TASK")
    context_cracking()
    command_line_parsing_safety()
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(int(sys.argv[3]), 1, job, ())
    try:
        scheduler.run()  # Infinite loop.
    except KeyboardInterrupt:
        sys.exit(0)
