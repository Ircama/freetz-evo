# User Management

### Create a User

Assume the new user should be named *picard*. User *root* then does the
following:

### Freetz

```
    # Add user
    adduser picard
    # Save to buffer ???
    # Save persistently
    modsave flash
```

### ds-mod

```
    # Add user
    echo "picard:*" >> /tmp/flash/shadow.save
    # Save persistently
    modsave flash
    # Reload all users, create missing home directories
    modpasswd load
    # Assign password (saved persistently automatically)
    modpasswd picard
    # Test
    login picard
```

### Delete a User

Now the reverse case: user *picard* should be removed again. User *root*
does the following:

### Freetz

```
    # Delete user
    deluser picard
    # Save persistently
    modsave flash
```

### ds-mod

```
    # Delete home directory
    rm -rf /mod/home/picard
    # Create temporary file without the deleted user
    grep -v '^picard:' /tmp/flash/shadow.save > /tmp/deleted-user
    # Overwrite user file
    mv /tmp/deleted-user /tmp/flash/shadow.save
    # Save persistently
    modsave flash
    # Reload all users (now one fewer)
    modpasswd load
    # Test (fails with "Login incorrect" when entering the password)
    login picard
```

### Manual Adjustments

To adjust the UID, for example, first create the user successfully as
described above, then proceed as follows:

-   Edit `/tmp/passwd`
-   modsave flash
-   modsave

### Special Cases

### Dropbear

In Freetz, Dropbear accepts only logins by user `root` by default. To
allow logins by other users, disable the option "allow login only for
root" in the Freetz web interface. Unlike older versions, removing the
patch `make/dropbear/patches/100-root-login-only.patch` is no longer
necessary.


