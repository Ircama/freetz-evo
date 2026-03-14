<?php
/**
 * elFinder Plugin - MovieInfo
 *
 * Enriches info() results with movie metadata resolved from the filename,
 * querying TMDb and/or OMDb. Designed for low-resource systems:
 * - lightweight filename parser (no external runtime dependency)
 * - response cache in /tmp
 * - short HTTP timeouts
 */
class elFinderPluginMovieInfo extends elFinderPlugin
{
    protected $lookupDebug = array();
    protected $lastHttpError = '';

    protected $opts = array(
        'enable'      => false,
        'provider'    => 'auto', // auto | tmdb | omdb | wikipedia | imdb
        'tmdbApiKey'  => '',
        'omdbApiKey'  => '',
        'language'    => 'en',
        'cacheFile'   => '/tmp/elfinder-movieinfo-cache.json',
        'cacheTtl'    => 43200,
        'cacheVersion'=> 'w3',
        'httpTimeout' => 4,
    );

    public function __construct($opts)
    {
        $this->opts = array_merge($this->opts, (array)$opts);
    }

    public function onInfo($cmd, &$result, $args, $elfinder, $dstVolume)
    {
        if (!$this->iaEnabled($this->opts)) {
            return false;
        }
        if (empty($result['files']) || !is_array($result['files'])) {
            return false;
        }

        $cache = $this->cacheLoad();

        foreach ($result['files'] as &$file) {
            if (empty($file['hash'])) {
                continue;
            }
            if (!empty($file['mime']) && $file['mime'] === 'directory') {
                continue;
            }

            $realpath = $elfinder->realpath($file['hash']);
            if (!$realpath || !is_file($realpath)) {
                continue;
            }
            if (!$this->isLikelyVideo($realpath)) {
                continue;
            }

            $guess = $this->guessFromFilename($realpath);
            if (!$guess || empty($guess['title'])) {
                continue;
            }

            $cacheKey = sha1(strtolower(
                (string)$this->opts['cacheVersion'] . '|' .
                $guess['title'] . '|' . (string)$guess['year'] . '|' .
                $this->opts['provider'] . '|' . (string)$this->opts['language']
            ));
            $entry = $this->cacheGet($cache, $cacheKey);
            if ($entry === null) {
                $entry = $this->lookupMovie($guess);
                if ($entry) {
                    $cache[$cacheKey] = array(
                        'ts'   => time(),
                        'data' => $entry,
                    );
                }
            }

            if (!$entry) {
                $file['movieinfo_html'] = $this->renderNotFound($guess, basename($realpath));
                continue;
            }

            $file['movieinfo_html'] = $this->renderHtml($entry, $guess, basename($realpath));
        }

        $this->cacheSave($cache);
        return false;
    }

    protected function isLikelyVideo($path)
    {
        $ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
        return in_array($ext, array(
            'mkv', 'mp4', 'avi', 'mov', 'wmv', 'm4v', 'webm', 'mpg', 'mpeg', 'ts', 'm2ts', 'flv'
        ), true);
    }

    protected function guessFromFilename($path)
    {
        $name = pathinfo($path, PATHINFO_FILENAME);
        $rawName = $name;

        // Extract year early (also works for "(2025)").
        $year = '';
        if (preg_match('/\b(19\d{2}|20\d{2})\b/', $rawName, $m)) {
            $year = $m[1];
        }

        // Remove bracketed tags/groups first
        $name = preg_replace('/\[[^\]]*\]/', ' ', $name);
        $name = preg_replace('/\([^\)]*\)/', ' ', $name);

        // Normalize separators to spaces
        $name = str_replace(array('.', '_', '-'), ' ', $name);

        // Drop obvious release tags and language/audio markers.
        $name = preg_replace('/\b(480p|576p|720p|1080p|2160p|4k|hdr|x264|x265|h264|h265|hevc|av1|dvdrip|brrip|bluray|webrip|web\s?dl|proper|repack|extended|remastered|multi|dubbed|subbed|aac|ddp|dts|ac3|atmos|ita|eng|dual|subs?|hdtv|cam|ts|tc|uhd|mkv|mp4)\b/i', ' ', $name);
        $name = preg_replace('/\b\d\.\d\b/', ' ', $name); // e.g. 5.1, 7.1
        $name = preg_replace('/\b([257])\s*[._\-]?\s*1\b/i', ' ', $name); // e.g. 5.1, 5 1, 7-1
        $name = preg_replace('/\s-\s[a-z0-9]{2,8}$/i', ' ', trim($name)); // release group suffix

        // TV episodes are out-of-scope for movie DB popup
        if (preg_match('/\bS\d{1,2}E\d{1,2}\b/i', $name) || preg_match('/\b\d{1,2}x\d{1,2}\b/i', $name)) {
            return null;
        }

        if ($year !== '') {
            // Keep title left side of year when available
            $pos = strpos($name, $year);
            if ($pos !== false && $pos > 2) {
                $name = substr($name, 0, $pos);
            }
        }

        $title = trim(preg_replace('/\s+/', ' ', $name));
        // Strip final scene/release group token if still present (e.g. "FHC").
        $title = preg_replace('/\s+[A-Z0-9]{2,8}$/', '', $title);
        $title = trim(preg_replace('/\s+/', ' ', $title));
        if ($title === '') {
            return null;
        }

        return array('title' => $title, 'year' => $year);
    }

    protected function lookupMovie($guess)
    {
        $this->lookupDebug = array();
        $provider = strtolower((string)$this->opts['provider']);

        if ($provider === 'tmdb') {
            return $this->lookupTmdb($guess);
        }
        if ($provider === 'omdb') {
            return $this->lookupOmdb($guess);
        }
        if ($provider === 'wikipedia') {
            return $this->lookupWikipedia($guess);
        }
        if ($provider === 'imdb') {
            return $this->lookupImdb($guess);
        }

        // auto: TMDb first (richer metadata), then OMDb, then Wikipedia, then keyless IMDb
        $hit = $this->lookupTmdb($guess);
        if ($hit) {
            return $hit;
        }
        $hit = $this->lookupOmdb($guess);
        if ($hit) {
            return $hit;
        }
        $hit = $this->lookupWikipedia($guess);
        if ($hit) {
            return $hit;
        }
        return $this->lookupImdb($guess);
    }

    protected function lookupTmdb($guess)
    {
        $key = trim((string)$this->opts['tmdbApiKey']);
        if ($key === '') {
            return null;
        }

        $params = array(
            'api_key'  => $key,
            'query'    => $guess['title'],
            'language' => (string)$this->opts['language'],
        );
        if (!empty($guess['year'])) {
            $params['year'] = $guess['year'];
        }

        $url = 'https://api.themoviedb.org/3/search/movie?' . http_build_query($params);
        $data = $this->httpJson($url);
        if (empty($data['results']) || !is_array($data['results'])) {
            return null;
        }
        $r = $data['results'][0];
        if (empty($r['id'])) {
            return null;
        }

        $details = $this->httpJson(
            'https://api.themoviedb.org/3/movie/' . rawurlencode((string)$r['id'])
            . '?' . http_build_query(array(
                'api_key'  => $key,
                'language' => (string)$this->opts['language'],
                'append_to_response' => 'credits',
            ))
        );

        $genres = array();
        if (!empty($details['genres']) && is_array($details['genres'])) {
            foreach ($details['genres'] as $g) {
                if (!empty($g['name'])) {
                    $genres[] = $g['name'];
                }
            }
        }

        $countries = array();
        if (!empty($details['production_countries']) && is_array($details['production_countries'])) {
            foreach ($details['production_countries'] as $c) {
                if (!empty($c['name'])) {
                    $countries[] = $c['name'];
                }
            }
        }

        $languages = array();
        if (!empty($details['spoken_languages']) && is_array($details['spoken_languages'])) {
            foreach ($details['spoken_languages'] as $l) {
                if (!empty($l['english_name'])) {
                    $languages[] = $l['english_name'];
                } elseif (!empty($l['name'])) {
                    $languages[] = $l['name'];
                }
            }
        }

        $directors = array();
        $writers = array();
        $cast = array();
        if (!empty($details['credits']) && is_array($details['credits'])) {
            if (!empty($details['credits']['crew']) && is_array($details['credits']['crew'])) {
                foreach ($details['credits']['crew'] as $crew) {
                    if (empty($crew['name']) || empty($crew['job'])) {
                        continue;
                    }
                    $job = strtolower((string)$crew['job']);
                    if ($job === 'director') {
                        $directors[] = (string)$crew['name'];
                    } elseif ($job === 'writer' || $job === 'screenplay') {
                        $writers[] = (string)$crew['name'];
                    }
                }
            }
            if (!empty($details['credits']['cast']) && is_array($details['credits']['cast'])) {
                foreach ($details['credits']['cast'] as $i => $actor) {
                    if ($i >= 6) {
                        break;
                    }
                    if (!empty($actor['name'])) {
                        $cast[] = (string)$actor['name'];
                    }
                }
            }
        }

        $budget = '';
        if (!empty($details['budget']) && (int)$details['budget'] > 0) {
            $budget = '$' . number_format((int)$details['budget']);
        }
        $revenue = '';
        if (!empty($details['revenue']) && (int)$details['revenue'] > 0) {
            $revenue = '$' . number_format((int)$details['revenue']);
        }

        return array(
            'source'      => 'TMDb',
            'title'       => isset($details['title']) ? $details['title'] : (isset($r['title']) ? $r['title'] : ''),
            'original'    => isset($details['original_title']) ? $details['original_title'] : (isset($r['original_title']) ? $r['original_title'] : ''),
            'year'        => !empty($r['release_date']) ? substr($r['release_date'], 0, 4) : '',
            'released'    => isset($details['release_date']) ? (string)$details['release_date'] : '',
            'plot'        => isset($details['overview']) ? $details['overview'] : (isset($r['overview']) ? $r['overview'] : ''),
            'rating'      => isset($r['vote_average']) ? (string)$r['vote_average'] : '',
            'votes'       => isset($r['vote_count']) ? (string)$r['vote_count'] : '',
            'runtime'     => isset($details['runtime']) ? (string)$details['runtime'] : '',
            'genres'      => implode(', ', $genres),
            'country'     => implode(', ', $countries),
            'language_name' => implode(', ', $languages),
            'director'    => implode(', ', array_values(array_unique($directors))),
            'writer'      => implode(', ', array_values(array_unique($writers))),
            'actors'      => implode(', ', $cast),
            'tagline'     => isset($details['tagline']) ? (string)$details['tagline'] : '',
            'status'      => isset($details['status']) ? (string)$details['status'] : '',
            'budget'      => $budget,
            'revenue'     => $revenue,
            'homepage'    => isset($details['homepage']) ? (string)$details['homepage'] : '',
            'poster'      => !empty($r['poster_path']) ? ('https://image.tmdb.org/t/p/w342' . $r['poster_path']) : '',
            'tmdb_url'    => 'https://www.themoviedb.org/movie/' . rawurlencode((string)$r['id']),
            'imdb_url'    => !empty($details['imdb_id']) ? ('https://www.imdb.com/title/' . rawurlencode($details['imdb_id'])) : '',
            'wikipedia_url' => '',
        );
    }

