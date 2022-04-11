import socket
import socks
import requests
import json
from decimal import*
from getpass4 import getpass
import base64
import os
import time
import select
import threading
import pyautogui

import Modules.to_launcher

game_port = 5588

# essential

# gets aqw server ips for hash test
def getServerIP():
    servers = json.loads(requests.get("https://game.aq.com/game/api/data/servers").text)
    return [server["sIP"] for server in servers]
def getGameversion():
    return json.loads(requests.get("https://game.aq.com/game/api/data/gameversion").text)["sFile"]

game_ip = getServerIP()[0]

# create the required folders for saving
def createFolders(folderpath):
    folders = folderpath.split("/")
    root = os.getcwd()
    try:
        for folder in folders:
            root += "/"+folder
            if not os.path.isdir(root):
                os.mkdir(root)
    except Exception as e:
        print("Failed to create dir. because:", e)

# gets the instance hash
def get_hash(userdata):
    data_login = {
        "pwd":userdata['password'],
        "unm":userdata['username'],
        "user":userdata['username'],
        "pass":userdata['password'],
        "option":0
        }
    headers_login = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0',
        'Referer':'https://www.aq.com/game/gamefiles/spider.swf'
        }
    #r = requests.post(url='https://game.aq.com/game/cf-userlogin.asp', data=data_login, headers=headers_login)
    r = requests.post(url='https://game.aq.com/game/api/login/now', data=data_login, headers=headers_login)
    #print(r.text.split('sToken="')[1])
    #print(r.text)
    hash_user = json.loads(r.text)["login"]["sToken"]
    return hash_user

# get bank data
def get_inventory(userdata):
    r = requests.post(url="https://game.aq.com/game/api/char/bank", headers={"ccid":userdata["charId"],
                                                                             "token":userdata["sToken"]})
    return r.text

# get the ccip
def get_charId(username):
    return requests.get(url="https://account.aq.com/CharPage?id={}".format(username)).text.split("ccid = ")[1].split(";",1)[0]

# send data to port
def send_data(data, s):
    s.send("{}\x00".format(data).encode('ascii'))

# login to the game
def game_login(username, hash_user, game_ip=game_ip, game_port=game_port):
    s = socks.socksocket()
    s.connect((game_ip, game_port))
    login_request = "<msg t='sys'><body action='login' r='0'><login z='zone_master'><nick><![CDATA[SPIDER#0001~{}~3.063]]></nick><pword><![CDATA[{}]]></pword></login></body></msg>".format(username, hash_user)
    send_data(login_request, s)
    print(f"Logged in to {username}.")
    time.sleep(0.5)
    return s


# for password protection purposes:
def encryptPass(password):
    getcontext().prec=64
    password = [Decimal(ord(i)) for i in password][::-1]
    sum1 = Decimal(1)
    password = [Decimal(min(password))]+[Decimal(i-Decimal(min(password))) for i in password]
    for i in password:
        sum1 += Decimal(i**2)
    password = [Decimal(Decimal(i)/Decimal(sum1)) for i in password]+[Decimal(Decimal(1)/Decimal(sum1))]
    password = [str(i) for i in password]
    return base64.b64encode(":".join(password).encode("ascii")).decode("ascii").replace("MD", "____________").replace("w_", "*********")

def decryptPass(password):
    password = base64.b64decode(password.replace("*********", "w_").replace("____________", "MD").encode("ascii")).decode("ascii")
    getcontext().prec=64
    x = password.split(":")
    sum1 = Decimal(1)/Decimal(x[-1])
    x = [round(Decimal(i)*Decimal(sum1)) for i in x[:-1]]
    return "".join([chr(i+x[0]) for i in x[1:]][::-1])

# open users file
def open_users():
    if not os.path.exists(os.getcwd()+"/Cache/Users.json"):
        return False
    f = open(os.getcwd()+"/Cache/Users.json", "r")
    data = f.read()
    f.close()
    try:
        data = json.loads(data)
    except Exception as e:
        print("Somewhing went wrong:", e)
        return False
    return data

