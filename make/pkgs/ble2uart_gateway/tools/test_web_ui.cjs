const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const {spawnSync} = require('node:child_process');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const binary = path.join(root, 'src/target/debug/ble2uart-gateway');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'ble-web-ui-'));
const config = path.join(directory, 'gateway.yaml');
const source = fs.readFileSync(path.join(root, 'files/root/usr/lib/cgi-bin/ble2uart_gateway.cgi'), 'utf8');
const start = source.indexOf('<style>\n#bbApp');
const html = '<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gateway UI test</title><body style="margin:16px;font:14px sans-serif"><form>' + source.slice(start, source.indexOf('</script>', start) + 9) + '</form></body></html>';
assert(start > 0);
const created = spawnSync(binary, ['--write-default-config', config]);
assert.equal(created.status, 0, created.stderr.toString());
const observations = [
    {mac:'A4C1383406CE', name:'ATC sensor', vendor:'Telink Semiconductor', format:'bt_home_v2', rssi:-70, phy:'phy_raw=0x33 primary=Coded secondary=Coded', count:6, last_seen:'2026-10-16T18:00:00Z', data:'0D16D2FC4000EB0C3E0B10001101', configured:false},
    {mac:'54EF44001122', name:'Other sensor', vendor:'Xiaomi Communications', format:'custom', rssi:-80, phy:'phy_raw=0x01 primary=1M secondary=none', count:2, last_seen:'2026-10-16T18:00:00Z', data:'020106', configured:false},
];
let active = false;
let restarts = 0;
let browser;
const escaped = text => text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const server = http.createServer(async (request, response) => {
    const assets = {'/ace/ace.js':path.resolve(root,'../disk-mgmt-cgi/files/root/usr/mww/ace/ace.js'),'/ble2uart_gateway/mode-yaml.js':path.join(root,'files/root/usr/mww/ble2uart_gateway/mode-yaml.js')};
    if (assets[request.url]) {response.setHeader('Content-Type','application/javascript');response.end(fs.readFileSync(assets[request.url]));return;}
    if (!request.url.startsWith('/cgi-bin/extra/')) {
        response.setHeader('Content-Type','text/html'); response.end(html); return;
    }
    let input = '';
    for await (const chunk of request) input += chunk;
    const action = new URL(request.url, 'http://localhost').searchParams.get('action');
    assert(!request.url.includes('11111111111111111111111111111111'));
    let result;
    if (['read','save','check','backups','restore','inspect'].includes(action)) {
        const child = spawnSync(binary, ['--config',config,'--web-config',action], {input, encoding:'utf8'});
        result = JSON.parse(child.stdout);
    } else if (['status','discover-start','discover-stop'].includes(action)) {
        if (action === 'discover-start') {assert.equal(request.method,'POST'); active = true;}
        if (action === 'discover-stop') {assert.equal(request.method,'POST'); active = false;}
        result = {success:true, connected:true, active, remaining_s:active?30:0, reports:8, devices:observations, overflow:0, error:''};
    } else if (action === 'restart') {restarts++;result={success:true};}
    else result={success:true};
    response.setHeader('Content-Type','text/html');
    response.end('<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json\n\n'+escaped(JSON.stringify(result))+'</pre></div></div>');
});