    protected function lookupOmdb($guess)
    {
        $key = trim((string)$this->opts['omdbApiKey']);
        if ($key === '') {
            return null;
        }

        $variants = $this->buildImdbQueryVariants((string)$guess['title']);
        $wantYear = !empty($guess['year']) ? (string)$guess['year'] : '';
        $attempted = array();

        foreach ($variants as $titleVariant) {
            // 1) Exact-title lookup with year when available.
            $data = $this->lookupOmdbByTitle($key, $titleVariant, $wantYear);
            if (is_array($data)) {
                return $this->mapOmdbMovie($data);
            }
            $attempted[] = $titleVariant . ($wantYear !== '' ? (' @' . $wantYear) : '');

            // 2) Retry exact-title lookup without year (OMDb can be strict).
            if ($wantYear !== '') {
                $data = $this->lookupOmdbByTitle($key, $titleVariant, '');
                if (is_array($data)) {
                    return $this->mapOmdbMovie($data);
                }
                $attempted[] = $titleVariant . ' @any-year';
            }

            // 3) Search fallback and resolve details by imdbID.
            $hit = $this->lookupOmdbViaSearch($key, $titleVariant, $wantYear);
            if (is_array($hit)) {
                return $this->mapOmdbMovie($hit);
            }
            $attempted[] = 'search:' . $titleVariant;
        }

        $this->lookupDebug = array(
            'stage' => 'omdb',
            'reason' => 'omdb_no_hit',
            'query' => (string)$guess['title'],
            'attempted' => implode(' | ', $attempted),
        );
        return null;
    }

    protected function lookupOmdbByTitle($key, $title, $year)
    {
        $params = array(
            'apikey' => $key,
            't'      => (string)$title,
            'plot'   => 'full',
            'r'      => 'json',
        );
        if ((string)$year !== '') {
            $params['y'] = (string)$year;
        }

        $url = 'https://www.omdbapi.com/?' . http_build_query($params);
        $data = $this->httpJson($url);
        if (empty($data) || (!empty($data['Response']) && strtolower((string)$data['Response']) === 'false')) {
            return null;
        }
        return $data;
    }

    protected function lookupOmdbViaSearch($key, $title, $year)
    {
        $params = array(
            'apikey' => $key,
            's'      => (string)$title,
            'type'   => 'movie',
            'r'      => 'json',
        );
        if ((string)$year !== '') {
            $params['y'] = (string)$year;
        }

        $url = 'https://www.omdbapi.com/?' . http_build_query($params);
        $data = $this->httpJson($url);
        if (empty($data) || (!empty($data['Response']) && strtolower((string)$data['Response']) === 'false') || empty($data['Search']) || !is_array($data['Search'])) {
            if ((string)$year !== '') {
                return $this->lookupOmdbViaSearch($key, $title, '');
            }
            return null;
        }

        $wantTitleNorm = strtolower(trim(preg_replace('/\s+/', ' ', (string)$title)));
        $wantYear = (int)$year;
        $best = null;
        $bestScore = -1;

        foreach ($data['Search'] as $row) {
            if (!is_array($row) || empty($row['imdbID'])) {
                continue;
            }
            $rowTitle = isset($row['Title']) ? (string)$row['Title'] : '';
            $rowTitleNorm = strtolower(trim(preg_replace('/\s+/', ' ', $rowTitle)));
            $rowYear = isset($row['Year']) ? (int)substr((string)$row['Year'], 0, 4) : 0;

            $score = 0;
            if ($rowTitleNorm === $wantTitleNorm) {
                $score += 25;
            }
            if ($wantTitleNorm !== '' && strpos($rowTitleNorm, $wantTitleNorm) !== false) {
                $score += 10;
            }
            if ($wantYear > 0 && $rowYear > 0) {
                if ($rowYear === $wantYear) {
                    $score += 30;
                } elseif (abs($rowYear - $wantYear) <= 1) {
                    $score += 8;
                }
            }

            if ($score > $bestScore) {
                $best = $row;
                $bestScore = $score;
            }
        }

        if (!is_array($best) || empty($best['imdbID'])) {
            return null;
        }

        $urlDetail = 'https://www.omdbapi.com/?' . http_build_query(array(
            'apikey' => $key,
            'i'      => (string)$best['imdbID'],
            'plot'   => 'full',
            'r'      => 'json',
        ));
        $detail = $this->httpJson($urlDetail);
        if (empty($detail) || (!empty($detail['Response']) && strtolower((string)$detail['Response']) === 'false')) {
            return null;
        }
        return $detail;
    }

    protected function mapOmdbMovie($data)
    {
        $imdbId = isset($data['imdbID']) ? (string)$data['imdbID'] : '';
        return array(
            'source'      => 'OMDb',
            'title'       => isset($data['Title']) ? $data['Title'] : '',
            'original'    => '',
            'year'        => isset($data['Year']) ? $data['Year'] : '',
            'released'    => isset($data['Released']) && (string)$data['Released'] !== 'N/A' ? $data['Released'] : '',
            'plot'        => isset($data['Plot']) ? $data['Plot'] : '',
            'rating'      => isset($data['imdbRating']) ? $data['imdbRating'] : '',
            'votes'       => isset($data['imdbVotes']) ? $data['imdbVotes'] : '',
            'runtime'     => isset($data['Runtime']) ? $data['Runtime'] : '',
            'genres'      => isset($data['Genre']) ? $data['Genre'] : '',
            'director'    => isset($data['Director']) && (string)$data['Director'] !== 'N/A' ? $data['Director'] : '',
            'writer'      => isset($data['Writer']) && (string)$data['Writer'] !== 'N/A' ? $data['Writer'] : '',
            'actors'      => isset($data['Actors']) && (string)$data['Actors'] !== 'N/A' ? $data['Actors'] : '',
            'country'     => isset($data['Country']) && (string)$data['Country'] !== 'N/A' ? $data['Country'] : '',
            'language_name' => isset($data['Language']) && (string)$data['Language'] !== 'N/A' ? $data['Language'] : '',
            'awards'      => isset($data['Awards']) && (string)$data['Awards'] !== 'N/A' ? $data['Awards'] : '',
            'boxoffice'   => isset($data['BoxOffice']) && (string)$data['BoxOffice'] !== 'N/A' ? $data['BoxOffice'] : '',
            'production'  => isset($data['Production']) && (string)$data['Production'] !== 'N/A' ? $data['Production'] : '',
            'homepage'    => isset($data['Website']) && (string)$data['Website'] !== 'N/A' ? $data['Website'] : '',
            'poster'      => (isset($data['Poster']) && $data['Poster'] !== 'N/A') ? $data['Poster'] : '',
            'tmdb_url'    => '',
            'imdb_url'    => $imdbId !== '' ? ('https://www.imdb.com/title/' . rawurlencode($imdbId)) : '',
            'wikipedia_url' => '',
        );
    }

