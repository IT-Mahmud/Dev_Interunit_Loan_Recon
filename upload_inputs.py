import requests

# Upload Steel file
with open('Input_Files/Interunit Steel.xlsx', 'rb') as f:
    files = {'file': f}
    data = {'sheet_name': 'Sheet7'}
    r = requests.post('http://localhost:5000/api/upload', files=files, data=data)
    print('Steel upload:', r.json())

# Upload GeoTex file
with open('Input_Files/Interunit GeoTex.xlsx', 'rb') as f:
    files = {'file': f}
    data = {'sheet_name': 'Sheet8'}
    r = requests.post('http://localhost:5000/api/upload', files=files, data=data)
    print('GeoTex upload:', r.json()) 