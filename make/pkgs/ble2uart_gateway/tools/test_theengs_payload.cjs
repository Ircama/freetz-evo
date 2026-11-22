const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../files/root/usr/lib/cgi-bin/ble2uart_gateway.cgi'), 'utf8');
const start = source.indexOf('\tfunction theengsReverseHex(');
const end = source.indexOf('\n\tlet theengsInput=', start);
assert(start >= 0 && end > start);
const context = {TextDecoder};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

function payload(data) {
    return JSON.parse(JSON.stringify(context.theengsPayload({mac: 'A4C1383406CE', name: 'Friendly label', rssi: -60, data})));
}

const complete = '0B094154435F333430364345';
const shortened = '0408415443';
for (const [data, key, expected, uuid] of [
    ['0D16D2FC40008A0C0E0B10001101', 'servicedata', '40008a0c0e0b10001101', '0xfcd2'],
    ['072078563412AABB', 'servicedata', 'aabb', '0x12345678'],
    ['1321000102030405060708090A0B0C0D0E0FAABB', 'servicedata', 'aabb', '0f0e0d0c0b0a09080706050403020100'],
    ['05FF5900AABB', 'manufacturerdata', '5900aabb', undefined],
]) {
    const before = payload(complete + data);
    const after = payload(data + complete);
    assert.deepEqual(after, before);
    assert.equal(after.name, 'ATC_3406CE');
    assert.equal(after[key], expected);
    assert.equal(after.servicedatauuid, uuid);
    for (const names of [complete + shortened, shortened + complete]) {
        assert.equal(payload(data + names).name, 'ATC_3406CE');
    }
    assert.equal(payload(data + '1A09415443').name, 'Friendly label');
}
assert.equal(payload(complete), null);
assert.equal(payload(''), null);
assert.equal(payload('05FF5900AABB05163412AABB' + complete).manufacturerdata, '5900aabb');
console.log('Theengs web payload: name order, all AD data types, complete-name priority, malformed suffix and first-data precedence passed');