    protected function lookupWikipedia($guess)
    {
        $query = trim((string)$guess['title']);
        if ($query === '') {
            $this->lookupDebug = array('stage' => 'wikipedia', 'reason' => 'empty_query');
            return null;
        }

        $lang = strtolower(trim((string)$this->opts['language']));
        if (!preg_match('/^[a-z][a-z0-9-]{1,7}$/', $lang)) {
            $lang = 'en';
        }

        $wantYear = !empty($guess['year']) ? (int)$guess['year'] : 0;
        $searchVariants = array($query);
        if ($wantYear > 0) {
            $searchVariants[] = $query . ' (' . $wantYear . ' film)';
            $searchVariants[] = $query . ' ' . $wantYear . ' film';
            $searchVariants[] = $query . ' ' . $wantYear;
        }

        $rows = array();
        $seen = array();
        foreach ($searchVariants as $variant) {
            $url = 'https://' . $lang . '.wikipedia.org/w/api.php?' . http_build_query(array(
                'action'      => 'query',
                'list'        => 'search',
                'srsearch'    => 'intitle:' . $variant,
                'format'      => 'json',
                'utf8'        => '1',
                'srlimit'     => 10,
                'srnamespace' => 0,
            ));
            $data = $this->httpJson($url);
            if (empty($data['query']['search']) || !is_array($data['query']['search'])) {
                continue;
            }
            foreach ($data['query']['search'] as $row) {
                $pid = isset($row['pageid']) ? (int)$row['pageid'] : 0;
                if ($pid <= 0 || isset($seen[$pid])) {
                    continue;
                }
                $rows[] = $row;
                $seen[$pid] = 1;
            }
            if (!empty($rows)) {
                break;
            }
        }

        if (empty($rows)) {
            $this->lookupDebug = array(
                'stage'  => 'wikipedia',
                'reason' => 'wikipedia_no_hit',
                'query'  => $query,
            );
            return null;
        }

        $best = null;
        $bestScore = -1;
        $wantTitleNorm = strtolower(trim(preg_replace('/\s+/', ' ', $query)));

        foreach ($rows as $row) {
            $title = isset($row['title']) ? (string)$row['title'] : '';
            if ($title === '') {
                continue;
            }
            $titleNorm = strtolower(trim(preg_replace('/\s+/', ' ', preg_replace('/\s*\([^\)]*\)\s*/', ' ', $title))));
            $snippet = isset($row['snippet']) ? strip_tags((string)$row['snippet']) : '';
            $score = 0;
            if ($titleNorm === $wantTitleNorm) {
                $score += 30;
            }
            if ($wantTitleNorm !== '' && strpos($titleNorm, $wantTitleNorm) !== false) {
                $score += 14;
            }
            if ($wantYear > 0) {
                $titleYear = $this->extractYearFromText($title);
                if ($titleYear > 0) {
                    if ($titleYear === $wantYear) {
                        $score += 30;
                    } elseif (abs($titleYear - $wantYear) <= 1) {
                        $score += 10;
                    }
                }
                if ($snippet !== '' && strpos($snippet, (string)$wantYear) !== false) {
                    $score += 8;
                }
            }
            if (stripos($title, 'film') !== false) {
                $score += 6;
            }

            if ($score > $bestScore) {
                $best = $row;
                $bestScore = $score;
            }
        }

        if (!is_array($best) || empty($best['title'])) {
            $this->lookupDebug = array(
                'stage'  => 'wikipedia',
                'reason' => 'wikipedia_no_scored_candidate',
                'query'  => $query,
            );
            return null;
        }

        $pageTitle = (string)$best['title'];
        $pageId = isset($best['pageid']) ? (int)$best['pageid'] : 0;
        $wikiUrl = 'https://' . $lang . '.wikipedia.org/wiki/' . rawurlencode(str_replace(' ', '_', $pageTitle));

        $summaryUrl = 'https://' . $lang . '.wikipedia.org/api/rest_v1/page/summary/' . rawurlencode($pageTitle);
        $summary = $this->httpJson($summaryUrl);

        $title = $pageTitle;
        $plot = isset($best['snippet']) ? strip_tags((string)$best['snippet']) : '';
        $poster = '';
        $year = $wantYear > 0 ? (string)$wantYear : '';
        $wikidataId = '';
        if (is_array($summary)) {
            if (!empty($summary['title'])) {
                $title = (string)$summary['title'];
            }
            if (!empty($summary['extract'])) {
                $plot = (string)$summary['extract'];
            }
            if (!empty($summary['thumbnail']) && is_array($summary['thumbnail']) && !empty($summary['thumbnail']['source'])) {
                $poster = (string)$summary['thumbnail']['source'];
            }
            if (empty($summary['content_urls']['desktop']['page']) && !empty($summary['content_urls']['mobile']['page'])) {
                $wikiUrl = (string)$summary['content_urls']['mobile']['page'];
            } elseif (!empty($summary['content_urls']['desktop']['page'])) {
                $wikiUrl = (string)$summary['content_urls']['desktop']['page'];
            }
            if ($year === '') {
                $yearGuess = 0;
                if (!empty($summary['description'])) {
                    $yearGuess = $this->extractYearFromText((string)$summary['description']);
                }
                if ($yearGuess <= 0) {
                    $yearGuess = $this->extractYearFromText($title);
                }
                if ($yearGuess > 0) {
                    $year = (string)$yearGuess;
                }
            }
        }

        if ($plot === '' && $pageId > 0) {
            $detail = $this->httpJson('https://' . $lang . '.wikipedia.org/w/api.php?' . http_build_query(array(
                'action'      => 'query',
                'prop'        => 'extracts|pageimages|info|pageprops',
                'explaintext' => 1,
                'exintro'     => 1,
                'inprop'      => 'url',
                'pithumbsize' => 500,
                'pageids'     => (string)$pageId,
                'format'      => 'json',
            )));
            if (!empty($detail['query']['pages']) && is_array($detail['query']['pages']) && !empty($detail['query']['pages'][$pageId])) {
                $page = $detail['query']['pages'][$pageId];
                if ($plot === '' && !empty($page['extract'])) {
                    $plot = (string)$page['extract'];
                }
                if ($poster === '' && !empty($page['thumbnail']) && is_array($page['thumbnail']) && !empty($page['thumbnail']['source'])) {
                    $poster = (string)$page['thumbnail']['source'];
                }
                if (!empty($page['canonicalurl'])) {
                    $wikiUrl = (string)$page['canonicalurl'];
                }
                if (!empty($page['pageprops']) && is_array($page['pageprops']) && !empty($page['pageprops']['wikibase_item'])) {
                    $wikidataId = (string)$page['pageprops']['wikibase_item'];
                }
            }
        }

        if ($wikidataId === '' && $pageId > 0) {
            $props = $this->httpJson('https://' . $lang . '.wikipedia.org/w/api.php?' . http_build_query(array(
                'action' => 'query',
                'prop'   => 'pageprops',
                'pageids' => (string)$pageId,
                'format' => 'json',
            )));
            if (!empty($props['query']['pages']) && !empty($props['query']['pages'][$pageId]['pageprops']['wikibase_item'])) {
                $wikidataId = (string)$props['query']['pages'][$pageId]['pageprops']['wikibase_item'];
            }
        }

        $wikiMeta = array();
        if ($wikidataId !== '') {
            $wikiMeta = $this->lookupWikipediaWikidata($wikidataId, $lang);
            if ($year === '' && !empty($wikiMeta['year'])) {
                $year = (string)$wikiMeta['year'];
            }
        }

        // Fallback: parse classic Wikipedia infobox from page wikitext.
        // Useful when Wikidata claims are sparse or unavailable.
        $infoboxMeta = $this->lookupWikipediaInfobox($pageTitle, $lang);
        if (!empty($infoboxMeta)) {
            $wikiMeta = $this->mergeMovieMeta($wikiMeta, $infoboxMeta);
            if ($year === '' && !empty($infoboxMeta['year'])) {
                $year = (string)$infoboxMeta['year'];
            }
        }

        if ($plot === '') {
            $this->lookupDebug = array(
                'stage'  => 'wikipedia',
                'reason' => 'wikipedia_empty_extract',
                'query'  => $query,
            );
        }

        return array(
            'source'      => 'Wikipedia',
            'title'       => $title,
            'original'    => '',
            'year'        => $year,
            'released'    => !empty($wikiMeta['released']) ? (string)$wikiMeta['released'] : '',
            'plot'        => trim($plot),
            'rating'      => '',
            'votes'       => '',
            'runtime'     => !empty($wikiMeta['runtime']) ? (string)$wikiMeta['runtime'] : '',
            'genres'      => !empty($wikiMeta['genres']) ? (string)$wikiMeta['genres'] : '',
            'director'    => !empty($wikiMeta['director']) ? (string)$wikiMeta['director'] : '',
            'writer'      => !empty($wikiMeta['writer']) ? (string)$wikiMeta['writer'] : '',
            'actors'      => !empty($wikiMeta['actors']) ? (string)$wikiMeta['actors'] : '',
            'country'     => !empty($wikiMeta['country']) ? (string)$wikiMeta['country'] : '',
            'language_name' => !empty($wikiMeta['language_name']) ? (string)$wikiMeta['language_name'] : '',
            'awards'      => '',
            'boxoffice'   => !empty($wikiMeta['boxoffice']) ? (string)$wikiMeta['boxoffice'] : '',
            'production'  => !empty($wikiMeta['production']) ? (string)$wikiMeta['production'] : '',
            'status'      => '',
            'tagline'     => '',
            'budget'      => !empty($wikiMeta['budget']) ? (string)$wikiMeta['budget'] : '',
            'revenue'     => '',
            'homepage'    => '',
            'poster'      => $poster,
            'tmdb_url'    => '',
            'imdb_url'    => !empty($wikiMeta['imdb_url']) ? (string)$wikiMeta['imdb_url'] : '',
            'wikipedia_url' => $wikiUrl,
        );
    }

