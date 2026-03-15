<?php
// ruTorrent auth gate for direct /rutorrent/ access.
$_webcfgAuth = '';
if (is_readable('/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/usr/lib/php/webcfg_auth.php';
} elseif (is_readable('/mod/external/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/mod/external/usr/lib/php/webcfg_auth.php';
}

if ($_webcfgAuth !== '') {
    require_once $_webcfgAuth;
    webcfg_require_auth(array(
        'mode' => 'redirect',
        'subpage' => 'rutorrent/',
        'login_url' => '/cgi-bin/conf/rtorrent?subpage=rutorrent/'
    ));
}

readfile(__DIR__ . '/index.html');