# parses all the data recieved
def data_parse(packets, sorted_packets):
    # returns false whenever player has logged out.
    # else returns true
    for packet in packets:
        packet = packet.decode("utf-8")

        # check for specific packets in json format
        if packet.startswith("{"):
            packet = json.loads(packet)
            if "b" in packet:
                if "o" in packet["b"]:
                    if "cmd" in packet["b"]["o"]:
                        
                        # checking if inventory packet
                        if packet["b"]["o"]["cmd"] == "loadInventoryBig":
                            sorted_packets["json"]["loadInventoryBig"] =packet

        # check for specific packets in xml format
        elif packet.startswith("<"):
            continue

        # check for specific packets in xt format
        elif packet.startswith("%"):

            #checking if logout packet
            if packet == "%xt%server%-1%Goodbye!%":
                return False
            elif packet.startswith("%xt%wheel%-1%"):
                print(packet[:-1].split("%")[-1])
    
    return True
        
    

# recieve server data
def data_collect(s, sorted_packets):
    data = b""
    sockets_error = []
    state = True
    while not len(sockets_error):
        sockets_read, sockets_write, sockets_error = select.select([s],[s],[s])
        for s in sockets_read:
            data += s.recv(4096)
        for s in sockets_write:
            message = data.split(b"\x00")
            packets = message[0:-1]
            data = message[-1]
            state = data_parse(packets, sorted_packets)
            time.sleep(0.05)
        if not state:
            break

# add the the two inventories
def composeInv(bank, inventory):
    return 0

# find item in inventory
def checkInvItem(item, inv):
    for item_ in inv:
        if item_["sName"].lower() == item.lower():
            return item_
    return False

# Specific: checks for an item if in inventory 
def checkItem(inv, bank, item="gear of doom"):
    GOD = checkInvItem(item, inv)
    if GOD:
        return GOD["iQty"], GOD
    GOD = checkInvItem(item, bank)
    if GOD:
        return GOD["iQty"], GOD
    return 0, GOD
        
    

#--------------------------------------------------------------------------------------------
# Commands

def daily(args):
    if len(args) < 2:
        print("Use: '/daily all', or '/daily [username/user#]' to quickly check and do dailies through all accounts.")
    elif args[1].lower() == "all":
        allusers = {}
        data = open_users()
        if not data:
            print("No account registered.")
            return False
        for user in data["users"]:
            try:
                logindata, s = login(["/login", user])
                god_count, GOD = checkItem(logindata["data"]["json"]["loadInventoryBig"]["b"]["o"]["items"],
                                     json.loads(logindata["bank"]))
                if god_count == 3:
                    print(user, "has 3 Gears of Doom. Please wait.")
                    send_data("%xt%zm%bankToInv%1%{}%{}%".format(GOD["ItemID"], int(GOD["CharItemID"])),s)
                    time.sleep(0.6)
                    send_data("%xt%zm%cmd%1%tfer%{}%doom-999999%".format(user),s)
                    time.sleep(0.6)
                    send_data("%xt%zm%moveToCell%1%Enter%Spawn%",s)
                    time.sleep(0.6)
                    send_data("%xt%zm%tryQuestComplete%1%3076%-1%false%wvz%",s)
                    time.sleep(1)
                    god_count = 0
                    
                send_data("%xt%zm%cmd%1%logout%",s)
                time.sleep(0.5) 
                print(f"Logged out of {user}.")
                allusers[user] = god_count
            except Exception as e:
                print(e)
        userspace = len(max(list(data["users"].keys()), key=len))
        if userspace < 9:
                userspace = 9
        print("username:".ljust(userspace+2, " ")+"Gears of Doom:")
        for collected in allusers:
            print(collected.ljust(userspace+2, " ")+str(allusers[collected]).rjust(14," "))
    else:
        logindata, s = login(["/login", args[1]])
        print(logindata["data"]["json"]["loadInventoryBig"]["b"]["o"])
        if god_count == 3:
            print("Has 3 Gears of Doom. Please wait.")
            send_data("%xt%zm%bankToInv%1%{}%{}%".format(GOD["ItemID"], int(GOD["CharItemID"])),s)
            time.sleep(0.6)
            send_data("%xt%zm%cmd%1%tfer%{}%doom-999999%".format(logindata["username"]),s)
            time.sleep(0.6)
            send_data("%xt%zm%moveToCell%1%Enter%Spawn%",s)
            time.sleep(0.6)
            send_data("%xt%zm%tryQuestComplete%1%3076%-1%false%wvz%",s)
            time.sleep(1)
            god_count = 0
        send_data("%xt%zm%cmd%1%logout%",s)
        time.sleep(0.5) 
        print(f"Logged out of {logindata['username']}.")
        if not logindata:
            return False
        god_count, GOD = checkItem(logindata["data"]["json"]["loadInventoryBig"]["b"]["o"]["items"],
                             json.loads(logindata["bank"]))
        print(logindata["username"]," has", god_count, "Gear(s) of Doom")
    return True
        


