<?php
/**
 * elFinder Plugin – MediaInfo
 *
 * Adds media technical details (codec, bitrate, resolution, duration, etc.)
 * to the elFinder info panel by running the 'mediainfo' command-line binary.
 *
 * Registration (in connector.php):
 *   $opts['bind']['info']              = array('Plugin.MediaInfo.onInfo');
 *   $opts['plugin']['MediaInfo']       = array(
 *       'enable'       => true,
 *       'mediaInfoCmd' => '/usr/bin/mediainfo',
 *   );
 *
 * The 'onInfo' handler fires after the elFinder 'info' command completes and
 * appends a 'mediainfo' key to each non-directory file stat in $result['files'].
 * The JavaScript client (elFinder) displays unknown keys in the info panel.
 */
class elFinderPluginMediaInfo extends elFinderPlugin
{
    /**
     * Default options (merged with user-supplied opts in constructor).
     *
     * @var array
     */
    protected $opts = array(
        'enable'       => false,
        'mediaInfoCmd' => null,
    );

    /**
     * Constructor – merge user opts over defaults.
     *
     * @param array $opts
     */
    public function __construct($opts)
    {
        $this->opts = array_merge($this->opts, (array)$opts);
    }

    /**
     * Post-command handler for the 'info' command.
     *
     * Called by elFinder after info() returns its result. Iterates every file
     * in $result['files'], resolves the real filesystem path via $dstVolume,
     * and runs 'mediainfo <path>' for every non-directory file. The output text is
     * stored as $file['mediainfo'] so elFinder displays it in the info panel.
     *
     * @param string        $cmd       Command name ('info')
     * @param array         $result    Command result (by reference)
     * @param array         $args      Command arguments
     * @param elFinder      $elfinder  elFinder instance
     * @param object|false  $dstVolume Volume of the first requested target
     *
     * @return bool  false = no client sync needed
     */
    public function onInfo($cmd, &$result, $args, $elfinder, $dstVolume)
    {
        if (!$this->iaEnabled($this->opts)) {
            return false;
        }

        $mediaInfoCmd = isset($this->opts['mediaInfoCmd']) ? (string)$this->opts['mediaInfoCmd'] : '';
        if ($mediaInfoCmd === '' || !is_executable($mediaInfoCmd)) {
            return false;
        }

        if (empty($result['files']) || !is_array($result['files'])) {
            return false;
        }

        foreach ($result['files'] as &$file) {
            if (empty($file['hash'])) {
                continue;
            }

            // Skip directories
            if (!empty($file['mime']) && $file['mime'] === 'directory') {
                continue;
            }

            // Resolve the real filesystem path via the public elFinder::realpath()
            // API.  elFinder::volume() is protected and cannot be called from a
            // plugin; realpath() is public and handles multi-volume lookups the
            // same way (each hash is resolved against its own volume).
            $realpath = $elfinder->realpath($file['hash']);
            if (!$realpath || !is_file($realpath)) {
                continue;
            }

            // Run mediainfo (each arg individually escaped)
            $output = shell_exec(
                escapeshellarg($mediaInfoCmd) . ' ' . escapeshellarg($realpath) . ' 2>/dev/null'
            );

            if ($output !== null && trim((string)$output) !== '') {
                $file['mediainfo'] = trim((string)$output);
            }
        }

        return false;
    }
}
