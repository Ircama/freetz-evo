//! AES-128-CCM for the encrypted advertisement formats.
//!
//! The four tunnels of the reference (`AtcMiCodec`, `MiLikeCodec`,
//! `BtHomeCodec`, `BtHomeV2Codec`) use the same primitive with different
//! nonces, and this module reproduces them exactly:
//!
//! | codec | nonce | AAD |
//! |---|---|---|
//! | `atc_mi` | `mac[::-1]` + `len+3` + `0x16` + UUID + `0xBD` | `0x11` |
//! | `mi_like` | `mac[::-1]` + device_id + counter + count_id | `0x11` |
//! | `bt_home` | `mac` + UUID + count_id | `0x11` |
//! | `bt_home_v2` | `mac` + UUID + DevInfo + count_id | none |
//!
//! Two of them reverse the MAC and two do not, the AAD differs, the nonce
//! length differs (11, 12 or 13 bytes) and so does the position of the counter
//! inside the frame: this is why the scheme is a table and not a function.
//!
//! The MIC (4 bytes) is verified by the AEAD: a wrong bindkey or a corrupted
//! frame is an error, never a plausible measurement.

use aes::Aes128;
use ccm::aead::{Aead, KeyInit, Payload};
use ccm::{Ccm, consts::{U11, U12, U13, U4}};

/// The AAD used by every codec except `bt_home_v2`.
const AAD: &[u8] = &[0x11];
/// The marker byte that opens an encrypted ATC payload.
const ATC_MARKER: u8 = 0xBD;

type AesCcm11 = Ccm<Aes128, U4, U11>;
type AesCcm12 = Ccm<Aes128, U4, U12>;
type AesCcm13 = Ccm<Aes128, U4, U13>;

#[derive(Debug)]
pub struct Error(pub String);

impl std::fmt::Display for Error {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for Error {}

type Result<T> = std::result::Result<T, Error>;

/// Everything a codec needs besides the frame itself.
#[derive(Clone, Debug)]
pub struct Params {
    /// The MAC in *display* order (`A4:C1:38:B3:32:6C` -> `A4C138B3326C`).
    pub mac: [u8; 6],
    pub bindkey: [u8; 16],
}

impl Params {
    /// The bindkey of a device as configured, or `None` when the device is
    /// known but its key is missing: an encrypted frame then simply cannot be
    /// decoded, which is the reference behaviour too.
    pub fn new(mac: &[u8; 6], bindkey: &[u8; 16]) -> Self {
        Params { mac: *mac, bindkey: *bindkey }
    }

    fn reversed_mac(&self) -> [u8; 6] {
        let mut out = [0u8; 6];
        for (index, byte) in self.mac.iter().rev().enumerate() {
            out[index] = *byte;
        }
        out
    }
}

/// Decrypt one frame. `uuid` is the service UUID in wire order (e.g. `1a18`),
/// `device_id`, `counter` and `header_length` come from the frame itself and
/// are only used by the codecs that include them in the nonce.
pub struct Frame<'a> {
    pub codec: &'a str,
    pub uuid: [u8; 2],
    /// Bytes before the tunnel data (mi_like: device_id + counter = 3).
    pub header: &'a [u8],
    pub data: &'a [u8],
}

pub fn decrypt(params: &Params, frame: &Frame<'_>) -> Result<Vec<u8>> {
    match frame.codec {
        "atc_mi" => decrypt_atc_mi(params, frame),
        "mi_like" => decrypt_mi_like(params, frame),
        "bt_home" => decrypt_bt_home(params, frame),
        "bt_home_v2" => decrypt_bt_home_v2(params, frame),
        other => Err(Error(format!("unknown codec {other}"))),
    }
}

