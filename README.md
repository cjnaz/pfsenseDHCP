# pfsenseDHCP - Manage your DHCP4 static mappings in a .csv master file

Supports both ISC and Kea backend DHCP4 servers

A partial list of pfSense GUI fields to .xml backup file elements, and how they are listed in the Kea DHCP .conf file.  If you are interested in an unlisted GUI field then experiment with creating a DHCP static mapping, then do a DHCP Server backup to identify the .xml element name and data format.

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
winsserver | WINS Server | netbios-name-servers (and sets netbios-node-type = 8)
ntpserver | NTP Server | ntp-servers
custom_kea_config | JSON Configuration | option-data | See kea documentation for options.  The .xml format is base64 encoded.

Kea DHCP server repo:  https://gitlab.isc.org/isc-projects/kea

After loading the updated/modified DHCP backup file you must manually restart the DHCP server.  Go to Services > DHCP Server and hit the Restart Service icon at the top-right (partial circle with arrow at top-right).  pfSense then extracts the settings from the DHCP Server GUI settings and constructs the Kea DHCP config file (stored at /usr/local/etc/kea/kea-dhcp4.conf), and then attempts to restart the Kea DHCP4 service.  If the Restart Service icon spins and then again shows the Restart Service icon then you're all good.  If it shows a red circle with a right-facing 'Play' icon then the server restart has failed.  There's probably some illegal syntax in the loaded config file.  

Error checking on the imported data is minimal.  If the Kea DHCP server refuses to start then 
- Look at the logs (Status > System Logs > System > General and scroll to the end) for clues.  
- connect to the pfSense console to restore recent configuration (option 15), and reboot system (option 5).
- If your control/setup computer can't get an IP address (shows 169.254.x.x), then change temporarily to a static IP address on the same subnet as the pfSense device (eg, 192.168.1.20) to gain access to the pfSense GUI.

Note:  WINS Servers, DNS Servers, and NTP Servers each accept two or four server entires.  In the DHCP backup file these are listed as multiple elements with the same name, eg two <winsserver> elements.  pfsenseDHCP handles these by allowing semicolon separated multiple entires for these fields, and will process them out to multiple elements in the regenerated DHCP backup .xml file.

Some GUI options are simply check boxes, such as 'Static ARP Entry'.  These switches are typically represented in the DHCP4 backup .xml file as the existence of an element if checked, or non-existence if not checked.  To set such option, in the .csv file define the appropriate column name ('arp_table_static_entry') and enter `__true__` in the appropriate row cell.

The pfSense GUI shows entry field for four ntpservers, but only three are allowed.

Either mac or cid is required.

All three types of private IPv4 ranges are supported (where 'x' is the subnet number):
- 192.168.x.y
- 172.x.y.y
- 10.y.y.y - All hosts are in the same subnet 10.

NOTEs on xml syntax variations
- pfsenseDHCP uses the lxml library, which uses the _empty-element tag_ syntax style for tags with no content, whereas pfSense backup outputs the -start-tag / end-tag pair_ syntax.  Both are equivalent and pfSense loads the empty-element tag syntax correctly.
- pfSense backup outputs raw text fields, such as `descr`, wrapped in a CDATA structure, whereas pfsenseDHCP uses lxml's feature to automatically escape xml special characters (eg, '>' in the descr text becomes '&gt'), which loads correctly into pfSense.


- \<staticmap> elements are created using the Template.  Using the Template \<staticmap> mechanism allows for higher portability across pfSense versions.
- `mac`, `ipaddr`, and `hostname` elements are required columns and are created in the \<staticmap>
- The `descr` element is handled only within pfSense's GUI system, not passed to Kea.
- Documentation fields in the .csv file have column names that start with `#`, such as `#Notes`.  These columns are ignored by this tool, with the exception of the `#Disable` column, which is used to mark individual rows as inactive.  Inactive/disabled rows are not processed into \<staticmap> blocks in the DHCP backup .xml file.
- Additional elements may be added to the \<staticmap> by creating .csv column names that match the expected .xml element names.  The element is created if the row's cell content is not empty.  No error checking on the validity of the element names or cell content.

- The `custom_key_config` element content is gzip'd and base64 compressed.  Only valid content makes it into the Kea .conf file (viewable via Diagostics > Command Prompt > Execute Shell Command with "cat /usr/local/etc/kea/kea-dhcp4.conf").


