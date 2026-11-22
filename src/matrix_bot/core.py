import simplematrixbotlib as botlib
import requests as req
from agentmail import AgentMail
from httpx_sse import connect_sse
import os.path, base64, poplib, smtplib, os, email, httpx2, json, time, asyncio
from  platformdirs import PlatformDirs, user_config_dir
from . import menu  # import the module
from dotenv import load_dotenv, dotenv_values
from email import policy

# matil.tm related variables
url = "https://api.mail.tm/domains"
domains = []

# Create an SMTP object
smtpobj = smtplib.SMTP();


# Load variables from .env file
load_dotenv()

# Sms number verification
api_key_number = os.getenv("API_SMS")

server = None

# Define user local dir
dirs = PlatformDirs("matrix_bot")
if not os.path.exists(dirs.user_config_dir):
    os.mkdir(dirs.user_config_dir)

config = botlib.Config()
config.encryption_enabled = True
config.emoji_verify = True
config.ignore_unverified_devices = True
config.store_path = f"{dirs.user_config_dir}/store"
prefix = "!"


# Read credentials
matrix_pass = os.getenv("MATRIX_PASSWORD")
bot_name = os.getenv("BOT_NAME")
if not bot_name or not matrix_pass:
    raise ValueError("Error: check .env file")

creds = botlib.Creds("https://matrix.org", bot_name , matrix_pass, session_stored_file=f"{dirs.user_config_dir}/session")
bot = botlib.Bot(creds, config)
client = AgentMail(api_key=os.getenv("API_AGENTEMAIL"))