# login to game
def login(args):
    if len(args) >= 2:
        data = open_users()
        if not data:
            print("Nothing registered.")
            return False

        if args[1].isnumeric():
            i = 0
            for user in data["users"]:
                if i == eval(args[1]):
                    args[1] = user
                    break
                i+=1
            if args[1].isnumeric():
                print(args[1],"is out of index.")
                return False
        elif args[1].lower() == "all":
            data = open_users()
            if not data:
                print("Nothing registered.")
                return False
            for user in data["users"]:
                try:
                    #threads += [threading.Thread(target=login, args=(["/login", user],))]
                    info, s = login(["/login", user])
                    send_data("%xt%zm%cmd%1%logout%",s)
                    time.sleep(0.5) 
                    print(f"Logged out of {user}.")
                except Exception as e:
                    print("Something went wrong:",e)
                #for thread in threads:
                 #   thread.start()
                                
            return True
        else:
            args[1] = args[1].lower()
            if args[1].lower() not in data["users"]:
                print("No user named", args[1], "is registered.")
                return False
        
        username = args[1]
        password = decryptPass(data["users"][args[1]]["secretKey"])
        try:
            sorted_packets = {"json":{}, "xml":[], "xt":[]}
            hash_user = get_hash({"username":username, "password":password})
            s = game_login(username, hash_user)

            # starting threading
            T = threading.Thread(target = data_collect, args = (s,sorted_packets,))
            T.daemon = True
            T.start()
            #T.join()
            time.sleep(0.3)
            send_data("%xt%zm%firstJoin%1%",s)
            time.sleep(0.4)
            send_data("%xt%zm%cmd%1%ignoreList%$clearAll%",s)
            time.sleep(0.6)
            send_data("%xt%zm%retrieveUserDatas%0%",s)
            time.sleep(0.6)
            send_data("%xt%zm%retrieveInventory%2%0%",s)
            time.sleep(0.5)
            while "loadInventoryBig" not in sorted_packets["json"]:
                #print(sorted_packets)
                time.sleep(0.5)

            send_data("%xt%zm%moveToCell%0%Enter%Spawn%",s)
            time.sleep(0.3)
            bank = get_inventory({"charId":data["users"][username]["charId"],"sToken":hash_user})
            ##data_collect(s)
            #T.terminate()
            #T.join()
            return {"data":sorted_packets, "bank":bank, "username":username},s
        except Exception as e:
            print("Error logging in:", e)

    else:
        users(args)
        print("Login to a character to register in-game. This is useful for daily rewards.",
              "\nType: '/login [username/user#]'",
              "\nOr:   '/login all'")
        return False
        
        
        

# add paths

