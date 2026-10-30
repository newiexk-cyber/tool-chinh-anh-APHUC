import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.drive_manager import get_drive_service

service = get_drive_service('config/credentials.json')
target_folder_id = '1ORVUU2QIBvKj0RnqJ1qN7QPB89_IFP1F'

try:
    old_resp = service.files().list(
        q=f"'{target_folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType)",
        pageSize=1000,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    print('SUCCESS! Files in target:', len(old_resp.get('files', [])))
except Exception as e:
    print('ERROR IN TARGET QUERY:', e)

