#!/usr/bin/env python3
"""Description goes here.
"""

#==========================================================
#
#  Chris Nelson, Copyright 2023
#
# 0.1 230226 - New
#
#==========================================================

import argparse
import sys
import os.path
# import io
# import tempfile
import time
import datetime
import re
import subprocess
import signal
import platform
import collections

print ("package:", __package__)
print ("name:   ", __name__)
print ("__package__ or __name__:", __package__ or __name__)
print ("__spec__:", __spec__)
# if __package__ is not None:
#     print (__package__.__spec__)
try:
    import importlib.metadata
    __version__ = importlib.metadata.version(__package__ or __name__)
    # print ("Using importlib.metadata for __version__ assignment")
except:
    try:
        import importlib_metadata
        __version__ = importlib_metadata.version(__package__ or __name__)
        # print ("Using importlib_metadata for __version__ assignment")
    except:
        __version__ = "0.2 X"
        # print ("Using local __version__ assignment")

from cjnfuncs.core          import set_toolname, logging, ConfigError    #, setuplogging, SndEmailError
from cjnfuncs.configman     import config_item
from cjnfuncs.mungePath     import mungePath
from cjnfuncs.deployfiles   import deploy_files
from cjnfuncs.timevalue     import timevalue, retime
# from cjnfuncs.resourcelock  import resource_lock
# from cjnfuncs.SMTP          import snd_notif, snd_email
import cjnfuncs.core as core


# Configs / Constants
TOOLNAME        = "newtool"
CONFIG_FILE     = "template.cfg"
# LOG_FILE      = "log_file.txt"        # Specify if args.log_file is used
PRINTLOGLENGTH  = 40
OUTFILE         = "myoutfile.txt"
PY_MIN_VERSION  = (3, 6)                # Remove check code for modules to be installed
PY_VERSION      = sys.version_info
SYSTEM          = platform.system()     # 'Linux', 'Windows', ...


