# Remove support-files
Removes the support files, which can be generated and saved via the URL http://fritz.box/html/support.html or http://fritz.box/support.lua.<br>
<br>

With this patch, in addition to the code for generating the support files, the corresponding page in the AVM web GUI is also removed.
If you call the above link after removing the support files, a message appears that the URL was not found:

```
FRITZ!Box:
The requested URL was not found.
You will be redirected to the start page of the FRITZ!Box.
If you are not automatically redirected to the start page of the FRITZ!Box, click here.
```

... and you will be redirected back to the start page of the AVM web GUI.