    protected function lookupWikipediaWikidata($qid, $lang)
    {
        if (!preg_match('/^Q\d+$/', (string)$qid)) {
            return array();
        }

        $entityDoc = $this->httpJson('https://www.wikidata.org/wiki/Special:EntityData/' . rawurlencode((string)$qid) . '.json');
        if (empty($entityDoc['entities']) || empty($entityDoc['entities'][$qid])) {
            return array();
        }

        $entity = $entityDoc['entities'][$qid];
        $claims = !empty($entity['claims']) && is_array($entity['claims']) ? $entity['claims'] : array();
        if (empty($claims)) {
            return array();
        }

        $directorIds = $this->wikidataEntityIds($claims, 'P57', 4);
        $writerIds = $this->wikidataEntityIds($claims, 'P58', 4);
        $actorIds = $this->wikidataEntityIds($claims, 'P161', 10);
        $genreIds = $this->wikidataEntityIds($claims, 'P136', 6);
        $countryIds = $this->wikidataEntityIds($claims, 'P495', 4);
        $langIds = $this->wikidataEntityIds($claims, 'P364', 4);
        $productionIds = $this->wikidataEntityIds($claims, 'P272', 4);

        $labelIds = array_merge($directorIds, $writerIds, $actorIds, $genreIds, $countryIds, $langIds, $productionIds);
        $labels = $this->wikidataLabels($labelIds, $lang);

        $runtime = $this->wikidataRuntime($claims);
        $released = $this->wikidataTimeClaim($claims, 'P577');
        $budget = $this->wikidataMoneyClaim($claims, 'P2130');
        $boxoffice = $this->wikidataMoneyClaim($claims, 'P2142');

        $imdbId = $this->wikidataStringClaim($claims, 'P345');
        $imdbUrl = '';
        if ($imdbId !== '') {
            $imdbUrl = 'https://www.imdb.com/title/' . rawurlencode($imdbId);
        }

        return array(
            'director'      => implode(', ', $this->wikidataIdListToLabels($directorIds, $labels)),
            'writer'        => implode(', ', $this->wikidataIdListToLabels($writerIds, $labels)),
            'actors'        => implode(', ', $this->wikidataIdListToLabels($actorIds, $labels)),
            'genres'        => implode(', ', $this->wikidataIdListToLabels($genreIds, $labels)),
            'country'       => implode(', ', $this->wikidataIdListToLabels($countryIds, $labels)),
            'language_name' => implode(', ', $this->wikidataIdListToLabels($langIds, $labels)),
            'production'    => implode(', ', $this->wikidataIdListToLabels($productionIds, $labels)),
            'runtime'       => $runtime,
            'released'      => $released,
            'year'          => $this->extractYearFromText($released),
            'budget'        => $budget,
            'boxoffice'     => $boxoffice,
            'imdb_url'      => $imdbUrl,
        );
    }

    protected function mergeMovieMeta($base, $fallback)
    {
        $base = is_array($base) ? $base : array();
        $fallback = is_array($fallback) ? $fallback : array();
        foreach ($fallback as $k => $v) {
            if (!isset($base[$k]) || (string)$base[$k] === '') {
                $base[$k] = $v;
            }
        }
        return $base;
    }

    protected function lookupWikipediaInfobox($pageTitle, $lang)
    {
        $data = $this->httpJson('https://' . $lang . '.wikipedia.org/w/api.php?' . http_build_query(array(
            'action'    => 'parse',
            'page'      => (string)$pageTitle,
            'prop'      => 'wikitext',
            'format'    => 'json',
            'redirects' => '1',
        )));
        if (empty($data['parse']['wikitext']) || !is_array($data['parse']['wikitext']) || !isset($data['parse']['wikitext']['*'])) {
            return array();
        }

        $wikitext = (string)$data['parse']['wikitext']['*'];
        $ibox = $this->extractInfoboxBlock($wikitext);
        if ($ibox === '') {
            return array();
        }

        $fields = $this->parseInfoboxFields($ibox);
        if (empty($fields)) {
            return array();
        }

        $released = $this->cleanupWikiText($this->pickInfoboxField($fields, array('released', 'release_date', 'release dates', 'release date')));
        $runtime = $this->cleanupWikiText($this->pickInfoboxField($fields, array('runtime', 'running_time')));
        $director = $this->cleanupWikiText($this->pickInfoboxField($fields, array('director', 'directors')));
        $writer = $this->cleanupWikiText($this->pickInfoboxField($fields, array('writer', 'writers', 'screenplay', 'story')));
        $actors = $this->cleanupWikiText($this->pickInfoboxField($fields, array('starring', 'cast')));
        $genres = $this->cleanupWikiText($this->pickInfoboxField($fields, array('genre', 'genres')));
        $country = $this->cleanupWikiText($this->pickInfoboxField($fields, array('country', 'countries')));
        $language = $this->cleanupWikiText($this->pickInfoboxField($fields, array('language', 'languages')));
        $production = $this->cleanupWikiText($this->pickInfoboxField($fields, array('studio', 'production_companies', 'production company', 'distributor')));
        $budget = $this->cleanupWikiText($this->pickInfoboxField($fields, array('budget')));
        $boxoffice = $this->cleanupWikiText($this->pickInfoboxField($fields, array('gross', 'box_office', 'boxoffice')));

        $imdbRaw = $this->pickInfoboxField($fields, array('imdb_id'));
        $imdbId = '';
        if ($imdbRaw !== '' && preg_match('/tt\d{5,10}/', $imdbRaw, $m)) {
            $imdbId = $m[0];
        } elseif (preg_match('/\{\{\s*IMDb\s*title\s*\|\s*(tt\d{5,10})/i', $wikitext, $m)) {
            $imdbId = $m[1];
        }

        if ($runtime !== '' && stripos($runtime, 'min') === false && preg_match('/\b\d{2,3}\b/', $runtime, $m)) {
            $runtime = $m[0] . ' min';
        }

        $year = '';
        if ($released !== '') {
            $yy = $this->extractYearFromText($released);
            if ($yy > 0) {
                $year = (string)$yy;
            }
        }

        $out = array(
            'released'      => $released,
            'runtime'       => $runtime,
            'director'      => $director,
            'writer'        => $writer,
            'actors'        => $actors,
            'genres'        => $genres,
            'country'       => $country,
            'language_name' => $language,
            'production'    => $production,
            'budget'        => $budget,
            'boxoffice'     => $boxoffice,
            'year'          => $year,
            'imdb_url'      => $imdbId !== '' ? ('https://www.imdb.com/title/' . rawurlencode($imdbId)) : '',
        );

        // Remove empty values so mergeMovieMeta can be straightforward.
        foreach ($out as $k => $v) {
            if ((string)$v === '') {
                unset($out[$k]);
            }
        }
        return $out;
    }

    protected function extractInfoboxBlock($wikitext)
    {
        if (!is_string($wikitext) || $wikitext === '') {
            return '';
        }

        if (!preg_match('/\{\{\s*Infobox\s+[Ff]ilm\b/', $wikitext, $m, PREG_OFFSET_CAPTURE)) {
            if (!preg_match('/\{\{\s*Infobox\b/', $wikitext, $m, PREG_OFFSET_CAPTURE)) {
                return '';
            }
        }

        $start = (int)$m[0][1];
        $len = strlen($wikitext);
        $depth = 0;
        for ($i = $start; $i < $len - 1; $i++) {
            $pair = $wikitext[$i] . $wikitext[$i + 1];
            if ($pair === '{{') {
                $depth++;
                $i++;
                continue;
            }
            if ($pair === '}}') {
                $depth--;
                $i++;
                if ($depth <= 0) {
                    return substr($wikitext, $start, $i - $start + 1);
                }
            }
        }
        return '';
    }

    protected function parseInfoboxFields($ibox)
    {
        $fields = array();
        if (!is_string($ibox) || $ibox === '') {
            return $fields;
        }

        $lines = preg_split('/\r?\n/', $ibox);
        $currentKey = '';
        foreach ($lines as $line) {
            if (preg_match('/^\|\s*([^=\|]+?)\s*=\s*(.*)$/', $line, $m)) {
                $currentKey = strtolower(trim((string)$m[1]));
                $fields[$currentKey] = trim((string)$m[2]);
                continue;
            }
            if ($currentKey !== '' && isset($fields[$currentKey])) {
                $t = trim((string)$line);
                if ($t !== '' && strpos($t, '|') !== 0) {
                    $fields[$currentKey] .= ' ' . $t;
                }
            }
        }
        return $fields;
    }

    protected function pickInfoboxField($fields, $keys)
    {
        if (!is_array($fields) || !is_array($keys)) {
            return '';
        }
        foreach ($keys as $k) {
            $kk = strtolower(trim((string)$k));
            if (isset($fields[$kk]) && trim((string)$fields[$kk]) !== '') {
                return (string)$fields[$kk];
            }
        }
        return '';
    }

