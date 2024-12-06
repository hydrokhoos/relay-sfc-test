from typing import Optional
from ndn.app import NDNApp
from ndn.encoding import Name, InterestParam, BinaryStr, FormalName
import subprocess as sp
import os
import requests
import tempfile
from send_msg import call_service

service_name = Name.normalize(os.environ['SERVICE_NAME'])

SEGMENT_SIZE = 8000
FRESHNESS_PERIOD = 1000
TIMEOUT = '10000'
IPFS_URL = 'http://ipfs:5001/api/v0'

app = NDNApp()


def get_ipfs_content(cid: str) -> Optional[bytes]:
    """ IPFSからコンテンツを取得し、バイナリデータを返す """
    print("get_ipfs_content")
    url_get = f'{IPFS_URL}/cat'
    params_get = {
        'arg': cid,
        'progress': 'false'
    }
    response = requests.post(url_get, params=params_get, stream=True)

    if response.ok:
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content += chunk
        return content
    else:
        print(f"Error fetching IPFS content: {response.status_code}")
        return None


def add_ipfs_content(content: bytes) -> Optional[str]:
    """ バイナリデータをIPFSに追加し、CIDを返す """
    print("add_ipfs_content")
    url_add = f'{IPFS_URL}/add'
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(content)
        tmp_file.flush()
        with open(tmp_file.name, 'rb') as file_to_add:
            files = {'file': file_to_add}
            response = requests.post(url_add, files=files)

            if response.ok:
                res_add = response.json()
                return res_add['Hash']
            else:
                print(f"Error adding content to IPFS: {response.status_code}")
                return None


@app.route(service_name)
def on_interest(name: FormalName, param: InterestParam, _app_param: Optional[BinaryStr]):
    print(f'>> I: {Name.to_str(name)}')
    trimmed_name = name[1:]

    if Name.to_str(trimmed_name[:1]) != '/ipfs':
        print(f"<< I: {Name.to_str(trimmed_name)}")
        base_cid = sp.run(['ndnpeek', Name.to_str(trimmed_name), '-fp', '-w', TIMEOUT], capture_output=True, text=True).stdout.strip()
        print(f">> D: {Name.to_str(trimmed_name)}\n{base_cid}")
    else:
        base_cid = Name.to_str(trimmed_name[1:])[1:]

    # IPFSからコンテンツを取得
    content = get_ipfs_content(base_cid)
    if not content:
        print("Failed to retrieve IPFS content.")
        return
    print(f"File saved. CID: {base_cid}")

    # コンテンツに処理を加える（グレースケール変換）
    # byte_stream = BytesIO(content)
    # img = Image.open(byte_stream)
    # gray_img = img.convert('L')
    # buffer = BytesIO()
    # gray_img.save(buffer, format='JPEG')
    # content = buffer.getvalue()
    with open(f'/vol/{base_cid}', 'wb') as f:
        f.write(content)
    content = call_service(base_cid)
    print('Service completed.')

    # IPFSに新しいコンテンツを追加
    new_cid = add_ipfs_content(content)
    if not new_cid:
        print("Failed to add content to IPFS.")
        return

    print(f"File added. CID: {new_cid}")

    # データをNDNネットワークに返す
    app.put_data(name, new_cid.encode(), freshness_period=FRESHNESS_PERIOD)


if __name__ == '__main__':
    print(f'My Service Name: {Name.to_str(service_name)}')
    try:
        app.run_forever()
    finally:
        sp.run('nlsrc -R $ROUTER_PREFIX -k withdraw $MY_SERVICE_NAME', shell=True)
