# 2026.03.05 Save project info into json files.
# Need to set environment variables before running this script.
# set  AUTH_TYPE=BASIC or set  AUTH_TYPE=OAUTH
# set  JAMA_URL=https://your-jama-instance.com
# set  JAMA_USERNAME=your_username  (Only for BASIC auth)
# set  JAMA_PASSWORD=your_password  (Only for BASIC auth)
# if auth type is not BASIC, then set the following environment variables instead of above 3 variables.
# set JAMA_CLIENT_ID=XXX
# set JAMA_CLIENT_SECRET=XXX

# $ python SaveJamaItems.py
# v1.1 - 2026.03.11 Added attachement file download functionality. If an item is of type "ATTACHMENT", the script will attempt to download the file using the Jama API and save it to the local "json" folder. If the file is not found (e.g., it has been deleted), the script will skip it and print a message. For other errors during download, it will print a detailed error message with a stack trace for troubleshooting.
#
import time
from datetime import datetime, date, time, timedelta
from py_jama_rest_client.client import JamaClient
import json, os

class JamaAccess(JamaClient):

    def __init__(self):

        print('Started')
        now = datetime.now()
        print(now)
        AUTH_TYPE           = os.environ.get('AUTH_TYPE')

        if AUTH_TYPE == 'BASIC':
            import urllib3
            from urllib3.exceptions import InsecureRequestWarning
            urllib3.disable_warnings(InsecureRequestWarning)

            print('Using BASIC authentication')
            
            JAMA_URL           = os.environ.get('JAMA_URL')
            CREDENTIALS        = (os.environ.get('JAMA_USERNAME'), os.environ.get('JAMA_PASSWORD'))
            super().__init__(JAMA_URL, credentials=CREDENTIALS, verify=False,allowed_results_per_page=50)

        else:
            print('Using OAUTH authentication')
            JAMA_URL           = os.environ.get('JAMA_URL')
            # 認証情報は環境変数にある前提
            CREDENTIALS        = (os.environ.get('JAMA_CLIENT_ID'), os.environ.get('JAMA_CLIENT_SECRET')) 
            super().__init__(JAMA_URL, credentials=CREDENTIALS, oauth=True)

def main():
    
    jama_access = JamaAccess()

    ret_json = jama_access.get_projects()
    #print ("プロジェクト一覧リスト :")

    #print(json.dumps(ret_json, indent=4, sort_keys=True, separators=(',', ': ')))
    #カレントフォルダ配下にjsonフォルダを作成して、そこにプロジェクトごとにアイテムタイプ、アイテム、リレーションの情報を保存する。
    if not os.path.exists(".\\json"):
        os.makedirs(".\\json")

    #print ("\n アイテムタイプを調べます")
    type_list = []
    for ret_type in jama_access.get_item_types():
        type_list.append(ret_type)
        #print(json.dumps(ret_type, indent=4, sort_keys=True, separators=(',', ': ')))
    # JSONファイルに保存
    output_filename = f".\\json\\project_itemtypes.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(type_list, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    print(f"itemTypeを {output_filename} に保存しました。")

    # Get the list of projects from Jama
    # The client will return to us a JSON array of Projects, where each project is a JSON object.
    pick_lists = jama_access.get_pick_lists()
    output_filename = f".\\json\\pick_lists.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(pick_lists, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    print(f"pickListsを {output_filename} に保存しました。")
    #
    for picklist in pick_lists:
        pick_list_options = jama_access.get_pick_list_options(picklist['id'])
        output_filename = f".\\json\\pick_list_{picklist['id']}_options.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(pick_list_options, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
        print(f"pickList optionsを {output_filename} に保存しました。")


    rel_types = jama_access.get_relationship_types()
    output_filename = f".\\json\\relationshiptypes.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(rel_types, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    print(f"relationshipTypesを {output_filename} に保存しました。")

    #project_info={'id':182}
    for project_info in ret_json:
        projectID = project_info["id"]
        ret_json = jama_access.get_project(projectID)
        name = ret_json["fields"]["name"]
        print("指定プロジェクト名:" + name)
        # JSONファイルに保存
        output_filename = f".\\json\\project_{projectID}.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(ret_json, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)

        #Porjectの全アイテム取得
        items_list = []
        for dct_requirement_item in jama_access.get_abstract_items(projectID):
            items_list.append(dct_requirement_item)
            #print(json.dumps(dct_requirement_item, indent=4, sort_keys=True, separators=(',', ': ')))
        
        # JSONファイルに保存
        output_filename = f".\\json\\project_{projectID}_items.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(items_list, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    
        print(f"itemsを {output_filename} に保存しました。")
    
        relations_list = []
        for dct_reration in jama_access.get_relationships(projectID):
            relations_list.append(dct_reration)
            #print(json.dumps(dct_reration, indent=4, sort_keys=True, separators=(',', ': ')))

        # JSONファイルに保存
        output_filename = f".\\json\\project_{projectID}_relations.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(relations_list, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)  
        print(f"relationsを {output_filename} に保存しました。")

        # アイテムの中からattachmentアイテムを探して、ファイルをダウンロードする。
        for item in items_list:
            if item["itemType"] == 22: # "ATTACHMENT"
                
                # JamaのAPIを使ってattachmentファイルを取得
                try:
                    attachment_id = item["id"]
                    print(f"Downloading attachment ID {attachment_id} using Jama API...")
                    
                    # get_attachments_fileメソッドを使用してファイルを取得
                    file_content = jama_access.get_attachments_file(attachment_id)
                    
                    # ファイル名を直接使用（item['fileName']から取得）
                    safe_filename = item.get('fileName', f'attachment_{attachment_id}')
                    
                    filepath = os.path.join(".\\json", safe_filename)
                    
                    # ファイルを保存
                    with open(filepath, 'wb') as f:
                        f.write(file_content)
                    
                    print(f"Successfully downloaded: {filepath} ({len(file_content)} bytes)")
                        
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # 404/not found エラーは軽くスキップ
                    if "404" in error_str or "not found" in error_str:
                        print(f"Skipping {item["id"]} (file not found - likely deleted)")
                    else:
                        # その他のエラーは目立つ表示
                        print(f"🚨 ===== DOWNLOAD ERROR =====")
                        print(f"❌ Failed to download attachment {item['id']} ")
                        print(f"🔍 Error: {e}")
                        print(f"📋 This may require attention:")                    
                        # エラーの詳細を表示
                        import traceback
                        print(f"Error details: {traceback.format_exc()}")
                    
if __name__ == '__main__':
    main()