    protected function cleanupWikiText($text)
    {
        if (!is_string($text) || $text === '') {
            return '';
        }

        $t = $text;
        $t = preg_replace('/<ref[^>]*>.*?<\/ref>/is', ' ', $t);
        $t = preg_replace('/<[^>]+>/', ' ', $t);
        $t = preg_replace('/\{\{\s*nowrap\s*\|([^\}]*)\}\}/i', '$1', $t);
        $t = preg_replace('/\{\{\s*plainlist\s*\|([^\}]*)\}\}/i', '$1', $t);
        $t = preg_replace('/\{\{\s*ubl\s*\|([^\}]*)\}\}/i', '$1', $t);
        $t = preg_replace('/\{\{\s*hlist\s*\|([^\}]*)\}\}/i', '$1', $t);
        $t = preg_replace('/\{\{\s*start date(?: and age)?\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})[^\}]*\}\}/i', '$1-$2-$3', $t);
        $t = preg_replace('/\{\{\s*start date\s*\|\s*(\d{4})\s*\|\s*(\d{1,2})[^\}]*\}\}/i', '$1-$2', $t);
        $t = preg_replace('/\{\{\s*start date\s*\|\s*(\d{4})[^\}]*\}\}/i', '$1', $t);
        $t = preg_replace('/\{\{\s*[^\}\|]+\s*\|\s*([^\}]*)\}\}/', '$1', $t);

        // [[Page|Label]] -> Label, [[Page]] -> Page
        $t = preg_replace('/\[\[[^\]|]+\|([^\]]+)\]\]/', '$1', $t);
        $t = preg_replace('/\[\[([^\]]+)\]\]/', '$1', $t);

        // External links: [url label] -> label
        $t = preg_replace('/\[https?:[^\s\]]+\s+([^\]]+)\]/i', '$1', $t);
        $t = preg_replace('/\[https?:[^\]]+\]/i', ' ', $t);

        $t = str_replace(array('&nbsp;', '&amp;'), array(' ', '&'), $t);
        $t = preg_replace('/\s*<br\s*\/?>\s*/i', ', ', $t);
        $t = str_replace(array('<br>', '<br/>', '<br />', '{{!}}', '•', '·'), array(', ', ', ', ', ', '|', ', ', ', '), $t);
        $t = str_replace('|', ', ', $t);
        $t = preg_replace('/\s*,\s*,+/', ', ', $t);
        $t = preg_replace('/\s+/', ' ', $t);
        $t = trim($t, " \t\n\r\0\x0B,;");

        // Avoid giant leftover template fragments.
        if (strpos($t, '{{') !== false || strpos($t, '}}') !== false) {
            $t = preg_replace('/\{\{[^\}]*\}\}/', ' ', $t);
            $t = preg_replace('/\s+/', ' ', $t);
            $t = trim($t, " \t\n\r\0\x0B,;");
        }

        return $t;
    }

    protected function wikidataEntityIds($claims, $property, $maxItems)
    {
        $ids = array();
        if (empty($claims[$property]) || !is_array($claims[$property])) {
            return $ids;
        }
        foreach ($claims[$property] as $statement) {
            if (!empty($statement['rank']) && (string)$statement['rank'] === 'deprecated') {
                continue;
            }
            if (empty($statement['mainsnak']['datavalue']['value']) || !is_array($statement['mainsnak']['datavalue']['value'])) {
                continue;
            }
            $value = $statement['mainsnak']['datavalue']['value'];
            $id = '';
            if (!empty($value['id'])) {
                $id = (string)$value['id'];
            } elseif (!empty($value['numeric-id'])) {
                $id = 'Q' . (int)$value['numeric-id'];
            }
            if ($id === '' || isset($ids[$id])) {
                continue;
            }
            $ids[$id] = 1;
            if ($maxItems > 0 && count($ids) >= $maxItems) {
                break;
            }
        }
        return array_keys($ids);
    }

    protected function wikidataLabels($ids, $lang)
    {
        $out = array();
        $uniq = array_values(array_unique(array_filter($ids)));
        if (empty($uniq)) {
            return $out;
        }

        $chunks = array_chunk($uniq, 40);
        foreach ($chunks as $chunk) {
            $url = 'https://www.wikidata.org/w/api.php?' . http_build_query(array(
                'action'           => 'wbgetentities',
                'ids'              => implode('|', $chunk),
                'props'            => 'labels',
                'languages'        => $lang . '|en',
                'languagefallback' => '1',
                'format'           => 'json',
            ));
            $data = $this->httpJson($url);
            if (empty($data['entities']) || !is_array($data['entities'])) {
                continue;
            }
            foreach ($data['entities'] as $id => $entity) {
                if (!is_array($entity) || empty($entity['labels']) || !is_array($entity['labels'])) {
                    continue;
                }
                if (!empty($entity['labels'][$lang]['value'])) {
                    $out[$id] = (string)$entity['labels'][$lang]['value'];
                } elseif (!empty($entity['labels']['en']['value'])) {
                    $out[$id] = (string)$entity['labels']['en']['value'];
                } else {
                    foreach ($entity['labels'] as $labelData) {
                        if (!empty($labelData['value'])) {
                            $out[$id] = (string)$labelData['value'];
                            break;
                        }
                    }
                }
            }
        }
        return $out;
    }

    protected function wikidataIdListToLabels($ids, $labels)
    {
        $out = array();
        foreach ($ids as $id) {
            if (!empty($labels[$id])) {
                $out[] = (string)$labels[$id];
            }
        }
        return $out;
    }

    protected function wikidataStringClaim($claims, $property)
    {
        if (empty($claims[$property]) || !is_array($claims[$property])) {
            return '';
        }
        foreach ($claims[$property] as $statement) {
            if (!empty($statement['rank']) && (string)$statement['rank'] === 'deprecated') {
                continue;
            }
            if (!empty($statement['mainsnak']['datavalue']['value']) && is_string($statement['mainsnak']['datavalue']['value'])) {
                return trim((string)$statement['mainsnak']['datavalue']['value']);
            }
        }
        return '';
    }

    protected function wikidataTimeClaim($claims, $property)
    {
        if (empty($claims[$property]) || !is_array($claims[$property])) {
            return '';
        }
        foreach ($claims[$property] as $statement) {
            if (!empty($statement['rank']) && (string)$statement['rank'] === 'deprecated') {
                continue;
            }
            if (empty($statement['mainsnak']['datavalue']['value']) || !is_array($statement['mainsnak']['datavalue']['value'])) {
                continue;
            }
            $v = $statement['mainsnak']['datavalue']['value'];
            if (empty($v['time'])) {
                continue;
            }
            $time = (string)$v['time'];
            $precision = !empty($v['precision']) ? (int)$v['precision'] : 9;
            if (preg_match('/^[+-]?(\d{4})-(\d{2})-(\d{2})T/', $time, $m)) {
                if ($precision >= 11) {
                    return $m[1] . '-' . $m[2] . '-' . $m[3];
                }
                if ($precision === 10) {
                    return $m[1] . '-' . $m[2];
                }
                return $m[1];
            }
        }
        return '';
    }

    protected function wikidataMoneyClaim($claims, $property)
    {
        if (empty($claims[$property]) || !is_array($claims[$property])) {
            return '';
        }
        foreach ($claims[$property] as $statement) {
            if (!empty($statement['rank']) && (string)$statement['rank'] === 'deprecated') {
                continue;
            }
            if (empty($statement['mainsnak']['datavalue']['value']) || !is_array($statement['mainsnak']['datavalue']['value'])) {
                continue;
            }
            $v = $statement['mainsnak']['datavalue']['value'];
            if (empty($v['amount'])) {
                continue;
            }
            return $this->wikidataFormatAmount((string)$v['amount']);
        }
        return '';
    }

    protected function wikidataRuntime($claims)
    {
        if (empty($claims['P2047']) || !is_array($claims['P2047'])) {
            return '';
        }
        foreach ($claims['P2047'] as $statement) {
            if (!empty($statement['rank']) && (string)$statement['rank'] === 'deprecated') {
                continue;
            }
            if (empty($statement['mainsnak']['datavalue']['value']) || !is_array($statement['mainsnak']['datavalue']['value'])) {
                continue;
            }
            $v = $statement['mainsnak']['datavalue']['value'];
            if (empty($v['amount'])) {
                continue;
            }
            $amount = (float)$v['amount'];
            $unit = !empty($v['unit']) ? (string)$v['unit'] : '';
            if ($unit !== '' && substr($unit, -6) === '/Q7727') {
                return (string)round($amount) . ' min';
            }
            if ($unit !== '' && substr($unit, -7) === '/Q11574') {
                return (string)round($amount / 60) . ' min';
            }
            if ($unit !== '' && substr($unit, -7) === '/Q25235') {
                return (string)round($amount * 60) . ' min';
            }
            if ($amount > 0) {
                return (string)round($amount) . ' min';
            }
        }
        return '';
    }

    protected function wikidataFormatAmount($amount)
    {
        $num = (float)$amount;
        if ($num === 0.0) {
            return '';
        }
        $abs = abs($num);
        if ($abs >= 1000000) {
            return '$' . number_format((int)round($num), 0, '.', ',');
        }
        if ($abs >= 1000) {
            return '$' . number_format($num, 0, '.', ',');
        }
        if (floor($num) == $num) {
            return '$' . (string)(int)$num;
        }
        return '$' . number_format($num, 2, '.', ',');
    }

    protected function extractYearFromText($text)
    {
        if (!is_string($text) || $text === '') {
            return 0;
        }
        if (preg_match('/\b(19\d{2}|20\d{2})\b/', $text, $m)) {
            return (int)$m[1];
        }
        return 0;
    }

