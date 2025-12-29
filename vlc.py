import requests

password = "pwd"
url = "http://localhost:8080/requests/playlist.json"
management_url = 'http://localhost:8080/requests/status.xml'
response = requests.get(url, auth=('', password))
print(response.json()['children'][0])

# To add a file to the playlist:
# command=in_enqueue adds to list; command=in_play plays immediately
new_media = 'file:///Users/azeraliyev/Downloads/Big_Buck_Bunny_360_10s_1MB.mp4'
requests.get(f"{management_url}?command=in_enqueue&input={new_media}", auth=('', password))

# To skip:
requests.get(f"{management_url}?command=pl_next", auth=('', password))