def get_access_token(client_id, refresh_token):
    data = {
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    ret = req.post('https://login.live.com/oauth20_token.srf', data=data)

    # Print the response content and access token
    return ret.json()['access_token']


def generate_auth_string(user, token):
    auth_string = f"user={user}\1auth=Bearer {token}\1\1"
    return auth_string

# Get content via pop3 protocol
def get_content_pop3(email_address: str):
    global server
    # Retrieve the list of emails
    num_messages = len(server.list()[1])
    print(f"There are {num_messages} emails in the inbox.")
    messages = []
    ids = []
    for i in range(num_messages):
            response, lines, octets = server.retr(i + 1)
            msg_content = b"\n".join(lines)
            msg = email.parser.BytesParser(policy=policy.default).parsebytes(msg_content)
            messages.append(msg['subject'] + " from " + msg['from'] + f" [{i+1}]")
            ids.append(email_address)
    return [num_messages, messages, ids]



# Pop3_ssl authentication
def pop3_connect(client_id, refresh_token, email):
    global server
    access_token = get_access_token(client_id, refresh_token)
    server = poplib.POP3_SSL('outlook.office365.com', 995)
    # Authenticate using OAuth2
    auth_string = generate_auth_string(email, access_token)
    encoded_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    server._shortcmd(f'AUTH XOAUTH2')
    server._shortcmd(f'{encoded_auth_string}')


# Create a temporary new email address
def spawn_email():
    resp = json.loads(req.get(url).text)
    for items in resp['hydra:member']:
        domains = str(items['domain'])
        return domains


# SMTP sending
def smtp_send(text,to,subject):
        smtpobj.ehlo()
        smtpobj.starttls() # Secure the connection
        smtpobj.login("","")



# Account creation
def spawn_account(address, passw):
    try:
        resp = json.loads(req.post("https://api.mail.tm/accounts", headers={"Content-Type": "application/json"}, json={"address":address, "password":"12345"}).text)
        if resp['@type'] == "Account":
            # Write token into storage file

            token = json.loads(req.post("https://api.mail.tm/token", headers={"Content-Type":"application/json"}, json={"address":address, "password":passw}).text)
            new_record = {"token": token['token'], "address": address,"account":token['id'] }
            with open(f"{dirs.user_config_dir}/token", "r") as fd:
                try:
                    # Read data and add new values
                    inner = json.load(fd)
                    inner.append(new_record)
                except:
                    print("Error: cannot read user data")

            fd = open(f"{dirs.user_config_dir}/token", "w+")
            try:
                json.dump(inner,fd)
            except:
                json.dump([new_record], fd)
            fd.close()
            return [200, new_record['token'], token['id']]
        else:
            return [resp['status'], resp['violations'][0]['message']]
    except:
        return ["0","unknown"]

# Fetch all existing mails
def fetch(token, address: str):
    # Distill logic based on email domain
    if address.split("@")[1] == "catchmail.io":
        inbox = json.loads(req.get(f"https://api.catchmail.io/api/v1/mailbox?address={address}").text)
        messages = []
        ids =[]
        for id, message in enumerate(inbox['messages']):
            new_str = message['subject'] + " from " + message['from'] +  f" [{id + 1}]"
            messages.append(new_str)
            ids.append(message['id'])

        return [inbox['total'], messages, ids, address]

    # If outlook
    elif address.split("@")[1] == "outlook.com":
        # Obtain client_id
        with open(f"{dirs.user_config_dir}/token", "r") as fd:
            pars = json.load(fd)
            for obj in pars:
                if obj['address'] == address:
                    pop3_connect(obj['account'], token, address)
                    return_val = get_content_pop3(address)
                    return_val.append(token)
                    print("output: ",  return_val)
                    return return_val
    else:
        try:
            resp = json.loads(req.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"}).text)
            # list every mail
            index =0
            ids =[]
            messages = []
            for arg  in resp['hydra:member']:
                index+=1
                new_str = arg['subject'] + " from " + arg['from']['address'] + f" [{index}]"
                ids.append(arg['id'])
                messages.append(new_str)
            return [resp['hydra:totalItems'],messages,ids,token ]
        except:
            print("error message")



# Register catchmail into config
def register_email(address: str):
    # Parse a new record
    new = {"token": "", "address": address, "account": ""}
    new_record = []
    with open(f"{dirs.user_config_dir}/token", "r") as fd:
        new_record = json.load(fd)
        # Check if the address already exists
        if any(str['address'] == address for str in new_record):
            return 0
        else:
            new_record.append(new)
    with open(f"{dirs.user_config_dir}/token", "w+") as fd:
        json.dump(new_record, fd)
        return 1



# Listener function
async def listen_mail(resp, room_id):
    async with httpx2.AsyncClient(timeout=None) as client:
        async with client.sse("https://mercure.mail.tm/.well-known/mercure", params = {"topic": f"/accounts/{resp[2]}"}, headers={"Authorization": f"Bearer {resp[1]}"}) as event_source:
            async for sse in event_source:
                data = json.loads(sse.data)
                #print("result: ", data['from'])
                if data['@type'] == "Message":
                    await bot.api.send_text_message(room_id, "You have received a new message from "+data['from']['address'])

# read all existing emails
def read_files():
    # Create file if not already
    if not os.path.isfile(f"{dirs.user_config_dir}/token"):
        open(f"{dirs.user_config_dir}/token", "w")
        return
    try:
        fd = open(f"{dirs.user_config_dir}/token", "r")
        data = json.load(fd)
        try:
            accounts = []
            fd.close()
            for i in data:
                accounts.append(i['address'])
            return [1, accounts]
        except:
            return [0]
    except:
        print("error")


# Find token based on address
def find_token(address):
    try:
        fd = open(f"{dirs.user_config_dir}/token", "r")
        parse = json.load(fd)
        for i in parse:
            if i['address'] == address:
                return [None, i['token'],i['account']]
    except:
        return [202]

# Obtain mail's content
def get_content(id, token, number):
    global server
    try:
        if token.split("@")[1] == "catchmail.io":
            resp = json.loads(req.get(f"https://api.catchmail.io/api/v1/message/{id}?mailbox={token}").text)
            return [resp['body']['text'], resp['body']['html']]
    except:
        # Check for outlook email
        try:
            if id.split("@")[1] == "outlook.com":
                response, lines, octets = server.retr(number)
                msg_content = b"\n".join(lines)
                msg = email.parser.BytesParser(policy=policy.default).parsebytes(msg_content)
                return [msg.get_body(preferencelist=("plain", "html")), ""]
        except:
            resp = json.loads(req.get(f"https://api.mail.tm/messages/{id}", params={"id":id},  headers={"Authorization": f"Bearer {token}"}).text)
            try:
                return [str(resp['text']), str(resp['html'])] # Return both: plain text and html content
            except:
                return [0]


# Check the purchase status
async def check_purchase(id):
    input = json.dumps({"key": os.getenv("API_DARKSTORE"), "id": id})
    resp = json.loads(req.post(f"https://darkstore.bz/api/v1/order/status", headers={"Content-Type": "application/json"}, data=input ).text)
    if resp['data']['status'] == "completed":
        # Look for the download link
        input = json.dumps({"key": os.getenv("API_DARKSTORE"), "id": id})
        resp = json.loads(req.post(f"https://darkstore.bz/api/v1/order/download", headers={"Content-Type": "application/json"}, data=input ).text)
        return resp['data']['link']
    else:
        return None


async def download_file(path: str):
    file = req.get(path)
    response = file.content.decode("utf-8")
    new_record = {"token": response.split(':')[2], "address": response.split(':')[0],"account": response.split(':')[3]}
    with open(f"{dirs.user_config_dir}/token", "r") as fd:
        try:
            # Read data and add new values
            inner = json.load(fd)
            inner.append(new_record)
        except:
            print("Error: cannot read user data")

    fd = open(f"{dirs.user_config_dir}/token", "w+")
    try:
        json.dump(inner,fd)
    except:
        json.dump([new_record], fd)
    fd.close()


# Purchase outlook account through darkstore service and 37283 product
async def buy_outlook(buy: bool, bot: botlib.Bot, room_id: str):
    if not buy:
        # Verify the cost
        input = json.dumps({"key": os.getenv("API_DARKSTORE"), "id": "37283"})
        resp = json.loads(req.post(f"https://darkstore.bz/api/v1/product/view", headers={"Content-Type": "application/json"}, data=input ).text)
        print("response_cost: ", resp['data']['price'] )
        return resp['data']['price']
    else:
        # Commit the purchase
        input = json.dumps({"key": os.getenv("API_DARKSTORE"), "product": "37283", "quantity": 1})
        resp = json.loads(req.post(f"https://darkstore.bz/api/v1/order/create", headers={"Content-Type": "application/json"}, data=input ).text)
        if resp['success'] == True:
            if resp['data']['status'] == "pending":
                await bot.api.send_text_message(room_id, "The purchase is successfull\nWaiting for the file...")
                # 50 attempts in total
                for i in range(50):
                    result = await check_purchase(resp['data']['id'])
                    if result != None:
                        await bot.api.send_text_message(room_id, "Confirmation!")
                        await download_file(result)
                        return
                    time.sleep(60) # Check every minute
                await bot.api.send_text_message(room_id, "Sorry, something went wrong with account purchase\n Check manually")
                return
            else:
                print("LInk for downloading: ", resp['data']['link'])
        else:
            print("error")



# Send email implementation
def send_mail(text, recever, subject):
    client.inboxes.messages.send(
        os.getenv("AGENTEMAIL_EMAIL"),
        to=[recever],
        subject=subject,
        text=text,
    )

# Delete an account
def delete_account(id, token):
    res = req.delete(f"https://api.mail.tm/accounts/{id}", headers={"Authorization": f"Bearer {token}"})
    try:
        new_content = []
        fd = open(f"{dirs.user_config_dir}/token", "r")
        parse = json.load(fd)
        fd.close()
        for i in parse:
            if i['account'] != id:
                new_content.append(i)
        with open(f"{dirs.user_config_dir}/token", "w+") as fd:
            json.dump(new_content, fd)
    except:
        print("Error")


# Balance viewer
def get_balance():
    repl = json.loads(req.get(f"https://api.buynumber.io/v1/account?api_key={api_key_number}&action=getBalance").text)
    return repl['data']['balance']



# Purchase a temporary phone number
def buy_number(service: str, max_price):
    repl = json.loads(req.get(f"https://api.buynumber.io/v1/activation-numbers?api_key={api_key_number}&action=getServices").text)
    for serv in repl['data']:
        if serv['name'].upper() == service.upper():
            repl = json.loads(req.get(f"https://api.buynumber.io/v1/activation-numbers?api_key={api_key_number}&action=getTopCountriesByService&service={serv['code']}").text)

            for country in repl['data']:
                # Make a purchase request
                repl = json.loads(req.get(f"https://api.buynumber.io/v1/activation-numbers?api_key={api_key_number}&action=newNumber&service={serv['code']}&country={country['country']}&max_price={max_price}").text)

                # If the result is successful
                if repl['result'] == "success":
                    return {"result": repl['result'], "price": repl['data']['price'], "number": repl['data']['phoneNumber'] }
                # If failed
                elif repl['result'] == "failed":
                    return {"result": repl['result'], "message":  repl['message']}



# Upload file to the room
async def upload_content( room_id: str, path: str, bot: botlib.Bot):
    fd = open(path, "rb") # Open file in binary mode
    resp, maybe_keys = await bot.api.async_client.upload(data_provider=fd, encrypt=True, filename="test")
    await bot.api.async_client.room_send( room_id=room_id,
        message_type="m.room.message",
          content = {
              "msgtype": "m.file",
              "url": resp.content_uri,
              "body": "descriptive title (like the filename)"
          }
    )
    fd.close()



# Command function menu
@bot.listener.on_message_event
async def echo(room, message):
        match = botlib.MessageMatch(room, message, bot, prefix)
        functions = {'read_files': read_files, "spawn_account": spawn_account, "listen_mail": listen_mail, "send_mail": send_mail, "register_email": register_email,
                     "spawn_email": spawn_email,"find_token": find_token, "fetch": fetch, "get_content": get_content,"get_balance": get_balance,"buy_number": buy_number, "buy_outlook": buy_outlook } # Define the functions
        await menu.get_call(room, message, match, bot, functions) # Call the callback function



while True:
    bot.run()
