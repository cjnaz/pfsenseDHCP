# pfsenseDHCP - Manage your DHCP4 static mappings in a .csv master file

This tool enables you to manage your network static host assignments in an Excel-style .csv file.  **Why?**  It's tedious to 
manage static assignments using the pfSense GUI.  All features of a DHCP4 static host assignment may be defined by simply
adding the appropriate columns to the .csv file, and the static host assignments will naturally track pfSense version changes.
- ISC and Kea DHCP server backends are supported
- This tool runs on Windows and Linux
- Tested on pfSense+ versions 23.09.1-RELEASE and 25.07.1-RELEASE
- Tested on Python 3.9 and 3.11

<br/>

---

## Usage

```
$ pfsenseDHCP -h
usage: pfsenseDHCP [-h] [--CIDR CIDR] [-v] [--setup-user] [-V] [Config_backup] [CSV_master_list]

Merge DHCP4 static host assignments .csv data into pfSense DHCP Server config file

DHCP static definitions in the CSV_master_list file are merged into (replacing) the static definitions
in the generated dhcp-config-pfSense....xml-csvX file.

Typically pfsense backups are saved to your browser backup directory.  If the Config_backup arg
refers to a directory then pfsenseDHCP will find the newest .xml file.  Alternately, the Config_backup
arg may refer to a specific input file.

The output file has the same name as the input file, plus '-csvX', where 'X' is an incrementing number
for each successive run.  The original input file is never modified.

The generated .xml-csvX file may then be restored into pfsense.  See the README for specifics.

This tool may also be run on a full pfsense backup (config-pfSense) file.
2.0

positional arguments:
  Config_backup    Path to dhcpd-config...xml backup.  If points to dir then use most recent file.  If points to file then use that specific file.
  CSV_master_list  Path to CSV master list file (default </home/cjn/.config/pfsenseDHCP/DHCP_master_list.csv>)

options:
  -h, --help       show this help message and exit
  --CIDR CIDR      Number of bits of the IP address that define the subnet (default 24)
  -v, --verbose    Print status and activity messages (-vv for debug logging)
  --setup-user     Install starter files in user space to </home/cjn/.config/pfsenseDHCP>
  -V, --version    Return version number and exit.
```

Example output:
```
$ pfsenseDHCP /pathto/Downloads -v
    pfsenseDHCP.cli                  -  WARNING:  ========== pfsenseDHCP (2.0) ==========
    pfsenseDHCP.cli                  -  WARNING:    Input config backup file:    /pathto/Downloads/dhcpd-config-pfSense.my.lan-20251020214639.xml
    pfsenseDHCP.cli                  -  WARNING:    Output config backup file:   /pathto/Downloads/dhcpd-config-pfSense.my.lan-20251020214639.xml-csv5
    pfsenseDHCP.cli                  -  WARNING:    CSV master list input file:  /home/me/.config/pfsenseDHCP/DHCP_master_list.csv
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  Switch1              at <192.168.99.5> on interface <opt4>
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  Switch2              at <192.168.99.6> on interface <opt4>
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  AP1                  at <192.168.99.15> on interface <opt4>
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  AP2                  at <192.168.99.16> on interface <opt4>
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  Office               at <192.168.10.10> on interface <opt1>
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  Office2              at <192.168.10.14> on interface <opt1>
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  testhost2            at <192.168.15.42> on interface <opt5>
    pfsenseDHCP.main                 -     INFO:  Processed DHCP static mapping for host:  testhostX            at <192.168.15.41> on interface <opt5>
    ...
    pfsenseDHCP.main                 -     INFO:  Processed 47 DHCP static assignments.
```

<br/>

---

## Setup and Usage notes
- Install pfsenseDHCP from PyPI:  `pip install pfsenseDHCP`.

- Install the initial configuration file: `pfsenseDHCP --setup-user` places a beginner `DHCP_master_list.csv` file at `~/.config/pfsenseDHCP`.