pub fn encrypt(params: &Params, frame: &Frame<'_>) -> Result<Vec<u8>> {
    let mut nonce = [0u8; 13];
    let (nonce_length, counter_length, aad) = match frame.codec {
        "atc_mi" => {
            if frame.data.len() > 247 { return Err(Error("ATC payload too large".into())); }
            nonce[..6].copy_from_slice(&params.reversed_mac());
            nonce[6] = (frame.data.len() + 8) as u8;
            nonce[7] = 0x16;
            nonce[8..10].copy_from_slice(&frame.uuid);
            nonce[10] = ATC_MARKER;
            (11, 0, AAD)
        }
        "mi_like" => {
            if frame.header.len() != 3 || frame.data.len() < 3 { return Err(Error("invalid MiLike header/counter".into())); }
            nonce[..6].copy_from_slice(&params.reversed_mac());
            nonce[6..9].copy_from_slice(frame.header);
            nonce[9..12].copy_from_slice(&frame.data[..3]);
            (12, 3, AAD)
        }
        "bt_home" | "bt_home_v2" => {
            if frame.data.len() < 4 { return Err(Error("missing BTHome counter".into())); }
            nonce[..6].copy_from_slice(&params.mac);
            nonce[6..8].copy_from_slice(&frame.uuid);
            if frame.codec == "bt_home_v2" {
                nonce[8] = *frame.header.first().ok_or_else(|| Error("missing DevInfo".into()))?;
                nonce[9..13].copy_from_slice(&frame.data[..4]);
                (13, 4, &[][..])
            } else {
                nonce[8..12].copy_from_slice(&frame.data[..4]);
                (12, 4, AAD)
            }
        }
        other => return Err(Error(format!("unknown codec {other}"))),
    };
    let input = Payload { msg: &frame.data[counter_length..], aad };
    let sealed = match nonce_length {
        11 => {
            let mut bytes = [0; 11];
            bytes.copy_from_slice(&nonce[..11]);
            AesCcm11::new_from_slice(&params.bindkey).unwrap().encrypt(&bytes.into(), input)
        }
        12 => {
            let mut bytes = [0; 12];
            bytes.copy_from_slice(&nonce[..12]);
            AesCcm12::new_from_slice(&params.bindkey).unwrap().encrypt(&bytes.into(), input)
        }
        _ => AesCcm13::new_from_slice(&params.bindkey).unwrap().encrypt(&nonce.into(), input),
    }.map_err(|_| Error("CCM encryption failed".into()))?;
    let mut output = Vec::new();
    if frame.codec == "atc_mi" { output.push(ATC_MARKER); }
    output.extend_from_slice(&sealed[..sealed.len() - 4]);
    output.extend_from_slice(&frame.data[..counter_length]);
    output.extend_from_slice(&sealed[sealed.len() - 4..]);
    Ok(output)
}

/// `custom_enc` / `atc1441_enc`: the frame is `0xBD + ciphertext + MIC`, the
/// nonce embeds the length of that frame plus three, and the plaintext is what
/// the plain ATC structures decode.
fn decrypt_atc_mi(params: &Params, frame: &Frame<'_>) -> Result<Vec<u8>> {
    let data = frame.data;
    if data.len() < 5 {
        return Err(Error(format!("atc_mi: not an encrypted frame ({} bytes)", data.len())));
    }
    let length = data.len() + 3;
    if length > 0xFF {
        return Err(Error(format!("atc_mi: impossible frame length {length}")));
    }
    let mut nonce = [0u8; 11];
    nonce[..6].copy_from_slice(&params.reversed_mac());
    nonce[6] = length as u8;
    nonce[7] = 0x16;
    nonce[8..10].copy_from_slice(&frame.uuid);
    nonce[10] = data[0];
    let ciphertext = &data[1..data.len() - 4];
    let mic = &data[data.len() - 4..];
    let mut message = Vec::with_capacity(ciphertext.len() + mic.len());
    message.extend_from_slice(ciphertext);
    message.extend_from_slice(mic);
    let cipher = AesCcm11::new_from_slice(&params.bindkey)
        .map_err(|_| Error("atc_mi: bad key length".into()))?;
    cipher
        .decrypt(&nonce.into(), Payload { msg: &message, aad: AAD })
        .map_err(|_| Error("atc_mi: authentication failed (wrong bindkey?)".into()))
}