def main():
    # code examples
    logging.warning(f"Python version <{PY_VERSION}>")
    logging.warning(f"Platform       <{SYSTEM}>")

    _cmd = ["uptime", "-p"]
    try:
        if PY_VERSION >= (3, 7):
            uptime = subprocess.run(_cmd, capture_output=True, text=True).stdout
        else:   #Py 3.6 .run does not support capture_output, so use the old method.
            uptime = subprocess.run(_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout
    except Exception as e:
        logging.warning (f"Getting uptime failed:\n  {e}")
    except Exception:
        logging.exception (f"Getting uptime failed")
    else:
        logging.warning (uptime.replace('\n',''))

    # matchstring = re.compile(r'^([\w:-]+)@$')
    # out = matchstring.match(args.Infile)        # matches "junk:5-@"
    # if out:
    #     logging.warning (f"Match: <{out.group(1)}>")

    # logging.warning (f"Update switch <{args.update}>")

    logging.warning (f"Making tool data directory <{core.tool.data_dir}>")
    mungePath(base_path=core.tool.data_dir, mkdir=True)      # Make dir if not yet existing

    out_file = mungePath(OUTFILE, core.tool.data_dir).full_path
    logging.warning (f"Writing to <{out_file}>")
    with out_file.open("w") as outfile:
        outfile.write(f"Python version <{PY_VERSION}>\n")
        outfile.write(f"Platform       <{SYSTEM}>\n")


def service():
    global network_error
    logging.info ("Entering service loop.  Edit config file 'testvar'.  Ctrl-C to exit")
    first = True
    missing_config_file = False
    network_error = False
    
    next_run_dt = datetime.datetime.now()
    tick = 0

    while True:
        try:
            # This code allows the config file to disappear (ie, network dropped) without
            # aborting.  Unhandled side effect:  If an _imported_ config file is not available then
            # the cfg will have been flushed and only partially reloaded, likely leading to a crash.
            reloaded = config.loadconfig(flush_on_reload=True,
                                         tolerate_missing=True,
                                         call_logfile_wins=call_logfile_override) #, ldcfg_ll=20)
            if reloaded == -1:      # config file not found
                network_error = True
                if not missing_config_file:
                    missing_config_file = True
                    logging.info(f"Can't find or load the config file <{config.config_full_path}> - skipping reload check.")
            else:                   # config file found
                network_error = False
                if missing_config_file:
                    missing_config_file = False
                    logging.info(f"Config file <{config.config_full_path}> found again.")
        except ConfigError as e:
            logging.error(f"Error when loading config file.  Aborting.:\n  {e}")
            sys.exit()

        if reloaded == 1:
            logging.warning ("Config file reloaded")
            logging.warning(f"testvar                {config.getcfg('testvar', None)}  type {type(config.getcfg('testvar', None))}")
            logging.warning(f"Current LogFile        {core.tool.log_full_path}")
            logging.warning(f"Config LogLevel        {config.getcfg('LogLevel', None)}")
            logging.warning(f"Current logging level  {logging.getLogger().level}")
            logging.info ("info  level log")
            logging.debug("debug level log")
            tick = 0

        if first  or  reloaded == 1:
            if first:
                first = False
            else:                   # reloaded case
                pass
                # Do any cleanup before re-setup

            # Do setup stuff

            if reloaded == 1:
                logging.info("***** Restarting Service loop *****")


        now_dt = datetime.datetime.now()
        if now_dt > next_run_dt:
            print (tick)
            tick += 1
            next_run_dt += datetime.timedelta(seconds=timevalue(config.getcfg("ServiceLoopTime", "1s")).seconds)
        time.sleep(0.5)


def cleanup():
    logging.warning ("Cleanup")


def int_handler(signal, frame):
    logging.warning(f"Signal {signal} received.  Exiting.")
    cleanup()
    sys.exit(0)
signal.signal(signal.SIGINT,  int_handler)      # Ctrl-C
signal.signal(signal.SIGTERM, int_handler)      # kill


def cli():
    global config, args, call_logfile_override

    set_toolname (TOOLNAME)
    print (core.tool)

    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    # parser.add_argument('Infile',                                               # Argparse argument examples
    #                     help="The infile")
    # parser.add_argument('Command', nargs='?',                                   # optional positional argument
    #                     help=f"The command  ({COMMANDS})")
    # parser.add_argument('-u', '--update', type=int, default=UPDATE_INTERVAL,
    #                     help=f"Update interval (default = {UPDATE_INTERVAL}s).")
    # parser.add_argument('--now', dest='format', choices=['std', 'iso', 'unix', 'tz'],
    #                     help="shows datetime in given format")
    # parser.add_argument('-v', '--verbose', action='count',
    #                     help="Print status and activity messages.")
    # parser.add_argument('-c', type=int, required=True, metavar='countvalue',
    #                     help="Count value.",)
    parser.add_argument('--config-file', '-c', type=str, default=CONFIG_FILE,
                        help=f"Path to the config file (Default <{CONFIG_FILE})> in user/site config directory.")
    # parser.add_argument('--log-file', default=None,         # With config file version
    #                     help=f"Path to log file (overrides LogFile in config file, default <{None}).")
    # parser.add_argument('--log-file', default=LOG_FILE,     # Without config file version
    #                     help=f"Path to log file (default <{LOG_FILE}).")
    parser.add_argument('--print-log', '-p', action='store_true',
                        help=f"Print the tail end of the log file (default last {PRINTLOGLENGTH} lines).")
    parser.add_argument('--service', action='store_true',
                        help="Enter endless loop for use as a systemd service.")
    parser.add_argument('--setup-user', action='store_true',
                        help=f"Install starter files in user space.")
    parser.add_argument('--setup-site', action='store_true',
                        help=f"Install starter files in system-wide space. Run with root prev.")
    parser.add_argument('-V', '--version', action='version', version=f"{core.tool.toolname} {__version__}",
                        help="Return version number and exit.")
    args = parser.parse_args()


    # Deploy template files
    if args.setup_user:
        deploy_files([
            { "source": CONFIG_FILE,        "target_dir": "USER_CONFIG_DIR", "file_stat": 0o644, "dir_stat": 0o755},
            { "source": "creds_SMTP",       "target_dir": "USER_CONFIG_DIR", "file_stat": 0o600},
            { "source": "template.service", "target_dir": "USER_CONFIG_DIR", "file_stat": 0o644},
            # { "source": "test_dir",         "target_dir": "USER_DATA_DIR/mydirs", "file_stat": 0o633, "dir_stat": 0o770},
            ]) #, overwrite=True)
        sys.exit()

    if args.setup_site:
        deploy_files([
            { "source": CONFIG_FILE,        "target_dir": "SITE_CONFIG_DIR", "file_stat": 0o644, "dir_stat": 0o755},
            { "source": "creds_SMTP",       "target_dir": "SITE_CONFIG_DIR", "file_stat": 0o600},
            { "source": "template.service", "target_dir": "SITE_CONFIG_DIR", "file_stat": 0o644},
            # { "source": "test_dir",         "target_dir": "SITE_DATA_DIR/mydirs", "file_stat": 0o633, "dir_stat": 0o770},
            ]) #, overwrite=True)
        sys.exit()


    # Load config file and setup logging
    # If no CLI --log-file, then remove 'call_logfile=args.log_file' from loadconfig calls
    # If using interactive mode then don't give --log-file so that it defaults to None, thus logging goes to console
    # Calculate call_logfile_override based on interactive needs:  True if not service mode then log to console
    #   Add 'or args.log_file is not None' if CLI --log-file should override config LogFile.
    call_logfile_override = True  if not args.service  else False        # or args.log_file is not None
    try:
        config = config_item(args.config_file)
        config.loadconfig(call_logfile_wins=call_logfile_override)       #, call_logfile=args.log_file, ldcfg_ll=10)
    except Exception:
        logging.exception(f"Failed loading config file <{args.config_file}>.  Aborting. \
\n  Run with  '--setup-user' or '--setup-site' to install starter files.")
        sys.exit(1)


    # Verbosity level
    # To use --verbose, don't include LogLevel in the config file (LogLevel would win)
    # if not args.service  and  args.verbose is not None:      # Python default logging level is logging.WARNING 
    #     _level = [logging.WARNING, logging.INFO, logging.DEBUG][args.verbose  if args.verbose <= 2  else 2]
    #     logging.getLogger().setLevel(_level)
    #     logging.info (f"Logging level set to <{_level}>")


    logging.warning (f"========== {core.tool.toolname} ({__version__}) ==========")
    logging.warning (f"Config file <{config.config_full_path}>")


    # Print log
    if args.print_log:
        try:
            _lf = mungePath(config.getcfg("LogFile"), core.tool.log_dir_base).full_path
            print (f"Tail of  <{_lf}>:")
            _xx = collections.deque(_lf.open(), config.getcfg("PrintLogLength", PRINTLOGLENGTH))
            for line in _xx:
                print (line, end="")
        except Exception as e:
            print (f"Couldn't print the log file.  LogFile defined in the config file?\n  {e}")
        sys.exit()


    # Python min version check      Remove check code for installed package
    if PY_VERSION < PY_MIN_VERSION:
        logging.error (f"Current Python version {platform.python_version_tuple()} is less than minimum required version {PY_MIN_VERSION}.  Aborting.")
        sys.exit(1)


    # Input file existence check (and any other idiot checks)
    # if not os.path.exists(args.Infile):
    #     logging.warning (f"Can't find the input file <{args.Infile}>.  Aborting.")
    #     sys.exit(1)


    # Run in service or interactive modes
    if args.service:
        service()

    main()

    
if __name__ == '__main__':
    sys.exit(cli())