def addPath(prefix):
    
    #
    if len(prefix)==1 or len(prefix) >= 4:
        print("Commands:",
              "\n\t/add suffix",
              "\n\t/add userpath",
              "\n\t/add quality\n")
        print("Set up a suffix for which client you wish to run by the format:",
              "\n\t'/add suffix [suffix-name]' (example: /add suffix grim)")
        print("You can set up a path for a specific registered user by the following:",
              "\n\t'/add userpath [username/user#]' (example /add userpath Jason)")
        print("Change in-game quality on /run using /add quality command")
        return False

    f = open(os.getcwd()+"/Cache/Users.json", "a+")
    f.seek(0)
    data = f.read()
    f.close()
    try:
        data = json.loads(data)
    except:
        data = {"users":{},"suffices":{}}
    f = open(os.getcwd()+"/Cache/Users.json", "w")
    f.write(json.dumps(data,indent=2))
    f.close()

    # adds a suffix to load clients   
    if prefix[1] == "suffix":
        if len(prefix) == 2:
            print("Set up a suffix for which client you wish to run by the format:",
                  "\n\t'/add suffix [suffix-name]' (example: /add suffix grim)")
        else:
            Modules.to_launcher.createPrefix(prefix[2])

    # adds a specific userpath
    elif prefix[1] == "userpath":
        if len(prefix) == 2:
            print("\nYou can set up a path for a specific registered user by the following:",
                  "\n\t'/add userpath [username/user#]' (example /add userpath Jason)")
        else:
            if prefix[2].isnumeric():
                try:
                    prefix[2] = list(data["users"].keys())[eval(prefix[2])]
                except:
                    print("Check your index.")
                    return False
            Modules.to_launcher.changeUsersPaths(user=prefix[2])

    # changes quality of client
    elif prefix[1] == "quality":
        data = open_users()
        if not data:
            data = {"users":{}, "suffices":{},"" "quality":"AUTO"}
        if "quality" not in data:
            data["quality"] = "AUTO"
            
        qualities = ["AUTO", "LOW", "MEDIUM", "HIGH"]
        print("#: " +"Quality:")
        for i in range(len(qualities)):
            print(i, " ", qualities[i].rjust(6, " "))
        try:
            quality = qualities[int(input("\nquality#: "))]
            data["quality"] = quality
            print(f"Quality set to {quality}.")
        except:
            print("Invalid choice. Pick a number between 0 and 3")
        f = open(os.getcwd()+"/Cache/Users.json", "w")
        f.write(json.dumps(data, indent=2))
        f.close()
        return True
            
        
    else:
        print("Commands:",
              "\n\t/add suffix",
              "\n\t/add userpath",
              "\n\t/add quality\n")
        print("Set up a suffix for which client you wish to run by the format:",
              "\n\t'/add suffix [suffix-name]' (example: /add suffix grim)")
        print("You can set up a path for a specific registered user by the following:",
              "\n\t'/add userpath [username/user#]' (example /add userpath Jason)")
        print("Change in-game quality on /run using /add quality command")
        return False
    

# registers user in Cache/Users.json file
def register(args):
    username = input("Username: ").lower()
    password = getpass("Password: ")
    try:
        hashcheck = get_hash({"username":username, "password":password})
        f = open(os.getcwd()+"/Cache/Users.json", "a+")
        f.seek(0)
        data = f.read()
        f.close()
        try:
            data = json.loads(data)
        except:
            data = {"users":{},"suffices":{}, "quality":"AUTO"}
        data["users"][username] = {"secretKey":encryptPass(password), "clientPath":"", "charId":get_charId(username)}
        f = open(os.getcwd()+"/Cache/Users.json", "w")
        f.write(json.dumps(data, indent=2))
        f.close()
        print("Successfully registered.")
    except:
        print("The username and password you entered did not match.\nPlease check the spelling and try again.")

# shows all registered users
def users(args):
    if not os.path.exists(os.getcwd()+"/Cache/Users.json"):
        print("No users/suffices registered.")
        return False
    f = open(os.getcwd()+"/Cache/Users.json", "r")
    
    try:
        data = json.loads(f.read())
        i = 0
        print("Users:")
        f.close()
        userspace = len(max(list(data["users"].keys()), key=len))
        if userspace < 9:
                userspace = 9
        print(" ".ljust(2," ")+"user#:".ljust(8, " ")+"username:".ljust(userspace+2, " ")+"direct-client-path:")
        for user in list(data["users"].keys()):
            print(" ".ljust(2," ")+str(i).rjust(5, " ")+" "*3+user.ljust(userspace+2, " ")+data["users"][user]["clientPath"])
            i += 1
            
        print("Suffices:")
        suffixspace = 7
        if len(data["suffices"])>0:
            suffixspace = len(max(list(data["suffices"].keys()), key=len))
            if suffixspace < 7:
                suffixspace = 7
            #print(suffixspace)
        print("  "+"suffix:".ljust(suffixspace+2, " ")+"client-path:")
        for suffix in list(data["suffices"].keys()):
            print("  "+suffix.rjust(suffixspace, " ")+"  "+data["suffices"][suffix])
    except:
        print("No users registered.")
        f.close()

