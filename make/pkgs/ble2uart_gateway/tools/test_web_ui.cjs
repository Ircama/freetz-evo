const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const {spawnSync} = require('node:child_process');
const {chromium} = process.env.BLE_WEB_UI_SERVE_ONLY ? {} : require('playwright');

const root = path.resolve(__dirname, '..');
const binary = path.join(root, 'src/target/debug/ble2uart-gateway');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'ble-web-ui-'));
const config = path.join(directory, 'gateway.yaml');
const source = fs.readFileSync(path.join(root, 'files/root/usr/lib/cgi-bin/ble2uart_gateway.cgi'), 'utf8');
const start = source.indexOf('<style>\n#bbApp');
const serialStart=source.indexOf('cat << EOF',source.indexOf('en:"Serial link"'));
const serialEnd=source.indexOf('\nsec_end',serialStart);
assert(serialStart>0&&serialEnd>serialStart);
function startupFields(baudrate) {
    const result=spawnSync('sh',['-s'],{
        input:'html() { printf "%s" "$1"; }\nlang() { for arg; do case "$arg" in en:*) printf "%s" "${arg#en:}"; return;; esac; done; }\n'+source.slice(serialStart,serialEnd),
        env:{...process.env,BLE2UART_GATEWAY_SERIAL:'/dev/ttyACM0',BLE2UART_GATEWAY_BAUDRATE:String(baudrate),BLE2UART_GATEWAY_CONFIG_WAIT:'120'},encoding:'utf8',
    });
    assert.equal(result.status,0,result.stderr);
    return result.stdout;
}
const speeds=fs.readFileSync(path.join(root,'src/src/link.rs'),'utf8').match(/fn speed_constant[\s\S]*?\n\}/)[0];
const baudrates=[...speeds.matchAll(/^\s+(\d+) =>/gm)].map(match=>match[1]);
const html = '<!doctype html><html lang="en"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gateway UI test</title><body style="margin:16px;font:14px sans-serif"><form action="/cgi-bin/conf/ble2uart_gateway"><details id="bbStartup" open><summary>Startup and storage</summary><label>Configuration directory <input id="store" name="store" value="/tmp/flash/ble2uart_gateway"></label>' + startupFields(2000000) + '<div class="section"><div class="section"><div id="bbStartupActions"></div></div></div></details>' + source.slice(start, source.indexOf('</script>', start) + 9) + '<div id="bbStartupAdvanced">Advanced startup settings</div><div class="btn"><input type="submit" value="Apply"></div></form><form action="/cgi-bin/conf/ble2uart_gateway?default"><input type="submit" value="Default"></form></body></html>';
assert(start > 0);
const created = spawnSync(binary, ['--write-default-config', config]);
assert.equal(created.status, 0, created.stderr.toString());
const observations = [
    {addr_type:0, mac:'A4C1383406CE', name:'ATC sensor', vendor:'Telink Semiconductor', format:'bt_home_v2', rssi:-70, phy:'phy_raw=0x33 primary=Coded secondary=Coded', count:6, last_seen:'2026-10-16T18:00:00Z', data:'0201060D16D2FC40008A0C0E0B100011010B094154435F333430364345', configured:false},
    {addr_type:1, mac:'54EF44001122', name:'Other sensor', vendor:'Random / local address', format:'custom', rssi:-80, phy:'phy_raw=0x01 primary=1M secondary=none', count:2, last_seen:'2026-10-16T18:00:00Z', data:'020106', configured:false},
];
let active = false;
let restarts = 0;
let persistCalls = 0, failPersist = false;
let scanning = true, txadv = false;
let gatt = null, suspendedRadio = null;
const sessionToken = 'A'.repeat(32);
let failInspect = false;
let failCommand = false;
let daemonRunning = true, commandGate = null;
const atcConfig = {flg2:{bt5phy:false,longrange:false}};
let legacyFrontends = false;
let legacyBaudrate = null;
const commands = [];
let browser;
const escaped = text => text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const server = http.createServer(async (request, response) => {
    const extraArtifacts={
        '/test_automation.py':path.join(root,'tools/test_automation.py'),
        '/replay_capture.py':path.join(root,'tools/replay_capture.py'),
        '/capture_trace.py':path.join(root,'tools/capture_trace.py'),
        ...Object.fromEntries(['ca.pem','server.pem','server.key'].filter(()=>process.env.BLE_WEB_UI_TLS_DIR).map(name=>['/'+name,path.join(process.env.BLE_WEB_UI_TLS_DIR,name)])),
    };
    const artifact=request.url==='/candidate.cgi'?process.env.BLE_WEB_UI_CGI
        :request.url==='/candidate.bin'?process.env.BLE_WEB_UI_BINARY
        :request.url==='/test_sqlite_history.py'&&process.env.BLE_WEB_UI_CGI?path.join(root,'tools/test_sqlite_history.py')
        :process.env.BLE_WEB_UI_CGI?extraArtifacts[request.url]:null;
    if(artifact){
        response.setHeader('Access-Control-Allow-Origin','http://192.168.178.1:81');
        response.setHeader('Access-Control-Allow-Private-Network','true');
        response.setHeader('Content-Type','application/octet-stream');
        response.end(fs.readFileSync(artifact));return;
    }
    const assets = {'/ace/ace.js':path.resolve(root,'../disk-mgmt-cgi/files/root/usr/mww/ace/ace.js'),'/ace/mode-json.js':path.resolve(root,'../disk-mgmt-cgi/files/root/usr/mww/ace/mode-json.js'),'/ble2uart_gateway/mode-yaml.js':path.join(root,'files/root/usr/mww/ble2uart_gateway/mode-yaml.js')};
    if (assets[request.url]) {response.setHeader('Content-Type','application/javascript');response.end(fs.readFileSync(assets[request.url]));return;}
    if (!request.url.startsWith('/cgi-bin/extra/')) {
        response.setHeader('Content-Type','text/html'); response.end(html); return;
    }
    let input = '';
    for await (const chunk of request) input += chunk;
    const action = new URL(request.url, 'http://localhost').searchParams.get('action');
    const send=result=>{response.setHeader('Content-Type','text/html');response.end('<div class="ajax-json-box"><div class="ajax-json-content"><pre>Content-Type: application/json\n\n'+escaped(JSON.stringify(result))+'</pre></div></div>');};
    assert(!request.url.includes('11111111111111111111111111111111'));
    if(action==='inspect'&&failInspect){response.setHeader('Content-Type','text/html');response.end('<p>Login required</p>');return;}
    let result;
    if(!daemonRunning&&['status','discover-start','discover-stop'].includes(action)){send({success:false,error:'gateway is not running or control socket is unavailable'});return;}
    if (['read','save','check','backups','restore','inspect','attributes','history-presets','availability-presets','availability-status'].includes(action)) {
        const child = spawnSync(binary, ['--config',config,'--web-config',action], {input, encoding:'utf8'});
        result = JSON.parse(child.stdout);
        if(action==='read'&&legacyFrontends)delete result.config.frontends.sqlite;
        if(action==='read'&&legacyBaudrate!==null)result.config.serial.baudrate=legacyBaudrate;
    } else if(action==='availability-test') {assert.equal(request.method,'POST');assert(JSON.parse(input).rule.webhook);result={success:true,message:'synthetic webhook test delivered'};}
    else if (['status','discover-start','discover-stop'].includes(action)) {
        if (action === 'discover-start') {assert.equal(request.method,'POST'); active = true;}
        if (action === 'discover-stop') {assert.equal(request.method,'POST'); active = false;}
        result = {success:true, connected:true, active, paused:active&&gatt!==null, remaining_s:active?30:0, reports:8, devices:observations, overflow:0, error:'', radio:{scanning,scan_suppressed:!scanning,txadv_active:txadv,gatt}};
    } else if (action === 'command') {
        assert.equal(request.method,'POST');
        assert.equal(request.headers['content-type'],'application/json');
        const command=JSON.parse(input);commands.push(command);
        if(!daemonRunning||failCommand){send({success:false,error:daemonRunning?'Command failed: <timeout>':'gateway is not running or control socket is unavailable'});return;}
        if(commandGate)await commandGate;
        if(command.command==='txadv-start'){scanning=false;txadv=true;active=false;}
        if(command.command==='txadv-stop')txadv=false;
        if(command.command==='scan-start'){scanning=true;txadv=false;}
        if(command.command==='scan-stop')scanning=false;
        let confirmation={confirmation:'stack-accepted'};
        if(command.command==='gatt-open'){
            suspendedRadio={scanning,txadv};scanning=false;txadv=false;gatt={mac:command.mac,mtu:200,remaining_ms:60000};
            confirmation={confirmation:'connected',session:sessionToken,connection:gatt,host_managed:true};
        }
        if(command.command==='gatt-close'){
            assert.equal(command.session,sessionToken);({scanning,txadv}=suspendedRadio);gatt=null;suspendedRadio=null;
            confirmation={confirmation:'disconnected'};
        }
        if(command.command==='gatt'){
            if(command.session)assert.equal(command.session,sessionToken);
            if(['exchange','patch'].includes(command.operation)){
                assert.equal(command.uuid,'1F1F');assert.equal(command.value,'55');assert.equal(command.prefix,'55');
                assert.equal(command.codec,'cfg');assert.equal(command.offset,1);
                if(command.operation==='patch'){
                    assert.equal(command.write_offset,1);assert.equal(command.write_prefix,undefined);
                    if(command.patch.flg2)Object.assign(atcConfig.flg2,command.patch.flg2);
                }
                const flags=0x10+(atcConfig.flg2.bt5phy?0x20:0)+(atcConfig.flg2.longrange?0x40:0);
                confirmation={confirmation:'application-notification',notifications:[{handle:42,value:'554385'+flags.toString(16).padStart(2,'0').toUpperCase()+'00002804A9313104B4',decoded:JSON.parse(JSON.stringify(atcConfig))}]};
                if(command.operation==='patch')confirmation.patch_verified=true;
            }
        }
        result={success:true,result:confirmation,radio:{scanning,scan_suppressed:!scanning,txadv_active:txadv,gatt}};
    } else if (action === 'persist') {persistCalls++;result=failPersist?{success:false,error:'simulated flash failure'}:{success:true};}
    else if (action === 'restart') {restarts++;result={success:true};}
    else result={success:true};
    send(result);
});

