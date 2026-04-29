# UI Modules and ctlmgr_ctl

`ctlmgr_ctl` can display and edit internal AVM variables, which are
usually stored in text files under `/var/flash/`. Some of these variables
are not visible in the web interface, are no longer visible there, or are
visible only with a different branding. This is not a public documented
interface and can behave rather idiosyncratically. Some values cannot be
changed, while others accept only certain value ranges. Some trigger an
event and then return to their old value. There may also be values that
are better left unchanged. Always create a configuration backup before
experimenting.


### Module

Modules are categories such as `wlan`, `env`, or `tr069`; they often
represent individual configuration files.
<br>To display all modules on the device:
```
$ ctlmgr_ctl u | sed '1,2d'

rights
uimodlogic
boxusers
...
avmcounter
rrd
move
```

### Keys

Keys are the variables of a module. They begin with `settings/`; some
alternatively begin with `status/`.
<br>To display all keys of a module:
```
$ ctlmgr_ctl u  tr064

tr064:settings/
enabled=0
username=dslf-config
password=***
only_https=0
check_sid=error
doupdate_require_auth=1
```

### All Variables

Lists all modules with all keys and their configured values. This command
takes about one minute and also saves the output in `uimods.txt`.

```
for x in $(ctlmgr_ctl u | sed '1,2d'); do echo; ctlmgr_ctl u $x; done | tee uimods.txt
```


### Read a Variable

```
$ ctlmgr_ctl r  tr064 settings/username

dslf-config
```

or

```
$ ctlmgr_ctl r -v  tr064 settings/username

tr064:settings/username = dslf-config
```

### Write a Variable

```
$ ctlmgr_ctl w  tr064 settings/username dslf-config

dslf-config
```

oder

```
$ ctlmgr_ctl w -v  tr064 settings/username dslf-config

tr064:settings/username = dslf-config
```

### Multiple Variables

Read:
```
$ ctlmgr_ctl r  tr064 settings/enabled  tr064 settings/username

0
dslf-config
```
oder
```
$ ctlmgr_ctl r -v  tr064 settings/enabled  tr064 settings/username

tr064:settings/enabled = 0
tr064:settings/username = dslf-config
```
Write:
```
$ctlmgr_ctl w  tr064 settings/enabled 0  tr064 settings/username dslf-config

0
dslf-config
```
oder
```
$ ctlmgr_ctl w -v  tr064 settings/enabled 0  tr064 settings/username dslf-config

tr064:settings/enabled = 0
tr064:settings/username = dslf-config
```

### Listen

Output the number of elements in a list:
```
$ ctlmgr_ctl r boxusers settings/user/count

2
```

Display all elements of a list:
```
$ ctlmgr_ctl l boxusers settings/user/list

  user0
  user1
```

Read selected variables of all elements:
```
$ ctlmgr_ctl l boxusers "settings/user/list(UID,name,box_admin_rights)"

  user0   boxuser11       fritz   3
  user1   boxuser10       horst   0
```

Read one variable of one element:
```
$ ctlmgr_ctl r boxusers settings/user0/UID

boxuser11
```

Display the next free element:
```
$ ctlmgr_ctl r boxusers settings/user/newid

user2
```

Create a new element:
```
$ ctlmgr_ctl w  boxusers settings/user2/enabled 0  boxusers settings/user2/name horst  boxusers settings/user2/box_admin_rights 3  boxusers settings/user2/password aciouasvdtn

0
horst
3
****
```

Delete an element:
```
$ ctlmgr_ctl del  boxusers boxusers:command/user2


```

### Links
 - [Losing Freetz due to an automatic update](https://github.com/Freetz-NG/freetz-ng/discussions/871#discussioncomment-7372142)