# delete users:
def remove(args):
    if len(args) == 1:
        print("Commands:",
              "\n\t/remove user",
              "\n\t/remove suffix")
        print("\n'/remove user [username]' removes the user from the storage.",
              "\n'/remove suffix [suffix]' removes the suffix from the storage.")
        return False
    if not os.path.exists(os.getcwd()+"/Cache/Users.json"):
        print("Nothing registered yet.")
        return False
    f = open(os.getcwd()+"/Cache/Users.json", "r")
    data = f.read()
    f.close()
    try:
        data = json.loads(data)
    except Exception as e:
        print("Somewhing went wrong:", e)
        return False
    
    if args[1] == "user":
        if len(args) != 3:
            print("'/remove user [username]' removes the user from the storage. Example: /remove user jason")
            return False
        args[2] = args[2].lower()
        try:
            if args[2] in data["users"]:
                del data["users"][args[2]]
            else:
                print("No user named",args[2], "is registered.")
        except Exception as e:
            print("Something went wrong:", e)
    elif args[1] == "suffix":
        if len(args) != 3:
            print("'/remove suffix [suffix]' removes the suffix from the storage. Example: /remove suffix grim")
            return False
        try:
            if args[2] in data["suffices"]:
                del data["suffices"][args[2]]
            else:
                print("No suffix named", args[2], "is registered.")
        except Exception as e:
            print("Something went wrong:", e)
    else:
        print("Commands:",
              "\n\t/remove user",
              "\n\t/remove suffix")
        return False    

    f = open(os.getcwd()+"/Cache/Users.json", "w")
    f.write(json.dumps(data, indent=2))
    f.close()
    users(args)

# open the client from user path
def run(args):
    if len(args) == 1:
        users(args)
        print("\nChoose a user to open client for. Specify suffix if necessary.",
              "\nGeneral format: '/run [username/user#] [suffix]' (example: /run 0 grim)")
        return False

    if not os.path.exists(os.getcwd()+"/Cache/Users.json"):
        #print("No users/suffices registered.")
        return False
    f = open(os.getcwd()+"/Cache/Users.json", "r")
    data = f.read()
    f.close()
    try:
        data = json.loads(data)
    except:
        return False
    
    if len(args) >= 2:
        if args[1].isnumeric():
            try:
                args[1] = list(data["users"].keys())[eval(args[1])]
            except:
                print("Check your index.")
                return False
        else:
            if args[1].lower() not in data["users"]:
                print("No user named "+args[1]+" is registered. Do '/users' to check.")
                return False
        
        password = decryptPass(data["users"][args[1].lower()]["secretKey"])
        suffix = ""
        userpath = True
        if len(args) == 3:
            suffix = args[2]
            userpath = False
                
        Modules.to_launcher.openClient(username=args[1], password=password,
                                       userpath=userpath, client=suffix, quality=data["quality"])
        time.sleep(5)
        pyautogui.press("l")
    else:
        print("Something went wrong. This was the user-input:", args)

# login to all users    


# function running the inputs and redirects:
fncts = {
    "/register" :   register,
    "/run"      :   run,
    "/login"    :   login,
    "/daily"    :   daily,
    "/add"      :   addPath,
    "/remove"   :   remove,
    "/users"    :   users
    }

def cmds(userinput):
    rec = userinput.split(" ")
    if rec[0] in fncts:
        fncts[rec[0]](rec)


def main():
    createFolders("Cache")
    if not os.path.exists(os.getcwd()+"/Cache/Users.json"):
        addPath(["/add", "quality"])
    f = open(os.getcwd()+"/Cache/Users.json", "r")
    d = json.loads(f.read())
    f.close()
    if "quality" not in d:
        addPath(["/add", "quality"])
    del d
    
    print("commands:")
    for fnct in fncts:
        print("\t"+fnct)
    print("\t"+"exit()")
    print("")
    userins = ""
    while not userins.startswith("exit"):
        userins = input(": ")
        cmds(userins)


#print(getServerIP())
print("NOTE: DO NOT USE /login [username/user#] FOR NOW.")
main()