async function hoverPacketField(page,key,{nested=false,value=false}={}) {
    await page.locator('#bbPacket').scrollIntoViewIfNeeded();
    const point=await page.evaluate(async({key,nested,value})=>{
        const editor=ace.edit('bbPacket'), lines=editor.getValue().split('\n');
        const row=lines.findIndex(line=>line.trimStart().startsWith(JSON.stringify(key)+':')&&(!nested||line.startsWith('    ')));
        if(row<0)throw new Error('Missing JSON field: '+key);
        editor.scrollToLine(row,true,false);
        await new Promise(resolve=>requestAnimationFrame(resolve));
        await new Promise(resolve=>requestAnimationFrame(resolve));
        const column=value?lines[row].indexOf(':')+3:lines[row].indexOf('"')+2;
        const result=editor.renderer.textToScreenCoordinates(row,column);
        return {x:result.pageX+2,y:result.pageY+7};
    },{key,nested,value});
    await page.mouse.move(point.x,point.y);
}

async function waitOutput(page,id,text) {
    await page.waitForFunction(({id,text})=>window.ace&&document.getElementById(id).classList.contains('ace_editor')&&ace.edit(id).getValue().includes(text),{id,text});
}

async function checkOutput(page,id,mode='json',readOnly=true) {
    const state=await page.evaluate(id=>{
        const editor=ace.edit(id);
        return {readOnly:editor.getReadOnly(),mode:editor.session.getMode().$id,value:editor.getValue(),width:editor.renderer.scroller.clientWidth,height:editor.renderer.scroller.clientHeight};
    },id);
    assert.equal(state.readOnly,readOnly);
    assert.equal(state.mode,'ace/mode/'+mode);
    assert(state.width>0&&state.height>0);
    return mode==='json'?JSON.parse(state.value):state.value;
}

async function setEditor(page,id,text) {
    await page.locator('#'+id+'.ace_editor').waitFor();
    await page.evaluate(({id,text})=>ace.edit(id).setValue(text,-1),{id,text});
}

async function confirmCommand(page) {
    await page.locator('#bbConfirm').waitFor({state:'visible'});
    const request=await checkOutput(page,'bbConfirmRequest');
    assert.deepEqual(await checkOutput(page,'bbCommandRequest'),request);
    await page.getByRole('button',{name:'Continue',exact:true}).click();
    return request;
}

