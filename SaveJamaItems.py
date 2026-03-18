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
# v1.1 - 2026.03.11 Added attachment file download functionality. If an item is of type "ATTACHMENT", the script will attempt to download the file using the Jama API and save it to the local "json" folder. If the file is not found (e.g., it has been deleted), the script will skip it and print a message. For other errors during download, it will print a detailed error message with a stack trace for troubleshooting.
#
import re
from datetime import datetime, date, time, timedelta
from py_jama_rest_client.client import JamaClient
import json, os
import requests
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
import subprocess


download_dir = f".\\json"


def download_with_curl_api(img_url, file_path):
    """
    curlを使ってセッションベースでファイルをダウンロードする関数
    ログインセッションを確立してからファイルをダウンロード
    """
    try:
        auth_type = os.environ.get('AUTH_TYPE', '')
        
        # 保存先パスを準備
        cookie_jar = os.path.join(download_dir, "cookies.txt")
        
        if auth_type == 'BASIC':
            # Basic認証の場合
            jama_username = os.environ.get('JAMA_USERNAME')
            jama_password = os.environ.get('JAMA_PASSWORD')
            jama_url_base = os.environ.get('JAMA_URL', '').rstrip('/')
            
            if jama_username and jama_password and jama_url_base:
                print(f"[SESSION] Starting session-based download for user: {jama_username}")
                
                # Step 1: ログインページにアクセスしてCSRFトークンとcookieを取得
                login_url = f"{jama_url_base}/login.req"
                print(f"[LOGIN] Getting login page: {login_url}")
                
                login_cmd = [
                    'curl.exe', '-v', '-L', '--insecure',
                    '-c', cookie_jar,  # Save cookies
                    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '-o', 'login_page.html',
                    login_url
                ]
                
                result = subprocess.run(login_cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    print(f"[ERROR] Login page access failed: {result.returncode}")
                    return False
                
                # Step 2: ログインフォームを送信してセッションを確立
                print(f"[LOGIN] Authenticating user: {jama_username}")
                auth_cmd = [
                    'curl.exe', '-v', '-L', '--insecure',
                    '-b', cookie_jar,  # Use saved cookies
                    '-c', cookie_jar,  # Save new cookies
                    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '-H', 'Content-Type: application/x-www-form-urlencoded',
                    '-H', 'Referer: ' + login_url,
                    '-d', f'j_username={jama_username}&j_password={jama_password}',
                    '-o', 'auth_result.html',
                    f"{jama_url_base}/j_acegi_security_check"
                ]
                
                result = subprocess.run(auth_cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    print(f"[ERROR] Authentication failed: {result.returncode}")
                    return False
                
                # Step 3: セッションが確立された状態でファイルをダウンロード
                print(f"[DOWNLOAD] Downloading file with session: {img_url}")
                download_cmd = [
                    'curl.exe', '-v', '-L', '--insecure',
                    '-b', cookie_jar,  # Use session cookies
                    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '-H', 'Referer: ' + jama_url_base + '/',
                    '-o', file_path,
                    img_url
                ]
                
                result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=60)
                
                # Cleanup temporary files
                for temp_file in ['login_page.html', 'auth_result.html', cookie_jar]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                
                if result.returncode == 0:
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        file_size = os.path.getsize(file_path)
                        
                        # ファイル内容をチェック（HTMLログインページでないか確認）
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content_preview = f.read(200)
                            if 'login' in content_preview.lower() or '<html' in content_preview.lower():
                                print(f"[WARNING] Downloaded content appears to be HTML login page!")
                                return False
                        
                        print(f"[SUCCESS] Session-based download successful: {file_size} bytes")
                        return True
                    else:
                        print(f"[ERROR] curl completed but no file created")
                        return False
                else:
                    print(f"[ERROR] Session download failed with return code: {result.returncode}")
                    if result.stderr:
                        print(f"[CURL-ERR] curl stderr: {result.stderr}")
                    return False
            else:
                print(f"[ERROR] Missing BASIC auth credentials or JAMA_URL")
                return False
        else:
            print(f"⚠️  OAuth authentication not supported for downloading embedded pictures ")
            return False

    except FileNotFoundError:
        print(f"❌ curl.exe not found - please install curl")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ curl timeout (60 seconds)")
        return False
    except Exception as e:
        print(f"❌ curl API execution error: {e}")
        return False

def convert_to_download_url(original_url):
    """
    JamaのURL仕様に基づいて、表示用URLをダウンロード用URLに変換する関数
    例: https://deimos.accelsofteng.com/attachment/202/UAV-small.jpg
    → https://deimos.accelsofteng.com/attachment/202/d/UAV-small.jpg
    """
    try:
        # URLを解析
        parsed = urlparse(original_url)
        path_parts = parsed.path.strip('/').split('/')
        
        # /attachment/ID/filename の形式かチェック
        if len(path_parts) >= 3 and path_parts[0] == 'attachment':
            # /d/ を挿入してダウンロード用URLに変換
            download_path = f"/{path_parts[0]}/{path_parts[1]}/d/{'/'.join(path_parts[2:])}"
            download_url = f"{parsed.scheme}://{parsed.netloc}{download_path}"
            if parsed.query:
                download_url += f"?{parsed.query}"
            return download_url
        else:
            # 想定外の形式の場合はそのまま返す
            return original_url
    except Exception as e:
        print(f"⚠️  URL変換エラー: {e}")
        return original_url

def download_file(url, filename):
    """
    指定されたURLからファイルをダウンロードして保存する関数
    """

    try:
        # 方法1: curlでREST APIを使用したダウンロード（推奨）
        print(f"🔧 Trying curl + REST API method first...")
        if download_with_curl_api(url, filename):
            return True
        
        print(f"⚠️  curl + REST API failed, trying Jama Client API...")

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        # DNS解決エラーやドメイン名問題を検出
        if "Failed to resolve" in error_msg or "NameResolutionError" in error_msg:
            parsed_url = urlparse(url)
            print(f"🌐 ドメイン '{parsed_url.netloc}' にアクセスできません（DNS解決失敗）")
            print(f"💡 このURLは古いドメインまたは無効なドメインかもしれません - スキップします")
        else:
            print(f"❌ HTTP請求エラー: {e}")
        return False
    except OSError as e:
        print(f"❌ ファイル保存エラー: {e}")
        return False
    except Exception as e:
        print(f"❌ 予期せぬエラー: {e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")
        return False

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
    global download_dir
    
    jama_access = JamaAccess()

    ret_json = jama_access.get_projects()
    #print ("プロジェクト一覧リスト :")

    #print(json.dumps(ret_json, indent=4, sort_keys=True, separators=(',', ': ')))
    #カレントフォルダ配下にjsonフォルダを作成して、そこにプロジェクトごとにアイテムタイプ、アイテム、リレーションの情報を保存する。
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    #print ("\n アイテムタイプを調べます")
    type_list = []
    for ret_type in jama_access.get_item_types():
        type_list.append(ret_type)
        #print(json.dumps(ret_type, indent=4, sort_keys=True, separators=(',', ': ')))
    # JSONファイルに保存
    output_filename = os.path.join(download_dir, "project_itemtypes.json")
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(type_list, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    print(f"itemTypeを {output_filename} に保存しました。")

    # Get the list of projects from Jama
    # The client will return to us a JSON array of Projects, where each project is a JSON object.
    pick_lists = jama_access.get_pick_lists()
    output_filename = os.path.join(download_dir, "pick_lists.json")
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(pick_lists, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    print(f"pickListsを {output_filename} に保存しました。")
    #
    for picklist in pick_lists:
        pick_list_options = jama_access.get_pick_list_options(picklist['id'])
        output_filename = os.path.join(download_dir, f"pick_list_{picklist['id']}_options.json")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(pick_list_options, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
        print(f"pickList optionsを {output_filename} に保存しました。")


    rel_types = jama_access.get_relationship_types()
    output_filename = os.path.join(download_dir, "relationshiptypes.json")
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(rel_types, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    print(f"relationshipTypesを {output_filename} に保存しました。")

    #project_info={'id':204}
    for project_info in ret_json:
        projectID = project_info["id"]
        ret_json = jama_access.get_project(projectID)
        name = ret_json["fields"]["name"]
        print("指定プロジェクト名:" + name)

        project_setting_dir = os.path.join(download_dir, "project_setting")
        if not os.path.exists(project_setting_dir):
            os.makedirs(project_setting_dir)
        # JSONファイルに保存
        output_filename = os.path.join(project_setting_dir, f"project_{projectID}.json")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(ret_json, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)

        #Porjectの全アイテム取得
        items_list = []
        for dct_requirement_item in jama_access.get_abstract_items(projectID):
            items_list.append(dct_requirement_item)
            #print(json.dumps(dct_requirement_item, indent=4, sort_keys=True, separators=(',', ': ')))
        
        # JSONファイルに保存
        output_filename = os.path.join(project_setting_dir, f"project_{projectID}_items.json")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(items_list, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
    
        print(f"itemsを {output_filename} に保存しました。")
        
        # testPlan (itemType 35) のitem IDを収集
        test_plan_ids = []
        for item in items_list:
            if item.get("itemType") == 35:  # testPlan
                test_plan_ids.append(item["id"])
        
        if test_plan_ids:
            print(f"Found {len(test_plan_ids)} test plan(s): {test_plan_ids}")
            
            # 各testPlanに対してtestGroupsを取得・保存
            for test_plan_id in test_plan_ids:
                try:
                    print(f"Getting test groups for test plan {test_plan_id}...")
                    test_groups = list(jama_access.get_testgroups(test_plan_id))
                    
                    # testGroupsを保存
                    output_filename = os.path.join(project_setting_dir, f"project_{projectID}_test_plan_{test_plan_id}_testGroups.json")
                    with open(output_filename, 'w', encoding='utf-8') as f:
                        json.dump(test_groups, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
                    print(f"testGroupsを {output_filename} に保存しました。")
                    
                    # 各testGroupに対してtestCasesを取得・保存
                    for test_group in test_groups:
                        test_group_id = test_group["id"]
                        test_group_name = test_group.get("name", "unknown")
                        
                        try:
                            print(f"Getting test cases for test group {test_group_id} ({test_group_name})...")
                            test_cases = list(jama_access.get_testgroup_testcases(test_plan_id,test_group_id))
                            
                            # testCasesを保存
                            output_filename = os.path.join(project_setting_dir, f"project_{projectID}_testGroup_{test_group_id}_testcases.json")
                            with open(output_filename, 'w', encoding='utf-8') as f:
                                json.dump(test_cases, f, indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
                            print(f"testCasesを {output_filename} に保存しました ({len(test_cases)} test cases)。")
                            
                        except Exception as e:
                            print(f"❌ Failed to get test cases for test group {test_group_id}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"❌ Failed to get test groups for test plan {test_plan_id}: {e}")
                    continue
        else:
            print("No test plans found in this project.")
    
        relations_list = []
        for dct_reration in jama_access.get_relationships(projectID):
            relations_list.append(dct_reration)
            #print(json.dumps(dct_reration, indent=4, sort_keys=True, separators=(',', ': ')))

        # JSONファイルに保存
        output_filename = os.path.join(project_setting_dir, f"project_{projectID}_relations.json")
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
                    filename = item.get('fileName', "")
                    safe_filename = f'attachment_{projectID}_{attachment_id}_{filename}'
                    
                    filepath = os.path.join(project_setting_dir, safe_filename)
                    
                    # ファイルを保存
                    with open(filepath, 'wb') as f:
                        f.write(file_content)
                    
                    print(f"Successfully downloaded: {filepath} ({len(file_content)} bytes)")
                        
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # 404/not found エラーはスキップ
                    if "404" in error_str or "not found" in error_str:
                        print(f"Skipping {item['id']} (file not found - likely deleted)")
                    else:
                        # その他のエラーは目立つ表示
                        print(f"🚨 ===== DOWNLOAD ERROR =====")
                        print(f"❌ Failed to download attachment {item['id']} ")
                        print(f"🔍 Error: {e}")
                        print(f"📋 This may require attention:")                    
                        # エラーの詳細を表示
                        import traceback
                        print(f"Error details: {traceback.format_exc()}")
            else:
                # アイテムがattachmentでない場合はスキップ
                description_field = item.get('fields', {}).get('description', '')
                
                #<img src= タグがdescriptionに含まれている場合、ファイルをJamaプロジェクトにアップロードしてURLを置換する
                if '<img' in description_field.lower() and 'src=' in description_field.lower():
                    img_text = description_field
                    # <img>タグのsrc属性を抽出する正規表現パターン
                    img_pattern = r'<img[^>]*?src\s*=\s*["\']([^"\']*?)["\'][^>]*?>'
                    img_matches = re.findall(img_pattern, img_text, re.IGNORECASE | re.DOTALL)
                    
                    if img_matches:
                        for i, img_url in enumerate(img_matches, 1):
                            if "jama.jamasoftware.net" in img_url:
                                #Jama's old domain - likely inaccessible, skip it
                                continue                    
                            try:
                                #print(f"🔽 Processing image {i}/{len(img_matches)}: {img_url}")
                            
                                # URLからファイル名を抽出（パス情報を除いた部分）
                                filename = os.path.basename(img_url.split('?')[0])  # クエリパラメータも除去
                                if not filename:
                                    filename = f'image_{i}'
                                
                                #print(f"Extracted filename: {filename}")
                                
                                # JamaのURL仕様に基づいてダウンロードURLに変換
                                download_url = convert_to_download_url(img_url)
                                #print(f"Download URL: {download_url}")
                                
                                from urllib.parse import urlparse
                                parsed_url = urlparse(download_url)
                                path_parts = parsed_url.path.strip('/').split('/')
                                
                                if len(path_parts) >= 2 and path_parts[0] == 'attachment':
                                    attachment_id = path_parts[1]

                                # ファイルをダウンロード
                                safe_filename = f'attachment_{projectID}_{attachment_id}_{filename}'
                                file_path = os.path.join(project_setting_dir, safe_filename)
                                success = download_file(download_url, file_path)
                                if success:
                                    print(f"✅ Downloaded: {safe_filename}")
                                else:
                                    print(f"❌ Failed to download: {safe_filename}")
                                    
                            except Exception as e:
                                print(f"❌ Error download image {i} ({img_url}): {e}")
                                import traceback
                                print(f"Error details: {traceback.format_exc()}")
                                continue                

if __name__ == '__main__':
    main()