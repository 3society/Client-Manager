import platform
import os
import json
from tkinter import Tk, filedialog
import subprocess

def findFolder(path, extra):
    folders = []
    for root, dirs, files in os.walk(path):
        for direc in dirs:
            if extra in direc:
                folders += [os.path.join(root, direc)]
    if folders != []:
        return folders
    return False

def findAQWcache_path():
    try:
        userpath = os.path.expanduser("~")
        if platform.system() == "Darwin":
            userpath = findFolder(userpath+"/Library/Application Support/Artix Game Launcher/Pepper Data/Shockwave Flash/WritableRoot/#SharedObjects", ".aq.com")
        elif platform.system().lower() == "windows":
            userpath = findFolder(userpath+"/AppData/Roaming/Macromedia/Flash Player/#SharedObjects", ".aq.com")
        else:
            print("Cannot not recognize your OS.")
            return False
        return userpath
    except:
        return False  

# Opens dialog for user to choose the file it wants to open.
def createPaths():
    open_file = ""
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.update()
    open_file = filedialog.askopenfilename(filetypes=[('Game Clients', '*.exe')])
    root.destroy()
    if open_file == "":
        return ""
    return os.path.abspath(open_file)

# Create a path for some prefix
def createPrefix(prefix):
    if not os.path.exists(os.getcwd()+"/Cache/Users.json"):
        print("Nothing registered.")
        data = {"users":{},"suffices":{}}
    else:
        f = open(os.getcwd()+"/Cache/Users.json", "r")
        try:
            data = json.loads(f.read())
            f.close()
        except:
            print("Something is missing in the /Cache/Users.json. Rewriting.")
            f.close()
            data = {"users":{},"suffices":{}}
            return False
    if prefix == "":
        print("No prefix inputted")
        return False
    data["suffices"][prefix] = createPaths()
    if data["suffices"][prefix] == "":
        print("Cancelled process.")
        return False
    f = open(os.getcwd()+"/Cache/Users.json", "w")
    f.write(json.dumps(data, indent=2))
    f.close()
    return True

# Changing the user path, or prefix if it is specified
def changeUsersPaths(user="", prefix=""):
    if not os.path.exists(os.getcwd()+"/Cache/Users.json"):
        print("No saved users registered.")
        return False
    f = open(os.getcwd()+"/Cache/Users.json", "r")
    try:
        data = json.loads(f.read())
    except:
        print("Something is missing in the /Cache/Users.json. Show to Eso if it looks unusual.")
        f.close()
        return False
    f.close()

    if user=="":
        if prefix not in data["suffices"]:
            print("No suffix of your choice is registered for suffices.\n",
                "We only have these:", list(data["suffices"].keys()))
            return False

        print("Current client-path:", data["suffices"][prefix])

        data["suffices"][prefix] = createPaths()
        if data["suffices"][prefix] == "":
            print("Cancelled process.")
            return False
        print(f"Changed path associated to {prefix} to", data["suffices"][prefix])

    elif user in data["users"]:
        print("Current client-path:", data["users"][user]["clientPath"])
        data["users"][user]["clientPath"] = createPaths()
        if data["users"][user]["clientPath"] == "":
            print("Cancelled process.")
            return False
        print("Changed to", data["users"][user]["clientPath"])

    else:
        print("User named", user, "is not registered.")
        return False

    f = open(os.getcwd()+"/Cache/Users.json", "w")
    f.write(json.dumps(data, indent=2)) 
    f.close()
    return True

######################################################################################
######################################################################################