if(process.env.BLE_WEB_UI_SERVE_ONLY){
    server.listen(Number(process.env.BLE_WEB_UI_PORT||8766),'127.0.0.1',()=>console.log('Isolated gateway UI: http://127.0.0.1:'+server.address().port));
    for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.close(()=>{fs.rmSync(directory,{recursive:true,force:true});process.exit(0);}));
} else (async () => {
    try {
        await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
        browser = await chromium.launch({headless:true});
        const page = await browser.newPage({viewport:{width:1280,height:900}});
        const errors=[];page.on('pageerror',error=>errors.push(error.message));
        await page.goto('http://127.0.0.1:'+server.address().port);
        await page.getByRole('status').filter({hasText:'Configuration loaded'}).waitFor();
        assert(await page.locator('#bbStartup').evaluate(node=>node.open));
        assert.equal(await page.locator('#bbStartupActions input[type=submit]').inputValue(),'Save startup/storage and restart if running');
        assert.equal(await page.locator('#bbStartup #bbStartupAdvanced').count(),1);
        assert.equal(await page.getByRole('button',{name:'Default',exact:true}).isVisible(),false);
        await page.locator('#bbStartupActions input[type=submit]').click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        assert.match(await page.locator('#bbConfirmText').textContent(),/Freetz restarts a running service/);
        await page.getByRole('button',{name:'Cancel',exact:true}).filter({visible:true}).click();
        assert.equal(await page.locator('#bbInitialBaudrate').evaluate(element=>element.tagName),'SELECT');
        assert.deepEqual(await page.locator('#bbInitialBaudrate option').evaluateAll(options=>options.map(option=>option.value)),baudrates);
        assert.equal(await page.locator('#bbInitialBaudrate').inputValue(),'2000000');
        const preserved=await page.evaluate(markup=>{
            const select=new DOMParser().parseFromString(markup,'text/html').getElementById('bbInitialBaudrate');
            return {value:select.value,values:[...select.options].map(option=>option.value)};
        },startupFields(500000));
        assert.equal(preserved.value,'500000');
        assert.deepEqual(preserved.values,[...baudrates,'500000']);
        assert.equal(await page.locator('#bbRestart').count(),0);
        assert.equal(await page.locator('#bbAdd').locator('..').getByRole('searchbox').count(),0);
        await page.getByRole('button',{name:'Add manually',exact:true}).click();
        await page.getByLabel('MAC',{exact:true}).fill('AABBCCDDEEFF');
        assert.match(await page.locator('#bbDeviceApply').getAttribute('title'),/page draft/);
        assert.match(await page.locator('#bbDeviceCancel').getAttribute('title'),/Other unsaved page changes/);
        assert.equal(await page.locator('#bbAvailabilityRules > legend').textContent(),'Availability monitoring');
        await page.getByRole('button',{name:'Add rule',exact:true}).click();
        const availabilityRule=page.locator('[data-availability-rule="0"]');
        assert.equal(await availabilityRule.getByLabel('Enabled',{exact:true}).isChecked(),false);
        assert.equal(await availabilityRule.locator('[data-parameter="device.rules[].stale_after_s"]').inputValue(),'600');
        assert.equal(await availabilityRule.locator('.bbAvailabilityWebhook').evaluate(element=>element.open),true);
        assert.equal(await availabilityRule.locator('[data-parameter="device.rules[].message"]').evaluate(element=>element.tagName),'TEXTAREA');
        await availabilityRule.locator('[data-parameter="device.rules[].message"]').fill('Synthetic custom notification');
        await availabilityRule.locator('[data-parameter="device.rules[].tgs"]').fill('warning,test');
        await page.locator('#bbAvailabilityRules').getByRole('button',{name:'Device availability status',exact:true}).click();
        await page.locator('#bbAvailabilityStatus.ace_editor').waitFor();
        assert.equal(await page.evaluate(()=>ace.edit('bbAvailabilityStatus').getReadOnly()),true);
        assert.equal(await page.evaluate(()=>ace.edit('bbAvailabilityStatus').session.getMode().$id),'ace/mode/json');
        await availabilityRule.getByLabel('Enabled',{exact:true}).check();
        await availabilityRule.getByLabel('HTTPS URL',{exact:true}).fill('http://localhost/topic');
        await page.getByRole('button',{name:'Add to configuration draft',exact:true}).click();
        await page.locator('#bbDeviceError').filter({hasText:'requires HTTPS'}).waitFor();
        await availabilityRule.getByLabel('HTTPS URL',{exact:true}).fill('https://ntfy.example.org/synthetic');
        await availabilityRule.getByRole('button',{name:'Test webhook',exact:true}).click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'HTTPS webhook test delivered'}).waitFor();
        await availabilityRule.getByLabel('Enabled',{exact:true}).uncheck();
        await page.getByRole('button',{name:'Add rule',exact:true}).click();
        assert.equal(await page.locator('[data-availability-rule]').count(),2);
        await page.locator('[data-availability-rule="1"]').getByRole('button',{name:'Remove rule',exact:true}).click();
        assert.equal(await page.locator('[data-availability-rule]').count(),1);
        await page.getByLabel('Device name',{exact:true}).fill('Test } </pre><script>window.injected=true</script>');
        await page.getByLabel('Bindkey (32 hexadecimal digits)',{exact:true}).fill('1'.repeat(32));
        await page.getByRole('button',{name:'Show bindkey',exact:true}).click();
        assert.equal(await page.getByLabel('Bindkey (32 hexadecimal digits)',{exact:true}).getAttribute('type'),'text');
        await page.getByRole('button',{name:'Hide bindkey',exact:true}).click();
        assert.equal(await page.getByLabel('Bindkey (32 hexadecimal digits)',{exact:true}).getAttribute('type'),'password');
        await page.getByRole('button',{name:'Add to configuration draft',exact:true}).click();
        await page.locator('#bbDeviceDialog').waitFor({state:'hidden'});
        assert.equal(JSON.parse(spawnSync(binary,['--config',config,'--web-config','read'],{encoding:'utf8'}).stdout).config.devices.length,0);
        await page.locator('#bbDevices tr').first().getByRole('button',{name:'Edit',exact:true}).click();
        await page.getByLabel('Device name',{exact:true}).fill('Discard this draft');
        await page.getByRole('button',{name:'Cancel',exact:true}).click();
        assert.match(await page.locator('#bbDevices').textContent(),/Test }/);
        assert.equal(await page.locator('#bbDirty').textContent(),'Unsaved changes');
        await page.getByRole('button',{name:'Save configuration',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'Saved.'}).waitFor();
        assert.equal(persistCalls,1);
        failPersist=true;
        await page.getByRole('button',{name:'Save configuration',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'persistence not confirmed'}).waitFor();
        assert.equal(await page.locator('#bbDirty').textContent(),'Unsaved changes');
        failPersist=false;
        await page.getByRole('button',{name:'Save configuration',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'Saved.'}).waitFor();
        assert.equal(persistCalls,3);
        assert.equal(restarts,0);
        assert.equal(await page.evaluate(()=>window.injected), undefined);
        await page.getByRole('tab',{name:'Settings',exact:true}).click();
        const baudrate=page.getByLabel('Baudrate',{exact:true});
        assert.equal(await baudrate.evaluate(element=>element.tagName),'SELECT');
        assert.deepEqual(await baudrate.locator('option').evaluateAll(options=>options.map(option=>option.value)),baudrates);
        await baudrate.selectOption('2000000');
        assert.deepEqual((await page.locator('#bbFrontends [data-frontend]').evaluateAll(groups=>groups.map(group=>group.dataset.frontend))).sort(),['influx','matter','mqtt','mysensors','sqlite'],'Rebuild the native daemon before testing: cargo build --manifest-path make/pkgs/ble2uart_gateway/src/Cargo.toml --offline --no-default-features');
        assert.equal(await page.locator('#bbFrontendNotice').count(),0);
        for(const group of await page.locator('#bbFrontends [data-frontend]').all()) {
            assert.equal(await group.locator(':scope > .bbGrid > .bbField').first().getByRole('checkbox').count(),1);
            assert.match(await group.locator(':scope > .bbGrid > .bbField').first().textContent(),/^Enabled/);
            assert.equal(await group.evaluate(node=>getComputedStyle(node).borderLeftWidth),'4px');
        }
        const sqlite=page.locator('#bbFrontends [data-frontend="sqlite"]');
        const sqliteFields=sqlite.locator(':scope > .bbGrid');
        await sqliteFields.getByRole('button',{name:'Help: Batch size',exact:true}).click();
        assert.match(await page.locator('#bbParameterText').textContent(),/SQLite counts advertisement frames/);
        await page.getByRole('button',{name:'Close',exact:true}).click();
        assert(await page.locator('#bbSettings input,#bbSettings select,#bbSettings textarea').evaluateAll(controls=>controls.every(control=>control.title.length>12)));
        assert.equal(await sqliteFields.getByLabel('Enabled',{exact:true}).isChecked(),false);
        await sqliteFields.getByLabel('Enabled',{exact:true}).check();
        await sqliteFields.getByLabel('Database file (absolute local path)',{exact:true}).fill(path.join(directory,'readings.sqlite3'));
        await sqliteFields.getByLabel('Batch size',{exact:true}).fill('128');
        await sqliteFields.getByLabel('Queue capacity',{exact:true}).fill('2048');
        await sqliteFields.getByLabel('Flush interval (ms)',{exact:true}).fill('250');
        await sqliteFields.getByLabel('SQLite busy timeout (ms)',{exact:true}).fill('1500');
        const maintenance=page.locator('#bbHistoryMaintenance');
        assert.equal(await maintenance.evaluate(element=>element.tagName),'DETAILS');
        assert.equal(await maintenance.evaluate(element=>element.open),false);
        await maintenance.locator(':scope > summary').click();
        assert.equal(await maintenance.getByLabel('Default counter history',{exact:true}).inputValue(),'discard');
        assert.equal(await maintenance.getByLabel('Enabled',{exact:true}).isChecked(),false);
        await maintenance.getByLabel('Enabled',{exact:true}).check();
        assert.equal(await page.locator('.bbHistoryPolicy').count(),5);
        const temperaturePolicy=page.locator('.bbHistoryPolicy').first();
        assert.equal(await temperaturePolicy.getByLabel('Attribute',{exact:true}).inputValue(),'temperature');
        assert.equal(await temperaturePolicy.locator('[data-tier]').count(),6);
        await temperaturePolicy.getByRole('button',{name:'Add age band',exact:true}).click();
        assert.equal(await temperaturePolicy.locator('[data-tier]').count(),7);
        await temperaturePolicy.getByRole('button',{name:'Temperature preset',exact:true}).click();
        await page.waitForFunction(()=>document.querySelectorAll('.bbHistoryPolicy:first-of-type [data-tier]').length===6);
        await page.locator('#bbHistoryPolicies').getByRole('button',{name:'Add policy',exact:true}).click();
        const contactPolicy=page.locator('.bbHistoryPolicy').last();
        await contactPolicy.getByLabel('Attribute',{exact:true}).fill('opened');
        await contactPolicy.getByLabel('MAC (empty = all devices)',{exact:true}).fill('AABBCCDDEEFF');
        await contactPolicy.getByRole('button',{name:'Battery preset',exact:true}).click();
        await page.getByRole('button',{name:'Validate',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'boolean/discrete attributes must use keep_all'}).waitFor();
        await contactPolicy.getByLabel('History mode',{exact:true}).selectOption('keep_all');
        assert.equal(await page.locator('#bbSettings #bbAvailabilityRules').count(),0);
        assert.equal(await page.locator('#bbAutomation').count(),0);
        assert.doesNotMatch(await page.locator('#bbSettings').textContent(),/ITTT|Availability rules|Rules \(not executed\)|Webhook configuration/);
        assert.match(await page.locator('#bbFilterState').textContent(),/filtering is ON/);
        assert.match(await page.locator('#bbFilterCommon').textContent(),/does not reload saved edits/);
        assert.match(await page.locator('#bbWhitelist').getAttribute('title'),/no wildcard/);
        assert.equal(await page.locator('#bbMacFilters #bbWhitelist').count(),1);
        assert.equal(await page.locator('#bbMacFilters #bbBlacklist').count(),1);
        assert.equal(await page.locator('#bbMacFilters').getByLabel('Filter registered devices in ESP32',{exact:true}).count(),1);
        assert.match(await page.locator('#bbMacFilterLists label').first().textContent(),/Include MACs/);
        await page.locator('#bbWhitelist').fill('A4:C1:38, A4C1383406CE');
        await page.locator('#bbBlacklist').fill('54:EF:44');
        assert.match(await page.locator('#bbFilterState').textContent(),/Both lists are populated/);
        await page.getByRole('button',{name:'Validate',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'mutually exclusive'}).waitFor();
        assert.equal(await page.locator('#bbWhitelist').inputValue(),'A4:C1:38, A4C1383406CE');
        await page.locator('#bbBlacklist').fill('');
        await page.getByLabel('Filter registered devices in ESP32',{exact:true}).uncheck();
        assert.match(await page.locator('#bbFilterState').textContent(),/filtering is OFF/);
        await page.screenshot({path:'/tmp/ble-filters.png',fullPage:true});
        await page.getByRole('button',{name:'Validate',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'Configuration is valid'}).waitFor();
        await page.getByRole('tab',{name:'YAML',exact:true}).click();
        await page.locator('#bbYaml.ace_editor').waitFor();
        assert(await page.evaluate(()=>ace.edit('bbYaml').getValue().includes('filter_known_devices: false')));
        assert.match(await page.evaluate(()=>ace.edit('bbYaml').getValue()),/\bbaudrate: 2000000\b/);
        assert.match(await page.evaluate(()=>ace.edit('bbYaml').getValue()),/whitelist:\s+- A4:C1:38\s+- A4C1383406CE/);
        assert.equal(await page.evaluate(()=>ace.edit('bbYaml').session.getMode().$id),'ace/mode/yaml');
        await page.getByRole('tab',{name:'Discovery',exact:true}).click();
        await page.locator('#bbFound tr').filter({hasText:'ATC sensor'}).waitFor();
        await page.getByRole('button',{name:'Start discovery',exact:true}).click();
        await page.locator('#bbDiscoveryStatus').filter({hasText:'Scanning'}).waitFor();
        await page.getByLabel('Filter by OUI vendor',{exact:true}).selectOption('Telink Semiconductor');
        assert.equal(await page.locator('#bbFound tr').count(),1);
        const dirtyBeforeInspect=await page.locator('#bbDirty').textContent();
        await page.getByRole('button',{name:'Inspect',exact:true}).click();
        await page.locator('#bbPacket.ace_editor').waitFor();
        await page.waitForFunction(()=>ace.edit('bbPacket').getValue().includes('"decode_status": "ok"'));
        const inspected=JSON.parse(await page.evaluate(()=>ace.edit('bbPacket').getValue()));
        assert.equal(inspected.wire_format,'bt_home_v2');
        assert.equal(inspected.measurements.opened,'1');
        assert.equal(inspected.measurements.switch,'0');
        assert.equal(inspected.measurements.packet_id,'138');
        assert.equal(inspected.measurements.battery_v,'2.83');
        assert.equal(inspected.phy,'phy_raw=0x33 primary=Coded secondary=Coded');
        assert.equal(await page.evaluate(()=>ace.edit('bbPacket').session.getMode().$id),'ace/mode/json');
        assert.equal(await page.evaluate(()=>ace.edit('bbPacket').getReadOnly()),true);
        assert(await page.evaluate(()=>ace.edit('bbPacket').session.getFoldWidgetRange(0).end.row>0));
        assert.equal(await page.locator('#bbPacketError').isVisible(),false);
        assert.equal(await page.locator('#bbPacketFields dt').count(),16);
        assert.equal(await page.locator('#bbPacketHelp').evaluate(element=>element.open),false);
        await hoverPacketField(page,'addr_type');
        await page.locator('#bbFieldTooltip').waitFor({state:'visible'});
        assert.match(await page.locator('#bbFieldTooltip').textContent(),/0 = public, 1 = random/);
        const tooltipBounds=await page.locator('#bbFieldTooltip').boundingBox();
        assert(tooltipBounds.x>=8&&tooltipBounds.y>=8&&tooltipBounds.x+tooltipBounds.width<=1272&&tooltipBounds.y+tooltipBounds.height<=892);
        await page.evaluate(()=>document.activeElement.blur());
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#bbFieldTooltip').isVisible(),false);
        await hoverPacketField(page,'vendor');
        await page.locator('#bbFieldTooltip').waitFor({state:'visible'});
        assert.match(await page.locator('#bbFieldTooltip').textContent(),/separate from decoded.mac_vendor/);
        assert.match(await page.locator('#bbFieldTooltip').textContent(),/bit 0x02/);
        await page.screenshot({path:'/tmp/ble-field-tooltip.png'});
        await hoverPacketField(page,'vendor',{value:true});
        assert.equal(await page.locator('#bbFieldTooltip').isVisible(),false);
        await hoverPacketField(page,'packet_id',{nested:true});
        await page.locator('#bbFieldTooltip').waitFor({state:'visible'});
        assert.match(await page.locator('#bbFieldTooltip').textContent(),/independent of Discovery count/);
        await page.evaluate(()=>ace.edit('bbPacket').session.setScrollTop(0));
        await page.locator('#bbFieldTooltip').waitFor({state:'hidden'});
        await hoverPacketField(page,'phy');
        await page.locator('#bbFieldTooltip').waitFor({state:'visible'});
        assert.match(await page.locator('#bbFieldTooltip').textContent(),/Coded packet can carry BTHome v2/);
        await page.mouse.move(0,0);
        assert.equal(await page.locator('#bbFieldTooltip').isVisible(),false);
        await page.locator('#bbPacketHelpTitle').focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#bbPacketHelp').evaluate(element=>element.open),true);
        assert.match(await page.locator('#bbPacketFields [data-field="decode_error"] + dd').textContent(),/web response was not the expected API envelope/);
        await page.locator('#bbPacketHelpTitle').click();
        assert.deepEqual(JSON.parse(await page.evaluate(()=>ace.edit('bbPacket').getValue())),inspected);
        assert.equal(await page.locator('#bbDirty').textContent(),dirtyBeforeInspect);
        await page.screenshot({path:'/tmp/ble-inspect-desktop.png',fullPage:true});
        await page.locator('#bbPacketDetails > summary').click();
        await page.locator('#bbPacketDetails > summary').click();
        await page.getByRole('tab',{name:'Devices',exact:true}).click();
        await page.getByRole('tab',{name:'Discovery',exact:true}).click();
        assert(await page.locator('#bbPacket .ace_scroller').evaluate(element=>element.clientWidth>0&&element.clientHeight>0));
        await page.setViewportSize({width:390,height:844});
        await page.locator('#bbPacketHelpTitle').click();
        assert.equal(await page.locator('#bbPacketFields dt').first().isVisible(),true);
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
        await page.screenshot({path:'/tmp/ble-inspect-mobile.png',fullPage:true});
        await page.locator('#bbPacketHelpTitle').click();
        await page.setViewportSize({width:1280,height:900});
        failInspect=true;
        await page.getByRole('button',{name:'Inspect',exact:true}).click();
        await page.waitForFunction(()=>ace.edit('bbPacket').getValue().includes('"decode_status": "failed"'));
        assert.equal(JSON.parse(await page.evaluate(()=>ace.edit('bbPacket').getValue())).decode_error,'Invalid response or session expired');
        assert.match(await page.locator('#bbPacketNotice').textContent(),/does not establish.*BLE packet is invalid/);
        failInspect=false;
        await page.getByLabel('Filter by OUI vendor',{exact:true}).selectOption('');
        await page.locator('#bbFound tr').filter({hasText:'Other sensor'}).getByRole('button',{name:'Inspect',exact:true}).click();
        await page.waitForFunction(()=>ace.edit('bbPacket').getValue().includes('"decode_status": "unsupported_format"'));
        assert.equal(await page.locator('#bbPacketNotice').isVisible(),false);
        assert.equal(JSON.parse(await page.evaluate(()=>ace.edit('bbPacket').getValue())).mac,'54EF44001122');
        await page.getByLabel('Filter by OUI vendor',{exact:true}).selectOption('Telink Semiconductor');
        await page.getByRole('button',{name:'Inspect',exact:true}).click();
        await page.waitForFunction(()=>ace.edit('bbPacket').getValue().includes('"decode_status": "ok"'));
        assert.equal(await page.locator('#bbPacket.ace_editor').count(),1);
        await page.getByRole('button',{name:'Configure',exact:true}).click();
        assert.equal(await page.getByLabel('MAC',{exact:true}).inputValue(),'A4C1383406CE');
        const supportedAttributes=JSON.parse(spawnSync(binary,['--web-config','attributes'],{encoding:'utf8'}).stdout).attributes;
        assert.deepEqual(await page.locator('#bbDeviceFields [data-parameter="device.expose[].attribute"]').evaluateAll(inputs=>inputs.map(input=>input.value)).then(values=>values.sort()),Object.keys(inspected.measurements).filter(name=>supportedAttributes.includes(name)).sort());
        await page.getByRole('button',{name:'Add to configuration draft',exact:true}).click();
        await page.locator('#bbDeviceDialog').waitFor({state:'hidden'});
        assert.equal(await page.getByRole('tab',{name:'Devices',exact:true}).getAttribute('aria-selected'),'true');
        assert.match(await page.locator('#bbMsg').textContent(),/Save configuration/);
        await page.getByRole('tab',{name:'Discovery',exact:true}).click();
        assert.equal(await page.locator('#bbFound .bbActions').first().evaluate(element=>getComputedStyle(element).gap),'8px');
        await page.getByRole('button',{name:'Remove',exact:true}).filter({visible:true}).first().click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await page.getByRole('button',{name:'Configure',exact:true}).click();
        await page.getByRole('button',{name:'Add to configuration draft',exact:true}).click();
        await page.locator('#bbDeviceDialog').waitFor({state:'hidden'});
        await page.getByRole('tab',{name:'Discovery',exact:true}).click();
        await page.getByRole('button',{name:'Stop',exact:true}).click();
        await page.locator('#bbDiscoveryStatus').filter({hasText:'Idle'}).waitFor();
        await page.getByRole('tab',{name:'Commands',exact:true}).click();
        await waitOutput(page,'bbRadio','"scanning": true');
        assert.equal((await checkOutput(page,'bbRadio')).connected,true);
        await page.locator('#bbAtcRead').click();
        assert.equal(await page.locator('#bbCmd_mac').evaluate(input=>input.validity.valueMissing),true);
        assert.equal(await page.locator('#bbConfirm').isVisible(),false);
        assert.equal(commands.length,0);
        await page.locator('#bbCommandType').selectOption('gatt-session');
        await page.locator('#bbAtcRead').click();
        assert.equal(await page.locator('#bbCommandType').inputValue(),'gatt-session');
        assert.equal(await page.locator('#bbCmd_session').evaluate(input=>input.validity.valueMissing),true);
        assert.equal(commands.length,0);
        await page.locator('#bbCommandType').selectOption('diagnostic');
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Cancel',exact:true}).filter({visible:true}).click();
        assert.equal(commands.length,0);
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbCommandResult','stack-accepted');
        const commandResult=await checkOutput(page,'bbCommandResult');
        assert.equal(commandResult.success,true);
        assert.equal(commandResult.result.confirmation,'stack-accepted');
        assert.equal(commandResult.radio.scanning,true);
        await page.locator('#bbCommandResult').click();
        await page.keyboard.press('Control+Home');
        await page.keyboard.type('changed');
        assert.deepEqual(await checkOutput(page,'bbCommandResult'),commandResult);
        assert.deepEqual(commands.at(-1),{command:'diagnostic',name:'info',pin:0});
        await page.locator('#bbCommandType').selectOption('gatt');
        await page.locator('#bbCmd_mac').fill('AABBCCDDEEFF');
        await page.locator('#bbCmd_operation').selectOption('write');
        await page.locator('#bbCmd_handle').fill('42');
        await page.locator('#bbCmd_value').fill('0102');
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbCommandResult','stack-accepted');
        assert.deepEqual(commands.at(-1),{command:'gatt',mac:'AABBCCDDEEFF',addr_type:0,coded:false,operation:'write',handle:42,uuid:'',value:'0102',timeout_ms:10000});
        await page.locator('#bbCmd_addr_type').fill('1');
        await page.locator('#bbCmd_coded').check();
        await page.locator('#bbCmd_timeout_ms').fill('3000');
        const beforePreset=commands.length;
        await page.locator('#bbAtcRead').click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        assert.equal(commands.length,beforePreset,'direct actions must await confirmation');
        assert.equal(await page.locator('#bbCmd_addr_type').inputValue(),'1');
        assert.equal(await page.locator('#bbCmd_coded').isChecked(),true);
        assert.equal(await page.locator('#bbCmd_timeout_ms').inputValue(),'3000');
        const preservedRequest=await confirmCommand(page);
        await waitOutput(page,'bbCommandResult','application-notification');
        assert.equal(commands.length,beforePreset+1,'ATC read must send without a second Send command click');
        assert.deepEqual(commands.at(-1),preservedRequest);
        assert.equal(commands.at(-1).addr_type,1);
        assert.equal(commands.at(-1).coded,true);
        assert.equal(commands.at(-1).timeout_ms,3000);
        await page.locator('#bbCommandType').selectOption('gatt-open');
        await page.locator('#bbCmd_mac').fill('AABBCCDDEEFF');
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbCommandResult','host_managed');
        await page.waitForFunction(()=>document.getElementById('bbCommandType').value==='gatt-session');
        assert.equal(await page.locator('#bbCmd_session').inputValue(),sessionToken);
        assert.equal(scanning,false);
        await page.locator('#bbCommandType').selectOption('gatt');
        await page.locator('#bbCmd_mac').fill('112233445566');
        await page.locator('#bbAtcRead').click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        assert.equal(await page.locator('#bbCommandType').inputValue(),'gatt','an explicit peer must not become the active session peer');
        assert.equal(await page.locator('#bbCmd_mac').inputValue(),'112233445566');
        assert.equal((await checkOutput(page,'bbConfirmRequest')).mac,'112233445566');
        await page.getByRole('button',{name:'Cancel',exact:true}).filter({visible:true}).click();
        await page.locator('#bbCommandType').selectOption('gatt-session');
        const preparedCount=commands.length;
        await page.locator('#bbAtcRead').click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        assert.equal(commands.length,preparedCount,'direct reads must not bypass confirmation');
        assert.equal(await page.locator('#bbCmd_uuid').inputValue(),'1F1F');
        assert.equal(await page.locator('#bbCmd_value').inputValue(),'55');
        assert.equal(await page.locator('#bbCmd_offset').inputValue(),'1');
        await confirmCommand(page);
        await waitOutput(page,'bbCommandResult','application-notification');
        assert.equal(commands.length,preparedCount+1);
        assert.equal(commands.at(-1).session,sessionToken);
        await page.locator('#bbAtcPatch').click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        assert.equal(await page.locator('#bbCmd_write_offset').inputValue(),'1');
        const defaultPatch=await confirmCommand(page);
        assert.deepEqual(defaultPatch.patch,{flg2:{bt5phy:true,longrange:true}});
        await waitOutput(page,'bbCommandResult','patch_verified');
        assert.equal(commands.at(-1).operation,'patch','ATC patch must send without a second Send command click');
        assert.deepEqual(await checkOutput(page,'bbCmd_patch','json',false),defaultPatch.patch);
        assert.equal(await page.locator('#bbCmd_patch').evaluate(element=>element.tagName),'DIV');
        const customPatch={flg2:{bt5phy:false,longrange:true}};
        await setEditor(page,'bbCmd_patch',JSON.stringify(customPatch));
        const beforeCancelledPatch=commands.length;
        await page.locator('#bbAtcPatch').click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        assert.deepEqual((await checkOutput(page,'bbConfirmRequest')).patch,customPatch);
        await page.getByRole('button',{name:'Cancel',exact:true}).filter({visible:true}).click();
        assert.equal(commands.length,beforeCancelledPatch);
        assert.deepEqual(await checkOutput(page,'bbCmd_patch','json',false),customPatch,'cancelling must retain edited patch JSON');
        await setEditor(page,'bbCmd_patch','{invalid');
        const beforeInvalid=commands.length;
        await page.locator('#bbAtcPatch').click();
        await page.locator('#bbCommandPatchError').filter({hasText:'Enter a nonempty JSON object'}).waitFor();
        assert.equal(commands.length,beforeInvalid);
        assert.equal(await page.locator('#bbConfirm').isVisible(),false);
        assert.equal(await page.evaluate(()=>ace.edit('bbCmd_patch').session.getAnnotations()[0].type),'error');
        assert.equal(await page.locator('#bbCmd_uuid').evaluate(input=>input.form.id),'bbCommandForm');
        assert(await page.evaluate(()=>document.getElementById('bbInitialBaudrate').form.checkValidity()),'invalid live JSON must not block Freetz startup settings');
        for(const invalid of ['[]','null','{}']){
            await setEditor(page,'bbCmd_patch',invalid);
            await page.getByRole('button',{name:'Send command',exact:true}).click();
            await page.locator('#bbCommandPatchError').filter({hasText:'Enter a nonempty JSON object'}).waitFor();
            assert.equal(commands.length,beforeInvalid);
        }
        await setEditor(page,'bbCmd_patch',JSON.stringify(customPatch));
        await page.locator('#bbAtcPatch').click();
        const patchedRequest=await confirmCommand(page);
        await waitOutput(page,'bbCommandResult','patch_verified');
        assert.equal((await checkOutput(page,'bbCommandResult')).result.patch_verified,true);
        assert.equal((await checkOutput(page,'bbCommandResult')).result.notifications[0].decoded.flg2.bt5phy,false);
        assert.deepEqual(patchedRequest.patch,customPatch,'direct ATC patch must not reset user edits to the Coded PHY preset');
        assert.deepEqual(commands.at(-1),patchedRequest);
        let releaseCommand;
        commandGate=new Promise(resolve=>{releaseCommand=resolve;});
        try {
            const started=page.waitForRequest(request=>request.url().includes('action=command'));
            await page.locator('#bbAtcRead').click();
            await confirmCommand(page);
            await started;
            for(const id of ['bbCommandSend','bbAtcRead','bbAtcPatch','bbCommandType'])assert(await page.locator('#'+id).isDisabled());
            const received=commands.length;
            await page.evaluate(()=>{document.getElementById('bbAtcRead').click();document.getElementById('bbCommandSend').click();});
            assert.equal(commands.length,received,'pending commands must not be submitted twice');
        } finally {releaseCommand();commandGate=null;}
        await waitOutput(page,'bbCommandResult','application-notification');
        await page.locator('#bbAtcPatch').click();
        await confirmCommand(page);
        await waitOutput(page,'bbCommandResult','patch_verified');
        assert.equal(scanning,false,'GATT operations must keep the session connected');
        await page.setViewportSize({width:390,height:844});
        await page.locator('#bbCmd_patch').scrollIntoViewIfNeeded();
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'GATT patch controls must fit mobile');
        await page.setViewportSize({width:1280,height:900});
        await page.locator('#bbCommandType').selectOption('gatt-close');
        assert.equal(await page.locator('#bbCmd_session').inputValue(),sessionToken);
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbCommandResult','disconnected');
        await waitOutput(page,'bbRadio','"gatt": null');
        assert.equal(scanning,true);
        assert.equal(restarts,0);
        await page.locator('#bbCommandType').selectOption('gatt-session');
        await page.locator('#bbCmd_session').fill('B'.repeat(32));
        await page.locator('#bbAtcRead').click();
        await page.locator('#bbConfirm').waitFor({state:'visible'});
        assert.equal(await page.locator('#bbCommandType').inputValue(),'gatt-session');
        assert.equal(await page.locator('#bbCmd_session').inputValue(),'B'.repeat(32),'presets must retain explicitly pasted CLI tokens');
        assert.equal((await checkOutput(page,'bbConfirmRequest')).session,'B'.repeat(32));
        await page.getByRole('button',{name:'Cancel',exact:true}).filter({visible:true}).click();
        daemonRunning=false;
        await page.locator('#bbCommandType').selectOption('gatt');
        await page.locator('#bbCmd_mac').fill('AABBCCDDEEFF');
        await page.locator('#bbAtcRead').click();
        await confirmCommand(page);
        await waitOutput(page,'bbCommandResult','gateway is not running');
        await checkOutput(page,'bbCommandResult','text');
        await waitOutput(page,'bbRadio','gateway is not running');
        assert.equal(restarts,0,'commands must not implicitly start or restart the service');
        assert.equal(daemonRunning,false);
        daemonRunning=true;
        await page.locator('#bbRadioRefresh').click();
        await waitOutput(page,'bbRadio','"scanning": true');
        await page.locator('#bbCommandType').selectOption('txadv-start');
        await page.locator('#bbCmd_data').fill('020106');
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbRadio','"scanning": false');
        assert.equal(commands.at(-1).command,'txadv-start');
        await page.locator('#bbCommandType').selectOption('txadv-stop');
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbRadio','"txadv_active": false');
        assert.equal(scanning,false);
        await page.locator('#bbCommandType').selectOption('scan-start');
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbRadio','"scanning": true');
        failCommand=true;
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbCommandResult','Command failed: <timeout>');
        assert.equal(await checkOutput(page,'bbCommandResult','text'),'Command failed: <timeout>');
        await page.locator('#bbMsg').filter({hasText:'Command failed:'}).waitFor();
        failCommand=false;
        await page.getByRole('button',{name:'Send command',exact:true}).click();
        await page.getByRole('button',{name:'Continue',exact:true}).click();
        await waitOutput(page,'bbCommandResult','stack-accepted');
        await checkOutput(page,'bbCommandResult');
        await page.getByRole('tab',{name:'YAML',exact:true}).click();
        await page.getByRole('tab',{name:'Commands',exact:true}).click();
        await waitOutput(page,'bbRadio','"scanning": true');
        await checkOutput(page,'bbRadio');
        await checkOutput(page,'bbCommandResult');
        await page.screenshot({path:'/tmp/ble-web-desktop.png',fullPage:true});
        await page.setViewportSize({width:390,height:844});
        await checkOutput(page,'bbRadio');
        await checkOutput(page,'bbCommandResult');
        await page.screenshot({path:'/tmp/ble-web-mobile.png',fullPage:true});
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
        await page.getByRole('tab',{name:'Devices',exact:true}).click();
        assert.equal(await page.locator('#bbDevices tr').count(),2);
        await page.getByRole('button',{name:'Save configuration',exact:true}).click();
        await page.locator('#bbMsg').filter({hasText:'Saved.'}).waitFor();
        const saved = JSON.parse(spawnSync(binary,['--config',config,'--web-config','read'],{encoding:'utf8'}).stdout);
        assert.equal(saved.config.devices.length,2);
        assert.equal(saved.config.scanner.filter_known_devices,false);
        assert.equal(saved.config.serial.baudrate,2000000);
        assert.deepEqual(saved.config.scanner.whitelist,['A4:C1:38','A4C1383406CE']);
        assert.deepEqual(saved.config.scanner.blacklist,[]);
        const {maintenance:savedMaintenance,...savedSqlite}=saved.config.frontends.sqlite;
        assert.deepEqual(savedSqlite,{enabled:true,path:path.join(directory,'readings.sqlite3'),batch_size:128,queue_capacity:2048,flush_interval_ms:250,busy_timeout_ms:1500});
        assert.equal(savedMaintenance.enabled,true);
        assert.equal(savedMaintenance.policies.length,6);
        assert.equal(savedMaintenance.policies.at(-1).mode,'keep_all');
        assert.equal(savedMaintenance.policies.at(-1).mac,'AABBCCDDEEFF');
        assert.equal(restarts,0);
        legacyFrontends=true;
        legacyBaudrate=500000;
        const legacy=await browser.newPage({locale:'it-IT'});
        legacy.on('pageerror',error=>errors.push(error.message));
        await legacy.goto('http://127.0.0.1:'+server.address().port);
        await legacy.locator('#bbMsg').filter({hasText:'Configuration loaded'}).waitFor();
        legacyFrontends=false;
        legacyBaudrate=null;
        await legacy.getByRole('tab',{name:'Settings',exact:true}).click();
        assert.equal(await legacy.getByLabel('Baudrate',{exact:true}).inputValue(),'500000');
        assert.deepEqual(await legacy.getByLabel('Baudrate',{exact:true}).locator('option').evaluateAll(options=>options.map(option=>option.value)),[...baudrates,'500000']);
        assert.equal(await legacy.locator('#bbDirty').textContent(),'');
        assert.match(await legacy.locator('#bbFrontendNotice').textContent(),/SQLite.*Aggiorna\/ricompila/);
        assert.equal(await legacy.locator('#bbFrontends [data-frontend="sqlite"]').count(),0);
        assert.equal(await legacy.locator('#bbFrontends [data-frontend]').count(),4);
        await legacy.close();
        for(const asset of ['ace.js','mode-json.js']){
            const fallback=await browser.newPage();
            fallback.on('pageerror',error=>errors.push(error.message));
            const blocked='**/ace/'+asset;
            await fallback.route(blocked,route=>route.abort());
            await fallback.goto('http://127.0.0.1:'+server.address().port);
            await fallback.locator('#bbMsg').filter({hasText:'Configuration loaded'}).waitFor();
            await fallback.getByRole('tab',{name:'Commands',exact:true}).click();
            await fallback.locator('#bbMsg').filter({hasText:'Cannot load editor asset:'}).waitFor();
            assert.equal(JSON.parse(await fallback.locator('#bbRadio').textContent()).connected,true);
            assert.equal(commands.length>0,true);
            const commandsBefore=commands.length;
            await fallback.getByRole('button',{name:'Send command',exact:true}).click();
            await fallback.locator('#bbMsg').filter({hasText:'Cannot load editor asset:'}).waitFor();
            assert.equal(commands.length,commandsBefore);
            await fallback.locator('#bbCommandType').selectOption('gatt');
            await fallback.locator('#bbCmd_mac').fill('AABBCCDDEEFF');
            await fallback.locator('#bbAtcRead').click();
            await fallback.locator('#bbMsg').filter({hasText:'Cannot load editor asset:'}).waitFor();
            assert.equal(commands.length,commandsBefore,'direct actions must not send without the Ace confirmation preview');
            await fallback.locator('#bbAtcPatch').click();
            await fallback.locator('#bbMsg').filter({hasText:'Cannot load editor asset:'}).waitFor();
            assert.equal(commands.length,commandsBefore,'patches must not send when Ace cannot load');
            await fallback.getByRole('tab',{name:'Discovery',exact:true}).click();
            await fallback.locator('#bbFound tr').filter({hasText:'ATC sensor'}).getByRole('button',{name:'Inspect',exact:true}).click();
            await fallback.locator('#bbPacketError').filter({hasText:asset}).waitFor();
            await fallback.waitForFunction(()=>document.getElementById('bbPacket').textContent.includes('"decode_status": "ok"'));
            assert.equal(JSON.parse(await fallback.locator('#bbPacket').textContent()).measurements.packet_id,'138');
            await fallback.locator('#bbPacketHelpTitle').click();
            assert.match(await fallback.locator('#bbPacketFields [data-field="vendor"] + dd').textContent(),/Offline IEEE OUI/);
            await fallback.locator('#bbPacketHelpTitle').click();
            await fallback.unroute(blocked);
            await fallback.getByRole('tab',{name:'Commands',exact:true}).click();
            await waitOutput(fallback,'bbRadio','"connected": true');
            await checkOutput(fallback,'bbRadio');
            await checkOutput(fallback,'bbCmd_patch','json',false);
            await fallback.getByRole('tab',{name:'Discovery',exact:true}).click();
            await fallback.locator('#bbFound tr').filter({hasText:'ATC sensor'}).getByRole('button',{name:'Inspect',exact:true}).click();
            await fallback.locator('#bbPacket.ace_editor').waitFor();
            await fallback.waitForFunction(()=>ace.edit('bbPacket').getValue().includes('"decode_status": "ok"'));
            assert.equal(await fallback.locator('#bbPacketError').isVisible(),false);
            await fallback.getByRole('tab',{name:'YAML',exact:true}).click();
            await fallback.locator('#bbYaml.ace_editor').waitFor();
            assert(await fallback.evaluate(()=>ace.edit('bbYaml').getValue().includes('filter_known_devices: false')));
            assert.equal(await fallback.locator('#bbDirty').textContent(),'');
            await fallback.close();
        }
        for(const [locale,tab,send,guide] of [['de-DE','Befehle','Befehl senden','Hilfe zu Advertisement-Feldern'],['it-IT','Comandi','Invia comando','Guida ai campi dell’advertisement'],['fr-FR','Commandes','Envoyer la commande','Guide des champs advertisement'],['es-ES','Comandos','Enviar comando','Guía de campos del advertisement']]){
            const localized=await browser.newPage({locale});
            await localized.goto('http://127.0.0.1:'+server.address().port);
            await localized.locator('#bbMsg').filter({hasText:'Configuration loaded'}).waitFor();
            assert.equal(await localized.locator('#bbPacketFields dt').count(),16);
            assert.equal(await localized.locator('#bbPacketHelpTitle').textContent(),guide);
            assert(await localized.locator('#bbDeviceApply').getAttribute('title'));
            await localized.getByRole('tab',{name:'Discovery',exact:true}).click();
            await localized.locator('#bbOpenFilters').click();
            assert.equal(await localized.getByRole('tab',{name:'Settings',exact:true}).getAttribute('aria-selected'),'true');
            assert.equal(await localized.evaluate(()=>document.activeElement.id),'bbMacFilters');
            assert.notEqual(await localized.locator('#bbFilterCommon').textContent(),await page.locator('#bbFilterCommon').textContent());
            await localized.setViewportSize({width:390,height:844});
            assert(await localized.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
            await localized.getByRole('tab',{name:tab,exact:true}).click();
            assert(await localized.getByRole('button',{name:send,exact:true}).getAttribute('title'));
            await localized.locator('#bbCommandType').selectOption('gatt-open');
            await localized.locator('#bbCmd_mac').fill('AABBCCDDEEFF');
            await localized.locator('#bbAtcPatch').click();
            await localized.locator('#bbConfirm').waitFor({state:'visible'});
            const fieldLabels=await localized.locator('#bbCommandFields label').evaluateAll(labels=>labels.map(label=>({text:label.firstChild.textContent,title:label.querySelector('input,textarea,select').title})));
            assert(fieldLabels.every(({text,title})=>text&&title&&!text.includes('undefined')&&!title.includes('undefined')));
            assert.equal(await localized.locator('#bbCmd_write_offset').inputValue(),'1');
            assert.equal((await checkOutput(localized,'bbConfirmRequest')).operation,'patch');
            await localized.getByRole('button',{name:'Cancel',exact:true}).filter({visible:true}).click();
            await checkOutput(localized,'bbCmd_patch','json',false);
            await localized.close();
        }
        assert.deepEqual(errors,[]);
        console.log('UI PASS: direct ATC read/patch submission with confirmation, editable Ace JSON patch, read-only Ace request/confirmation/response views, custom-patch preservation, duplicate-send blocking, stopped-service errors without implicit restart; persistent GATT open/operate/close, token propagation, JSON validation, localized tooltips and mobile controls; existing startup/runtime baudrate, five frontends, SQLite, discovery, inspection/tooltips, MAC filters, YAML, asset fallback/retry and TXADV regressions preserved.');
    } finally {
        if (browser) await browser.close();
        server.close();
        fs.rmSync(directory,{recursive:true,force:true});
    }
})().catch(error=>{console.error(error);process.exitCode=1;});