/// `mi_like`: `ciphertext + count_id(3) + MIC(4)`, the payload keeps the
/// counter in front, as the reference returns `count_id + message`.
fn decrypt_mi_like(params: &Params, frame: &Frame<'_>) -> Result<Vec<u8>> {
    let data = frame.data;
    if data.len() < 7 || frame.header.len() != 3 {
        return Err(Error(format!("mi_like: frame too short ({} bytes)", data.len())));
    }
    let mut nonce = [0u8; 12];
    nonce[..6].copy_from_slice(&params.reversed_mac());
    nonce[6..8].copy_from_slice(&frame.header[..2]);
    nonce[8] = frame.header[2];
    nonce[9..12].copy_from_slice(&data[data.len() - 7..data.len() - 4]);
    let ciphertext = &data[..data.len() - 7];
    let mic = &data[data.len() - 4..];
    let mut message = Vec::with_capacity(ciphertext.len() + mic.len());
    message.extend_from_slice(ciphertext);
    message.extend_from_slice(mic);
    let cipher = AesCcm12::new_from_slice(&params.bindkey)
        .map_err(|_| Error("mi_like: bad key length".into()))?;
    let mut plain = cipher
        .decrypt(&nonce.into(), Payload { msg: &message, aad: AAD })
        .map_err(|_| Error("mi_like: authentication failed (wrong bindkey?)".into()))?;
    let mut payload = Vec::with_capacity(plain.len() + 3);
    payload.extend_from_slice(&nonce[9..12]);
    payload.append(&mut plain);
    Ok(payload)
}

/// `bt_home_enc`: `ciphertext + count_id(4) + MIC(4)`, nonce without the
/// reversed MAC.
fn decrypt_bt_home(params: &Params, frame: &Frame<'_>) -> Result<Vec<u8>> {
    bt_home_common(params, frame, false)
}

/// `bt_home_v2`: same as `bt_home` with the `DevInfo` byte in the nonce and no
/// AAD at all.
fn decrypt_bt_home_v2(params: &Params, frame: &Frame<'_>) -> Result<Vec<u8>> {
    bt_home_common(params, frame, true)
}