    protected function lookupImdb($guess)
    {
        $query = trim((string)$guess['title']);
        if ($query === '') {
            $this->lookupDebug = array('stage' => 'imdb', 'reason' => 'empty_query');
            return null;
        }
        $rows = array();
        $seen = array();
        $attempted = array();
            $hadTransportError = false;
            $lastTransportError = '';
        foreach ($this->buildImdbQueryVariants($query) as $variant) {
            $suggestUrl = $this->imdbSuggestUrl($variant);
            $attempted[] = $variant;
            $data = $this->httpJson($suggestUrl);
            if (empty($data['d']) || !is_array($data['d'])) {
                    if ($this->lastHttpError !== '') {
                        $hadTransportError = true;
                        $lastTransportError = $this->lastHttpError;
                    }
                continue;
            }
            foreach ($data['d'] as $row) {
                $id = !empty($row['id']) ? (string)$row['id'] : '';
                if ($id === '' || isset($seen[$id])) {
                    continue;
                }
                $rows[] = $row;
                $seen[$id] = 1;
            }
            if (!empty($rows)) {
                break;
            }
        }
        if (empty($rows)) {
            $fallback = $this->lookupImdbViaFind($query);
            if (is_array($fallback) && !empty($fallback['id'])) {
                $rows[] = $fallback;
            } else {
                $this->lookupDebug = array(
                    'stage' => 'imdb',
                    'reason' => $hadTransportError ? 'imdb_transport_error' : 'suggest_empty_and_find_no_hit',
                    'query' => $query,
                    'attempted' => implode(' | ', $attempted),
                    'transport' => $lastTransportError,
                );
                return null;
            }
        }

        $best = null;
        $bestScore = -1;
        $wantYear = !empty($guess['year']) ? (int)$guess['year'] : 0;
        $wantTitleNorm = strtolower(trim(preg_replace('/\s+/', ' ', $query)));

        foreach ($rows as $row) {
            if (empty($row['id']) || strpos((string)$row['id'], 'tt') !== 0) {
                continue;
            }
            $label = isset($row['l']) ? (string)$row['l'] : '';
            if ($label === '') {
                continue;
            }

            $type = strtolower((string)(isset($row['q']) ? $row['q'] : ''));
            $rowYear = isset($row['y']) ? (int)$row['y'] : 0;
            $labelNorm = strtolower(trim(preg_replace('/\s+/', ' ', $label)));

            $score = 0;
            if (strpos($type, 'movie') !== false || strpos($type, 'feature') !== false) {
                $score += 20;
            }
            if ($wantTitleNorm !== '' && $labelNorm === $wantTitleNorm) {
                $score += 20;
            }
            if ($wantTitleNorm !== '' && strpos($labelNorm, $wantTitleNorm) !== false) {
                $score += 8;
            }
            if ($wantYear > 0 && $rowYear > 0) {
                if ($rowYear === $wantYear) {
                    $score += 30;
                } elseif (abs($rowYear - $wantYear) <= 1) {
                    $score += 8;
                }
            }

            if ($score > $bestScore) {
                $best = $row;
                $bestScore = $score;
            }
        }

        if (!$best || empty($best['id'])) {
            $this->lookupDebug = array(
                'stage' => 'imdb',
                'reason' => 'no_scored_candidate',
                'query' => $query,
            );
            return null;
        }

        $imdbId = (string)$best['id'];
        $title = isset($best['l']) ? (string)$best['l'] : $query;
        $year = isset($best['y']) ? (string)$best['y'] : '';
        $poster = '';
        if (!empty($best['i']) && is_array($best['i']) && !empty($best['i']['imageUrl'])) {
            $poster = (string)$best['i']['imageUrl'];
        }

        $details = $this->lookupImdbDetails($imdbId);
        if (!is_array($details)) {
            $details = array();
        }

        $movie = array(
            'source'      => 'IMDb',
            'title'       => !empty($details['title']) ? $details['title'] : $title,
            'original'    => '',
            'year'        => !empty($details['year']) ? $details['year'] : $year,
            'released'    => !empty($details['released']) ? $details['released'] : '',
            'plot'        => isset($details['plot']) ? $details['plot'] : '',
            'rating'      => isset($details['rating']) ? $details['rating'] : '',
            'votes'       => isset($details['votes']) ? $details['votes'] : '',
            'runtime'     => isset($details['runtime']) ? $details['runtime'] : '',
            'genres'      => isset($details['genres']) ? $details['genres'] : '',
            'director'    => isset($details['director']) ? $details['director'] : '',
            'writer'      => isset($details['writer']) ? $details['writer'] : '',
            'actors'      => isset($details['actors']) ? $details['actors'] : '',
            'country'     => isset($details['country']) ? $details['country'] : '',
            'language_name' => isset($details['language_name']) ? $details['language_name'] : '',
            'poster'      => !empty($details['poster']) ? $details['poster'] : $poster,
            'tmdb_url'    => '',
            'imdb_url'    => 'https://www.imdb.com/title/' . rawurlencode($imdbId),
            'wikipedia_url' => '',
        );

        // If IMDb page scraping is blocked/partial (common with WAF challenge),
        // enrich missing fields through OMDb using the resolved imdbID.
        return $this->enrichImdbWithOmdb($imdbId, $movie);
    }

    protected function enrichImdbWithOmdb($imdbId, $movie)
    {
        $key = trim((string)$this->opts['omdbApiKey']);
        if ($key === '' || !preg_match('/^tt\d+$/', (string)$imdbId)) {
            return $movie;
        }

        $needs = false;
        foreach (array('plot', 'rating', 'votes', 'runtime', 'genres') as $k) {
            if (empty($movie[$k])) {
                $needs = true;
                break;
            }
        }
        if (!$needs) {
            return $movie;
        }

        $url = 'https://www.omdbapi.com/?' . http_build_query(array(
            'apikey' => $key,
            'i'      => $imdbId,
            'plot'   => 'full',
            'r'      => 'json',
        ));
        $data = $this->httpJson($url);
        if (empty($data) || (!empty($data['Response']) && strtolower((string)$data['Response']) === 'false')) {
            return $movie;
        }

        $filled = false;
        $map = array(
            'title'   => 'Title',
            'year'    => 'Year',
            'released'=> 'Released',
            'plot'    => 'Plot',
            'rating'  => 'imdbRating',
            'votes'   => 'imdbVotes',
            'runtime' => 'Runtime',
            'genres'  => 'Genre',
            'director'=> 'Director',
            'writer'  => 'Writer',
            'actors'  => 'Actors',
            'country' => 'Country',
            'language_name' => 'Language',
            'awards'  => 'Awards',
            'boxoffice' => 'BoxOffice',
            'production' => 'Production',
            'poster'  => 'Poster',
        );
        foreach ($map as $dst => $src) {
            if (empty($movie[$dst]) && !empty($data[$src]) && (string)$data[$src] !== 'N/A') {
                $movie[$dst] = (string)$data[$src];
                $filled = true;
            }
        }

        if ($filled && $movie['source'] === 'IMDb') {
            $movie['source'] = 'IMDb+OMDb';
        }
        return $movie;
    }

    protected function lookupImdbViaFind($query)
    {
        $url = 'https://www.imdb.com/find/?q=' . rawurlencode((string)$query) . '&s=tt&ttype=ft&ref_=fn_ft';
        $html = $this->httpGet($url);
        if ($html === null || $html === '') {
            return null;
        }

        if (!preg_match('/\/title\/(tt\d+)\//i', $html, $mId)) {
            return null;
        }
        $imdbId = (string)$mId[1];
        $label = '';
        if (preg_match('/href="\/title\/' . preg_quote($imdbId, '/') . '\/[^\"]*"[^>]*>([^<]+)<\/a>/i', $html, $mLabel)) {
            $label = trim(html_entity_decode((string)$mLabel[1], ENT_QUOTES, 'UTF-8'));
        }
        $year = 0;
        if (preg_match('/\/title\/' . preg_quote($imdbId, '/') . '\/[^\"]*"[^\n\r]{0,200}\((\d{4})\)/i', $html, $mYear)) {
            $year = (int)$mYear[1];
        }

        return array(
            'id' => $imdbId,
            'l'  => ($label !== '' ? $label : $query),
            'q'  => 'feature',
            'y'  => $year,
        );
    }

    protected function buildImdbQueryVariants($query)
    {
        $variants = array();
        $add = function($value) use (&$variants) {
            $value = trim((string)$value);
            if ($value === '') {
                return;
            }
            $k = strtolower($value);
            if (!isset($variants[$k])) {
                $variants[$k] = $value;
            }
        };

        $add($query);

        // Common franchise subtitle variant: "Title A Franchise Name" -> "Title: A Franchise Name"
        if (stripos($query, ' a knives out mystery') !== false && stripos($query, ': a knives out mystery') === false) {
            $add(preg_replace('/\s+a\s+knives\s+out\s+mystery\s*$/i', ': A Knives Out Mystery', $query));
            $add(preg_replace('/\s+a\s+knives\s+out\s+mystery\s*$/i', '', $query));
        }

        return array_values($variants);
    }

    protected function imdbSuggestUrl($query)
    {
        $slug = preg_replace('/\s+/', '_', trim((string)$query));
        $first = strtolower(substr($slug, 0, 1));
        if ($first < 'a' || $first > 'z') {
            $first = 'x';
        }
        return 'https://v3.sg.media-imdb.com/suggestion/'
            . rawurlencode($first) . '/' . rawurlencode($slug) . '.json';
    }

