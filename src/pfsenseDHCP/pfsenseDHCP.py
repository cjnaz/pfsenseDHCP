#!/usr/bin/env python3
"""Merge DHCP4 static assignments .csv data into pfSense DHCP Server config file

DHCP static definitions in the CSV_master_list file are merged into (replacing) the static definitions
in the generated dhcp-config-pfSense....xml-csvX file.

Typically pfsense backups are saved to your browser backup directory.  If the Config_backup arg
refers to a directory then pfsenseDHCP will find the newest .xml file.  Alternately, the Config_backup
arg may refer to a specific input file.

The output file has the same name as the input file, plus '-csvX', where 'X' is an incrementing number
for each successive run.  The original input file is never modified.

The generated .xml-csvX file may then be restored into pfsense.  See the README for specifics.

This tool may also be run on a full pfsense backup (config-pfSense) file.
"""

#==========================================================
#
#  Chris Nelson, Copyright 2025
#
#==========================================================

import argparse
import sys
import os.path
import copy
import csv
import base64
from pathlib import Path
from lxml import etree

import importlib.metadata
__version__ = importlib.metadata.version(__package__ or __name__)

from cjnfuncs.core          import set_toolname, setuplogging, logging
from cjnfuncs.mungePath     import mungePath, check_path_exists
from cjnfuncs.deployfiles   import deploy_files
import cjnfuncs.core as core


# Configs / Constants
TOOLNAME =      'pfsenseDHCP'
DEFAULT_CSV =   'DHCP_master_list.csv'
CIDR_DEFAULT =  24                                  # Number of NetworkID bits in ipaddr, eg 24 in 192.168.1.1


