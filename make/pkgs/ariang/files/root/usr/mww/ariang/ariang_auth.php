<?php
/**
 * Freetz EVO SSO gateway for AriaNg.
 *
 * Called exclusively by the JS SSO preflight injected into /ariang/index.html:
 *   GET /ariang/ariang_auth.php?auth_ping=1
 *
 * Validates the Freetz webcfg session cookie and returns:
 *   - Session valid            → 200 OK  + JSON {"success":true,"authenticated":true}
 *   - Session invalid (SSO on) → 403     + JSON {"error":"...","auth_required":true,"login_url":"..."}
 *   - SSO not enabled          → 200 OK  (webcfg_auth.php absent or new-login disabled)
 *
 * The JS on the AriaNg page handles the 403 response by saving the current URL
 * hash to localStorage and redirecting to the login page.  After a successful
 * login the aria2 CGI redirects back to /ariang/ where the hash is restored.
 */

header('Cache-Control: no-store, no-cache, must-revalidate');
header('Pragma: no-cache');

$_webcfgAuth = '';
if (is_readable('/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/usr/lib/php/webcfg_auth.php';
} elseif (is_readable('/mod/external/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/mod/external/usr/lib/php/webcfg_auth.php';
}

if ($_webcfgAuth !== '') {
    require_once $_webcfgAuth;
    // Always use JSON mode: the caller is a JS XHR, not a browser navigation.
    // webcfg_require_auth() will either return true (session OK) or send a 403
    // JSON body and exit (session missing / SSO enabled).
    webcfg_require_auth(array(
        'mode'      => 'json',
        'subpage'   => 'ariang/',
        'login_url' => '/cgi-bin/conf/aria2?subpage=ariang/',
    ));
    // If we reach here the session is valid.
}

// SSO not enabled, or session is valid: confirm to caller.
header('Content-Type: application/json; charset=UTF-8');
echo json_encode(array('success' => true, 'authenticated' => true));
