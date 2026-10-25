"""Lossless, session-scoped compressed blocks; legacy TEXT remains readable."""
import hashlib
import struct
import zlib

MAGIC=b'PAPZ1'
LIMIT=100000

def setup(db):
    db.execute('CREATE TABLE IF NOT EXISTS telemetry_blocks (session TEXT, digest BLOB, data BLOB, PRIMARY KEY(session,digest))')
    db.create_function('telemetry_raw_size',1,raw_size)

def raw_size(data):
    return struct.unpack('>I',data[5:9])[0] if isinstance(data,bytes) and data.startswith(MAGIC) else len(data.encode() if isinstance(data,str) else data)

def encode(db,session,text):
    raw=text.encode()
    if len(raw)<512:return text
    # Content-defined boundaries retain sharing even when timestamps shift offsets.
    blocks=[];start=0;rolling=0
    for i,b in enumerate(raw):
        rolling=((rolling<<1)+b)&0xffffffff
        n=i+1-start
        if n>=512 and ((rolling&1023)==0 or n>=4096):
            blocks.append(raw[start:i+1]);start=i+1;rolling=0
    if start<len(raw):blocks.append(raw[start:])
    hashes=[]
    for block in blocks:
        digest=hashlib.sha256(block).digest();hashes.append(digest)
        db.execute('INSERT OR IGNORE INTO telemetry_blocks VALUES (?,?,?)',(session,digest,zlib.compress(block)))
    return MAGIC+struct.pack('>I',len(raw))+b''.join(hashes)

def decode(db,session,data):
    if isinstance(data,str):return data
    if not data.startswith(MAGIC) or (len(data)-9)%32:raise ValueError('Invalid telemetry encoding')
    expected=raw_size(data)
    if expected>LIMIT:raise ValueError('Telemetry record too large')
    result=[]
    for i in range(9,len(data),32):
        digest=data[i:i+32]
        row=db.execute('SELECT data FROM telemetry_blocks WHERE session=? AND digest=?',(session,digest)).fetchone()
        if row is None:raise ValueError('Missing telemetry block')
        decoder=zlib.decompressobj();block=decoder.decompress(row[0],4097)
        if not decoder.eof or len(block)>4096 or hashlib.sha256(block).digest()!=digest:raise ValueError('Invalid telemetry block')
        result.append(block)
    raw=b''.join(result)
    if len(raw)!=expected:raise ValueError('Invalid telemetry length')
    return raw.decode()

def read_rows(db,session):
    return [(seq,received,kind,decode(db,session,data)) for seq,received,kind,data in db.execute('SELECT seq,received,type,data FROM events WHERE session=? ORDER BY seq',(session,)).fetchall()]

def block_size(db,session=None):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='telemetry_blocks'").fetchone():return 0
    sql='SELECT COALESCE(SUM(LENGTH(data)+LENGTH(digest)),0) FROM telemetry_blocks'
    return db.execute(sql+(' WHERE session=?' if session is not None else ''),(session,) if session is not None else ()).fetchone()[0]

def collect(db):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='telemetry_blocks'").fetchone():
        db.execute('DELETE FROM telemetry_blocks WHERE session NOT IN (SELECT DISTINCT session FROM events)')