def main():

    parser = etree.XMLParser(strip_cdata=False)     # CDATA sections are retained when working with a full backup
    tree = etree.parse(in_config_file, parser)
    root = tree.getroot()
    dhcpd_root = root                               # case for working with a dhcpd backup
    if root.tag == 'pfsense':
        dhcpd_root = root.find('dhcpd')             # case for working with a full backup


    # Get dhcpd sections/subnets
    subnet_names = []                               # ['lan', 'opt1', 'opt2', ...]
    networkID_to_subnet_name_map = {}               # {'192.168.1':'lan', '192.168.10':'opt1', '192.168.20':'opt2', }
    for child in dhcpd_root:
        subnet_names.append(child.tag)
        networkID = get_networkID(child.find('range').find('from').text)
        networkID_to_subnet_name_map[networkID] = child.tag
        logging.debug (f"Found interface <{child.tag}> with networkID <{networkID}>") # Found interface <opt2> with networkID <192.168.20>
    

    # Get the staticmap template
    found = False
    for subnet in subnet_names:
        for staticmap in dhcpd_root.find(subnet).findall('staticmap'):
            mac = staticmap.find('mac').text
            if mac == '12:34:56:78:90:ab':
                found = True
                template = copy.deepcopy(staticmap)
                add_entry(template, 'hostname', '')
                add_entry(template, 'ipaddr', '')
                add_entry(template, 'mac', '')
                add_entry(template, 'descr', '')
                break

        if found:
            break

    if not found:
        logging.error (f"Template <staticmap> block not found in input file - Aborting, see the documentation")
        sys.exit(1)
    else:
        logging.debug (f"Template:\n{etree.tostring(template, encoding='unicode')}")


    # Remove all <staticmap> blocks
    for subnet in subnet_names:
        for staticmap in dhcpd_root.find(subnet).findall('staticmap'):
            logging.debug (f"Removed staticmap block with mac {staticmap.find('mac').text} from subnet {subnet}")
            dhcpd_root.find(subnet).remove(staticmap)


    # Build the <staticmap> blocks
    with CSV_master_list_mp.full_path.open('rt') as csvfile:
        csv_table = csv.DictReader(csvfile, dialect='excel')


        # Create <staticmap> block per the CSV row
        numrows = 0
        for row in csv_table:
            logging.debug("-----------------------------------------------------------------------------------")
            logging.debug(f".csv line: {row}")

            try:
                if row['#Active'].strip() != '':                # Any non-whitespace in #Active column of a row marks the row to be processed
                    gotta_hostname = gotta_ipaddr = gotta_mac = gotta_cid = False
                    numrows += 1
                    temp_staticmap = copy.deepcopy(template)

                    for col in csv_table.fieldnames:
                        if not col.startswith('#'):                                     # A real entry column, not a comment
                            cell_text = row[col].strip()

                            if cell_text != '':
                                logging.debug (f".csv column    <{col}> = <{cell_text}>")

                                if col == 'hostname':
                                    add_entry(temp_staticmap, 'hostname', cell_text)
                                    hostname = cell_text
                                    gotta_hostname = True

                                elif col == 'ipaddr':
                                    networkID = get_networkID(cell_text)                # 192.168.10
                                    if networkID not in networkID_to_subnet_name_map:
                                        logging.error (f"IP address {cell_text} not valid or does not map to any defined subnet - Aborting\n  Row: {row}")
                                        sys.exit(1)
                                    add_entry(temp_staticmap, 'ipaddr', cell_text)
                                    gotta_ipaddr = True
                                    ipaddr = cell_text

                                elif col == 'mac':
                                    if '-' in cell_text:
                                        logging.error (f"MAC addresses must use ':' separators, not '-' - Aborting\n  Row: {row}")
                                        sys.exit(1)
                                    add_entry(temp_staticmap, 'mac', cell_text.lower())
                                    gotta_mac = True

                                elif col == 'cid':
                                    add_entry(temp_staticmap, 'cid', cell_text)
                                    gotta_cid = True

                                elif col == 'custom_kea_config':
                                    cell_text_bytes = cell_text.encode('utf-8')
                                    cell_text_encoded = base64.b64encode(cell_text_bytes).decode('utf-8')
                                    add_entry(temp_staticmap, 'custom_kea_config', cell_text_encoded)

                                elif cell_text.lower() == '__true__':
                                    add_entry(temp_staticmap, col, '')

                                elif col in ['winsserver', 'dnsserver', 'ntpserver']:
                                    for entry in cell_text.split(';'):
                                        add_entry(temp_staticmap, col, entry.replace(';', '').strip(), force_add=True)
                                else:
                                    add_entry(temp_staticmap, col, cell_text)

                    # Confirm minimum requirements of hostname, ipaddr, and mac
                    if not gotta_hostname or not gotta_ipaddr or not (gotta_mac or gotta_cid):
                        logging.error (f"Row missing required hostname, ipaddr, or mac/cid - Aborting\n  Row: {row}")
                        sys.exit(1)
                    else:
                        dhcpd_section = networkID_to_subnet_name_map[networkID]
                        logging.info (f"Processed DHCP static mapping for host:  {hostname:20} at <{ipaddr}> on interface <{dhcpd_section}>")
                        logging.debug(f"Adding to interface <{dhcpd_section}>:\n{etree.tostring(temp_staticmap, encoding='unicode')}")
                        dhcpd_root.find(dhcpd_section).append(temp_staticmap)
            except Exception as e:
                logging.error (f"Error during parsing of row - Aborting\n  Row: {row}")
                sys.exit(1)


    logging.info(f"Processed {numrows} DHCP static assignments.")

    etree.indent(tree, space='\t')      # Forces cleanup of indentation
    out_config_file.write_bytes (etree.tostring(root, pretty_print=True, encoding='utf-8'))


#---------------------------------------------------------------------------------------------
def add_entry (staticmap, element_name, value, force_add=False):
    logging.debug (f"Adding element <{element_name}> = <{value}>")
    if not force_add:           # Add only if not in template
        try:
            staticmap.find(element_name).text = value
        except:
            xx = etree.SubElement(staticmap, element_name)
            xx.text = value
            xx.tail = '\n                        '

    else:                       # Always add new element
        xx = etree.SubElement(staticmap, element_name)
        xx.text = value
        xx.tail = '\n                        '