# tries to open client from path specified, and saved if there is no path for user.
def openClient(username="", password="", userpath=False, client="", quality="AUTO"):
    root = os.getcwd()
    state = saveLogin(username, password, quality=quality)

    if os.path.exists(root+"/Cache/Users.json"):
        f = open(root+"/Cache/Users.json", "r")
        try:
            data = json.loads(f.read())
            f.close()
        except:
            print("Cannot parse the json file. Please check", root+"/Cache/Users.json", 
                "and report to Eso if the file looks unusual.")
            f.close()
            return False
    else:
        data = {"users":{},"suffices":{}}
        return False
    
    # Checking if we are opening the file from user specified or from the general prefix
    if userpath:
        if username in data["users"]:
            if os.path.exists(data["users"][username]["clientPath"]):
                path = data["users"][username]["clientPath"]
            else:
                print(f"Direct to the Botting Client you wish to save/use for {username},\n",
                    f"because the path: {data['users'][username]['clientPath']} could not be found.")
                path = createPaths()
                data["users"][username]["clientPath"] = path

        else:
            print(username, "is not registered. Please do so first before trying to open client for that user.\n",
                "You can do so by '/register'")
            return False
    else:
        if client in data["suffices"]:
            if not os.path.exists(data["suffices"][client]):
                print(f"Direct to the Botting Client you wish to save/use for the suffix {client}",
                    f"because the path: {data['suffices'][client]} could not be found.")
                path = createPaths()
                data["suffices"][client] = path
            else:
                path = data["suffices"][client]
        else:
            print(client, "is not registered as a suffix. You can do so by '/add suffix [suffix-name]'")
            return False
    if not os.path.exists(path):
        print("No path selected")
        return False
    try:
        #os.system('"'+path+'"')
        os.startfile('"'+path+'"')
        f = open(root+"/Cache/Users.json", "w")
        f.write(json.dumps(data,indent=2))
        f.close()
        return True
    except Exception as e:
        print("Failed opening the file because:", e)
        return False
######################################################################################
######################################################################################

def saveLogin(username, password, quality='LOW'):
    AQWUserPref_path = findAQWcache_path()
    #print(AQWUserPref_path)
    if len(username) > 63 or len(password) > 63 or not AQWUserPref_path:
        return False
    UsrBin = (len(username)*2+1).to_bytes(1, "little").decode('Windows-1252')
    PswBin = (len(password)*2+1).to_bytes(1, "little").decode('Windows-1252')
    QtyBin = (len(quality)*2 +1).to_bytes(1, "little").decode('Windows-1252')
    TotBin = (len(username+password+quality)+132).to_bytes(1, "little").decode('Windows-1252')
    

    #AQWUserPref = b'\x00\xbf\x00\x00\x00uTCSO\x00\x04\x00\x00\x00\x00\x00\x0bAQWUserPref\x00\x00\x00\x03%bitCheckedUsername\x03\x00\x17strPassword\x06{PswBin}{password}\x00%bitCheckedPassword\x03\x00\x17strUsername\x06{UsrBin}{username}\x00\x0fquality\x06\tAUTO\x00'

    AQWUserPref = b'\x00\xbf\x00\x00\x00{TotBin}TCSO\x00\x04\x00\x00\x00\x00\x00\x0bAQWUserPref\x00\x00\x00\x03\x0fquality\x06{QtyBin}{quality}\x00%bitCheckedUsername\x03\x00\x11bSoundOn\x03\x00%bitCheckedPassword\x03\x00\x17strUsername\x06{UsrBin}{username}\x00\x11bDeathAd\x03\x00\x17strPassword\x06{PswBin}{password}\x00'

    AQWUserPref = AQWUserPref.decode('Windows-1252').format(TotBin=TotBin,QtyBin=QtyBin,quality=quality,
                                                            UsrBin=UsrBin,username=username,
                                                            PswBin=PswBin,password=password).encode('Windows-1252')
    
    #AQWUserPref = AQWUserPref.replace(b"{PswBin}", PswBin).replace(b"{password}", bytes(password, "utf-8")).replace(b"{UsrBin}", UsrBin).replace(b"{username}", bytes(username, "utf-8"))
    #print(AQWUserPref)
    for userpref_path in AQWUserPref_path:
        f = open(userpref_path + "/AQWUserPref.sol", "wb")
        f.write(AQWUserPref)
        f.close()
    return True