- Edit/configure the `DHCP_master_list.csv` to define static host assignments (one per row).  Add columns as needed for features you need.  Excel, LibreOffice Calc, or a text editor may be used.
  - At a minimum, define the `mac` (or `cid`), `ipaddr`, and `hostname` for each host assignment.
  - A static host assignment can be enabled with a `y` (or any text) int the `#Active` column, or disabled if left blank.  Blank line are also supported.
  - Notes related columns may be defined (column name starting with `#`).  This data doesn't make it into pfSense.
  - Other DHCP server features may be configured by adding more columns.  Values in cells are only needed for hosts that need them.
  -  Save from Excel as "CSV (MS-DOS)" format, not "CSV UTF-8"

- In pfSense, create a new static mapping in any one of your DHCP Server interfaces (does not matter which) with `hostname` = `Template`, `mac` address = `12:34:56:78:90:ab`, and any `ipaddr` within the subnet's address space. pfsenseDHCP uses this Template instance when generating new `<staticmap>` blocks.

- Export/save the initial/current DHCP backup.  It will likely be saved to your browser's Downloads directory.
  - Diagnositics > Backup & Restore > Backup Configuration - set Backup area to `DHCP Server`, and hit the `Download configuration as XML` button.

- Run pfsenseDHCP:  `pfsenseDHCP <path-to-Downloads-dir>`.
  - The most recent `dhcpd-config...xml` will be used.
  - The `CSV_master_list` arg defaults to `~/.config/pfsenseDHCP/DHCP_master_list.csv`.
  - A new XML file will be written to the Downloads directory with a `.xml-csvX` suffix.

- Back in pfSense, load the new .xml-csvX file
  - ... > Restore Backup - set Restore area to `DHCP Server`, select the generated `.xml-csvX` in the Downloads directory, and hit `Restore Configuration`.

- In pfSense, go to Services > DHCP Server and check that the interface DHCP Static Mappings look proper.
  - Re-edit the .csv file, regenerate the `.xml-csvX` file, and reload as needed. `X` is an integer that increments for each generated version.

- When happy with the loaded mappings, hit the `Restart Service` icon at the top-right of the page.  Your mappings are now live!

<br/>

---

## Reference details

- After loading the updated/modified DHCP backup file you must manually restart the DHCP server.  Go to Services > DHCP Server and hit the Restart Service icon at the top-right (partial circle with arrow at top-right).  pfSense then extracts the settings from the DHCP Server GUI settings and constructs the Kea DHCP config file (stored at /usr/local/etc/kea/kea-dhcp4.conf), and then attempts to restart the Kea DHCP4 service.  If the Restart Service icon spins and then again shows the Restart Service icon then you're all good.  If it shows a red circle with a right-facing 'Play' icon then the server restart has failed.  There's probably some illegal syntax in the loaded config file.  

- Error checking on the imported data is minimal.  If the Kea DHCP server refuses to start then 
  - Look at the logs (Status > System Logs > System > General and scroll to the most recent) for clues.  
  - If your control/setup computer can't get an IP address (shows 169.254.x.x), then change temporarily to a static IP address on the same subnet as the pfSense device (eg, 192.168.1.20) to gain access to the pfSense GUI.
  - Connect to the pfSense console to restore recent configuration (option 15), and reboot system (option 5).