(async () => {
    try {
        await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
        browser = await chromium.launch({headless:true});
        const page = await browser.newPage({viewport:{width:1280,height:900}});
        const errors=[];page.on('pageerror',error=>errors.push(error.message));
        await page.goto('http://127.0.0.1:'+server.address().port);
        await page.getByRole('status').filter({hasText:'Configuration loaded'}).waitFor();
        await page.getByRole('button',{name:'Add device',exact:true}).click();
        await page.getByLabel('MAC',{exact:true}).fill('AABBCCDDEEFF');
        await page.getByLabel('Label',{exact:true}).fill('Test } </pre><script>window.injected=true</script>');
        await page.getByLabel('Bindkey (32 hexadecimal digits)',{exact:true}).fill('1'.repeat(32));
        await page.getByRole('button',{name:'Show bindkey',exact:true}).click();
        assert.equal(await page.getByLabel('Bindkey (32 hexadecimal digits)',{exact:true}).getAttribute('type'),'text');
        await page.getByRole('button',{name:'Hide bindkey',exact:true}).click();
        assert.equal(await page.getByLabel('Bindkey (32 hexadecimal digits)',{exact:true}).getAttribute('type'),'password');
        await page.getByRole('button',{name:'Keep changes',exact:true}).click();
        await page.locator('#bbDeviceDialog').waitFor({state:'hidden'});
        await page.getByRole('button',{name:'Save configuration',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'Saved.'}).waitFor();
        assert.equal(restarts,0);
        assert.equal(await page.evaluate(()=>window.injected), undefined);
        await page.getByRole('tab',{name:'Settings',exact:true}).click();
        await page.getByLabel('Filter registered devices in ESP32',{exact:true}).uncheck();
        await page.getByRole('button',{name:'Validate',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'Configuration is valid'}).waitFor();
        await page.getByRole('tab',{name:'YAML',exact:true}).click();
        await page.locator('#bbYaml.ace_editor').waitFor();
        assert(await page.evaluate(()=>ace.edit('bbYaml').getValue().includes('filter_known_devices: false')));
        assert.equal(await page.evaluate(()=>ace.edit('bbYaml').session.getMode().$id),'ace/mode/yaml');
        await page.getByRole('tab',{name:'Discovery',exact:true}).click();
        await page.locator('#bbFound tr').filter({hasText:'ATC sensor'}).waitFor();
        await page.getByRole('button',{name:'Start discovery',exact:true}).click();
        await page.locator('#bbDiscoveryStatus').filter({hasText:'Scanning'}).waitFor();
        await page.getByLabel('Filter by OUI vendor',{exact:true}).selectOption('Telink Semiconductor');
        assert.equal(await page.locator('#bbFound tr').count(),1);
        await page.getByRole('button',{name:'Inspect',exact:true}).click();
        await page.waitForFunction(()=>document.getElementById('bbPacket').textContent.includes('"decode_status": "ok"'));
        const inspected=JSON.parse(await page.locator('#bbPacket').textContent());
        assert.equal(inspected.wire_format,'bt_home_v2');
        assert.equal(inspected.measurements.opened,'1');
        assert.equal(inspected.measurements.switch,'0');
        await page.getByRole('button',{name:'Configure',exact:true}).click();
        assert.equal(await page.getByLabel('MAC',{exact:true}).inputValue(),'A4C1383406CE');
        await page.getByRole('button',{name:'Keep changes',exact:true}).click();
        await page.locator('#bbDeviceDialog').waitFor({state:'hidden'});
        assert.equal(await page.locator('#bbFound .bbActions').first().evaluate(element=>getComputedStyle(element).gap),'8px');
        await page.getByRole('button',{name:'Remove',exact:true}).filter({visible:true}).first().click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await page.getByRole('button',{name:'Configure',exact:true}).click();
        await page.getByRole('button',{name:'Keep changes',exact:true}).click();
        await page.locator('#bbDeviceDialog').waitFor({state:'hidden'});
        await page.getByRole('button',{name:'Stop',exact:true}).click();
        await page.locator('#bbDiscoveryStatus').filter({hasText:'Idle'}).waitFor();
        await page.screenshot({path:'/tmp/ble-web-desktop.png',fullPage:true});
        await page.setViewportSize({width:390,height:844});
        await page.screenshot({path:'/tmp/ble-web-mobile.png',fullPage:true});
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
        await page.getByRole('tab',{name:'Devices',exact:true}).click();
        assert.equal(await page.locator('#bbDevices tr').count(),2);
        await page.getByRole('button',{name:'Save configuration',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'Saved.'}).waitFor();
        const saved = JSON.parse(spawnSync(binary,['--config',config,'--web-config','read'],{encoding:'utf8'}).stdout);
        assert.equal(saved.config.devices.length,2);
        assert.equal(saved.config.scanner.filter_known_devices,false);
        assert.deepEqual(errors,[]);
        console.log('UI PASS: device editing/saving, escaped labels, masked keys, settings/YAML sync, discovery/vendor filter/inspection/configure/stop, desktop/mobile layout; no implicit restart.');
    } finally {
        if (browser) await browser.close();
        server.close();
        fs.rmSync(directory,{recursive:true,force:true});
    }
})().catch(error=>{console.error(error);process.exitCode=1;});