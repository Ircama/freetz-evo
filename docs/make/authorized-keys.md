# authorized_keys: Frontend for SSH keys
  - Package: [master/make/pkgs/authorized-keys/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/authorized-keys/)
  - Steward: -

The authorized_keys package can be used to edit the files required for
SSH. It can be found in the web interface under "SSH".

-   authorized_keys - contains public keys for authentication
-   known_hosts - public keys for checking known servers
-   id_dsa - private keys in DSA format
-   id_rsa - private keys in RSA format

Explanation of the private keys: the user keys ~/.ssh/id_dsa and
~/.ssh/id_rsa are not required. If they are present, the client can use
them to authenticate itself to the server. This is an alternative to
entering a password when logging in. These two files have nothing to do
with the host keys. Host keys are required by the SSH server and are
created automatically if they do not already exist. They allow the server
to authenticate itself to the client.

