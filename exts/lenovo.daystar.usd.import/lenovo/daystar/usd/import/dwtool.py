import os
import json
import requests
import carb
import omni
import omni.kit.pipapi

omni.kit.pipapi.install(
    package="requests",
    # version="2.13.0",
    # sometimes module is different from package name, module is used for import check
    module="requests",
    # ignore_import_check=False,
    # ignore_cache=False,
    # use_online_index=True,
    # surpress_output=False,
    # extra_args=[]
)

class DWTool:
    _instance = None  
  
    def __new__(cls, *args, **kwargs):  
        if not cls._instance:  
            cls._instance = super(DWTool, cls).__new__(cls, *args, **kwargs)  
        return cls._instance 
    
    def __init__(self):
        carb.log_info(f"**********init**********")
        self.captchaCode = "3$2s"
        self.is_login = False
        # self.domain = "https://testng-starworld.lenovo-r.cloud:30007"
    
    def check_status(self):
        return self.is_login == True

    def loginToDW(self,domain,user_name,pwd):
        carb.log_info(f"**********login**********")
        self.domain = domain
        self.userName = user_name
        self.password = pwd
        data = {'username': self.userName,
                'password': self.password, 'captchaCode': self.captchaCode}
        json_str = json.dumps(data)
        json_data = json_str.encode('utf-8')
        headers = {"Content-type": "application/json"}
        url = self.domain + "/platform/api/v1/auth/login"
        response = requests.post(url, headers=headers, data=json_data)
        data = json.loads(response.text)
        carb.log_info(response.text)
        if data["code"] != 200:
            carb.log_info(f"login error...")
            self.is_login = False
            return False
        
        self.token = data["data"]["accessToken"]
        self.is_login = True
        return True

    def getAssetByName(self,file_name):
        carb.log_info(f"getAssetByName:{file_name}")
        url = f"{self.domain}/platform/api/v1/asset/contents/page?current=1&size=99999&type_in=model&platform=windows"
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(url, headers=headers)
        carb.log_info(response.text)
        data = json.loads(response.text)
        if data and data["data"]["records"]:
            for item in data["data"]["records"]:
                if file_name == item['name']:
                    return item['id']
        return ''           
        
    def uploadAssetToDW(self,file_name, targetfile):
        # file_name = os.path.basename(targetfile)
        # file_name, _ = os.path.splitext(file_name)
        file_name = f'[ov]-{file_name}'
        carb.log_info(f"filename:" + file_name)
        if not os.path.exists(targetfile):
            carb.log_info(f"**********file is not exit**********" + targetfile)
            return
        
        headers = {"Authorization": "Bearer " + self.token}
        id = self.getAssetByName(file_name)
        if not id == '':
            # 更新逻辑
            carb.log_info(f"**********update_asset**********")
            url = self.domain + "/platform/api/v1/asset/contents/update"
            form_data = {'name': file_name, 'type': 'model','id':id}
        else:
            # 新增逻辑
            carb.log_info(f"**********upload_asset**********")
            url = self.domain + "/platform/api/v1/asset/contents/add"
            form_data = {'name': file_name, 'type': 'model'}
       
        files = {'dataFile': open(targetfile, 'rb')}
        response = requests.post(url, headers=headers,
                                 data=form_data, files=files)
        carb.log_info(response.text)