- Either `mac` or `cid` is required. See the Kea DHCP server repo [https://gitlab.isc.org/isc-projects/kea](https://gitlab.isc.org/isc-projects/kea) and [pfSense static mapping documentation](https://docs.netgate.com/pfsense/en/latest/services/dhcp/ipv4.html#static-mappings) as needed.

- The built-in assumption is that all subnets/interfaces use the same netmask / CIDR width (default 24, aka 255.255.255.0).  CIDR is settable on the command line.  However, within pfSense the netmask / CIDR width may be set differently on each interface.  If different netmask widths are needed this tool can be enhanced (would require operating on a full backup as the subnet netmask width is not available on a DHCP Server backup).

- Notes on specific columns
  - `mac` (or `cid`), `ipaddr`, and `hostname` elements are required columns.

  - The `descr` element is handled only within pfSense's GUI system, not passed to Kea.

  - Documentation fields in the .csv file have column names that start with `#`, such as `#Notes`.  These columns are ignored by this tool, with the exception of the `#Active` column, which is used to mark individual rows as in-use or inactive.  Inactive/disabled rows are not processed into \<staticmap> blocks in the DHCP backup .xml file.

  - Additional elements may be added to the \<staticmap> by creating .csv column names that match the expected .xml element names.  The element is created if the row's cell content is not empty.  No error checking is done on the validity of the element names or cell content.

  - `WINS Servers`, `DNS Servers`, and `NTP Servers` each accept multiple entires.  In the DHCP backup .xml file these are listed as multiple elements with the same name, eg two \<winsserver> elements.  pfsenseDHCP handles these by allowing semicolon separated multiple entires for these fields, and will process them out to multiple elements in the regenerated DHCP backup .xml file.
    - Note that pfSense shows room for four NTP Server entries, but only three are accepted.

  - Some GUI options are simply check boxes, such as `Static ARP Entry`.  These switches are typically represented in the DHCP backup .xml file as the existence of an element if checked, or non-existence if not checked.  To set such options in the .csv file define the appropriate column name (`arp_table_static_entry`) and enter `__true__` in the appropriate row cell.

  - The `custom_key_config` element content is base64 compressed.  Only valid content makes it into the Kea .conf file (viewable via Diagostics > Command Prompt > Execute Shell Command with "cat /usr/local/etc/kea/kea-dhcp4.conf").


  - A partial list of pfSense GUI fields to .xml backup file elements, and how they are listed in the Kea DHCP .conf file.  If you are interested in an unlisted GUI field then experiment with creating a DHCP static mapping, then do a DHCP Server backup to identify the .xml element name and data format.

    DHCP backup .xml element | GUI field (V25.07.1) | kea-dhcp4.conf json key | Notes
    --|--|--|--
    mac | MAC Address | hw-address
    cid | Client Identifier | reservations > client-id 
    ipaddr | IP Address | ip-address
    hostname | Hostname | hostname
    arp_table_static_entry | Static ARP Entry | (not passed to Kea)
    descr | Description | (not passed to Kea)
    earlydnsregpolicy | Early DNS Registration | (not passed to Kea)
    gateway | Gateway | routers
    domain | Donmain Name | domain-name
    domainsearchlist | Domain Search List | domain-search
    dnsserver | DNS Servers | domain-name-servers
    winsserver | WINS Server | netbios-name-servers (also set netbios-node-type = 8)
    ntpserver | NTP Server | ntp-servers
    custom_kea_config | JSON Configuration | option-data | See kea documentation for options.  The .xml format is base64 encoded.

- Notes on xml syntax variations
  - pfsenseDHCP uses the lxml library, which uses the _empty-element tag_ syntax style for tags with no content, whereas pfSense backup outputs the _start-tag / end-tag pair_ syntax.  Both are equivalent and pfSense loads the empty-element tag syntax correctly.

  - pfSense backup outputs raw text fields, such as `descr`, wrapped in a CDATA structure, whereas pfsenseDHCP uses lxml's feature to automatically escape xml special characters (eg, '>' in the descr text becomes '&gt'), which loads correctly into pfSense.

<br/>

---

## Known issues / Future enhancements

- Support for per-interface CIDR width
- The cid mechanism has not been tested (I don't use it)

<br/>

---

## Version history
- 2.0 251022 - Packaged and upgraded for Kea DHCP server support
- 1.0 211025 - Reworked to use real .xml handling (lxml dependency). Supports multiple dhcpd subnets.
- 0.1 211009 - Bug fix for row ignore based on first column blank. Properly carry over the real postamble and block indentation.
- 0.0 211007 - New