    protected function lookupImdbDetails($imdbId)
    {
        if (!preg_match('/^tt\d+$/', (string)$imdbId)) {
            return null;
        }

        $html = $this->httpGet('https://www.imdb.com/title/' . rawurlencode($imdbId) . '/');
        if ($html === null || $html === '') {
            return null;
        }

        if (!preg_match('/<script[^>]+type="application\/ld\+json"[^>]*>(.*?)<\/script>/is', $html, $m)) {
            return null;
        }

        $raw = html_entity_decode(trim($m[1]), ENT_QUOTES, 'UTF-8');
        $data = json_decode($raw, true);
        if (!is_array($data)) {
            return null;
        }

        $title = isset($data['name']) ? (string)$data['name'] : '';
        $year = '';
        $released = '';
        if (!empty($data['datePublished']) && preg_match('/^(\d{4})/', (string)$data['datePublished'], $ym)) {
            $year = $ym[1];
            $released = (string)$data['datePublished'];
        }

        $genres = '';
        if (!empty($data['genre'])) {
            if (is_array($data['genre'])) {
                $genres = implode(', ', $data['genre']);
            } else {
                $genres = (string)$data['genre'];
            }
        }

        $runtime = '';
        if (!empty($data['duration'])) {
            $runtime = $this->parseIsoDuration((string)$data['duration']);
        }

        $rating = '';
        $votes = '';
        if (!empty($data['aggregateRating']) && is_array($data['aggregateRating'])) {
            if (isset($data['aggregateRating']['ratingValue'])) {
                $rating = (string)$data['aggregateRating']['ratingValue'];
            }
            if (isset($data['aggregateRating']['ratingCount'])) {
                $votes = (string)$data['aggregateRating']['ratingCount'];
            }
        }

        $poster = '';
        if (!empty($data['image'])) {
            if (is_array($data['image'])) {
                $poster = (string)reset($data['image']);
            } else {
                $poster = (string)$data['image'];
            }
        }

        $director = '';
        if (!empty($data['director'])) {
            if (is_array($data['director'])) {
                $dNames = array();
                foreach ($data['director'] as $d) {
                    if (is_array($d) && !empty($d['name'])) {
                        $dNames[] = (string)$d['name'];
                    }
                }
                $director = implode(', ', $dNames);
            } elseif (is_string($data['director'])) {
                $director = (string)$data['director'];
            }
        }

        $actors = '';
        if (!empty($data['actor'])) {
            if (is_array($data['actor'])) {
                $aNames = array();
                foreach ($data['actor'] as $i => $a) {
                    if ($i >= 6) {
                        break;
                    }
                    if (is_array($a) && !empty($a['name'])) {
                        $aNames[] = (string)$a['name'];
                    }
                }
                $actors = implode(', ', $aNames);
            }
        }

        return array(
            'title'  => $title,
            'year'   => $year,
            'released' => $released,
            'plot'   => isset($data['description']) ? (string)$data['description'] : '',
            'genres' => $genres,
            'runtime'=> $runtime,
            'rating' => $rating,
            'votes'  => $votes,
            'director' => $director,
            'writer' => '',
            'actors' => $actors,
            'country' => '',
            'language_name' => '',
            'poster' => $poster,
        );
    }

    protected function parseIsoDuration($iso)
    {
        if (!preg_match('/^PT(?:(\d+)H)?(?:(\d+)M)?$/', $iso, $m)) {
            return '';
        }
        $hours = !empty($m[1]) ? (int)$m[1] : 0;
        $mins  = !empty($m[2]) ? (int)$m[2] : 0;
        $total = $hours * 60 + $mins;
        if ($total <= 0) {
            return '';
        }
        return $total . ' min';
    }

    protected function httpGet($url)
    {
        $timeout = max(1, (int)$this->opts['httpTimeout']);
            $this->lastHttpError = '';
        $ctx = stream_context_create(array(
            'http' => array(
                'method'  => 'GET',
                'timeout' => $timeout,
                'header'  => "User-Agent: elFinder-MovieInfo\r\n",
            ),
        ));
        $raw = @file_get_contents($url, false, $ctx);
            if ($raw !== false && $raw !== '') {
                return $raw;
            }

            $err = error_get_last();
            if (!empty($err['message'])) {
                $this->lastHttpError = (string)$err['message'];
            }

            // Fallback for embedded targets where PHP streams fail on modern TLS,
            // while curl binary still succeeds.
            if (function_exists('shell_exec')) {
                $cmd = 'curl -L -s --max-time ' . (int)$timeout
                    . ' --connect-timeout ' . (int)$timeout
                    . ' -A ' . escapeshellarg('elFinder-MovieInfo')
                    . ' ' . escapeshellarg($url)
                    . ' 2>/dev/null';
                $raw2 = @shell_exec($cmd);
                if (is_string($raw2) && $raw2 !== '') {
                    $this->lastHttpError = '';
                    return $raw2;
                }
                if ($this->lastHttpError === '') {
                    $this->lastHttpError = 'stream_failed_and_curl_empty';
                }
            }

            return null;
    }

    protected function httpJson($url)
    {
            $json = $this->httpGet($url);
            if ($json === null || $json === '') {
            return null;
        }
        $data = json_decode($json, true);
        return is_array($data) ? $data : null;
    }

    protected function cacheLoad()
    {
        $f = (string)$this->opts['cacheFile'];
        if ($f === '' || !is_readable($f)) {
            return array();
        }
        $raw = @file_get_contents($f);
        if ($raw === false || $raw === '') {
            return array();
        }
        $data = json_decode($raw, true);
        return is_array($data) ? $data : array();
    }

    protected function cacheGet($cache, $key)
    {
        if (empty($cache[$key]) || !is_array($cache[$key])) {
            return null;
        }
        $ttl = max(60, (int)$this->opts['cacheTtl']);
        $ts = isset($cache[$key]['ts']) ? (int)$cache[$key]['ts'] : 0;
        if ($ts <= 0 || (time() - $ts) > $ttl) {
            return null;
        }
        return isset($cache[$key]['data']) && is_array($cache[$key]['data']) ? $cache[$key]['data'] : null;
    }

    protected function cacheSave($cache)
    {
        $f = (string)$this->opts['cacheFile'];
        if ($f === '') {
            return;
        }
        @file_put_contents($f, json_encode($cache), LOCK_EX);
    }

    protected function renderLookupPanel($provider, $tmdbKey, $omdbKey, $message)
    {
        $provider = strtolower((string)$provider);
        if ($provider !== 'tmdb' && $provider !== 'omdb' && $provider !== 'wikipedia' && $provider !== 'imdb' && $provider !== 'auto') {
            $provider = 'auto';
        }

        $hasTmdbKey = (trim((string)$tmdbKey) !== '');
        $hasOmdbKey = (trim((string)$omdbKey) !== '');
        $esc = function($v) { return htmlspecialchars((string)$v, ENT_QUOTES, 'UTF-8'); };

        $providerBtn = function($id, $label) use ($provider, $esc) {
            $active = ($provider === $id) ? ' ef-mi-provider-btn-active' : '';
            return '<button type="button" class="ef-mi-provider-btn' . $active . '" data-ef-mi-provider="' . $esc($id) . '"'
                . ' style="margin:0 6px 6px 0;padding:4px 8px;font-size:12px;">'
                . $esc($label)
                . '</button>';
        };

        $editLabel = ($hasTmdbKey || $hasOmdbKey) ? 'Advanced: replace keys' : 'Advanced: edit keys';
        $collapsedByDefault = ($hasTmdbKey && $hasOmdbKey);

        return ''
            . '<div class="ef-mi-tmdb-panel"'
            . ' data-ef-mi-selected-provider="' . $esc($provider) . '"'
            . ' data-ef-mi-has-tmdb-key="' . ($hasTmdbKey ? '1' : '0') . '"'
            . ' data-ef-mi-has-omdb-key="' . ($hasOmdbKey ? '1' : '0') . '"'
            . ' data-ef-mi-keys-collapsed="' . ($collapsedByDefault ? '1' : '0') . '"'
            . ' style="margin-top:10px;padding:10px;border:1px solid #e5e7eb;border-radius:6px;background:#f9fafb;">'
            . '<div style="font-weight:600;margin-bottom:6px;">Try another database</div>'
            . '<div style="font-size:12px;color:#4b5563;margin-bottom:8px;">'
            . $esc($message)
            . '</div>'
            . '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">'
            . '<div style="font-size:12px;color:#374151;">'
            . 'Provider: '
            . $providerBtn('auto', 'Auto')
            . $providerBtn('tmdb', 'TMDb')
            . $providerBtn('omdb', 'OMDb')
            . $providerBtn('wikipedia', 'Wikipedia')
            . $providerBtn('imdb', 'IMDb')
            . '</div>'
            . '<button type="button" class="ef-mi-edit-keys"'
            . ' style="padding:2px 4px;font-size:11px;color:#6b7280;background:transparent;border:0;text-decoration:underline;cursor:pointer;white-space:nowrap;">'
            . $esc($editLabel)
            . '</button>'
            . '</div>'
            . '<div class="ef-mi-key-fields">'
            . '<label style="display:block;margin:8px 0 4px;font-size:12px;color:#374151;">TMDb API key (optional)</label>'
            . '<input type="text" class="ef-mi-key-tmdb" style="width:100%;box-sizing:border-box;" placeholder="TMDb API key">'
            . '<label style="display:block;margin:8px 0 4px;font-size:12px;color:#374151;">OMDb API key (optional)</label>'
            . '<input type="text" class="ef-mi-key-omdb" style="width:100%;box-sizing:border-box;" placeholder="OMDb API key">'
            . '<label style="display:block;margin-top:8px;font-size:12px;color:#374151;">'
            . '<input type="checkbox" class="ef-mi-keys-save" value="1"> Save in configuration'
            . '</label>'
            . '</div>'
            . '<button type="button" class="ef-mi-keys-apply" style="margin-top:8px;">Run selected provider</button>'
            . '<div class="ef-mi-keys-status" style="margin-top:6px;font-size:12px;color:#6b7280;"></div>'
            . '</div>';
    }