#---------------------------------------------------------------------------------------------
def get_networkID(ipaddr):
    # given cidr=24 and ipaddr=192.168.10.16 returns '192.168.10'
    # given cidr=12 and ipaddr=10.255.5.5 returns '10.240'

    # print (ipaddr)
    octets_list = ipaddr.split('.')
    if len(octets_list) != 4:
        logging.error (f"Malformed ipaddr <{ipaddr}> - Aborting")
        sys.exit(1)

    ipaddr_value = 0
    for octet in octets_list:
        ipaddr_value = (ipaddr_value << 8) + int(octet)

    subnet_num = ipaddr_value >> (32 - args.CIDR)   # trim off lower bits

    justified_ID = subnet_num << (32 - args.CIDR)
    cidr_count = args.CIDR
    nbits = 24
    mask = 0xff000000
    subnet_str = ''

    while cidr_count > 0:
        xx = justified_ID >> nbits
        subnet_str += str(xx) + '.'
        justified_ID = justified_ID & ~mask
        mask = mask >> 8
        cidr_count -= 8
        nbits -= 8
    
    subnet_str = subnet_str[:-1]                    # trim off ending '.'
    
    logging.debug (f"ipaddr <{ipaddr}> on networkID/subnet <{subnet_str}>")
    return subnet_str


#---------------------------------------------------------------------------------------------
def cli():
    global in_config_file, out_config_file, CSV_master_list_mp
    global args

    set_toolname (TOOLNAME)
    setuplogging()
    defaultCSV =mungePath(DEFAULT_CSV, core.tool.config_dir)

    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('Config_backup',  nargs='?', default='.',
                        help="Path to dhcpd-config...xml backup.  If points to dir then use most recent file.  If points to file then use that specific file.")
    parser.add_argument('CSV_master_list', default=defaultCSV.full_path,  nargs='?',
                        help=f"Path to CSV master list file (default <{defaultCSV.full_path}>)")
    parser.add_argument('--CIDR', type=int, default=CIDR_DEFAULT,
                        help=f"Number of bits of the IP address that define the subnet (default {CIDR_DEFAULT})")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print status and activity messages (-vv for debug logging)")
    parser.add_argument('--setup-user', action='store_true',
                        help=f"Install starter files in user space to <{core.tool.config_dir}>")
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__,
                        help="Return version number and exit.")

    args = parser.parse_args()

    if args.setup_user:
        deploy_files([
            { 'source': DEFAULT_CSV,        'target_dir': 'USER_CONFIG_DIR', 'file_stat': 0o644, 'dir_stat': 0o755},
            ]) #, overwrite=True)
        logging.warning (f"Deployed <{DEFAULT_CSV}> to <{core.tool.config_dir}>")
        sys.exit()

    _level = [logging.WARNING, logging.INFO, logging.DEBUG][args.verbose  if args.verbose <= 2  else 2]
    logging.getLogger().setLevel(_level)

    logging.warning (f"========== {core.tool.toolname} ({__version__}) ==========")


    inconfig_mp = mungePath(args.Config_backup, '.', set_attributes=True)   # default to CWD
    in_config_file = ''
    if inconfig_mp.is_dir:
        files = inconfig_mp.full_path.glob('dhcpd-config*.xml')             # find newest backup .xml
        try:
            in_config_file = max(files, key=os.path.getctime)
        except:
            logging.error(f"No appropriate config backup .xml files found at <{inconfig_mp.full_path}> - Aborting")
            sys.exit(1)
    elif inconfig_mp.is_file:
        in_config_file = inconfig_mp.full_path

    if in_config_file == '':
        logging.error(f"Input argument Config_backup <{inconfig_mp.full_path}> is not a valid path to a file or directory - Aborting")
        sys.exit(1)
    logging.warning (f"  Input config backup file:    {in_config_file}")


    vnum = 1
    while 1:
        out_config_file = Path(str(in_config_file) + f'-csv{vnum}')
        if check_path_exists(out_config_file):
            vnum += 1
        else:
            break
    logging.warning (f"  Output config backup file:   {out_config_file}")


    CSV_master_list_mp = mungePath(args.CSV_master_list, core.tool.config_dir, set_attributes=True)
    if not CSV_master_list_mp.exists  or  not CSV_master_list_mp.is_file:
        logging.error(f"Input argument CSV_master_list {CSV_master_list_mp.full_path} is not a valid file path - Aborting")
        sys.exit(1)
    logging.warning (f"  CSV master list input file:  {CSV_master_list_mp.full_path}")

    main()


    
if __name__ == '__main__':
    sys.exit(cli())
