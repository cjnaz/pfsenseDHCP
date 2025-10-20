#!/usr/bin/env python3
"""Merge DHCP static assignments .csv data into pfSense DHCP Server config file

DHCP static definitions in the CSV_master_list .csv file are merged into (replacing) the static definitions
in the generated dhcp-config-pfSense... .xlm-csvX file.

Typically pfsense backups are saved to your browser backup directory.  If the Config_backup param
references the save directory, then pfsenseDHCP will find the newest .xml file.  Alternately, a specific 
input file may be directly referenced.

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
import re
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
IPADDR_FORMAT = r'192.168.([\d]+).\d+'      # Adjust for your local IP subnet strategy TODO arg param


def main():

    parser = etree.XMLParser(strip_cdata=False)     # CDATA sections retained when working with a full backup
    tree = etree.parse(in_config_file, parser)
    root = tree.getroot()
    dhcpd_root = root                               # case for working with a dhcpd backup
    if root.tag == 'pfsense':
        dhcpd_root = root.find('dhcpd')             # case for working with a full backup


    # Get dhcpd sections/subnets
    subnets = []
    octet_to_subnet_map = {}
    for child in dhcpd_root:
        octet = get_ip_subnet(child.find('range').find('from').text)
        subnets.append([child.tag, octet])
        octet_to_subnet_map[octet] = child.tag
        logging.debug (f"Found interface <{child.tag}> with IP subnet octet <{octet}>") # Found interface <opt2> with IP subnet octet <20>
    
        print (get_subnet(child.find('range').find('from').text))

    sys.exit()

    # Get the staticmap template
    found = False
    for subnet in subnets:
        for staticmap in dhcpd_root.find(subnet[0]).findall('staticmap'):
            mac = staticmap.find('mac').text
            if mac == '12:34:56:78:90:ab':
                found = True
                template = copy.deepcopy(staticmap)
                add_entry(template, 'hostname', '')
                add_entry(template, 'ipaddr', '')
                add_entry(template, 'mac', '')
                break

        if found:
            break

    if not found:
        logging.error (f"ERROR:  Template <staticmap> block not found in input file - See the documentation")
        sys.exit(1)
    else:
        logging.debug (f"Template:\n{etree.tostring(template, encoding='unicode')}")


    # Remove all <staticmap> blocks
    for subnet in subnets:
        for staticmap in dhcpd_root.find(subnet[0]).findall('staticmap'):
            logging.debug (f"Removed staticmap block with mac {staticmap.find('mac').text} from subnet {subnet[0]}")
            dhcpd_root.find(subnet[0]).remove(staticmap)


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
                                    octet = get_ip_subnet(cell_text)
                                    if octet not in octet_to_subnet_map:
                                        logging.error (f"ERROR:  IP address {cell_text} not valid or does not map to any defined subnet - Aborting. \nRow: {row}")
                                        sys.exit(1)
                                    add_entry(temp_staticmap, 'ipaddr', cell_text)
                                    gotta_ipaddr = True

                                elif col == 'mac':
                                    if '-' in cell_text:
                                        logging.error (f"ERROR:  MAC addresses must use ':' separators, not '-' - Aborting. \nRow: {row}")
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
                        logging.error (f"ERROR:  Row missing required hostname, ipaddr, or mac - Aborting. \nRow: {row}")
                        sys.exit(1)
                    else:
                        logging.info (f"Processed DHCP static mapping for host <{hostname}>")
                        dhcpd_section = octet_to_subnet_map[octet]
                        logging.debug(f"Adding to interface <{dhcpd_section}>:\n{etree.tostring(temp_staticmap, encoding='unicode')}")
                        dhcpd_root.find(dhcpd_section).append(temp_staticmap)
            except Exception as e:
                logging.error (f"ERROR during parsing of row - Aborting.  Row:\n  {row}")
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
ip_format_re = re.compile(IPADDR_FORMAT)

def get_ip_subnet(ipaddr):
    """Given an IP address, return the subnet octet based on the defined IPADDR_FORMAT
    EG:
        192.168.99.7  returns str '99', given IPADDR_FORMAT = '192.168.([\d]+)'
    """
    out = ip_format_re.match(ipaddr)
    if out:
        subnet = out.group(1)
    else:
        subnet = 'ERROR'
        logging.debug (f"ERROR:  Failed getting subnet from ipaddr <{ipaddr}>")

    return subnet

cidr = 24
def get_subnet(ipaddr):
    # get upper <cidr> bits and return as int
    # cidr=24 for ipaddress 192.168.10.16 returns

    print (ipaddr)
    octets_list = ipaddr.split('.')
    # cidr_nbits = cidr
    # octet_index = -1
    # cidr_value = 0
    ipaddr_value = 0  # TODO check len=4
    for octet in octets_list:
        print (octet)
        ipaddr_value = (ipaddr_value << 8) + int(octet)
    # for octet_num in range(4):

    #     ipaddr_value << 8 + int(octets_list[octet_num])
    print (ipaddr_value)
    subnet_num = ipaddr_value >> (32 - cidr)
    print (subnet_num)

    return subnet_num


#---------------------------------------------------------------------------------------------
def cli():
    global in_config_file, out_config_file, CSV_master_list_mp

    set_toolname (TOOLNAME)
    setuplogging()
    defaultCSV =mungePath(DEFAULT_CSV, core.tool.config_dir)

    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('Config_backup',  nargs='?', default='.',
                        help="Path to dhcpd-config...xml backup.  If points to dir then use most recent file.  If points to file then use that specific file.")
    parser.add_argument('CSV_master_list', default=defaultCSV.full_path,  nargs='?',
                        help=f"Path to CSV master list file (default <{defaultCSV.full_path}>)")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print status and activity messages (-vv for debug logging).")
    parser.add_argument('--setup-user', action='store_true',
                        help=f"Install starter files in user space to <{core.tool.config_dir}>.")
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


    inconfig_mp = mungePath(args.Config_backup, '.', set_attributes=True)                # default to CWD
    in_config_file = ''
    if inconfig_mp.is_dir:
        files = inconfig_mp.full_path.glob('dhcpd-config*.xml')     # find newest backup .xml
        try:
            in_config_file = max(files, key=os.path.getctime)
        except:
            logging.error(f"Error:  No appropriate config backup .xml files found at <{inconfig_mp.full_path}>")
            sys.exit(1)
    elif inconfig_mp.is_file:
        in_config_file = inconfig_mp.full_path

    if in_config_file == '':
        logging.error(f"Error:  Input argument Config_backup <{inconfig_mp.full_path}> is not a valid path to a file or directory.")
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
        logging.error(f"Error:  Input argument CSV_master_list {CSV_master_list_mp.full_path} is not a valid file path.")
        sys.exit(1)
    logging.warning (f"  CSV master list input file:  {CSV_master_list_mp.full_path}")

    main()


    
if __name__ == '__main__':
    sys.exit(cli())