    protected function renderNotFound($guess, $filename)
    {
        $title = htmlspecialchars($guess['title'], ENT_QUOTES, 'UTF-8');
        $year = htmlspecialchars((string)$guess['year'], ENT_QUOTES, 'UTF-8');
        $name = htmlspecialchars($filename, ENT_QUOTES, 'UTF-8');
        $titleRaw = (string)$guess['title'];
        $yearRaw = (string)$guess['year'];
        $tmdbKey = trim((string)$this->opts['tmdbApiKey']);
        $omdbKey = trim((string)$this->opts['omdbApiKey']);
        $provider = strtolower((string)$this->opts['provider']);
        $hint = (($provider === 'tmdb' && $tmdbKey === '') || ($provider === 'omdb' && $omdbKey === ''))
            ? 'The selected provider requires an API key. Add it below and retry.'
            : 'No match found in configured providers.';

        $debugReason = 'no_match';
        if ($provider === 'tmdb' && $tmdbKey === '') {
            $debugReason = 'tmdb_key_missing';
        } elseif ($provider === 'omdb' && $omdbKey === '') {
            $debugReason = 'omdb_key_missing';
        } elseif ($provider === 'auto' && $tmdbKey === '' && $omdbKey === '') {
            $debugReason = 'auto_fallback_to_wikipedia_imdb_no_hit';
        } elseif ($provider === 'wikipedia') {
            $debugReason = 'wikipedia_no_hit';
        } elseif ($provider === 'imdb') {
            $debugReason = 'imdb_no_hit';
        }
        if (!empty($this->lookupDebug['reason'])) {
            $debugReason = (string)$this->lookupDebug['reason'];
        }

        $attemptedProviders = ($provider === 'auto') ? 'tmdb,omdb,wikipedia,imdb' : $provider;
        $debugDetail = '';
        if (!empty($this->lookupDebug) && is_array($this->lookupDebug)) {
            $parts = array();
            if (!empty($this->lookupDebug['reason'])) {
                $parts[] = 'reason=' . (string)$this->lookupDebug['reason'];
            }
            if (!empty($this->lookupDebug['query'])) {
                $parts[] = 'query=' . (string)$this->lookupDebug['query'];
            }
            if (!empty($this->lookupDebug['attempted'])) {
                $parts[] = 'attempted=' . (string)$this->lookupDebug['attempted'];
            }
            if (!empty($this->lookupDebug['transport'])) {
                $parts[] = 'transport=' . (string)$this->lookupDebug['transport'];
            }
            $debugDetail = implode('; ', $parts);
        }

        $attr = function($v) {
            return htmlspecialchars((string)$v, ENT_QUOTES, 'UTF-8');
        };

        $panel = $this->renderLookupPanel(
            $provider,
            $tmdbKey,
            $omdbKey,
            'Select a provider and retry. If a required API key is missing, add it below.'
        );

        return '<div class="ef-movieinfo-card"'
            . ' data-ef-mi-status="not-found"'
            . ' data-ef-mi-provider="' . $attr($provider) . '"'
            . ' data-ef-mi-attempted="' . $attr($attemptedProviders) . '"'
            . ' data-ef-mi-guess-title="' . $attr($titleRaw) . '"'
            . ' data-ef-mi-guess-year="' . $attr($yearRaw) . '"'
            . ' data-ef-mi-debug-reason="' . $attr($debugReason) . '"'
            . ' data-ef-mi-debug-detail="' . $attr($debugDetail) . '"'
            . ' data-ef-mi-has-tmdb-key="' . ($tmdbKey === '' ? '0' : '1') . '"'
            . ' data-ef-mi-has-omdb-key="' . ($omdbKey === '' ? '0' : '1') . '"'
            . '>'
            . '<h3 style="margin:0 0 8px 0;">Movie lookup</h3>'
            . '<p style="margin:0 0 6px 0;"><b>File:</b> ' . $name . '</p>'
            . '<p style="margin:0 0 6px 0;"><b>Guess:</b> ' . $title . ($year !== '' ? (' (' . $year . ')') : '') . '</p>'
            . '<p style="margin:0;color:#888;">' . htmlspecialchars($hint, ENT_QUOTES, 'UTF-8') . '</p>'
            . $panel
            . '</div>';
    }

    protected function renderHtml($m, $guess, $filename)
    {
        $esc = function($v) { return htmlspecialchars((string)$v, ENT_QUOTES, 'UTF-8'); };
        $poster = !empty($m['poster']) ? '<img class="ef-mi-poster" src="' . $esc($m['poster']) . '" alt="poster">' : '';
        $tmdb = !empty($m['tmdb_url']) ? '<a href="' . $esc($m['tmdb_url']) . '" target="_blank" rel="noopener">TMDb</a>' : '';
        $imdb = !empty($m['imdb_url']) ? '<a href="' . $esc($m['imdb_url']) . '" target="_blank" rel="noopener">IMDb</a>' : '';
        $wiki = !empty($m['wikipedia_url']) ? '<a href="' . $esc($m['wikipedia_url']) . '" target="_blank" rel="noopener">Wikipedia</a>' : '';
        $home = !empty($m['homepage']) ? '<a href="' . $esc($m['homepage']) . '" target="_blank" rel="noopener">Official</a>' : '';
        $linkItems = array();
        foreach (array($tmdb, $imdb, $wiki, $home) as $lk) {
            if ($lk !== '') {
                $linkItems[] = $lk;
            }
        }
        $links = implode(' · ', $linkItems);

        $metaRows = array();
        if (!empty($m['year']))   $metaRows[] = '<span><b>Year:</b> ' . $esc($m['year']) . '</span>';
        if (!empty($m['released'])) $metaRows[] = '<span><b>Released:</b> ' . $esc($m['released']) . '</span>';
        if (!empty($m['genres'])) $metaRows[] = '<span><b>Genres:</b> ' . $esc($m['genres']) . '</span>';
        if (!empty($m['runtime'])) $metaRows[] = '<span><b>Runtime:</b> ' . $esc($m['runtime']) . '</span>';
        if (!empty($m['rating'])) $metaRows[] = '<span><b>Rating:</b> ' . $esc($m['rating'])
            . (!empty($m['votes']) ? (' (' . $esc($m['votes']) . ' votes)') : '') . '</span>';
        if (!empty($m['country'])) $metaRows[] = '<span><b>Country:</b> ' . $esc($m['country']) . '</span>';
        if (!empty($m['language_name'])) $metaRows[] = '<span><b>Language:</b> ' . $esc($m['language_name']) . '</span>';

        $detailRows = array();
        if (!empty($m['director'])) $detailRows[] = '<div><b>Director:</b> ' . $esc($m['director']) . '</div>';
        if (!empty($m['writer'])) $detailRows[] = '<div><b>Writer:</b> ' . $esc($m['writer']) . '</div>';
        if (!empty($m['actors'])) $detailRows[] = '<div><b>Cast:</b> ' . $esc($m['actors']) . '</div>';
        if (!empty($m['tagline'])) $detailRows[] = '<div><b>Tagline:</b> ' . $esc($m['tagline']) . '</div>';
        if (!empty($m['status'])) $detailRows[] = '<div><b>Status:</b> ' . $esc($m['status']) . '</div>';
        if (!empty($m['awards'])) $detailRows[] = '<div><b>Awards:</b> ' . $esc($m['awards']) . '</div>';
        if (!empty($m['production'])) $detailRows[] = '<div><b>Production:</b> ' . $esc($m['production']) . '</div>';
        if (!empty($m['boxoffice'])) $detailRows[] = '<div><b>Box office:</b> ' . $esc($m['boxoffice']) . '</div>';
        if (!empty($m['budget'])) $detailRows[] = '<div><b>Budget:</b> ' . $esc($m['budget']) . '</div>';
        if (!empty($m['revenue'])) $detailRows[] = '<div><b>Revenue:</b> ' . $esc($m['revenue']) . '</div>';

        $provider = strtolower((string)$this->opts['provider']);
        if ($provider !== 'tmdb' && $provider !== 'omdb' && $provider !== 'wikipedia' && $provider !== 'imdb' && $provider !== 'auto') {
            $provider = 'auto';
        }
        $panel = $this->renderLookupPanel(
            $provider,
            trim((string)$this->opts['tmdbApiKey']),
            trim((string)$this->opts['omdbApiKey']),
            'Current result loaded from ' . (isset($m['source']) ? (string)$m['source'] : 'provider')
                . '. You can query again with any provider.'
        );

        return '<div class="ef-movieinfo-card">'
            . '<div class="ef-mi-head">'
            . $poster
            . '<div class="ef-mi-main">'
            . '<h3 style="margin:0 0 4px 0;">' . $esc($m['title']) . '</h3>'
            . (!empty($m['original']) ? ('<div style="color:#777;margin-bottom:4px;">' . $esc($m['original']) . '</div>') : '')
            . '<div style="font-size:12px;color:#666;margin-bottom:6px;">Source: ' . $esc($m['source']) . '</div>'
            . ($links !== '' ? ('<div style="margin-bottom:8px;">' . $links . '</div>') : '')
            . '<div class="ef-mi-meta">' . implode(' · ', $metaRows) . '</div>'
            . (!empty($detailRows) ? ('<div style="margin-top:8px;line-height:1.45;">' . implode('', $detailRows) . '</div>') : '')
            . '</div></div>'
            . (!empty($m['plot']) ? ('<p style="margin:10px 0 0 0;line-height:1.4;">' . $esc($m['plot']) . '</p>') : '')
            . '<div style="margin-top:10px;font-size:12px;color:#666;">'
            . 'File: ' . $esc($filename) . '<br>'
            . 'Parsed as: ' . $esc($guess['title']) . (!empty($guess['year']) ? (' (' . $esc($guess['year']) . ')') : '')
            . '</div>'
            . $panel
            . '</div>';
    }
}
