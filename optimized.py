import concurrent
import datetime
import filecmp
import shutil
import sys
import os
import sched
import time
import pathlib
import stat
import concurrent.futures


def context_cracking():
    if sys.platform != 'win32':
        print('WARNING - This script was designed and tested only on Windows')
    if sys.version_info.major != 3 and sys.version_info.minor != 12:
        print('WARNING - This script was designed and tested only on Python 3.12')


def command_line_parsing_safety():
    if len(sys.argv) != 5:
        sys.exit('ERROR - NUMBER OF ARGUMENTS INCORRECT')
    if not os.path.isdir(sys.argv[1]) and not os.path.isabs(sys.argv[1]):
        sys.exit('ERROR - SOURCE PATH NOT UP TO REQS')
    if not os.path.isdir(sys.argv[2]) and not os.path.isabs(sys.argv[2]):
        sys.exit('ERROR - REPLICA PATH NOT UP TO REQS')
    try:
        int(sys.argv[3])  # This is limited by 4300 digits the default.
    except ValueError as e:
        print(e)
        sys.exit('ERROR - INTERVAL DEFINITION NOT UP TO REQS')
    if not os.path.isfile(sys.argv[4]) and not os.path.isabs(sys.argv[4]):
        sys.exit('ERROR - LOG FILE PATH NOT UP TO REQS')
    try:
        open(sys.argv[4], 'a')  # Check if file is possible to open in write mode.
    except PermissionError:
        sys.exit('ERROR - YOU DO NOT HAVE PERMISSION TO WRITE TO LOG FILE')


def logs_manager(s):
    #  maybe delete last file if write to log failed? to avoid missmatch?
    print(s)  # log to stdout
    try:
        with open(sys.argv[4], 'a') as f:
            f.write(str(s + '\n'))  # log to log file
    except PermissionError:
        sys.exit('ERROR - PERMISSION ERROR OCCURRED ON LOG FILE')


def directory_comparison_object_exists_on_source_only(dir_cmp):
    for name in dir_cmp.left_only:
        path_source = os.path.join(sys.argv[1], dir_cmp.left, name)
        path_replica = os.path.join(sys.argv[2], dir_cmp.right, name)
        if os.path.isdir(path_source):
            try:
                os.chmod(path_source, stat.S_IWRITE)
                shutil.copytree(path_source, path_replica)
                logLine = "{} INFO - COPIED DIR {} FROM {} TO {}".format(datetime.datetime.now(), name, path_source,
                                                                         path_replica)
                logs_manager(logLine)
            except shutil.Error:
                print('WARNING - COPY FN RETURNED A ERROR WILL RETRY NEXT SYNC')  # file is in use most likely

        else:
            try:
                os.chmod(path_source, stat.S_IWRITE)  # Platform dependant.
                shutil.copy2(path_source, path_replica)
                logLine = "{} INFO - COPIED FILE {} FROM {} TO {}".format(datetime.datetime.now(), name, path_source,
                                                                          path_replica)
                logs_manager(logLine)
            except PermissionError as e:
                print('WARNING - {}'.format(e))

    for sub in dir_cmp.subdirs.values():
        directory_comparison_object_exists_on_source_only(sub)


def redo_with_write(redo_func, path, err):  # Fixes error with readonly directories.
    os.chmod(path, stat.S_IWRITE)  # this is platform dependant. (https://docs.python.org/3/library/os.html#os.chmod)
    redo_func(path)


def directory_comparison_object_exists_on_replica_only(dir_cmp):
    for name in dir_cmp.right_only:
        path_replica = os.path.join(sys.argv[2], dir_cmp.right, name)
        if os.path.isdir(path_replica):
            shutil.rmtree(path_replica, onerror=redo_with_write)
            logLine = "{} INFO - DELETED DIR {} FROM {}".format(datetime.datetime.now(), name, path_replica)
        else:
            if not os.access(path_replica, os.W_OK):
                os.chmod(path_replica, stat.S_IWRITE)  # Handles if file is readonly.
            pathlib.Path(path_replica).unlink()
            logLine = "{} INFO - DELETED FILE {} FROM {}".format(datetime.datetime.now(), name, path_replica)
        logs_manager(logLine)
    for sub in dir_cmp.subdirs.values():
        directory_comparison_object_exists_on_replica_only(sub)


def file_comparison(path_source, path_replica, name):
    try:
        if filecmp.cmp(path_source, path_replica):  # Shallow comparison.
            return True
        else:
            if not filecmp.cmp(path_source, path_replica, shallow=False):
                shutil.copy2(path_source, path_replica)
                logLine = "{} INFO - UPDATED EXISTENT FILE {} FROM {} TO {}".format(datetime.datetime.now(), name,
                                                                                    path_source, path_replica)
                logs_manager(logLine)
    except FileNotFoundError as e:
        print('WARNING - {}'.format(e))  # todo This could be better maybe say what happens.


def directory_comparison_object_exists_on_both(dir_cmp):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for name in dir_cmp.common_files:
            path_source = os.path.join(sys.argv[1], dir_cmp.left, name)
            path_replica = os.path.join(sys.argv[2], dir_cmp.right, name)
            executor.submit(file_comparison, path_source, path_replica, name)
        for sub in dir_cmp.subdirs.values():
            directory_comparison_object_exists_on_both(sub)


def job():
    log_line = "{} INFO - NEW SYNCHRONIZATION".format(datetime.datetime.now())
    logs_manager(log_line)
    filecmp.clear_cache()
    fc = filecmp.dircmp(sys.argv[1], sys.argv[2])
    directory_comparison_object_exists_on_replica_only(fc)  # Delete files unique on replica.
    fc = filecmp.dircmp(sys.argv[1], sys.argv[2])
    directory_comparison_object_exists_on_source_only(fc)  # Add files unique on source to replica.
    fc = filecmp.dircmp(sys.argv[1], sys.argv[2])
    directory_comparison_object_exists_on_both(fc)  # Updates files that are similar but with different contents.
    scheduler.enter(int(sys.argv[3]), 1, job, ())


if __name__ == '__main__':
    print("INFO - STARTING TASK")
    context_cracking()
    command_line_parsing_safety()
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(2, 1, job, ())
    try:
        scheduler.run()  # Infinite loop.
    except KeyboardInterrupt:
        sys.exit(0)