fn bt_home_common(params: &Params, frame: &Frame<'_>, version2: bool) -> Result<Vec<u8>> {
    let data = frame.data;
    if data.len() < 8 {
        return Err(Error(format!("bt_home: frame too short ({} bytes)", data.len())));
    }
    let count_id = &data[data.len() - 8..data.len() - 4];
    let mut nonce = [0u8; 13];
    nonce[..6].copy_from_slice(&params.mac);
    nonce[6..8].copy_from_slice(&frame.uuid);
    let length = if version2 {
        nonce[8] = frame.header.first().copied().unwrap_or(0);
        nonce[9..13].copy_from_slice(count_id);
        13
    } else {
        nonce[8..12].copy_from_slice(count_id);
        12
    };
    let ciphertext = &data[..data.len() - 8];
    let mic = &data[data.len() - 4..];
    let mut message = Vec::with_capacity(ciphertext.len() + mic.len());
    message.extend_from_slice(ciphertext);
    message.extend_from_slice(mic);
    let aad = if version2 { &[][..] } else { AAD };
    let plain = if version2 {
        let mut nonce13 = [0u8; 13];
        nonce13.copy_from_slice(&nonce);
        let cipher = AesCcm13::new_from_slice(&params.bindkey)
            .map_err(|_| Error("bt_home_v2: bad key length".into()))?;
        cipher
            .decrypt(&nonce13.into(), Payload { msg: &message, aad })
            .map_err(|_| Error("bt_home_v2: authentication failed".into()))?
    } else {
        let mut nonce12 = [0u8; 12];
        nonce12.copy_from_slice(&nonce[..12]);
        let cipher = AesCcm12::new_from_slice(&params.bindkey)
            .map_err(|_| Error("bt_home: bad key length".into()))?;
        cipher
            .decrypt(&nonce12.into(), Payload { msg: &message, aad })
            .map_err(|_| Error("bt_home: authentication failed".into()))?
    };
    debug_assert!(length == 12 || length == 13);
    let mut payload = Vec::with_capacity(plain.len() + 4);
    payload.extend_from_slice(count_id);
    payload.extend_from_slice(&plain);
    Ok(payload)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `tools/gen_crypto_vectors.py` encrypts known payloads with the real MAC
    /// and bindkey of the user's sensors through the reference encoder: this
    /// test decrypts them again, so a wrong nonce, a wrong AAD or a wrong MIC
    /// position shows up immediately.
    const VECTORS: &str = include_str!("../tests/crypto_vectors.json");

    fn bytes(text: &str) -> Vec<u8> {
        (0..text.len() / 2)
            .map(|index| u8::from_str_radix(&text[index * 2..index * 2 + 2], 16).unwrap_or(0))
            .collect()
    }

    fn decode(hex: &str) -> [u8; 6] {
        let raw = bytes(hex);
        let mut out = [0u8; 6];
        out.copy_from_slice(&raw[..6]);
        out
    }

    #[test]
    fn every_reference_frame_decrypts_to_the_recorded_payload() {
        let document: serde_json::Value =
            serde_json::from_str(VECTORS).expect("crypto vectors are JSON");
        let vectors = document["vectors"].as_array().expect("vectors array");
        let mut checked = 0;
        for vector in vectors {
            let text = |key: &str| vector[key].as_str().unwrap_or_default().to_string();
            let bindkey = bytes(&text("bindkey"));
            let mut key = [0u8; 16];
            key.copy_from_slice(&bindkey);
            let params = Params::new(&decode(&text("mac")), &key);

            let blob = bytes(&text("blob"));
            let codec = text("codec");
            // The advertisement frame is: [UUID (2)] [optional header] tunnel.
            // `bt_home_v2` carries its one byte DevInfo right after the UUID and
            // that byte is part of the nonce, so it must not be part of the
            // encrypted data.
            let (uuid, header, data): ([u8; 2], Vec<u8>, &[u8]) = match codec.as_str() {
                "mi_like" => {
                    let header = blob[..3].to_vec();
                    ([0x95, 0xFE], header, &blob[3..])
                }
                "bt_home_v2" => (([blob[0], blob[1]]), blob[2..3].to_vec(), &blob[3..]),
                _ => ([blob[0], blob[1]], Vec::new(), &blob[2..]),
            };
            let frame = Frame { codec: &codec, uuid, header: &header, data };
            let payload = decrypt(&params, &frame)
                .unwrap_or_else(|error| panic!("{codec} {}: {error}", text("blob")));
            assert_eq!(
                crate::codec::value::hex(&payload),
                text("payload"),
                "{codec} {}",
                text("blob")
            );
            let encoded = encrypt(&params, &Frame { codec: &codec, uuid, header: &header, data: &payload }).unwrap();
            assert_eq!(encoded, data, "reference encoder mismatch: {codec}");
            checked += 1;
        }
        assert_eq!(checked, 40, "all the vectors must be exercised");
    }

    #[test]
    fn a_wrong_bindkey_is_rejected_not_guessed() {
        let document: serde_json::Value =
            serde_json::from_str(VECTORS).expect("crypto vectors are JSON");
        let vector = &document["vectors"][0];
        let blob = bytes(vector["blob"].as_str().unwrap_or_default());
        let mut key = [0u8; 16];
        key.copy_from_slice(&bytes(vector["bindkey"].as_str().unwrap_or_default()));
        key[0] ^= 0xFF;
        let params = Params::new(&decode(vector["mac"].as_str().unwrap_or_default()), &key);
        let frame = Frame {
            codec: "atc_mi",
            uuid: [blob[0], blob[1]],
            header: &[],
            data: &blob[2..],
        };
        let error = decrypt(&params, &frame).expect_err("a wrong key must not decrypt");
        assert!(error.0.contains("authentication"), "{}", error.0);
    }
}