Pending:  DHCP V6 support.




This repo is a shell / template/ set of start files for a new tool using the cjnfuncs freamework.

README placeholder text follows

Monitors WAN-side internet access and WAN IP address changes on a home network.  Sends email and/or text notifications for internet outages (after restored) and WAN IP changes.  The tool is highly configurable for which modem and router you may be using.  Configurations for dd-wrt and pfSense routers, and Motorola and Technicolor/Cox gateway modems are included.

Supported on Python3.6+ on Linux and Windows.

**NOTE:**  Due to as-of-yet unsolved problems with Python 3.6 and import_resources, the `--setup-user` and `--setup-site` switches are not working on Py 3.6.  Manually grab the files from the [github](https://github.com/cjnaz/XXXX) `src/deployment_files directory` and place them in the `~\.config\XXXX` directory.  These command line switches work correctly on Python 3.7+.



`wanstatus --service` enters an infinite loop, periodically checking the status of internet access and the WAN IP address.  `wanstatus` interactively checks status.

- Internet access is detected by contacting an external DNS server (faster) such as the Google public DNS server at 8.8.8.8.  Alternately, web addresses may be pinged to detect internet access (slower).
- If there is NO internet access then the outage time is captured and logged, and wanstatus enters a tight loop checking for recovery of internet access.  Once restored, wanstatus sends email and/or text notifications that internet access was lost and now restored, and how long the outage was.
- If there IS access to the internet, then wanstatus reads and logs the modem status page (typically at 192.168.100.1).
- wanstatus then reads the pfSense or dd-wrt router status page for the WAN IP address, and if changed then sends email and/or notification messages of the change.
- Finally, wanstatus periodically checks with an external web page for the reported WAN IP address.  


All parameters are set in the `wanstatus.cfg` config file.  On each loop in service mode the config file is checked for changes, and reloaded as needed.  This allows for on-the-fly configuration changes.

wanstatus may be started manually, or may be configured to start at system boot.  An example systemd unit file is included.  See systemd documentation for how to set it up.

<br/>

---

## Notable changes since prior release
V3.0 - Converted to package format, updated to cjnfuncs 2.0

<br/>

---

## Usage
```
$ wanstatus -h
usage: wanstatus [-h] [--config-file CONFIG_FILE] [--log-file LOG_FILE]
                 [--print-log] [--service] [--setup-user] [--setup-site] [-V]

Check internet access and WAN IP address.  Send notification/email after outage is over and
on WAN IP change.
3.0

optional arguments:
  -h, --help            show this help message and exit
  --config-file CONFIG_FILE, -c CONFIG_FILE
                        Path to the config file (Default <wanstatus.cfg)> in user/site config directory.
  --log-file LOG_FILE, -l LOG_FILE
                        Path to the log file.
  --print-log, -p       Print the tail end of the log file (default last 40 lines).
  --service             Enter endless loop for use as a systemd service.
  --setup-user          Install starter files in user space.
  --setup-site          Install starter files in system-wide space. Run with root prev.
  -V, --version         Return version number and exit.
```

<br/>

---

## Example output
```
$$ wanstatus 
 WARNING:  ========== wanstatus (3.0) ==========
 WARNING:  Config file </home/me/.config/wanstatus/wanstatus.cfg>
    INFO:  Internet access:             Working          (DNS server 72.105.29.22, command run time   11.3 ms)
    INFO:  Modem status:                Locked           (command run time 6550.7 ms)
    INFO:  Router reported WANIP:       27.177.61.124    (command run time 2300.2 ms)
    INFO:  Externally reported WANIP:   27.177.61.124    (command run time  350.1 ms)
```

<br/>

---

## Setup and Usage notes
- Install wanstatus from PyPI (pip install wanstatus).
- Install the initial configuration files (`wanstatus --setup-user` places files at ~/.config/wanstatus).
- Edit/configure `wanstatus.cfg`, `creds_SMTP`, and `creds_wanstatus` as needed.
- Run manually as `wanstatus`, or install the systemd service.
- When running in service mode (continuously looping) the config file may be edited and is reloaded when changed.  This allows for changing settings without having to restart the service.


<br/>

---

## Customization notes

<br/>

---

## Version history
- 0.1 230226 - New
